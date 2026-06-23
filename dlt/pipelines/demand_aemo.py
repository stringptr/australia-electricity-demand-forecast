import logging
from typing import Generator

import dlt
import pendulum

from utils.aemo import process_year

logger = logging.getLogger(__name__)


@dlt.resource(
    name="demand",
    write_disposition="merge",
    merge_key=("time", "region_id"),
)
def demand_resource(year: int) -> Generator[dict, None, None]:
    """DLT resource: AEMO DISPATCHDEMAND rows → bronze.demand (streaming)."""
    for row in process_year(year):
        yield {
            "time": pendulum.parse(row["time"], tz="Australia/Sydney"),
            "region_id": row["region_id"],
            "raw_payload": {
                "SETTLEMENTDATE": row["time"],
                "REGIONID": row["region_id"],
                "TOTALDEMAND": row["total_demand"],
            },
        }


def run_demand_pipeline(year: int) -> None:
    pipeline = dlt.pipeline(
        pipeline_name="demand_aemo",
        destination="postgres",
        dataset_name="bronze",
    )
    logger.info("PIPELINE: demand_aemo starting DLT run for year %d → bronze.demand", year)
    info = pipeline.run(demand_resource(year))
    logger.info("PIPELINE: demand_aemo completed for year %d: %s", year, info)
