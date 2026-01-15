"""
L04 Model Gateway Layer - Model Tests

Tests for data models and error codes.
"""

import pytest
from datetime import datetime

from ..models import (
    # Error codes
    L04ErrorCode,
    L04Error,
    ConfigurationError,
    RoutingError,

    # Inference request
    Message,
    MessageRole,
    LogicalPrompt,
    ModelRequirements,
    RequestConstraints,
    InferenceRequest,

    # Inference response
    TokenUsage,
    InferenceResponse,
    ResponseStatus,
    StreamChunk,

    # Model config
    ModelCapabilities,
    ModelConfig,
    ModelStatus,

    # Provider config
    ProviderHealth,
    ProviderStatus,
    CircuitState,

    # Routing config
    RoutingStrategy,
    RoutingDecision
)


def test_error_codes():
    """Test error code definitions"""
    # Test configuration error
    error = L04ErrorCode.E4001_MODEL_NOT_FOUND
    assert error.code == "E4001"
    assert "not found" in error.message.lower()

    # Test routing error
    error = L04ErrorCode.E4101_NO_CAPABLE_MODEL
    assert error.code == "E4101"

    # Test provider error
    error = L04ErrorCode.E4200_PROVIDER_ERROR
    assert error.code == "E4200"


def test_l04_error():
    """Test L04Error exception"""
    error = ConfigurationError(
        L04ErrorCode.E4001_MODEL_NOT_FOUND,
        "Model xyz not found",
        {"model_id": "xyz"}
    )

    assert error.error_code == L04ErrorCode.E4001_MODEL_NOT_FOUND
    assert "xyz" in error.message
    assert error.details["model_id"] == "xyz"

    # Test serialization
    error_dict = error.to_dict()
    assert error_dict["error_code"] == "E4001"
    assert error_dict["message"] == "Model xyz not found"


def test_message_creation():
    """Test Message model"""
    msg = Message(
        role=MessageRole.USER,
        content="Hello, world!"
    )

    assert msg.role == MessageRole.USER
    assert msg.content == "Hello, world!"

    # Test serialization
    msg_dict = msg.to_dict()
    assert msg_dict["role"] == "user"
    assert msg_dict["content"] == "Hello, world!"


def test_logical_prompt():
    """Test LogicalPrompt model"""
    messages = [
        Message(role=MessageRole.USER, content="Hello")
    ]

    prompt = LogicalPrompt(
        messages=messages,
        system_prompt="You are helpful",
        temperature=0.7,
        max_tokens=100
    )

    assert len(prompt.messages) == 1
    assert prompt.system_prompt == "You are helpful"
    assert prompt.temperature == 0.7

    # Test token estimation
    tokens = prompt.estimate_tokens()
    assert tokens > 0


def test_inference_request():
    """Test InferenceRequest model"""
    messages = [
        Message(role=MessageRole.USER, content="Test message")
    ]

    request = InferenceRequest.create(
        agent_did="did:key:test123",
        messages=messages,
        system_prompt="Test system",
        capabilities=["text"]
    )

    assert request.agent_did == "did:key:test123"
    assert len(request.logical_prompt.messages) == 1
    assert "text" in request.requirements.capabilities

    # Test serialization
    request_dict = request.to_dict()
    assert request_dict["agent_did"] == "did:key:test123"


def test_token_usage():
    """Test TokenUsage model"""
    usage = TokenUsage(
        input_tokens=100,
        output_tokens=50,
        cached_tokens=10
    )

    assert usage.input_tokens == 100
    assert usage.output_tokens == 50
    assert usage.total_tokens == 150


def test_inference_response():
    """Test InferenceResponse model"""
    token_usage = TokenUsage(
        input_tokens=100,
        output_tokens=50
    )

    response = InferenceResponse(
        request_id="req123",
        model_id="llama3.1:8b",
        provider="ollama",
        content="Test response",
        token_usage=token_usage,
        latency_ms=500,
        cached=False
    )

    assert response.request_id == "req123"
    assert response.model_id == "llama3.1:8b"
    assert response.is_success()
    assert not response.has_tool_calls()

    # Test serialization
    response_dict = response.to_dict()
    assert response_dict["model_id"] == "llama3.1:8b"


def test_stream_chunk():
    """Test StreamChunk model"""
    chunk = StreamChunk(
        request_id="req123",
        content_delta="Hello ",
        is_final=False
    )

    assert chunk.content_delta == "Hello "
    assert not chunk.is_final


def test_model_capabilities():
    """Test ModelCapabilities"""
    caps = ModelCapabilities(
        supports_vision=True,
        supports_tool_use=True,
        supports_streaming=True
    )

    assert caps.has_capability("vision")
    assert caps.has_capability("tool_use")
    assert caps.has_capability("streaming")
    assert not caps.has_capability("nonexistent")


def test_model_config():
    """Test ModelConfig"""
    caps = ModelCapabilities(supports_streaming=True)

    model = ModelConfig(
        model_id="test-model",
        provider="test-provider",
        display_name="Test Model",
        capabilities=caps,
        context_window=8192,
        max_output_tokens=4096,
        cost_per_1m_input_tokens=1.0,
        cost_per_1m_output_tokens=2.0,
        status=ModelStatus.ACTIVE
    )

    assert model.model_id == "test-model"
    assert model.is_available()
    assert model.supports_capability("streaming")

    # Test cost calculation
    cost = model.calculate_cost(1000, 500)
    assert cost > 0


def test_provider_health():
    """Test ProviderHealth"""
    health = ProviderHealth(
        provider_id="ollama",
        status=ProviderStatus.HEALTHY,
        circuit_state=CircuitState.CLOSED,
        last_check=datetime.utcnow()
    )

    assert health.is_available()
    assert health.can_accept_request()


def test_routing_decision():
    """Test RoutingDecision"""
    decision = RoutingDecision(
        primary_model_id="llama3.1:8b",
        primary_provider="ollama",
        fallback_models=["llama3.2:3b"],
        routing_strategy=RoutingStrategy.COST_OPTIMIZED,
        estimated_cost_cents=0.5,
        estimated_latency_ms=500
    )

    assert decision.primary_model_id == "llama3.1:8b"
    assert len(decision.fallback_models) == 1
    assert decision.routing_strategy == RoutingStrategy.COST_OPTIMIZED
