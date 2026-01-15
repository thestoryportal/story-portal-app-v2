"""
L04 Model Gateway Layer - Model Registry Tests

Tests for ModelRegistry service.
"""

import pytest

from ..services import ModelRegistry
from ..models import (
    ModelConfig,
    ModelCapabilities,
    ModelStatus,
    ConfigurationError
)


def test_registry_initialization():
    """Test registry initialization"""
    registry = ModelRegistry()

    assert not registry.is_initialized()
    assert len(registry.list_models()) == 0


def test_load_default_models():
    """Test loading default Ollama models"""
    registry = ModelRegistry()
    registry.load_default_models()

    assert registry.is_initialized()
    assert len(registry.list_models()) > 0

    # Check for default Ollama models
    llama31 = registry.get_model("llama3.1:8b")
    assert llama31 is not None
    assert llama31.provider == "ollama"
    assert llama31.is_available()


def test_register_model():
    """Test registering a model"""
    registry = ModelRegistry()

    caps = ModelCapabilities(supports_streaming=True)
    model = ModelConfig(
        model_id="test-model",
        provider="test-provider",
        display_name="Test Model",
        capabilities=caps,
        context_window=8192,
        max_output_tokens=4096,
        cost_per_1m_input_tokens=1.0,
        cost_per_1m_output_tokens=2.0
    )

    registry.register_model(model)

    retrieved = registry.get_model("test-model")
    assert retrieved is not None
    assert retrieved.model_id == "test-model"


def test_get_model_or_raise():
    """Test get_model_or_raise"""
    registry = ModelRegistry()
    registry.load_default_models()

    # Should succeed
    model = registry.get_model_or_raise("llama3.1:8b")
    assert model.model_id == "llama3.1:8b"

    # Should raise
    with pytest.raises(ConfigurationError):
        registry.get_model_or_raise("nonexistent-model")


def test_list_models_by_provider():
    """Test filtering models by provider"""
    registry = ModelRegistry()
    registry.load_default_models()

    ollama_models = registry.list_models(provider="ollama")
    assert len(ollama_models) > 0
    assert all(m.provider == "ollama" for m in ollama_models)


def test_get_models_by_capability():
    """Test filtering models by capability"""
    registry = ModelRegistry()
    registry.load_default_models()

    # Get models with streaming capability
    streaming_models = registry.get_models_by_capability("streaming")
    assert len(streaming_models) > 0
    assert all(m.supports_capability("streaming") for m in streaming_models)

    # Get models with vision capability
    vision_models = registry.get_models_by_capability("vision")
    # Should have llava model
    assert any("llava" in m.model_id for m in vision_models)


def test_get_models_by_capabilities():
    """Test filtering models by multiple capabilities"""
    registry = ModelRegistry()
    registry.load_default_models()

    # Get models with both text and streaming
    models = registry.get_models_by_capabilities(["text", "streaming"])
    assert len(models) > 0

    # Get models with vision (fewer models)
    vision_models = registry.get_models_by_capabilities(["vision"])
    assert len(vision_models) < len(models)


def test_update_model_status():
    """Test updating model status"""
    registry = ModelRegistry()
    registry.load_default_models()

    model_id = "llama3.1:8b"

    # Disable model
    registry.update_model_status(model_id, ModelStatus.DISABLED)
    model = registry.get_model(model_id)
    assert model.status == ModelStatus.DISABLED
    assert not model.is_available()

    # Re-enable model
    registry.update_model_status(model_id, ModelStatus.ACTIVE)
    model = registry.get_model(model_id)
    assert model.status == ModelStatus.ACTIVE
    assert model.is_available()


def test_get_providers():
    """Test getting list of providers"""
    registry = ModelRegistry()
    registry.load_default_models()

    providers = registry.get_providers()
    assert "ollama" in providers


def test_get_capabilities():
    """Test getting list of capabilities"""
    registry = ModelRegistry()
    registry.load_default_models()

    capabilities = registry.get_capabilities()
    assert "text" in capabilities
    assert "streaming" in capabilities


def test_get_stats():
    """Test registry statistics"""
    registry = ModelRegistry()
    registry.load_default_models()

    stats = registry.get_stats()
    assert stats["total_models"] > 0
    assert stats["active_models"] > 0
    assert "ollama" in stats["providers"]
    assert "text" in stats["capabilities"]
