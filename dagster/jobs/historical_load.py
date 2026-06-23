import logging
import subprocess
import sys

sys.path.insert(0, "/opt/dagster/dlt")

from dagster import StaticPartitionsDefinition, in_process_executor, job, op


class DagsterLogHandler(logging.Handler):
    """Forward Python logging records to Dagster context.log."""

    def __init__(self, dagster_log):
        super().__init__()
        self._dagster_log = dagster_log

    def emit(self, record: logging.LogRecord) -> None:
        try:
            msg = self.format(record)
            if record.levelno >= logging.ERROR:
                self._dagster_log.error(msg)
            elif record.levelno >= logging.WARNING:
                self._dagster_log.warning(msg)
            elif record.levelno >= logging.INFO:
                self._dagster_log.info(msg)
            else:
                self._dagster_log.debug(msg)
        except Exception:
            self.handleError(record)


partitions = StaticPartitionsDefinition(["2026"])


@op
def load_demand_op(context) -> None:
    year = int(context.partition_key)
    from pipelines.demand_aemo import run_demand_pipeline

    handler = DagsterLogHandler(context.log)
    handler.setLevel(logging.INFO)
    handler.setFormatter(logging.Formatter("%(name)s: %(message)s"))

    loggers = [
        logging.getLogger("pipelines.demand_aemo"),
        logging.getLogger("utils.aemo"),
    ]
    for lg in loggers:
        lg.addHandler(handler)
        lg.setLevel(logging.INFO)

    try:
        context.log.info("Starting AEMO demand load for year %d", year)
        run_demand_pipeline(year)
        context.log.info("AEMO demand load complete for year %d", year)
    finally:
        for lg in loggers:
            lg.removeHandler(handler)


@op
def load_weather_op(context) -> None:
    year = int(context.partition_key)
    from pipelines.weather_openmeteo import run_weather_pipeline

    handler = DagsterLogHandler(context.log)
    handler.setLevel(logging.INFO)
    handler.setFormatter(logging.Formatter("%(name)s: %(message)s"))

    loggers = [
        logging.getLogger("pipelines.weather_openmeteo"),
        logging.getLogger("utils.openmeteo"),
    ]
    for lg in loggers:
        lg.addHandler(handler)
        lg.setLevel(logging.INFO)

    try:
        context.log.info("Starting OpenMeteo weather load for year %d", year)
        run_weather_pipeline(year)
        context.log.info("OpenMeteo weather load complete for year %d", year)
    finally:
        for lg in loggers:
            lg.removeHandler(handler)


@op
def dbt_run_op(context) -> None:
    context.log.info("Running DBT silver models")
    result = subprocess.run(
        ["dbt", "run", "--models", "silver", "--profiles-dir", "/opt/dagster/dbt"],
        cwd="/opt/dagster/dbt",
        capture_output=True,
        text=True,
    )
    if result.stdout:
        context.log.info(result.stdout.strip())
    if result.stderr:
        context.log.error(result.stderr.strip())
    if result.returncode != 0:
        raise Exception(f"dbt run failed with exit code {result.returncode}")
    context.log.info("DBT run complete")


@job(
    partitions_def=partitions,
    executor_def=in_process_executor,
    description="Historical backfill: DLT bronze → DBT silver",
)
def historical_backfill() -> None:
    load_demand_op()
    load_weather_op()
    dbt_run_op()
