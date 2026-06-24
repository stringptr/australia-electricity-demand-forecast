import logging

import pandas as pd
from sqlalchemy import create_engine, text

from .config import MAX_HORIZON, PG_DSN, REGIONS

logger = logging.getLogger(__name__)

COLUMNS_SQL = ", ".join(
    [f"horizon_h{h:02d} DOUBLE PRECISION" for h in range(1, MAX_HORIZON + 1)]
)

CREATE_TABLE_SQL = f"""
CREATE TABLE IF NOT EXISTS silver.predictions (
    id           BIGSERIAL PRIMARY KEY,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    region_id    TEXT NOT NULL,
    {COLUMNS_SQL},
    UNIQUE(created_at, region_id)
)
"""

INSERT_SQL = text(
    f"""
    INSERT INTO silver.predictions (created_at, region_id, {", ".join(
        f"horizon_h{h:02d}" for h in range(1, MAX_HORIZON + 1)
    )})
    VALUES (:created_at, :region_id, {", ".join(
        f":horizon_h{h:02d}" for h in range(1, MAX_HORIZON + 1)
    )})
    ON CONFLICT (created_at, region_id) DO NOTHING
"""
)


def ensure_table():
    engine = create_engine(PG_DSN)
    with engine.connect() as conn:
        conn.execute(text(CREATE_TABLE_SQL))
        conn.commit()
    engine.dispose()
    logger.info("Table silver.predictions ready")


def fetch_demand_history(current_time: pd.Timestamp, lookback_hours: int) -> pd.DataFrame:
    start = current_time - pd.Timedelta(hours=lookback_hours)
    query = text(
        "SELECT time, region_id, demand_mw, temperature_2m "
        "FROM silver.features_ml "
        "WHERE time >= :start AND time <= :end "
        "ORDER BY region_id, time"
    )
    engine = create_engine(PG_DSN)
    with engine.connect() as conn:
        df = pd.read_sql_query(
            query,
            conn,
            params={"start": start, "end": current_time},
            parse_dates=["time"],
        )
    engine.dispose()
    logger.info("History: %d rows [%s → %s]", len(df),
                df["time"].min() if not df.empty else "-",
                df["time"].max() if not df.empty else "-")
    return df


def store_predictions(
    predictions: dict[str, list[float]], created_at: pd.Timestamp
) -> int:
    engine = create_engine(PG_DSN)
    rows_inserted = 0

    with engine.connect() as conn:
        for region_id in REGIONS:
            pred = predictions.get(region_id)
            if not pred or len(pred) != MAX_HORIZON:
                logger.warning("Skipping %s: missing/invalid predictions", region_id)
                continue

            params = {"created_at": created_at, "region_id": region_id}
            for h in range(1, MAX_HORIZON + 1):
                params[f"horizon_h{h:02d}"] = float(pred[h - 1])

            result = conn.execute(INSERT_SQL, params)
            rows_inserted += result.rowcount

        conn.commit()

    engine.dispose()
    logger.info("Stored %d prediction rows at %s", rows_inserted, created_at)
    return rows_inserted
