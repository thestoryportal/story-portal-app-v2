"""
Standardized Error Handling for Agentic Platform

Provides consistent error classes, error codes, and error responses
across all services with structured logging integration.
"""

import logging
from enum import Enum
from typing import Any, Dict, Optional, List
from datetime import datetime

from pydantic import BaseModel, Field


logger = logging.getLogger(__name__)


class ErrorCode(str, Enum):
    """
    Standardized error codes across the platform.

    Error code format: CATEGORY_SPECIFIC_ERROR
    Categories:
    - AUTH: Authentication/Authorization errors
    - VAL: Validation errors
    - RES: Resource errors (not found, conflict, etc.)
    - SYS: System errors (internal, service unavailable, etc.)
    - EXT: External service errors
    - RATE: Rate limiting errors
    """

    # Authentication & Authorization (401, 403)
    AUTH_INVALID_TOKEN = "AUTH_INVALID_TOKEN"
    AUTH_EXPIRED_TOKEN = "AUTH_EXPIRED_TOKEN"
    AUTH_MISSING_TOKEN = "AUTH_MISSING_TOKEN"
    AUTH_INSUFFICIENT_PERMISSIONS = "AUTH_INSUFFICIENT_PERMISSIONS"
    AUTH_INVALID_CREDENTIALS = "AUTH_INVALID_CREDENTIALS"

    # Validation Errors (400, 422)
    VAL_INVALID_INPUT = "VAL_INVALID_INPUT"
    VAL_MISSING_FIELD = "VAL_MISSING_FIELD"
    VAL_INVALID_FORMAT = "VAL_INVALID_FORMAT"
    VAL_OUT_OF_RANGE = "VAL_OUT_OF_RANGE"
    VAL_INVALID_TYPE = "VAL_INVALID_TYPE"

    # Resource Errors (404, 409)
    RES_NOT_FOUND = "RES_NOT_FOUND"
    RES_ALREADY_EXISTS = "RES_ALREADY_EXISTS"
    RES_CONFLICT = "RES_CONFLICT"
    RES_GONE = "RES_GONE"

    # System Errors (500, 503)
    SYS_INTERNAL_ERROR = "SYS_INTERNAL_ERROR"
    SYS_SERVICE_UNAVAILABLE = "SYS_SERVICE_UNAVAILABLE"
    SYS_DATABASE_ERROR = "SYS_DATABASE_ERROR"
    SYS_TIMEOUT = "SYS_TIMEOUT"
    SYS_CONFIGURATION_ERROR = "SYS_CONFIGURATION_ERROR"

    # External Service Errors (502, 503, 504)
    EXT_SERVICE_ERROR = "EXT_SERVICE_ERROR"
    EXT_SERVICE_TIMEOUT = "EXT_SERVICE_TIMEOUT"
    EXT_SERVICE_UNAVAILABLE = "EXT_SERVICE_UNAVAILABLE"
    EXT_INVALID_RESPONSE = "EXT_INVALID_RESPONSE"

    # Rate Limiting (429)
    RATE_LIMIT_EXCEEDED = "RATE_LIMIT_EXCEEDED"
    RATE_QUOTA_EXCEEDED = "RATE_QUOTA_EXCEEDED"

    # Business Logic Errors (400, 422)
    BIZ_OPERATION_NOT_ALLOWED = "BIZ_OPERATION_NOT_ALLOWED"
    BIZ_INVALID_STATE = "BIZ_INVALID_STATE"
    BIZ_PRECONDITION_FAILED = "BIZ_PRECONDITION_FAILED"


class ErrorDetail(BaseModel):
    """
    Detailed information about a specific error.
    """

    field: Optional[str] = Field(None, description="Field that caused the error (for validation errors)")
    message: str = Field(..., description="Human-readable error message")
    code: Optional[str] = Field(None, description="Specific error code")
    context: Optional[Dict[str, Any]] = Field(None, description="Additional context")


class ErrorResponse(BaseModel):
    """
    Standardized error response format.

    Example:
    {
        "error": {
            "code": "VAL_INVALID_INPUT",
            "message": "Validation failed for request",
            "details": [
                {
                    "field": "email",
                    "message": "Invalid email format",
                    "code": "VAL_INVALID_FORMAT"
                }
            ],
            "timestamp": "2026-01-18T10:30:45.123456Z",
            "correlation_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
            "request_id": "req-12345678-1234-1234-1234-123456789012",
            "path": "/api/v1/agents"
        }
    }
    """

    error: Dict[str, Any] = Field(
        ...,
        description="Error information",
        example={
            "code": "VAL_INVALID_INPUT",
            "message": "Validation failed",
            "timestamp": "2026-01-18T10:30:45.123456Z",
        }
    )

    @classmethod
    def from_exception(
        cls,
        exc: Exception,
        code: ErrorCode,
        correlation_id: Optional[str] = None,
        request_id: Optional[str] = None,
        path: Optional[str] = None,
        details: Optional[List[ErrorDetail]] = None,
    ) -> "ErrorResponse":
        """
        Create error response from exception.

        Args:
            exc: Exception instance
            code: Error code
            correlation_id: Request correlation ID
            request_id: Request ID
            path: Request path
            details: Additional error details

        Returns:
            ErrorResponse instance
        """
        error_data = {
            "code": code.value,
            "message": str(exc),
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }

        if correlation_id:
            error_data["correlation_id"] = correlation_id

        if request_id:
            error_data["request_id"] = request_id

        if path:
            error_data["path"] = path

        if details:
            error_data["details"] = [d.dict(exclude_none=True) for d in details]

        return cls(error=error_data)


