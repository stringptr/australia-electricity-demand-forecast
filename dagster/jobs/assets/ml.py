import os
import time
from datetime import datetime

import numpy as np
import pandas as pd
from dagster import AssetExecutionContext, AssetKey, asset
from sqlalchemy import create_engine, text
from sklearn.metrics import mean_absolute_error, r2_score
from xgboost import XGBRegressor

import mlflow
import mlflow.xgboost

from jobs.preprocessing import (
    MAX_HORIZON,
    REGIONS,
    STATIC_FEATS,
    build_long_format,
    pivot_to_wide,
)

XGB_PARAMS = {
    "n_estimators": 200,
    "max_depth": 5,
    "learning_rate": 0.05,
    "subsample": 0.8,
    "colsample_bytree": 0.8,
    "min_child_weight": 5,
    "reg_alpha": 0.1,
    "reg_lambda": 1.0,
    "multi_strategy": "multi_output_tree",
    "random_state": 911,
    "n_jobs": -1,
    "verbosity": 0,
}

MLFLOW_TRACKING_URI = os.environ.get("MLFLOW_TRACKING_URI", "http://mlflow:5000")
MLFLOW_EXPERIMENT = "demand-forecasting"

TRAIN_END = pd.Timestamp("2026-03-01", tz="UTC")
VAL_END = pd.Timestamp("2026-05-01", tz="UTC")


def _get_db_engine():
    host = os.environ.get("PG_HOST", os.environ.get("POSTGRES_HOST", "postgres"))
    port = os.environ.get("PG_PORT", os.environ.get("POSTGRES_PORT", "5432"))
    user = os.environ.get("PG_USER", os.environ.get("POSTGRES_USER", "postgres"))
    password = os.environ.get("PG_PASSWORD", os.environ.get("POSTGRES_PASSWORD", "postgres"))
    db = os.environ.get("PG_DB", os.environ.get("POSTGRES_DB", "electricity"))
    return create_engine(f"postgresql://{user}:{password}@{host}:{port}/{db}")


def _configure_mlflow():
    mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
    os.environ.setdefault("MLFLOW_S3_ENDPOINT_URL", "http://garage:3900")
    os.environ.setdefault("AWS_ACCESS_KEY_ID", "mlflow-key-id")
    os.environ.setdefault("AWS_SECRET_ACCESS_KEY", "mlflow-secret-key")
    os.environ.setdefault("AWS_DEFAULT_REGION", "us-east-1")
    os.environ.setdefault("AWS_S3_FORCE_PATH_STYLE", "true")
    mlflow.set_experiment(MLFLOW_EXPERIMENT)


