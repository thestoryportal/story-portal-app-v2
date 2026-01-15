"""
Idempotency Handler - 24-hour Request Deduplication
"""

import json
from uuid import UUID
from typing import Optional
from datetime import datetime, timedelta
from ..models import RequestContext, GatewayResponse
from ..errors import ErrorCode, ValidationError


class IdempotencyHandler:
    """
    Ensures idempotent operations are not duplicated when requests are retried

    Features:
    - 24-hour deduplication window
    - UUID v4 idempotency keys
    - Cached response replay
    - Only caches successful responses
    """

    def __init__(self, redis_client):
        """
        Args:
            redis_client: Redis client for idempotency cache
        """
        self.redis = redis_client
        self.ttl_seconds = 86400  # 24 hours

    async def check_idempotency(
        self, context: RequestContext
    ) -> Optional[GatewayResponse]:
        """
        Check if request is duplicate based on idempotency key

        Args:
            context: Request context with idempotency_key

        Returns:
            Cached GatewayResponse if duplicate, None if first request

        Raises:
            ValidationError: If idempotency key format invalid
        """
        if not context.idempotency_key:
            return None

        # Validate idempotency key format (UUID v4)
        try:
            UUID(str(context.idempotency_key), version=4)
        except (ValueError, AttributeError):
            raise ValidationError(
                ErrorCode.E9301,
                "Invalid idempotency key format (must be UUID v4)",
                details={"provided": str(context.idempotency_key)},
            )

        # Check Redis cache
        key = f"idempotency:{context.idempotency_key}"

        try:
            cached_data = await self.redis.get(key)

            if cached_data:
                # Cache hit - return cached response
                cached = json.loads(cached_data)

                # Mark as replayed
                context.is_replayed = True

                response = GatewayResponse(
                    status_code=cached["status_code"],
                    headers=cached.get("headers", {}),
                    body=cached.get("body"),
                    timestamp=datetime.fromisoformat(cached["timestamp"]),
                )

                # Add replay headers
                response.headers["X-Idempotency-Replayed"] = "true"
                response.headers["X-Idempotency-Original-Request-ID"] = cached.get(
                    "request_id", ""
                )

                return response

        except Exception as e:
            # If Redis fails, log error but allow request to proceed
            # Better to risk duplicate than block requests
            pass

        return None

    async def store_response(
        self, context: RequestContext, response: GatewayResponse
    ) -> None:
        """
        Store successful response for idempotency replay

        Args:
            context: Request context with idempotency_key
            response: Gateway response to cache

        Note: Only caches successful responses (2xx status codes)
        """
        if not context.idempotency_key:
            return

        # Only cache successful responses
        if response.status_code < 200 or response.status_code >= 300:
            return

        key = f"idempotency:{context.idempotency_key}"

        try:
            # Prepare cached data
            cached_data = {
                "status_code": response.status_code,
                "headers": response.headers,
                "body": response.body,
                "timestamp": response.timestamp.isoformat(),
                "request_id": context.request_id,
            }

            # Store in Redis with TTL
            await self.redis.setex(
                key, self.ttl_seconds, json.dumps(cached_data)
            )

        except Exception as e:
            # If Redis fails, log error but don't fail the request
            pass

    async def invalidate(self, idempotency_key: UUID) -> None:
        """
        Invalidate cached response for idempotency key

        Args:
            idempotency_key: Idempotency key to invalidate
        """
        key = f"idempotency:{idempotency_key}"

        try:
            await self.redis.delete(key)
        except Exception:
            pass
