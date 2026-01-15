"""
L09 API Gateway - L01 Data Layer Bridge

Bridge between L09 API Gateway and L01 Data Layer for persistent request tracking.
Records API requests, authentication events, and rate limit violations.
"""

import logging
from typing import Optional
from datetime import datetime
from uuid import uuid4

from src.L01_data_layer.client import L01Client

logger = logging.getLogger(__name__)


class L09Bridge:
    """
    Bridge between L09 API Gateway and L01 Data Layer.

    Responsibilities:
    - Record API request logs with latency and status
    - Track authentication events (successes and failures)
    - Record rate limit violations with token bucket tracking
    """

    def __init__(self, l01_base_url: str = "http://localhost:8002"):
        """Initialize L09 bridge.

        Args:
            l01_base_url: Base URL for L01 Data Layer API
        """
        self.l01_client = L01Client(base_url=l01_base_url)
        self.enabled = True
        logger.info(f"L09Bridge initialized with base_url={l01_base_url}")

    async def initialize(self) -> None:
        """Initialize bridge (async setup if needed)."""
        logger.info("L09Bridge initialized")

    async def record_api_request(
        self,
        request_id: str,
        trace_id: str,
        span_id: str,
        timestamp: datetime,
        method: str,
        path: str,
        status_code: int,
        latency_ms: float,
        consumer_id: Optional[str] = None,
        tenant_id: Optional[str] = None,
        authenticated: bool = False,
        auth_method: Optional[str] = None,
        request_size_bytes: Optional[int] = None,
        response_size_bytes: Optional[int] = None,
        rate_limit_tier: Optional[str] = None,
        idempotency_key: Optional[str] = None,
        idempotent_cache_hit: bool = False,
        error_code: Optional[str] = None,
        error_message: Optional[str] = None,
        client_ip: Optional[str] = None,
        user_agent: Optional[str] = None,
        headers: Optional[dict] = None,
        query_params: Optional[dict] = None,
        metadata: Optional[dict] = None
    ) -> bool:
        """Record an API request in L01.

        Args:
            request_id: Unique request identifier
            trace_id: Distributed trace ID
            span_id: Span ID within trace
            timestamp: Request timestamp
            method: HTTP method (GET, POST, etc.)
            path: Request path
            status_code: HTTP response status code
            latency_ms: Request latency in milliseconds
            consumer_id: Authenticated consumer ID
            tenant_id: Tenant identifier
            authenticated: Whether request was authenticated
            auth_method: Authentication method used
            request_size_bytes: Request body size
            response_size_bytes: Response body size
            rate_limit_tier: Consumer's rate limit tier
            idempotency_key: Idempotency key if provided
            idempotent_cache_hit: Whether idempotent cache was hit
            error_code: Error code if request failed
            error_message: Error message if request failed
            client_ip: Client IP address
            user_agent: Client user agent
            headers: Request headers (sanitized)
            query_params: Query parameters
            metadata: Additional metadata

        Returns:
            True if recorded successfully, False otherwise
        """
        if not self.enabled:
            return False

        try:
            await self.l01_client.record_api_request(
                request_id=request_id,
                trace_id=trace_id,
                span_id=span_id,
                timestamp=timestamp.isoformat(),
                method=method,
                path=path,
                status_code=status_code,
                latency_ms=latency_ms,
                consumer_id=consumer_id,
                tenant_id=tenant_id,
                authenticated=authenticated,
                auth_method=auth_method,
                request_size_bytes=request_size_bytes,
                response_size_bytes=response_size_bytes,
                rate_limit_tier=rate_limit_tier,
                idempotency_key=idempotency_key,
                idempotent_cache_hit=idempotent_cache_hit,
                error_code=error_code,
                error_message=error_message,
                client_ip=client_ip,
                user_agent=user_agent,
                headers=headers,
                query_params=query_params,
                metadata=metadata
            )

            logger.debug(
                f"Recorded API request {request_id} in L01 "
                f"({method} {path} -> {status_code}, {latency_ms:.2f}ms)"
            )
            return True

        except Exception as e:
            logger.error(f"Failed to record API request in L01: {e}")
            return False

    async def record_authentication_event(
        self,
        timestamp: datetime,
        auth_method: str,
        success: bool,
        consumer_id: Optional[str] = None,
        tenant_id: Optional[str] = None,
        failure_reason: Optional[str] = None,
        client_ip: Optional[str] = None,
        user_agent: Optional[str] = None,
        metadata: Optional[dict] = None
    ) -> bool:
        """Record an authentication event in L01.

        Args:
            timestamp: Event timestamp
            auth_method: Authentication method (api_key, oauth, jwt, etc.)
            success: Whether authentication succeeded
            consumer_id: Consumer ID if authenticated
            tenant_id: Tenant identifier
            failure_reason: Reason for failure if not successful
            client_ip: Client IP address
            user_agent: Client user agent
            metadata: Additional metadata

        Returns:
            True if recorded successfully, False otherwise
        """
        if not self.enabled:
            return False

        try:
            event_id = f"auth-{uuid4()}"

            await self.l01_client.record_authentication_event(
                event_id=event_id,
                timestamp=timestamp.isoformat(),
                auth_method=auth_method,
                success=success,
                consumer_id=consumer_id,
                tenant_id=tenant_id,
                failure_reason=failure_reason,
                client_ip=client_ip,
                user_agent=user_agent,
                metadata=metadata
            )

            logger.info(
                f"Recorded authentication event {event_id} in L01 "
                f"(method={auth_method}, success={success})"
            )
            return True

        except Exception as e:
            logger.error(f"Failed to record authentication event in L01: {e}")
            return False

    async def record_rate_limit_event(
        self,
        timestamp: datetime,
        consumer_id: str,
        rate_limit_tier: str,
        tokens_remaining: int,
        tokens_limit: int,
        window_start: datetime,
        window_end: datetime,
        tenant_id: Optional[str] = None,
        endpoint: Optional[str] = None,
        tokens_requested: int = 1,
        exceeded: bool = False,
        metadata: Optional[dict] = None
    ) -> bool:
        """Record a rate limit event in L01.

        Args:
            timestamp: Event timestamp
            consumer_id: Consumer identifier
            rate_limit_tier: Rate limit tier (standard, premium, etc.)
            tokens_remaining: Tokens remaining in window
            tokens_limit: Total tokens allowed in window
            window_start: Rate limit window start time
            window_end: Rate limit window end time
            tenant_id: Tenant identifier
            endpoint: Endpoint being rate limited
            tokens_requested: Number of tokens requested
            exceeded: Whether rate limit was exceeded
            metadata: Additional metadata

        Returns:
            True if recorded successfully, False otherwise
        """
        if not self.enabled:
            return False

        try:
            event_id = f"ratelimit-{uuid4()}"

            await self.l01_client.record_rate_limit_event(
                event_id=event_id,
                timestamp=timestamp.isoformat(),
                consumer_id=consumer_id,
                rate_limit_tier=rate_limit_tier,
                tokens_remaining=tokens_remaining,
                tokens_limit=tokens_limit,
                window_start=window_start.isoformat(),
                window_end=window_end.isoformat(),
                tenant_id=tenant_id,
                endpoint=endpoint,
                tokens_requested=tokens_requested,
                exceeded=exceeded,
                metadata=metadata
            )

            logger.info(
                f"Recorded rate limit event {event_id} in L01 "
                f"(consumer={consumer_id}, tier={rate_limit_tier}, "
                f"remaining={tokens_remaining}/{tokens_limit}, exceeded={exceeded})"
            )
            return True

        except Exception as e:
            logger.error(f"Failed to record rate limit event in L01: {e}")
            return False

    async def cleanup(self) -> None:
        """Cleanup bridge resources."""
        try:
            await self.l01_client.close()
            logger.info("L09Bridge cleanup complete")
        except Exception as e:
            logger.warning(f"L09Bridge cleanup failed: {e}")
