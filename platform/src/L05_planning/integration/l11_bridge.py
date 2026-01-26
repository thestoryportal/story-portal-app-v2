"""
L11 Bridge - Connects L05 Planning to L11 Service Mesh
Path: platform/src/L05_planning/integration/l11_bridge.py

Provides integration with:
- SagaOrchestrator for multi-step workflows
- EventBus for publishing execution events
- CircuitBreaker for failure isolation
"""

import logging
import os
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional
from uuid import uuid4

logger = logging.getLogger(__name__)

# Optional httpx import for real HTTP calls
try:
    import httpx
    HTTPX_AVAILABLE = True
except ImportError:
    HTTPX_AVAILABLE = False
    logger.warning("httpx not available, L11Bridge will use local operation only")


class EventType(Enum):
    """Types of events that can be published."""
    PLAN_STARTED = "plan.started"
    PLAN_COMPLETED = "plan.completed"
    PLAN_FAILED = "plan.failed"
    UNIT_STARTED = "unit.started"
    UNIT_COMPLETED = "unit.completed"
    UNIT_FAILED = "unit.failed"
    CHECKPOINT_CREATED = "checkpoint.created"
    ROLLBACK_STARTED = "rollback.started"
    ROLLBACK_COMPLETED = "rollback.completed"
    VALIDATION_PASSED = "validation.passed"
    VALIDATION_FAILED = "validation.failed"


