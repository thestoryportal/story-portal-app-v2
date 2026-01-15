"""
Error codes for L09 API Gateway Layer

Error Code Range: E9000-E9999

Categories:
- E9001-E9099: Routing errors
- E9101-E9199: Authentication errors
- E9201-E9299: Authorization errors
- E9301-E9399: Request validation errors
- E9401-E9499: Rate limiting errors
- E9501-E9599: Operations errors
- E9601-E9699: Async operations errors
- E9701-E9799: Webhook errors
- E9801-E9899: Circuit breaker errors
- E9901-E9999: Server errors
"""

from enum import Enum
from typing import Optional
from pydantic import BaseModel


class ErrorCode(str, Enum):
    """API Gateway error codes"""

    # Routing (E9001-E9099)
    E9001 = "E9001"  # Route not found
    E9002 = "E9002"  # Invalid API version
    E9003 = "E9003"  # Deprecated route

    # Authentication (E9101-E9199)
    E9101 = "E9101"  # Invalid API key
    E9102 = "E9102"  # Token expired
    E9103 = "E9103"  # Missing credentials
    E9104 = "E9104"  # Invalid JWT signature
    E9105 = "E9105"  # Invalid mTLS certificate
    E9106 = "E9106"  # Certificate revoked

    # Authorization (E9201-E9299)
    E9201 = "E9201"  # Authorization failed
    E9202 = "E9202"  # Consumer suspended
    E9203 = "E9203"  # Consumer not found
    E9204 = "E9204"  # Invalid consumer state
    E9205 = "E9205"  # Cross-tenant access attempt
    E9206 = "E9206"  # Role insufficient
    E9207 = "E9207"  # OAuth scope insufficient

    # Request Validation (E9301-E9399)
    E9301 = "E9301"  # Invalid idempotency key format
    E9302 = "E9302"  # Required parameter missing
    E9303 = "E9303"  # Parameter type mismatch
    E9304 = "E9304"  # Request body exceeds size limit
    E9305 = "E9305"  # Invalid JSON format
    E9306 = "E9306"  # Invalid character encoding
    E9307 = "E9307"  # Null byte detected
    E9308 = "E9308"  # Query string too long
    E9309 = "E9309"  # Header validation failed

    # Rate Limiting (E9401-E9499)
    E9401 = "E9401"  # Rate limit exceeded
    E9402 = "E9402"  # Daily quota exceeded
    E9403 = "E9403"  # Rate limit tier not found
    E9404 = "E9404"  # Burst capacity exceeded

    # Operations (E9501-E9599)
    E9501 = "E9501"  # Operation not found
    E9502 = "E9502"  # Operation creation failed
    E9503 = "E9503"  # Operation status unknown

    # Async Operations (E9601-E9699)
    E9601 = "E9601"  # Async operation error
    E9602 = "E9602"  # Operation not found
    E9603 = "E9603"  # Operation expired
    E9604 = "E9604"  # Operation already completed

    # Webhooks (E9701-E9799)
    E9701 = "E9701"  # Invalid webhook URL
    E9702 = "E9702"  # Webhook delivery failed
    E9703 = "E9703"  # Webhook signature invalid
    E9704 = "E9704"  # SSRF violation detected
    E9705 = "E9705"  # Webhook TLS certificate invalid
    E9706 = "E9706"  # Webhook timeout

    # Circuit Breaker (E9801-E9899)
    E9801 = "E9801"  # Circuit breaker open
    E9802 = "E9802"  # Backend unhealthy
    E9803 = "E9803"  # All replicas unavailable
    E9804 = "E9804"  # Connection pool exhausted

    # Server Errors (E9901-E9999)
    E9901 = "E9901"  # Internal server error
    E9902 = "E9902"  # Service unavailable
    E9903 = "E9903"  # Gateway timeout
    E9904 = "E9904"  # Bad gateway
    E9905 = "E9905"  # Configuration error
    E9906 = "E9906"  # Redis unavailable
    E9907 = "E9907"  # Database unavailable


class GatewayError(Exception):
    """Base exception for API Gateway errors"""

    def __init__(
        self,
        code: ErrorCode,
        message: str,
        http_status: int = 500,
        details: Optional[dict] = None,
    ):
        self.code = code
        self.message = message
        self.http_status = http_status
        self.details = details or {}
        super().__init__(message)

    def to_dict(self) -> dict:
        """Convert error to dictionary for response"""
        return {
            "error": {
                "code": self.code.value,
                "message": self.message,
                "details": self.details,
            }
        }


