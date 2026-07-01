import logging
import os
from datetime import datetime, timedelta

import dlt
from sqlalchemy import create_engine, text

from utils.openelectricity import fetch_demand_range

logger = logging.getLogger(__name__)


def _get_db_engine():
    host = os.environ.get("PG_HOST", os.environ.get("POSTGRES_HOST", "postgres"))
    port = os.environ.get("PG_PORT", os.environ.get("POSTGRES_PORT", "5432"))
    user = os.environ.get("PG_USER", os.environ.get("POSTGRES_USER", "postgres"))
    password = os.environ.get("PG_PASSWORD", os.environ.get("POSTGRES_PASSWORD", "postgres"))
    db = os.environ.get("PG_DB", os.environ.get("POSTGRES_DB", "electricity"))
    return create_engine(f"postgresql://{user}:{password}@{host}:{port}/{db}")


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

    try:
        engine = _get_db_engine()
        with engine.connect() as conn:
            result = conn.execute(text("SELECT MAX(time) FROM bronze.demand"))
            last_time = result.scalar()
    except Exception:
        logger.warning("Cannot query bronze.demand, fetching all data")
        last_time = None

    if last_time is not None:
        start_from = last_time.date() - timedelta(days=1)
        today = now.date()
        if start_from >= today:
            start_from = today
            logger.info("DB has data up to %s (today), will re-fetch today", last_time)
        else:
            logger.info("DB has data up to %s, starting from %s", last_time, start_from)
    else:
        start_from = None
        logger.info("DB has no bronze.demand data, fetching all")

    end_month = min(12, now.month) if year == now.year else 12

    for month in range(1, end_month + 1):
        month_start = datetime(year, month, 1)
        month_end = datetime(year + 1, 1, 1) if month == 12 else datetime(year, month + 1, 1)
        if year == now.year and month == now.month:
            month_end = now

        if start_from is not None:
            adjusted = datetime.combine(start_from, datetime.min.time())
            if adjusted > month_start:
                month_start = adjusted

        if month_start >= month_end:
            logger.info("MONTH %d-%02d: already complete, skipping", year, month)
            continue

        logger.info("MONTH %d-%02d: starting ...", year, month)

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
