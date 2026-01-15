"""
Tests for Error Handling
"""

import pytest
from ..errors import (
    ErrorCode,
    GatewayError,
    AuthenticationError,
    AuthorizationError,
    ValidationError,
    RateLimitError,
    ERROR_MESSAGES,
)


def test_gateway_error_creation():
    """Test basic gateway error creation"""
    error = GatewayError(
        code=ErrorCode.E9001,
        message="Test error",
        http_status=404,
        details={"key": "value"},
    )

    assert error.code == ErrorCode.E9001
    assert error.message == "Test error"
    assert error.http_status == 404
    assert error.details == {"key": "value"}


def test_error_to_dict():
    """Test error conversion to dictionary"""
    error = GatewayError(
        code=ErrorCode.E9101,
        message="Invalid API key",
        http_status=401,
    )

    error_dict = error.to_dict()

    assert error_dict["error"]["code"] == "E9101"
    assert error_dict["error"]["message"] == "Invalid API key"
    assert "details" in error_dict["error"]


def test_authentication_error():
    """Test authentication error"""
    error = AuthenticationError(
        code=ErrorCode.E9101,
        message="Invalid API key",
    )

    assert error.http_status == 401
    assert error.code == ErrorCode.E9101


def test_authorization_error():
    """Test authorization error"""
    error = AuthorizationError(
        code=ErrorCode.E9207,
        message="Insufficient OAuth scopes",
    )

    assert error.http_status == 403
    assert error.code == ErrorCode.E9207


def test_validation_error():
    """Test validation error"""
    error = ValidationError(
        code=ErrorCode.E9301,
        message="Invalid idempotency key",
    )

    assert error.http_status == 400
    assert error.code == ErrorCode.E9301


def test_rate_limit_error():
    """Test rate limit error"""
    error = RateLimitError(
        code=ErrorCode.E9401,
        message="Rate limit exceeded",
        retry_after=60,
    )

    assert error.http_status == 429
    assert error.retry_after == 60


def test_error_messages_coverage():
    """Test that all error codes have messages"""
    # Check that main error codes have messages
    assert ErrorCode.E9001 in ERROR_MESSAGES
    assert ErrorCode.E9101 in ERROR_MESSAGES
    assert ErrorCode.E9201 in ERROR_MESSAGES
    assert ErrorCode.E9301 in ERROR_MESSAGES
    assert ErrorCode.E9401 in ERROR_MESSAGES
    assert ErrorCode.E9701 in ERROR_MESSAGES
    assert ErrorCode.E9801 in ERROR_MESSAGES
    assert ErrorCode.E9901 in ERROR_MESSAGES


def test_error_code_ranges():
    """Test error code ranges are correct"""
    # Routing errors
    assert ErrorCode.E9001.value.startswith("E90")

    # Authentication errors
    assert ErrorCode.E9101.value.startswith("E91")

    # Authorization errors
    assert ErrorCode.E9205.value.startswith("E92")

    # Validation errors
    assert ErrorCode.E9301.value.startswith("E93")

    # Rate limit errors
    assert ErrorCode.E9401.value.startswith("E94")

    # Webhook errors
    assert ErrorCode.E9701.value.startswith("E97")

    # Circuit breaker errors
    assert ErrorCode.E9801.value.startswith("E98")

    # Server errors
    assert ErrorCode.E9901.value.startswith("E99")
