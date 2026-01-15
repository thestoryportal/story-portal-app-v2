"""
Response Formatter - Response Formatting and Header Injection
"""

from typing import Dict, Any, Optional
from datetime import datetime
from ..models import GatewayResponse, RequestContext, RateLimitHeaders
from ..errors import GatewayError


class ResponseFormatter:
    """
    Formats responses and injects gateway headers

    Features:
    - Standard response format
    - Error response formatting
    - Rate limit headers
    - Trace context headers
    - Cache control headers
    - Security headers
    """

    def __init__(self):
        # Security headers to inject
        self.security_headers = {
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "X-XSS-Protection": "1; mode=block",
            "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
        }

    async def format_response(
        self,
        response: GatewayResponse,
        context: RequestContext,
        rate_limit_info: Optional[Dict[str, Any]] = None,
    ) -> GatewayResponse:
        """
        Format response with gateway headers

        Args:
            response: Backend response
            context: Request context
            rate_limit_info: Rate limit information

        Returns:
            Formatted GatewayResponse
        """
        # Inject trace context headers
        response.headers["X-Request-ID"] = context.request_id
        response.headers["X-Trace-ID"] = context.trace_id
        response.headers["X-Span-ID"] = context.span_id

        # Inject rate limit headers
        if rate_limit_info:
            response.headers["X-RateLimit-Limit"] = str(
                rate_limit_info.get("limit", 0)
            )
            response.headers["X-RateLimit-Remaining"] = str(
                rate_limit_info.get("tokens_remaining", 0)
            )
            response.headers["X-RateLimit-Reset"] = str(
                rate_limit_info.get("reset", 0)
            )

        # Inject idempotency headers if replayed
        if context.is_replayed:
            response.headers["X-Idempotency-Replayed"] = "true"

        # Inject security headers
        response.headers.update(self.security_headers)

        # Remove internal headers
        self._remove_internal_headers(response)

        return response

    async def format_error(
        self,
        error: GatewayError,
        context: RequestContext,
    ) -> GatewayResponse:
        """
        Format error response

        Args:
            error: Gateway error
            context: Request context

        Returns:
            GatewayResponse with error details
        """
        error_body = {
            "error": {
                "code": error.code.value,
                "message": error.message,
                "timestamp": int(datetime.utcnow().timestamp() * 1000),
                "trace_id": context.trace_id,
                "request_id": context.request_id,
            }
        }

        # Add details if present
        if error.details:
            error_body["error"]["details"] = error.details

        response = GatewayResponse(
            status_code=error.http_status,
            headers={
                "Content-Type": "application/json",
                "X-Request-ID": context.request_id,
                "X-Trace-ID": context.trace_id,
            },
            body=error_body,
            timestamp=datetime.utcnow(),
        )

        # Add retry-after header for rate limit errors
        if hasattr(error, "retry_after") and error.retry_after:
            response.headers["Retry-After"] = str(error.retry_after)

        # Inject security headers
        response.headers.update(self.security_headers)

        return response

    async def format_async_accepted(
        self,
        operation_id: str,
        context: RequestContext,
        poll_url: Optional[str] = None,
    ) -> GatewayResponse:
        """
        Format 202 Accepted response for async operation

        Args:
            operation_id: Operation ID
            context: Request context
            poll_url: URL to poll operation status

        Returns:
            GatewayResponse with 202 status
        """
        body = {
            "operation_id": operation_id,
            "status": "accepted",
            "message": "Operation accepted for async processing",
        }

        if poll_url:
            body["poll_url"] = poll_url

        response = GatewayResponse(
            status_code=202,
            headers={
                "Content-Type": "application/json",
                "X-Request-ID": context.request_id,
                "X-Trace-ID": context.trace_id,
                "X-Operation-ID": operation_id,
            },
            body=body,
            timestamp=datetime.utcnow(),
        )

        # Inject security headers
        response.headers.update(self.security_headers)

        return response

    def _remove_internal_headers(self, response: GatewayResponse) -> None:
        """Remove internal headers that shouldn't be exposed"""
        internal_headers = [
            "x-internal-auth",
            "x-backend-key",
            "x-admin-token",
            "x-backend-version",
        ]

        for header in internal_headers:
            response.headers.pop(header, None)
            response.headers.pop(header.upper(), None)

    def sanitize_response_body(self, body: Any) -> Any:
        """
        Sanitize response body to remove sensitive data

        Args:
            body: Response body

        Returns:
            Sanitized body
        """
        # In production, implement PII redaction
        # For now, return as-is
        return body
