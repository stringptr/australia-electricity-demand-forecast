import logging

import dlt
import pendulum

from utils.aemo import iter_month_files

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
        logger.info("MONTH %d-%02d: starting ...", year, month)
        file_count = 0
        month_rows = 0

        for file_rows in iter_month_files(year, month):
            if not file_rows:
                continue
            pipeline.run(
                (_transform_row(r) for r in file_rows),
                table_name="demand",
                write_disposition="merge",
                primary_key=("time", "region_id"),
            )
            file_count += 1
            month_rows += len(file_rows)

        if month_rows == 0:
            logger.info("MONTH %d-%02d: no rows, skipping", year, month)
        else:
            logger.info("MONTH %d-%02d: DLT done (%d files, %d rows)", year, month, file_count, month_rows)

    logger.info("PIPELINE: demand_aemo completed for year %d", year)