@asset(
    group_name="ml",
    deps=[AssetKey(["silver", "features_ml"])],
    description="Train 5 multi-output XGBoost models (one per region) with MLflow tracking",
)
def xgboost_models(context: AssetExecutionContext) -> dict:
    engine = _get_db_engine()

    query = text(
        "SELECT time, region_id, demand_mw, temperature_2m, "
        "relative_humidity_2m, precipitation, cloud_cover, "
        "wind_speed_10m, shortwave_radiation, hour, day_of_week, "
        "is_weekend, month "
        "FROM silver.features_ml "
        "WHERE time < :end_date "
        "ORDER BY region_id, time"
    )
    with engine.connect() as conn:
        df = pd.read_sql_query(
            query,
            conn,
            params={"end_date": VAL_END + pd.Timedelta(days=90)},
            parse_dates=["time"],
        )

    context.log.info(
        f"Loaded {len(df):,} rows | "
        f"regions: {sorted(df['region_id'].unique().tolist())} | "
        f"period: {df['time'].min()} -> {df['time'].max()}"
    )

    t0 = time.time()
    context.log.info("Building long-format multi-horizon dataset ...")
    df_long = build_long_format(df)
    context.log.info(f"Long format: {len(df_long):,} rows ({time.time() - t0:.0f}s)")

    t0 = time.time()
    context.log.info("Pivoting to wide format ...")
    df_wide, target_cols, feature_cols = pivot_to_wide(df_long)
    context.log.info(
        f"Wide format: {len(df_wide):,} rows, "
        f"{len(feature_cols)} features ({time.time() - t0:.0f}s)"
    )

    df_train = df_wide[df_wide["time"] < TRAIN_END]
    df_val = df_wide[(df_wide["time"] >= TRAIN_END) & (df_wide["time"] < VAL_END)]
    df_test = df_wide[df_wide["time"] >= VAL_END]

    context.log.info(
        f"Split: train={len(df_train):,}  val={len(df_val):,}  test={len(df_test):,}"
    )

    _configure_mlflow()

    run_name = f"multi_output_{datetime.utcnow().strftime('%Y%m%d_%H%M')}"
    context.log.info(f"MLflow run: {run_name}")

    all_regions_r2 = {}
    all_regions_mae = {}

    with mlflow.start_run(run_name=run_name) as parent_run:
        mlflow.log_params({f"xgb_{k}": v for k, v in XGB_PARAMS.items()})
        mlflow.log_params(
            {
                "n_horizons": MAX_HORIZON,
                "n_features": len(feature_cols),
                "n_static_features": len(STATIC_FEATS),
                "train_end": str(TRAIN_END),
                "val_end": str(VAL_END),
            }
        )
        mlflow.set_tags(
            {
                "data_source": "silver.features_ml",
                "n_train_rows": str(len(df_train)),
                "n_val_rows": str(len(df_val)),
                "n_test_rows": str(len(df_test)),
            }
        )

        for region_id in REGIONS:
            context.log.info(f"{region_id}: training multi-output XGBoost ...")
            t0 = time.time()

            tr = pd.concat(
                [
                    df_train[df_train["region_id"] == region_id],
                    df_val[df_val["region_id"] == region_id],
                ]
            )
            ts = df_test[df_test["region_id"] == region_id]

            X_tr = tr[feature_cols].values.astype(np.float32)
            y_tr = tr[target_cols].values.astype(np.float32)
            X_ts = ts[feature_cols].values.astype(np.float32)
            y_ts = ts[target_cols].values.astype(np.float32)

            with mlflow.start_run(run_name=region_id, nested=True) as child_run:
                mlflow.set_tag("region", region_id)
                mlflow.set_tags(
                    {"n_train_rows": str(len(tr)), "n_test_rows": str(len(ts))}
                )

                model = XGBRegressor(**XGB_PARAMS)
                model.fit(X_tr, y_tr, verbose=False)

                y_pred = model.predict(X_ts)

                if y_pred.ndim == 1:
                    context.log.warning(
                        f"{region_id}: y_pred is 1D (shape {y_pred.shape}), "
                        f"expected ({len(X_ts)}, {MAX_HORIZON})"
                    )
                    y_pred = np.column_stack([y_pred] * MAX_HORIZON)

                per_horizon_r2 = {}
                per_horizon_mae = {}
                for h_idx, h in enumerate(range(1, MAX_HORIZON + 1)):
                    yt = y_ts[:, h_idx]
                    yp = y_pred[:, h_idx]
                    per_horizon_r2[h] = float(r2_score(yt, yp))
                    per_horizon_mae[h] = float(mean_absolute_error(yt, yp))

                avg_r2 = np.mean(list(per_horizon_r2.values()))
                avg_mae = np.mean(list(per_horizon_mae.values()))

                mlflow.log_metric("avg_r2", avg_r2)
                mlflow.log_metric("avg_mae", avg_mae)

                for h in range(1, MAX_HORIZON + 1):
                    mlflow.log_metric(f"r2_h{h:02d}", per_horizon_r2[h])
                    mlflow.log_metric(f"mae_h{h:02d}", per_horizon_mae[h])

                mlflow.xgboost.log_model(
                    model,
                    artifact_path="model",
                    registered_model_name=f"xgb_multi_{region_id}",
                )

                all_regions_r2[region_id] = avg_r2
                all_regions_mae[region_id] = avg_mae

                context.log.info(
                    f"  avg R2={avg_r2:.3f}  avg MAE={avg_mae:.0f} MW  "
                    f"({time.time() - t0:.0f}s)"
                )

        overall_avg_r2 = np.mean(list(all_regions_r2.values()))
        mlflow.log_metric("overall_avg_r2", overall_avg_r2)

        context.log.info(f"Overall avg R2: {overall_avg_r2:.3f}")
        context.log.info(f"MLflow run ID: {parent_run.info.run_id}")

        context.add_output_metadata(
            {
                "mlflow_run_id": parent_run.info.run_id,
                "overall_avg_r2": overall_avg_r2,
                "regions": list(all_regions_r2.keys()),
            }
        )

    return {"run_id": parent_run.info.run_id, "overall_avg_r2": overall_avg_r2}
