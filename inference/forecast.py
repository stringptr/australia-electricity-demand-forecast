import logging
from typing import Optional

import httpx
import pandas as pd

from .config import OPENMETEO_FORECAST_API, REGION_COORDS, WEATHER_COLS

logger = logging.getLogger(__name__)


def _fetch_region_forecast(region: dict) -> list[dict]:
    params = {
        "latitude": region["lat"],
        "longitude": region["lon"],
        "hourly": ",".join(WEATHER_COLS),
        "timezone": region["tz"],
        "forecast_days": 1,
    }

    with httpx.Client(timeout=httpx.Timeout(30)) as client:
        resp = client.get(OPENMETEO_FORECAST_API, params=params)
        resp.raise_for_status()

    data = resp.json()
    hourly = data["hourly"]
    times = hourly["time"]

    rows = []
    for i, ts in enumerate(times):
        row = {"time": ts, "region_id": region["id"]}
        for col in WEATHER_COLS:
            values = hourly.get(col, [])
            row[col] = values[i] if i < len(values) else None
        rows.append(row)

    logger.info("Forecast %s: %d hours [%s → %s]",
                region["id"], len(rows), rows[0]["time"] if rows else "-",
                rows[-1]["time"] if rows else "-")
    return rows


def fetch_forecast_all_regions() -> pd.DataFrame:
    rows = []
    for region in REGION_COORDS:
        try:
            rows.extend(_fetch_region_forecast(region))
        except Exception:
            logger.exception("Forecast failed for %s", region["id"])

    df = pd.DataFrame(rows)
    if not df.empty:
        df["time"] = pd.to_datetime(df["time"])
    return df


def forecast_at(df: pd.DataFrame, region_id: str, target_time: pd.Timestamp) -> dict:
    subset = df[
        (df["region_id"] == region_id) & (df["time"] == target_time)
    ]
    if subset.empty:
        raise ValueError(
            f"No forecast for {region_id} at {target_time}"
        )
    return subset.iloc[0].to_dict()
