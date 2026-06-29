import argparse

from shared.logging import setup_json_logging
from pipelines.demand_aemo import run_demand_pipeline

setup_json_logging("dlt-demand")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="DLT: OpenElectricity demand → bronze.demand")
    parser.add_argument("--year", type=int, required=True, help="Year to backfill (e.g. 2023)")
    args = parser.parse_args()
    run_demand_pipeline(args.year)
