from fastapi import APIRouter
import httpx
import shutil
from core.config import settings

try:
    import psutil  # type: ignore
    _HAS_PSUTIL = True
except ImportError:
    _HAS_PSUTIL = False

router = APIRouter(prefix="/monitoring", tags=["monitoring"])

SERVICES = [
    "PostgreSQL", "NATS", "Debezium", "VictoriaMetrics",
    "VictoriaLogs", "Dagster", "MLflow", "Inference",
    "Garage", "Dashboard Backend",
]
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
async def get_accuracy(region_id: str | None = None, source: str = "realtime"):
    """Get prediction accuracy per region and horizon.

    Args:
        region_id: optional region filter
        source: 'realtime' (VM prediction_mape) or 'training' (MLflow metrics)
    """
    if source == "training":
        return await _get_training_accuracy(region_id)
    return await _get_realtime_accuracy(region_id)


async def _get_realtime_accuracy(region_id: str | None = None):
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
            "source": "realtime",
        })

    items.sort(key=lambda x: (x["region"], x["horizon"]))

    by_region = {}
    for item in items:
        reg = item["region"]
        if reg not in by_region:
            by_region[reg] = []
        by_region[reg].append(item)

    return {"regions": by_region, "items": items, "source": "realtime"}


async def _get_training_accuracy(region_id: str | None = None):
    """Fetch training metrics from MLflow for the latest demand-forecasting run."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            exp_resp = await client.get(
                f"{settings.MLFLOW_URL}/api/2.0/mlflow/experiments/search",
                params={"filter": "name = 'demand-forecasting'", "max_results": "1"},
            )
            if exp_resp.status_code != 200:
                return {"regions": {}, "items": [], "source": "training"}

            experiments = exp_resp.json().get("experiments", [])
            if not experiments:
                return {"regions": {}, "items": [], "source": "training"}

            exp_id = experiments[0]["experiment_id"]

            runs_resp = await client.post(
                f"{settings.MLFLOW_URL}/api/2.0/mlflow/runs/search",
                json={
                    "experiment_ids": [exp_id],
                    "filter": "tags.region != ''",
                    "order_by": ["start_time DESC"],
                    "max_results": 25,
                },
            )
            if runs_resp.status_code != 200:
                return {"regions": {}, "items": [], "source": "training"}

            runs = runs_resp.json().get("runs", [])

            by_region = {}
            for run in runs:
                region = run.get("data", {}).get("tags", {}).get("region", "")
                if not region:
                    continue
                if region in by_region:
                    continue

                metrics = {
                    m["key"]: m["value"]
                    for m in run.get("data", {}).get("metrics", [])
                }
                items = []
                for h in range(1, 25):
                    mae_key = f"mae_h{h:02d}"
                    r2_key = f"r2_h{h:02d}"
                    mae = metrics.get(mae_key)
                    r2 = metrics.get(r2_key)
                    if mae is not None or r2 is not None:
                        items.append({
                            "region": region,
                            "horizon": h,
                            "mape": None,
                            "mae": round(mae, 2) if mae is not None else None,
                            "r2": round(r2, 4) if r2 is not None else None,
                            "source": "training",
                        })
                if items:
                    by_region[region] = items

            all_items = []
            for items in by_region.values():
                all_items.extend(items)
            all_items.sort(key=lambda x: (x["region"], x["horizon"]))

            return {"regions": by_region, "items": all_items, "source": "training"}

    except Exception:
        return {"regions": {}, "items": [], "source": "training"}


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


@router.get("/resources")
async def get_resources():
    """Get current system resource usage from psutil (host-level)."""
    try:
        if _HAS_PSUTIL:
            cpu = psutil.cpu_percent(interval=None)
            mem = psutil.virtual_memory().percent
            disk = shutil.disk_usage("/")
            disk_pct = (disk.used / disk.total) * 100
        else:
            cpu = 0.0
            mem = 0.0
            disk_pct = 0.0
    except Exception:
        cpu = 0.0
        mem = 0.0
        disk_pct = 0.0

    return {
        "cpu": round(cpu, 1),
        "memory": round(mem, 1),
        "disk": round(disk_pct, 1),
        "thresholds": {
            "cpu": 90,
            "memory": 80,
            "disk": 80,
        },
    }
