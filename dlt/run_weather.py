import argparse

from shared.logging import setup_json_logging
from pipelines.weather_openmeteo import run_weather_pipeline

setup_json_logging("dlt-weather")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="DLT: OpenMeteo weather → bronze.weather")
    parser.add_argument("--year", type=int, required=True, help="Year to backfill (e.g. 2023)")
    args = parser.parse_args()
    run_weather_pipeline(args.year)
