"""
FastAPI Middleware for Request Tracking and Correlation IDs

Provides middleware for injecting correlation IDs, request IDs, and tracking
request/response lifecycle across all services.
"""

import logging
import time
from typing import Callable, Optional
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from .logging_config import (
    generate_correlation_id,
    generate_request_id,
    set_correlation_id,
    set_request_id,
    set_user_id,
    set_session_id,
    clear_context,
    get_correlation_id,
    get_request_id,
)


logger = logging.getLogger(__name__)


class CorrelationIDMiddleware(BaseHTTPMiddleware):
    """
    Middleware to handle correlation ID tracking across requests.

    Features:
    - Extracts correlation ID from incoming request headers
    - Generates new correlation ID if not present
    - Propagates correlation ID to downstream services
    - Adds correlation ID to response headers
    - Tracks request/response timing
    - Logs request lifecycle events
    """

    # Standard header names for correlation tracking
    CORRELATION_ID_HEADER = "X-Correlation-ID"
    REQUEST_ID_HEADER = "X-Request-ID"
    USER_ID_HEADER = "X-User-ID"
    SESSION_ID_HEADER = "X-Session-ID"

    def __init__(
        self,
        app: ASGIApp,
        service_name: str,
        log_requests: bool = True,
        log_responses: bool = True,
    ):
        """
        Initialize middleware.

        Args:
            app: ASGI application
            service_name: Name of the service for logging
            log_requests: Whether to log incoming requests
            log_responses: Whether to log outgoing responses
        """
        super().__init__(app)
        self.service_name = service_name
        self.log_requests = log_requests
        self.log_responses = log_responses

    async def dispatch(
        self, request: Request, call_next: Callable
    ) -> Response:
        """
        Process request and inject correlation tracking.

        Args:
            request: Incoming request
            call_next: Next middleware/handler in chain

        Returns:
            Response with correlation headers
        """
        # Clear any existing context
        clear_context()

        # Extract or generate correlation ID
        correlation_id = request.headers.get(
            self.CORRELATION_ID_HEADER.lower()
        ) or request.headers.get(self.CORRELATION_ID_HEADER)

        if not correlation_id:
            correlation_id = generate_correlation_id()
            is_new_correlation = True
        else:
            is_new_correlation = False

        set_correlation_id(correlation_id)

        # Extract or generate request ID
        request_id = request.headers.get(
            self.REQUEST_ID_HEADER.lower()
        ) or request.headers.get(self.REQUEST_ID_HEADER)

        if not request_id:
            request_id = generate_request_id()

        set_request_id(request_id)

        # Extract user and session IDs if present
        user_id = request.headers.get(
            self.USER_ID_HEADER.lower()
        ) or request.headers.get(self.USER_ID_HEADER)

        if user_id:
            set_user_id(user_id)

        session_id = request.headers.get(
            self.SESSION_ID_HEADER.lower()
        ) or request.headers.get(self.SESSION_ID_HEADER)

        if session_id:
            set_session_id(session_id)

        # Start timing
        start_time = time.time()

        # Log incoming request
        if self.log_requests:
            logger.info(
                f"Incoming request",
                extra={
                    'event': 'request_start',
                    'method': request.method,
                    'path': request.url.path,
                    'query': str(request.url.query) if request.url.query else None,
                    'client_host': request.client.host if request.client else None,
                    'user_agent': request.headers.get('user-agent'),
                    'is_new_correlation': is_new_correlation,
                }
            )

        # Process request
        try:
            response = await call_next(request)

            # Calculate duration
            duration = time.time() - start_time

            # Log response
            if self.log_responses:
                logger.info(
                    f"Request completed",
                    extra={
                        'event': 'request_complete',
                        'method': request.method,
                        'path': request.url.path,
                        'status_code': response.status_code,
                        'duration_ms': round(duration * 1000, 2),
                    }
                )

            # Add correlation headers to response
            response.headers[self.CORRELATION_ID_HEADER] = correlation_id
            response.headers[self.REQUEST_ID_HEADER] = request_id

            return response

        except Exception as exc:
            # Calculate duration
            duration = time.time() - start_time

            # Log error
            logger.error(
                f"Request failed",
                extra={
                    'event': 'request_error',
                    'method': request.method,
                    'path': request.url.path,
                    'duration_ms': round(duration * 1000, 2),
                    'error': str(exc),
                    'error_type': type(exc).__name__,
                },
                exc_info=True,
            )

            raise

        finally:
            # Clear context after request
            clear_context()


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Enhanced request logging middleware with detailed metrics.

    Tracks:
    - Request body size
    - Response body size
    - Query parameter count
    - Header count
    - Detailed timing metrics
    """

    def __init__(
        self,
        app: ASGIApp,
        service_name: str,
        log_body_size: bool = True,
        max_body_log_size: int = 1000,
    ):
        """
        Initialize middleware.

        Args:
            app: ASGI application
            service_name: Name of the service
            log_body_size: Whether to log request/response body sizes
            max_body_log_size: Maximum body size to log (bytes)
        """
        super().__init__(app)
        self.service_name = service_name
        self.log_body_size = log_body_size
        self.max_body_log_size = max_body_log_size

    async def dispatch(
        self, request: Request, call_next: Callable
    ) -> Response:
        """Process request with detailed logging."""
        start_time = time.time()

        # Gather request metadata
        request_metadata = {
            'event': 'request_metadata',
            'method': request.method,
            'path': request.url.path,
            'header_count': len(request.headers),
            'query_param_count': len(request.query_params),
        }

        # Add body size if configured
        if self.log_body_size:
            try:
                body = await request.body()
                request_metadata['request_body_size'] = len(body)

                # Reconstruct request body for downstream handlers
                async def receive():
                    return {'type': 'http.request', 'body': body}

                request._receive = receive

            except Exception as e:
                logger.warning(
                    f"Failed to read request body",
                    extra={'error': str(e)}
                )

        # Process request
        response = await call_next(request)

        # Calculate timing
        duration = time.time() - start_time

        # Add response metadata
        request_metadata.update({
            'status_code': response.status_code,
            'duration_ms': round(duration * 1000, 2),
        })

        # Log metadata
        logger.info(
            f"Request metadata",
            extra=request_metadata
        )

        return response


def get_correlation_id_from_request(request: Request) -> Optional[str]:
    """
    Extract correlation ID from request headers.

    Args:
        request: FastAPI Request object

    Returns:
        Correlation ID if present, None otherwise
    """
    return (
        request.headers.get("x-correlation-id") or
        request.headers.get("X-Correlation-ID")
    )


def add_correlation_headers(headers: dict) -> dict:
    """
    Add correlation tracking headers to outgoing requests.

    Args:
        headers: Existing headers dictionary

    Returns:
        Headers with correlation tracking added
    """
    correlation_id = get_correlation_id()
    request_id = get_request_id()

    if correlation_id:
        headers["X-Correlation-ID"] = correlation_id

    if request_id:
        headers["X-Request-ID"] = request_id

    return headers


class PerformanceMonitoringMiddleware(BaseHTTPMiddleware):
    """
    Middleware for performance monitoring and slow request detection.

    Logs warnings for requests exceeding configured thresholds.
    """

    def __init__(
        self,
        app: ASGIApp,
        service_name: str,
        slow_request_threshold_ms: float = 1000.0,
        very_slow_threshold_ms: float = 5000.0,
    ):
        """
        Initialize middleware.

        Args:
            app: ASGI application
            service_name: Name of the service
            slow_request_threshold_ms: Threshold for slow request warning (ms)
            very_slow_threshold_ms: Threshold for very slow request error (ms)
        """
        super().__init__(app)
        self.service_name = service_name
        self.slow_threshold = slow_request_threshold_ms / 1000.0
        self.very_slow_threshold = very_slow_threshold_ms / 1000.0

    async def dispatch(
        self, request: Request, call_next: Callable
    ) -> Response:
        """Monitor request performance."""
        start_time = time.time()

        response = await call_next(request)

        duration = time.time() - start_time

        # Log slow requests
        if duration >= self.very_slow_threshold:
            logger.error(
                f"Very slow request detected",
                extra={
                    'event': 'very_slow_request',
                    'method': request.method,
                    'path': request.url.path,
                    'duration_ms': round(duration * 1000, 2),
                    'threshold_ms': self.very_slow_threshold * 1000,
                }
            )
        elif duration >= self.slow_threshold:
            logger.warning(
                f"Slow request detected",
                extra={
                    'event': 'slow_request',
                    'method': request.method,
                    'path': request.url.path,
                    'duration_ms': round(duration * 1000, 2),
                    'threshold_ms': self.slow_threshold * 1000,
                }
            )

        return response
