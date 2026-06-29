import os
import pandas as pd
from sqlalchemy import create_engine, text
from dagster import in_process_executor, job, op

REGION_NAMES = {
    "NSW1": "New South Wales",
    "QLD1": "Queensland",
    "SA1": "South Australia",
    "TAS1": "Tasmania",
    "VIC1": "Victoria",
}

EPOCH = "1970-01-01T00:00:00Z"


def _get_db_engine():
    host = os.environ.get("PG_HOST", os.environ.get("POSTGRES_HOST", "postgres"))
    port = os.environ.get("PG_PORT", os.environ.get("POSTGRES_PORT", "5432"))
    user = os.environ.get("PG_USER", os.environ.get("POSTGRES_USER", "postgres"))
    password = os.environ.get("PG_PASSWORD", os.environ.get("POSTGRES_PASSWORD", "postgres"))
    db = os.environ.get("PG_DB", os.environ.get("POSTGRES_DB", "electricity"))
    return create_engine(f"postgresql://{user}:{password}@{host}:{port}/{db}")


@op(description="Load new 5-min demand data, aggregate to hourly, only rows after last gold hour")
def load_new_demand_op(context) -> pd.DataFrame:
    engine = _get_db_engine()

    with engine.connect() as conn:
        last_hour = conn.execute(
            text("SELECT COALESCE(MAX(time), '1970-01-01T00:00:00Z'::TIMESTAMPTZ) FROM gold.correlation_hourly")
        ).scalar()

    context.log.info(f"Last gold hour: {last_hour}")

    query = text("""
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
        df = pd.read_sql_query(query, conn, params={"last_hour": last_hour}, parse_dates=["time"])

    df["region_name"] = df["region_id"].map(REGION_NAMES)
    context.log.info(f"New demand hours: {len(df):,} rows | time range: {df['time'].min()} -> {df['time'].max()}")
    return df


@op(description="Load new weather data after last gold hour")
def load_new_weather_op(context) -> pd.DataFrame:
    engine = _get_db_engine()

    with engine.connect() as conn:
        last_hour = conn.execute(
            text("SELECT COALESCE(MAX(time), '1970-01-01T00:00:00Z'::TIMESTAMPTZ) FROM gold.correlation_hourly")
        ).scalar()

    context.log.info(f"Last gold hour: {last_hour}")

    query = text("""
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
        df = pd.read_sql_query(query, conn, params={"last_hour": last_hour}, parse_dates=["time"])

    df["region_name"] = df["region_id"].map(REGION_NAMES)
    context.log.info(f"New weather hours: {len(df):,} rows | time range: {df['time'].min()} -> {df['time'].max()}")
    return df


@op(description="Merge demand + weather into gold.correlation_hourly (append only)")
def merge_hourly_op(context, df_demand: pd.DataFrame, df_weather: pd.DataFrame) -> None:
    if df_demand.empty:
        context.log.info("No new demand data to merge")
        return

    df = df_demand.merge(
        df_weather,
        on=["time", "region_id", "region_name"],
        how="left",
    )

    # Fill missing weather from previous hour per region (forward fill)
    df = df.sort_values(["region_id", "time"]).reset_index(drop=True)
    weather_cols = [
        "temperature_2m", "relative_humidity_2m", "precipitation",
        "cloud_cover", "wind_speed_10m", "shortwave_radiation",
    ]
    for col in weather_cols:
        df[col] = df.groupby("region_id")[col].transform(lambda s: s.ffill())

    engine = _get_db_engine()
    with engine.connect() as conn:
        df.to_sql(
            "correlation_hourly",
            conn,
            schema="gold",
            if_exists="append",
            index=False,
            method="multi",
        )
        conn.commit()

    context.log.info(f"Appended {len(df):,} rows to gold.correlation_hourly")


@op(description="Aggregate gold hourly to daily, append only complete days")
def merge_daily_op(context) -> None:
    engine = _get_db_engine()

    with engine.connect() as conn:
        last_date = conn.execute(
            text("SELECT COALESCE(MAX(date), '1970-01-01'::DATE) FROM gold.correlation_daily")
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
        context.log.info("No complete daily data to aggregate yet")
        return

    with engine.begin() as conn:
        df.to_sql(
            "correlation_daily",
            conn,
            schema="gold",
            if_exists="append",
            index=False,
            method="multi",
        )

    context.log.info(f"Appended {len(df):,} rows to gold.correlation_daily (dates: {df['date'].min()} -> {df['date'].max()})")


@job(
    executor_def=in_process_executor,
    description="Incremental gold pipeline: silver.demand_5min + silver.weather_hourly → gold hourly & daily",
)
def build_gold_correlation() -> None:
    demand = load_new_demand_op()
    weather = load_new_weather_op()
    merge_hourly_op(demand, weather)
    merge_daily_op()
