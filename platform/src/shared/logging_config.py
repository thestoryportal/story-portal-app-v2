"""
Structured Logging Configuration for Agentic Platform

Provides standardized JSON logging with correlation IDs, request tracking,
and consistent formatting across all services.
"""

import json
import logging
import sys
import uuid
from contextvars import ContextVar
from datetime import datetime
from typing import Any, Dict, Optional
from pythonjsonlogger.json import JsonFormatter as BaseJsonFormatter


# Context variable for storing correlation ID across async contexts
correlation_id_var: ContextVar[Optional[str]] = ContextVar(
    'correlation_id', default=None
)
request_id_var: ContextVar[Optional[str]] = ContextVar(
    'request_id', default=None
)
user_id_var: ContextVar[Optional[str]] = ContextVar(
    'user_id', default=None
)
session_id_var: ContextVar[Optional[str]] = ContextVar(
    'session_id', default=None
)


class CorrelationIDFilter(logging.Filter):
    """
    Logging filter that adds correlation ID and other context to log records.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        """Add context variables to log record."""
        record.correlation_id = correlation_id_var.get()
        record.request_id = request_id_var.get()
        record.user_id = user_id_var.get()
        record.session_id = session_id_var.get()
        return True


class CustomJsonFormatter(BaseJsonFormatter):
    """
    Custom JSON formatter that ensures consistent field ordering
    and additional metadata.
    """

    def add_fields(
        self,
        log_record: Dict[str, Any],
        record: logging.LogRecord,
        message_dict: Dict[str, Any],
    ) -> None:
        """Add standard fields to log record in consistent order."""
        super().add_fields(log_record, record, message_dict)

        # Timestamp
        if not log_record.get('timestamp'):
            log_record['timestamp'] = datetime.utcnow().isoformat() + 'Z'

        # Service information
        if not log_record.get('service'):
            log_record['service'] = getattr(record, 'service_name', 'unknown')

        # Log level
        if log_record.get('level'):
            log_record['level'] = log_record['level'].upper()
        else:
            log_record['level'] = record.levelname

        # Correlation and request IDs
        correlation_id = getattr(record, 'correlation_id', None)
        if correlation_id:
            log_record['correlation_id'] = correlation_id

        request_id = getattr(record, 'request_id', None)
        if request_id:
            log_record['request_id'] = request_id

        user_id = getattr(record, 'user_id', None)
        if user_id:
            log_record['user_id'] = user_id

        session_id = getattr(record, 'session_id', None)
        if session_id:
            log_record['session_id'] = session_id

        # Module and function information
        if not log_record.get('logger'):
            log_record['logger'] = record.name

        if record.funcName:
            log_record['function'] = record.funcName

        # Exception information
        if record.exc_info:
            log_record['exc_info'] = self.formatException(record.exc_info)

        # Reorder fields for better readability
        ordered_record = {
            'timestamp': log_record.get('timestamp'),
            'level': log_record.get('level'),
            'service': log_record.get('service'),
            'logger': log_record.get('logger'),
            'message': log_record.get('message'),
            'correlation_id': log_record.get('correlation_id'),
            'request_id': log_record.get('request_id'),
            'user_id': log_record.get('user_id'),
            'session_id': log_record.get('session_id'),
        }

        # Add remaining fields
        for key, value in log_record.items():
            if key not in ordered_record:
                ordered_record[key] = value

        # Clear and update log_record
        log_record.clear()
        log_record.update({k: v for k, v in ordered_record.items() if v is not None})


def setup_logging(
    service_name: str,
    log_level: str = "INFO",
    json_logs: bool = True,
    include_debug_fields: bool = False,
) -> logging.Logger:
    """
    Setup structured logging for a service.

    Args:
        service_name: Name of the service (e.g., "L01-data-layer")
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        json_logs: Whether to use JSON formatting (True for production)
        include_debug_fields: Include additional debug fields (filename, lineno, etc.)

    Returns:
        Configured logger instance
    """
    # Remove existing handlers
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Set log level
    level = getattr(logging, log_level.upper(), logging.INFO)
    root_logger.setLevel(level)

    # Create console handler
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(level)

    # Add correlation ID filter
    correlation_filter = CorrelationIDFilter()
    handler.addFilter(correlation_filter)

    # Configure formatter
    if json_logs:
        # JSON formatter for structured logs
        format_string = '%(timestamp)s %(level)s %(service)s %(logger)s %(message)s'
        if include_debug_fields:
            format_string += ' %(filename)s %(lineno)d %(funcName)s'

        formatter = CustomJsonFormatter(format_string)
    else:
        # Human-readable format for development
        format_string = (
            '%(asctime)s - %(name)s - %(levelname)s - '
            '[%(correlation_id)s] - %(message)s'
        )
        formatter = logging.Formatter(format_string)

    handler.setFormatter(formatter)
    root_logger.addHandler(handler)

    # Create service-specific logger
    logger = logging.getLogger(service_name)

    # Add service name to all records
    old_factory = logging.getLogRecordFactory()

    def record_factory(*args, **kwargs):
        record = old_factory(*args, **kwargs)
        record.service_name = service_name
        return record

    logging.setLogRecordFactory(record_factory)

    logger.info(
        f"Structured logging initialized for {service_name}",
        extra={
            'log_level': log_level,
            'json_logs': json_logs,
            'service': service_name,
        }
    )

    return logger


def get_correlation_id() -> Optional[str]:
    """Get current correlation ID from context."""
    return correlation_id_var.get()


def set_correlation_id(correlation_id: str) -> None:
    """Set correlation ID in context."""
    correlation_id_var.set(correlation_id)


def generate_correlation_id() -> str:
    """Generate a new correlation ID."""
    return str(uuid.uuid4())


def get_request_id() -> Optional[str]:
    """Get current request ID from context."""
    return request_id_var.get()


def set_request_id(request_id: str) -> None:
    """Set request ID in context."""
    request_id_var.set(request_id)


def generate_request_id() -> str:
    """Generate a new request ID."""
    return str(uuid.uuid4())


def get_user_id() -> Optional[str]:
    """Get current user ID from context."""
    return user_id_var.get()


def set_user_id(user_id: str) -> None:
    """Set user ID in context."""
    user_id_var.set(user_id)


def get_session_id() -> Optional[str]:
    """Get current session ID from context."""
    return session_id_var.get()


def set_session_id(session_id: str) -> None:
    """Set session ID in context."""
    session_id_var.set(session_id)


def clear_context() -> None:
    """Clear all context variables."""
    correlation_id_var.set(None)
    request_id_var.set(None)
    user_id_var.set(None)
    session_id_var.set(None)


class LogContext:
    """
    Context manager for temporarily setting logging context.

    Example:
        with LogContext(correlation_id="abc-123", user_id="user-456"):
            logger.info("This log will include correlation_id and user_id")
    """

    def __init__(
        self,
        correlation_id: Optional[str] = None,
        request_id: Optional[str] = None,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
    ):
        self.correlation_id = correlation_id
        self.request_id = request_id
        self.user_id = user_id
        self.session_id = session_id
        self.previous_correlation_id = None
        self.previous_request_id = None
        self.previous_user_id = None
        self.previous_session_id = None

    def __enter__(self):
        """Save previous context and set new values."""
        self.previous_correlation_id = get_correlation_id()
        self.previous_request_id = get_request_id()
        self.previous_user_id = get_user_id()
        self.previous_session_id = get_session_id()

        if self.correlation_id:
            set_correlation_id(self.correlation_id)
        if self.request_id:
            set_request_id(self.request_id)
        if self.user_id:
            set_user_id(self.user_id)
        if self.session_id:
            set_session_id(self.session_id)

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Restore previous context."""
        if self.previous_correlation_id:
            set_correlation_id(self.previous_correlation_id)
        else:
            correlation_id_var.set(None)

        if self.previous_request_id:
            set_request_id(self.previous_request_id)
        else:
            request_id_var.set(None)

        if self.previous_user_id:
            set_user_id(self.previous_user_id)
        else:
            user_id_var.set(None)

        if self.previous_session_id:
            set_session_id(self.previous_session_id)
        else:
            session_id_var.set(None)


# Convenience function for logging with extra context
def log_with_context(
    logger: logging.Logger,
    level: str,
    message: str,
    **extra_fields: Any,
) -> None:
    """
    Log a message with additional context fields.

    Args:
        logger: Logger instance
        level: Log level (debug, info, warning, error, critical)
        message: Log message
        **extra_fields: Additional fields to include in log
    """
    log_func = getattr(logger, level.lower())
    log_func(message, extra=extra_fields)
