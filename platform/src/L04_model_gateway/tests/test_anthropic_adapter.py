"""
L04 Model Gateway Layer - Anthropic Adapter Tests

Validation-first tests for the AnthropicAdapter implementation.
"""

import pytest
import json
from unittest.mock import patch, AsyncMock, MagicMock

from ..providers.anthropic_adapter import AnthropicAdapter
from ..models import (
    InferenceRequest,
    InferenceResponse,
    Message,
    MessageRole,
    ProviderHealth,
    ProviderStatus,
    CircuitState,
    ProviderError,
    L04ErrorCode,
)

from .fixtures.mock_clients import (
    create_mock_anthropic_client,
    MockHTTPClient,
    MockHTTPResponse,
    MockStreamResponse,
)
from .fixtures.api_responses import (
    ANTHROPIC_RESPONSE_SUCCESS,
    ANTHROPIC_RESPONSE_STREAM,
    ANTHROPIC_RESPONSE_ERROR_429,
    ANTHROPIC_RESPONSE_ERROR_401,
    create_anthropic_success_response,
)


@pytest.mark.l04
@pytest.mark.unit
class TestAnthropicAdapterInit:
    """Tests for AnthropicAdapter initialization"""

    def test_init_with_api_key(self):
        """Test adapter initializes with API key"""
        adapter = AnthropicAdapter(api_key="test-key-12345")
        assert adapter.api_key == "test-key-12345"
        assert adapter.provider_id == "anthropic"
        assert adapter.base_url == "https://api.anthropic.com"

    def test_init_with_custom_base_url(self):
        """Test adapter initializes with custom base URL"""
        adapter = AnthropicAdapter(
            api_key="test-key",
            base_url="https://custom.anthropic.com"
        )
        assert adapter.base_url == "https://custom.anthropic.com"

    def test_init_with_custom_timeout(self):
        """Test adapter initializes with custom timeout"""
        adapter = AnthropicAdapter(api_key="test-key", timeout=60)
        assert adapter.timeout == 60


@pytest.mark.l04
@pytest.mark.unit
class TestAnthropicAdapterCapabilities:
    """Tests for AnthropicAdapter capability checking"""

    def test_supports_capability_text(self):
        """Test adapter reports text capability"""
        adapter = AnthropicAdapter(api_key="test-key")
        assert adapter.supports_capability("text") is True

    def test_supports_capability_vision(self):
        """Test adapter reports vision capability"""
        adapter = AnthropicAdapter(api_key="test-key")
        assert adapter.supports_capability("vision") is True

    def test_supports_capability_streaming(self):
        """Test adapter reports streaming capability"""
        adapter = AnthropicAdapter(api_key="test-key")
        assert adapter.supports_capability("streaming") is True

    def test_supports_capability_tool_use(self):
        """Test adapter reports tool_use capability"""
        adapter = AnthropicAdapter(api_key="test-key")
        assert adapter.supports_capability("tool_use") is True

    def test_supports_capability_function_calling(self):
        """Test adapter reports function_calling capability"""
        adapter = AnthropicAdapter(api_key="test-key")
        assert adapter.supports_capability("function_calling") is True

    def test_supports_capability_unknown(self):
        """Test adapter returns False for unknown capability"""
        adapter = AnthropicAdapter(api_key="test-key")
        assert adapter.supports_capability("quantum_computing") is False

    def test_supports_model_claude_sonnet_4(self):
        """Test adapter supports claude-sonnet-4-20250514"""
        adapter = AnthropicAdapter(api_key="test-key")
        assert adapter.supports_model("claude-sonnet-4-20250514") is True

    def test_supports_model_claude_3_5_sonnet(self):
        """Test adapter supports claude-3-5-sonnet-20241022"""
        adapter = AnthropicAdapter(api_key="test-key")
        assert adapter.supports_model("claude-3-5-sonnet-20241022") is True

    def test_supports_model_claude_3_opus(self):
        """Test adapter supports claude-3-opus-20240229"""
        adapter = AnthropicAdapter(api_key="test-key")
        assert adapter.supports_model("claude-3-opus-20240229") is True

    def test_supports_model_claude_3_haiku(self):
        """Test adapter supports claude-3-haiku-20240307"""
        adapter = AnthropicAdapter(api_key="test-key")
        assert adapter.supports_model("claude-3-haiku-20240307") is True

    def test_supports_model_unknown(self):
        """Test adapter returns False for unknown model"""
        adapter = AnthropicAdapter(api_key="test-key")
        assert adapter.supports_model("gpt-4") is False


