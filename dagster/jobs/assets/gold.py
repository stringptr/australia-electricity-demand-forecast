import os

import pandas as pd
from dagster import AssetExecutionContext, AssetKey, asset
from sqlalchemy import create_engine, text

REGION_NAMES = {
    "NSW1": "New South Wales",
    "QLD1": "Queensland",
    "SA1": "South Australia",
    "TAS1": "Tasmania",
    "VIC1": "Victoria",
}


def _get_db_engine():
    host = os.environ.get("PG_HOST", os.environ.get("POSTGRES_HOST", "postgres"))
    port = os.environ.get("PG_PORT", os.environ.get("POSTGRES_PORT", "5432"))
    user = os.environ.get("PG_USER", os.environ.get("POSTGRES_USER", "postgres"))
    password = os.environ.get("PG_PASSWORD", os.environ.get("POSTGRES_PASSWORD", "postgres"))
    db = os.environ.get("PG_DB", os.environ.get("POSTGRES_DB", "electricity"))
    return create_engine(f"postgresql://{user}:{password}@{host}:{port}/{db}")


@asset(
    key_prefix=["gold"],
    group_name="gold",
    io_manager_key="postgres_io_manager",
    deps=[
        AssetKey(["silver", "demand_5min"]),
        AssetKey(["silver", "weather_hourly"]),
    ],
    description="Incremental: merge new silver demand + weather into gold.correlation_hourly",
)
def correlation_hourly(context: AssetExecutionContext) -> pd.DataFrame:
    engine = _get_db_engine()

    with engine.connect() as conn:
        last_hour = conn.execute(
            text(
                "SELECT COALESCE(MAX(time), '1970-01-01T00:00:00Z'::TIMESTAMPTZ) "
                "FROM gold.correlation_hourly"
            )
        ).scalar()

    context.log.info(f"Last gold hour: {last_hour}")

    demand_query = text("""
        SELECT
            date_trunc('hour', time) AS time,
            region_id,
            AVG(demand_mw) AS demand_mw
        FROM silver.demand_5min
        WHERE time > :last_hour
        GROUP BY date_trunc('hour', time), region_id
        ORDER BY time, region_id
    """)
    with engine.connect() as conn:
        df_demand = pd.read_sql_query(
            demand_query, conn, params={"last_hour": last_hour}, parse_dates=["time"]
        )

    weather_query = text("""
        SELECT
            time, region_id,
            temperature_2m, relative_humidity_2m,
            precipitation, cloud_cover,
            wind_speed_10m, shortwave_radiation
        FROM silver.weather_hourly
        WHERE time > :last_hour
        ORDER BY time, region_id
    """)
    with engine.connect() as conn:
        df_weather = pd.read_sql_query(
            weather_query, conn, params={"last_hour": last_hour}, parse_dates=["time"]
        )

    df_demand["region_name"] = df_demand["region_id"].map(REGION_NAMES)
    df_weather["region_name"] = df_weather["region_id"].map(REGION_NAMES)

    context.log.info(
        f"New demand hours: {len(df_demand):,}  |  "
        f"New weather hours: {len(df_weather):,}"
    )

    if df_demand.empty:
        context.log.info("No new demand data to merge")
        return pd.DataFrame()

    df = df_demand.merge(
        df_weather,
        on=["time", "region_id", "region_name"],
        how="left",
    )

    df = df.sort_values(["region_id", "time"]).reset_index(drop=True)
    weather_cols = [
        "temperature_2m", "relative_humidity_2m", "precipitation",
        "cloud_cover", "wind_speed_10m", "shortwave_radiation",
    ]
    for col in weather_cols:
        df[col] = df.groupby("region_id")[col].transform(lambda s: s.ffill())

    context.log.info(f"Merged {len(df)} rows for gold.correlation_hourly")
    return df


@asset(
    key_prefix=["gold"],
    group_name="gold",
    io_manager_key="postgres_io_manager",
    deps=[AssetKey(["gold", "correlation_hourly"])],
    description="Daily aggregates from gold.correlation_hourly → gold.correlation_daily",
)
def correlation_daily(context: AssetExecutionContext) -> pd.DataFrame:
    engine = _get_db_engine()

    with engine.connect() as conn:
        last_date = conn.execute(
            text(
                "SELECT COALESCE(MAX(date), '1970-01-01'::DATE) "
                "FROM gold.correlation_daily"
            )
        ).scalar()

    context.log.info(f"Last daily date: {last_date}")

    query = text("""
        SELECT
            time::DATE AS date,
            region_id,
            region_name,
            AVG(demand_mw) AS demand_mw_avg,
            MIN(demand_mw) AS demand_mw_min,
            MAX(demand_mw) AS demand_mw_max,
            AVG(temperature_2m) AS temperature_2m_avg,
            MIN(temperature_2m) AS temperature_2m_min,
            MAX(temperature_2m) AS temperature_2m_max,
            AVG(relative_humidity_2m) AS relative_humidity_avg,
            SUM(COALESCE(precipitation, 0)) AS precipitation_sum,
            AVG(cloud_cover) AS cloud_cover_avg,
            AVG(wind_speed_10m) AS wind_speed_10m_avg,
            AVG(shortwave_radiation) AS shortwave_radiation_avg,
            COUNT(*) AS data_points
        FROM gold.correlation_hourly
        WHERE time::DATE > :last_date
        GROUP BY time::DATE, region_id, region_name
        HAVING MAX(EXTRACT(HOUR FROM time)) >= 23
        ORDER BY date, region_id
    """)

    with engine.connect() as conn:
        df = pd.read_sql_query(query, conn, params={"last_date": last_date}, parse_dates=["date"])

    if df.empty:
        context.log.info("No complete daily data to aggregate")
        return pd.DataFrame()

    context.log.info(
        f"Aggregated {len(df)} rows for gold.correlation_daily "
        f"(dates: {df['date'].min()} -> {df['date'].max()})"
    )
    return df
