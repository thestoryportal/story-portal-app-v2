"""
L10 Human Interface Layer - WebSocket Gateway

Manages WebSocket connections and broadcasts events.
"""

import json
import logging
import asyncio
from datetime import datetime, UTC
from typing import Dict, Set
from dataclasses import dataclass
from collections import defaultdict
import redis.asyncio as redis

logger = logging.getLogger(__name__)


@dataclass
class WebSocketConnection:
    """Represents a single WebSocket connection."""
    websocket: any  # FastAPI WebSocket
    connection_id: str
    tenant_id: str
    subscriptions: Set[str]
    connected_at: datetime


class WebSocketGateway:
    """
    WebSocket gateway for real-time updates.

    Features:
    - In-memory connection registry
    - Redis pub/sub for multi-instance broadcasting
    - Topic-based subscriptions
    - Heartbeat ping/pong
    """

    def __init__(self, event_bus=None, redis_client: redis.Redis = None):
        self.event_bus = event_bus
        self.redis = redis_client
        self._connections: Dict[str, WebSocketConnection] = {}
        self._topic_subscribers: Dict[str, Set[str]] = defaultdict(set)
        self._lock = asyncio.Lock()
        self._broadcast_channel = "l10:websocket:broadcast"
        self._pubsub_task = None

    async def start(self):
        """Start WebSocket gateway."""
        if self.redis:
            self._pubsub_task = asyncio.create_task(self._listen_broadcast_channel())
        logger.info("WebSocket gateway started")

    async def stop(self):
        """Stop WebSocket gateway."""
        async with self._lock:
            for conn in list(self._connections.values()):
                try:
                    await conn.websocket.close()
                except:
                    pass
            self._connections.clear()

        if self._pubsub_task:
            self._pubsub_task.cancel()
        logger.info("WebSocket gateway stopped")

    async def handle_connection(self, websocket, connection_id: str, tenant_id: str):
        """Handle WebSocket connection lifecycle."""
        await websocket.accept()

        conn = WebSocketConnection(
            websocket=websocket,
            connection_id=connection_id,
            tenant_id=tenant_id,
            subscriptions=set(),
            connected_at=datetime.now(UTC),
        )

        async with self._lock:
            self._connections[connection_id] = conn

        logger.info(f"WebSocket connected: {connection_id}")

        try:
            await conn.websocket.send_json({
                "type": "connected",
                "connection_id": connection_id,
                "timestamp": datetime.now(UTC).isoformat(),
            })

            while True:
                message = await websocket.receive_json()
                await self._handle_client_message(conn, message)

        except Exception as e:
            logger.info(f"WebSocket disconnected: {connection_id} - {e}")
        finally:
            await self._unregister_connection(connection_id)

    async def _handle_client_message(self, conn: WebSocketConnection, message: dict):
        """Handle message from client."""
        msg_type = message.get("type")

        if msg_type == "subscribe":
            topics = message.get("topics", [])
            await self._subscribe_connection(conn, topics)
            await conn.websocket.send_json({"type": "subscribed", "topics": topics})

        elif msg_type == "unsubscribe":
            topics = message.get("topics", [])
            await self._unsubscribe_connection(conn, topics)
            await conn.websocket.send_json({"type": "unsubscribed", "topics": topics})

        elif msg_type == "ping":
            await conn.websocket.send_json({"type": "pong", "timestamp": datetime.now(UTC).isoformat()})

    async def _subscribe_connection(self, conn: WebSocketConnection, topics: list):
        """Subscribe connection to topics."""
        async with self._lock:
            for topic in topics:
                conn.subscriptions.add(topic)
                self._topic_subscribers[topic].add(conn.connection_id)

    async def _unsubscribe_connection(self, conn: WebSocketConnection, topics: list):
        """Unsubscribe connection from topics."""
        async with self._lock:
            for topic in topics:
                conn.subscriptions.discard(topic)
                self._topic_subscribers[topic].discard(conn.connection_id)

    async def _unregister_connection(self, connection_id: str):
        """Unregister connection."""
        async with self._lock:
            if connection_id in self._connections:
                conn = self._connections.pop(connection_id)
                for topic in conn.subscriptions:
                    self._topic_subscribers[topic].discard(connection_id)

    async def broadcast_event(self, topic: str, event_data: dict):
        """Broadcast event to all subscribers."""
        if self.redis:
            broadcast_msg = {"topic": topic, "event": event_data, "timestamp": datetime.now(UTC).isoformat()}
            await self.redis.publish(self._broadcast_channel, json.dumps(broadcast_msg))

        await self._broadcast_locally(topic, event_data)

    async def _broadcast_locally(self, topic: str, event_data: dict):
        """Broadcast to local connections."""
        async with self._lock:
            subscriber_ids = self._topic_subscribers.get(topic, set()).copy()

        for conn_id in subscriber_ids:
            conn = self._connections.get(conn_id)
            if conn:
                asyncio.create_task(self._send_to_connection(conn, topic, event_data))

    async def _send_to_connection(self, conn: WebSocketConnection, topic: str, event_data: dict):
        """Send event to specific connection."""
        try:
            await conn.websocket.send_json({
                "type": "event",
                "topic": topic,
                "data": event_data,
                "timestamp": datetime.now(UTC).isoformat(),
            })
        except Exception as e:
            logger.error(f"Failed to send to {conn.connection_id}: {e}")
            await self._unregister_connection(conn.connection_id)

    async def _listen_broadcast_channel(self):
        """Listen for broadcast messages from other instances."""
        if not self.redis:
            return

        pubsub = self.redis.pubsub()
        await pubsub.subscribe(self._broadcast_channel)

        try:
            async for message in pubsub.listen():
                if message["type"] == "message":
                    data = json.loads(message["data"])
                    await self._broadcast_locally(data["topic"], data["event"])
        except asyncio.CancelledError:
            await pubsub.unsubscribe()
            await pubsub.aclose()
