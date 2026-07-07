from fastapi import APIRouter
import asyncio
import httpx
import shutil
import time
from datetime import timedelta

from core.config import settings
from core.db import fetch, fetchval

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

SERVICE_CHECK_MAP = {
    "PostgreSQL":       ("tcp",  "postgres", 5432),
    "NATS":             ("http", "http://nats:8222/healthz"),
    "Debezium":         ("http", "http://debezium-server:8080/q/health/ready"),
    "VictoriaMetrics":  ("http", "http://victoriametrics:8428/-/healthy"),
    "VictoriaLogs":     ("http", "http://victorialogs:9428/health"),
    "Dagster":          ("http", "http://dagster-webserver:3000/dagit_info"),
    "MLflow":           ("http", "http://mlflow:5000/health"),
    "Inference":        ("vm", "inference_cycle_completed_total"),
    "Garage":           ("http", "http://garage:3902/health"),
    "Dashboard Backend": ("self",),
}


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


async def _check_service_direct(svc: str) -> bool:
    try:
        entry = SERVICE_CHECK_MAP.get(svc)
        if not entry:
            return False
        method = entry[0]
        if method == "self":
            return True
        if method == "tcp":
            _, host, port = entry
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(host, port), timeout=3.0
            )
            writer.close()
            await writer.wait_closed()
            return True
        if method == "http":
            url = entry[1]
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(url)
                return 200 <= resp.status_code < 400
        if method == "vm":
            results = await _vm_query(entry[1])
            if results:
                ts = float(results[0]["value"][0])
                return (time.time() - ts) < 120
            return False
    except Exception:
        return False


async def _compute_mape_from_db(region_id: str | None = None) -> dict:
    """Compute real-time MAPE directly from DB when VM has no data."""
    try:
        pred_rows = await fetch(
            """
            SELECT p.region_id, p.created_at,
                   p.horizon_h01, p.horizon_h02, p.horizon_h03, p.horizon_h04,
                   p.horizon_h05, p.horizon_h06, p.horizon_h07, p.horizon_h08,
                   p.horizon_h09, p.horizon_h10, p.horizon_h11, p.horizon_h12,
                   p.horizon_h13, p.horizon_h14, p.horizon_h15, p.horizon_h16,
                   p.horizon_h17, p.horizon_h18, p.horizon_h19, p.horizon_h20,
                   p.horizon_h21, p.horizon_h22, p.horizon_h23, p.horizon_h24
            FROM silver.predictions p
            WHERE p.created_at >= NOW() - INTERVAL '48 hours'
              AND p.created_at < NOW() - INTERVAL '24 hours'
            ORDER BY p.created_at DESC
            LIMIT 50
            """
        )
        if not pred_rows:
            return {"regions": {}, "items": [], "source": "realtime"}

        from collections import defaultdict
        regions_map: dict = defaultdict(list)

        for row in pred_rows:
            rid = row["region_id"]
            if region_id and rid != region_id:
                continue
            created_at = row["created_at"]
            horizons = [row[f"horizon_h{h:02d}"] for h in range(1, 25)]

            for h_idx, predicted in enumerate(horizons):
                if predicted is None or predicted <= 0:
                    continue
                h = h_idx + 1
                expected_time = created_at + timedelta(hours=h)

                actual_val = await fetchval(
                    "SELECT demand_mw FROM silver.features_ml "
                    "WHERE region_id = $1 AND time = $2",
                    rid, expected_time,
                )
                if actual_val and actual_val > 0:
                    mape = abs((float(actual_val) - float(predicted)) / float(actual_val)) * 100
                    regions_map[(rid, h)].append(mape)

        items = []
        for (rid, horizon), mapes in regions_map.items():
            avg_mape = sum(mapes) / len(mapes)
            items.append({
                "region": rid,
                "horizon": horizon,
                "mape": round(avg_mape, 2),
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
    except Exception:
        return {"regions": {}, "items": [], "source": "realtime"}


async def _compute_latency_from_db() -> float:
    try:
        val = await fetchval(
            """
            SELECT COALESCE(
              MAX(ABS(EXTRACT(EPOCH FROM (updated_at - time)))),
              0
            )
            FROM silver.demand_5min
            WHERE updated_at > NOW() - INTERVAL '5 minutes'
            """
        )
        return round(float(val), 2) if val is not None else 0.0
    except Exception:
        return 0.0


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

    if not items:
        return await _compute_mape_from_db(region_id)

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
                params={"max_results": "50"},
            )
            if exp_resp.status_code != 200:
                return {"regions": {}, "items": [], "source": "training"}

            experiments = exp_resp.json().get("experiments", [])
            if not experiments:
                return {"regions": {}, "items": [], "source": "training"}

            exp_id = None
            for exp in experiments:
                if exp.get("name") == "demand-forecasting":
                    exp_id = exp["experiment_id"]
                    break
            if not exp_id:
                return {"regions": {}, "items": [], "source": "training"}

            by_region = {}
            for rid in REGIONS:
                if region_id and rid != region_id:
                    continue

                runs_resp = await client.post(
                    f"{settings.MLFLOW_URL}/api/2.0/mlflow/runs/search",
                    json={
                        "experiment_ids": [exp_id],
                        "filter": f"tags.region = '{rid}'",
                        "order_by": ["start_time DESC"],
                        "max_results": 1,
                    },
                )
                if runs_resp.status_code != 200:
                    continue

                runs = runs_resp.json().get("runs", [])
                if not runs:
                    continue

                run = runs[0]
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
                            "region": rid,
                            "horizon": h,
                            "mape": None,
                            "mae": round(mae, 2) if mae is not None else None,
                            "r2": round(r2, 4) if r2 is not None else None,
                            "source": "training",
                        })
                if items:
                    by_region[rid] = items

            all_items = []
            for items in by_region.values():
                all_items.extend(items)
            all_items.sort(key=lambda x: (x["region"], x["horizon"]))

            return {"regions": by_region, "items": all_items, "source": "training"}

    except Exception:
        return {"regions": {}, "items": [], "source": "training"}