class PlatformError(Exception):
    """
    Base exception class for all platform errors.

    All custom exceptions should inherit from this class.
    """

    def __init__(
        self,
        message: str,
        code: ErrorCode,
        status_code: int = 500,
        details: Optional[List[ErrorDetail]] = None,
        context: Optional[Dict[str, Any]] = None,
    ):
        """
        Initialize platform error.

        Args:
            message: Human-readable error message
            code: Error code
            status_code: HTTP status code
            details: Additional error details
            context: Extra context for logging
        """
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details or []
        self.context = context or {}

    def to_response(
        self,
        correlation_id: Optional[str] = None,
        request_id: Optional[str] = None,
        path: Optional[str] = None,
    ) -> ErrorResponse:
        """
        Convert exception to error response.

        Args:
            correlation_id: Request correlation ID
            request_id: Request ID
            path: Request path

        Returns:
            ErrorResponse instance
        """
        return ErrorResponse.from_exception(
            exc=self,
            code=self.code,
            correlation_id=correlation_id,
            request_id=request_id,
            path=path,
            details=self.details,
        )


# Authentication & Authorization Errors

class AuthenticationError(PlatformError):
    """Authentication failed."""

    def __init__(
        self,
        message: str = "Authentication failed",
        code: ErrorCode = ErrorCode.AUTH_INVALID_TOKEN,
        details: Optional[List[ErrorDetail]] = None,
    ):
        super().__init__(
            message=message,
            code=code,
            status_code=401,
            details=details,
        )


class InvalidTokenError(AuthenticationError):
    """Invalid authentication token."""

    def __init__(self, message: str = "Invalid authentication token"):
        super().__init__(
            message=message,
            code=ErrorCode.AUTH_INVALID_TOKEN,
        )


class ExpiredTokenError(AuthenticationError):
    """Expired authentication token."""

    def __init__(self, message: str = "Authentication token expired"):
        super().__init__(
            message=message,
            code=ErrorCode.AUTH_EXPIRED_TOKEN,
        )


class MissingTokenError(AuthenticationError):
    """Missing authentication token."""

    def __init__(self, message: str = "Authentication token required"):
        super().__init__(
            message=message,
            code=ErrorCode.AUTH_MISSING_TOKEN,
        )


class AuthorizationError(PlatformError):
    """Authorization failed - insufficient permissions."""

    def __init__(
        self,
        message: str = "Insufficient permissions",
        required_permission: Optional[str] = None,
    ):
        details = []
        if required_permission:
            details.append(
                ErrorDetail(
                    message=f"Required permission: {required_permission}",
                    context={"required_permission": required_permission}
                )
            )

        super().__init__(
            message=message,
            code=ErrorCode.AUTH_INSUFFICIENT_PERMISSIONS,
            status_code=403,
            details=details,
        )


# Validation Errors

class ValidationError(PlatformError):
    """Input validation failed."""

    def __init__(
        self,
        message: str = "Validation failed",
        details: Optional[List[ErrorDetail]] = None,
    ):
        super().__init__(
            message=message,
            code=ErrorCode.VAL_INVALID_INPUT,
            status_code=422,
            details=details,
        )


class InvalidInputError(ValidationError):
    """Invalid input provided."""

    def __init__(
        self,
        field: str,
        message: str,
        expected: Optional[str] = None,
    ):
        details = [
            ErrorDetail(
                field=field,
                message=message,
                code=ErrorCode.VAL_INVALID_INPUT.value,
                context={"expected": expected} if expected else None,
            )
        ]
        super().__init__(
            message=f"Invalid input for field '{field}': {message}",
            details=details,
        )


class MissingFieldError(ValidationError):
    """Required field missing."""

    def __init__(self, field: str):
        details = [
            ErrorDetail(
                field=field,
                message=f"Required field '{field}' is missing",
                code=ErrorCode.VAL_MISSING_FIELD.value,
            )
        ]
        super().__init__(
            message=f"Missing required field: {field}",
            details=details,
        )


# Resource Errors

class ResourceError(PlatformError):
    """Base class for resource-related errors."""

    pass


