import logging
import time as _time
from datetime import datetime, timezone

import pandas as pd
from xgboost import XGBRegressor

from . import metrics
from .config import HISTORY_LOOKBACK_HOURS, REGIONS
from .features import assemble_feature_matrix
from .forecast import fetch_forecast_all_regions
from .store import fetch_demand_history, store_predictions

logger = logging.getLogger(__name__)


def run_inference_cycle(
    models: dict[str, XGBRegressor], trigger_time: datetime
) -> None:
    t0 = _time.perf_counter()

    if trigger_time.tzinfo is None:
        trigger_time = trigger_time.replace(tzinfo=timezone.utc)

    current_time = pd.Timestamp(trigger_time)

    logger.info("=== Inference cycle: %s ===", current_time)

    history = fetch_demand_history(current_time, HISTORY_LOOKBACK_HOURS)
    if history.empty:
        logger.warning("No demand history available, skipping")
        metrics.push("inference_skipped_total", 1.0, {"reason": "no_history"})
        return

    forecast_df = fetch_forecast_all_regions()
    if forecast_df.empty:
        logger.warning("No forecast available, skipping")
        metrics.push("inference_skipped_total", 1.0, {"reason": "no_forecast"})
        return

    X = assemble_feature_matrix(history, forecast_df, current_time)
    logger.info("Feature matrix: %s", X.shape)

    predictions = {}
    for idx, region_id in enumerate(REGIONS):
        model = models.get(region_id)
        if model is None:
            logger.warning("Model not loaded for %s", region_id)
            metrics.push("inference_skipped_total", 1.0, {"reason": "no_model", "region": region_id})
            continue

        pred = model.predict(X[idx : idx + 1])[0]
        predictions[region_id] = pred.tolist()
        logger.info("  %s: %s...%s MW", region_id,
                     ", ".join(f"{v:.0f}" for v in pred[:3]),
                     ", ".join(f"{v:.0f}" for v in pred[-2:]))

    store_predictions(predictions, current_time)

    elapsed = _time.perf_counter() - t0
    metrics.push("inference_latency_seconds", elapsed)
    metrics.push("inference_cycle_completed_total", 1.0)

    logger.info("=== Inference done in %.2fs ===", elapsed)