@router.get("/uptime")
async def get_uptime():
    """Get service uptime percentage over 24h and 7d with direct-check fallback."""
    services = []
    for svc in SERVICES:
        query_24h = f'avg_over_time(service_up{{service="{svc}"}}[24h]) * 100'
        query_7d = f'avg_over_time(service_up{{service="{svc}"}}[7d]) * 100'
        query_now = f'service_up{{service="{svc}"}}'

        results_24h = await _vm_query(query_24h)
        results_7d = await _vm_query(query_7d)
        results_now = await _vm_query(query_now)

        if results_24h:
            uptime_24h = round(float(results_24h[0]["value"][1]), 1)
        else:
            results_1h = await _vm_query(
                f'avg_over_time(service_up{{service="{svc}"}}[1h]) * 100'
            )
            if results_1h:
                uptime_24h = round(float(results_1h[0]["value"][1]), 1)
            else:
                results_10m = await _vm_query(
                    f'avg_over_time(service_up{{service="{svc}"}}[10m]) * 100'
                )
                if results_10m:
                    uptime_24h = round(float(results_10m[0]["value"][1]), 1)
                else:
                    uptime_24h = None

        if results_7d:
            uptime_7d = round(float(results_7d[0]["value"][1]), 1)
        elif results_24h:
            uptime_7d = round(float(results_24h[0]["value"][1]), 1)
        else:
            results_1h = await _vm_query(
                f'avg_over_time(service_up{{service="{svc}"}}[1h]) * 100'
            )
            if results_1h:
                uptime_7d = round(float(results_1h[0]["value"][1]), 1)
            else:
                uptime_7d = None

        if results_now and float(results_now[0]["value"][1]) == 1:
            status = "up"
        elif results_now:
            status = "down"
        else:
            status = "up" if await _check_service_direct(svc) else "down"

        services.append({
            "name": svc,
            "status": status,
            "uptime_24h": uptime_24h,
            "uptime_7d": uptime_7d,
        })

    return {"services": services}


@router.get("/latency")
async def get_latency():
    """Get current pipeline latency and trend over 24h with DB fallback."""
    latest_results = await _vm_query("pipeline_latency_seconds")
    latest = round(float(latest_results[0]["value"][1]), 2) if latest_results else None

    if latest is None:
        latest = await _compute_latency_from_db()

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
            cpu = psutil.cpu_percent(interval=0.1)
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
