"""
E2E tests for L09 API Gateway - L01 Data Layer Bridge

Tests the integration between L09 API Gateway and L01 Data Layer for:
- API request logging
- Authentication event tracking
- Rate limit event recording
"""

import asyncio
import pytest
from datetime import datetime, timedelta
from uuid import uuid4

from src.L01_data_layer.client import L01Client
from src.L09_api_gateway.services.l01_bridge import L09Bridge


@pytest.fixture
async def l01_client():
    """Create L01 client for testing."""
    client = L01Client(base_url="http://localhost:8002")
    yield client
    await client.close()


@pytest.fixture
async def l09_bridge():
    """Create L09 bridge for testing."""
    bridge = L09Bridge(l01_base_url="http://localhost:8002")
    await bridge.initialize()
    yield bridge
    await bridge.cleanup()


@pytest.mark.asyncio
async def test_record_api_request(l09_bridge, l01_client):
    """Test recording an API request."""
    # Arrange
    request_id = f"req-test-{uuid4()}"
    trace_id = uuid4().hex
    span_id = uuid4().hex[:16]
    timestamp = datetime.utcnow()

    # Act - Record API request
    success = await l09_bridge.record_api_request(
        request_id=request_id,
        trace_id=trace_id,
        span_id=span_id,
        timestamp=timestamp,
        method="GET",
        path="/api/test",
        status_code=200,
        latency_ms=45.67,
        consumer_id="test_consumer",
        tenant_id="test_tenant",
        authenticated=True,
        auth_method="api_key",
        rate_limit_tier="standard",
        client_ip="127.0.0.1",
        user_agent="test-agent",
    )

    # Assert
    assert success is True

    # Verify in L01 - Give it a moment to persist
    await asyncio.sleep(0.5)

    # Query L01 to verify the request was recorded
    # Note: L01Client doesn't have a get_api_request method yet,
    # so we'll just verify the record operation succeeded


@pytest.mark.asyncio
async def test_record_authentication_event(l09_bridge, l01_client):
    """Test recording authentication events."""
    # Arrange
    timestamp = datetime.utcnow()

    # Act - Record successful authentication
    success = await l09_bridge.record_authentication_event(
        timestamp=timestamp,
        auth_method="oauth",
        success=True,
        consumer_id="test_consumer",
        tenant_id="test_tenant",
        client_ip="127.0.0.1",
        user_agent="test-agent",
    )

    # Assert
    assert success is True

    # Act - Record failed authentication
    success_fail = await l09_bridge.record_authentication_event(
        timestamp=timestamp,
        auth_method="api_key",
        success=False,
        failure_reason="Invalid API key",
        client_ip="127.0.0.1",
        user_agent="test-agent",
    )

    # Assert
    assert success_fail is True


@pytest.mark.asyncio
async def test_record_rate_limit_event(l09_bridge, l01_client):
    """Test recording rate limit events."""
    # Arrange
    timestamp = datetime.utcnow()
    window_start = timestamp - timedelta(hours=1)
    window_end = timestamp + timedelta(hours=1)

    # Act - Record rate limit event (not exceeded)
    success = await l09_bridge.record_rate_limit_event(
        timestamp=timestamp,
        consumer_id="test_consumer",
        rate_limit_tier="standard",
        tokens_remaining=950,
        tokens_limit=1000,
        window_start=window_start,
        window_end=window_end,
        tenant_id="test_tenant",
        endpoint="/api/agents",
        tokens_requested=1,
        exceeded=False,
    )

    # Assert
    assert success is True

    # Act - Record rate limit exceeded event
    success_exceeded = await l09_bridge.record_rate_limit_event(
        timestamp=timestamp,
        consumer_id="test_consumer",
        rate_limit_tier="standard",
        tokens_remaining=0,
        tokens_limit=1000,
        window_start=window_start,
        window_end=window_end,
        tenant_id="test_tenant",
        endpoint="/api/agents",
        tokens_requested=1,
        exceeded=True,
    )

    # Assert
    assert success_exceeded is True


@pytest.mark.asyncio
async def test_full_api_request_lifecycle(l09_bridge, l01_client):
    """Test full API request lifecycle with auth and rate limiting."""
    # Arrange
    timestamp = datetime.utcnow()
    request_id = f"req-lifecycle-{uuid4()}"
    trace_id = uuid4().hex
    span_id = uuid4().hex[:16]
    consumer_id = "lifecycle_consumer"
    window_start = timestamp - timedelta(hours=1)
    window_end = timestamp + timedelta(hours=1)

    # Act 1 - Record authentication
    auth_success = await l09_bridge.record_authentication_event(
        timestamp=timestamp,
        auth_method="jwt",
        success=True,
        consumer_id=consumer_id,
        tenant_id="lifecycle_tenant",
        client_ip="127.0.0.1",
        user_agent="lifecycle-test",
    )
    assert auth_success is True

    # Act 2 - Record rate limit check
    rate_limit_success = await l09_bridge.record_rate_limit_event(
        timestamp=timestamp,
        consumer_id=consumer_id,
        rate_limit_tier="premium",
        tokens_remaining=4999,
        tokens_limit=5000,
        window_start=window_start,
        window_end=window_end,
        endpoint="/api/v1/agents",
        tokens_requested=1,
        exceeded=False,
    )
    assert rate_limit_success is True

    # Act 3 - Record API request
    request_success = await l09_bridge.record_api_request(
        request_id=request_id,
        trace_id=trace_id,
        span_id=span_id,
        timestamp=timestamp,
        method="POST",
        path="/api/v1/agents",
        status_code=201,
        latency_ms=123.45,
        consumer_id=consumer_id,
        tenant_id="lifecycle_tenant",
        authenticated=True,
        auth_method="jwt",
        rate_limit_tier="premium",
        client_ip="127.0.0.1",
        user_agent="lifecycle-test",
    )
    assert request_success is True

    # Give it a moment to persist
    await asyncio.sleep(0.5)


@pytest.mark.asyncio
async def test_bridge_disabled(l09_bridge):
    """Test that bridge gracefully handles being disabled."""
    # Arrange
    l09_bridge.enabled = False
    timestamp = datetime.utcnow()

    # Act - Try to record when disabled
    success = await l09_bridge.record_authentication_event(
        timestamp=timestamp,
        auth_method="api_key",
        success=True,
        consumer_id="test",
    )

    # Assert - Should return False when disabled
    assert success is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
