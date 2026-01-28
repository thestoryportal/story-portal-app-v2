"""
L04 Model Gateway Layer - Models HTTP API Routes

Provides HTTP endpoints for model listing and discovery.
Used by L02 Runtime for dynamic model selection.
"""

import logging
from typing import List, Optional

from fastapi import APIRouter, Request
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["models"])


# ============================================================================
# Response DTOs
# ============================================================================

class ModelCapabilitiesDTO(BaseModel):
    """Model capabilities"""
    capabilities: List[str] = Field(
        default_factory=list,
        description="List of capability names"
    )
    context_window: int = Field(128000, description="Context window size in tokens")
    max_output_tokens: int = Field(4096, description="Maximum output tokens")
    supports_vision: bool = Field(False, description="Supports image input")
    supports_tool_use: bool = Field(False, description="Supports tool calling")
    supports_streaming: bool = Field(True, description="Supports streaming output")

    model_config = {"extra": "ignore"}


class ModelInfoDTO(BaseModel):
    """Model information for listing"""
    model_id: str = Field(..., description="Unique model identifier")
    provider: str = Field(..., description="Provider name (e.g., claude_code, ollama)")
    display_name: str = Field(..., description="Human-readable display name")
    status: str = Field("active", description="Model status")
    capabilities: ModelCapabilitiesDTO = Field(
        default_factory=ModelCapabilitiesDTO,
        description="Model capabilities"
    )

    model_config = {"extra": "ignore"}


class ModelsListResponseDTO(BaseModel):
    """Response for model listing"""
    models: List[ModelInfoDTO] = Field(..., description="Available models")
    count: int = Field(..., description="Number of models")

    model_config = {"extra": "ignore"}


# ============================================================================
# Endpoints
# ============================================================================

@router.get(
    "/models",
    response_model=ModelsListResponseDTO,
    responses={
        503: {"description": "Service unavailable"}
    }
)
async def list_models(request: Request) -> ModelsListResponseDTO:
    """
    List all available models.

    Returns a list of models with their capabilities and status.
    Used by L02 Runtime for dynamic model discovery.
    """
    gateway = getattr(request.app.state, "model_gateway", None)

    models = []

    # Get models from gateway registry if available
    if gateway and hasattr(gateway, "registry"):
        try:
            registry_models = await gateway.registry.list_models()
            for model in registry_models:
                caps = model.capabilities
                models.append(ModelInfoDTO(
                    model_id=model.model_id,
                    provider=model.provider,
                    display_name=model.display_name,
                    status=model.status.value if hasattr(model.status, "value") else str(model.status),
                    capabilities=ModelCapabilitiesDTO(
                        capabilities=caps.capabilities_list if hasattr(caps, "capabilities_list") else [],
                        context_window=caps.context_window if hasattr(caps, "context_window") else 128000,
                        max_output_tokens=caps.max_output_tokens if hasattr(caps, "max_output_tokens") else 4096,
                        supports_vision=caps.supports_vision if hasattr(caps, "supports_vision") else False,
                        supports_tool_use=caps.supports_tool_use if hasattr(caps, "supports_tool_use") else False,
                        supports_streaming=caps.supports_streaming if hasattr(caps, "supports_streaming") else True,
                    )
                ))
        except Exception as e:
            logger.warning(f"Failed to get models from registry: {e}")

    # Add fallback models from providers if registry is empty
    if not models and gateway and hasattr(gateway, "providers"):
        # Claude Code provider
        if "claude_code" in gateway.providers:
            models.extend([
                ModelInfoDTO(
                    model_id="claude-opus-4-5-20251101",
                    provider="claude_code",
                    display_name="Claude Opus 4.5",
                    status="active",
                    capabilities=ModelCapabilitiesDTO(
                        capabilities=["text", "code_generation", "reasoning", "tool_use", "vision"],
                        context_window=200000,
                        max_output_tokens=8192,
                        supports_vision=True,
                        supports_tool_use=True,
                        supports_streaming=True,
                    )
                ),
                ModelInfoDTO(
                    model_id="claude-sonnet-4-20250514",
                    provider="claude_code",
                    display_name="Claude Sonnet 4",
                    status="active",
                    capabilities=ModelCapabilitiesDTO(
                        capabilities=["text", "code_generation", "reasoning", "tool_use", "vision"],
                        context_window=200000,
                        max_output_tokens=8192,
                        supports_vision=True,
                        supports_tool_use=True,
                        supports_streaming=True,
                    )
                ),
            ])

        # Ollama provider
        if "ollama" in gateway.providers:
            models.append(ModelInfoDTO(
                model_id="llama3.2",
                provider="ollama",
                display_name="Llama 3.2",
                status="active",
                capabilities=ModelCapabilitiesDTO(
                    capabilities=["text", "code_generation"],
                    context_window=128000,
                    max_output_tokens=4096,
                    supports_vision=False,
                    supports_tool_use=False,
                    supports_streaming=True,
                )
            ))

        # Mock provider
        if "mock" in gateway.providers:
            models.append(ModelInfoDTO(
                model_id="mock-model",
                provider="mock",
                display_name="Mock Model (Testing)",
                status="active",
                capabilities=ModelCapabilitiesDTO(
                    capabilities=["text"],
                    context_window=16000,
                    max_output_tokens=2048,
                    supports_vision=False,
                    supports_tool_use=False,
                    supports_streaming=False,
                )
            ))

    # Fallback if no gateway
    if not models:
        models = [
            ModelInfoDTO(
                model_id="claude-opus-4-5-20251101",
                provider="claude_code",
                display_name="Claude Opus 4.5",
                status="active",
                capabilities=ModelCapabilitiesDTO(
                    capabilities=["text", "code_generation", "reasoning", "tool_use", "vision"],
                    context_window=200000,
                    max_output_tokens=8192,
                    supports_vision=True,
                    supports_tool_use=True,
                    supports_streaming=True,
                )
            ),
        ]

    return ModelsListResponseDTO(
        models=models,
        count=len(models)
    )