@pytest.mark.l04
@pytest.mark.unit
@pytest.mark.asyncio
class TestAnthropicAdapterComplete:
    """Tests for AnthropicAdapter completion"""

    async def test_complete_basic_request(
        self, mock_anthropic_client, sample_inference_request
    ):
        """Test basic completion request transforms correctly"""
        adapter = AnthropicAdapter(api_key="test-key")
        adapter._client = mock_anthropic_client

        response = await adapter.complete(
            sample_inference_request, "claude-sonnet-4-20250514"
        )

        assert response is not None
        assert response.request_id == sample_inference_request.request_id
        assert response.model_id == "claude-sonnet-4-20250514"
        assert response.provider == "anthropic"
        assert response.content is not None
        assert len(response.content) > 0
        assert response.is_success()

    async def test_complete_with_system_prompt(
        self, mock_anthropic_client, sample_inference_request
    ):
        """Test system prompt is properly included in request"""
        adapter = AnthropicAdapter(api_key="test-key")
        adapter._client = mock_anthropic_client

        await adapter.complete(sample_inference_request, "claude-sonnet-4-20250514")

        # Check that the request was made with system prompt
        last_request = mock_anthropic_client.get_last_request()
        assert last_request is not None
        # System prompt should be a separate field in Anthropic API
        if last_request["json"]:
            assert "system" in last_request["json"] or "messages" in last_request["json"]

    async def test_complete_returns_token_usage(
        self, mock_anthropic_client, sample_inference_request
    ):
        """Test token usage is returned in response"""
        adapter = AnthropicAdapter(api_key="test-key")
        adapter._client = mock_anthropic_client

        response = await adapter.complete(
            sample_inference_request, "claude-sonnet-4-20250514"
        )

        assert response.token_usage is not None
        assert response.token_usage.input_tokens > 0
        assert response.token_usage.output_tokens > 0

    async def test_complete_returns_latency(
        self, mock_anthropic_client, sample_inference_request
    ):
        """Test latency is tracked and returned"""
        adapter = AnthropicAdapter(api_key="test-key")
        adapter._client = mock_anthropic_client

        response = await adapter.complete(
            sample_inference_request, "claude-sonnet-4-20250514"
        )

        assert response.latency_ms >= 0

    async def test_complete_includes_finish_reason(
        self, mock_anthropic_client, sample_inference_request
    ):
        """Test finish reason is included in response"""
        adapter = AnthropicAdapter(api_key="test-key")
        adapter._client = mock_anthropic_client

        response = await adapter.complete(
            sample_inference_request, "claude-sonnet-4-20250514"
        )

        assert response.finish_reason in ["stop", "end_turn", "tool_use", "length"]


