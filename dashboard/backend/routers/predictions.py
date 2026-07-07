from datetime import timedelta

import httpx
from fastapi import APIRouter, HTTPException

from core.config import settings
from core.db import fetchrow, fetch

router = APIRouter(prefix="/predictions", tags=["predictions"])


@router.get("/latest")
async def get_latest_predictions(region_id: str):
    """Get latest 24h prediction for a region."""
    row = await fetchrow(
        """
        SELECT created_at, 
            horizon_h01, horizon_h02, horizon_h03, horizon_h04,
            horizon_h05, horizon_h06, horizon_h07, horizon_h08,
            horizon_h09, horizon_h10, horizon_h11, horizon_h12,
            horizon_h13, horizon_h14, horizon_h15, horizon_h16,
            horizon_h17, horizon_h18, horizon_h19, horizon_h20,
            horizon_h21, horizon_h22, horizon_h23, horizon_h24
        FROM silver.predictions
        WHERE region_id = $1
        ORDER BY created_at DESC
        LIMIT 1
        """,
        region_id
    )

    if not row:
        raise HTTPException(status_code=404, detail="No predictions found")

    predictions = []
    for i in range(1, 25):
        val = row[f"horizon_h{i:02d}"]
        predictions.append(float(val) if val is not None else None)

    return {
        "region_id": region_id,
        "created_at": row["created_at"].isoformat(),
        "predictions": predictions
    }


