"""
L04 Model Gateway Layer - LLM Router Service

Intelligent model selection based on requirements, cost, and availability.
"""

from typing import List, Optional, Dict
import logging

from ..models import (
    InferenceRequest,
    ModelConfig,
    RoutingDecision,
    RoutingStrategy,
    LatencyClass,
    ProviderHealth,
    CircuitState,
    L04ErrorCode,
    RoutingError
)
from .model_registry import ModelRegistry

logger = logging.getLogger(__name__)


class LLMRouter:
    """
    Intelligent LLM router

    Selects optimal model based on:
    - Required capabilities
    - Cost constraints
    - Latency requirements
    - Provider health
    - Data residency
    """

    def __init__(
        self,
        registry: ModelRegistry,
        default_strategy: RoutingStrategy = RoutingStrategy.CAPABILITY_FIRST
    ):
        """
        Initialize router

        Args:
            registry: ModelRegistry instance
            default_strategy: Default routing strategy
        """
        self.registry = registry
        self.default_strategy = default_strategy
        self.provider_health: Dict[str, ProviderHealth] = {}
        logger.info(f"LLMRouter initialized with strategy: {default_strategy.value}")

    def update_provider_health(self, health: ProviderHealth) -> None:
        """
        Update provider health status

        Args:
            health: ProviderHealth object
        """
        self.provider_health[health.provider_id] = health
        logger.debug(
            f"Updated health for {health.provider_id}: "
            f"{health.status.value}, circuit={health.circuit_state.value}"
        )

    def route(
        self,
        request: InferenceRequest,
        strategy: Optional[RoutingStrategy] = None
    ) -> RoutingDecision:
        """
        Route request to appropriate model

        Args:
            request: InferenceRequest with requirements
            strategy: Optional override for routing strategy

        Returns:
            RoutingDecision with selected model and fallbacks

        Raises:
            RoutingError: If no suitable model found
        """
        strategy = strategy or self.default_strategy

        logger.info(
            f"Routing request {request.request_id} with strategy {strategy.value}"
        )

        try:
            # Step 1: Filter by capabilities
            candidates = self._filter_by_capabilities(request)
            if not candidates:
                raise RoutingError(
                    L04ErrorCode.E4101_NO_CAPABLE_MODEL,
                    "No models match required capabilities",
                    {"required": request.requirements.capabilities}
                )

            # Step 2: Filter by context length
            candidates = self._filter_by_context_length(request, candidates)
            if not candidates:
                raise RoutingError(
                    L04ErrorCode.E4104_CONTEXT_LENGTH_EXCEEDED,
                    "Prompt exceeds all model context lengths",
                    {"estimated_tokens": request.estimate_input_tokens()}
                )

            # Step 3: Filter by data residency
            candidates = self._filter_by_data_residency(request, candidates)
            if not candidates:
                raise RoutingError(
                    L04ErrorCode.E4107_DATA_RESIDENCY_VIOLATION,
                    "No models available in required regions",
                    {"allowed_regions": request.constraints.allowed_regions}
                )

            # Step 4: Filter by provider health
            candidates = self._filter_by_health(candidates)
            if not candidates:
                raise RoutingError(
                    L04ErrorCode.E4102_ALL_MODELS_UNAVAILABLE,
                    "All candidate models unavailable",
                    {}
                )

            # Step 5: Filter by latency class
            candidates = self._filter_by_latency(request, candidates)

            # Step 6: Apply routing strategy
            ranked = self._apply_strategy(request, candidates, strategy)

            if not ranked:
                raise RoutingError(
                    L04ErrorCode.E4100_ROUTING_FAILED,
                    "No models after applying routing strategy",
                    {}
                )

            # Select primary and fallbacks
            primary = ranked[0]
            fallbacks = [m.model_id for m in ranked[1:3]]  # Up to 2 fallbacks

            # Calculate estimated cost and latency
            estimated_tokens = request.estimate_input_tokens()
            estimated_cost = primary.calculate_cost(
                estimated_tokens,
                request.requirements.max_output_tokens
            )

            decision = RoutingDecision(
                primary_model_id=primary.model_id,
                primary_provider=primary.provider,
                fallback_models=fallbacks,
                routing_strategy=strategy,
                estimated_cost_cents=estimated_cost,
                estimated_latency_ms=primary.latency_p50_ms,
                reason=self._generate_reason(primary, strategy),
                metadata={
                    "candidates_count": len(candidates),
                    "estimated_input_tokens": estimated_tokens
                }
            )

            logger.info(
                f"Routed to {decision.primary_model_id} "
                f"(cost=${estimated_cost:.4f}, latency={decision.estimated_latency_ms}ms)"
            )

            return decision

        except RoutingError:
            raise
        except Exception as e:
            logger.error(f"Routing failed: {e}")
            raise RoutingError(
                L04ErrorCode.E4100_ROUTING_FAILED,
                f"Routing failed: {str(e)}",
                {"error": str(e)}
            )

    def _filter_by_capabilities(
        self,
        request: InferenceRequest
    ) -> List[ModelConfig]:
        """Filter models by required capabilities"""
        required = request.requirements.capabilities
        if not required:
            # No specific capabilities required, return all active models
            return self.registry.get_available_models()

        # Get models supporting all required capabilities
        candidates = self.registry.get_models_by_capabilities(required)

        # Filter to only active models
        candidates = [m for m in candidates if m.is_available()]

        logger.debug(
            f"Capability filter: {len(candidates)} models support {required}"
        )
        return candidates

    def _filter_by_context_length(
        self,
        request: InferenceRequest,
        candidates: List[ModelConfig]
    ) -> List[ModelConfig]:
        """Filter models by context window size"""
        estimated_tokens = request.estimate_input_tokens()
        required_context = max(
            estimated_tokens + request.requirements.max_output_tokens,
            request.requirements.min_context_length
        )

        filtered = [
            m for m in candidates
            if m.context_window >= required_context
        ]

        logger.debug(
            f"Context filter: {len(filtered)} models have >= {required_context} context"
        )
        return filtered

    def _filter_by_data_residency(
        self,
        request: InferenceRequest,
        candidates: List[ModelConfig]
    ) -> List[ModelConfig]:
        """Filter models by data residency requirements"""
        allowed_regions = request.constraints.allowed_regions
        if not allowed_regions:
            return candidates

        filtered = [
            m for m in candidates
            if not m.regions or any(r in m.regions for r in allowed_regions)
        ]

        logger.debug(
            f"Residency filter: {len(filtered)} models in regions {allowed_regions}"
        )
        return filtered

    def _filter_by_health(
        self,
        candidates: List[ModelConfig]
    ) -> List[ModelConfig]:
        """Filter out models from unhealthy providers"""
        filtered = []
        for model in candidates:
            health = self.provider_health.get(model.provider)

            if health is None:
                # No health info, assume healthy
                filtered.append(model)
                continue

            if health.circuit_state == CircuitState.OPEN:
                # Circuit breaker open, skip this provider
                logger.debug(
                    f"Skipping {model.model_id}: provider {model.provider} circuit open"
                )
                continue

            if health.can_accept_request():
                filtered.append(model)

        logger.debug(f"Health filter: {len(filtered)} models from healthy providers")
        return filtered

    def _filter_by_latency(
        self,
        request: InferenceRequest,
        candidates: List[ModelConfig]
    ) -> List[ModelConfig]:
        """Filter models by latency requirements"""
        max_latency = request.constraints.max_latency_ms

        filtered = [
            m for m in candidates
            if m.latency_p99_ms <= max_latency
        ]

        logger.debug(
            f"Latency filter: {len(filtered)} models with p99 <= {max_latency}ms"
        )
        return filtered if filtered else candidates  # Don't eliminate all candidates

    def _apply_strategy(
        self,
        request: InferenceRequest,
        candidates: List[ModelConfig],
        strategy: RoutingStrategy
    ) -> List[ModelConfig]:
        """Apply routing strategy to rank candidates"""

        if strategy == RoutingStrategy.COST_OPTIMIZED:
            return self._rank_by_cost(request, candidates)

        elif strategy == RoutingStrategy.LATENCY_OPTIMIZED:
            return self._rank_by_latency(candidates)

        elif strategy == RoutingStrategy.QUALITY_OPTIMIZED:
            return self._rank_by_quality(request, candidates)

        elif strategy == RoutingStrategy.PROVIDER_PINNED:
            return self._filter_by_preferred_providers(request, candidates)

        else:  # CAPABILITY_FIRST (default)
            return self._rank_by_cost(request, candidates)

    def _rank_by_cost(
        self,
        request: InferenceRequest,
        candidates: List[ModelConfig]
    ) -> List[ModelConfig]:
        """Rank models by cost (lowest first)"""
        estimated_input = request.estimate_input_tokens()
        estimated_output = request.requirements.max_output_tokens

        def cost_key(model: ModelConfig) -> float:
            # Prefer provisioned throughput (zero marginal cost)
            if model.has_provisioned_throughput():
                return 0.0
            return model.calculate_cost(estimated_input, estimated_output)

        return sorted(candidates, key=cost_key)

    def _rank_by_latency(
        self,
        candidates: List[ModelConfig]
    ) -> List[ModelConfig]:
        """Rank models by latency (fastest first)"""
        return sorted(candidates, key=lambda m: m.latency_p50_ms)

    def _rank_by_quality(
        self,
        request: InferenceRequest,
        candidates: List[ModelConfig]
    ) -> List[ModelConfig]:
        """Rank models by quality score"""
        quality_type = request.requirements.preferred_quality or "reasoning"

        def quality_key(model: ModelConfig) -> float:
            if quality_type == "reasoning":
                return -model.quality_scores.reasoning
            elif quality_type == "coding":
                return -model.quality_scores.coding
            elif quality_type == "creative":
                return -model.quality_scores.creative
            elif quality_type == "summarization":
                return -model.quality_scores.summarization
            else:
                return 0.0

        return sorted(candidates, key=quality_key)

    def _filter_by_preferred_providers(
        self,
        request: InferenceRequest,
        candidates: List[ModelConfig]
    ) -> List[ModelConfig]:
        """Filter to preferred providers if specified"""
        preferred = request.constraints.preferred_providers
        if not preferred:
            return candidates

        filtered = [m for m in candidates if m.provider in preferred]
        return filtered if filtered else candidates

    def _generate_reason(
        self,
        model: ModelConfig,
        strategy: RoutingStrategy
    ) -> str:
        """Generate human-readable routing reason"""
        reasons = []
        reasons.append(f"Selected {model.display_name} ({model.model_id})")
        reasons.append(f"from {model.provider}")
        reasons.append(f"using {strategy.value} strategy")

        if model.has_provisioned_throughput():
            reasons.append("(provisioned throughput available)")

        return " ".join(reasons)
