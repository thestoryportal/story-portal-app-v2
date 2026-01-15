"""
Event Publisher - Audit Logs and Metrics Emission
"""

import time
from datetime import datetime
from typing import Dict, Any, Optional
from ..models import RequestContext, GatewayResponse


class EventPublisher:
    """
    Publishes events and metrics

    Features:
    - Audit logs (immutable, time-locked)
    - Request/response logging with sampling
    - Prometheus metrics
    - Event store integration (L01)
    """

    def __init__(
        self,
        event_store,
        metrics_client=None,
        log_sampling_rate: float = 0.01,
    ):
        """
        Args:
            event_store: L01 Event Store client
            metrics_client: Prometheus metrics client
            log_sampling_rate: Probabilistic sampling (1% default)
        """
        self.event_store = event_store
        self.metrics_client = metrics_client
        self.log_sampling_rate = log_sampling_rate

    async def publish_request_event(
        self,
        context: RequestContext,
        response: GatewayResponse,
        latency_ms: float,
        route_id: Optional[str] = None,
        backend_id: Optional[str] = None,
        error_code: Optional[str] = None,
    ) -> None:
        """
        Publish API request event

        Args:
            context: Request context
            response: Gateway response
            latency_ms: Request latency in milliseconds
            route_id: Matched route ID
            backend_id: Backend service ID
            error_code: Error code if failed
        """
        # Apply sampling (but always log errors)
        if response.status_code >= 400 or self._should_sample():
            event = {
                "event_type": "APIRequestEvent",
                "timestamp": datetime.utcnow().isoformat(),
                "request_id": context.request_id,
                "trace_id": context.trace_id,
                "span_id": context.span_id,
                # Request info
                "method": context.metadata.method,
                "path": self._redact_path(context.metadata.path),
                "client_ip": context.metadata.client_ip,
                # Consumer info
                "consumer_id": context.consumer_id,
                "tenant_id": context.tenant_id,
                "auth_method": context.auth_method,
                # Response info
                "status_code": response.status_code,
                "latency_ms": latency_ms,
                # Routing info
                "route_id": route_id,
                "backend_id": backend_id,
                # Error info
                "error_code": error_code,
                # Idempotency
                "idempotency_key": str(context.idempotency_key) if context.idempotency_key else None,
                "is_replayed": context.is_replayed,
                # Rate limiting
                "rate_limit_tier": context.rate_limit_tier,
                "tokens_consumed": context.tokens_consumed,
            }

            # Publish to L01 Event Store
            await self.event_store.publish_event(event)

        # Emit metrics (always, regardless of sampling)
        await self._emit_metrics(context, response, latency_ms, error_code)

    async def publish_audit_event(
        self,
        event_type: str,
        context: RequestContext,
        details: Dict[str, Any],
    ) -> None:
        """
        Publish immutable audit event

        Args:
            event_type: Type of audit event
            context: Request context
            details: Event details
        """
        event = {
            "event_type": event_type,
            "timestamp": datetime.utcnow().isoformat(),
            "request_id": context.request_id,
            "trace_id": context.trace_id,
            "consumer_id": context.consumer_id,
            "tenant_id": context.tenant_id,
            "details": details,
            "immutable": True,
        }

        # Publish to L01 Event Store (immutable, time-locked)
        await self.event_store.publish_audit_event(event)

    async def _emit_metrics(
        self,
        context: RequestContext,
        response: GatewayResponse,
        latency_ms: float,
        error_code: Optional[str],
    ) -> None:
        """Emit Prometheus metrics"""
        if not self.metrics_client:
            return

        labels = {
            "method": context.metadata.method,
            "status": str(response.status_code),
            "route": "unknown",  # Set by caller
        }

        # Request duration histogram
        self.metrics_client.histogram(
            "http_request_duration_seconds",
            latency_ms / 1000.0,
            labels=labels,
        )

        # Request counter
        self.metrics_client.counter(
            "http_requests_total",
            1,
            labels=labels,
        )

        # Error counter
        if response.status_code >= 400:
            error_labels = {**labels, "error_code": error_code or "unknown"}
            self.metrics_client.counter(
                "http_request_errors_total",
                1,
                labels=error_labels,
            )

        # Rate limit violations
        if response.status_code == 429:
            self.metrics_client.counter(
                "rate_limit_violations_total",
                1,
                labels={"consumer_id": context.consumer_id or "unknown"},
            )

        # Idempotency cache hits
        if context.is_replayed:
            self.metrics_client.counter(
                "idempotency_cache_hits_total",
                1,
            )

    def _should_sample(self) -> bool:
        """Decide if should sample this request"""
        import random
        return random.random() < self.log_sampling_rate

    def _redact_path(self, path: str) -> str:
        """Redact sensitive path parameters"""
        # In production, implement proper PII redaction
        # For now, return as-is
        return path

    async def emit_circuit_breaker_event(
        self,
        backend_id: str,
        old_state: str,
        new_state: str,
        reason: str,
    ) -> None:
        """Emit circuit breaker state transition event"""
        event = {
            "event_type": "CircuitBreakerStateChange",
            "timestamp": datetime.utcnow().isoformat(),
            "backend_id": backend_id,
            "old_state": old_state,
            "new_state": new_state,
            "reason": reason,
        }

        await self.event_store.publish_event(event)

    async def emit_webhook_delivery_event(
        self,
        operation_id: str,
        status: str,
        attempt: int,
        error: Optional[str] = None,
    ) -> None:
        """Emit webhook delivery event"""
        event = {
            "event_type": "WebhookDeliveryEvent",
            "timestamp": datetime.utcnow().isoformat(),
            "operation_id": operation_id,
            "status": status,
            "attempt": attempt,
            "error": error,
        }

        await self.event_store.publish_event(event)
