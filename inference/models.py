import logging
import os

import mlflow
from xgboost import XGBRegressor

from .config import MLFLOW_TRACKING_URI, REGIONS

logger = logging.getLogger(__name__)


def load_models() -> dict[str, XGBRegressor]:
    os.environ.setdefault("MLFLOW_S3_ENDPOINT_URL", "http://garage:3900")
    os.environ.setdefault("AWS_ACCESS_KEY_ID", "mlflow-key-id")
    os.environ.setdefault("AWS_SECRET_ACCESS_KEY", "mlflow-secret-key")
    os.environ.setdefault("AWS_DEFAULT_REGION", "us-east-1")
    os.environ.setdefault("AWS_S3_FORCE_PATH_STYLE", "true")

    mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)

    models = {}
    for region in REGIONS:
        model_uri = f"models:/xgb_multi_{region}/latest"
        logger.info("Loading model: %s", model_uri)
        models[region] = mlflow.xgboost.load_model(model_uri)
        logger.info("Loaded %s: %s estimators, %s features",
                     region, models[region].n_estimators, models[region].n_features_in_)

    return models
