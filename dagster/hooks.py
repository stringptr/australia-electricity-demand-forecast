import sys

sys.path.insert(0, "/opt/dagster/app")
sys.path.insert(0, "/opt/dagster/dlt")

from dagster import HookContext, hook

from shared.alerts import send_alert


@hook
def alert_on_failure(context: HookContext):
    send_alert(
        f"Dagster job *{context.job_name}* FAILED\n"
        f"Run ID: `{context.run_id}`\n"
        f"Error: `{context.op_exception}`",
        level="CRITICAL",
        throttle_key=f"dagster_{context.job_name}",
        throttle_seconds=300,
    )


@hook
def alert_on_success(context: HookContext):
    send_alert(
        f"Dagster job *{context.job_name}* completed successfully\n"
        f"Run ID: `{context.run_id}`",
        level="INFO",
        throttle_key=f"dagster_success_{context.job_name}",
        throttle_seconds=600,
    )