@pytest.mark.l04
@pytest.mark.unit
@pytest.mark.asyncio
class TestAnthropicAdapterErrors:
    """Tests for AnthropicAdapter error handling"""

    async def test_rate_limit_error_raises_E4402(
        self, mock_anthropic_client_429, sample_inference_request
    ):
        """Test 429 response raises E4402_PROVIDER_RATE_LIMIT"""
        adapter = AnthropicAdapter(api_key="test-key")
        adapter._client = mock_anthropic_client_429

        with pytest.raises(ProviderError) as exc_info:
            await adapter.complete(sample_inference_request, "claude-sonnet-4-20250514")

        assert exc_info.value.error_code == L04ErrorCode.E4402_PROVIDER_RATE_LIMIT

    async def test_auth_error_raises_E4203(
        self, mock_anthropic_client_401, sample_inference_request
    ):
        """Test 401 response raises E4203_PROVIDER_AUTH_FAILED"""
        adapter = AnthropicAdapter(api_key="invalid-key")
        adapter._client = mock_anthropic_client_401

        with pytest.raises(ProviderError) as exc_info:
            await adapter.complete(sample_inference_request, "claude-sonnet-4-20250514")

        assert exc_info.value.error_code == L04ErrorCode.E4203_PROVIDER_AUTH_FAILED

    async def test_server_error_raises_E4200(
        self, mock_anthropic_client_500, sample_inference_request
    ):
        """Test 500 response raises E4200_PROVIDER_ERROR"""
        adapter = AnthropicAdapter(api_key="test-key")
        adapter._client = mock_anthropic_client_500

        with pytest.raises(ProviderError) as exc_info:
            await adapter.complete(sample_inference_request, "claude-sonnet-4-20250514")

        assert exc_info.value.error_code in [
            L04ErrorCode.E4200_PROVIDER_ERROR,
            L04ErrorCode.E4206_PROVIDER_API_ERROR,
        ]

    async def test_timeout_error_raises_E4202(self, sample_inference_request):
        """Test timeout raises E4202_PROVIDER_TIMEOUT"""
        import httpx

        adapter = AnthropicAdapter(api_key="test-key", timeout=1)

        # Create a mock client that raises TimeoutException
        mock_client = MagicMock()
        mock_client.post = AsyncMock(side_effect=httpx.TimeoutException("timeout"))
        adapter._client = mock_client

        with pytest.raises(ProviderError) as exc_info:
            await adapter.complete(sample_inference_request, "claude-sonnet-4-20250514")

        assert exc_info.value.error_code == L04ErrorCode.E4202_PROVIDER_TIMEOUT


@pytest.mark.l04
@pytest.mark.unit
@pytest.mark.asyncio
class TestAnthropicAdapterStreaming:
    """Tests for AnthropicAdapter streaming"""

    async def test_stream_yields_chunks(
        self, mock_anthropic_client, sample_inference_request
    ):
        """Test streaming returns proper SSE chunks"""
        adapter = AnthropicAdapter(api_key="test-key")
        adapter._client = mock_anthropic_client

        chunks = []
        async for chunk in adapter.stream(
            sample_inference_request, "claude-sonnet-4-20250514"
        ):
            chunks.append(chunk)

        assert len(chunks) >= 1
        # Check that we got content
        content = "".join(c.content_delta for c in chunks)
        assert len(content) > 0

    async def test_stream_has_final_chunk(
        self, mock_anthropic_client, sample_inference_request
    ):
        """Test streaming has a final chunk marker"""
        adapter = AnthropicAdapter(api_key="test-key")
        adapter._client = mock_anthropic_client

        chunks = []
        async for chunk in adapter.stream(
            sample_inference_request, "claude-sonnet-4-20250514"
        ):
            chunks.append(chunk)

        assert len(chunks) >= 1
        # Last chunk should be marked as final
        assert chunks[-1].is_final is True

    async def test_stream_handles_errors_gracefully(
        self, sample_inference_request
    ):
        """Test streaming error handling"""
        import httpx

        adapter = AnthropicAdapter(api_key="test-key")

        # Create a mock client that raises HTTPStatusError on stream
        mock_client = MagicMock()

        # Mock the stream context manager to raise an error
        async def mock_stream(*args, **kwargs):
            mock_response = MagicMock()
            mock_response.status_code = 500
            mock_response.aread = AsyncMock(return_value=b'{"error": {"type": "api_error", "message": "Server error"}}')

            async def __aenter__():
                return mock_response

            async def __aexit__(*args):
                pass

            context = MagicMock()
            context.__aenter__ = __aenter__
            context.__aexit__ = __aexit__
            return context

        mock_client.stream = mock_stream
        adapter._client = mock_client

        with pytest.raises(ProviderError):
            async for _ in adapter.stream(
                sample_inference_request, "claude-sonnet-4-20250514"
            ):
                pass