@router.get(
    "/models/{model_id}",
    response_model=ModelInfoDTO,
    responses={
        404: {"description": "Model not found"},
        503: {"description": "Service unavailable"}
    }
)
async def get_model(model_id: str, request: Request) -> ModelInfoDTO:
    """
    Get details for a specific model.

    Returns model information including capabilities and status.
    """
    gateway = getattr(request.app.state, "model_gateway", None)

    # Try to get from registry
    if gateway and hasattr(gateway, "registry"):
        try:
            model = gateway.registry.get_model(model_id)
            if model:
                caps = model.capabilities
                return ModelInfoDTO(
                    model_id=model.model_id,
                    provider=model.provider,
                    display_name=model.display_name,
                    status=model.status.value if hasattr(model.status, "value") else str(model.status),
                    capabilities=ModelCapabilitiesDTO(
                        capabilities=caps.capabilities_list if hasattr(caps, "capabilities_list") else [],
                        context_window=caps.context_window if hasattr(caps, "context_window") else 128000,
                        max_output_tokens=caps.max_output_tokens if hasattr(caps, "max_output_tokens") else 4096,
                        supports_vision=caps.supports_vision if hasattr(caps, "supports_vision") else False,
                        supports_tool_use=caps.supports_tool_use if hasattr(caps, "supports_tool_use") else False,
                        supports_streaming=caps.supports_streaming if hasattr(caps, "supports_streaming") else True,
                    )
                )
        except Exception as e:
            logger.warning(f"Failed to get model {model_id} from registry: {e}")

    # Fallback for known models
    known_models = {
        "claude-opus-4-5-20251101": ModelInfoDTO(
            model_id="claude-opus-4-5-20251101",
            provider="claude_code",
            display_name="Claude Opus 4.5",
            status="active",
            capabilities=ModelCapabilitiesDTO(
                capabilities=["text", "code_generation", "reasoning", "tool_use", "vision"],
                context_window=200000,
                max_output_tokens=8192,
                supports_vision=True,
                supports_tool_use=True,
                supports_streaming=True,
            )
        ),
        "claude-sonnet-4-20250514": ModelInfoDTO(
            model_id="claude-sonnet-4-20250514",
            provider="claude_code",
            display_name="Claude Sonnet 4",
            status="active",
            capabilities=ModelCapabilitiesDTO(
                capabilities=["text", "code_generation", "reasoning", "tool_use", "vision"],
                context_window=200000,
                max_output_tokens=8192,
                supports_vision=True,
                supports_tool_use=True,
                supports_streaming=True,
            )
        ),
    }

    if model_id in known_models:
        return known_models[model_id]

    from fastapi import HTTPException
    raise HTTPException(status_code=404, detail=f"Model {model_id} not found")
