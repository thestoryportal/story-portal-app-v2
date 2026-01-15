"""L11 Integration Layer - Data Models."""

from .error_codes import ErrorCode, IntegrationError, ERROR_MESSAGES, RECOVERABLE_ERRORS
from .service import (
    ServiceInfo,
    ServiceStatus,
    HealthCheck,
    HealthCheckType,
)
from .circuit_breaker import (
    CircuitBreakerState,
    CircuitState,
    CircuitBreakerConfig,
)
from .event import (
    EventMessage,
    EventMetadata,
    EventPriority,
    EventHandler,
    EventSubscription,
)
from .saga import (
    SagaDefinition,
    SagaExecution,
    SagaStatus,
    SagaStep,
    StepStatus,
    StepAction,
    CompensationAction,
)
from .trace import (
    RequestContext,
    TraceSpan,
    SpanKind,
    SpanStatus,
    Metric,
)

__all__ = [
    # Error codes
    "ErrorCode",
    "IntegrationError",
    "ERROR_MESSAGES",
    "RECOVERABLE_ERRORS",
    # Service registry
    "ServiceInfo",
    "ServiceStatus",
    "HealthCheck",
    "HealthCheckType",
    # Circuit breaker
    "CircuitBreakerState",
    "CircuitState",
    "CircuitBreakerConfig",
    # Event bus
    "EventMessage",
    "EventMetadata",
    "EventPriority",
    "EventHandler",
    "EventSubscription",
    # Saga orchestration
    "SagaDefinition",
    "SagaExecution",
    "SagaStatus",
    "SagaStep",
    "StepStatus",
    "StepAction",
    "CompensationAction",
    # Tracing and observability
    "RequestContext",
    "TraceSpan",
    "SpanKind",
    "SpanStatus",
    "Metric",
]
