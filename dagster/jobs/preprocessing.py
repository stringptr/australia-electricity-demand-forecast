import pandas as pd
import numpy as np

WEATHER_COLS = [
    "temperature_2m",
    "relative_humidity_2m",
    "precipitation",
    "cloud_cover",
    "wind_speed_10m",
    "shortwave_radiation",
]

PER_HORIZON = [
    "temperature_2m",
    "relative_humidity_2m",
    "hour_sin",
    "hour_cos",
    "dow_sin",
    "dow_cos",
    "month_sin",
    "month_cos",
    "is_weekend",
    "wind_power",
    "solar_potential",
    "temp_change",
    "has_precip",
]

STATIC_FEATS = [
    "demand_lag_24h",
    "demand_lag_48h",
    "demand_lag_72h",
    "demand_lag_168h",
    "demand_lag_744h",
    "temp_lag_24h",
    "temp_lag_48h",
    "demand_rolling_mean_24h",
    "demand_rolling_std_24h",
    "demand_rolling_mean_168h",
]

MAX_HORIZON = 24
REGIONS = ["NSW1", "QLD1", "SA1", "TAS1", "VIC1"]


def build_long_format(df: pd.DataFrame) -> pd.DataFrame:
    """Build one row per (region, time, horizon) with features at time t+h."""

    df = df.sort_values(["region_id", "time"]).reset_index(drop=True)

    weather_cols = [c for c in WEATHER_COLS if c in df.columns]

    groups = []
    for _rid, grp in df.groupby("region_id"):
        grp = grp.sort_values("time")
        grp = grp.copy()
        grp["demand_lag_24h"] = grp["demand_mw"].shift(24)
        grp["demand_lag_48h"] = grp["demand_mw"].shift(48)
        grp["demand_lag_72h"] = grp["demand_mw"].shift(72)
        grp["demand_lag_168h"] = grp["demand_mw"].shift(168)
        grp["demand_lag_744h"] = grp["demand_mw"].shift(744)
        grp["temp_lag_24h"] = grp["temperature_2m"].shift(24)
        grp["temp_lag_48h"] = grp["temperature_2m"].shift(48)
        grp["demand_rolling_mean_24h"] = (
            grp["demand_mw"].shift(1).rolling(24, min_periods=1).mean()
        )
        grp["demand_rolling_std_24h"] = (
            grp["demand_mw"].shift(1).rolling(24, min_periods=1).std()
        )
        grp["demand_rolling_mean_168h"] = (
            grp["demand_mw"].shift(1).rolling(168, min_periods=1).mean()
        )
        groups.append(grp)
    df_base = pd.concat(groups, ignore_index=True)
    df_base["temp_now"] = df_base["temperature_2m"]

    dfs = []
    for h in range(1, MAX_HORIZON + 1):
        df_h = df_base.copy()
        df_h["horizon"] = h

        for col in weather_cols:
            df_h[col] = df.groupby("region_id")[col].shift(-h)

        target_time = df_h["time"] + pd.Timedelta(hours=h)
        df_h["hour"] = target_time.dt.hour
        df_h["day_of_week"] = target_time.dt.dayofweek
        df_h["month"] = target_time.dt.month
        df_h["is_weekend"] = df_h["day_of_week"].isin([5, 6]).astype(int)

        df_h["target"] = df.groupby("region_id")["demand_mw"].shift(-h)

        df_h["wind_power"] = df_h["wind_speed_10m"] ** 3
        df_h["solar_potential"] = (
            df_h["shortwave_radiation"] * (1 - df_h["cloud_cover"] / 100)
        )
        df_h["temp_change"] = df_h["temperature_2m"] - df_h["temp_now"]

        df_h["hour_sin"] = np.sin(2 * np.pi * df_h["hour"] / 24)
        df_h["hour_cos"] = np.cos(2 * np.pi * df_h["hour"] / 24)
        df_h["dow_sin"] = np.sin(2 * np.pi * df_h["day_of_week"] / 7)
        df_h["dow_cos"] = np.cos(2 * np.pi * df_h["day_of_week"] / 7)
        df_h["month_sin"] = np.sin(2 * np.pi * df_h["month"] / 12)
        df_h["month_cos"] = np.cos(2 * np.pi * df_h["month"] / 12)
        df_h["has_precip"] = (df_h["precipitation"] > 0).astype(int)

        dfs.append(df_h)

    return pd.concat(dfs, ignore_index=True).dropna()


def pivot_to_wide(df_long: pd.DataFrame) -> tuple[pd.DataFrame, list[str], list[str]]:
    """Pivot long-format to wide: one row per (region, time) with 24 target + 322
    feature columns.  Returns (df_wide, target_cols, feature_cols)."""

    per_horizon = [c for c in PER_HORIZON if c in df_long.columns]

    pivot_dfs = []
    for h in range(1, MAX_HORIZON + 1):
        df_h = df_long[df_long["horizon"] == h].copy()

        renames = {col: col + f"_h{h}" for col in per_horizon}
        renames["target"] = f"target_h{h}"
        df_h = df_h.rename(columns=renames)

        keep = ["region_id", "time"] + STATIC_FEATS + list(renames.values())
        keep = [c for c in keep if c in df_h.columns]
        pivot_dfs.append(df_h[keep])

    df_wide = pivot_dfs[0]
    for i in range(1, MAX_HORIZON):
        df_wide = df_wide.merge(
            pivot_dfs[i],
            on=["region_id", "time"] + STATIC_FEATS,
            how="inner",
        )

    target_cols = [f"target_h{h}" for h in range(1, MAX_HORIZON + 1)]
    feature_cols = [
        c
        for c in df_wide.columns
        if c not in target_cols + ["region_id", "time"]
    ]

    return df_wide, target_cols, feature_cols
