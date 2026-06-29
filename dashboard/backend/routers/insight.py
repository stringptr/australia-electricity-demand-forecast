from fastapi import APIRouter, Query
from core.duck import get_duck
from typing import List, Optional
from datetime import date

router = APIRouter(prefix="/insight", tags=["insight"])

WEATHER_VARS = [
    "temperature_2m",
    "relative_humidity_2m",
    "precipitation",
    "cloud_cover",
    "wind_speed_10m",
    "shortwave_radiation",
]

WEATHER_LABELS = {
    "temperature_2m": "Temperature (°C)",
    "relative_humidity_2m": "Humidity (%)",
    "precipitation": "Precipitation (mm)",
    "cloud_cover": "Cloud Cover (%)",
    "wind_speed_10m": "Wind Speed (km/h)",
    "shortwave_radiation": "Solar Radiation (W/m²)",
}

# Daily columns for scatter: use _avg suffixed columns
DAILY_VAR_MAP = {v: v + "_avg" for v in WEATHER_VARS}
DAILY_VAR_MAP["demand_mw"] = "demand_mw_avg"


def _build_filters(region_ids: List[str], start_date: Optional[date], end_date: Optional[date], granularity: str):
    """Build list of DuckDB-compatible filter expressions using parameterized placeholders."""
    params = []
    filters = []

    # Region filter using DuckDB list/array syntax
    placeholders = ", ".join(f"'{r}'" for r in region_ids)
    filters.append(f"region_id IN ({placeholders})")

    if start_date:
        if granularity == "daily":
            filters.append(f"date >= '{start_date}'::DATE")
        else:
            filters.append(f"time >= '{start_date}'::TIMESTAMPTZ")

    if end_date:
        if granularity == "daily":
            filters.append(f"date <= '{end_date}'::DATE")
        else:
            filters.append(f"time <= '{end_date}'::TIMESTAMPTZ")

    return filters, params


@router.get("/data")
async def get_insight_data(
    region_ids: List[str] = Query(default=["NSW1"], alias="region_id"),
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    granularity: str = "daily",
):
    duck = get_duck()
    filters, _ = _build_filters(region_ids, start_date, end_date, granularity)
    where = " AND ".join(filters)

    table = "gold.correlation_daily" if granularity == "daily" else "gold.correlation_hourly"
    if granularity == "daily":
        columns = "date, region_id, region_name, demand_mw_avg, demand_mw_min, demand_mw_max, temperature_2m_avg, relative_humidity_avg, precipitation_sum, cloud_cover_avg, wind_speed_10m_avg, shortwave_radiation_avg"
    else:
        columns = "time, region_id, region_name, demand_mw, temperature_2m, relative_humidity_2m, precipitation, cloud_cover, wind_speed_10m, shortwave_radiation"

    order_col = "date" if granularity == "daily" else "time"
    result = duck.execute(
        f"SELECT {columns} FROM {table} WHERE {where} ORDER BY region_id, {order_col}"
    ).fetchdf()

    return {
        "granularity": granularity,
        "region_ids": region_ids,
        "data": result.to_dict(orient="records"),
    }


@router.get("/correlation")
async def get_correlation(
    region_ids: List[str] = Query(default=["NSW1"], alias="region_id"),
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
):
    duck = get_duck()
    filters, _ = _build_filters(region_ids, start_date, end_date, "daily")
    where = " AND ".join(filters)

    corr_exprs = []
    for var in WEATHER_VARS:
        col = DAILY_VAR_MAP[var]
        corr_exprs.append(f"CORR(demand_mw_avg, {col}) AS {var}")
    corr_sql = ", ".join(corr_exprs)

    result = duck.execute(
        f"SELECT COUNT(*) AS n, {corr_sql} FROM gold.correlation_daily WHERE {where}"
    ).fetchdf()

    row = result.to_dict(orient="records")[0]
    n = row.pop("n")
    coefficients = []
    for var in WEATHER_VARS:
        coefficients.append({
            "variable": var,
            "variable_label": WEATHER_LABELS[var],
            "r": round(float(row[var]), 4) if row[var] is not None else None,
            "n": int(n),
        })

    return {"region_ids": region_ids, "coefficients": coefficients}


@router.get("/variables")
async def get_variables():
    return {"variables": WEATHER_VARS, "labels": WEATHER_LABELS}
