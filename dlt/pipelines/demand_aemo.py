import logging
from datetime import datetime

import dlt

from utils.openelectricity import fetch_demand_range

logger = logging.getLogger(__name__)


def run_demand_pipeline(year: int) -> None:
    logger.info("START: Demand data pipeline for year %d", year)

    pipeline = dlt.pipeline(
        pipeline_name="demand_openelectricity",
        destination="postgres",
        dataset_name="bronze",
    )

    now = datetime.now()

    if year > now.year:
        logger.info("YEAR %d: future year, nothing to do", year)
        return

    end_month = min(12, now.month) if year == now.year else 12

    for month in range(1, end_month + 1):
        logger.info("MONTH %d-%02d: starting ...", year, month)

        month_start = datetime(year, month, 1)
        month_end = datetime(year + 1, 1, 1) if month == 12 else datetime(year, month + 1, 1)

        chunk_count = 0
        month_rows = 0

        for chunk in fetch_demand_range(month_start, month_end):
            pipeline.run(
                chunk,
                table_name="demand",
                write_disposition="merge",
                primary_key=("time", "region_id"),
            )
            chunk_count += 1
            month_rows += len(chunk)
            logger.info("STORE: wrote chunk %d (%d rows) for %d-%02d",
                        chunk_count, len(chunk), year, month)

        if month_rows == 0:
            logger.info("MONTH %d-%02d: no rows", year, month)
        else:
            logger.info("MONTH %d-%02d: DLT done (%d chunks, %d rows)",
                        year, month, chunk_count, month_rows)

    logger.info("PIPELINE: demand pipeline completed for year %d", year)
