import logging
import os

import mlflow
from mlflow.exceptions import RestException
from xgboost import XGBRegressor

from shared.alerts import send_alert
from shared.retry import retry

from .config import MLFLOW_TRACKING_URI, REGIONS

logger = logging.getLogger(__name__)

_RETRYABLE = (RestException, ConnectionError, OSError)


def load_models() -> dict[str, XGBRegressor]:
    os.environ.setdefault("MLFLOW_S3_ENDPOINT_URL", "http://garage:3900")
    os.environ.setdefault("AWS_ACCESS_KEY_ID", "mlflow-key-id")
    os.environ.setdefault("AWS_SECRET_ACCESS_KEY", "mlflow-secret-key")
    os.environ.setdefault("AWS_DEFAULT_REGION", "us-east-1")
    os.environ.setdefault("AWS_S3_FORCE_PATH_STYLE", "true")

    mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)

    models = {}
    failed_regions = []
    for region in REGIONS:
        model_uri = f"models:/xgb_multi_{region}/latest"
        logger.info("Loading model: %s", model_uri)
        try:
            models[region] = retry(
                lambda: mlflow.xgboost.load_model(model_uri),
                max_retries=None,
                delay=2,
                exceptions=_RETRYABLE,
            )()
            logger.info(
                "Loaded %s: %s estimators, %s features",
                region,
                models[region].n_estimators,
                models[region].n_features_in_,
            )
        except Exception as e:
            logger.exception("Failed to load model for %s after retries", region)
            failed_regions.append(region)

    if failed_regions:
        send_alert(
            f"Model loading failed for regions: *{', '.join(failed_regions)}*",
            level="CRITICAL",
            throttle_key="model_load_fail",
        )

    return models
