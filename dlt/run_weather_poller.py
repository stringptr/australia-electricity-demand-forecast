import os
import time
import signal
import logging
from datetime import datetime

from shared.logging import setup_json_logging
from pipelines.weather_openmeteo import run_weather_pipeline
from utils.triggers import trigger_silver_assets

setup_json_logging("dlt-weather-poller")

logger = logging.getLogger(__name__)

POLL_INTERVAL = int(os.getenv("POLL_INTERVAL", "300"))

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