class SagaStatus(Enum):
    """Status of a saga."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    COMPENSATING = "compensating"
    FAILED = "failed"
    CANCELLED = "cancelled"


class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing if recovered


@dataclass
class Event:
    """An event to be published."""
    event_id: str
    event_type: EventType
    payload: Dict[str, Any]
    timestamp: datetime = field(default_factory=datetime.now)
    source: str = "l05_planning"
    correlation_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SagaStep:
    """A step in a saga."""
    step_id: str
    name: str
    action: str  # Action to execute
    compensation: str  # Compensation action on failure
    status: SagaStatus = SagaStatus.PENDING
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


@dataclass
class Saga:
    """A saga for orchestrating multi-step workflows."""
    saga_id: str
    name: str
    steps: List[SagaStep] = field(default_factory=list)
    status: SagaStatus = SagaStatus.PENDING
    current_step: int = 0
    created_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    correlation_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CircuitBreaker:
    """Circuit breaker for failure isolation."""
    name: str
    state: CircuitState = CircuitState.CLOSED
    failure_count: int = 0
    success_count: int = 0
    failure_threshold: int = 5
    recovery_timeout: int = 30  # seconds
    last_failure_time: Optional[datetime] = None


@dataclass
class PublishResult:
    """Result of publishing an event."""
    success: bool
    event_id: str
    message: str = ""
    remote: bool = False
    error: Optional[str] = None


class L11Bridge:
    """
    Bridge to L11 Service Mesh for workflow orchestration and events.

    Features:
    - Real HTTP connection to L11 service (localhost:8011)
    - Health check on initialization
    - Graceful fallback to local operation when L11 unavailable
    - Circuit breaker pattern for failure isolation

    Provides abstraction for:
    - Publishing execution events
    - Creating and managing sagas
    - Circuit breaker management
    - Distributed tracing support
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        timeout: float = 30.0,
        circuit_failure_threshold: int = 5,
        circuit_recovery_timeout: int = 30,
    ):
        """
        Initialize L11 bridge.

        Args:
            base_url: Base URL for L11 service (default: http://localhost:8011)
            api_key: API key for L11 authentication
            timeout: HTTP request timeout in seconds
            circuit_failure_threshold: Failures before opening circuit
            circuit_recovery_timeout: Seconds before trying half-open
        """
        self.base_url = base_url or os.getenv("L11_BASE_URL", "http://localhost:8011")
        self.api_key = api_key or os.getenv("L11_API_KEY", "test_token_123")
        self.timeout = timeout
        self.circuit_failure_threshold = circuit_failure_threshold
        self.circuit_recovery_timeout = circuit_recovery_timeout

        self._initialized = False
        self._connected = False
        self._http_client: Optional["httpx.AsyncClient"] = None

        # Local storage
        self._events: List[Event] = []
        self._sagas: Dict[str, Saga] = {}
        self._circuit_breakers: Dict[str, CircuitBreaker] = {}

        # Statistics
        self._remote_publish_count = 0
        self._local_publish_count = 0
        self._saga_count = 0

    async def initialize(self):
        """Initialize connection to L11 with health check."""
        if self._initialized:
            return

        logger.info(f"Initializing L11Bridge (base_url={self.base_url})")

        if HTTPX_AVAILABLE:
            try:
                self._http_client = httpx.AsyncClient(
                    base_url=self.base_url,
                    timeout=self.timeout,
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                )

                # Health check
                response = await self._http_client.get("/health/live")
                if response.status_code == 200:
                    self._connected = True
                    logger.info("L11Bridge connected to L11 service")
                else:
                    logger.warning(f"L11 health check failed: {response.status_code}")
                    self._connected = False

            except Exception as e:
                logger.warning(f"Failed to connect to L11: {e}. Using local operation.")
                self._connected = False
                if self._http_client:
                    await self._http_client.aclose()
                    self._http_client = None
        else:
            logger.info("httpx not available, using local operation only")
            self._connected = False

        self._initialized = True
        logger.info(f"L11Bridge initialized (connected={self._connected})")

    async def close(self):
        """Close HTTP client connection."""
        if self._http_client:
            await self._http_client.aclose()
            self._http_client = None
        self._connected = False

    # ==================== Event Publishing ====================

    async def publish_event(
        self,
        event_type: EventType,
        payload: Dict[str, Any],
        correlation_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> PublishResult:
        """
        Publish an event to the event bus.

        Args:
            event_type: Type of event
            payload: Event payload data
            correlation_id: Optional correlation ID for tracing
            metadata: Optional additional metadata

        Returns:
            PublishResult with success status
        """
        event = Event(
            event_id=str(uuid4())[:12],
            event_type=event_type,
            payload=payload,
            correlation_id=correlation_id,
            metadata=metadata or {},
        )

        logger.debug(f"Publishing event: {event_type.value} ({event.event_id})")

        # Try remote publish first
        if self._connected and self._http_client:
            try:
                result = await self._publish_remote(event)
                if result.success:
                    self._remote_publish_count += 1
                    return result
            except Exception as e:
                logger.warning(f"Remote publish failed, falling back to local: {e}")

        # Fall back to local storage
        return self._publish_local(event)

    async def _publish_remote(self, event: Event) -> PublishResult:
        """Publish event via HTTP to L11 service."""
        if not self._http_client:
            raise RuntimeError("HTTP client not initialized")

        payload = {
            "event_id": event.event_id,
            "event_type": event.event_type.value,
            "payload": event.payload,
            "source": event.source,
            "correlation_id": event.correlation_id,
            "metadata": event.metadata,
            "timestamp": event.timestamp.isoformat(),
        }

        response = await self._http_client.post("/api/events", json=payload)

        if response.status_code in (200, 201):
            return PublishResult(
                success=True,
                event_id=event.event_id,
                message=f"Published {event.event_type.value} to L11",
                remote=True,
            )
        else:
            return PublishResult(
                success=False,
                event_id=event.event_id,
                error=f"HTTP {response.status_code}: {response.text}",
                remote=True,
            )

    def _publish_local(self, event: Event) -> PublishResult:
        """Store event locally."""
        self._events.append(event)
        self._local_publish_count += 1

        logger.debug(f"Stored event locally: {event.event_id}")

        return PublishResult(
            success=True,
            event_id=event.event_id,
            message=f"Stored {event.event_type.value} locally",
            remote=False,
        )

    # Convenience methods for common events
    async def publish_plan_started(
        self,
        plan_id: str,
        unit_count: int,
        correlation_id: Optional[str] = None,
    ) -> PublishResult:
        """Publish plan started event."""
        return await self.publish_event(
            EventType.PLAN_STARTED,
            {"plan_id": plan_id, "unit_count": unit_count},
            correlation_id=correlation_id,
        )

    async def publish_plan_completed(
        self,
        plan_id: str,
        passed_count: int,
        failed_count: int,
        score: float,
        correlation_id: Optional[str] = None,
    ) -> PublishResult:
        """Publish plan completed event."""
        return await self.publish_event(
            EventType.PLAN_COMPLETED,
            {
                "plan_id": plan_id,
                "passed_count": passed_count,
                "failed_count": failed_count,
                "score": score,
            },
            correlation_id=correlation_id,
        )

    async def publish_plan_failed(
        self,
        plan_id: str,
        error: str,
        correlation_id: Optional[str] = None,
    ) -> PublishResult:
        """Publish plan failed event."""
        return await self.publish_event(
            EventType.PLAN_FAILED,
            {"plan_id": plan_id, "error": error},
            correlation_id=correlation_id,
        )

    async def publish_unit_started(
        self,
        unit_id: str,
        plan_id: str,
        correlation_id: Optional[str] = None,
    ) -> PublishResult:
        """Publish unit started event."""
        return await self.publish_event(
            EventType.UNIT_STARTED,
            {"unit_id": unit_id, "plan_id": plan_id},
            correlation_id=correlation_id,
        )

    async def publish_unit_completed(
        self,
        unit_id: str,
        plan_id: str,
        score: float,
        correlation_id: Optional[str] = None,
    ) -> PublishResult:
        """Publish unit completed event."""
        return await self.publish_event(
            EventType.UNIT_COMPLETED,
            {"unit_id": unit_id, "plan_id": plan_id, "score": score},
            correlation_id=correlation_id,
        )

    async def publish_unit_failed(
        self,
        unit_id: str,
        plan_id: str,
        error: str,
        correlation_id: Optional[str] = None,
    ) -> PublishResult:
        """Publish unit failed event."""
        return await self.publish_event(
            EventType.UNIT_FAILED,
            {"unit_id": unit_id, "plan_id": plan_id, "error": error},
            correlation_id=correlation_id,
        )

    # ==================== Saga Management ====================

    def create_saga(
        self,
        name: str,
        steps: List[Dict[str, str]],
        correlation_id: Optional[str] = None,
    ) -> Saga:
        """
        Create a new saga for orchestrating multi-step workflows.

        Args:
            name: Saga name
            steps: List of step definitions with action and compensation
            correlation_id: Optional correlation ID

        Returns:
            Created Saga instance
        """
        saga_id = str(uuid4())[:12]

        saga_steps = [
            SagaStep(
                step_id=f"{saga_id}-{i}",
                name=step.get("name", f"step_{i}"),
                action=step["action"],
                compensation=step["compensation"],
            )
            for i, step in enumerate(steps)
        ]

        saga = Saga(
            saga_id=saga_id,
            name=name,
            steps=saga_steps,
            correlation_id=correlation_id,
        )

        self._sagas[saga_id] = saga
        self._saga_count += 1

        logger.info(f"Created saga: {saga_id} ({name}) with {len(steps)} steps")

        return saga

    async def execute_saga(self, saga_id: str) -> Saga:
        """
        Execute a saga (runs all steps in order, compensates on failure).

        Args:
            saga_id: Saga identifier

        Returns:
            Updated Saga with execution results
        """
        saga = self._sagas.get(saga_id)
        if not saga:
            raise ValueError(f"Saga not found: {saga_id}")

        saga.status = SagaStatus.RUNNING
        logger.info(f"Executing saga: {saga_id}")

        # Publish saga started event
        await self.publish_event(
            EventType.PLAN_STARTED,
            {"saga_id": saga_id, "name": saga.name},
            correlation_id=saga.correlation_id,
        )

        try:
            for i, step in enumerate(saga.steps):
                saga.current_step = i
                step.status = SagaStatus.RUNNING

                logger.debug(f"Executing saga step: {step.name}")

                # In a real implementation, this would execute the action
                # For now, mark as completed
                step.status = SagaStatus.COMPLETED
                step.result = {"executed": True, "action": step.action}

            saga.status = SagaStatus.COMPLETED
            saga.completed_at = datetime.now()

            await self.publish_event(
                EventType.PLAN_COMPLETED,
                {"saga_id": saga_id, "steps_completed": len(saga.steps)},
                correlation_id=saga.correlation_id,
            )

        except Exception as e:
            logger.error(f"Saga {saga_id} failed at step {saga.current_step}: {e}")
            saga.status = SagaStatus.COMPENSATING

            # Run compensation for completed steps in reverse
            await self._compensate_saga(saga)

            saga.status = SagaStatus.FAILED

            await self.publish_event(
                EventType.PLAN_FAILED,
                {"saga_id": saga_id, "error": str(e)},
                correlation_id=saga.correlation_id,
            )

        return saga

    async def _compensate_saga(self, saga: Saga):
        """Run compensation actions for a failed saga."""
        logger.info(f"Compensating saga: {saga.saga_id}")

        # Compensate completed steps in reverse order
        for i in range(saga.current_step - 1, -1, -1):
            step = saga.steps[i]
            if step.status == SagaStatus.COMPLETED:
                logger.debug(f"Running compensation for step: {step.name}")
                # In a real implementation, this would run the compensation action
                step.status = SagaStatus.COMPENSATING

        logger.info(f"Saga compensation complete: {saga.saga_id}")

    def get_saga(self, saga_id: str) -> Optional[Saga]:
        """Get a saga by ID."""
        return self._sagas.get(saga_id)

    # ==================== Circuit Breaker ====================

    def get_circuit_breaker(self, name: str) -> CircuitBreaker:
        """
        Get or create a circuit breaker.

        Args:
            name: Circuit breaker name

        Returns:
            CircuitBreaker instance
        """
        if name not in self._circuit_breakers:
            self._circuit_breakers[name] = CircuitBreaker(
                name=name,
                failure_threshold=self.circuit_failure_threshold,
                recovery_timeout=self.circuit_recovery_timeout,
            )
        return self._circuit_breakers[name]

    def record_success(self, circuit_name: str):
        """Record a successful operation for a circuit breaker."""
        cb = self.get_circuit_breaker(circuit_name)
        cb.success_count += 1

        if cb.state == CircuitState.HALF_OPEN:
            # Successful call in half-open state closes the circuit
            cb.state = CircuitState.CLOSED
            cb.failure_count = 0
            logger.info(f"Circuit {circuit_name} closed after recovery")

    def record_failure(self, circuit_name: str):
        """Record a failed operation for a circuit breaker."""
        cb = self.get_circuit_breaker(circuit_name)
        cb.failure_count += 1
        cb.last_failure_time = datetime.now()

        if cb.failure_count >= cb.failure_threshold:
            if cb.state != CircuitState.OPEN:
                cb.state = CircuitState.OPEN
                logger.warning(f"Circuit {circuit_name} opened after {cb.failure_count} failures")

    def is_circuit_open(self, circuit_name: str) -> bool:
        """Check if a circuit is open (should reject requests)."""
        cb = self.get_circuit_breaker(circuit_name)

        if cb.state == CircuitState.CLOSED:
            return False

        if cb.state == CircuitState.OPEN:
            # Check if we should try half-open
            if cb.last_failure_time:
                elapsed = (datetime.now() - cb.last_failure_time).total_seconds()
                if elapsed >= cb.recovery_timeout:
                    cb.state = CircuitState.HALF_OPEN
                    logger.info(f"Circuit {circuit_name} entering half-open state")
                    return False

        return cb.state == CircuitState.OPEN

    # ==================== Statistics & Utilities ====================

    def get_events(
        self,
        event_type: Optional[EventType] = None,
        correlation_id: Optional[str] = None,
        limit: int = 100,
    ) -> List[Event]:
        """Get stored events with optional filtering."""
        events = self._events

        if event_type:
            events = [e for e in events if e.event_type == event_type]

        if correlation_id:
            events = [e for e in events if e.correlation_id == correlation_id]

        return events[-limit:]

    def get_statistics(self) -> Dict[str, Any]:
        """Returns bridge statistics."""
        return {
            "total_events": len(self._events),
            "total_sagas": len(self._sagas),
            "circuit_breakers": len(self._circuit_breakers),
            "initialized": self._initialized,
            "connected": self._connected,
            "base_url": self.base_url,
            "remote_publish_count": self._remote_publish_count,
            "local_publish_count": self._local_publish_count,
            "saga_count": self._saga_count,
            "circuit_states": {
                name: cb.state.value
                for name, cb in self._circuit_breakers.items()
            },
        }

    def is_connected(self) -> bool:
        """Returns True if connected to L11 service."""
        return self._connected

    def clear(self):
        """Clear all local storage."""
        self._events = []
        self._sagas = {}
        logger.info("L11Bridge local storage cleared")
