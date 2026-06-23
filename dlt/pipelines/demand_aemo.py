import logging

import dlt
import pendulum

from utils.aemo import _download_and_extract

logger = logging.getLogger(__name__)


def _transform_row(row: dict) -> dict:
    return {
        "time": pendulum.parse(row["time"], tz="Australia/Sydney"),
        "region_id": row["region_id"],
        "raw_payload": {
            "SETTLEMENTDATE": row["time"],
            "REGIONID": row["region_id"],
            "TOTALDEMAND": row["total_demand"],
        },
    }


def run_demand_pipeline(year: int) -> None:
    from datetime import datetime

    pipeline = dlt.pipeline(
        pipeline_name="demand_aemo",
        destination="postgres",
        dataset_name="bronze",
    )

    current = datetime.now()
    end_month = 12
    if year == current.year:
        end_month = min(12, current.month)
    if year > current.year:
        return

    for month in range(1, end_month + 1):
        logger.info("MONTH %d-%02d: DLT pipeline run starting ...", year, month)
        rows = _download_and_extract(year, month)
        if not rows:
            logger.info("MONTH %d-%02d: no rows, skipping DLT run", year, month)
            continue

        pipeline.run(
            (_transform_row(r) for r in rows),
            table_name="demand",
            write_disposition="merge",
            primary_key=("time", "region_id"),
        )
        logger.info("MONTH %d-%02d: DLT pipeline done (%d rows)", year, month, len(rows))

    logger.info("PIPELINE: demand_aemo completed for year %d", year)
