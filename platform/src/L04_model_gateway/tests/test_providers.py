"""
L04 Model Gateway Layer - Provider Tests

Tests for provider adapters.
"""

import pytest

from ..providers import MockAdapter, OllamaAdapter
from ..models import (
    InferenceRequest,
    Message,
    MessageRole,
    ProviderStatus
)


@pytest.mark.asyncio
async def test_mock_adapter_complete():
    """Test MockAdapter completion"""
    adapter = MockAdapter()

    messages = [Message(role=MessageRole.USER, content="Test message")]
    request = InferenceRequest.create(
        agent_did="did:key:test",
        messages=messages
    )

    response = await adapter.complete(request, "mock-model")

    assert response.request_id == request.request_id
    assert response.model_id == "mock-model"
    assert response.provider == "mock"
    assert response.is_success()
    assert len(response.content) > 0


@pytest.mark.asyncio
async def test_mock_adapter_stream():
    """Test MockAdapter streaming"""
    adapter = MockAdapter()

    messages = [Message(role=MessageRole.USER, content="Test message")]
    request = InferenceRequest.create(
        agent_did="did:key:test",
        messages=messages
    )

    chunks = []
    async for chunk in adapter.stream(request, "mock-model"):
        chunks.append(chunk)

    assert len(chunks) > 0
    assert chunks[-1].is_final
    assert chunks[-1].finish_reason == "stop"


@pytest.mark.asyncio
async def test_mock_adapter_health():
    """Test MockAdapter health check"""
    adapter = MockAdapter()

    health = await adapter.health_check()

    assert health.provider_id == "mock"
    assert health.status == ProviderStatus.HEALTHY


@pytest.mark.asyncio
async def test_mock_adapter_failure():
    """Test MockAdapter configured to fail"""
    adapter = MockAdapter(should_fail=True)

    messages = [Message(role=MessageRole.USER, content="Test message")]
    request = InferenceRequest.create(
        agent_did="did:key:test",
        messages=messages
    )

    with pytest.raises(Exception):
        await adapter.complete(request, "mock-model")

    health = await adapter.health_check()
    assert health.status == ProviderStatus.UNAVAILABLE


def test_ollama_adapter_initialization():
    """Test OllamaAdapter initialization"""
    adapter = OllamaAdapter()

    assert adapter.provider_id == "ollama"
    assert adapter.base_url == "http://localhost:11434"
    assert adapter.supports_capability("text")
    assert adapter.supports_capability("streaming")
    assert adapter.supports_model("llama3.1:8b")


def test_mock_adapter_call_counting():
    """Test MockAdapter call counting"""
    adapter = MockAdapter()

    assert adapter.get_call_count() == 0

    # Reset should work
    adapter.reset()
    assert adapter.get_call_count() == 0
