"""
L04 Model Gateway Layer - L01 Bridge Tests

Tests for L01 Data Layer integration.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone

import httpx

from ..services.l01_bridge import L01Bridge
from ..models import (
    InferenceRequest,
    InferenceResponse,
    Message,
    MessageRole,
    TokenUsage,
    ResponseStatus,
)


@pytest.mark.l04
@pytest.mark.unit
class TestL01BridgeInit:
    """Tests for L01Bridge initialization"""

    def test_init_with_defaults(self):
        """Test bridge initializes with default values"""
        bridge = L01Bridge()
        assert bridge.base_url == "http://localhost:8001"
        assert bridge.timeout == 10.0
        assert bridge.max_retries == 2
        assert bridge.enabled is True

    def test_init_with_custom_url(self):
        """Test bridge initializes with custom URL"""
        bridge = L01Bridge(base_url="http://custom-l01:8080")
        assert bridge.base_url == "http://custom-l01:8080"

    def test_init_with_api_key(self):
        """Test bridge initializes with API key"""
        bridge = L01Bridge(api_key="test-api-key")
        assert bridge.api_key == "test-api-key"

    def test_init_with_custom_timeout(self):
        """Test bridge initializes with custom timeout"""
        bridge = L01Bridge(timeout=30.0)
        assert bridge.timeout == 30.0

    def test_init_strips_trailing_slash(self):
        """Test bridge strips trailing slash from URL"""
        bridge = L01Bridge(base_url="http://localhost:8001/")
        assert bridge.base_url == "http://localhost:8001"


@pytest.mark.l04
@pytest.mark.unit
@pytest.mark.asyncio
class TestL01BridgeRecordInference:
    """Tests for recording inference usage"""

    async def test_record_inference_success(self):
        """Test successful inference recording"""
        bridge = L01Bridge(base_url="http://localhost:8001")

        # Create mock client
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        bridge._client = mock_client

        # Create test request and response
        messages = [Message(role=MessageRole.USER, content="Hello")]
        request = InferenceRequest.create(
            agent_did="did:key:test-agent",
            messages=messages,
        )

        response = InferenceResponse(
            request_id=request.request_id,
            model_id="gpt-4o",
            provider="openai",
            content="Hello! How can I help?",
            token_usage=TokenUsage(input_tokens=10, output_tokens=20),
            latency_ms=150,
            status=ResponseStatus.SUCCESS,
        )

        result = await bridge.record_inference(request, response)

        assert result is True
        mock_client.post.assert_called_once()
        call_args = mock_client.post.call_args
        assert "/api/models/usage" in str(call_args)

    async def test_record_inference_disabled(self):
        """Test recording when bridge is disabled"""
        bridge = L01Bridge()
        bridge.enabled = False

        messages = [Message(role=MessageRole.USER, content="Hello")]
        request = InferenceRequest.create(
            agent_did="did:key:test",
            messages=messages,
        )
        response = InferenceResponse(
            request_id=request.request_id,
            model_id="gpt-4o",
            provider="openai",
            content="Response",
            token_usage=TokenUsage(input_tokens=5, output_tokens=10),
            latency_ms=100,
        )

        result = await bridge.record_inference(request, response)
        assert result is False

    async def test_record_inference_handles_connection_error(self):
        """Test graceful handling of connection errors"""
        bridge = L01Bridge(base_url="http://localhost:9999", max_retries=0)

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(
            side_effect=httpx.ConnectError("Connection refused")
        )
        bridge._client = mock_client

        messages = [Message(role=MessageRole.USER, content="Hello")]
        request = InferenceRequest.create(
            agent_did="did:key:test",
            messages=messages,
        )
        response = InferenceResponse(
            request_id=request.request_id,
            model_id="gpt-4o",
            provider="openai",
            content="Response",
            token_usage=TokenUsage(input_tokens=5, output_tokens=10),
            latency_ms=100,
        )

        # Should not raise, returns False
        result = await bridge.record_inference(request, response)
        assert result is False

    async def test_record_inference_handles_timeout(self):
        """Test graceful handling of timeouts"""
        bridge = L01Bridge(timeout=1.0, max_retries=0)

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(side_effect=httpx.TimeoutException("Timeout"))
        bridge._client = mock_client

        messages = [Message(role=MessageRole.USER, content="Hello")]
        request = InferenceRequest.create(
            agent_did="did:key:test",
            messages=messages,
        )
        response = InferenceResponse(
            request_id=request.request_id,
            model_id="gpt-4o",
            provider="openai",
            content="Response",
            token_usage=TokenUsage(input_tokens=5, output_tokens=10),
            latency_ms=100,
        )

        result = await bridge.record_inference(request, response)
        assert result is False

    async def test_record_inference_retries_on_server_error(self):
        """Test retry logic on server errors"""
        bridge = L01Bridge(max_retries=2)

        # First two calls fail with 500, third succeeds
        mock_response_500 = MagicMock()
        mock_response_500.status_code = 500
        mock_response_500.raise_for_status = MagicMock(
            side_effect=httpx.HTTPStatusError(
                "Server Error",
                request=MagicMock(),
                response=mock_response_500,
            )
        )

        mock_response_200 = MagicMock()
        mock_response_200.status_code = 200
        mock_response_200.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(
            side_effect=[
                httpx.HTTPStatusError(
                    "Server Error",
                    request=MagicMock(),
                    response=mock_response_500,
                ),
                httpx.HTTPStatusError(
                    "Server Error",
                    request=MagicMock(),
                    response=mock_response_500,
                ),
                mock_response_200,
            ]
        )
        bridge._client = mock_client

        messages = [Message(role=MessageRole.USER, content="Hello")]
        request = InferenceRequest.create(
            agent_did="did:key:test",
            messages=messages,
        )
        response = InferenceResponse(
            request_id=request.request_id,
            model_id="gpt-4o",
            provider="openai",
            content="Response",
            token_usage=TokenUsage(input_tokens=5, output_tokens=10),
            latency_ms=100,
        )

        result = await bridge.record_inference(request, response)
        assert result is True
        assert mock_client.post.call_count == 3


@pytest.mark.l04
@pytest.mark.unit
@pytest.mark.asyncio
class TestL01BridgeRecordInferenceSimple:
    """Tests for simple inference recording"""

    async def test_record_simple_success(self):
        """Test simple recording with basic parameters"""
        bridge = L01Bridge()

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        bridge._client = mock_client

        result = await bridge.record_inference_simple(
            agent_did="did:key:test-agent",
            model_id="gpt-4o",
            input_tokens=100,
            output_tokens=50,
            latency_ms=250,
            provider="openai",
        )

        assert result is True
        mock_client.post.assert_called_once()

    async def test_record_simple_with_optional_params(self):
        """Test simple recording with all optional parameters"""
        bridge = L01Bridge()

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        bridge._client = mock_client

        result = await bridge.record_inference_simple(
            agent_did="did:key:test-agent",
            model_id="gpt-4o",
            input_tokens=100,
            output_tokens=50,
            latency_ms=250,
            provider="openai",
            cached=True,
            session_id="session-123",
            tenant_id="tenant-456",
            request_id="req-789",
        )

        assert result is True

        # Check payload includes optional params
        call_args = mock_client.post.call_args
        payload = call_args[1]["json"]
        assert payload["session_id"] == "session-123"
        assert payload["tenant_id"] == "tenant-456"
        assert payload["request_id"] == "req-789"
        assert payload["cached"] is True

    async def test_record_simple_disabled(self):
        """Test simple recording when disabled"""
        bridge = L01Bridge()
        bridge.enabled = False

        result = await bridge.record_inference_simple(
            agent_did="did:key:test",
            model_id="gpt-4o",
            input_tokens=10,
            output_tokens=5,
            latency_ms=100,
        )

        assert result is False


@pytest.mark.l04
@pytest.mark.unit
@pytest.mark.asyncio
class TestL01BridgeHealthCheck:
    """Tests for health check functionality"""

    async def test_health_check_healthy(self):
        """Test health check returns healthy status"""
        bridge = L01Bridge()

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.elapsed = MagicMock()
        mock_response.elapsed.total_seconds = MagicMock(return_value=0.05)

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        bridge._client = mock_client

        health = await bridge.health_check()

        assert health["status"] == "healthy"
        assert health["reachable"] is True
        assert "latency_ms" in health

    async def test_health_check_timeout(self):
        """Test health check handles timeout"""
        bridge = L01Bridge(timeout=1.0)

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(side_effect=httpx.TimeoutException("Timeout"))
        bridge._client = mock_client

        health = await bridge.health_check()

        assert health["status"] == "unavailable"
        assert health["reachable"] is False
        assert health["error"] == "timeout"

    async def test_health_check_connection_error(self):
        """Test health check handles connection errors"""
        bridge = L01Bridge()

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(
            side_effect=httpx.ConnectError("Connection refused")
        )
        bridge._client = mock_client

        health = await bridge.health_check()

        assert health["status"] == "unavailable"
        assert health["reachable"] is False
        assert "connection_failed" in health["error"]


@pytest.mark.l04
@pytest.mark.unit
@pytest.mark.asyncio
class TestL01BridgePublishEvent:
    """Tests for event publishing"""

    async def test_publish_event_success(self):
        """Test successful event publishing"""
        bridge = L01Bridge()

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        bridge._client = mock_client

        result = await bridge.publish_event(
            event_type="inference_completed",
            payload={
                "model_id": "gpt-4o",
                "tokens": 150,
            },
        )

        assert result is True
        mock_client.post.assert_called_once()

    async def test_publish_event_failure(self):
        """Test event publishing handles failures gracefully"""
        bridge = L01Bridge()

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(
            side_effect=httpx.ConnectError("Connection refused")
        )
        bridge._client = mock_client

        result = await bridge.publish_event(
            event_type="inference_completed",
            payload={"test": "data"},
        )

        assert result is False


@pytest.mark.l04
@pytest.mark.unit
@pytest.mark.asyncio
class TestL01BridgeGetAgentUsage:
    """Tests for agent usage retrieval"""

    async def test_get_agent_usage_success(self):
        """Test successful usage retrieval"""
        bridge = L01Bridge()

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json = MagicMock(
            return_value={
                "total_requests": 100,
                "total_tokens": 5000,
                "total_cost_cents": 150,
            }
        )
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        bridge._client = mock_client

        usage = await bridge.get_agent_usage("did:key:test-agent")

        assert usage["total_requests"] == 100
        assert usage["total_tokens"] == 5000

    async def test_get_agent_usage_with_time_range(self):
        """Test usage retrieval with time range"""
        bridge = L01Bridge()

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json = MagicMock(return_value={"total_requests": 50})
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        bridge._client = mock_client

        start = datetime(2024, 1, 1, tzinfo=timezone.utc)
        end = datetime(2024, 1, 31, tzinfo=timezone.utc)

        usage = await bridge.get_agent_usage(
            "did:key:test-agent",
            start_time=start,
            end_time=end,
        )

        assert usage["total_requests"] == 50

        # Verify params were passed
        call_args = mock_client.get.call_args
        params = call_args[1]["params"]
        assert "start_time" in params
        assert "end_time" in params

    async def test_get_agent_usage_failure(self):
        """Test usage retrieval handles failures"""
        bridge = L01Bridge()

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(
            side_effect=httpx.ConnectError("Connection refused")
        )
        bridge._client = mock_client

        usage = await bridge.get_agent_usage("did:key:test-agent")

        # Should return error response, not raise
        assert "error" in usage
        assert usage["total_requests"] == 0


@pytest.mark.l04
@pytest.mark.unit
@pytest.mark.asyncio
class TestL01BridgeContextManager:
    """Tests for context manager functionality"""

    async def test_context_manager_creates_client(self):
        """Test context manager creates client on enter"""
        bridge = L01Bridge()
        assert bridge._client is None

        async with bridge:
            assert bridge._client is not None

    async def test_context_manager_cleanup(self):
        """Test context manager cleans up on exit"""
        bridge = L01Bridge()

        # Mock client to verify aclose is called
        mock_client = AsyncMock()
        mock_client.aclose = AsyncMock()

        async with bridge:
            bridge._client = mock_client

        mock_client.aclose.assert_called_once()


@pytest.mark.l04
@pytest.mark.unit
@pytest.mark.asyncio
class TestL01BridgeAuthHeader:
    """Tests for authentication header handling"""

    async def test_auth_header_included_when_api_key_provided(self):
        """Test Authorization header is included when API key is set"""
        bridge = L01Bridge(api_key="test-key-123")

        # Get client to trigger creation
        client = await bridge._get_client()

        # Check headers
        assert "Authorization" in client.headers
        assert client.headers["Authorization"] == "Bearer test-key-123"

    async def test_no_auth_header_when_no_api_key(self):
        """Test no Authorization header when API key is not set"""
        bridge = L01Bridge(api_key=None)

        client = await bridge._get_client()

        # Should not have Authorization header
        assert "Authorization" not in client.headers
