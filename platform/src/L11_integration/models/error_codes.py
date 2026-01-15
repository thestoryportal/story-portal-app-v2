"""
L11 Integration Layer - Error Codes (E11000-E11999).

Error code ranges per specification:
- E11000-E11099: Service registry and discovery
- E11100-E11199: Event bus operations
- E11200-E11299: Circuit breaker
- E11300-E11399: Request orchestration
- E11400-E11499: Saga orchestration
- E11500-E11599: Observability and tracing
- E11600-E11699: Service mesh
- E11700-E11799: Configuration
- E11800-E11899: Health checking
- E11900-E11999: Generic integration errors
"""

from enum import Enum
from dataclasses import dataclass
from typing import Optional


class ErrorCode(str, Enum):
    """L11 Integration Layer error codes."""

    # E11000-E11099: Service registry and discovery
    E11000 = "E11000"  # SERVICE_REGISTRY_ERROR
    E11001 = "E11001"  # SERVICE_NOT_FOUND
    E11002 = "E11002"  # SERVICE_REGISTRATION_FAILED
    E11003 = "E11003"  # SERVICE_DEREGISTRATION_FAILED
    E11004 = "E11004"  # SERVICE_HEALTH_CHECK_FAILED
    E11005 = "E11005"  # SERVICE_DISCOVERY_FAILED
    E11006 = "E11006"  # INVALID_SERVICE_METADATA
    E11007 = "E11007"  # DUPLICATE_SERVICE_REGISTRATION

    # E11100-E11199: Event bus operations
    E11100 = "E11100"  # EVENT_BUS_ERROR
    E11101 = "E11101"  # EVENT_PUBLISH_FAILED
    E11102 = "E11102"  # EVENT_SUBSCRIBE_FAILED
    E11103 = "E11103"  # EVENT_UNSUBSCRIBE_FAILED
    E11104 = "E11104"  # EVENT_HANDLER_ERROR
    E11105 = "E11105"  # INVALID_EVENT_TOPIC
    E11106 = "E11106"  # INVALID_EVENT_PAYLOAD
    E11107 = "E11107"  # EVENT_DELIVERY_TIMEOUT
    E11108 = "E11108"  # DEAD_LETTER_QUEUE_FULL
    E11109 = "E11109"  # EVENT_SCHEMA_VALIDATION_FAILED

    # E11200-E11299: Circuit breaker
    E11200 = "E11200"  # CIRCUIT_BREAKER_ERROR
    E11201 = "E11201"  # CIRCUIT_BREAKER_OPEN
    E11202 = "E11202"  # CIRCUIT_BREAKER_HALF_OPEN
    E11203 = "E11203"  # FAILURE_THRESHOLD_EXCEEDED
    E11204 = "E11204"  # INVALID_CIRCUIT_BREAKER_CONFIG

    # E11300-E11399: Request orchestration
    E11300 = "E11300"  # REQUEST_ORCHESTRATION_ERROR
    E11301 = "E11301"  # REQUEST_ROUTING_FAILED
    E11302 = "E11302"  # REQUEST_TIMEOUT
    E11303 = "E11303"  # INVALID_REQUEST_CONTEXT
    E11304 = "E11304"  # CORRELATION_ID_MISSING
    E11305 = "E11305"  # REQUEST_TRANSFORMATION_FAILED
    E11306 = "E11306"  # RESPONSE_AGGREGATION_FAILED
    E11307 = "E11307"  # BACKPRESSURE_LIMIT_EXCEEDED

    # E11400-E11499: Saga orchestration
    E11400 = "E11400"  # SAGA_ORCHESTRATION_ERROR
    E11401 = "E11401"  # SAGA_STEP_FAILED
    E11402 = "E11402"  # SAGA_COMPENSATION_FAILED
    E11403 = "E11403"  # SAGA_TIMEOUT
    E11404 = "E11404"  # INVALID_SAGA_DEFINITION
    E11405 = "E11405"  # SAGA_STATE_PERSISTENCE_FAILED
    E11406 = "E11406"  # SAGA_NOT_FOUND

    # E11500-E11599: Observability and tracing
    E11500 = "E11500"  # OBSERVABILITY_ERROR
    E11501 = "E11501"  # TRACE_PROPAGATION_FAILED
    E11502 = "E11502"  # SPAN_CREATION_FAILED
    E11503 = "E11503"  # METRICS_COLLECTION_FAILED
    E11504 = "E11504"  # LOG_CORRELATION_FAILED
    E11505 = "E11505"  # INVALID_TRACE_CONTEXT

    # E11600-E11699: Service mesh
    E11600 = "E11600"  # SERVICE_MESH_ERROR
    E11601 = "E11601"  # MTLS_HANDSHAKE_FAILED
    E11602 = "E11602"  # CERTIFICATE_VALIDATION_FAILED
    E11603 = "E11603"  # LOAD_BALANCING_FAILED
    E11604 = "E11604"  # TRAFFIC_ROUTING_FAILED

    # E11700-E11799: Configuration
    E11700 = "E11700"  # CONFIGURATION_ERROR
    E11701 = "E11701"  # INVALID_CONFIGURATION
    E11702 = "E11702"  # CONFIGURATION_LOAD_FAILED
    E11703 = "E11703"  # CONFIGURATION_VALIDATION_FAILED

    # E11800-E11899: Health checking
    E11800 = "E11800"  # HEALTH_CHECK_ERROR
    E11801 = "E11801"  # HEALTH_CHECK_TIMEOUT
    E11802 = "E11802"  # ENDPOINT_UNAVAILABLE
    E11803 = "E11803"  # HEALTH_AGGREGATION_FAILED

    # E11900-E11999: Generic integration errors
    E11900 = "E11900"  # INTEGRATION_ERROR
    E11901 = "E11901"  # LAYER_COMMUNICATION_FAILED
    E11902 = "E11902"  # UNSUPPORTED_OPERATION
    E11903 = "E11903"  # INITIALIZATION_FAILED
    E11904 = "E11904"  # SHUTDOWN_FAILED


