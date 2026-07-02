from fastapi import APIRouter
import httpx
from core.config import settings

router = APIRouter(prefix="/monitoring", tags=["monitoring"])

SERVICES = ["PostgreSQL", "NATS", "Debezium", "VictoriaMetrics"]
REGIONS = ["NSW1", "QLD1", "SA1", "TAS1", "VIC1"]
HORIZONS = list(range(1, 25))


async def _vm_query(query: str) -> list:
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(
                f"{settings.VM_URL}/api/v1/query",
                params={"query": query},
            )
            if resp.status_code == 200:
                data = resp.json()
                return data.get("data", {}).get("result", [])
    except Exception:
        pass
    return []


async def _vm_query_range(query: str, start: float, end: float, step: int = 300) -> list:
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(
                f"{settings.VM_URL}/api/v1/query_range",
                params={"query": query, "start": start, "end": end, "step": step},
            )
            if resp.status_code == 200:
                data = resp.json()
                return data.get("data", {}).get("result", [])
    except Exception:
        pass
    return []


@router.get("/accuracy")
async def get_accuracy(region_id: str | None = None):
    """Get latest prediction accuracy per region and horizon."""
    if region_id:
        query = f'prediction_mape{{region="{region_id}"}}'
    else:
        query = "prediction_mape"

    results = await _vm_query(query)
    items = []
    for r in results:
        labels = r.get("metric", {})
        value = float(r["value"][1])
        items.append({
            "region": labels.get("region", ""),
            "horizon": int(labels.get("horizon", 0)),
            "mape": round(value, 2),
        })

    items.sort(key=lambda x: (x["region"], x["horizon"]))

    by_region = {}
    for item in items:
        reg = item["region"]
        if reg not in by_region:
            by_region[reg] = []
        by_region[reg].append(item)

    return {"regions": by_region, "items": items}


@router.get("/uptime")
async def get_uptime():
    """Get service uptime percentage over 24h and 7d."""
    services = []
    for svc in SERVICES:
        query_24h = f'avg_over_time(service_up{{service="{svc}"}}[24h]) * 100'
        query_7d = f'avg_over_time(service_up{{service="{svc}"}}[7d]) * 100'
        query_now = f'service_up{{service="{svc}"}}'

        results_24h = await _vm_query(query_24h)
        results_7d = await _vm_query(query_7d)
        results_now = await _vm_query(query_now)

        uptime_24h = round(float(results_24h[0]["value"][1]), 1) if results_24h else None
        uptime_7d = round(float(results_7d[0]["value"][1]), 1) if results_7d else None
        status = "up" if results_now and float(results_now[0]["value"][1]) == 1 else "down"

        services.append({
            "name": svc,
            "status": status,
            "uptime_24h": uptime_24h,
            "uptime_7d": uptime_7d,
        })

    return {"services": services}


@router.get("/latency")
async def get_latency():
    """Get current pipeline latency and trend over 24h."""
    latest_results = await _vm_query("pipeline_latency_seconds")
    latest = round(float(latest_results[0]["value"][1]), 2) if latest_results else 0.0

    import time
    now = time.time()
    range_results = await _vm_query_range(
        "pipeline_latency_seconds", now - 86400, now, 300
    )

    trend = []
    if range_results:
        for ts, val in range_results[0].get("values", []):
            trend.append({"time": ts, "value": round(float(val), 2)})

    return {
        "latest": latest,
        "trend": trend,
        "threshold_warning": 60,
        "threshold_critical": 300,
    }
