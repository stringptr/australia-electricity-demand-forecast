import os

MAX_HORIZON = 24
REGIONS = ["NSW1", "QLD1", "SA1", "TAS1", "VIC1"]

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

WEATHER_COLS = [
    "temperature_2m",
    "relative_humidity_2m",
    "precipitation",
    "cloud_cover",
    "wind_speed_10m",
    "shortwave_radiation",
]

MLFLOW_TRACKING_URI = os.environ.get(
    "MLFLOW_TRACKING_URI", "http://mlflow:5000"
)

PG_DSN = (
    f"postgresql://{os.environ.get('PG_USER', 'postgres')}:"
    f"{os.environ.get('PG_PASSWORD', 'postgres')}@"
    f"{os.environ.get('PG_HOST', 'postgres')}:"
    f"{os.environ.get('PG_PORT', '5432')}/"
    f"{os.environ.get('PG_DB', 'electricity')}"
)

NATS_URL = os.environ.get("NATS_URL", "nats://nats:4222")
NATS_SUBJECT = os.environ.get(
    "NATS_SUBJECT", "electricity.silver.demand_5min"
)

HISTORY_LOOKBACK_HOURS = 744

OPENMETEO_FORECAST_API = "https://api.open-meteo.com/v1/forecast"

REGION_COORDS = [
    {"id": "NSW1", "lat": -33.87, "lon": 151.21, "tz": "Australia/Sydney"},
    {"id": "QLD1", "lat": -27.47, "lon": 153.03, "tz": "Australia/Brisbane"},
    {"id": "SA1", "lat": -34.93, "lon": 138.60, "tz": "Australia/Adelaide"},
    {"id": "TAS1", "lat": -42.88, "lon": 147.33, "tz": "Australia/Hobart"},
    {"id": "VIC1", "lat": -37.81, "lon": 144.96, "tz": "Australia/Melbourne"},
]

REGION_COORDS_MAP = {r["id"]: r for r in REGION_COORDS}