# Error code metadata
ERROR_MESSAGES = {
    # Service registry and discovery
    ErrorCode.E11000: "Service registry operation failed",
    ErrorCode.E11001: "Service not found in registry",
    ErrorCode.E11002: "Failed to register service",
    ErrorCode.E11003: "Failed to deregister service",
    ErrorCode.E11004: "Service health check failed",
    ErrorCode.E11005: "Service discovery operation failed",
    ErrorCode.E11006: "Invalid service metadata",
    ErrorCode.E11007: "Service already registered",

    # Event bus operations
    ErrorCode.E11100: "Event bus operation failed",
    ErrorCode.E11101: "Failed to publish event to event bus",
    ErrorCode.E11102: "Failed to subscribe to event topic",
    ErrorCode.E11103: "Failed to unsubscribe from event topic",
    ErrorCode.E11104: "Event handler encountered error",
    ErrorCode.E11105: "Invalid event topic name",
    ErrorCode.E11106: "Invalid event payload",
    ErrorCode.E11107: "Event delivery timeout exceeded",
    ErrorCode.E11108: "Dead letter queue is full",
    ErrorCode.E11109: "Event schema validation failed",

    # Circuit breaker
    ErrorCode.E11200: "Circuit breaker operation failed",
    ErrorCode.E11201: "Circuit breaker is open, requests blocked",
    ErrorCode.E11202: "Circuit breaker is half-open, limited requests allowed",
    ErrorCode.E11203: "Failure threshold exceeded",
    ErrorCode.E11204: "Invalid circuit breaker configuration",

    # Request orchestration
    ErrorCode.E11300: "Request orchestration failed",
    ErrorCode.E11301: "Failed to route request to destination service",
    ErrorCode.E11302: "Request timeout exceeded",
    ErrorCode.E11303: "Invalid request context",
    ErrorCode.E11304: "Correlation ID missing from request context",
    ErrorCode.E11305: "Request transformation failed",
    ErrorCode.E11306: "Response aggregation failed",
    ErrorCode.E11307: "Backpressure limit exceeded",

    # Saga orchestration
    ErrorCode.E11400: "Saga orchestration failed",
    ErrorCode.E11401: "Saga step execution failed",
    ErrorCode.E11402: "Saga compensation failed",
    ErrorCode.E11403: "Saga execution timeout exceeded",
    ErrorCode.E11404: "Invalid saga definition",
    ErrorCode.E11405: "Failed to persist saga state",
    ErrorCode.E11406: "Saga not found",

    # Observability and tracing
    ErrorCode.E11500: "Observability operation failed",
    ErrorCode.E11501: "Failed to propagate trace context",
    ErrorCode.E11502: "Failed to create trace span",
    ErrorCode.E11503: "Failed to collect metrics",
    ErrorCode.E11504: "Failed to correlate logs",
    ErrorCode.E11505: "Invalid trace context",

    # Service mesh
    ErrorCode.E11600: "Service mesh operation failed",
    ErrorCode.E11601: "mTLS handshake failed",
    ErrorCode.E11602: "Certificate validation failed",
    ErrorCode.E11603: "Load balancing failed",
    ErrorCode.E11604: "Traffic routing failed",

    # Configuration
    ErrorCode.E11700: "Configuration operation failed",
    ErrorCode.E11701: "Invalid configuration",
    ErrorCode.E11702: "Failed to load configuration",
    ErrorCode.E11703: "Configuration validation failed",

    # Health checking
    ErrorCode.E11800: "Health check operation failed",
    ErrorCode.E11801: "Health check timeout exceeded",
    ErrorCode.E11802: "Endpoint unavailable",
    ErrorCode.E11803: "Health aggregation failed",

    # Generic integration errors
    ErrorCode.E11900: "Generic integration error",
    ErrorCode.E11901: "Layer communication failed",
    ErrorCode.E11902: "Operation not supported",
    ErrorCode.E11903: "Integration layer initialization failed",
    ErrorCode.E11904: "Integration layer shutdown failed",
}


