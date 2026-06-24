import json
import logging
import threading
from datetime import datetime, timezone

import nats

from .config import NATS_SUBJECT, NATS_URL

logger = logging.getLogger(__name__)


class InferenceTrigger:
    def __init__(self):
        self._last_hour = None
        self._lock = threading.Lock()

    def should_trigger(self, msg_time: datetime) -> bool:
        if msg_time.minute != 0:
            return False

        hour_key = msg_time.replace(minute=0, second=0, microsecond=0)

        with self._lock:
            if self._last_hour is None or hour_key > self._last_hour:
                self._last_hour = hour_key
                return True
        return False

    def reset_last_hour(self) -> None:
        with self._lock:
            self._last_hour = None


async def run_nats_loop(on_inference_trigger) -> None:
    nc = await nats.connect(NATS_URL)
    logger.info("Connected to NATS at %s", NATS_URL)

    trigger = InferenceTrigger()

    async def message_handler(msg):
        try:
            data = json.loads(msg.data)
        except json.JSONDecodeError:
            logger.warning("Invalid JSON in NATS message, skipping")
            return

        payload = data.get("payload", {})
        after = payload.get("after")
        if not after:
            return

        raw_time = after.get("time")
        if raw_time is None:
            return

        try:
            if isinstance(raw_time, (int, float)):
                msg_time = datetime.fromtimestamp(
                    raw_time / 1_000_000, tz=timezone.utc
                )
            else:
                msg_time = datetime.fromisoformat(str(raw_time))
        except (ValueError, TypeError, OverflowError):
            logger.warning("Invalid time in message: %s", raw_time)
            return

        if msg_time.tzinfo is None:
            msg_time = msg_time.replace(tzinfo=timezone.utc)

        if trigger.should_trigger(msg_time):
            logger.info("NATS trigger: inference at %s", msg_time)
            try:
                await on_inference_trigger(msg_time)
            except Exception:
                logger.exception("Inference cycle failed at %s", msg_time)
                trigger.reset_last_hour()

    js = nc.jetstream()
    await js.subscribe(NATS_SUBJECT, cb=message_handler)
    logger.info("Subscribed to %s — waiting for messages", NATS_SUBJECT)

    try:
        while True:
            await nc.flush()
            import asyncio
            await asyncio.sleep(0.5)
    except KeyboardInterrupt:
        logger.info("Shutting down NATS loop")
    finally:
        await nc.close()
