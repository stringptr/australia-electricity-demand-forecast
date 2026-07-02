import logging
import os
import sys

sys.path.insert(0, "/opt/dagster/app")
sys.path.insert(0, "/opt/dagster/dlt")

from dagster import AssetCheckResult, AssetCheckSeverity, Definitions, asset_check
from dagster_dbt import DbtCliResource

from jobs.assets.bronze import demand as bronze_demand
from jobs.assets.bronze import weather as bronze_weather
from jobs.assets.silver import dbt_silver_assets
from jobs.assets.gold import correlation_hourly as gold_correlation_hourly
from jobs.assets.gold import correlation_daily as gold_correlation_daily
from jobs.assets.ml import xgboost_models

from jobs.historical_load import historical_backfill
from jobs.train_model import train_multi_output_xgboost
from jobs.validate_data import validate_data
from jobs.gold_correlation import build_gold_correlation

from hooks import alert_on_failure

from resources.postgres_io_manager import PostgresIOManager

DBT_PROJECT_DIR = os.environ.get("DBT_PROJECT_DIR", "/opt/dagster/dbt")
DBT_PROFILES_DIR = os.environ.get("DBT_PROFILES_DIR", "/opt/dagster/dbt")

_GX_AVAILABLE = True
try:
    from gx_quality.context import get_context
    from gx_quality.setup_expectations import CHECKPOINT_GROUPS
    from gx_quality.setup_expectations import setup_all as gx_setup_all
except Exception:
    _GX_AVAILABLE = False
    logging.getLogger(__name__).warning(
        "Great Expectations not available, asset checks will be skipped"
    )


def _run_gx_checkpoint(context, cp_name: str) -> AssetCheckResult:
    gx = get_context()
    try:
        cp = gx.checkpoints.get(cp_name)
    except Exception:
        gx_setup_all()
        cp = gx.checkpoints.get(cp_name)

    result = cp.run()
    passed = result.success
    total = 0
    success = 0
    failed = 0
    for vr in result.run_results.values():
        s = vr.statistics
        total += s.get("evaluated_expectations", 0)
        success += s.get("successful_expectations", 0)
        failed += s.get("unsuccessful_expectations", 0)

    if not passed:
        from shared.alerts import send_alert
        send_alert(
            f"GX asset check *{cp_name}* FAILED\n"
            f"Expectations: {success}/{total} passed\n"
            f"Failures: *{failed}*",
            level="WARNING",
            throttle_key=f"gx_asset_{cp_name}",
            throttle_seconds=600,
        )

    return AssetCheckResult(
        passed=passed,
        severity=AssetCheckSeverity.ERROR,
        metadata={
            "checkpoint": cp_name,
            "expectations_total": total,
            "expectations_success": success,
            "expectations_failed": failed,
        },
    )


if _GX_AVAILABLE:

    @asset_check(
        asset=["bronze", "demand"],
        description="GX validation: bronze.demand and bronze.weather",
    )
    def bronze_validation_check(context):
        return _run_gx_checkpoint(context, "bronze_validation")

    @asset_check(
        asset=["silver", "demand_5min"],
        description="GX validation: silver.demand_5min and silver.weather_hourly",
    )
    def silver_validation_check(context):
        return _run_gx_checkpoint(context, "silver_validation")

    @asset_check(
        asset=["silver", "features_ml"],
        description="GX validation: silver.features_ml",
    )
    def features_validation_check(context):
        return _run_gx_checkpoint(context, "features_validation")

    @asset_check(
        asset=["silver", "predictions"],
        description="GX validation: silver.predictions",
    )
    def predictions_validation_check(context):
        return _run_gx_checkpoint(context, "predictions_validation")

    asset_checks = [
        bronze_validation_check,
        silver_validation_check,
        features_validation_check,
        predictions_validation_check,
    ]
else:
    asset_checks = []


defs = Definitions(
    assets=[
        bronze_demand,
        bronze_weather,
        dbt_silver_assets,
        gold_correlation_hourly,
        gold_correlation_daily,
        xgboost_models,
    ],
    asset_checks=asset_checks,
    resources={
        "postgres_io_manager": PostgresIOManager(),
        "dbt": DbtCliResource(
            project_dir=DBT_PROJECT_DIR,
            profiles_dir=DBT_PROFILES_DIR,
            global_config_flags=["--no-use-colors"],
        ),
    },
    jobs=[
        historical_backfill.with_hooks({alert_on_failure}),
        train_multi_output_xgboost.with_hooks({alert_on_failure}),
        validate_data.with_hooks({alert_on_failure}),
        build_gold_correlation.with_hooks({alert_on_failure}),
    ],
)