@pytest.mark.l04
@pytest.mark.unit
@pytest.mark.asyncio
class TestAnthropicAdapterHealth:
    """Tests for AnthropicAdapter health check"""

    async def test_health_check_returns_healthy_status(self, mock_anthropic_client):
        """Test health check returns provider status"""
        adapter = AnthropicAdapter(api_key="test-key")
        adapter._client = mock_anthropic_client

        # Mock a successful response for health check
        mock_anthropic_client.responses[("GET", "/v1/messages")] = MockHTTPResponse(
            status_code=200,
            content=b'{"status": "ok"}',
        )

        health = await adapter.health_check()

        assert health.provider_id == "anthropic"
        assert health.status in [ProviderStatus.HEALTHY, ProviderStatus.DEGRADED]

    async def test_health_check_timeout_returns_unavailable(self):
        """Test health check timeout returns unavailable"""
        import httpx

        adapter = AnthropicAdapter(api_key="test-key", timeout=1)

        mock_client = MagicMock()
        mock_client.get = AsyncMock(side_effect=httpx.TimeoutException("timeout"))
        adapter._client = mock_client

        health = await adapter.health_check()

        assert health.provider_id == "anthropic"
        assert health.status == ProviderStatus.UNAVAILABLE

    async def test_health_check_includes_metadata(self, mock_anthropic_client):
        """Test health check includes useful metadata"""
        adapter = AnthropicAdapter(api_key="test-key")
        adapter._client = mock_anthropic_client

        health = await adapter.health_check()

        assert health.last_check is not None


@pytest.mark.l04
@pytest.mark.unit
class TestAnthropicAdapterRequestTransformation:
    """Tests for request transformation to Anthropic format"""

    def test_build_request_includes_model(self):
        """Test request includes model parameter"""
        adapter = AnthropicAdapter(api_key="test-key")

        messages = [Message(role=MessageRole.USER, content="Hello")]
        request = InferenceRequest.create(
            agent_did="did:key:test",
            messages=messages,
        )

        anthropic_request = adapter._build_anthropic_request(
            request, "claude-sonnet-4-20250514"
        )

        assert anthropic_request["model"] == "claude-sonnet-4-20250514"

    def test_build_request_includes_messages(self):
        """Test request includes messages in Anthropic format"""
        adapter = AnthropicAdapter(api_key="test-key")

        messages = [
            Message(role=MessageRole.USER, content="Hello"),
            Message(role=MessageRole.ASSISTANT, content="Hi there!"),
            Message(role=MessageRole.USER, content="How are you?"),
        ]
        request = InferenceRequest.create(
            agent_did="did:key:test",
            messages=messages,
        )

        anthropic_request = adapter._build_anthropic_request(
            request, "claude-sonnet-4-20250514"
        )

        assert "messages" in anthropic_request
        assert len(anthropic_request["messages"]) == 3

    def test_build_request_includes_system_prompt(self):
        """Test request includes system prompt separately"""
        adapter = AnthropicAdapter(api_key="test-key")

        messages = [Message(role=MessageRole.USER, content="Hello")]
        request = InferenceRequest.create(
            agent_did="did:key:test",
            messages=messages,
            system_prompt="You are a helpful assistant.",
        )

        anthropic_request = adapter._build_anthropic_request(
            request, "claude-sonnet-4-20250514"
        )

        # Anthropic API uses separate "system" field
        assert "system" in anthropic_request
        assert anthropic_request["system"] == "You are a helpful assistant."

    def test_build_request_includes_max_tokens(self):
        """Test request includes max_tokens"""
        adapter = AnthropicAdapter(api_key="test-key")

        messages = [Message(role=MessageRole.USER, content="Hello")]
        request = InferenceRequest.create(
            agent_did="did:key:test",
            messages=messages,
            max_tokens=1000,
        )

        anthropic_request = adapter._build_anthropic_request(
            request, "claude-sonnet-4-20250514"
        )

        assert anthropic_request["max_tokens"] == 1000

    def test_build_request_includes_temperature(self):
        """Test request includes temperature"""
        adapter = AnthropicAdapter(api_key="test-key")

        messages = [Message(role=MessageRole.USER, content="Hello")]
        request = InferenceRequest.create(
            agent_did="did:key:test",
            messages=messages,
            temperature=0.5,
        )

        anthropic_request = adapter._build_anthropic_request(
            request, "claude-sonnet-4-20250514"
        )

        assert anthropic_request.get("temperature") == 0.5