class NotFoundError(ResourceError):
    """Resource not found."""

    def __init__(
        self,
        resource_type: str,
        resource_id: str,
    ):
        super().__init__(
            message=f"{resource_type} not found: {resource_id}",
            code=ErrorCode.RES_NOT_FOUND,
            status_code=404,
            context={
                "resource_type": resource_type,
                "resource_id": resource_id,
            },
        )


class AlreadyExistsError(ResourceError):
    """Resource already exists."""

    def __init__(
        self,
        resource_type: str,
        resource_id: str,
    ):
        super().__init__(
            message=f"{resource_type} already exists: {resource_id}",
            code=ErrorCode.RES_ALREADY_EXISTS,
            status_code=409,
            context={
                "resource_type": resource_type,
                "resource_id": resource_id,
            },
        )


class ConflictError(ResourceError):
    """Resource conflict."""

    def __init__(
        self,
        message: str,
        details: Optional[List[ErrorDetail]] = None,
    ):
        super().__init__(
            message=message,
            code=ErrorCode.RES_CONFLICT,
            status_code=409,
            details=details,
        )


# System Errors

class SystemError(PlatformError):
    """Internal system error."""

    def __init__(
        self,
        message: str = "Internal server error",
        code: ErrorCode = ErrorCode.SYS_INTERNAL_ERROR,
        context: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            message=message,
            code=code,
            status_code=500,
            context=context,
        )


class DatabaseError(SystemError):
    """Database operation failed."""

    def __init__(
        self,
        message: str = "Database error occurred",
        operation: Optional[str] = None,
    ):
        context = {"operation": operation} if operation else None
        super().__init__(
            message=message,
            code=ErrorCode.SYS_DATABASE_ERROR,
            context=context,
        )


class TimeoutError(SystemError):
    """Operation timed out."""

    def __init__(
        self,
        message: str = "Operation timed out",
        timeout_seconds: Optional[float] = None,
    ):
        context = {"timeout_seconds": timeout_seconds} if timeout_seconds else None
        super().__init__(
            message=message,
            code=ErrorCode.SYS_TIMEOUT,
            status_code=504,
            context=context,
        )


class ServiceUnavailableError(SystemError):
    """Service temporarily unavailable."""

    def __init__(
        self,
        message: str = "Service temporarily unavailable",
        retry_after: Optional[int] = None,
    ):
        context = {"retry_after_seconds": retry_after} if retry_after else None
        super().__init__(
            message=message,
            code=ErrorCode.SYS_SERVICE_UNAVAILABLE,
            status_code=503,
            context=context,
        )


# External Service Errors

class ExternalServiceError(PlatformError):
    """External service error."""

    def __init__(
        self,
        service_name: str,
        message: str = "External service error",
        code: ErrorCode = ErrorCode.EXT_SERVICE_ERROR,
        status_code: int = 502,
    ):
        super().__init__(
            message=f"{service_name}: {message}",
            code=code,
            status_code=status_code,
            context={"service_name": service_name},
        )


class ExternalServiceTimeoutError(ExternalServiceError):
    """External service timeout."""

    def __init__(
        self,
        service_name: str,
        timeout_seconds: Optional[float] = None,
    ):
        message = f"Request to {service_name} timed out"
        if timeout_seconds:
            message += f" after {timeout_seconds}s"

        super().__init__(
            service_name=service_name,
            message=message,
            code=ErrorCode.EXT_SERVICE_TIMEOUT,
            status_code=504,
        )


# Rate Limiting Errors

class RateLimitError(PlatformError):
    """Rate limit exceeded."""

    def __init__(
        self,
        message: str = "Rate limit exceeded",
        limit: Optional[int] = None,
        retry_after: Optional[int] = None,
    ):
        context = {}
        if limit:
            context["limit"] = limit
        if retry_after:
            context["retry_after_seconds"] = retry_after

        super().__init__(
            message=message,
            code=ErrorCode.RATE_LIMIT_EXCEEDED,
            status_code=429,
            context=context,
        )


# Business Logic Errors

class BusinessLogicError(PlatformError):
    """Business logic constraint violated."""

    def __init__(
        self,
        message: str,
        code: ErrorCode = ErrorCode.BIZ_OPERATION_NOT_ALLOWED,
        details: Optional[List[ErrorDetail]] = None,
    ):
        super().__init__(
            message=message,
            code=code,
            status_code=400,
            details=details,
        )


class InvalidStateError(BusinessLogicError):
    """Resource in invalid state for operation."""

    def __init__(
        self,
        message: str,
        current_state: str,
        required_state: Optional[str] = None,
    ):
        context = {"current_state": current_state}
        if required_state:
            context["required_state"] = required_state

        super().__init__(
            message=message,
            code=ErrorCode.BIZ_INVALID_STATE,
        )
