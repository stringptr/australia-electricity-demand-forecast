import calendar
import logging
from datetime import datetime

import dlt
import pendulum

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
        "time": pendulum.parse(row["time"]),
        "region_id": row["region_id"],
    }
    for f in WEATHER_FIELDS:
        result[f] = row.get(f)
    return result


def run_weather_pipeline(year: int) -> None:
    pipeline = dlt.pipeline(
        pipeline_name="weather_openmeteo",
        destination="postgres",
        dataset_name="bronze",
    )

    now = datetime.now()
    end_month = min(12, now.month) if year == now.year else 12

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

            logger.info("REGION %s month %02d: fetching %s → %s", region_id, month, month_start, month_end)
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

    logger.info("PIPELINE: weather_openmeteo completed for year %d", year)
