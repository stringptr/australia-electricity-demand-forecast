import asyncio
import json
import logging
from typing import List

from fastapi import WebSocket
import nats
from nats.aio.client import Client as NATS
from nats.aio.subscription import Subscription

from core.config import settings

logger = logging.getLogger(__name__)

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.nats_client: NATS | None = None
        self.nats_subscription: Subscription | None = None
        self._lock = asyncio.Lock()
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        async with self._lock:
            self.active_connections.append(websocket)
        logger.info("WebSocket client connected. Total: %d", len(self.active_connections))
    
    async def disconnect(self, websocket: WebSocket):
        async with self._lock:
            if websocket in self.active_connections:
                self.active_connections.remove(websocket)
        logger.info("WebSocket client disconnected. Total: %d", len(self.active_connections))
    
    async def broadcast(self, message: dict):
        if not self.active_connections:
            return
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                disconnected.append(connection)
        
        if disconnected:
            async with self._lock:
                for conn in disconnected:
                    if conn in self.active_connections:
                        self.active_connections.remove(conn)
    
    async def start_nats_consumer(self):
        """Subscribe to NATS JetStream and broadcast to all WS clients.
        Does not raise on failure — retries in background so the app stays up."""
        try:
            self.nats_client = await nats.connect(settings.NATS_URL)
        except Exception as e:
            logger.warning("Cannot connect to NATS (%s). Will retry in background.", e)
            asyncio.create_task(self._retry_connect())
            return

        js = self.nats_client.jetstream()

        async def msg_handler(msg):
            try:
                data = json.loads(msg.data)
                payload = data.get("payload", {}).get("after", {})
                if not payload:
                    await msg.ack()
                    return

                region_id = payload.get("region_id")
                demand_mw = payload.get("demand_mw")
                raw_time = payload.get("time")

                if not region_id or demand_mw is None:
                    await msg.ack()
                    return

                await self.broadcast({
                    "type": "demand_update",
                    "timestamp": raw_time,
                    "region_id": region_id,
                    "demand_mw": float(demand_mw)
                })
                await msg.ack()
            except Exception as e:
                logger.error("Error handling NATS message: %s", e)
                await msg.nak()

        try:
            self.nats_subscription = await js.subscribe(
                settings.NATS_SUBJECT,
                cb=msg_handler,
                durable="dashboard-consumer",
                deliver_policy=nats.js.api.DeliverPolicy.NEW
            )
            logger.info("Subscribed to NATS subject: %s", settings.NATS_SUBJECT)
        except nats.js.errors.NotFoundError:
            logger.warning("NATS stream not found yet. Will retry in background.")
            asyncio.create_task(self._retry_subscribe(js, msg_handler))
        except Exception as e:
            logger.warning("NATS subscribe failed (%s). Will retry in background.", e)
            asyncio.create_task(self._retry_connect())

    async def _retry_connect(self):
        await asyncio.sleep(30)
        try:
            await self.start_nats_consumer()
        except Exception:
            logger.warning("NATS reconnect failed, scheduling another attempt.")
            asyncio.create_task(self._retry_connect())

    async def _retry_subscribe(self, js, msg_handler):
        await asyncio.sleep(30)
        try:
            self.nats_subscription = await js.subscribe(
                settings.NATS_SUBJECT,
                cb=msg_handler,
                durable="dashboard-consumer",
                deliver_policy=nats.js.api.DeliverPolicy.NEW
            )
            logger.info("Subscribed to NATS subject (on retry): %s", settings.NATS_SUBJECT)
        except nats.js.errors.NotFoundError:
            logger.warning("NATS stream still not found. Will retry again.")
            asyncio.create_task(self._retry_subscribe(js, msg_handler))
        except Exception:
            logger.warning("NATS subscribe failed on retry. Reconnecting from scratch.")
            asyncio.create_task(self._retry_connect())
    
    async def stop_nats_consumer(self):
        if self.nats_subscription:
            await self.nats_subscription.unsubscribe()
        if self.nats_client:
            await self.nats_client.close()
        logger.info("NATS consumer stopped")

manager = ConnectionManager()
