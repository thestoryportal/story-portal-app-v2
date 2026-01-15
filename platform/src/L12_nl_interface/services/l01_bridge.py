"""L01 Bridge for L12 Natural Language Interface.

This module implements the L12Bridge class for tracking L12 service
invocations to the L01 Data Layer. It records usage metrics including
service calls, latency, errors, and user patterns.

Key features:
- Async event recording to L01 EventStore
- Graceful degradation when L01 unavailable
- Batching support for high-volume scenarios
- Fire-and-forget with timeout (non-blocking)
- Comprehensive usage metrics tracking

Example:
    >>> bridge = L12Bridge(base_url="http://localhost:8002")
    >>> await bridge.start()
    >>> await bridge.record_invocation(
    ...     session_id="session-123",
    ...     service_name="PlanningService",
    ...     method_name="create_plan",
    ...     parameters={"goal": "test"},
    ...     result={"plan_id": "plan-456"},
    ...     execution_time_ms=123.45,
    ...     status="success"
    ... )
"""

import asyncio
import logging
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID, uuid4

import httpx

logger = logging.getLogger(__name__)


@dataclass
class UsageMetrics:
    """Usage metrics for L12 service invocations.

    Attributes:
        total_invocations: Total number of service invocations
        successful_invocations: Number of successful invocations
        failed_invocations: Number of failed invocations
        total_latency_ms: Total execution time in milliseconds
        avg_latency_ms: Average execution time per invocation
        services_used: Set of unique service names used
        methods_used: Set of unique method names used
    """

    total_invocations: int = 0
    successful_invocations: int = 0
    failed_invocations: int = 0
    total_latency_ms: float = 0.0
    avg_latency_ms: float = 0.0
    services_used: set = field(default_factory=set)
    methods_used: set = field(default_factory=set)

    def update(
        self,
        service_name: str,
        method_name: str,
        execution_time_ms: float,
        success: bool,
    ):
        """Update metrics with new invocation data.

        Args:
            service_name: Service name
            method_name: Method name
            execution_time_ms: Execution time in milliseconds
            success: Whether invocation was successful
        """
        self.total_invocations += 1
        if success:
            self.successful_invocations += 1
        else:
            self.failed_invocations += 1

        self.total_latency_ms += execution_time_ms
        self.avg_latency_ms = self.total_latency_ms / self.total_invocations

        self.services_used.add(service_name)
        self.methods_used.add(method_name)

    def to_dict(self) -> Dict[str, Any]:
        """Convert metrics to dictionary.

        Returns:
            Dictionary with metrics
        """
        return {
            "total_invocations": self.total_invocations,
            "successful_invocations": self.successful_invocations,
            "failed_invocations": self.failed_invocations,
            "total_latency_ms": self.total_latency_ms,
            "avg_latency_ms": self.avg_latency_ms,
            "services_used": list(self.services_used),
            "methods_used": list(self.methods_used),
        }


@dataclass
class InvocationEvent:
    """Invocation event for batching.

    Attributes:
        session_id: Session identifier
        service_name: Service name
        method_name: Method name
        parameters: Method parameters
        result: Method result (or error)
        execution_time_ms: Execution time in milliseconds
        status: Invocation status ("success" or "error")
        timestamp: Event timestamp
    """

    session_id: str
    service_name: str
    method_name: str
    parameters: Dict[str, Any]
    result: Any
    execution_time_ms: float
    status: str
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def to_event_create(self) -> Dict[str, Any]:
        """Convert to EventCreate format for L01.

        Returns:
            Dictionary in EventCreate format
        """
        return {
            "event_type": "l12.service_invoked",
            "aggregate_type": "l12_session",
            "aggregate_id": self.session_id,
            "payload": {
                "service_name": self.service_name,
                "method_name": self.method_name,
                "parameters": self.parameters,
                "result": self.result if self.status == "success" else None,
                "error": str(self.result) if self.status == "error" else None,
                "execution_time_ms": self.execution_time_ms,
                "status": self.status,
            },
            "metadata": {
                "source": "L12_nl_interface",
                "timestamp": self.timestamp.isoformat(),
            },
            "version": 1,
        }


