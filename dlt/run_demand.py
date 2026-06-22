import argparse
import logging

from pipelines.demand_aemo import run_demand_pipeline

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="DLT: AEMO NEMWeb demand → bronze.demand")
    parser.add_argument("--year", type=int, required=True, help="Year to backfill (e.g. 2023)")
    args = parser.parse_args()
    run_demand_pipeline(args.year)
