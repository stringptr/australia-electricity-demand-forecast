import calendar
import logging
import os
import shutil
from datetime import datetime, timedelta

import dlt
from sqlalchemy import create_engine, text

from utils.openmeteo import REGIONS, _fetch_region

logger = logging.getLogger(__name__)

WEATHER_FIELDS = [
    "temperature_2m",
    "relative_humidity_2m",
    "precipitation",
    "cloud_cover",
    "wind_speed_10m",
    "shortwave_radiation",
]


def _transform_row(row: dict) -> dict:
    result = {
        "time": datetime.fromisoformat(row["time"]),
        "region_id": row["region_id"],
    }
    for f in WEATHER_FIELDS:
        result[f] = row.get(f)
    return result


def _get_db_engine():
    host = os.environ.get("PG_HOST", os.environ.get("POSTGRES_HOST", "postgres"))
    port = os.environ.get("PG_PORT", os.environ.get("POSTGRES_PORT", "5432"))
    user = os.environ.get("PG_USER", os.environ.get("POSTGRES_USER", "postgres"))
    password = os.environ.get("PG_PASSWORD", os.environ.get("POSTGRES_PASSWORD", "postgres"))
    db = os.environ.get("PG_DB", os.environ.get("POSTGRES_DB", "electricity"))
    return create_engine(f"postgresql://{user}:{password}@{host}:{port}/{db}")


def run_weather_pipeline(year: int) -> int:
    pipelines_dir = "/tmp/dlt/weather_openmeteo"
    if os.path.exists(pipelines_dir):
        shutil.rmtree(pipelines_dir)

    pipeline = dlt.pipeline(
        pipeline_name="weather_openmeteo",
        destination="postgres",
        dataset_name="bronze",
        pipelines_dir=pipelines_dir,
    )

    now = datetime.now()

    try:
        engine = _get_db_engine()
        with engine.connect() as conn:
            result = conn.execute(text("SELECT MAX(time) FROM bronze.weather"))
            last_time = result.scalar()
    except Exception:
        logger.warning("Cannot query bronze.weather, fetching all data")
        last_time = None

    if last_time is not None:
        start_from = last_time.date() - timedelta(days=1)
        today = now.date()
        if start_from >= today:
            start_from = today
            logger.info("DB has weather up to %s (today), will re-fetch today", last_time)
        else:
            logger.info("DB has weather up to %s, starting from %s", last_time, start_from)
    else:
        start_from = None
        logger.info("DB has no bronze.weather data, fetching all")

    end_month = min(12, now.month) if year == now.year else 12

    total_rows = 0

    for region in REGIONS:
        region_id = region["id"]
        region_rows = 0
        logger.info("REGION %s: DLT pipeline run starting ...", region_id)

        for month in range(1, end_month + 1):
            month_start = f"{year}-{month:02d}-01"
            last_day = calendar.monthrange(year, month)[1]
            month_end = f"{year}-{month:02d}-{last_day:02d}"
            if year == now.year and month == now.month:
                month_end = now.strftime("%Y-%m-%d")

            if start_from is not None:
                adjusted_start = start_from.isoformat()
                if adjusted_start > month_start:
                    month_start = adjusted_start

            if month_start >= month_end:
                logger.info("REGION %s month %02d: already complete, skipping",
                            region_id, month)
                continue

            logger.info("REGION %s month %02d: fetching %s → %s",
                        region_id, month, month_start, month_end)
            rows = _fetch_region(region, month_start, month_end)
            if not rows:
                continue

            pipeline.run(
                (_transform_row(r) for r in rows),
                table_name="weather",
                write_disposition="merge",
                primary_key=("time", "region_id"),
            )
            region_rows += len(rows)

        logger.info("REGION %s: DLT pipeline done (%d rows)", region_id, region_rows)
        total_rows += region_rows

    logger.info("PIPELINE: weather_openmeteo completed for year %d (%d rows)", year, total_rows)
    return total_rows
