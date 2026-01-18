"""WebSocket handler for L12 real-time event streaming.

This module provides WebSocket support for streaming real-time updates
about service execution, task progress, and system events to connected clients.
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Set

import redis.asyncio as aioredis
from fastapi import WebSocket, WebSocketDisconnect

from ..config.settings import get_settings

logger = logging.getLogger(__name__)


class WebSocketConnectionManager:
    """Manages WebSocket connections and event distribution."""

    def __init__(self):
        """Initialize the connection manager."""
        # Map session_id -> set of WebSocket connections
        self.active_connections: Dict[str, Set[WebSocket]] = {}
        # Global connections (receive all events)
        self.global_connections: Set[WebSocket] = set()
        self.redis: Optional[aioredis.Redis] = None
        self._pubsub_task: Optional[asyncio.Task] = None
        self._running = False

        logger.info("WebSocketConnectionManager initialized")

    async def start(self, redis_url: str = None):
        """Start the WebSocket manager and Redis pub/sub listener.

        Args:
            redis_url: Redis connection URL (defaults to settings)
        """
        if self._running:
            return

        settings = get_settings()
        redis_url = redis_url or f"redis://{settings.redis_host}:{settings.redis_port}"

        try:
            # Connect to Redis
            self.redis = await aioredis.from_url(redis_url, decode_responses=True)

            # Start pub/sub listener
            self._pubsub_task = asyncio.create_task(self._listen_to_events())
            self._running = True

            logger.info(f"WebSocketConnectionManager started (redis={redis_url})")

        except Exception as e:
            logger.error(f"Failed to start WebSocket manager: {e}", exc_info=True)
            raise

    async def stop(self):
        """Stop the WebSocket manager."""
        self._running = False

        # Cancel pub/sub task
        if self._pubsub_task:
            self._pubsub_task.cancel()
            try:
                await self._pubsub_task
            except asyncio.CancelledError:
                pass

        # Close Redis connection
        if self.redis:
            await self.redis.close()

        # Close all WebSocket connections
        for session_connections in self.active_connections.values():
            for connection in session_connections:
                await connection.close()

        for connection in self.global_connections:
            await connection.close()

        logger.info("WebSocketConnectionManager stopped")

    async def connect(
        self, websocket: WebSocket, session_id: Optional[str] = None
    ):
        """Accept and register a WebSocket connection.

        Args:
            websocket: WebSocket instance
            session_id: Optional session ID to filter events
        """
        await websocket.accept()

        if session_id:
            # Session-specific connection
            if session_id not in self.active_connections:
                self.active_connections[session_id] = set()
            self.active_connections[session_id].add(websocket)
            logger.info(f"WebSocket connected: session={session_id}")
        else:
            # Global connection (receives all events)
            self.global_connections.add(websocket)
            logger.info("WebSocket connected: global")

        # Send welcome message
        await self._send_to_connection(
            websocket,
            {
                "type": "connected",
                "session_id": session_id,
                "timestamp": datetime.utcnow().isoformat(),
                "message": "Connected to L12 event stream",
            },
        )

    def disconnect(self, websocket: WebSocket, session_id: Optional[str] = None):
        """Remove a WebSocket connection.

        Args:
            websocket: WebSocket instance
            session_id: Optional session ID
        """
        if session_id:
            if session_id in self.active_connections:
                self.active_connections[session_id].discard(websocket)
                if not self.active_connections[session_id]:
                    del self.active_connections[session_id]
            logger.info(f"WebSocket disconnected: session={session_id}")
        else:
            self.global_connections.discard(websocket)
            logger.info("WebSocket disconnected: global")

    async def broadcast_to_session(self, session_id: str, event: Dict):
        """Broadcast event to all connections for a specific session.

        Args:
            session_id: Session ID
            event: Event data to broadcast
        """
        if session_id not in self.active_connections:
            return

        connections = self.active_connections[session_id].copy()
        for connection in connections:
            await self._send_to_connection(connection, event)

    async def broadcast_global(self, event: Dict):
        """Broadcast event to all global connections.

        Args:
            event: Event data to broadcast
        """
        connections = self.global_connections.copy()
        for connection in connections:
            await self._send_to_connection(connection, event)

    async def _send_to_connection(self, websocket: WebSocket, event: Dict):
        """Send event to a single WebSocket connection.

        Args:
            websocket: WebSocket instance
            event: Event data
        """
        try:
            await websocket.send_json(event)
        except WebSocketDisconnect:
            # Connection closed, will be cleaned up
            pass
        except Exception as e:
            logger.error(f"Error sending to WebSocket: {e}")

    async def _listen_to_events(self):
        """Listen to Redis pub/sub events and distribute to connections."""
        if not self.redis:
            logger.error("Cannot listen to events: Redis not connected")
            return

        try:
            # Subscribe to L01 event channels
            pubsub = self.redis.pubsub()
            await pubsub.subscribe(
                "platform:events",  # General platform events
                "platform:services",  # Service execution events
                "platform:tasks",  # Task progress events
                "platform:agents",  # Agent lifecycle events
            )

            logger.info("Started listening to Redis pub/sub events")

            # Process messages
            async for message in pubsub.listen():
                if not self._running:
                    break

                if message["type"] != "message":
                    continue

                try:
                    # Parse event
                    event_data = json.loads(message["data"])

                    # Add metadata
                    event_data["channel"] = message["channel"]
                    event_data["timestamp"] = datetime.utcnow().isoformat()

                    # Extract session_id if present
                    session_id = event_data.get("session_id")

                    # Route event
                    if session_id:
                        # Send to session-specific connections
                        await self.broadcast_to_session(session_id, event_data)

                    # Always send to global connections
                    await self.broadcast_global(event_data)

                except json.JSONDecodeError:
                    logger.warning(f"Invalid JSON in event: {message['data']}")
                except Exception as e:
                    logger.error(f"Error processing event: {e}", exc_info=True)

        except asyncio.CancelledError:
            logger.info("Event listener cancelled")
            raise
        except Exception as e:
            logger.error(f"Event listener error: {e}", exc_info=True)
        finally:
            await pubsub.unsubscribe()
            await pubsub.close()


# Global manager instance
_manager: Optional[WebSocketConnectionManager] = None


def get_manager() -> WebSocketConnectionManager:
    """Get the global WebSocket connection manager.

    Returns:
        WebSocketConnectionManager instance
    """
    global _manager
    if _manager is None:
        _manager = WebSocketConnectionManager()
    return _manager
