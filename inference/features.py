import numpy as np
import pandas as pd

from .config import MAX_HORIZON, REGIONS
from .forecast import forecast_at


def _compute_static(
    region_history: pd.DataFrame, current_time: pd.Timestamp
) -> list[float]:
    demand = region_history.set_index("time")["demand_mw"]
    temp = region_history.set_index("time").get("temperature_2m", pd.Series(dtype=float))

    def _demand_at(offset_h: int) -> float:
        t = current_time - pd.Timedelta(hours=offset_h)
        val = demand.get(t)
        return float(val) if pd.notna(val) else 0.0

    def _temp_at(offset_h: int) -> float:
        t = current_time - pd.Timedelta(hours=offset_h)
        val = temp.get(t)
        return float(val) if (val is not None and pd.notna(val)) else 0.0

    end = current_time - pd.Timedelta(hours=1)
    start_24 = current_time - pd.Timedelta(hours=24)
    start_168 = current_time - pd.Timedelta(hours=168)

    window_24h = demand[(demand.index > start_24) & (demand.index <= end)]
    window_168h = demand[(demand.index > start_168) & (demand.index <= end)]

    return [
        _demand_at(24),
        _demand_at(48),
        _demand_at(72),
        _demand_at(168),
        _demand_at(744),
        _temp_at(24),
        _temp_at(48),
        float(window_24h.mean()) if len(window_24h) > 0 else 0.0,
        float(window_24h.std()) if len(window_24h) > 1 else 0.0,
        float(window_168h.mean()) if len(window_168h) > 0 else 0.0,
    ]


def _calendar_features(target_time: pd.Timestamp) -> dict:
    h = target_time.hour
    dow = target_time.dayofweek
    m = target_time.month
    return {
        "hour_sin": np.sin(2 * np.pi * h / 24),
        "hour_cos": np.cos(2 * np.pi * h / 24),
        "dow_sin": np.sin(2 * np.pi * dow / 7),
        "dow_cos": np.cos(2 * np.pi * dow / 7),
        "month_sin": np.sin(2 * np.pi * m / 12),
        "month_cos": np.cos(2 * np.pi * m / 12),
        "is_weekend": 1.0 if dow in (5, 6) else 0.0,
    }


def _build_per_horizon_row(
    fh: dict, cal: dict, current_temp: float
) -> list[float]:
    temp = fh.get("temperature_2m", 0.0) or 0.0
    humidity = fh.get("relative_humidity_2m", 0.0) or 0.0
    wind = fh.get("wind_speed_10m", 0.0) or 0.0
    radiation = fh.get("shortwave_radiation", 0.0) or 0.0
    cloud = fh.get("cloud_cover", 0.0) or 0.0
    precip = fh.get("precipitation", 0.0) or 0.0

    wind_power = wind**3
    solar_potential = radiation * (1.0 - cloud / 100.0)
    temp_change = temp - current_temp
    has_precip = 1.0 if precip > 0 else 0.0

    return [
        temp,
        humidity,
        cal["hour_sin"],
        cal["hour_cos"],
        cal["dow_sin"],
        cal["dow_cos"],
        cal["month_sin"],
        cal["month_cos"],
        cal["is_weekend"],
        wind_power,
        solar_potential,
        temp_change,
        has_precip,
    ]


def assemble_feature_matrix(
    demand_history: pd.DataFrame,
    forecast_df: pd.DataFrame,
    current_time: pd.Timestamp,
) -> np.ndarray:
    rows = []
    for region_id in REGIONS:
        region_history = demand_history[
            demand_history["region_id"] == region_id
        ].sort_values("time")

        static = _compute_static(region_history, current_time)

        current_temp = 0.0
        if not region_history.empty:
            t_now = region_history.set_index("time").get("temperature_2m")
            ct = t_now.get(current_time)
            current_temp = float(ct) if (ct is not None and pd.notna(ct)) else 0.0

        per_horizon = []
        for h in range(1, MAX_HORIZON + 1):
            target_time = current_time + pd.Timedelta(hours=h)

            try:
                fh = forecast_at(forecast_df, region_id, target_time)
            except ValueError:
                fh = {}

            cal = _calendar_features(target_time)
            per_horizon.extend(_build_per_horizon_row(fh, cal, current_temp))

        rows.append(static + per_horizon)

    return np.array(rows, dtype=np.float32)
