"""
L04 Model Gateway Layer - Model Gateway Service

Main gateway service that coordinates all components.
"""

import logging
from typing import Optional, Dict, AsyncIterator
from datetime import datetime

from ..models import (
    InferenceRequest,
    InferenceResponse,
    StreamChunk,
    RoutingStrategy,
    L04Error,
    L04ErrorCode,
    ProviderError,
    RateLimitError,
    RoutingError
)
from ..providers import ProviderAdapter, OllamaAdapter, MockAdapter
from .model_registry import ModelRegistry
from .llm_router import LLMRouter
from .semantic_cache import SemanticCache
from .rate_limiter import RateLimiter
from .circuit_breaker import CircuitBreaker
from .request_queue import RequestQueue, Priority

logger = logging.getLogger(__name__)


class ModelGateway:
    """
    Main Model Gateway service

    Coordinates all L04 components to provide intelligent LLM inference
    with caching, rate limiting, routing, and failover.
    """

    def __init__(
        self,
        registry: Optional[ModelRegistry] = None,
        router: Optional[LLMRouter] = None,
        cache: Optional[SemanticCache] = None,
        rate_limiter: Optional[RateLimiter] = None,
        circuit_breaker: Optional[CircuitBreaker] = None,
        request_queue: Optional[RequestQueue] = None,
        providers: Optional[Dict[str, ProviderAdapter]] = None,
        l01_bridge = None
    ):
        """
        Initialize Model Gateway

        Args:
            registry: ModelRegistry instance (creates default if None)
            router: LLMRouter instance (creates default if None)
            cache: SemanticCache instance (creates default if None)
            rate_limiter: RateLimiter instance (creates default if None)
            circuit_breaker: CircuitBreaker instance (creates default if None)
            request_queue: RequestQueue instance (creates default if None)
            providers: Dictionary of provider adapters (creates defaults if None)
            l01_bridge: Optional L04Bridge instance for L01 integration
        """
        # Initialize registry
        self.registry = registry or ModelRegistry()
        if not self.registry.is_initialized():
            self.registry.load_default_models()

        # Initialize components
        self.router = router or LLMRouter(self.registry)
        self.cache = cache or SemanticCache()
        self.rate_limiter = rate_limiter or RateLimiter()
        self.circuit_breaker = circuit_breaker or CircuitBreaker()
        self.request_queue = request_queue or RequestQueue()

        # Initialize L01 bridge (optional)
        self.l01_bridge = l01_bridge

        # Initialize providers
        self.providers = providers or {}
        if not self.providers:
            self._setup_default_providers()

        logger.info("ModelGateway initialized with all components")

    def _setup_default_providers(self) -> None:
        """Setup default provider adapters"""
        # Ollama (primary for local dev)
        self.providers["ollama"] = OllamaAdapter()

        # Mock provider (for testing)
        self.providers["mock"] = MockAdapter()

        logger.info(f"Initialized {len(self.providers)} provider adapters")

    async def execute(
        self,
        request: InferenceRequest,
        routing_strategy: Optional[RoutingStrategy] = None
    ) -> InferenceResponse:
        """
        Execute inference request

        Full request pipeline:
        1. Check rate limits
        2. Check cache
        3. Route to model
        4. Execute with circuit breaker
        5. Cache response
        6. Return result

        Args:
            request: InferenceRequest to execute
            routing_strategy: Optional routing strategy override

        Returns:
            InferenceResponse with result

        Raises:
            L04Error: On any error during execution
        """
        start_time = datetime.utcnow()

        try:
            logger.info(f"Executing request {request.request_id}")

            # Step 1: Check rate limits
            estimated_tokens = request.estimate_input_tokens()
            await self.rate_limiter.check_rate_limit(
                agent_did=request.agent_did,
                provider="gateway",  # Global rate limit
                tokens=estimated_tokens
            )

            # Step 2: Check cache (if enabled)
            if request.enable_cache:
                cached = await self.cache.get(request)
                if cached:
                    logger.info(f"Cache hit for request {request.request_id}")
                    return cached

            # Step 3: Route to model
            routing_decision = self.router.route(request, routing_strategy)
            logger.info(
                f"Routed to {routing_decision.primary_model_id} "
                f"({routing_decision.primary_provider})"
            )

            # Step 4: Execute with failover
            response = await self._execute_with_failover(
                request,
                routing_decision.primary_model_id,
                routing_decision.primary_provider,
                routing_decision.fallback_models
            )

            # Step 5: Cache response (if enabled and successful)
            if request.enable_cache and response.is_success():
                await self.cache.set(request, response)

            # Step 6: Record usage in L01 (if bridge is enabled)
            if self.l01_bridge:
                await self.l01_bridge.record_inference(request, response)

            # Log execution time
            total_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            logger.info(
                f"Request {request.request_id} completed in {total_time:.0f}ms "
                f"(model_latency={response.latency_ms}ms, cached={response.cached})"
            )

            return response

        except (RateLimitError, RoutingError):
            raise
        except Exception as e:
            logger.error(f"Request execution failed: {e}")
            if isinstance(e, L04Error):
                raise
            raise ProviderError(
                L04ErrorCode.E4200_PROVIDER_ERROR,
                f"Request execution failed: {str(e)}",
                {"error": str(e)}
            )

    async def complete(
        self,
        request: InferenceRequest,
        routing_strategy: Optional[RoutingStrategy] = None
    ) -> InferenceResponse:
        """
        Alias for execute() - completes an inference request

        Args:
            request: InferenceRequest to complete
            routing_strategy: Optional routing strategy override

        Returns:
            InferenceResponse with result

        Raises:
            L04Error: On any error during execution
        """
        return await self.execute(request, routing_strategy)

    async def stream(
        self,
        request: InferenceRequest,
        routing_strategy: Optional[RoutingStrategy] = None
    ) -> AsyncIterator[StreamChunk]:
        """
        Execute streaming inference request

        Args:
            request: InferenceRequest to execute
            routing_strategy: Optional routing strategy override

        Yields:
            StreamChunk objects with incremental content

        Raises:
            L04Error: On any error during execution
        """
        try:
            logger.info(f"Executing streaming request {request.request_id}")

            # Check rate limits
            estimated_tokens = request.estimate_input_tokens()
            await self.rate_limiter.check_rate_limit(
                agent_did=request.agent_did,
                provider="gateway",
                tokens=estimated_tokens
            )

            # Note: Streaming bypasses cache

            # Route to model
            routing_decision = self.router.route(request, routing_strategy)

            # Get provider
            provider = self.providers.get(routing_decision.primary_provider)
            if not provider:
                raise ProviderError(
                    L04ErrorCode.E4002_PROVIDER_NOT_CONFIGURED,
                    f"Provider not found: {routing_decision.primary_provider}"
                )

            # Execute streaming with circuit breaker
            async def stream_operation():
                return provider.stream(request, routing_decision.primary_model_id)

            stream_gen = await self.circuit_breaker.call(
                routing_decision.primary_provider,
                stream_operation
            )

            # Yield chunks
            async for chunk in stream_gen:
                yield chunk

        except Exception as e:
            logger.error(f"Streaming request failed: {e}")
            if isinstance(e, L04Error):
                raise
            raise ProviderError(
                L04ErrorCode.E4604_STREAMING_ERROR,
                f"Streaming failed: {str(e)}",
                {"error": str(e)}
            )

    async def _execute_with_failover(
        self,
        request: InferenceRequest,
        primary_model_id: str,
        primary_provider: str,
        fallback_models: list
    ) -> InferenceResponse:
        """
        Execute request with automatic failover to fallback models

        Args:
            request: InferenceRequest
            primary_model_id: Primary model to try
            primary_provider: Primary provider
            fallback_models: List of fallback model IDs

        Returns:
            InferenceResponse from successful execution

        Raises:
            ProviderError: If all attempts fail
        """
        # Try primary model
        try:
            return await self._execute_on_provider(
                request,
                primary_model_id,
                primary_provider
            )
        except Exception as e:
            logger.warning(
                f"Primary model {primary_model_id} failed: {e}, "
                f"trying {len(fallback_models)} fallbacks"
            )

        # Try fallback models
        for fallback_model_id in fallback_models:
            try:
                fallback_model = self.registry.get_model(fallback_model_id)
                if not fallback_model:
                    continue

                logger.info(f"Trying fallback model: {fallback_model_id}")

                return await self._execute_on_provider(
                    request,
                    fallback_model_id,
                    fallback_model.provider
                )

            except Exception as e:
                logger.warning(f"Fallback model {fallback_model_id} failed: {e}")
                continue

        # All attempts failed
        raise ProviderError(
            L04ErrorCode.E4102_ALL_MODELS_UNAVAILABLE,
            "All models failed",
            {"primary": primary_model_id, "fallbacks": fallback_models}
        )

    async def _execute_on_provider(
        self,
        request: InferenceRequest,
        model_id: str,
        provider_id: str
    ) -> InferenceResponse:
        """
        Execute request on specific provider

        Args:
            request: InferenceRequest
            model_id: Model ID to use
            provider_id: Provider ID

        Returns:
            InferenceResponse

        Raises:
            ProviderError: If execution fails
        """
        # Get provider adapter
        provider = self.providers.get(provider_id)
        if not provider:
            raise ProviderError(
                L04ErrorCode.E4002_PROVIDER_NOT_CONFIGURED,
                f"Provider not configured: {provider_id}"
            )

        # Execute through circuit breaker
        async def execute_operation():
            return await provider.complete(request, model_id)

        return await self.circuit_breaker.call(provider_id, execute_operation)

    async def health_check(self) -> Dict[str, dict]:
        """
        Check health of all components

        Returns:
            Dictionary with health status of each component
        """
        health = {
            "gateway": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "registry": self.registry.get_stats(),
            "cache": self.cache.get_stats(),
            "queue": self.request_queue.get_stats(),
            "circuit_breaker": self.circuit_breaker.get_stats(),
            "providers": {}
        }

        # Check each provider
        for provider_id, provider in self.providers.items():
            try:
                provider_health = await provider.health_check()
                health["providers"][provider_id] = provider_health.to_dict()

                # Update router with provider health
                self.router.update_provider_health(provider_health)

            except Exception as e:
                logger.error(f"Health check failed for {provider_id}: {e}")
                health["providers"][provider_id] = {
                    "status": "unavailable",
                    "error": str(e)
                }

        return health

    async def close(self) -> None:
        """Cleanup resources"""
        logger.info("Closing ModelGateway")

        if self.cache:
            await self.cache.close()

        if self.rate_limiter:
            await self.rate_limiter.close()

        if self.l01_bridge:
            await self.l01_bridge.cleanup()

        for provider in self.providers.values():
            if hasattr(provider, 'close'):
                await provider.close()

        logger.info("ModelGateway closed")
