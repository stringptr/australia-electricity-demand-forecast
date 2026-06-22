import sys

sys.path.insert(0, "/opt/dagster/dlt")

from dagster import Definitions

from jobs.assets.bronze import demand_5min_asset, weather_hourly_asset
from jobs.historical_load import historical_backfill

defs = Definitions(
    assets=[demand_5min_asset, weather_hourly_asset],
    jobs=[historical_backfill],
)
