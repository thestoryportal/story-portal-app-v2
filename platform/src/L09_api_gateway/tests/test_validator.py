"""
Tests for Request Validator
"""

import pytest
from ..services.validator import RequestValidator
from ..models import RequestContext, RequestMetadata
from ..errors import ValidationError, ErrorCode


@pytest.mark.asyncio
async def test_valid_request():
    """Test valid request passes validation"""
    validator = RequestValidator()

    context = RequestContext(
        trace_id="a" * 32,
        span_id="b" * 16,
        metadata=RequestMetadata(
            method="POST",
            path="/api/test",
            headers={"content-type": "application/json"},
            query_params={},
            client_ip="127.0.0.1",
        ),
    )

    body = b'{"message": "Hello World"}'

    # Should not raise
    await validator.validate_request(context, body)


@pytest.mark.asyncio
async def test_body_size_limit():
    """Test body size limit enforcement"""
    validator = RequestValidator(max_body_size=100)

    context = RequestContext(
        trace_id="a" * 32,
        span_id="b" * 16,
        metadata=RequestMetadata(
            method="POST",
            path="/api/test",
            headers={},
            query_params={},
            client_ip="127.0.0.1",
        ),
    )

    # Body exceeds limit
    body = b"x" * 200

    with pytest.raises(ValidationError) as exc_info:
        await validator.validate_request(context, body)

    assert exc_info.value.code == ErrorCode.E9304


@pytest.mark.asyncio
async def test_null_byte_detection():
    """Test null byte detection"""
    validator = RequestValidator()

    context = RequestContext(
        trace_id="a" * 32,
        span_id="b" * 16,
        metadata=RequestMetadata(
            method="POST",
            path="/api/test",
            headers={},
            query_params={},
            client_ip="127.0.0.1",
        ),
    )

    # Body contains null byte
    body = b"hello\x00world"

    with pytest.raises(ValidationError) as exc_info:
        await validator.validate_request(context, body)

    assert exc_info.value.code == ErrorCode.E9307


@pytest.mark.asyncio
async def test_invalid_json():
    """Test invalid JSON detection"""
    validator = RequestValidator()

    context = RequestContext(
        trace_id="a" * 32,
        span_id="b" * 16,
        metadata=RequestMetadata(
            method="POST",
            path="/api/test",
            headers={"content-type": "application/json"},
            query_params={},
            client_ip="127.0.0.1",
            content_type="application/json",  # Need to set this explicitly
        ),
    )

    # Invalid JSON
    body = b"{invalid json"

    with pytest.raises(ValidationError) as exc_info:
        await validator.validate_request(context, body)

    assert exc_info.value.code == ErrorCode.E9305


@pytest.mark.asyncio
async def test_header_count_limit():
    """Test header count limit"""
    validator = RequestValidator(max_header_count=5)

    headers = {f"header-{i}": "value" for i in range(10)}

    context = RequestContext(
        trace_id="a" * 32,
        span_id="b" * 16,
        metadata=RequestMetadata(
            method="GET",
            path="/api/test",
            headers=headers,
            query_params={},
            client_ip="127.0.0.1",
        ),
    )

    with pytest.raises(ValidationError) as exc_info:
        await validator.validate_request(context)

    assert exc_info.value.code == ErrorCode.E9309


@pytest.mark.asyncio
async def test_unicode_normalization():
    """Test Unicode normalization"""
    validator = RequestValidator()

    # Test NFC normalization
    text = "café"  # é as single character
    normalized = validator.normalize_unicode(text)

    assert normalized == "café"
    assert len(normalized) == 4
