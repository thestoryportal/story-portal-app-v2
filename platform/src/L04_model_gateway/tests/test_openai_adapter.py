"""
L04 Model Gateway Layer - OpenAI Adapter Tests

Validation-first tests for the OpenAIAdapter implementation.
"""

import pytest
import json
from unittest.mock import patch, AsyncMock, MagicMock

from ..providers.openai_adapter import OpenAIAdapter
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
    create_mock_openai_client,
    MockHTTPClient,
    MockHTTPResponse,
    MockStreamResponse,
)
from .fixtures.api_responses import (
    OPENAI_RESPONSE_SUCCESS,
    OPENAI_RESPONSE_STREAM,
    OPENAI_RESPONSE_WITH_FUNCTION_CALL,
    create_openai_success_response,
)


@pytest.mark.l04
@pytest.mark.unit
class TestOpenAIAdapterInit:
    """Tests for OpenAIAdapter initialization"""

    def test_init_with_api_key(self):
        """Test adapter initializes with API key"""
        adapter = OpenAIAdapter(api_key="sk-test-key-12345")
        assert adapter.api_key == "sk-test-key-12345"
        assert adapter.provider_id == "openai"
        assert adapter.base_url == "https://api.openai.com/v1"

    def test_init_with_custom_base_url(self):
        """Test adapter initializes with custom base URL"""
        adapter = OpenAIAdapter(
            api_key="sk-test",
            base_url="https://custom.openai.azure.com"
        )
        assert adapter.base_url == "https://custom.openai.azure.com"

    def test_init_with_custom_timeout(self):
        """Test adapter initializes with custom timeout"""
        adapter = OpenAIAdapter(api_key="sk-test", timeout=120)
        assert adapter.timeout == 120


@pytest.mark.l04
@pytest.mark.unit
class TestOpenAIAdapterCapabilities:
    """Tests for OpenAIAdapter capability checking"""

    def test_supports_capability_text(self):
        """Test adapter reports text capability"""
        adapter = OpenAIAdapter(api_key="sk-test")
        assert adapter.supports_capability("text") is True

    def test_supports_capability_vision(self):
        """Test adapter reports vision capability"""
        adapter = OpenAIAdapter(api_key="sk-test")
        assert adapter.supports_capability("vision") is True

    def test_supports_capability_streaming(self):
        """Test adapter reports streaming capability"""
        adapter = OpenAIAdapter(api_key="sk-test")
        assert adapter.supports_capability("streaming") is True

    def test_supports_capability_tool_use(self):
        """Test adapter reports tool_use capability"""
        adapter = OpenAIAdapter(api_key="sk-test")
        assert adapter.supports_capability("tool_use") is True

    def test_supports_capability_function_calling(self):
        """Test adapter reports function_calling capability"""
        adapter = OpenAIAdapter(api_key="sk-test")
        assert adapter.supports_capability("function_calling") is True

    def test_supports_capability_unknown(self):
        """Test adapter returns False for unknown capability"""
        adapter = OpenAIAdapter(api_key="sk-test")
        assert adapter.supports_capability("quantum_computing") is False

    def test_supports_model_gpt4o(self):
        """Test adapter supports gpt-4o"""
        adapter = OpenAIAdapter(api_key="sk-test")
        assert adapter.supports_model("gpt-4o") is True

    def test_supports_model_gpt4o_mini(self):
        """Test adapter supports gpt-4o-mini"""
        adapter = OpenAIAdapter(api_key="sk-test")
        assert adapter.supports_model("gpt-4o-mini") is True

    def test_supports_model_gpt4_turbo(self):
        """Test adapter supports gpt-4-turbo"""
        adapter = OpenAIAdapter(api_key="sk-test")
        assert adapter.supports_model("gpt-4-turbo-2024-04-09") is True

    def test_supports_model_gpt35_turbo(self):
        """Test adapter supports gpt-3.5-turbo"""
        adapter = OpenAIAdapter(api_key="sk-test")
        assert adapter.supports_model("gpt-3.5-turbo") is True

    def test_supports_model_unknown(self):
        """Test adapter returns False for unknown model"""
        adapter = OpenAIAdapter(api_key="sk-test")
        assert adapter.supports_model("claude-3-opus") is False


