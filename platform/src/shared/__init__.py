"""
Shared utilities for the Agentic Platform.

This package contains common functionality used across all service layers.
"""

from .logging_config import (
    setup_logging,
    get_correlation_id,
    set_correlation_id,
    generate_correlation_id,
    get_request_id,
    set_request_id,
    generate_request_id,
    get_user_id,
    set_user_id,
    get_session_id,
    set_session_id,
    clear_context,
    LogContext,
    log_with_context,
)

from .middleware import (
    CorrelationIDMiddleware,
    RequestLoggingMiddleware,
    PerformanceMonitoringMiddleware,
    get_correlation_id_from_request,
    add_correlation_headers,
)

from .http_client import (
    CorrelatedHTTPClient,
    get_with_correlation,
    post_with_correlation,
)

from .errors import (
    ErrorCode,
    ErrorDetail,
    ErrorResponse,
    PlatformError,
    AuthenticationError,
    InvalidTokenError,
    ExpiredTokenError,
    MissingTokenError,
    AuthorizationError,
    ValidationError,
    InvalidInputError,
    MissingFieldError,
    ResourceError,
    NotFoundError,
    AlreadyExistsError,
    ConflictError,
    SystemError,
    DatabaseError,
    TimeoutError,
    ServiceUnavailableError,
    ExternalServiceError,
    ExternalServiceTimeoutError,
    RateLimitError,
    BusinessLogicError,
    InvalidStateError,
)

from .error_handlers import (
    register_error_handlers,
    raise_not_found,
    raise_already_exists,
    raise_validation_error,
    raise_authorization_error,
    raise_rate_limit_error,
    ErrorContext,
    handle_database_error,
    handle_external_service_error,
)

from .token_manager import (
    TokenType,
    TokenConfig,
    TokenPair,
    RefreshTokenData,
    TokenManager,
)

from .token_store import (
    TokenStore,
    PostgreSQLTokenStore,
    InMemoryTokenStore,
)

from .health import (
    HealthStatus,
    ComponentHealth,
    HealthCheckResponse,
    HealthCheck,
    DatabaseHealthCheck,
    RedisHealthCheck,
    HTTPServiceHealthCheck,
    CustomHealthCheck,
    HealthCheckManager,
    create_health_router,
    setup_health_checks,
)

from .service_discovery import (
    ConsulClient,
    ServiceInstance,
    ServiceRegistry,
    create_service_registry,
    register_with_consul,
)

from .config_manager import (
    EtcdClient,
    ConfigValue,
    ConfigManager,
    get_config,
    set_config,
)

from .openapi_utils import (
    customize_openapi,
    setup_swagger_ui,
    create_openapi_endpoint,
    add_common_responses,
    generate_service_openapi,
    setup_complete_api_docs,
)

from .events import (
    Event,
    EventBus,
    EventTypes,
    publish_event,
)

from .security_scanner import (
    SeverityLevel,
    SecurityIssue,
    SecurityScanResult,
    DependencyScanner,
    StaticCodeAnalyzer,
    SecretDetector,
    ContainerScanner,
    SecurityReportGenerator,
    SecurityScanner,
)

__all__ = [
    # Logging
    'setup_logging',
    'get_correlation_id',
    'set_correlation_id',
    'generate_correlation_id',
    'get_request_id',
    'set_request_id',
    'generate_request_id',
    'get_user_id',
    'set_user_id',
    'get_session_id',
    'set_session_id',
    'clear_context',
    'LogContext',
    'log_with_context',
    # Middleware
    'CorrelationIDMiddleware',
    'RequestLoggingMiddleware',
    'PerformanceMonitoringMiddleware',
    'get_correlation_id_from_request',
    'add_correlation_headers',
    # HTTP Client
    'CorrelatedHTTPClient',
    'get_with_correlation',
    'post_with_correlation',
    # Errors
    'ErrorCode',
    'ErrorDetail',
    'ErrorResponse',
    'PlatformError',
    'AuthenticationError',
    'InvalidTokenError',
    'ExpiredTokenError',
    'MissingTokenError',
    'AuthorizationError',
    'ValidationError',
    'InvalidInputError',
    'MissingFieldError',
    'ResourceError',
    'NotFoundError',
    'AlreadyExistsError',
    'ConflictError',
    'SystemError',
    'DatabaseError',
    'TimeoutError',
    'ServiceUnavailableError',
    'ExternalServiceError',
    'ExternalServiceTimeoutError',
    'RateLimitError',
    'BusinessLogicError',
    'InvalidStateError',
    # Error Handlers
    'register_error_handlers',
    'raise_not_found',
    'raise_already_exists',
    'raise_validation_error',
    'raise_authorization_error',
    'raise_rate_limit_error',
    'ErrorContext',
    'handle_database_error',
    'handle_external_service_error',
    # Token Management
    'TokenType',
    'TokenConfig',
    'TokenPair',
    'RefreshTokenData',
    'TokenManager',
    'TokenStore',
    'PostgreSQLTokenStore',
    'InMemoryTokenStore',
    # Health Checks
    'HealthStatus',
    'ComponentHealth',
    'HealthCheckResponse',
    'HealthCheck',
    'DatabaseHealthCheck',
    'RedisHealthCheck',
    'HTTPServiceHealthCheck',
    'CustomHealthCheck',
    'HealthCheckManager',
    'create_health_router',
    'setup_health_checks',
    # Service Discovery
    'ConsulClient',
    'ServiceInstance',
    'ServiceRegistry',
    'create_service_registry',
    'register_with_consul',
    # Configuration Management
    'EtcdClient',
    'ConfigValue',
    'ConfigManager',
    'get_config',
    'set_config',
    # OpenAPI Documentation
    'customize_openapi',
    'setup_swagger_ui',
    'create_openapi_endpoint',
    'add_common_responses',
    'generate_service_openapi',
    'setup_complete_api_docs',
    # Event System
    'Event',
    'EventBus',
    'EventTypes',
    'publish_event',
    # Security Scanner
    'SeverityLevel',
    'SecurityIssue',
    'SecurityScanResult',
    'DependencyScanner',
    'StaticCodeAnalyzer',
    'SecretDetector',
    'ContainerScanner',
    'SecurityReportGenerator',
    'SecurityScanner',
]
