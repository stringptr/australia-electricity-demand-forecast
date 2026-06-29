import logging
from typing import Generator

import httpx

logger = logging.getLogger(__name__)

ARCHIVE_API = "https://archive-api.open-meteo.com/v1/archive"

HOURLY_PARAMS = [
    "temperature_2m",
    "relative_humidity_2m",
    "precipitation",
    "cloud_cover",
    "wind_speed_10m",
    "shortwave_radiation",
]

REGIONS: list[dict] = [
    {"id": "NSW1", "name": "NSW", "lat": -33.87, "lon": 151.21, "tz": "Australia/Sydney"},
    {"id": "QLD1", "name": "QLD", "lat": -27.47, "lon": 153.03, "tz": "Australia/Brisbane"},
    {"id": "SA1", "name": "SA", "lat": -34.93, "lon": 138.60, "tz": "Australia/Adelaide"},
    {"id": "TAS1", "name": "TAS", "lat": -42.88, "lon": 147.33, "tz": "Australia/Hobart"},
    {"id": "VIC1", "name": "VIC", "lat": -37.81, "lon": 144.96, "tz": "Australia/Melbourne"},
]


def _fetch_region(region: dict, start_date: str, end_date: str) -> list[dict]:
    """Fetch hourly weather for one region over a date range."""
    params = {
        "latitude": region["lat"],
        "longitude": region["lon"],
        "start_date": start_date,
        "end_date": end_date,
        "hourly": ",".join(HOURLY_PARAMS),
        "timezone": region["tz"],
    }

    logger.info("FETCH: weather for %s (%s) [lat=%.2f, lon=%.2f] from %s to %s", region["id"], region["name"], region["lat"], region["lon"], start_date, end_date)

    with httpx.Client(timeout=httpx.Timeout(90)) as client:
        resp = client.get(ARCHIVE_API, params=params)
        resp.raise_for_status()

    logger.info("FETCHED: %s → HTTP %d, %d bytes received", region["id"], resp.status_code, len(resp.content))

    data = resp.json()
    hourly = data.get("hourly", {})
    if not hourly:
        logger.warning("EMPTY: no hourly data for %s (%s to %s)", region["id"], start_date, end_date)
        return []

    times = hourly.get("time", [])
    rows = []
    for idx, ts in enumerate(times):
        row = {
            "time": ts,
            "region_id": region["id"],
        }
        for param in HOURLY_PARAMS:
            values = hourly.get(param, [])
            val = values[idx] if idx < len(values) else None
            row[param] = val
        rows.append(row)

    logger.info("PARSED: %s → %d hourly rows [%.1f%% of year]", region["id"], len(rows), 100 * len(rows) / 8760 if len(rows) <= 8760 else 0)
    return rows


def fetch_all_regions(year: int) -> Generator[dict, None, None]:
    """Yield hourly weather rows for all 5 regions in a year (sequential)."""
    from datetime import datetime

    current = datetime.now()
    start_date = f"{year}-01-01"
    end_date = f"{year}-12-31"
    if year == current.year:
        end_date = current.strftime("%Y-%m-%d")

    total_regions = len(REGIONS)
    logger.info("YEAR %d: fetching weather for %d regions [%s → %s] sequentially", year, total_regions, start_date, end_date)
    completed = 0

    for region in REGIONS:
        region_id = region["id"]
        try:
            logger.info("REGION %s: starting [%d/%d]", region_id, completed + 1, total_regions)
            rows = _fetch_region(region, start_date, end_date)
            yielded = 0
            for row in rows:
                yield row
                yielded += 1
            completed += 1
            logger.info("REGION %s OK: %d rows yielded [%d/%d regions done]", region_id, yielded, completed, total_regions)
        except Exception:
            logger.exception("REGION %s FAILED year %d", region_id, year)
            completed += 1
            logger.info("REGION %s FAILED: skipped [%d/%d regions done]", region_id, completed, total_regions)