@pytest.mark.l04
@pytest.mark.unit
@pytest.mark.asyncio
class TestOpenAIAdapterComplete:
    """Tests for OpenAIAdapter completion"""

    async def test_complete_basic_request(
        self, mock_openai_client, sample_inference_request
    ):
        """Test basic chat completion request"""
        adapter = OpenAIAdapter(api_key="sk-test")
        adapter._client = mock_openai_client

        response = await adapter.complete(sample_inference_request, "gpt-4o")

        assert response is not None
        assert response.request_id == sample_inference_request.request_id
        assert response.model_id == "gpt-4o"
        assert response.provider == "openai"
        assert response.content is not None
        assert len(response.content) > 0
        assert response.is_success()

    async def test_complete_with_system_prompt(
        self, mock_openai_client, sample_inference_request
    ):
        """Test system prompt is properly included in messages"""
        adapter = OpenAIAdapter(api_key="sk-test")
        adapter._client = mock_openai_client

        await adapter.complete(sample_inference_request, "gpt-4o")

        # Check that the request was made with system message
        last_request = mock_openai_client.get_last_request()
        assert last_request is not None
        if last_request["json"]:
            messages = last_request["json"].get("messages", [])
            # Should have system message as first message
            has_system = any(m.get("role") == "system" for m in messages)
            assert has_system

    async def test_complete_returns_token_usage(
        self, mock_openai_client, sample_inference_request
    ):
        """Test token usage is returned in response"""
        adapter = OpenAIAdapter(api_key="sk-test")
        adapter._client = mock_openai_client

        response = await adapter.complete(sample_inference_request, "gpt-4o")

        assert response.token_usage is not None
        assert response.token_usage.input_tokens > 0
        assert response.token_usage.output_tokens > 0

    async def test_complete_returns_latency(
        self, mock_openai_client, sample_inference_request
    ):
        """Test latency is tracked and returned"""
        adapter = OpenAIAdapter(api_key="sk-test")
        adapter._client = mock_openai_client

        response = await adapter.complete(sample_inference_request, "gpt-4o")

        assert response.latency_ms >= 0

    async def test_complete_includes_finish_reason(
        self, mock_openai_client, sample_inference_request
    ):
        """Test finish reason is included in response"""
        adapter = OpenAIAdapter(api_key="sk-test")
        adapter._client = mock_openai_client

        response = await adapter.complete(sample_inference_request, "gpt-4o")

        assert response.finish_reason in ["stop", "length", "tool_calls", "content_filter"]


