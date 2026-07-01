import sys

sys.path.insert(0, "/opt/dagster/dlt")

from dagster import AssetExecutionContext, asset

from pipelines.demand_aemo import run_demand_pipeline
from pipelines.weather_openmeteo import run_weather_pipeline


@asset(
    key_prefix=["bronze"],
    description="OpenElectricity 5-min demand → bronze.demand",
    group_name="bronze",
)
def demand(context: AssetExecutionContext) -> None:
    year = int(context.partition_key)
    context.log.info("Loading OpenElectricity demand data for year %d", year)
    run_demand_pipeline(year)


@asset(
    key_prefix=["bronze"],
    description="OpenMeteo hourly weather → bronze.weather",
    group_name="bronze",
)
def weather(context: AssetExecutionContext) -> None:
    year = int(context.partition_key)
    context.log.info("Loading OpenMeteo weather data for year %d", year)
    run_weather_pipeline(year)
