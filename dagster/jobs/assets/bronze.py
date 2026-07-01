import logging
import sys

sys.path.insert(0, "/opt/dagster/dlt")

from dagster import AssetExecutionContext, StaticPartitionsDefinition, asset

from pipelines.demand_aemo import run_demand_pipeline
from pipelines.weather_openmeteo import run_weather_pipeline

partitions = StaticPartitionsDefinition(["2024", "2025", "2026"])


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


@asset(
    key_prefix=["bronze"],
    description="OpenElectricity 5-min demand → bronze.demand",
    group_name="bronze",
    partitions_def=partitions,
)
def demand(context: AssetExecutionContext) -> None:
    year = int(context.partition_key)

    handler = DagsterLogHandler(context.log)
    handler.setLevel(logging.INFO)
    handler.setFormatter(logging.Formatter("%(name)s: %(message)s"))

    loggers = [
        logging.getLogger("pipelines.demand_aemo"),
        logging.getLogger("utils.openelectricity"),
    ]
    for lg in loggers:
        lg.addHandler(handler)
        lg.setLevel(logging.INFO)

    try:
        context.log.info("Starting OpenElectricity demand load for year %d", year)
        run_demand_pipeline(year)
        context.log.info("OpenElectricity demand load complete for year %d", year)
    finally:
        for lg in loggers:
            lg.removeHandler(handler)


@asset(
    key_prefix=["bronze"],
    description="OpenMeteo hourly weather → bronze.weather",
    group_name="bronze",
    partitions_def=partitions,
)
def weather(context: AssetExecutionContext) -> None:
    year = int(context.partition_key)

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
