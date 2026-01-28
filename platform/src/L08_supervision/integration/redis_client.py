"""
L08 Supervision Layer - Redis Rate Limiter

Redis-based rate limiting with token bucket algorithm and Lua scripts
for atomic Compare-And-Set (CAS) operations.
"""

import time
import logging
from typing import Optional, Tuple, Dict, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)


# Redis Lua script for atomic token bucket rate limiting
TOKEN_BUCKET_SCRIPT = """
local key = KEYS[1]
local requested = tonumber(ARGV[1])
local max_tokens = tonumber(ARGV[2])
local refill_rate = tonumber(ARGV[3])
local now = tonumber(ARGV[4])

local data = redis.call('HGETALL', key)
local tokens = max_tokens
local last_update = now

if #data > 0 then
    for i = 1, #data, 2 do
        if data[i] == 'tokens' then
            tokens = tonumber(data[i + 1])
        elseif data[i] == 'last_update' then
            last_update = tonumber(data[i + 1])
        end
    end

    -- Refill tokens based on elapsed time
    local elapsed = now - last_update
    tokens = math.min(max_tokens, tokens + (elapsed * refill_rate))
end

if tokens >= requested then
    tokens = tokens - requested
    redis.call('HSET', key, 'tokens', tokens, 'last_update', now)
    redis.call('EXPIRE', key, 3600)  -- 1 hour TTL
    return {1, tokens}  -- Allowed, remaining tokens
else
    return {0, tokens}  -- Denied, remaining tokens
end
"""

# Lua script for sliding window rate limiting
SLIDING_WINDOW_SCRIPT = """
local key = KEYS[1]
local now = tonumber(ARGV[1])
local window_size = tonumber(ARGV[2])
local limit = tonumber(ARGV[3])

-- Remove expired entries
local window_start = now - window_size
redis.call('ZREMRANGEBYSCORE', key, '-inf', window_start)

-- Get current count
local current_count = redis.call('ZCARD', key)

if current_count < limit then
    -- Add new entry
    redis.call('ZADD', key, now, now .. ':' .. math.random())
    redis.call('EXPIRE', key, window_size + 1)
    return {1, limit - current_count - 1}  -- Allowed, remaining
else
    return {0, 0}  -- Denied, no remaining
end
"""


@dataclass
class RateLimitResult:
    """Result of a rate limit check"""
    allowed: bool
    remaining: float
    reset_at: Optional[float] = None
    error: Optional[str] = None


