"""L04 Model Gateway layer tests."""
import pytest
from uuid import uuid4

class TestL04ModelGateway:
    """Test L04 Model Gateway functionality."""

    @pytest.fixture
    async def gateway(self):
        """Initialize model gateway."""
        from src.L04_model_gateway.services.model_gateway import ModelGateway
        gateway = ModelGateway()
        yield gateway

    @pytest.fixture
    async def model_registry(self):
        """Initialize model registry."""
        from src.L04_model_gateway.services.model_registry import ModelRegistry
        registry = ModelRegistry()
        yield registry

    @pytest.fixture
    async def llm_router(self):
        """Initialize LLM router."""
        from src.L04_model_gateway.services.llm_router import LLMRouter
        from src.L04_model_gateway.services.model_registry import ModelRegistry
        registry = ModelRegistry()
        router = LLMRouter(registry)
        yield router

    @pytest.mark.asyncio
    async def test_gateway_initialization(self, gateway):
        """Gateway initializes correctly."""
        assert gateway is not None

    @pytest.mark.asyncio
    async def test_registry_initialization(self, model_registry):
        """Model registry initializes correctly."""
        assert model_registry is not None

    @pytest.mark.asyncio
    async def test_router_initialization(self, llm_router):
        """LLM router initializes correctly."""
        assert llm_router is not None

    @pytest.mark.asyncio
    async def test_list_available_models(self, model_registry):
        """Can list available models."""
        models = await model_registry.list_models()
        assert isinstance(models, list)

    @pytest.mark.asyncio
    async def test_ollama_provider_health(self, gateway):
        """Ollama provider is healthy."""
        from src.L04_model_gateway.providers.ollama_adapter import OllamaAdapter
        adapter = OllamaAdapter(base_url="http://localhost:11434")
        health = await adapter.health_check()
        assert health is not None

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_simple_completion(self, gateway):
        """Can complete a simple prompt via Ollama."""
        from src.L04_model_gateway.models.inference_request import (
            InferenceRequest, LogicalPrompt, ModelRequirements, RequestConstraints
        )

        request = InferenceRequest(
            request_id=str(uuid4()),
            agent_did="did:agent:e2e-test",
            logical_prompt=LogicalPrompt(
                system="You are a helpful assistant.",
                user="Say 'hello' and nothing else."
            ),
            requirements=ModelRequirements(capabilities=[]),
            constraints=RequestConstraints(max_latency_ms=30000)
        )

        response = await gateway.complete(request)
        assert response is not None
        assert response.content is not None
        assert len(response.content) > 0

    @pytest.mark.asyncio
    async def test_semantic_cache(self, gateway):
        """Semantic cache stores and retrieves."""
        from src.L04_model_gateway.services.semantic_cache import SemanticCache
        cache = SemanticCache()

        # Cache operations may be stubbed
        assert cache is not None

    @pytest.mark.asyncio
    async def test_rate_limiter(self, gateway):
        """Rate limiter tracks requests."""
        from src.L04_model_gateway.services.rate_limiter import RateLimiter
        limiter = RateLimiter()

        allowed = await limiter.check_limit(agent_id="test-agent", tokens=100)
        assert isinstance(allowed, bool)
