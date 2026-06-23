import logging

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
    "shortwave_radiation_sum",
]


def _transform_row(row: dict) -> dict:
    raw = {"time": row["time"], "region_id": row["region_id"]}
    for f in WEATHER_FIELDS:
        raw[f] = row.get(f)

    return {
        "time": pendulum.parse(row["time"]),
        "region_id": row["region_id"],
        "raw_payload": raw,
    }


def run_weather_pipeline(year: int) -> None:
    from datetime import datetime

    pipeline = dlt.pipeline(
        pipeline_name="weather_openmeteo",
        destination="postgres",
        dataset_name="bronze",
    )

    current = datetime.now()
    start_date = f"{year}-01-01"
    end_date = f"{year}-12-31"
    if year == current.year:
        end_date = current.strftime("%Y-%m-%d")

    for region in REGIONS:
        region_id = region["id"]
        logger.info("REGION %s: DLT pipeline run starting ...", region_id)
        rows = _fetch_region(region, start_date, end_date)
        if not rows:
            logger.info("REGION %s: no rows, skipping DLT run", region_id)
            continue

        pipeline.run(
            (_transform_row(r) for r in rows),
            table_name="weather",
            write_disposition="merge",
            primary_key=("time", "region_id"),
        )
        logger.info("REGION %s: DLT pipeline done (%d rows)", region_id, len(rows))

    logger.info("PIPELINE: weather_openmeteo completed for year %d", year)
