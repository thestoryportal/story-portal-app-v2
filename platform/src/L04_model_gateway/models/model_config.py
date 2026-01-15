"""
L04 Model Gateway Layer - Model Configuration Models

Defines model definitions and capabilities.
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict
from datetime import datetime
from enum import Enum


class ModelStatus(Enum):
    """Status of a model in the registry"""
    ACTIVE = "active"
    DEPRECATED = "deprecated"
    DISABLED = "disabled"


class ModelCapability(Enum):
    """Standard capabilities that models can support"""
    TEXT = "text"
    VISION = "vision"
    TOOL_USE = "tool_use"
    STREAMING = "streaming"
    JSON_MODE = "json_mode"
    LONG_CONTEXT = "long_context"
    FUNCTION_CALLING = "function_calling"
    CODE_EXECUTION = "code_execution"


@dataclass
class ProvisionedThroughput:
    """Provisioned throughput configuration"""
    enabled: bool = False
    provisioned_units: Optional[int] = None  # PTUs for Azure, CUs for Bedrock
    unit_cost_per_hour: Optional[float] = None
    reserved_capacity_tpm: Optional[int] = None

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization"""
        return {
            "enabled": self.enabled,
            "provisioned_units": self.provisioned_units,
            "unit_cost_per_hour": self.unit_cost_per_hour,
            "reserved_capacity_tpm": self.reserved_capacity_tpm
        }


@dataclass
class QualityScores:
    """Quality scores for different task types"""
    reasoning: float = 0.0
    coding: float = 0.0
    creative: float = 0.0
    summarization: float = 0.0

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization"""
        return {
            "reasoning": self.reasoning,
            "coding": self.coding,
            "creative": self.creative,
            "summarization": self.summarization
        }


@dataclass
class ModelCapabilities:
    """Detailed model capabilities"""
    supports_vision: bool = False
    supports_tool_use: bool = False
    supports_streaming: bool = True
    supports_json_mode: bool = False
    supports_function_calling: bool = False
    supports_code_execution: bool = False
    capabilities_list: List[str] = field(default_factory=list)

    def __post_init__(self):
        """Populate capabilities list from boolean flags"""
        if not self.capabilities_list:
            self.capabilities_list = []
            self.capabilities_list.append("text")  # All models support text
            if self.supports_vision:
                self.capabilities_list.append("vision")
            if self.supports_tool_use or self.supports_function_calling:
                self.capabilities_list.append("tool_use")
                self.capabilities_list.append("function_calling")
            if self.supports_streaming:
                self.capabilities_list.append("streaming")
            if self.supports_json_mode:
                self.capabilities_list.append("json_mode")
            if self.supports_code_execution:
                self.capabilities_list.append("code_execution")

    def has_capability(self, capability: str) -> bool:
        """Check if model has a specific capability"""
        return capability.lower() in [c.lower() for c in self.capabilities_list]

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization"""
        return {
            "supports_vision": self.supports_vision,
            "supports_tool_use": self.supports_tool_use,
            "supports_streaming": self.supports_streaming,
            "supports_json_mode": self.supports_json_mode,
            "supports_function_calling": self.supports_function_calling,
            "supports_code_execution": self.supports_code_execution,
            "capabilities_list": self.capabilities_list
        }


@dataclass
class ModelConfig:
    """
    Model configuration and metadata

    This defines everything the gateway needs to know about a model.
    """
    model_id: str
    provider: str
    display_name: str
    capabilities: ModelCapabilities
    context_window: int
    max_output_tokens: int
    cost_per_1m_input_tokens: float
    cost_per_1m_output_tokens: float
    cost_per_1m_cached_input_tokens: float = 0.0
    rate_limit_rpm: int = 60
    rate_limit_tpm: int = 100000
    latency_p50_ms: int = 1000
    latency_p99_ms: int = 5000
    status: ModelStatus = ModelStatus.ACTIVE
    regions: List[str] = field(default_factory=list)
    provisioned_throughput: ProvisionedThroughput = field(default_factory=ProvisionedThroughput)
    quality_scores: QualityScores = field(default_factory=QualityScores)
    pricing_last_updated: Optional[datetime] = None
    metadata: Dict = field(default_factory=dict)

    def is_available(self) -> bool:
        """Check if model is available for use"""
        return self.status == ModelStatus.ACTIVE

    def supports_capability(self, capability: str) -> bool:
        """Check if model supports a specific capability"""
        return self.capabilities.has_capability(capability)

    def calculate_cost(self, input_tokens: int, output_tokens: int, cached_tokens: int = 0) -> float:
        """
        Calculate cost in cents for given token counts
        """
        input_cost = (input_tokens / 1_000_000) * self.cost_per_1m_input_tokens
        output_cost = (output_tokens / 1_000_000) * self.cost_per_1m_output_tokens
        cached_cost = (cached_tokens / 1_000_000) * self.cost_per_1m_cached_input_tokens
        return input_cost + output_cost + cached_cost

    def has_provisioned_throughput(self) -> bool:
        """Check if model has provisioned throughput"""
        return self.provisioned_throughput.enabled

    def get_effective_cost(self, input_tokens: int, output_tokens: int) -> float:
        """
        Get effective cost considering provisioned throughput.
        Provisioned capacity has zero marginal cost.
        """
        if self.has_provisioned_throughput():
            return 0.0
        return self.calculate_cost(input_tokens, output_tokens)

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization"""
        return {
            "model_id": self.model_id,
            "provider": self.provider,
            "display_name": self.display_name,
            "capabilities": self.capabilities.to_dict(),
            "context_window": self.context_window,
            "max_output_tokens": self.max_output_tokens,
            "cost_per_1m_input_tokens": self.cost_per_1m_input_tokens,
            "cost_per_1m_output_tokens": self.cost_per_1m_output_tokens,
            "cost_per_1m_cached_input_tokens": self.cost_per_1m_cached_input_tokens,
            "rate_limit_rpm": self.rate_limit_rpm,
            "rate_limit_tpm": self.rate_limit_tpm,
            "latency_p50_ms": self.latency_p50_ms,
            "latency_p99_ms": self.latency_p99_ms,
            "status": self.status.value,
            "regions": self.regions,
            "provisioned_throughput": self.provisioned_throughput.to_dict(),
            "quality_scores": self.quality_scores.to_dict(),
            "pricing_last_updated": self.pricing_last_updated.isoformat() if self.pricing_last_updated else None,
            "metadata": self.metadata
        }
