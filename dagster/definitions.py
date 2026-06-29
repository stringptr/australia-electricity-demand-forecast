import sys

sys.path.insert(0, "/opt/dagster/dlt")

from dagster import Definitions

from jobs.assets.bronze import demand_5min_asset, weather_hourly_asset
from jobs.historical_load import historical_backfill
from jobs.train_model import train_multi_output_xgboost
from jobs.validate_data import validate_data

defs = Definitions(
    assets=[demand_5min_asset, weather_hourly_asset],
    jobs=[historical_backfill, train_multi_output_xgboost, validate_data],
)
