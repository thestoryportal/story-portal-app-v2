"""
L04 Model Gateway Layer - Integration Test Fixtures

Fixtures for end-to-end integration testing.
"""

import pytest
import pytest_asyncio
import asyncio
from typing import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock

from L04_model_gateway.models import (
    InferenceRequest,
    InferenceResponse,
    Message,
    MessageRole,
    TokenUsage,
    ResponseStatus,
    ProviderHealth,
    ProviderStatus,
    CircuitState,
    StreamChunk,
    ModelConfig,
    ModelCapabilities,
    ModelStatus,
)
from L04_model_gateway.services import (
    ModelRegistry,
    LLMRouter,
    SemanticCache,
    RateLimiter,
    CircuitBreaker,
    RequestQueue,
    ModelGateway,
    L01Bridge,
)
from L04_model_gateway.providers import MockAdapter


@pytest.fixture
def mock_provider():
    """Create a mock provider adapter for testing."""
    adapter = MockAdapter(provider_id="mock", base_url="http://mock")
    return adapter


@pytest.fixture
def mock_l01_bridge():
    """Create a mock L01 bridge that doesn't make real HTTP calls."""
    bridge = L01Bridge(base_url="http://localhost:8001")
    bridge.enabled = False  # Disable actual HTTP calls
    return bridge


@pytest.fixture
def mock_model_config():
    """Create a mock model configuration."""
    return ModelConfig(
        model_id="mock",
        provider="mock",
        display_name="Mock Model",
        capabilities=ModelCapabilities(
            supports_streaming=True,
            supports_tool_use=True,
            supports_vision=False,
        ),
        context_window=8192,
        max_output_tokens=4096,
        cost_per_1m_input_tokens=0.0,
        cost_per_1m_output_tokens=0.0,
        status=ModelStatus.ACTIVE,
    )


@pytest.fixture
def model_registry(mock_model_config):
    """Create a model registry with mock model."""
    registry = ModelRegistry()
    registry.register_model(mock_model_config)
    return registry


@pytest.fixture
def llm_router(model_registry):
    """Create LLM router with model registry."""
    return LLMRouter(model_registry)


@pytest.fixture
def rate_limiter():
    """Create rate limiter for testing."""
    return RateLimiter(
        default_rpm=60,
        default_tpm=10000,
    )


@pytest.fixture
def circuit_breaker():
    """Create circuit breaker for testing."""
    return CircuitBreaker(
        failure_threshold=5,
        recovery_timeout=30.0,
    )


@pytest.fixture
def request_queue():
    """Create request queue for testing."""
    return RequestQueue(max_size=100)


@pytest_asyncio.fixture
async def model_gateway(
    model_registry,
    llm_router,
    rate_limiter,
    circuit_breaker,
    mock_l01_bridge,
    mock_provider,
):
    """Create fully configured model gateway for E2E testing."""
    # Create a cache with embeddings disabled for simpler testing
    cache = SemanticCache(
        ttl_seconds=60,
        similarity_threshold=0.95,
        enable_embeddings=False,  # Disable embeddings for testing
    )

    gateway = ModelGateway(
        registry=model_registry,
        router=llm_router,
        rate_limiter=rate_limiter,
        circuit_breaker=circuit_breaker,
        cache=cache,
        l01_bridge=mock_l01_bridge,
        providers={"mock": mock_provider},
    )
    yield gateway
    await gateway.close()


@pytest.fixture
def sample_inference_request():
    """Create a sample inference request for testing."""
    return InferenceRequest.create(
        agent_did="did:key:test-agent",
        messages=[
            Message(role=MessageRole.SYSTEM, content="You are a helpful assistant."),
            Message(role=MessageRole.USER, content="Hello, how are you?"),
        ],
        model_id="mock",
        max_tokens=100,
        temperature=0.7,
    )


@pytest.fixture
def sample_messages():
    """Create sample messages for testing."""
    return [
        Message(role=MessageRole.SYSTEM, content="You are a helpful assistant."),
        Message(role=MessageRole.USER, content="Hello!"),
    ]
