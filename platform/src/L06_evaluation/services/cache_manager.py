"""Redis-based cache manager for scores, baselines, and query results"""

import asyncio
import json
import logging
from datetime import datetime, timedelta, UTC
from typing import Any, Optional

logger = logging.getLogger(__name__)


class CacheManager:
    """
    Redis-based caching for quality scores, baselines, and query results.

    Per spec Section 3.2 (Component Responsibilities #12):
    - Redis-based caching for scores, baselines, query results
    - TTL management (60s for scores, longer for baselines)
    - Cache miss handling
    """

    def __init__(
        self,
        redis_client: Optional[any] = None,
        default_ttl_seconds: int = 60,
    ):
        """
        Initialize cache manager.

        Args:
            redis_client: Redis client instance
            default_ttl_seconds: Default TTL for cache entries (default: 60s)
        """
        self.redis_client = redis_client
        self.default_ttl_seconds = default_ttl_seconds

        # In-memory fallback cache
        self._local_cache: dict[str, tuple[Any, datetime]] = {}

        # Statistics
        self.cache_hits = 0
        self.cache_misses = 0

    async def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache.

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found
        """
        try:
            # Try Redis first
            if self.redis_client:
                value = await self._get_from_redis(key)
                if value is not None:
                    self.cache_hits += 1
                    return value

            # Fallback to local cache
            value = self._get_from_local(key)
            if value is not None:
                self.cache_hits += 1
                return value

            self.cache_misses += 1
            return None

        except Exception as e:
            logger.error(f"Cache get failed for key {key}: {e}")
            self.cache_misses += 1
            return None

    async def set(
        self,
        key: str,
        value: Any,
        ttl_seconds: Optional[int] = None,
    ):
        """
        Set value in cache.

        Args:
            key: Cache key
            value: Value to cache (must be JSON serializable)
            ttl_seconds: Time-to-live in seconds (default: 60s)
        """
        ttl = ttl_seconds or self.default_ttl_seconds

        try:
            # Try Redis first
            if self.redis_client:
                await self._set_in_redis(key, value, ttl)
            else:
                # Fallback to local cache
                self._set_in_local(key, value, ttl)

        except Exception as e:
            logger.error(f"Cache set failed for key {key}: {e}")

    async def delete(self, key: str):
        """Delete key from cache"""
        try:
            if self.redis_client:
                await asyncio.to_thread(self.redis_client.delete, key)

            # Also delete from local cache
            self._local_cache.pop(key, None)

        except Exception as e:
            logger.error(f"Cache delete failed for key {key}: {e}")

    async def exists(self, key: str) -> bool:
        """Check if key exists in cache"""
        try:
            if self.redis_client:
                result = await asyncio.to_thread(self.redis_client.exists, key)
                return result > 0

            # Check local cache
            return key in self._local_cache

        except Exception as e:
            logger.error(f"Cache exists check failed for key {key}: {e}")
            return False

    async def clear(self, pattern: str = "*"):
        """
        Clear cache entries matching pattern.

        Args:
            pattern: Key pattern to match (default: all keys)
        """
        try:
            if self.redis_client:
                # Scan and delete matching keys
                cursor = 0
                while True:
                    cursor, keys = await asyncio.to_thread(
                        self.redis_client.scan,
                        cursor,
                        match=pattern,
                        count=100,
                    )
                    if keys:
                        await asyncio.to_thread(self.redis_client.delete, *keys)
                    if cursor == 0:
                        break

            # Clear local cache
            if pattern == "*":
                self._local_cache.clear()
            else:
                # Simple prefix matching for local cache
                prefix = pattern.rstrip("*")
                keys_to_delete = [k for k in self._local_cache.keys() if k.startswith(prefix)]
                for key in keys_to_delete:
                    del self._local_cache[key]

        except Exception as e:
            logger.error(f"Cache clear failed for pattern {pattern}: {e}")

    async def _get_from_redis(self, key: str) -> Optional[Any]:
        """Get value from Redis"""
        try:
            value_str = await asyncio.to_thread(self.redis_client.get, key)
            if value_str:
                return json.loads(value_str)
            return None
        except Exception as e:
            logger.warning(f"Redis get failed: {e}")
            return None

    async def _set_in_redis(self, key: str, value: Any, ttl: int):
        """Set value in Redis"""
        try:
            value_str = json.dumps(value, default=str)
            await asyncio.to_thread(
                self.redis_client.setex,
                key,
                ttl,
                value_str,
            )
        except Exception as e:
            logger.warning(f"Redis set failed: {e}")

    def _get_from_local(self, key: str) -> Optional[Any]:
        """Get value from local cache"""
        if key in self._local_cache:
            value, expiry = self._local_cache[key]
            if datetime.now(UTC) < expiry:
                return value
            else:
                # Expired, remove it
                del self._local_cache[key]
        return None

    def _set_in_local(self, key: str, value: Any, ttl: int):
        """Set value in local cache"""
        expiry = datetime.now(UTC) + timedelta(seconds=ttl)
        self._local_cache[key] = (value, expiry)

        # Cleanup old entries periodically
        if len(self._local_cache) > 1000:
            self._cleanup_local_cache()

    def _cleanup_local_cache(self):
        """Remove expired entries from local cache"""
        now = datetime.now(UTC)
        expired_keys = [
            key
            for key, (_, expiry) in self._local_cache.items()
            if now >= expiry
        ]
        for key in expired_keys:
            del self._local_cache[key]

    def get_statistics(self) -> dict:
        """Get cache statistics"""
        total_requests = self.cache_hits + self.cache_misses
        hit_rate = self.cache_hits / total_requests if total_requests > 0 else 0.0

        return {
            "cache_hits": self.cache_hits,
            "cache_misses": self.cache_misses,
            "hit_rate": hit_rate,
            "local_cache_size": len(self._local_cache),
        }

    def reset_statistics(self):
        """Reset statistics counters"""
        self.cache_hits = 0
        self.cache_misses = 0

    # Convenience methods for specific cache types

    async def get_quality_score(self, agent_id: str, timestamp: datetime) -> Optional[dict]:
        """Get cached quality score"""
        key = f"quality_score:{agent_id}:{timestamp.isoformat()}"
        return await self.get(key)

    async def set_quality_score(self, agent_id: str, timestamp: datetime, score: dict, ttl: int = 60):
        """Cache quality score (60s default TTL)"""
        key = f"quality_score:{agent_id}:{timestamp.isoformat()}"
        await self.set(key, score, ttl)

    async def get_baseline(self, metric_name: str) -> Optional[dict]:
        """Get cached baseline"""
        key = f"baseline:{metric_name}"
        return await self.get(key)

    async def set_baseline(self, metric_name: str, baseline: dict, ttl: int = 3600):
        """Cache baseline (1 hour default TTL)"""
        key = f"baseline:{metric_name}"
        await self.set(key, baseline, ttl)

    async def get_query_result(self, query_hash: str) -> Optional[dict]:
        """Get cached query result"""
        key = f"query:{query_hash}"
        return await self.get(key)

    async def set_query_result(self, query_hash: str, result: dict, ttl: int = 60):
        """Cache query result (60s default TTL)"""
        key = f"query:{query_hash}"
        await self.set(key, result, ttl)
