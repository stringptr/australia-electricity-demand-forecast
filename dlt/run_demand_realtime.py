import time
import logging
import signal

from pipelines.demand_aemo_realtime import run_realtime_pipeline

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)

logger = logging.getLogger(__name__)

NORMAL_INTERVAL = 300
RETRY_INTERVAL = 30
DAILY_LIMIT = 500

running = True


def _signal_handler(sig, frame):
    global running
    logger.info("Signal %s received, shutting down gracefully", sig)
    running = False


signal.signal(signal.SIGINT, _signal_handler)
signal.signal(signal.SIGTERM, _signal_handler)


def main() -> None:
    next_fetch_at = time.time()
    daily_req = 0
    last_reset_day = time.localtime().tm_yday

    logger.info("START: Open Electricity real-time scraper (daily limit: %d)", DAILY_LIMIT)

    while running:
        now = time.time()

        if time.localtime().tm_yday != last_reset_day:
            daily_req = 0
            last_reset_day = time.localtime().tm_yday
            logger.info("Daily request counter reset")

        if daily_req >= DAILY_LIMIT:
            logger.warning("Daily limit reached (%d/%d), sleeping 10min", daily_req, DAILY_LIMIT)
            time.sleep(600)
            continue

        if now < next_fetch_at:
            time.sleep(min(next_fetch_at - now, 10))
            continue

        daily_req += 1
        logger.info("FETCH (req #%d today) ...", daily_req)

        try:
            has_new = run_realtime_pipeline()
        except Exception:
            logger.exception("Pipeline error")
            next_fetch_at = time.time() + NORMAL_INTERVAL
            continue

        if has_new:
            logger.info("DATA OK: reset to %ds schedule", NORMAL_INTERVAL)
            next_fetch_at = time.time() + NORMAL_INTERVAL
        else:
            retry_deadline = time.time() + NORMAL_INTERVAL
            while time.time() < retry_deadline:
                if daily_req >= DAILY_LIMIT or not running:
                    break

                retry_in = min(RETRY_INTERVAL, retry_deadline - time.time())
                logger.info("RETRY in %ds (window: %ds left, req #%d today)",
                            retry_in, retry_deadline - time.time(), daily_req + 1)
                time.sleep(retry_in)

                daily_req += 1
                logger.info("RETRY FETCH (req #%d today) ...", daily_req)

                try:
                    has_new = run_realtime_pipeline()
                except Exception:
                    logger.exception("Pipeline error")
                    break

                if has_new:
                    logger.info("DATA FOUND during retry")
                    break

            next_fetch_at = time.time() + NORMAL_INTERVAL

    logger.info("Scraper stopped after %d requests today", daily_req)


if __name__ == "__main__":
    main()