class L12Bridge:
    """Bridge for recording L12 usage to L01 Data Layer.

    The L12Bridge tracks all service invocations through the L12 Natural
    Language Interface and records them as events in the L01 Data Layer.
    It provides usage analytics and supports graceful degradation when
    L01 is unavailable.

    Attributes:
        base_url: L01 Data Layer base URL
        timeout_seconds: Request timeout in seconds
        batch_size: Number of events to batch before sending
        batch_interval_seconds: Maximum time to wait before sending batch
        metrics: Global usage metrics
        enabled: Whether bridge is enabled

    Example:
        >>> bridge = L12Bridge(base_url="http://localhost:8002")
        >>> await bridge.start()
        >>> await bridge.record_invocation(...)
        >>> metrics = bridge.get_metrics()
        >>> await bridge.stop()
    """

    def __init__(
        self,
        base_url: str = "http://localhost:8002",
        timeout_seconds: float = 5.0,
        batch_size: int = 10,
        batch_interval_seconds: float = 5.0,
        enabled: bool = True,
    ):
        """Initialize L01 bridge.

        Args:
            base_url: L01 Data Layer base URL
            timeout_seconds: Request timeout in seconds
            batch_size: Number of events to batch before sending
            batch_interval_seconds: Maximum time to wait before sending batch
            enabled: Whether bridge is enabled
        """
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self.batch_size = batch_size
        self.batch_interval_seconds = batch_interval_seconds
        self.enabled = enabled

        # HTTP client
        self.client: Optional[httpx.AsyncClient] = None

        # Metrics
        self.metrics = UsageMetrics()

        # Batching
        self.event_queue: deque = deque()
        self.batch_task: Optional[asyncio.Task] = None
        self.running = False

        # L01 availability tracking
        self.l01_available = True
        self.consecutive_failures = 0
        self.max_consecutive_failures = 3

        logger.info(
            f"L12Bridge initialized: url={base_url}, timeout={timeout_seconds}s, "
            f"batch_size={batch_size}, enabled={enabled}"
        )

    async def start(self):
        """Start the bridge and background tasks."""
        if not self.enabled:
            logger.info("L12Bridge disabled, skipping start")
            return

        self.client = httpx.AsyncClient(timeout=self.timeout_seconds)
        self.running = True

        # Start batch processing task
        self.batch_task = asyncio.create_task(self._batch_processor())

        logger.info("L12Bridge started")

    async def stop(self):
        """Stop the bridge and flush pending events."""
        if not self.enabled:
            return

        self.running = False

        # Cancel batch task
        if self.batch_task:
            self.batch_task.cancel()
            try:
                await self.batch_task
            except asyncio.CancelledError:
                pass

        # Flush remaining events
        await self._flush_batch()

        # Close HTTP client
        if self.client:
            await self.client.aclose()

        logger.info("L12Bridge stopped")

    async def record_invocation(
        self,
        session_id: str,
        service_name: str,
        method_name: str,
        parameters: Dict[str, Any],
        result: Any,
        execution_time_ms: float,
        status: str,
    ):
        """Record service invocation to L01.

        This method is non-blocking and will not fail the service invocation
        if L01 is unavailable. Events are batched for efficiency.

        Args:
            session_id: Session identifier
            service_name: Service name
            method_name: Method name
            parameters: Method parameters
            result: Method result (or error message)
            execution_time_ms: Execution time in milliseconds
            status: Invocation status ("success" or "error")

        Example:
            >>> await bridge.record_invocation(
            ...     session_id="session-123",
            ...     service_name="PlanningService",
            ...     method_name="create_plan",
            ...     parameters={"goal": "test"},
            ...     result={"plan_id": "plan-456"},
            ...     execution_time_ms=123.45,
            ...     status="success"
            ... )
        """
        if not self.enabled:
            return

        # Update local metrics immediately
        self.metrics.update(
            service_name, method_name, execution_time_ms, status == "success"
        )

        # Skip recording if L01 is unavailable (after max failures)
        if not self.l01_available:
            logger.debug(
                f"L01 unavailable, skipping event recording for {service_name}.{method_name}"
            )
            return

        # Create event
        event = InvocationEvent(
            session_id=session_id,
            service_name=service_name,
            method_name=method_name,
            parameters=parameters,
            result=result,
            execution_time_ms=execution_time_ms,
            status=status,
        )

        # Add to batch queue
        self.event_queue.append(event)

        # Flush if batch size reached
        if len(self.event_queue) >= self.batch_size:
            asyncio.create_task(self._flush_batch())

    async def _batch_processor(self):
        """Background task to flush batches periodically."""
        while self.running:
            try:
                await asyncio.sleep(self.batch_interval_seconds)
                await self._flush_batch()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in batch processor: {e}", exc_info=True)

    async def _flush_batch(self):
        """Flush pending events to L01."""
        if not self.event_queue:
            return

        # Get all pending events
        events_to_send = []
        while self.event_queue:
            events_to_send.append(self.event_queue.popleft())

        if not events_to_send:
            return

        logger.debug(f"Flushing {len(events_to_send)} events to L01")

        # Send events to L01 (fire-and-forget with timeout)
        try:
            await self._send_events_to_l01(events_to_send)
            self.consecutive_failures = 0
            self.l01_available = True
        except Exception as e:
            self.consecutive_failures += 1
            logger.warning(
                f"Failed to send events to L01 (attempt {self.consecutive_failures}/{self.max_consecutive_failures}): {e}"
            )

            # Mark L01 as unavailable after max failures
            if self.consecutive_failures >= self.max_consecutive_failures:
                self.l01_available = False
                logger.error(
                    f"L01 marked as unavailable after {self.consecutive_failures} failures"
                )

    async def _send_events_to_l01(self, events: list[InvocationEvent]):
        """Send events to L01 EventStore.

        Args:
            events: List of invocation events to send

        Raises:
            Exception: If request fails or times out
        """
        if not self.client:
            raise RuntimeError("L12Bridge not started (client is None)")

        # Send each event individually (L01 API expects one event per request)
        for event in events:
            event_data = event.to_event_create()

            # Convert session_id string to UUID
            # For L12, we'll use a deterministic UUID based on session_id
            # This allows us to track all events for a session
            import hashlib

            session_uuid = UUID(
                hashlib.md5(event.session_id.encode()).hexdigest()
            )
            event_data["aggregate_id"] = str(session_uuid)

            try:
                response = await self.client.post(
                    f"{self.base_url}/events/", json=event_data
                )
                response.raise_for_status()
            except httpx.TimeoutException:
                logger.warning(f"Timeout sending event to L01 for {event.service_name}.{event.method_name}")
                raise
            except httpx.HTTPError as e:
                logger.warning(f"HTTP error sending event to L01: {e}")
                raise
            except Exception as e:
                logger.warning(f"Unexpected error sending event to L01: {e}")
                raise

    def get_metrics(self) -> Dict[str, Any]:
        """Get current usage metrics.

        Returns:
            Dictionary with usage metrics

        Example:
            >>> metrics = bridge.get_metrics()
            >>> print(f"Total invocations: {metrics['total_invocations']}")
        """
        return {
            **self.metrics.to_dict(),
            "l01_available": self.l01_available,
            "consecutive_failures": self.consecutive_failures,
            "pending_events": len(self.event_queue),
        }

    def reset_metrics(self):
        """Reset usage metrics.

        Example:
            >>> bridge.reset_metrics()
        """
        self.metrics = UsageMetrics()
        logger.info("L12Bridge metrics reset")

    async def health_check(self) -> bool:
        """Check if L01 is available.

        Returns:
            True if L01 is available, False otherwise

        Example:
            >>> if await bridge.health_check():
            ...     print("L01 is available")
        """
        if not self.enabled or not self.client:
            return False

        try:
            response = await self.client.get(
                f"{self.base_url}/health", timeout=2.0
            )
            response.raise_for_status()
            self.l01_available = True
            self.consecutive_failures = 0
            return True
        except Exception as e:
            logger.warning(f"L01 health check failed: {e}")
            return False
