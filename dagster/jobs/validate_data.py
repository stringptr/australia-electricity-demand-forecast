import sys

sys.path.insert(0, "/opt/dagster/app")
sys.path.insert(0, "/opt/dagster/dlt")

from dagster import job, op

from shared.alerts import send_alert

from gx_quality.context import get_context
from gx_quality.setup_expectations import CHECKPOINT_GROUPS
from gx_quality.setup_expectations import setup_all as gx_setup_all


def _run_cp(context, cp_name):
    gx = get_context()
    try:
        cp = gx.checkpoints.get(cp_name)
    except Exception:
        gx_setup_all()
        cp = gx.checkpoints.get(cp_name)

    result = cp.run()
    stats = result.to_json_dict().get("statistics", {})
    passed = result.success
    total = stats.get("evaluated_expectations", 0)
    success = stats.get("successful_expectations", 0)
    failed = stats.get("unsuccessful_expectations", 0)

    if passed:
        context.log.info(
            "GX %s PASS — %d/%d expectations met", cp_name, success, total
        )
    else:
        context.log.warning(
            "GX %s FAIL — %d/%d expectations met (%d failures)",
            cp_name,
            success,
            total,
            failed,
        )
        send_alert(
            f"GX checkpoint *{cp_name}* FAILED\n"
            f"Expectations: {success}/{total} passed\n"
            f"Failures: *{failed}*",
            level="WARNING",
            throttle_key=f"gx_{cp_name}",
            throttle_seconds=600,
        )

    context.add_output_metadata(
        {
            "gx_checkpoint": cp_name,
            "gx_passed": passed,
            "gx_expectations_total": total,
            "gx_expectations_success": success,
            "gx_expectations_failed": failed,
        }
    )


@op(description="Validate bronze.demand and bronze.weather")
def validate_bronze(context):
    _run_cp(context, "bronze_validation")


@op(description="Validate silver.demand_5min and silver.weather_hourly")
def validate_silver(context):
    _run_cp(context, "silver_validation")


@op(description="Validate silver.features_ml")
def validate_features(context):
    _run_cp(context, "features_validation")


@op(description="Validate silver.predictions")
def validate_predictions(context):
    _run_cp(context, "predictions_validation")


@op(description="Run all GX validation checkpoints")
def validate_all(context):
    for cp_name in CHECKPOINT_GROUPS:
        _run_cp(context, cp_name)


@job(description="Great Expectations data validation across all tables")
def validate_data():
    validate_bronze()
    validate_silver()
    validate_features()
    validate_predictions()
