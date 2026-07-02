import os
import time
import signal
import logging

from shared.logging import setup_json_logging
from pipelines.demand_nemweb import run_nemweb_pipeline
from utils.triggers import trigger_silver_assets

setup_json_logging("dlt-demand-nemweb")

logger = logging.getLogger(__name__)

POLL_INTERVAL = os.getenv("POLL_INTERVAL", 30)

running = True


def _signal_handler(sig, frame):
    global running
    logger.info("Signal %s received, shutting down", sig)
    running = False


signal.signal(signal.SIGINT, _signal_handler)
signal.signal(signal.SIGTERM, _signal_handler)


def main() -> None:
    daily_req = 0
    last_reset_day = time.localtime().tm_yday

    logger.info("START: NEMWEB DispatchIS scraper (daily limit: %d)")

    while running:
        now = time.time()

        if time.localtime().tm_yday != last_reset_day:
            daily_req = 0
            last_reset_day = time.localtime().tm_yday
            logger.info("Daily request counter reset")

        daily_req += 1
        logger.info("FETCH (req #%d today) ...", daily_req)

        try:
            rows = run_nemweb_pipeline()
        except Exception:
            logger.exception("Pipeline error")
            time.sleep(POLL_INTERVAL)
            continue

        if rows:
            logger.info("OK: %d new rows", len(rows))
            trigger_silver_assets()
        else:
            logger.info("No new data yet")

        time.sleep(POLL_INTERVAL)

    logger.info("NEMWEB scraper stopped after %d requests", daily_req)


if __name__ == "__main__":
    main()
