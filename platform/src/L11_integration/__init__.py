"""
L11 Integration Layer

Cross-layer orchestration and service mesh coordination for the Agentic AI Workforce.

Provides:
- Service discovery and health tracking
- Event-driven integration (Redis Pub/Sub)
- Circuit breaker for failure isolation
- Request orchestration with tracing
- Saga orchestration for multi-step workflows
- Observability (traces and metrics)

Error Code Range: E11000-E11999
"""

from .models import (
    # Error codes
    ErrorCode,
    IntegrationError,
    # Service registry
    ServiceInfo,
    ServiceStatus,
    HealthCheck,
    HealthCheckType,
    # Circuit breaker
    CircuitBreakerState,
    CircuitState,
    CircuitBreakerConfig,
    # Event bus
    EventMessage,
    EventMetadata,
    EventPriority,
    EventHandler,
    EventSubscription,
    # Saga orchestration
    SagaDefinition,
    SagaExecution,
    SagaStatus,
    SagaStep,
    StepStatus,
    # Tracing
    RequestContext,
    TraceSpan,
    SpanKind,
    SpanStatus,
    Metric,
)

from .services import (
    ServiceRegistry,
    EventBusManager,
    CircuitBreaker,
    CircuitBreakerMiddleware,
    RequestOrchestrator,
    SagaOrchestrator,
    ObservabilityCollector,
)

from .integration_layer import IntegrationLayer


__version__ = "0.1.0"

__all__ = [
    # Main class
    "IntegrationLayer",
    # Error codes
    "ErrorCode",
    "IntegrationError",
    # Service registry
    "ServiceRegistry",
    "ServiceInfo",
    "ServiceStatus",
    "HealthCheck",
    "HealthCheckType",
    # Event bus
    "EventBusManager",
    "EventMessage",
    "EventMetadata",
    "EventPriority",
    "EventHandler",
    "EventSubscription",
    # Circuit breaker
    "CircuitBreaker",
    "CircuitBreakerMiddleware",
    "CircuitBreakerState",
    "CircuitState",
    "CircuitBreakerConfig",
    # Request orchestration
    "RequestOrchestrator",
    "RequestContext",
    # Saga orchestration
    "SagaOrchestrator",
    "SagaDefinition",
    "SagaExecution",
    "SagaStatus",
    "SagaStep",
    "StepStatus",
    # Observability
    "ObservabilityCollector",
    "TraceSpan",
    "SpanKind",
    "SpanStatus",
    "Metric",
]
