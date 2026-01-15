"""
L04 Model Gateway Layer - Model Registry Service

Maintains catalog of available models with capabilities and costs.
"""

from typing import Dict, List, Optional, Set
import logging
from datetime import datetime

from ..models import (
    ModelConfig,
    ModelCapabilities,
    QualityScores,
    ProvisionedThroughput,
    ModelStatus,
    L04ErrorCode,
    ConfigurationError
)

logger = logging.getLogger(__name__)


class ModelRegistry:
    """
    Central registry of available models

    Maintains an authoritative catalog of models with their capabilities,
    costs, and operational limits.
    """

    def __init__(self):
        self._models: Dict[str, ModelConfig] = {}
        self._capability_index: Dict[str, Set[str]] = {}
        self._provider_index: Dict[str, Set[str]] = {}
        self._initialized = False
        logger.info("ModelRegistry initialized")

    def register_model(self, model: ModelConfig) -> None:
        """
        Register a model in the registry

        Args:
            model: ModelConfig instance to register

        Raises:
            ConfigurationError: If model configuration is invalid
        """
        try:
            # Validate model configuration
            self._validate_model_config(model)

            # Add to main registry
            self._models[model.model_id] = model

            # Update capability index
            for capability in model.capabilities.capabilities_list:
                if capability not in self._capability_index:
                    self._capability_index[capability] = set()
                self._capability_index[capability].add(model.model_id)

            # Update provider index
            if model.provider not in self._provider_index:
                self._provider_index[model.provider] = set()
            self._provider_index[model.provider].add(model.model_id)

            logger.info(
                f"Registered model: {model.model_id} "
                f"(provider={model.provider}, status={model.status.value})"
            )

        except Exception as e:
            logger.error(f"Failed to register model {model.model_id}: {e}")
            raise ConfigurationError(
                L04ErrorCode.E4003_INVALID_MODEL_CONFIG,
                f"Failed to register model {model.model_id}",
                {"error": str(e)}
            )

    def _validate_model_config(self, model: ModelConfig) -> None:
        """Validate model configuration"""
        if not model.model_id:
            raise ValueError("model_id is required")
        if not model.provider:
            raise ValueError("provider is required")
        if model.context_window <= 0:
            raise ValueError("context_window must be positive")
        if model.max_output_tokens <= 0:
            raise ValueError("max_output_tokens must be positive")

    def get_model(self, model_id: str) -> Optional[ModelConfig]:
        """
        Get a model by ID

        Args:
            model_id: Model identifier

        Returns:
            ModelConfig if found, None otherwise
        """
        return self._models.get(model_id)

    def get_model_or_raise(self, model_id: str) -> ModelConfig:
        """
        Get a model by ID or raise error

        Args:
            model_id: Model identifier

        Returns:
            ModelConfig

        Raises:
            ConfigurationError: If model not found
        """
        model = self.get_model(model_id)
        if model is None:
            raise ConfigurationError(
                L04ErrorCode.E4001_MODEL_NOT_FOUND,
                f"Model not found: {model_id}"
            )
        return model

    async def list_models(
        self,
        provider: Optional[str] = None,
        status: Optional[ModelStatus] = None
    ) -> List[ModelConfig]:
        """
        List models with optional filtering

        Args:
            provider: Filter by provider
            status: Filter by status

        Returns:
            List of ModelConfig objects
        """
        models = list(self._models.values())

        if provider:
            models = [m for m in models if m.provider == provider]

        if status:
            models = [m for m in models if m.status == status]

        return models

    def get_models_by_capability(self, capability: str) -> List[ModelConfig]:
        """
        Get all models that support a specific capability

        Args:
            capability: Capability to filter by (e.g., "vision", "tool_use")

        Returns:
            List of ModelConfig objects
        """
        model_ids = self._capability_index.get(capability.lower(), set())
        return [self._models[mid] for mid in model_ids if mid in self._models]

    def get_models_by_capabilities(self, capabilities: List[str]) -> List[ModelConfig]:
        """
        Get all models that support ALL specified capabilities

        Args:
            capabilities: List of required capabilities

        Returns:
            List of ModelConfig objects that support all capabilities
        """
        if not capabilities:
            return self.list_models(status=ModelStatus.ACTIVE)

        # Start with models supporting the first capability
        result_ids = self._capability_index.get(capabilities[0].lower(), set()).copy()

        # Intersect with models supporting each additional capability
        for capability in capabilities[1:]:
            capability_models = self._capability_index.get(capability.lower(), set())
            result_ids &= capability_models

        return [self._models[mid] for mid in result_ids if mid in self._models]

    def get_models_by_provider(self, provider: str) -> List[ModelConfig]:
        """
        Get all models from a specific provider

        Args:
            provider: Provider identifier

        Returns:
            List of ModelConfig objects
        """
        model_ids = self._provider_index.get(provider, set())
        return [self._models[mid] for mid in model_ids if mid in self._models]

    def get_available_models(self) -> List[ModelConfig]:
        """
        Get all available (active) models

        Returns:
            List of active ModelConfig objects
        """
        return [m for m in self._models.values() if m.is_available()]

    def get_providers(self) -> List[str]:
        """
        Get list of all registered providers

        Returns:
            List of provider identifiers
        """
        return list(self._provider_index.keys())

    def get_capabilities(self) -> List[str]:
        """
        Get list of all available capabilities

        Returns:
            List of capability names
        """
        return list(self._capability_index.keys())

    def update_model_status(self, model_id: str, status: ModelStatus) -> None:
        """
        Update the status of a model

        Args:
            model_id: Model identifier
            status: New status

        Raises:
            ConfigurationError: If model not found
        """
        model = self.get_model_or_raise(model_id)
        old_status = model.status
        model.status = status
        logger.info(
            f"Updated model {model_id} status: {old_status.value} -> {status.value}"
        )

    def load_default_models(self) -> None:
        """
        Load default model configurations for local development

        Includes Ollama models that are commonly available.
        """
        # Ollama llama3.1:8b
        llama31_8b = ModelConfig(
            model_id="llama3.1:8b",
            provider="ollama",
            display_name="Llama 3.1 8B",
            capabilities=ModelCapabilities(
                supports_streaming=True,
                supports_tool_use=False,
                supports_json_mode=True
            ),
            context_window=128000,
            max_output_tokens=8192,
            cost_per_1m_input_tokens=0.0,  # Local model, no cost
            cost_per_1m_output_tokens=0.0,
            rate_limit_rpm=1000,
            rate_limit_tpm=100000,
            latency_p50_ms=500,
            latency_p99_ms=2000,
            status=ModelStatus.ACTIVE,
            quality_scores=QualityScores(
                reasoning=0.75,
                coding=0.70,
                creative=0.80,
                summarization=0.78
            )
        )

        # Ollama llama3.2:3b
        llama32_3b = ModelConfig(
            model_id="llama3.2:3b",
            provider="ollama",
            display_name="Llama 3.2 3B",
            capabilities=ModelCapabilities(
                supports_streaming=True,
                supports_tool_use=False,
                supports_json_mode=True
            ),
            context_window=128000,
            max_output_tokens=8192,
            cost_per_1m_input_tokens=0.0,
            cost_per_1m_output_tokens=0.0,
            rate_limit_rpm=1000,
            rate_limit_tpm=100000,
            latency_p50_ms=300,
            latency_p99_ms=1000,
            status=ModelStatus.ACTIVE,
            quality_scores=QualityScores(
                reasoning=0.65,
                coding=0.60,
                creative=0.70,
                summarization=0.68
            )
        )

        # Ollama llava-llama3 (vision model)
        llava = ModelConfig(
            model_id="llava-llama3:latest",
            provider="ollama",
            display_name="LLaVA Llama 3",
            capabilities=ModelCapabilities(
                supports_streaming=True,
                supports_vision=True,
                supports_tool_use=False
            ),
            context_window=8192,
            max_output_tokens=4096,
            cost_per_1m_input_tokens=0.0,
            cost_per_1m_output_tokens=0.0,
            rate_limit_rpm=1000,
            rate_limit_tpm=50000,
            latency_p50_ms=800,
            latency_p99_ms=3000,
            status=ModelStatus.ACTIVE,
            quality_scores=QualityScores(
                reasoning=0.60,
                coding=0.50,
                creative=0.65,
                summarization=0.62
            )
        )

        # Register all default models
        for model in [llama31_8b, llama32_3b, llava]:
            self.register_model(model)

        self._initialized = True
        logger.info(f"Loaded {len(self._models)} default models")

    def is_initialized(self) -> bool:
        """Check if registry has been initialized with models"""
        return self._initialized

    def get_stats(self) -> dict:
        """
        Get registry statistics

        Returns:
            Dictionary with registry statistics
        """
        return {
            "total_models": len(self._models),
            "active_models": len([m for m in self._models.values() if m.status == ModelStatus.ACTIVE]),
            "total_providers": len(self._provider_index),
            "total_capabilities": len(self._capability_index),
            "providers": list(self._provider_index.keys()),
            "capabilities": list(self._capability_index.keys())
        }
