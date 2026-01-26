"""Infrastructure Services for Platform.

Provides database and Redis connection pools for service dependency injection.
These are L00 infrastructure services used by higher layers.
"""

import os
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


class DatabasePool:
    """PostgreSQL connection pool provider.

    Provides async connection pool for database operations.
    Supports environment-based configuration and graceful fallback.
    """

    def __init__(
        self,
        connection_string: Optional[str] = None,
        min_size: int = 2,
        max_size: int = 10,
    ):
        """Initialize database pool.

        Args:
            connection_string: PostgreSQL connection string (or from env)
            min_size: Minimum pool connections
            max_size: Maximum pool connections
        """
        self.connection_string = connection_string or os.environ.get(
            "DATABASE_URL",
            "postgresql://postgres:postgres@localhost:5432/platform"
        )
        self.min_size = min_size
        self.max_size = max_size
        self._pool = None
        self._mock_mode = os.environ.get("MOCK_INFRASTRUCTURE", "false").lower() == "true"

    async def initialize(self) -> None:
        """Initialize the connection pool."""
        if self._mock_mode:
            logger.info("DatabasePool initialized in MOCK mode")
            return

        try:
            import asyncpg
            self._pool = await asyncpg.create_pool(
                self.connection_string,
                min_size=self.min_size,
                max_size=self.max_size,
            )
            logger.info(f"DatabasePool initialized (min={self.min_size}, max={self.max_size})")
        except ImportError:
            logger.warning("asyncpg not installed, running in mock mode")
            self._mock_mode = True
        except Exception as e:
            logger.error(f"Failed to create database pool: {e}")
            self._mock_mode = True

    async def acquire(self):
        """Acquire a connection from the pool."""
        if self._mock_mode or self._pool is None:
            return MockConnection()
        return await self._pool.acquire()

    async def release(self, conn) -> None:
        """Release a connection back to the pool."""
        if self._pool and not self._mock_mode:
            await self._pool.release(conn)

    async def close(self) -> None:
        """Close the connection pool."""
        if self._pool:
            await self._pool.close()
            logger.info("DatabasePool closed")

    @property
    def pool(self):
        """Get the underlying pool (for direct access)."""
        return self._pool if not self._mock_mode else MockPool()


class RedisPool:
    """Redis connection pool provider.

    Provides Redis client for caching and pub/sub operations.
    Supports environment-based configuration and graceful fallback.
    """

    def __init__(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        db: int = 0,
        decode_responses: bool = True,
    ):
        """Initialize Redis pool.

        Args:
            host: Redis host (or from env)
            port: Redis port (or from env)
            db: Redis database number
            decode_responses: Whether to decode responses to strings
        """
        self.host = host or os.environ.get("REDIS_HOST", "localhost")
        self.port = port or int(os.environ.get("REDIS_PORT", "6379"))
        self.db = db
        self.decode_responses = decode_responses
        self._client = None
        self._mock_mode = os.environ.get("MOCK_INFRASTRUCTURE", "false").lower() == "true"

    async def initialize(self) -> None:
        """Initialize the Redis client."""
        if self._mock_mode:
            logger.info("RedisPool initialized in MOCK mode")
            return

        try:
            import redis.asyncio as redis
            self._client = redis.Redis(
                host=self.host,
                port=self.port,
                db=self.db,
                decode_responses=self.decode_responses,
            )
            # Test connection
            await self._client.ping()
            logger.info(f"RedisPool initialized ({self.host}:{self.port})")
        except ImportError:
            logger.warning("redis package not installed, running in mock mode")
            self._mock_mode = True
        except Exception as e:
            logger.warning(f"Failed to connect to Redis: {e}, running in mock mode")
            self._mock_mode = True

    async def get(self, key: str) -> Optional[str]:
        """Get a value from Redis."""
        if self._mock_mode or self._client is None:
            return None
        return await self._client.get(key)

    async def set(self, key: str, value: str, ex: Optional[int] = None) -> bool:
        """Set a value in Redis."""
        if self._mock_mode or self._client is None:
            return True
        return await self._client.set(key, value, ex=ex)

    async def delete(self, key: str) -> int:
        """Delete a key from Redis."""
        if self._mock_mode or self._client is None:
            return 0
        return await self._client.delete(key)

    async def close(self) -> None:
        """Close the Redis connection."""
        if self._client:
            await self._client.close()
            logger.info("RedisPool closed")

    @property
    def client(self):
        """Get the underlying Redis client."""
        return self._client if not self._mock_mode else MockRedis()


class MockConnection:
    """Mock database connection for testing/fallback."""

    async def fetch(self, query: str, *args) -> list:
        return []

    async def fetchrow(self, query: str, *args) -> Optional[Dict]:
        return None

    async def execute(self, query: str, *args) -> str:
        return "MOCK"

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        pass


class MockPool:
    """Mock connection pool for testing/fallback."""

    async def acquire(self):
        return MockConnection()

    async def release(self, conn):
        pass


class MockRedis:
    """Mock Redis client for testing/fallback."""

    _store: Dict[str, str] = {}

    async def get(self, key: str) -> Optional[str]:
        return self._store.get(key)

    async def set(self, key: str, value: str, ex: Optional[int] = None) -> bool:
        self._store[key] = value
        return True

    async def delete(self, key: str) -> int:
        if key in self._store:
            del self._store[key]
            return 1
        return 0

    async def ping(self) -> bool:
        return True
