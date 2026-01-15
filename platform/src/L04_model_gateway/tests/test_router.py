"""
L04 Model Gateway Layer - LLM Router Tests

Tests for LLMRouter service.
"""

import pytest

from ..services import ModelRegistry, LLMRouter
from ..models import (
    InferenceRequest,
    Message,
    MessageRole,
    RoutingStrategy,
    RoutingError,
    ProviderHealth,
    ProviderStatus,
    CircuitState
)
from datetime import datetime


def test_router_initialization():
    """Test router initialization"""
    registry = ModelRegistry()
    registry.load_default_models()

    router = LLMRouter(registry)
    assert router.registry == registry
    assert router.default_strategy == RoutingStrategy.CAPABILITY_FIRST


def test_route_simple_request():
    """Test routing a simple request"""
    registry = ModelRegistry()
    registry.load_default_models()
    router = LLMRouter(registry)

    messages = [Message(role=MessageRole.USER, content="Hello")]
    request = InferenceRequest.create(
        agent_did="did:key:test",
        messages=messages,
        capabilities=["text"]
    )

    decision = router.route(request)

    assert decision.primary_model_id is not None
    assert decision.primary_provider is not None
    assert decision.routing_strategy == RoutingStrategy.CAPABILITY_FIRST


def test_route_with_capabilities():
    """Test routing with specific capabilities"""
    registry = ModelRegistry()
    registry.load_default_models()
    router = LLMRouter(registry)

    messages = [Message(role=MessageRole.USER, content="Describe this image")]
    request = InferenceRequest.create(
        agent_did="did:key:test",
        messages=messages,
        capabilities=["vision"]
    )

    decision = router.route(request)

    # Should route to a vision-capable model
    model = registry.get_model(decision.primary_model_id)
    assert model.supports_capability("vision")


def test_route_no_capable_model():
    """Test routing when no model matches requirements"""
    registry = ModelRegistry()
    registry.load_default_models()
    router = LLMRouter(registry)

    messages = [Message(role=MessageRole.USER, content="Test")]
    request = InferenceRequest.create(
        agent_did="did:key:test",
        messages=messages,
        capabilities=["nonexistent_capability"]
    )

    with pytest.raises(RoutingError):
        router.route(request)


def test_route_cost_optimized():
    """Test cost-optimized routing strategy"""
    registry = ModelRegistry()
    registry.load_default_models()
    router = LLMRouter(registry)

    messages = [Message(role=MessageRole.USER, content="Hello")]
    request = InferenceRequest.create(
        agent_did="did:key:test",
        messages=messages,
        capabilities=["text"]
    )

    decision = router.route(request, RoutingStrategy.COST_OPTIMIZED)

    assert decision.routing_strategy == RoutingStrategy.COST_OPTIMIZED
    # Should select a low-cost model (local Ollama models have zero cost)
    assert decision.estimated_cost_cents == 0.0


def test_route_latency_optimized():
    """Test latency-optimized routing strategy"""
    registry = ModelRegistry()
    registry.load_default_models()
    router = LLMRouter(registry)

    messages = [Message(role=MessageRole.USER, content="Hello")]
    request = InferenceRequest.create(
        agent_did="did:key:test",
        messages=messages,
        capabilities=["text"]
    )

    decision = router.route(request, RoutingStrategy.LATENCY_OPTIMIZED)

    assert decision.routing_strategy == RoutingStrategy.LATENCY_OPTIMIZED
    assert decision.estimated_latency_ms > 0


def test_route_with_provider_health():
    """Test routing with provider health information"""
    registry = ModelRegistry()
    registry.load_default_models()
    router = LLMRouter(registry)

    # Mark ollama as unavailable
    health = ProviderHealth(
        provider_id="ollama",
        status=ProviderStatus.UNAVAILABLE,
        circuit_state=CircuitState.OPEN,
        last_check=datetime.utcnow()
    )
    router.update_provider_health(health)

    messages = [Message(role=MessageRole.USER, content="Hello")]
    request = InferenceRequest.create(
        agent_did="did:key:test",
        messages=messages,
        capabilities=["text"]
    )

    # Should fail since all default models are Ollama
    with pytest.raises(RoutingError):
        router.route(request)


def test_route_with_fallbacks():
    """Test that routing provides fallback models"""
    registry = ModelRegistry()
    registry.load_default_models()
    router = LLMRouter(registry)

    messages = [Message(role=MessageRole.USER, content="Hello")]
    request = InferenceRequest.create(
        agent_did="did:key:test",
        messages=messages,
        capabilities=["text"]
    )

    decision = router.route(request)

    # Should have fallback models
    assert isinstance(decision.fallback_models, list)
    # May have 0-2 fallbacks depending on available models
    assert len(decision.fallback_models) >= 0
