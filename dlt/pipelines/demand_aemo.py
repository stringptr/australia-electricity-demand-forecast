import logging
import os
import tempfile
from datetime import datetime

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
        pipelines_dir=tempfile.mkdtemp(prefix="dlt_demand_"),
    )

    now = datetime.now()

    if year > now.year:
        logger.info("YEAR %d: future year, nothing to do", year)
        return

    try:
        engine = _get_db_engine()
        with engine.connect() as conn:
            rows = conn.execute(
                text(
                    "SELECT DISTINCT EXTRACT(MONTH FROM time)::int "
                    "FROM bronze.demand "
                    "WHERE time >= :s AND time < :e"
                ),
                {"s": datetime(year, 1, 1), "e": datetime(year + 1, 1, 1)},
            ).fetchall()
            months_with_data = {r[0] for r in rows}
    except Exception:
        months_with_data = set()
        logger.warning("Cannot query bronze.demand months, will fetch all")

    end_month = min(12, now.month) if year == now.year else 12

    for month in range(1, end_month + 1):
        if month in months_with_data:
            logger.info("MONTH %d-%02d: already has data, skipping", year, month)
            continue

        month_start = datetime(year, month, 1)
        month_end = datetime(year + 1, 1, 1) if month == 12 else datetime(year, month + 1, 1)
        if year == now.year and month == now.month:
            month_end = now

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
