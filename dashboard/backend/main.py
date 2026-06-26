from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from core.nats_manager import manager
from core.db import close_pool
from routers import demand, predictions, metrics, websocket

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await manager.start_nats_consumer()
    yield
    # Shutdown
    await manager.stop_nats_consumer()
    await close_pool()

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

@app.get("/health")
async def health_check():
    return {"status": "ok"}