class RedisRateLimiter:
    """
    Redis-based rate limiter with token bucket algorithm.

    Supports:
    - Token bucket rate limiting with refill
    - Sliding window rate limiting
    - Atomic CAS operations via Lua scripts
    - In-memory fallback for development
    """

    def __init__(
        self,
        redis_url: str = "redis://localhost:6379/0",
        dev_mode: bool = True,
        script_timeout_ms: int = 50
    ):
        """
        Initialize Redis rate limiter.

        Args:
            redis_url: Redis connection URL
            dev_mode: If True, use in-memory fallback
            script_timeout_ms: Timeout for Lua script execution
        """
        self.redis_url = redis_url
        self.dev_mode = dev_mode
        self.script_timeout_ms = script_timeout_ms

        # In-memory fallback for development
        self._memory_store: Dict[str, Dict[str, Any]] = {}
        self._redis = None
        self._token_bucket_sha: Optional[str] = None
        self._sliding_window_sha: Optional[str] = None
        self._initialized = False

        logger.info(f"RedisRateLimiter initialized (dev_mode={dev_mode})")

    async def initialize(self) -> None:
        """Initialize Redis connection and load Lua scripts"""
        if self.dev_mode:
            logger.info("RedisRateLimiter running in dev mode with in-memory fallback")
            self._initialized = True
            return

        try:
            import redis.asyncio as aioredis
            self._redis = aioredis.from_url(
                self.redis_url,
                decode_responses=False
            )

            # Load Lua scripts
            self._token_bucket_sha = await self._redis.script_load(TOKEN_BUCKET_SCRIPT)
            self._sliding_window_sha = await self._redis.script_load(SLIDING_WINDOW_SCRIPT)

            logger.info("RedisRateLimiter connected to Redis and loaded scripts")
            self._initialized = True

        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            logger.warning("Falling back to in-memory rate limiting")
            self.dev_mode = True
            self._initialized = True

    async def check_rate_limit(
        self,
        key: str,
        limit: float,
        window_seconds: int,
        requested: int = 1
    ) -> RateLimitResult:
        """
        Check rate limit using token bucket algorithm.

        Args:
            key: Rate limit key (e.g., "agent_001:api_calls")
            limit: Maximum tokens in bucket
            window_seconds: Time window for refill rate calculation
            requested: Number of tokens requested

        Returns:
            RateLimitResult with allowed status and remaining tokens
        """
        if not self._initialized:
            await self.initialize()

        if self.dev_mode:
            return await self._check_rate_limit_memory(key, limit, window_seconds, requested)

        try:
            now = time.time()
            refill_rate = limit / window_seconds

            result = await self._redis.evalsha(
                self._token_bucket_sha,
                1,  # Number of keys
                key,
                requested,
                limit,
                refill_rate,
                now
            )

            allowed = bool(result[0])
            remaining = float(result[1])

            return RateLimitResult(
                allowed=allowed,
                remaining=remaining,
                reset_at=now + window_seconds if not allowed else None
            )

        except Exception as e:
            logger.error(f"Redis rate limit check failed: {e}")
            return RateLimitResult(
                allowed=False,
                remaining=0,
                error=str(e)
            )

    async def check_sliding_window(
        self,
        key: str,
        limit: int,
        window_seconds: int
    ) -> RateLimitResult:
        """
        Check rate limit using sliding window algorithm.

        Args:
            key: Rate limit key
            limit: Maximum requests in window
            window_seconds: Window size in seconds

        Returns:
            RateLimitResult with allowed status
        """
        if not self._initialized:
            await self.initialize()

        if self.dev_mode:
            return await self._check_sliding_window_memory(key, limit, window_seconds)

        try:
            now = time.time()

            result = await self._redis.evalsha(
                self._sliding_window_sha,
                1,  # Number of keys
                key,
                now,
                window_seconds,
                limit
            )

            allowed = bool(result[0])
            remaining = int(result[1])

            return RateLimitResult(
                allowed=allowed,
                remaining=remaining,
                reset_at=now + window_seconds if not allowed else None
            )

        except Exception as e:
            logger.error(f"Redis sliding window check failed: {e}")
            return RateLimitResult(
                allowed=False,
                remaining=0,
                error=str(e)
            )

    async def _check_rate_limit_memory(
        self,
        key: str,
        limit: float,
        window_seconds: int,
        requested: int
    ) -> RateLimitResult:
        """In-memory token bucket rate limiting (development fallback)"""
        now = time.time()

        if key not in self._memory_store:
            self._memory_store[key] = {
                "tokens": limit,
                "last_update": now
            }

        bucket = self._memory_store[key]

        # Refill tokens
        elapsed = now - bucket["last_update"]
        refill_rate = limit / window_seconds
        bucket["tokens"] = min(limit, bucket["tokens"] + (elapsed * refill_rate))
        bucket["last_update"] = now

        if bucket["tokens"] >= requested:
            bucket["tokens"] -= requested
            return RateLimitResult(
                allowed=True,
                remaining=bucket["tokens"]
            )
        else:
            return RateLimitResult(
                allowed=False,
                remaining=bucket["tokens"],
                reset_at=now + window_seconds
            )

    async def _check_sliding_window_memory(
        self,
        key: str,
        limit: int,
        window_seconds: int
    ) -> RateLimitResult:
        """In-memory sliding window rate limiting (development fallback)"""
        now = time.time()
        window_key = f"{key}:window"

        if window_key not in self._memory_store:
            self._memory_store[window_key] = []

        # Remove expired entries
        window_start = now - window_seconds
        self._memory_store[window_key] = [
            ts for ts in self._memory_store[window_key]
            if ts > window_start
        ]

        current_count = len(self._memory_store[window_key])

        if current_count < limit:
            self._memory_store[window_key].append(now)
            return RateLimitResult(
                allowed=True,
                remaining=limit - current_count - 1
            )
        else:
            return RateLimitResult(
                allowed=False,
                remaining=0,
                reset_at=now + window_seconds
            )

    async def get_usage(self, key: str) -> Dict[str, Any]:
        """Get current usage for a rate limit key"""
        if self.dev_mode:
            if key in self._memory_store:
                return self._memory_store[key]
            return {"tokens": 0, "last_update": None}

        try:
            data = await self._redis.hgetall(key)
            return {
                "tokens": float(data.get(b"tokens", 0)),
                "last_update": float(data.get(b"last_update", 0))
            }
        except Exception as e:
            logger.error(f"Failed to get usage: {e}")
            return {"tokens": 0, "last_update": None, "error": str(e)}

    async def reset(self, key: str) -> bool:
        """Reset rate limit for a key"""
        if self.dev_mode:
            if key in self._memory_store:
                del self._memory_store[key]
            return True

        try:
            await self._redis.delete(key)
            return True
        except Exception as e:
            logger.error(f"Failed to reset rate limit: {e}")
            return False

    async def health_check(self) -> Dict[str, Any]:
        """Check Redis connection health"""
        if self.dev_mode:
            return {
                "status": "healthy",
                "dev_mode": True,
                "keys_tracked": len(self._memory_store)
            }

        try:
            await self._redis.ping()
            return {
                "status": "healthy",
                "dev_mode": False,
                "connected": True
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "dev_mode": False,
                "error": str(e)
            }

    async def close(self) -> None:
        """Cleanup resources"""
        if self._redis:
            await self._redis.close()
        logger.info("RedisRateLimiter closed")
