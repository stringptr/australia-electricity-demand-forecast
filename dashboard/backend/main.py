import logging
import socket

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from shared.logging import setup_json_logging

from core.nats_manager import manager
from core.db import close_pool, get_pool
from core.duck import close_duck
from routers import demand, predictions, metrics, websocket, insight

setup_json_logging("dashboard-backend")
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await manager.start_nats_consumer()
    yield
    await manager.stop_nats_consumer()
    await close_pool()
    await close_duck()


app = FastAPI(title="VoltaicMap Backend", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(demand.router)
app.include_router(predictions.router)
app.include_router(metrics.router)
app.include_router(websocket.router)
app.include_router(insight.router)


def _check_postgres() -> bool:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(3)
        s.connect(("postgres", 5432))
        s.close()
        return True
    except Exception:
        return False


def _check_nats() -> bool:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(3)
        s.connect(("nats", 4222))
        s.close()
        return True
    except Exception:
        return False


@app.get("/health")
async def health_check():
    db_ok = _check_postgres()
    nats_ok = _check_nats()
    status = "ok" if (db_ok and nats_ok) else "degraded"
    return {
        "status": status,
        "db": db_ok,
        "nats": nats_ok,
    }
