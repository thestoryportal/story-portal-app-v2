"""
L04 Model Gateway Layer - Routing Configuration Models

Defines routing strategies and decisions.
"""

from dataclasses import dataclass, field
from typing import Optional, List
from enum import Enum


class RoutingStrategy(Enum):
    """Routing strategy for model selection"""
    CAPABILITY_FIRST = "capability_first"  # Filter by capabilities, then by cost
    COST_OPTIMIZED = "cost_optimized"  # Among capable models, select lowest cost
    LATENCY_OPTIMIZED = "latency_optimized"  # Among capable models, select lowest latency
    QUALITY_OPTIMIZED = "quality_optimized"  # Among capable models, select highest quality
    PROVIDER_PINNED = "provider_pinned"  # Route to specific provider regardless of cost
    ROUND_ROBIN = "round_robin"  # Distribute load evenly across capable models


class LatencyClass(Enum):
    """Latency classification for routing"""
    REALTIME = "realtime"  # p99 < 2000ms
    INTERACTIVE = "interactive"  # p99 < 5000ms
    BATCH = "batch"  # No latency constraint


@dataclass
class RoutingDecision:
    """
    Result of routing logic

    Contains the selected model and fallback options.
    """
    primary_model_id: str
    primary_provider: str
    fallback_models: List[str] = field(default_factory=list)
    routing_strategy: RoutingStrategy = RoutingStrategy.CAPABILITY_FIRST
    estimated_cost_cents: float = 0.0
    estimated_latency_ms: int = 0
    reason: str = ""
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization"""
        return {
            "primary_model_id": self.primary_model_id,
            "primary_provider": self.primary_provider,
            "fallback_models": self.fallback_models,
            "routing_strategy": self.routing_strategy.value,
            "estimated_cost_cents": self.estimated_cost_cents,
            "estimated_latency_ms": self.estimated_latency_ms,
            "reason": self.reason,
            "metadata": self.metadata
        }


@dataclass
class RoutingRules:
    """
    Routing rules for a specific context

    Can be used to define tenant-specific or agent-specific routing preferences.
    """
    default_strategy: RoutingStrategy = RoutingStrategy.CAPABILITY_FIRST
    preferred_providers: List[str] = field(default_factory=list)
    excluded_providers: List[str] = field(default_factory=list)
    max_cost_cents: Optional[int] = None
    max_latency_ms: Optional[int] = None
    required_capabilities: List[str] = field(default_factory=list)
    latency_class: LatencyClass = LatencyClass.INTERACTIVE
    prefer_provisioned_throughput: bool = True
    allowed_regions: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization"""
        return {
            "default_strategy": self.default_strategy.value,
            "preferred_providers": self.preferred_providers,
            "excluded_providers": self.excluded_providers,
            "max_cost_cents": self.max_cost_cents,
            "max_latency_ms": self.max_latency_ms,
            "required_capabilities": self.required_capabilities,
            "latency_class": self.latency_class.value,
            "prefer_provisioned_throughput": self.prefer_provisioned_throughput,
            "allowed_regions": self.allowed_regions
        }
