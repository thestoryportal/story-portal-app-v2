"""
L09 API Gateway Layer

Provides external API access with authentication, authorization, rate limiting,
and request routing to backend services.

Core Components:
- Request Router: Path-based routing to backend services
- Authentication Handler: API Key, OAuth/JWT, mTLS authentication
- Authorization Engine: RBAC, OAuth scopes, ABAC policy enforcement
- Rate Limiter: Distributed token bucket with Redis
- Idempotency Handler: 24-hour request deduplication
- Backend Executor: Circuit breaker with 4-state machine
- Async Handler: 202 responses with webhook delivery
- Request Validator: Input validation and sanitization
- Response Formatter: Response formatting and header injection
- Event Publisher: Audit logs and metrics emission

Error Code Range: E9000-E9999
"""

from .models import (
    RequestContext,
    ConsumerProfile,
    RouteDefinition,
    RateLimitTier,
    CircuitBreakerState,
    OperationStatus,
)

from .services import (
    AuthenticationHandler,
    AuthorizationEngine,
    RateLimiter,
    IdempotencyHandler,
    RequestRouter,
    RequestValidator,
    BackendExecutor,
    AsyncHandler,
    ResponseFormatter,
    EventPublisher,
)

from .gateway import APIGateway

__version__ = "1.2.0"

__all__ = [
    # Models
    "RequestContext",
    "ConsumerProfile",
    "RouteDefinition",
    "RateLimitTier",
    "CircuitBreakerState",
    "OperationStatus",
    # Services
    "AuthenticationHandler",
    "AuthorizationEngine",
    "RateLimiter",
    "IdempotencyHandler",
    "RequestRouter",
    "RequestValidator",
    "BackendExecutor",
    "AsyncHandler",
    "ResponseFormatter",
    "EventPublisher",
    # Main Gateway
    "APIGateway",
]
