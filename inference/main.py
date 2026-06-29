import asyncio
import logging
import signal
import threading
import time

from shared.logging import setup_json_logging

from . import metrics
from .config import REGIONS
from .models import load_models
from .nats_handler import run_nats_loop
from .predictor import run_inference_cycle
from .store import ensure_table

setup_json_logging("inference")
logger = logging.getLogger("inference")

_inference_busy = threading.Lock()


def _staleness_loop(stop_event: threading.Event) -> None:
    while not stop_event.is_set():
        now = time.time()
        for region_id in REGIONS:
            last_ts = metrics.last_demand_time.get(region_id)
            if last_ts is not None:
                staleness = now - last_ts
                metrics.push(
                    "demand_staleness_seconds",
                    staleness,
                    {"region": region_id},
                )
        stop_event.wait(timeout=30)


async def main() -> None:
    logger.info("Starting stream-inference service")

    ensure_table()

    models = load_models()
    logger.info("Loaded %d models: %s", len(models), list(models.keys()))

    async def on_trigger(trigger_time):
        if not _inference_busy.acquire(blocking=False):
            logger.warning("Previous inference still running, skipping")
            return
        try:
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(
                None, run_inference_cycle, models, trigger_time
            )
        finally:
            _inference_busy.release()

    stop_event = threading.Event()

    staleness_thread = threading.Thread(
        target=_staleness_loop, args=(stop_event,), daemon=True
    )
    staleness_thread.start()

    def _shutdown():
        logger.info("Received shutdown signal")
        stop_event.set()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, _shutdown)

    nats_task = asyncio.create_task(run_nats_loop(on_trigger))

    await _async_stop(stop_event, nats_task)


async def _async_stop(stop_event: threading.Event, nats_task) -> None:
    while not stop_event.is_set():
        await asyncio.sleep(0.5)
    nats_task.cancel()
    try:
        await nats_task
    except asyncio.CancelledError:
        pass
    logger.info("Service stopped")


if __name__ == "__main__":
    asyncio.run(main())