class RoutingError(GatewayError):
    """Routing errors"""
    def __init__(self, code: ErrorCode, message: str, details: Optional[dict] = None):
        super().__init__(code, message, 404, details)


class AuthenticationError(GatewayError):
    """Authentication errors"""
    def __init__(self, code: ErrorCode, message: str, details: Optional[dict] = None):
        super().__init__(code, message, 401, details)


class AuthorizationError(GatewayError):
    """Authorization errors"""
    def __init__(self, code: ErrorCode, message: str, details: Optional[dict] = None):
        super().__init__(code, message, 403, details)


class ValidationError(GatewayError):
    """Request validation errors"""
    def __init__(self, code: ErrorCode, message: str, details: Optional[dict] = None):
        super().__init__(code, message, 400, details)


class RateLimitError(GatewayError):
    """Rate limiting errors"""
    def __init__(
        self,
        code: ErrorCode,
        message: str,
        retry_after: int = 60,
        details: Optional[dict] = None,
    ):
        super().__init__(code, message, 429, details)
        self.retry_after = retry_after


class CircuitBreakerError(GatewayError):
    """Circuit breaker errors"""
    def __init__(self, code: ErrorCode, message: str, details: Optional[dict] = None):
        super().__init__(code, message, 503, details)


class ServerError(GatewayError):
    """Server errors"""
    def __init__(self, code: ErrorCode, message: str, details: Optional[dict] = None):
        super().__init__(code, message, 500, details)


ERROR_MESSAGES = {
    ErrorCode.E9001: "Route not found",
    ErrorCode.E9002: "Invalid API version",
    ErrorCode.E9003: "Route deprecated",
    ErrorCode.E9101: "Invalid API key",
    ErrorCode.E9102: "Token expired",
    ErrorCode.E9103: "Missing credentials",
    ErrorCode.E9104: "Invalid JWT signature",
    ErrorCode.E9105: "Invalid mTLS certificate",
    ErrorCode.E9106: "Certificate revoked",
    ErrorCode.E9201: "Authorization failed",
    ErrorCode.E9202: "Consumer suspended",
    ErrorCode.E9203: "Consumer not found",
    ErrorCode.E9204: "Invalid consumer state",
    ErrorCode.E9205: "Cross-tenant access attempt",
    ErrorCode.E9206: "Role insufficient for operation",
    ErrorCode.E9207: "OAuth scope insufficient",
    ErrorCode.E9301: "Invalid idempotency key format",
    ErrorCode.E9302: "Required parameter missing",
    ErrorCode.E9303: "Parameter type mismatch",
    ErrorCode.E9304: "Request body exceeds size limit",
    ErrorCode.E9305: "Invalid JSON format",
    ErrorCode.E9306: "Invalid character encoding",
    ErrorCode.E9307: "Null byte detected in input",
    ErrorCode.E9308: "Query string too long",
    ErrorCode.E9309: "Header validation failed",
    ErrorCode.E9401: "Rate limit exceeded",
    ErrorCode.E9402: "Daily quota exceeded",
    ErrorCode.E9403: "Rate limit tier not found",
    ErrorCode.E9404: "Burst capacity exceeded",
    ErrorCode.E9501: "Operation not found",
    ErrorCode.E9502: "Operation creation failed",
    ErrorCode.E9503: "Operation status unknown",
    ErrorCode.E9601: "Async operation error",
    ErrorCode.E9602: "Operation not found",
    ErrorCode.E9603: "Operation expired",
    ErrorCode.E9604: "Operation already completed",
    ErrorCode.E9701: "Invalid webhook URL",
    ErrorCode.E9702: "Webhook delivery failed",
    ErrorCode.E9703: "Webhook signature invalid",
    ErrorCode.E9704: "SSRF violation detected",
    ErrorCode.E9705: "Webhook TLS certificate invalid",
    ErrorCode.E9706: "Webhook timeout",
    ErrorCode.E9801: "Circuit breaker open",
    ErrorCode.E9802: "Backend unhealthy",
    ErrorCode.E9803: "All replicas unavailable",
    ErrorCode.E9804: "Connection pool exhausted",
    ErrorCode.E9901: "Internal server error",
    ErrorCode.E9902: "Service unavailable",
    ErrorCode.E9903: "Gateway timeout",
    ErrorCode.E9904: "Bad gateway",
    ErrorCode.E9905: "Configuration error",
    ErrorCode.E9906: "Redis unavailable",
    ErrorCode.E9907: "Database unavailable",
}
