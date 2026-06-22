import logging
from typing import Generator

import dlt
import pendulum

from utils.openmeteo import fetch_all_regions

logger = logging.getLogger(__name__)

WEATHER_FIELDS = [
    "temperature_2m",
    "relative_humidity_2m",
    "precipitation",
    "cloud_cover",
    "wind_speed_10m",
    "shortwave_radiation_sum",
]


@dlt.resource(
    name="weather",
    write_disposition="merge",
    merge_key=("time", "region_id"),
)
def weather_resource(year: int) -> Generator[dict, None, None]:
    """DLT resource: OpenMeteo hourly weather → bronze.weather."""
    for row in fetch_all_regions(year):
        raw = {"time": row["time"], "region_id": row["region_id"]}
        for f in WEATHER_FIELDS:
            raw[f] = row.get(f)

        yield {
            "time": pendulum.parse(row["time"]),
            "region_id": row["region_id"],
            "raw_payload": raw,
        }


def run_weather_pipeline(year: int) -> None:
    pipeline = dlt.pipeline(
        pipeline_name="weather_openmeteo",
        destination="postgres",
        dataset_name="bronze",
    )
    info = pipeline.run(weather_resource(year))
    logger.info("Weather pipeline completed: %s", info)