@pytest.mark.l04
@pytest.mark.unit
@pytest.mark.asyncio
class TestOpenAIAdapterErrors:
    """Tests for OpenAIAdapter error handling"""

    async def test_rate_limit_error_raises_E4402(
        self, mock_openai_client_429, sample_inference_request
    ):
        """Test 429 response raises E4402_PROVIDER_RATE_LIMIT"""
        adapter = OpenAIAdapter(api_key="sk-test")
        adapter._client = mock_openai_client_429

        with pytest.raises(ProviderError) as exc_info:
            await adapter.complete(sample_inference_request, "gpt-4o")

        assert exc_info.value.error_code == L04ErrorCode.E4402_PROVIDER_RATE_LIMIT

    async def test_auth_error_raises_E4203(
        self, mock_openai_client_401, sample_inference_request
    ):
        """Test 401 response raises E4203_PROVIDER_AUTH_FAILED"""
        adapter = OpenAIAdapter(api_key="invalid-key")
        adapter._client = mock_openai_client_401

        with pytest.raises(ProviderError) as exc_info:
            await adapter.complete(sample_inference_request, "gpt-4o")

        assert exc_info.value.error_code == L04ErrorCode.E4203_PROVIDER_AUTH_FAILED

    async def test_server_error_raises_E4200(
        self, mock_openai_client_500, sample_inference_request
    ):
        """Test 500 response raises E4200_PROVIDER_ERROR"""
        adapter = OpenAIAdapter(api_key="sk-test")
        adapter._client = mock_openai_client_500

        with pytest.raises(ProviderError) as exc_info:
            await adapter.complete(sample_inference_request, "gpt-4o")

        assert exc_info.value.error_code in [
            L04ErrorCode.E4200_PROVIDER_ERROR,
            L04ErrorCode.E4206_PROVIDER_API_ERROR,
        ]

    async def test_invalid_model_raises_E4207(self, sample_inference_request):
        """Test invalid model returns E4207_MODEL_NOT_SUPPORTED"""
        adapter = OpenAIAdapter(api_key="sk-test")

        # Create mock client returning 404 error
        mock_client = create_mock_openai_client(success=False, error_type="400")
        adapter._client = mock_client

        with pytest.raises(ProviderError) as exc_info:
            await adapter.complete(sample_inference_request, "gpt-5")

        assert exc_info.value.error_code in [
            L04ErrorCode.E4207_MODEL_NOT_SUPPORTED,
            L04ErrorCode.E4500_INVALID_REQUEST,
        ]

    async def test_timeout_error_raises_E4202(self, sample_inference_request):
        """Test timeout raises E4202_PROVIDER_TIMEOUT"""
        import httpx

        adapter = OpenAIAdapter(api_key="sk-test", timeout=1)

        mock_client = MagicMock()
        mock_client.post = AsyncMock(side_effect=httpx.TimeoutException("timeout"))
        adapter._client = mock_client

        with pytest.raises(ProviderError) as exc_info:
            await adapter.complete(sample_inference_request, "gpt-4o")

        assert exc_info.value.error_code == L04ErrorCode.E4202_PROVIDER_TIMEOUT


@pytest.mark.l04
@pytest.mark.unit
@pytest.mark.asyncio
class TestOpenAIAdapterStreaming:
    """Tests for OpenAIAdapter streaming"""

    async def test_stream_yields_deltas(
        self, mock_openai_client, sample_inference_request
    ):
        """Test streaming returns proper delta chunks"""
        adapter = OpenAIAdapter(api_key="sk-test")
        adapter._client = mock_openai_client

        chunks = []
        async for chunk in adapter.stream(sample_inference_request, "gpt-4o"):
            chunks.append(chunk)

        assert len(chunks) >= 1
        # Check that we got content
        content = "".join(c.content_delta for c in chunks)
        assert len(content) > 0

    async def test_stream_handles_done_signal(
        self, mock_openai_client, sample_inference_request
    ):
        """Test [DONE] signal terminates stream"""
        adapter = OpenAIAdapter(api_key="sk-test")
        adapter._client = mock_openai_client

        chunks = []
        async for chunk in adapter.stream(sample_inference_request, "gpt-4o"):
            chunks.append(chunk)

        # Last chunk should be final
        assert len(chunks) >= 1
        assert chunks[-1].is_final is True

    async def test_stream_has_finish_reason(
        self, mock_openai_client, sample_inference_request
    ):
        """Test streaming includes finish reason in final chunk"""
        adapter = OpenAIAdapter(api_key="sk-test")
        adapter._client = mock_openai_client

        chunks = []
        async for chunk in adapter.stream(sample_inference_request, "gpt-4o"):
            chunks.append(chunk)

        # Final chunk should have finish reason
        final_chunk = chunks[-1]
        assert final_chunk.is_final is True