async def _vm_query_accuracy(region_id: str) -> list:
    """Query VictoriaMetrics for prediction_mape and return accuracy items."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(
                f"{settings.VM_URL}/api/v1/query",
                params={"query": f'prediction_mape{{region="{region_id}"}}'},
            )
            if resp.status_code == 200:
                data = resp.json()
                results = data.get("data", {}).get("result", [])
                items = []
                for r in results:
                    horizon = int(r.get("metric", {}).get("horizon", 0))
                    value = float(r["value"][1])
                    items.append({"horizon": horizon, "mape": round(value, 2)})
                items.sort(key=lambda x: x["horizon"])
                return items
    except Exception:
        pass
    return []


async def _compute_mape_batch_for_region(region_id: str) -> list:
    """Batch-compute MAPE from DB (same as monitoring's _compute_mape_from_db)."""
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
            WHERE p.region_id = $1
              AND p.created_at >= NOW() - INTERVAL '48 hours'
              AND p.created_at < NOW() - INTERVAL '24 hours'
            ORDER BY p.created_at DESC
            LIMIT 50
            """,
            region_id,
        )
        if not pred_rows:
            return []

        from collections import defaultdict
        regions_map: dict = defaultdict(list)

        for row in pred_rows:
            created_at = row["created_at"]
            horizons = [row[f"horizon_h{h:02d}"] for h in range(1, 25)]

            for h_idx, predicted in enumerate(horizons):
                if predicted is None or predicted <= 0:
                    continue
                h = h_idx + 1
                expected_time = created_at + timedelta(hours=h)

                actual_val = await fetchrow(
                    "SELECT demand_mw FROM silver.features_ml "
                    "WHERE region_id = $1 AND time = $2",
                    region_id, expected_time,
                )
                if actual_val and actual_val["demand_mw"] and actual_val["demand_mw"] > 0:
                    mape = abs((float(actual_val["demand_mw"]) - float(predicted))
                               / float(actual_val["demand_mw"])) * 100
                    regions_map[h].append(mape)

        items = []
        for horizon, mapes in regions_map.items():
            avg_mape = sum(mapes) / len(mapes)
            items.append({"horizon": horizon, "mape": round(avg_mape, 2)})
        items.sort(key=lambda x: x["horizon"])
        return items
    except Exception:
        return []


@router.get("/accuracy")
async def get_prediction_accuracy(region_id: str, source: str = "realtime"):
    """Get per-horizon accuracy for a region.

    Args:
        region_id: region filter (required)
        source: 'realtime' (VM → DB fallback) or 'training' (MLflow metrics)
    """
    if source == "training":
        return await _get_training_accuracy_for_region(region_id)

    vm_items = await _vm_query_accuracy(region_id)
    if vm_items:
        return {
            "region_id": region_id,
            "source": "realtime",
            "accuracy": vm_items,
        }

    batch_items = await _compute_mape_batch_for_region(region_id)
    if batch_items:
        return {
            "region_id": region_id,
            "source": "realtime",
            "accuracy": batch_items,
        }

    row = await fetchrow(
        """
        SELECT created_at,
            horizon_h01, horizon_h02, horizon_h03, horizon_h04,
            horizon_h05, horizon_h06, horizon_h07, horizon_h08,
            horizon_h09, horizon_h10, horizon_h11, horizon_h12,
            horizon_h13, horizon_h14, horizon_h15, horizon_h16,
            horizon_h17, horizon_h18, horizon_h19, horizon_h20,
            horizon_h21, horizon_h22, horizon_h23, horizon_h24
        FROM silver.predictions
        WHERE region_id = $1
        ORDER BY created_at DESC
        LIMIT 1
        """,
        region_id
    )

    if not row:
        return {
            "region_id": region_id,
            "source": "realtime",
            "accuracy": [],
        }

    created_at = row["created_at"]

    horizon_data = []
    for h in range(1, 25):
        pred_val = row[f"horizon_h{h:02d}"]
        if pred_val is None:
            horizon_data.append({"horizon": h, "mape": None})
            continue

        actual_row = await fetchrow(
            """
            SELECT demand_mw FROM silver.features_ml
            WHERE region_id = $1 AND time = $2
            """,
            region_id,
            created_at + timedelta(hours=h)
        )

        if actual_row and actual_row["demand_mw"] and actual_row["demand_mw"] > 0:
            actual = float(actual_row["demand_mw"])
            predicted = float(pred_val)
            mape = abs((actual - predicted) / actual) * 100
            horizon_data.append({"horizon": h, "mape": round(mape, 2)})
        else:
            horizon_data.append({"horizon": h, "mape": None})

    return {
        "region_id": region_id,
        "source": "realtime",
        "accuracy": horizon_data,
    }


async def _get_training_accuracy_for_region(region_id: str) -> dict:
    """Fetch training metrics from MLflow for a specific region."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            exp_resp = await client.get(
                f"{settings.MLFLOW_URL}/api/2.0/mlflow/experiments/search",
                params={"max_results": "50"},
            )
            if exp_resp.status_code != 200:
                return {"region_id": region_id, "source": "training", "accuracy": []}

            experiments = exp_resp.json().get("experiments", [])
            if not experiments:
                return {"region_id": region_id, "source": "training", "accuracy": []}

            exp_id = None
            for exp in experiments:
                if exp.get("name") == "demand-forecasting":
                    exp_id = exp["experiment_id"]
                    break
            if not exp_id:
                return {"region_id": region_id, "source": "training", "accuracy": []}

            runs_resp = await client.post(
                f"{settings.MLFLOW_URL}/api/2.0/mlflow/runs/search",
                json={
                    "experiment_ids": [exp_id],
                    "filter": f"tags.region = '{region_id}'",
                    "order_by": ["start_time DESC"],
                    "max_results": 1,
                },
            )
            if runs_resp.status_code != 200:
                return {"region_id": region_id, "source": "training", "accuracy": []}

            runs = runs_resp.json().get("runs", [])
            if not runs:
                return {"region_id": region_id, "source": "training", "accuracy": []}

            run = runs[0]
            metrics = {
                m["key"]: m["value"]
                for m in run.get("data", {}).get("metrics", [])
            }

            horizon_data = []
            for h in range(1, 25):
                mae_key = f"mae_h{h:02d}"
                r2_key = f"r2_h{h:02d}"
                mae = metrics.get(mae_key)
                r2 = metrics.get(r2_key)
                horizon_data.append({
                    "horizon": h,
                    "mape": None,
                    "mae": round(mae, 2) if mae is not None else None,
                    "r2": round(r2, 4) if r2 is not None else None,
                })

            return {
                "region_id": region_id,
                "source": "training",
                "accuracy": horizon_data,
            }

    except Exception:
        return {"region_id": region_id, "source": "training", "accuracy": []}
