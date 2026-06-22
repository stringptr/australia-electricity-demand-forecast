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
    """DLT resource: AEMO DISPATCHDEMAND rows → bronze.demand."""
    rows = process_year(year)
    for row in rows:
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
    info = pipeline.run(demand_resource(year))
    logger.info("Demand pipeline completed: %s", info)
