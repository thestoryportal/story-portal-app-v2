"""
L04 Model Gateway Layer - Rate Limiter Service

Token bucket rate limiting with Redis backend for distributed state.
"""

import time
from typing import Optional, Dict
import logging

from ..models import (
    RateLimitError,
    L04ErrorCode
)

logger = logging.getLogger(__name__)


class RateLimiter:
    """
    Token bucket rate limiter

    Implements distributed rate limiting using Redis for state storage.
    Supports both RPM (requests per minute) and TPM (tokens per minute) limits.
    """

    def __init__(
        self,
        redis_url: str = "redis://localhost:6379",
        default_rpm: int = 60,
        default_tpm: int = 100000
    ):
        """
        Initialize rate limiter

        Args:
            redis_url: Redis connection URL
            default_rpm: Default requests per minute limit
            default_tpm: Default tokens per minute limit
        """
        self.redis_url = redis_url
        self.default_rpm = default_rpm
        self.default_tpm = default_tpm
        self._redis = None
        self._local_cache: Dict[str, dict] = {}
        logger.info(
            f"RateLimiter initialized "
            f"(default_rpm={default_rpm}, default_tpm={default_tpm})"
        )

    async def check_rate_limit(
        self,
        agent_did: str,
        provider: str,
        tokens: int,
        rpm_limit: Optional[int] = None,
        tpm_limit: Optional[int] = None
    ) -> bool:
        """
        Check if request is within rate limits

        Args:
            agent_did: Agent DID
            provider: Provider identifier
            tokens: Number of tokens in request
            rpm_limit: Optional override for RPM limit
            tpm_limit: Optional override for TPM limit

        Returns:
            True if within limits

        Raises:
            RateLimitError: If rate limit exceeded
        """
        rpm_limit = rpm_limit or self.default_rpm
        tpm_limit = tpm_limit or self.default_tpm

        try:
            # Check RPM limit
            rpm_key = f"ratelimit:rpm:{agent_did}:{provider}"
            if not await self._check_token_bucket(rpm_key, 1, rpm_limit, 60):
                logger.warning(
                    f"RPM limit exceeded for {agent_did} on {provider}"
                )
                raise RateLimitError(
                    L04ErrorCode.E4404_RPM_LIMIT_EXCEEDED,
                    f"Request rate limit exceeded ({rpm_limit} RPM)",
                    {
                        "agent_did": agent_did,
                        "provider": provider,
                        "limit": rpm_limit
                    }
                )

            # Check TPM limit
            tpm_key = f"ratelimit:tpm:{agent_did}:{provider}"
            if not await self._check_token_bucket(tpm_key, tokens, tpm_limit, 60):
                logger.warning(
                    f"TPM limit exceeded for {agent_did} on {provider}"
                )
                raise RateLimitError(
                    L04ErrorCode.E4405_TPM_LIMIT_EXCEEDED,
                    f"Token rate limit exceeded ({tpm_limit} TPM)",
                    {
                        "agent_did": agent_did,
                        "provider": provider,
                        "tokens": tokens,
                        "limit": tpm_limit
                    }
                )

            return True

        except RateLimitError:
            raise
        except Exception as e:
            logger.error(f"Rate limit check error: {e}")
            # On error, allow the request (fail open)
            return True

    async def check_limit(
        self,
        agent_id: str,
        tokens: int,
        provider: str = "default",
        rpm_limit: Optional[int] = None,
        tpm_limit: Optional[int] = None
    ) -> bool:
        """
        Convenience method - alias for check_rate_limit with simplified parameters

        Args:
            agent_id: Agent identifier (agent_did)
            tokens: Number of tokens in request
            provider: Provider identifier (default: "default")
            rpm_limit: Optional override for RPM limit
            tpm_limit: Optional override for TPM limit

        Returns:
            True if within limits

        Raises:
            RateLimitError: If rate limit exceeded
        """
        return await self.check_rate_limit(
            agent_did=agent_id,
            provider=provider,
            tokens=tokens,
            rpm_limit=rpm_limit,
            tpm_limit=tpm_limit
        )

    async def _check_token_bucket(
        self,
        key: str,
        tokens: int,
        capacity: int,
        refill_period: int
    ) -> bool:
        """
        Check token bucket and consume tokens if available

        Args:
            key: Redis key for bucket
            tokens: Number of tokens to consume
            capacity: Bucket capacity
            refill_period: Refill period in seconds

        Returns:
            True if tokens available and consumed
        """
        try:
            redis_client = await self._get_redis_client()
            current_time = time.time()

            # Get current bucket state
            bucket_data = await redis_client.hgetall(key)

            if not bucket_data:
                # Initialize new bucket
                bucket_data = {
                    "tokens": str(capacity),
                    "last_refill": str(current_time)
                }

            # Parse bucket state
            available_tokens = float(bucket_data.get("tokens", capacity))
            last_refill = float(bucket_data.get("last_refill", current_time))

            # Calculate refill
            elapsed = current_time - last_refill
            refill_amount = (elapsed / refill_period) * capacity
            available_tokens = min(capacity, available_tokens + refill_amount)

            # Check if enough tokens
            if available_tokens >= tokens:
                # Consume tokens
                available_tokens -= tokens

                # Update bucket state
                await redis_client.hset(
                    key,
                    mapping={
                        "tokens": str(available_tokens),
                        "last_refill": str(current_time)
                    }
                )
                await redis_client.expire(key, refill_period * 2)

                return True
            else:
                # Not enough tokens
                return False

        except Exception as e:
            logger.error(f"Token bucket error: {e}")
            # On error, allow the request (fail open)
            return True

    async def get_usage(
        self,
        agent_did: str,
        provider: str
    ) -> Dict[str, dict]:
        """
        Get current usage for agent/provider

        Args:
            agent_did: Agent DID
            provider: Provider identifier

        Returns:
            Dictionary with RPM and TPM usage
        """
        try:
            redis_client = await self._get_redis_client()
            current_time = time.time()

            rpm_key = f"ratelimit:rpm:{agent_did}:{provider}"
            tpm_key = f"ratelimit:tpm:{agent_did}:{provider}"

            rpm_data = await redis_client.hgetall(rpm_key)
            tpm_data = await redis_client.hgetall(tpm_key)

            def parse_bucket(data: dict, capacity: int) -> dict:
                if not data:
                    return {"available": capacity, "capacity": capacity}

                available = float(data.get("tokens", capacity))
                last_refill = float(data.get("last_refill", current_time))
                elapsed = current_time - last_refill

                # Calculate with refill
                refill_amount = (elapsed / 60) * capacity
                available = min(capacity, available + refill_amount)

                return {
                    "available": int(available),
                    "capacity": capacity,
                    "used": capacity - int(available)
                }

            return {
                "rpm": parse_bucket(rpm_data, self.default_rpm),
                "tpm": parse_bucket(tpm_data, self.default_tpm)
            }

        except Exception as e:
            logger.error(f"Get usage error: {e}")
            return {
                "rpm": {"available": self.default_rpm, "capacity": self.default_rpm, "used": 0},
                "tpm": {"available": self.default_tpm, "capacity": self.default_tpm, "used": 0}
            }

    async def reset(self, agent_did: str, provider: str) -> None:
        """
        Reset rate limits for agent/provider

        Args:
            agent_did: Agent DID
            provider: Provider identifier
        """
        try:
            redis_client = await self._get_redis_client()

            rpm_key = f"ratelimit:rpm:{agent_did}:{provider}"
            tpm_key = f"ratelimit:tpm:{agent_did}:{provider}"

            await redis_client.delete(rpm_key, tpm_key)
            logger.info(f"Reset rate limits for {agent_did} on {provider}")

        except Exception as e:
            logger.error(f"Reset error: {e}")

    async def _get_redis_client(self):
        """Get or create Redis client"""
        if self._redis is None:
            try:
                import redis.asyncio as redis
                self._redis = redis.from_url(
                    self.redis_url,
                    encoding="utf-8",
                    decode_responses=True
                )
            except ImportError:
                logger.error("redis package not installed")
                raise RateLimitError(
                    L04ErrorCode.E4400_RATE_LIMIT_EXCEEDED,
                    "Redis package not installed"
                )
        return self._redis

    async def close(self) -> None:
        """Close Redis connection"""
        if self._redis:
            await self._redis.close()
            self._redis = None
