"""
Redis client for event publishing and caching.
"""

import redis.asyncio as redis
import json
import logging
from typing import Optional, Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)


class RedisClient:
    """Redis client with event publishing support."""

    def __init__(self, host: str = "localhost", port: int = 6379, db: int = 0):
        self.host = host
        self.port = port
        self.db = db
        self.client: Optional[redis.Redis] = None

    async def connect(self):
        """Create Redis connection."""
        if self.client is None:
            try:
                self.client = await redis.from_url(
                    f"redis://{self.host}:{self.port}/{self.db}",
                    encoding="utf-8",
                    decode_responses=True
                )
                await self.client.ping()
                logger.info(f"Connected to Redis at {self.host}:{self.port}")
            except Exception as e:
                logger.error(f"Failed to connect to Redis: {e}")
                raise

    async def disconnect(self):
        """Close Redis connection."""
        if self.client:
            await self.client.close()
            self.client = None
            logger.info("Redis connection closed")

    async def publish_event(self, event_type: str, aggregate_type: str,
                          aggregate_id: str, payload: Dict[Any, Any],
                          metadata: Optional[Dict[Any, Any]] = None):
        """
        Publish an event to the l01:events channel.

        Args:
            event_type: Type of event (e.g., "agent.spawned")
            aggregate_type: Entity type (e.g., "agent")
            aggregate_id: Entity ID
            payload: Event data
            metadata: Optional metadata
        """
        if not self.client:
            logger.warning("Redis not connected, skipping event publish")
            return

        event = {
            "event_type": event_type,
            "aggregate_type": aggregate_type,
            "aggregate_id": aggregate_id,
            "payload": payload,
            "metadata": metadata or {},
            "timestamp": datetime.utcnow().isoformat()
        }

        try:
            await self.client.publish("l01:events", json.dumps(event))
            logger.debug(f"Published event: {event_type}")
        except Exception as e:
            logger.error(f"Failed to publish event {event_type}: {e}")

    async def health_check(self) -> bool:
        """Check Redis connectivity."""
        if not self.client:
            return False

        try:
            await self.client.ping()
            return True
        except Exception as e:
            logger.error(f"Redis health check failed: {e}")
            return False


# Global Redis instance
import os

# Read from environment variables
_redis_host = os.getenv("REDIS_HOST", "localhost")
_redis_port = int(os.getenv("REDIS_PORT", "6379"))
_redis_db = int(os.getenv("REDIS_DB", "0"))

# Parse REDIS_URL if provided (overrides individual vars)
_redis_url = os.getenv("REDIS_URL")
if _redis_url:
    # Parse redis://host:port/db
    import re
    match = re.match(r'redis://([^:]+):(\d+)(?:/(\d+))?', _redis_url)
    if match:
        _redis_host = match.group(1)
        _redis_port = int(match.group(2))
        if match.group(3):
            _redis_db = int(match.group(3))

redis_client = RedisClient(host=_redis_host, port=_redis_port, db=_redis_db)
