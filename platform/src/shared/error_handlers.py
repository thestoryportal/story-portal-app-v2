"""
Error Handling Middleware and Utilities

Provides FastAPI exception handlers and middleware for consistent
error responses across all services.
"""

import logging
import traceback
from typing import Callable, Optional, Union
from fastapi import Request, Response, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from .errors import (
    PlatformError,
    ErrorCode,
    ErrorResponse,
    ErrorDetail,
    ValidationError,
    SystemError,
)
from .logging_config import get_correlation_id, get_request_id


logger = logging.getLogger(__name__)


async def platform_error_handler(
    request: Request,
    exc: PlatformError,
) -> JSONResponse:
    """
    Handle PlatformError exceptions.

    Args:
        request: FastAPI request
        exc: PlatformError instance

    Returns:
        JSON response with standardized error format
    """
    correlation_id = get_correlation_id()
    request_id = get_request_id()

    # Log error with correlation ID
    logger.error(
        f"Platform error occurred",
        extra={
            'event': 'platform_error',
            'error_code': exc.code.value,
            'error_message': exc.message,
            'status_code': exc.status_code,
            'path': request.url.path,
            'method': request.method,
            'correlation_id': correlation_id,
            'request_id': request_id,
            'error_context': exc.context,
        },
        exc_info=exc.status_code >= 500,  # Full traceback for 5xx errors
    )

    # Create error response
    error_response = exc.to_response(
        correlation_id=correlation_id,
        request_id=request_id,
        path=request.url.path,
    )

    return JSONResponse(
        status_code=exc.status_code,
        content=error_response.dict(),
    )


async def validation_error_handler(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    """
    Handle Pydantic validation errors.

    Args:
        request: FastAPI request
        exc: RequestValidationError from Pydantic

    Returns:
        JSON response with validation error details
    """
    correlation_id = get_correlation_id()
    request_id = get_request_id()

    # Convert Pydantic errors to ErrorDetail format
    details = []
    for error in exc.errors():
        field = ".".join(str(loc) for loc in error["loc"])
        details.append(
            ErrorDetail(
                field=field,
                message=error["msg"],
                code=ErrorCode.VAL_INVALID_INPUT.value,
                context={"type": error["type"]},
            )
        )

    # Log validation error
    logger.warning(
        f"Validation error occurred",
        extra={
            'event': 'validation_error',
            'error_count': len(details),
            'path': request.url.path,
            'method': request.method,
            'correlation_id': correlation_id,
            'request_id': request_id,
        }
    )

    # Create validation error response
    validation_error = ValidationError(
        message="Request validation failed",
        details=details,
    )

    error_response = validation_error.to_response(
        correlation_id=correlation_id,
        request_id=request_id,
        path=request.url.path,
    )

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=error_response.dict(),
    )


async def http_exception_handler(
    request: Request,
    exc: StarletteHTTPException,
) -> JSONResponse:
    """
    Handle Starlette HTTP exceptions.

    Args:
        request: FastAPI request
        exc: StarletteHTTPException

    Returns:
        JSON response with error details
    """
    correlation_id = get_correlation_id()
    request_id = get_request_id()

    # Map HTTP status codes to error codes
    error_code_map = {
        400: ErrorCode.VAL_INVALID_INPUT,
        401: ErrorCode.AUTH_INVALID_TOKEN,
        403: ErrorCode.AUTH_INSUFFICIENT_PERMISSIONS,
        404: ErrorCode.RES_NOT_FOUND,
        409: ErrorCode.RES_CONFLICT,
        429: ErrorCode.RATE_LIMIT_EXCEEDED,
        500: ErrorCode.SYS_INTERNAL_ERROR,
        502: ErrorCode.EXT_SERVICE_ERROR,
        503: ErrorCode.SYS_SERVICE_UNAVAILABLE,
        504: ErrorCode.SYS_TIMEOUT,
    }

    error_code = error_code_map.get(exc.status_code, ErrorCode.SYS_INTERNAL_ERROR)

    # Log HTTP exception
    log_level = logging.ERROR if exc.status_code >= 500 else logging.WARNING
    logger.log(
        log_level,
        f"HTTP exception occurred",
        extra={
            'event': 'http_exception',
            'error_code': error_code.value,
            'status_code': exc.status_code,
            'error_message': exc.detail,
            'path': request.url.path,
            'method': request.method,
            'correlation_id': correlation_id,
            'request_id': request_id,
        }
    )

    # Create error response
    error_data = {
        "code": error_code.value,
        "message": exc.detail,
        "timestamp": __import__('datetime').datetime.utcnow().isoformat() + "Z",
        "correlation_id": correlation_id,
        "request_id": request_id,
        "path": request.url.path,
    }

    return JSONResponse(
        status_code=exc.status_code,
        content={"error": error_data},
    )


async def unhandled_exception_handler(
    request: Request,
    exc: Exception,
) -> JSONResponse:
    """
    Handle unhandled exceptions (fallback handler).

    Args:
        request: FastAPI request
        exc: Exception instance

    Returns:
        JSON response with generic error message
    """
    correlation_id = get_correlation_id()
    request_id = get_request_id()

    # Log unhandled exception with full traceback
    logger.error(
        f"Unhandled exception occurred",
        extra={
            'event': 'unhandled_exception',
            'error_type': type(exc).__name__,
            'error_message': str(exc),
            'path': request.url.path,
            'method': request.method,
            'correlation_id': correlation_id,
            'request_id': request_id,
            'traceback': traceback.format_exc(),
        },
        exc_info=True,
    )

    # Create generic error response (don't expose internal details)
    system_error = SystemError(
        message="An unexpected error occurred",
        code=ErrorCode.SYS_INTERNAL_ERROR,
        context={
            'error_type': type(exc).__name__,
            # Only include in development
            'error_detail': str(exc) if __import__('os').getenv('ENV') == 'development' else None,
        }
    )

    error_response = system_error.to_response(
        correlation_id=correlation_id,
        request_id=request_id,
        path=request.url.path,
    )

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=error_response.dict(),
    )


