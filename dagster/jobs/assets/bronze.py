import sys

sys.path.insert(0, "/opt/dagster/dlt")

from dagster import AssetExecutionContext, asset

from pipelines.demand_aemo import run_demand_pipeline
from pipelines.weather_openmeteo import run_weather_pipeline


@asset(
    description="AEMO NEMWeb 5-min DISPATCHDEMAND → bronze.demand",
    group_name="bronze",
)
def demand_5min_asset(context: AssetExecutionContext) -> None:
    year = int(context.partition_key)
    context.log.info("Loading AEMO demand data for year %d", year)
    run_demand_pipeline(year)


@asset(
    description="OpenMeteo hourly weather → bronze.weather",
    group_name="bronze",
)
def weather_hourly_asset(context: AssetExecutionContext) -> None:
    year = int(context.partition_key)
    context.log.info("Loading OpenMeteo weather data for year %d", year)
    run_weather_pipeline(year)