# Recoverable vs non-recoverable errors
RECOVERABLE_ERRORS = {
    ErrorCode.E11004,  # SERVICE_HEALTH_CHECK_FAILED
    ErrorCode.E11101,  # EVENT_PUBLISH_FAILED
    ErrorCode.E11107,  # EVENT_DELIVERY_TIMEOUT
    ErrorCode.E11201,  # CIRCUIT_BREAKER_OPEN
    ErrorCode.E11202,  # CIRCUIT_BREAKER_HALF_OPEN
    ErrorCode.E11302,  # REQUEST_TIMEOUT
    ErrorCode.E11401,  # SAGA_STEP_FAILED
    ErrorCode.E11403,  # SAGA_TIMEOUT
    ErrorCode.E11801,  # HEALTH_CHECK_TIMEOUT
    ErrorCode.E11802,  # ENDPOINT_UNAVAILABLE
}


@dataclass
class IntegrationError(Exception):
    """Base exception for L11 Integration Layer errors."""

    code: ErrorCode
    message: str
    details: Optional[dict] = None
    recovery_suggestion: Optional[str] = None

    def __str__(self) -> str:
        """String representation of error."""
        base = f"{self.code}: {self.message}"
        if self.details:
            base += f" | Details: {self.details}"
        if self.recovery_suggestion:
            base += f" | Suggestion: {self.recovery_suggestion}"
        return base

    @property
    def is_recoverable(self) -> bool:
        """Check if error is recoverable (retry allowed)."""
        return self.code in RECOVERABLE_ERRORS

    @classmethod
    def from_code(cls, code: ErrorCode, details: Optional[dict] = None,
                  recovery_suggestion: Optional[str] = None) -> "IntegrationError":
        """Create error from error code."""
        message = ERROR_MESSAGES.get(code, "Unknown integration error")
        return cls(code=code, message=message, details=details,
                   recovery_suggestion=recovery_suggestion)