@pytest.mark.l04
@pytest.mark.unit
@pytest.mark.asyncio
class TestOpenAIAdapterHealth:
    """Tests for OpenAIAdapter health check"""

    async def test_health_check_validates_api_key(self, mock_openai_client):
        """Test health check validates credentials"""
        adapter = OpenAIAdapter(api_key="sk-test")
        adapter._client = mock_openai_client

        health = await adapter.health_check()

        assert health.provider_id == "openai"
        assert health.status in [ProviderStatus.HEALTHY, ProviderStatus.DEGRADED]

    async def test_health_check_timeout_returns_unavailable(self):
        """Test health check timeout returns unavailable"""
        import httpx

        adapter = OpenAIAdapter(api_key="sk-test", timeout=1)

        mock_client = MagicMock()
        mock_client.get = AsyncMock(side_effect=httpx.TimeoutException("timeout"))
        adapter._client = mock_client

        health = await adapter.health_check()

        assert health.provider_id == "openai"
        assert health.status == ProviderStatus.UNAVAILABLE

    async def test_health_check_includes_metadata(self, mock_openai_client):
        """Test health check includes useful metadata"""
        adapter = OpenAIAdapter(api_key="sk-test")
        adapter._client = mock_openai_client

        health = await adapter.health_check()

        assert health.last_check is not None


@pytest.mark.l04
@pytest.mark.unit
class TestOpenAIAdapterRequestTransformation:
    """Tests for request transformation to OpenAI format"""

    def test_build_request_includes_model(self):
        """Test request includes model parameter"""
        adapter = OpenAIAdapter(api_key="sk-test")

        messages = [Message(role=MessageRole.USER, content="Hello")]
        request = InferenceRequest.create(
            agent_did="did:key:test",
            messages=messages,
        )

        openai_request = adapter._build_openai_request(request, "gpt-4o")

        assert openai_request["model"] == "gpt-4o"

    def test_build_request_includes_messages(self):
        """Test request includes messages in OpenAI format"""
        adapter = OpenAIAdapter(api_key="sk-test")

        messages = [
            Message(role=MessageRole.USER, content="Hello"),
            Message(role=MessageRole.ASSISTANT, content="Hi there!"),
            Message(role=MessageRole.USER, content="How are you?"),
        ]
        request = InferenceRequest.create(
            agent_did="did:key:test",
            messages=messages,
        )

        openai_request = adapter._build_openai_request(request, "gpt-4o")

        assert "messages" in openai_request
        assert len(openai_request["messages"]) == 3

    def test_build_request_includes_system_message(self):
        """Test request includes system message first"""
        adapter = OpenAIAdapter(api_key="sk-test")

        messages = [Message(role=MessageRole.USER, content="Hello")]
        request = InferenceRequest.create(
            agent_did="did:key:test",
            messages=messages,
            system_prompt="You are a helpful assistant.",
        )

        openai_request = adapter._build_openai_request(request, "gpt-4o")

        # OpenAI API uses system message in messages array
        msgs = openai_request["messages"]
        assert msgs[0]["role"] == "system"
        assert msgs[0]["content"] == "You are a helpful assistant."

    def test_build_request_includes_max_tokens(self):
        """Test request includes max_tokens"""
        adapter = OpenAIAdapter(api_key="sk-test")

        messages = [Message(role=MessageRole.USER, content="Hello")]
        request = InferenceRequest.create(
            agent_did="did:key:test",
            messages=messages,
            max_tokens=1000,
        )

        openai_request = adapter._build_openai_request(request, "gpt-4o")

        assert openai_request["max_tokens"] == 1000

    def test_build_request_includes_temperature(self):
        """Test request includes temperature"""
        adapter = OpenAIAdapter(api_key="sk-test")

        messages = [Message(role=MessageRole.USER, content="Hello")]
        request = InferenceRequest.create(
            agent_did="did:key:test",
            messages=messages,
            temperature=0.5,
        )

        openai_request = adapter._build_openai_request(request, "gpt-4o")

        assert openai_request.get("temperature") == 0.5
