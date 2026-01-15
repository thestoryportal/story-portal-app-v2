"""
Result Cache Service

Caches tool execution results in Redis with TTL-based invalidation.
Based on Section 3 architecture with Redis 7 backend.

Features:
- Result caching with configurable TTL
- Cache key generation with idempotency support
- Cache invalidation strategies
- Metrics for cache hit/miss rates
"""

import asyncio
import logging
import json
import hashlib
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
import redis.asyncio as redis

from ..models import (
    ToolInvokeRequest,
    ToolResult,
    ErrorCode,
    ToolExecutionError,
)

logger = logging.getLogger(__name__)


class ResultCache:
    """
    Redis-backed result cache for tool executions.

    Caches tool results with idempotency key support and TTL expiration.
    """

    def __init__(
        self,
        redis_url: str = "redis://localhost:6379",
        default_ttl_seconds: int = 300,  # 5 minutes
        key_prefix: str = "tool:result:",
    ):
        """
        Initialize Result Cache.

        Args:
            redis_url: Redis connection URL
            default_ttl_seconds: Default cache TTL (seconds)
            key_prefix: Cache key prefix
        """
        self.redis_url = redis_url
        self.default_ttl_seconds = default_ttl_seconds
        self.key_prefix = key_prefix
        self.redis_client: Optional[redis.Redis] = None

    async def initialize(self):
        """Initialize Redis connection"""
        try:
            self.redis_client = await redis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True,
            )
            await self.redis_client.ping()
            logger.info("Result Cache initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Result Cache: {e}")
            raise ToolExecutionError(
                ErrorCode.E3503,
                message="Failed to initialize result cache",
                details={"error": str(e)}
            )

    async def close(self):
        """Close Redis connection"""
        if self.redis_client:
            await self.redis_client.close()
            logger.info("Result Cache closed")

    def _generate_cache_key(self, request: ToolInvokeRequest) -> str:
        """
        Generate cache key for tool invocation.

        Uses idempotency_key if provided, otherwise generates from parameters.

        Args:
            request: Tool invocation request

        Returns:
            Cache key string
        """
        # Use idempotency key if provided
        if request.execution_options and request.execution_options.idempotency_key:
            return f"{self.key_prefix}{request.execution_options.idempotency_key}"

        # Generate key from tool_id, version, and parameters
        key_components = {
            "tool_id": request.tool_id,
            "tool_version": request.tool_version or "latest",
            "parameters": request.parameters,
        }

        # Create deterministic hash
        key_json = json.dumps(key_components, sort_keys=True)
        key_hash = hashlib.sha256(key_json.encode()).hexdigest()[:16]

        return f"{self.key_prefix}{request.tool_id}:{key_hash}"

    async def get(self, request: ToolInvokeRequest) -> Optional[ToolResult]:
        """
        Retrieve cached result for tool invocation.

        Args:
            request: Tool invocation request

        Returns:
            Cached ToolResult or None if not found
        """
        try:
            cache_key = self._generate_cache_key(request)
            cached_data = await self.redis_client.get(cache_key)

            if cached_data:
                data = json.loads(cached_data)
                logger.info(f"Cache HIT for {cache_key}")
                return ToolResult(
                    result=data["result"],
                    result_type=data.get("result_type", "object")
                )

            logger.debug(f"Cache MISS for {cache_key}")
            return None

        except Exception as e:
            logger.error(f"Cache retrieval error: {e}")
            # Don't fail on cache errors, just return None
            return None

    async def set(
        self,
        request: ToolInvokeRequest,
        result: ToolResult,
        ttl_seconds: Optional[int] = None
    ):
        """
        Store tool execution result in cache.

        Args:
            request: Tool invocation request
            result: Tool execution result
            ttl_seconds: Cache TTL (seconds), uses default if None
        """
        try:
            cache_key = self._generate_cache_key(request)
            ttl = ttl_seconds or self.default_ttl_seconds

            cache_data = {
                "result": result.result,
                "result_type": result.result_type,
                "cached_at": datetime.utcnow().isoformat(),
            }

            await self.redis_client.setex(
                cache_key,
                ttl,
                json.dumps(cache_data)
            )

            logger.info(f"Cached result for {cache_key} (TTL: {ttl}s)")

        except Exception as e:
            logger.error(f"Cache storage error: {e}")
            # Don't fail on cache errors

    async def invalidate(self, request: ToolInvokeRequest):
        """
        Invalidate cached result for tool invocation.

        Args:
            request: Tool invocation request
        """
        try:
            cache_key = self._generate_cache_key(request)
            await self.redis_client.delete(cache_key)
            logger.info(f"Invalidated cache for {cache_key}")

        except Exception as e:
            logger.error(f"Cache invalidation error: {e}")

    async def invalidate_tool(self, tool_id: str):
        """
        Invalidate all cached results for a specific tool.

        Useful when tool is updated or deprecated.

        Args:
            tool_id: Tool identifier
        """
        try:
            pattern = f"{self.key_prefix}{tool_id}:*"
            keys = []

            # Scan for matching keys
            async for key in self.redis_client.scan_iter(match=pattern, count=100):
                keys.append(key)

            # Delete in batch
            if keys:
                await self.redis_client.delete(*keys)
                logger.info(f"Invalidated {len(keys)} cache entries for tool {tool_id}")

        except Exception as e:
            logger.error(f"Tool cache invalidation error: {e}")

    async def clear_all(self):
        """Clear all cached results"""
        try:
            pattern = f"{self.key_prefix}*"
            keys = []

            async for key in self.redis_client.scan_iter(match=pattern, count=100):
                keys.append(key)

            if keys:
                await self.redis_client.delete(*keys)
                logger.info(f"Cleared {len(keys)} cache entries")

        except Exception as e:
            logger.error(f"Cache clear error: {e}")

    async def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.

        Returns:
            Dictionary with cache stats
        """
        try:
            # Count cached entries
            pattern = f"{self.key_prefix}*"
            count = 0

            async for _ in self.redis_client.scan_iter(match=pattern, count=100):
                count += 1

            # Get Redis info
            info = await self.redis_client.info("stats")

            return {
                "cached_entries": count,
                "redis_hits": info.get("keyspace_hits", 0),
                "redis_misses": info.get("keyspace_misses", 0),
            }

        except Exception as e:
            logger.error(f"Failed to get cache stats: {e}")
            return {}