def register_error_handlers(app) -> None:
    """
    Register all error handlers with FastAPI app.

    Args:
        app: FastAPI application instance

    Example:
        from fastapi import FastAPI
        from shared.error_handlers import register_error_handlers

        app = FastAPI()
        register_error_handlers(app)
    """
    # Platform errors
    app.add_exception_handler(PlatformError, platform_error_handler)

    # Validation errors
    app.add_exception_handler(RequestValidationError, validation_error_handler)

    # HTTP exceptions
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)

    # Catch-all for unhandled exceptions
    app.add_exception_handler(Exception, unhandled_exception_handler)

    logger.info(
        "Error handlers registered",
        extra={
            'event': 'error_handlers_registered',
            'handlers': [
                'PlatformError',
                'RequestValidationError',
                'StarletteHTTPException',
                'Exception',
            ]
        }
    )


# Utility functions for error handling in route handlers

def raise_not_found(resource_type: str, resource_id: str) -> None:
    """
    Raise NotFoundError.

    Args:
        resource_type: Type of resource (e.g., "Agent", "Goal")
        resource_id: Resource identifier

    Raises:
        NotFoundError
    """
    from .errors import NotFoundError
    raise NotFoundError(resource_type, resource_id)


def raise_already_exists(resource_type: str, resource_id: str) -> None:
    """
    Raise AlreadyExistsError.

    Args:
        resource_type: Type of resource
        resource_id: Resource identifier

    Raises:
        AlreadyExistsError
    """
    from .errors import AlreadyExistsError
    raise AlreadyExistsError(resource_type, resource_id)


def raise_validation_error(field: str, message: str) -> None:
    """
    Raise InvalidInputError for single field.

    Args:
        field: Field name
        message: Error message

    Raises:
        InvalidInputError
    """
    from .errors import InvalidInputError
    raise InvalidInputError(field, message)


def raise_authorization_error(required_permission: str) -> None:
    """
    Raise AuthorizationError.

    Args:
        required_permission: Required permission

    Raises:
        AuthorizationError
    """
    from .errors import AuthorizationError
    raise AuthorizationError(required_permission=required_permission)


def raise_rate_limit_error(limit: int, retry_after: int) -> None:
    """
    Raise RateLimitError.

    Args:
        limit: Rate limit value
        retry_after: Seconds until retry allowed

    Raises:
        RateLimitError
    """
    from .errors import RateLimitError
    raise RateLimitError(limit=limit, retry_after=retry_after)


# Context manager for error handling

class ErrorContext:
    """
    Context manager for converting exceptions to PlatformErrors.

    Example:
        with ErrorContext("database", operation="fetch_agent"):
            result = await db.fetch_one(query)
            if not result:
                raise NotFoundError("Agent", agent_id)
    """

    def __init__(
        self,
        context_name: str,
        operation: Optional[str] = None,
        reraise: bool = True,
    ):
        """
        Initialize error context.

        Args:
            context_name: Name of the context (e.g., "database", "external_api")
            operation: Specific operation being performed
            reraise: Whether to re-raise exceptions (default: True)
        """
        self.context_name = context_name
        self.operation = operation
        self.reraise = reraise

    def __enter__(self):
        """Enter context."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        Exit context and handle exceptions.

        Returns:
            True to suppress exception, False to propagate
        """
        if exc_type is None:
            return False

        # Don't wrap PlatformErrors
        if isinstance(exc_val, PlatformError):
            return False

        # Log the error
        logger.error(
            f"Error in {self.context_name}",
            extra={
                'event': 'error_context',
                'context_name': self.context_name,
                'operation': self.operation,
                'error_type': exc_type.__name__,
                'error_message': str(exc_val),
            },
            exc_info=True,
        )

        if self.reraise:
            # Convert to appropriate PlatformError based on context
            if self.context_name == "database":
                from .errors import DatabaseError
                raise DatabaseError(
                    message=f"Database error during {self.operation or 'operation'}",
                    operation=self.operation,
                ) from exc_val
            elif self.context_name == "external_service":
                from .errors import ExternalServiceError
                raise ExternalServiceError(
                    service_name=self.operation or "unknown",
                    message=str(exc_val),
                ) from exc_val
            else:
                # Generic system error
                from .errors import SystemError
                raise SystemError(
                    message=f"Error in {self.context_name}: {str(exc_val)}",
                    context={
                        'context_name': self.context_name,
                        'operation': self.operation,
                    }
                ) from exc_val

        return not self.reraise


def handle_database_error(operation: str = "database operation"):
    """
    Decorator for database operations that converts exceptions to DatabaseError.

    Args:
        operation: Description of the operation

    Example:
        @handle_database_error("fetch agent")
        async def get_agent(agent_id: str):
            return await db.fetch_one(...)
    """
    def decorator(func: Callable):
        async def wrapper(*args, **kwargs):
            with ErrorContext("database", operation=operation):
                return await func(*args, **kwargs)
        return wrapper
    return decorator


def handle_external_service_error(service_name: str):
    """
    Decorator for external service calls that converts exceptions to ExternalServiceError.

    Args:
        service_name: Name of the external service

    Example:
        @handle_external_service_error("OpenAI API")
        async def call_openai(prompt: str):
            return await httpx.post(...)
    """
    def decorator(func: Callable):
        async def wrapper(*args, **kwargs):
            with ErrorContext("external_service", operation=service_name):
                return await func(*args, **kwargs)
        return wrapper
    return decorator
