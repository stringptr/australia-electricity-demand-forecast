import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from shared.logging import setup_json_logging

from core.nats_manager import manager
from core.db import close_pool
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


@app.get("/health")
async def health_check():
    return {"status": "ok"}
