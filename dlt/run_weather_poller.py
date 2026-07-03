import os
import time
import signal
import logging
from datetime import datetime

from sqlalchemy import create_engine, text

from shared.logging import setup_json_logging
from pipelines.weather_openmeteo import run_weather_pipeline
from utils.triggers import trigger_silver_assets

setup_json_logging("dlt-weather-poller")

logger = logging.getLogger(__name__)

POLL_INTERVAL = int(os.getenv("POLL_INTERVAL", "300"))


def _is_backfill_complete() -> bool:
    try:
        host = os.environ.get("PG_HOST", os.environ.get("POSTGRES_HOST", "postgres"))
        port = os.environ.get("PG_PORT", os.environ.get("POSTGRES_PORT", "5432"))
        user = os.environ.get("PG_USER", os.environ.get("POSTGRES_USER", "postgres"))
        password = os.environ.get("PG_PASSWORD", os.environ.get("POSTGRES_PASSWORD", "postgres"))
        db = os.environ.get("PG_DB", os.environ.get("POSTGRES_DB", "electricity"))
        engine = create_engine(f"postgresql://{user}:{password}@{host}:{port}/{db}")
        with engine.connect() as conn:
            row = conn.execute(text("SELECT MIN(time), MAX(time) FROM bronze.weather")).one()
            min_time, max_time = row
            if min_time is None or max_time is None:
                return False
            span = max_time - min_time
            return span.days >= 28
    except Exception:
        return False

running = True


def _signal_handler(sig, frame):
    global running
    logger.info("Signal %s received, shutting down", sig)
    running = False


signal.signal(signal.SIGINT, _signal_handler)
signal.signal(signal.SIGTERM, _signal_handler)


def main() -> None:
    logger.info("START: Open-Meteo weather poller (interval: %ds)", POLL_INTERVAL)

    while running:
        if not _is_backfill_complete():
            logger.info("Waiting for historical backfill (< 1 month data in bronze.weather) ...")
            time.sleep(POLL_INTERVAL)
            continue

        now = datetime.utcnow()

        try:
            rows = run_weather_pipeline(now.year)
        except Exception:
            logger.exception("Pipeline error")
            time.sleep(POLL_INTERVAL)
            continue

        if rows:
            logger.info("OK: %d new rows", rows)
            trigger_silver_assets()
        else:
            logger.info("No new data yet")

        time.sleep(POLL_INTERVAL)

    logger.info("Weather poller stopped")


if __name__ == "__main__":
    main()
