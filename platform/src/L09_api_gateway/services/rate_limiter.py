"""
Rate Limiter - Distributed Token Bucket with Redis
"""

import time
from typing import Optional, Tuple
from ..models import ConsumerProfile, RateLimitTier, RATE_LIMIT_CONFIGS
from ..errors import ErrorCode, RateLimitError


class RateLimiter:
    """
    Distributed rate limiter using token bucket algorithm with Redis

    Features:
    - Burst capacity for traffic spikes
    - Daily quota enforcement
    - Cost-aware rate limiting (heavy ops cost more tokens)
    - Unified across HTTP/1.1, HTTP/2, gRPC
    """

    def __init__(self, redis_client):
        """
        Args:
            redis_client: Redis client for distributed state
        """
        self.redis = redis_client

        # Lua script for atomic token bucket operations
        self.token_bucket_script = """
        local key = KEYS[1]
        local now = tonumber(ARGV[1])
        local tokens_required = tonumber(ARGV[2])
        local rps_limit = tonumber(ARGV[3])
        local burst_capacity = tonumber(ARGV[4])
        local daily_quota = tonumber(ARGV[5])

        -- Get current state
        local state = redis.call('HMGET', key, 'tokens', 'last_refill', 'daily_used', 'daily_reset')
        local tokens = tonumber(state[1]) or burst_capacity
        local last_refill = tonumber(state[2]) or now
        local daily_used = tonumber(state[3]) or 0
        local daily_reset = tonumber(state[4]) or (now + 86400)

        -- Reset daily counter if needed
        if now >= daily_reset then
            daily_used = 0
            daily_reset = now + 86400
        end

        -- Refill tokens based on time elapsed
        local elapsed = now - last_refill
        local refill = elapsed * rps_limit
        tokens = math.min(burst_capacity, tokens + refill)

        -- Check if enough tokens
        if tokens < tokens_required then
            return {0, tokens, daily_used, daily_quota - daily_used}
        end

        -- Check daily quota
        if daily_used + tokens_required > daily_quota then
            return {0, tokens, daily_used, daily_quota - daily_used}
        end

        -- Consume tokens
        tokens = tokens - tokens_required
        daily_used = daily_used + tokens_required

        -- Update state
        redis.call('HMSET', key,
            'tokens', tokens,
            'last_refill', now,
            'daily_used', daily_used,
            'daily_reset', daily_reset
        )
        redis.call('EXPIRE', key, 86400)

        return {1, tokens, daily_used, daily_quota - daily_used}
        """

    async def check_rate_limit(
        self,
        consumer: ConsumerProfile,
        tokens_required: int = 1,
    ) -> Tuple[bool, int]:
        """
        Check if request is within rate limit

        Args:
            consumer: Consumer profile with rate limit tier
            tokens_required: Number of tokens to consume (default 1)

        Returns:
            (allowed, retry_after_seconds)

        Raises:
            RateLimitError: If rate limit exceeded
        """
        # Get rate limit configuration
        config = RATE_LIMIT_CONFIGS.get(consumer.rate_limit_tier)
        if not config:
            raise RateLimitError(
                ErrorCode.E9403,
                f"Rate limit tier not found: {consumer.rate_limit_tier}",
            )

        # Check rate limit using Redis
        key = f"rl:consumer:{consumer.consumer_id}"
        now = time.time()

        try:
            # Execute Lua script atomically
            result = await self._execute_token_bucket(
                key,
                now,
                tokens_required,
                config.rps_limit,
                config.burst_capacity,
                config.daily_quota,
            )

            allowed = result[0] == 1
            tokens_remaining = int(result[1])
            daily_used = int(result[2])
            daily_remaining = int(result[3])

            if not allowed:
                # Calculate retry_after
                if daily_remaining <= 0:
                    # Daily quota exceeded - retry after daily reset
                    retry_after = 86400
                    raise RateLimitError(
                        ErrorCode.E9402,
                        "Daily quota exceeded",
                        retry_after=retry_after,
                        details={
                            "daily_quota": config.daily_quota,
                            "daily_used": daily_used,
                        },
                    )
                else:
                    # Burst capacity exceeded - retry based on refill rate
                    retry_after = int(tokens_required / config.rps_limit)
                    raise RateLimitError(
                        ErrorCode.E9401,
                        "Rate limit exceeded",
                        retry_after=retry_after,
                        details={
                            "limit": config.rps_limit,
                            "burst_capacity": config.burst_capacity,
                            "tokens_remaining": tokens_remaining,
                        },
                    )

            return True, 0

        except RateLimitError:
            raise
        except Exception as e:
            # Fallback to in-memory rate limiting if Redis unavailable
            return await self._fallback_rate_limit(consumer, tokens_required)

    async def _execute_token_bucket(
        self,
        key: str,
        now: float,
        tokens_required: int,
        rps_limit: int,
        burst_capacity: int,
        daily_quota: int,
    ) -> list:
        """Execute token bucket Lua script"""
        # In production, use redis.eval() or redis.evalsha()
        # For now, simulate with Redis commands

        # Try to get script SHA
        if not hasattr(self, '_script_sha'):
            self._script_sha = await self.redis.script_load(self.token_bucket_script)

        # Execute script
        result = await self.redis.evalsha(
            self._script_sha,
            1,
            key,
            now,
            tokens_required,
            rps_limit,
            burst_capacity,
            daily_quota,
        )
        return result

    async def _fallback_rate_limit(
        self, consumer: ConsumerProfile, tokens_required: int
    ) -> Tuple[bool, int]:
        """
        Fallback to in-memory rate limiting when Redis unavailable

        Note: This is per-gateway instance only, not distributed
        """
        # In production, implement simple in-memory token bucket
        # For now, allow all requests in fallback mode
        return True, 0

    async def get_rate_limit_info(
        self, consumer: ConsumerProfile
    ) -> dict:
        """
        Get current rate limit status

        Returns:
            Dict with limit, remaining, reset timestamp
        """
        config = RATE_LIMIT_CONFIGS.get(consumer.rate_limit_tier)
        if not config:
            return {}

        key = f"rl:consumer:{consumer.consumer_id}"

        try:
            state = await self.redis.hmget(key, "tokens", "daily_used", "daily_reset")
            tokens = float(state[0]) if state[0] else config.burst_capacity
            daily_used = int(state[1]) if state[1] else 0
            daily_reset = int(state[2]) if state[2] else int(time.time()) + 86400

            return {
                "limit": config.rps_limit,
                "burst_capacity": config.burst_capacity,
                "tokens_remaining": int(tokens),
                "daily_quota": config.daily_quota,
                "daily_used": daily_used,
                "daily_remaining": config.daily_quota - daily_used,
                "reset": daily_reset,
            }

        except Exception:
            return {
                "limit": config.rps_limit,
                "burst_capacity": config.burst_capacity,
                "daily_quota": config.daily_quota,
            }
