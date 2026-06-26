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
        """Subscribe to NATS JetStream and broadcast to all WS clients."""
        try:
            self.nats_client = await nats.connect(settings.NATS_URL)
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
            
            self.nats_subscription = await js.subscribe(
                settings.NATS_SUBJECT,
                cb=msg_handler,
                durable="dashboard-consumer",
                deliver_policy=nats.js.api.DeliverPolicy.ALL
            )
            logger.info("Subscribed to NATS subject: %s", settings.NATS_SUBJECT)
        except Exception as e:
            logger.error("Failed to start NATS consumer: %s", e)
            raise
    
    async def stop_nats_consumer(self):
        if self.nats_subscription:
            await self.nats_subscription.unsubscribe()
        if self.nats_client:
            await self.nats_client.close()
        logger.info("NATS consumer stopped")

manager = ConnectionManager()