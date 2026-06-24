import asyncio
import logging
import signal
import threading

from .models import load_models
from .nats_handler import run_nats_loop
from .predictor import run_inference_cycle
from .store import ensure_table

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("inference")

_inference_busy = threading.Lock()


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

    stop_event = asyncio.Event()

    def _shutdown():
        logger.info("Received shutdown signal")
        stop_event.set()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, _shutdown)

    nats_task = asyncio.create_task(run_nats_loop(on_trigger))

    await stop_event.wait()
    nats_task.cancel()
    try:
        await nats_task
    except asyncio.CancelledError:
        pass
    logger.info("Service stopped")


if __name__ == "__main__":
    asyncio.run(main())
