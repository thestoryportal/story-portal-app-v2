"""
L04 Bridge - Connects L05 Planning to L04 Model Gateway
Path: platform/src/L05_planning/integration/l04_bridge.py

Enhanced with real HTTP client support for connecting to L04 service.
"""

import logging
import os
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, AsyncIterator, Dict, List, Optional
from uuid import uuid4

logger = logging.getLogger(__name__)

# Optional httpx import for real HTTP calls
try:
    import httpx
    HTTPX_AVAILABLE = True
except ImportError:
    HTTPX_AVAILABLE = False
    logger.warning("httpx not available, L04Bridge will use mock generation only")


class ModelProvider(Enum):
    """Available model providers."""
    ANTHROPIC = "anthropic"
    OPENAI = "openai"
    OLLAMA = "ollama"
    LOCAL = "local"


class RoutingStrategy(Enum):
    """Model routing strategies."""
    COST = "cost"        # Minimize cost (prefer Ollama)
    QUALITY = "quality"  # Maximize quality (prefer Claude)
    LATENCY = "latency"  # Minimize latency
    BALANCED = "balanced"  # Balance cost/quality


@dataclass
class GenerationRequest:
    """Request for plan generation."""
    prompt: str
    context: Dict[str, Any] = field(default_factory=dict)
    model: str = "claude-3-sonnet"
    provider: ModelProvider = ModelProvider.ANTHROPIC
    max_tokens: int = 4096
    temperature: float = 0.7
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class GeneratedPlan:
    """A generated plan from the model."""
    plan_id: str
    content: str
    model: str
    provider: ModelProvider
    tokens_used: int = 0
    latency_ms: int = 0
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CompletionResult:
    """Result of a model completion."""
    content: str
    model: str
    tokens_used: int = 0
    latency_ms: int = 0
    cached: bool = False


class L04Bridge:
    """
    Bridge to L04 Model Gateway for LLM-powered plan generation.

    Features:
    - Real HTTP connection to L04 service (localhost:8004)
    - Health check on initialization
    - Graceful fallback to mock generation when L04 unavailable
    - Support for multiple routing strategies
    - Streaming response support

    Provides abstraction for:
    - Generating implementation plans
    - Completing partial plans
    - Refining existing plans
    - Model selection and routing
    """

    def __init__(
        self,
        model_gateway: Optional[Any] = None,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        default_model: str = "claude-3-sonnet",
        default_provider: ModelProvider = ModelProvider.ANTHROPIC,
        default_strategy: RoutingStrategy = RoutingStrategy.BALANCED,
        timeout: float = 60.0,
    ):
        """
        Initialize L04 bridge.

        Args:
            model_gateway: Optional L04 gateway instance (for dependency injection)
            base_url: Base URL for L04 service (default: http://localhost:8004)
            api_key: API key for L04 authentication
            default_model: Default model for generation
            default_provider: Default model provider
            default_strategy: Default routing strategy
            timeout: HTTP request timeout in seconds
        """
        self.model_gateway = model_gateway
        self.base_url = base_url or os.getenv("L04_BASE_URL", "http://localhost:8004")
        self.api_key = api_key or os.getenv("L04_API_KEY", "test_token_123")
        self.default_model = default_model
        self.default_provider = default_provider
        self.default_strategy = default_strategy
        self.timeout = timeout

        self._initialized = False
        self._connected = False
        self._http_client: Optional["httpx.AsyncClient"] = None
        self._generation_history: List[GeneratedPlan] = []

        # Statistics
        self._remote_generation_count = 0
        self._local_generation_count = 0
        self._failed_generation_count = 0
        self._total_tokens_used = 0

    async def initialize(self):
        """Initialize connection to L04 with health check."""
        if self._initialized:
            return

        logger.info(f"Initializing L04Bridge (base_url={self.base_url})")

        if HTTPX_AVAILABLE:
            try:
                self._http_client = httpx.AsyncClient(
                    base_url=self.base_url,
                    timeout=self.timeout,
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                )

                # Health check
                response = await self._http_client.get("/health")
                if response.status_code == 200:
                    self._connected = True
                    logger.info("L04Bridge connected to L04 service")
                else:
                    logger.warning(f"L04 health check failed: {response.status_code}")
                    self._connected = False

            except Exception as e:
                logger.warning(f"Failed to connect to L04: {e}. Using mock generation.")
                self._connected = False
                if self._http_client:
                    await self._http_client.aclose()
                    self._http_client = None
        else:
            logger.info("httpx not available, using mock generation only")
            self._connected = False

        self._initialized = True
        logger.info(f"L04Bridge initialized (connected={self._connected})")

    async def close(self):
        """Close HTTP client connection."""
        if self._http_client:
            await self._http_client.aclose()
            self._http_client = None
        self._connected = False

    def generate_plan(
        self,
        task_description: str,
        context: Optional[Dict[str, Any]] = None,
        model: Optional[str] = None,
        provider: Optional[ModelProvider] = None,
    ) -> GeneratedPlan:
        """
        Generates an implementation plan for a task.

        Args:
            task_description: Description of the task to plan
            context: Optional context for generation
            model: Model to use (defaults to instance default)
            provider: Provider to use (defaults to instance default)

        Returns:
            GeneratedPlan with generated content
        """
        start_time = datetime.now()
        use_model = model or self.default_model
        use_provider = provider or self.default_provider

        logger.info(f"Generating plan with {use_model} ({use_provider.value})")

        # Build prompt
        prompt = self._build_plan_prompt(task_description, context or {})

        # If gateway available, use it
        if self.model_gateway:
            result = self._generate_via_gateway(prompt, use_model, use_provider)
        else:
            # Generate mock plan for standalone operation
            result = self._generate_mock_plan(task_description)

        end_time = datetime.now()
        latency_ms = int((end_time - start_time).total_seconds() * 1000)

        plan = GeneratedPlan(
            plan_id=str(uuid4())[:8],
            content=result.content,
            model=use_model,
            provider=use_provider,
            tokens_used=result.tokens_used,
            latency_ms=latency_ms,
            metadata={
                "task_description": task_description[:100],
                "cached": result.cached,
            }
        )

        self._generation_history.append(plan)
        logger.debug(f"Generated plan {plan.plan_id} ({result.tokens_used} tokens)")

        return plan

    async def generate_plan_async(
        self,
        task_description: str,
        context: Optional[Dict[str, Any]] = None,
        model: Optional[str] = None,
        provider: Optional[ModelProvider] = None,
        strategy: Optional[RoutingStrategy] = None,
    ) -> GeneratedPlan:
        """
        Generates an implementation plan for a task (async with remote support).

        Args:
            task_description: Description of the task to plan
            context: Optional context for generation
            model: Model to use (defaults to instance default)
            provider: Provider to use (defaults to instance default)
            strategy: Routing strategy (defaults to instance default)

        Returns:
            GeneratedPlan with generated content
        """
        start_time = datetime.now()
        use_model = model or self.default_model
        use_provider = provider or self.default_provider
        use_strategy = strategy or self.default_strategy

        logger.info(f"Generating plan async with {use_model} ({use_provider.value}, strategy={use_strategy.value})")

        # Build prompt
        prompt = self._build_plan_prompt(task_description, context or {})

        # Try remote generation first
        if self._connected and self._http_client:
            try:
                result = await self._generate_via_http(prompt, use_model, use_provider, use_strategy)
                if result:
                    self._remote_generation_count += 1
                    self._total_tokens_used += result.tokens_used
                else:
                    result = self._generate_mock_plan(task_description)
                    self._local_generation_count += 1
            except Exception as e:
                logger.warning(f"Remote generation failed, falling back to mock: {e}")
                result = self._generate_mock_plan(task_description)
                self._local_generation_count += 1
        elif self.model_gateway:
            result = self._generate_via_gateway(prompt, use_model, use_provider)
        else:
            result = self._generate_mock_plan(task_description)
            self._local_generation_count += 1

        end_time = datetime.now()
        latency_ms = int((end_time - start_time).total_seconds() * 1000)

        plan = GeneratedPlan(
            plan_id=str(uuid4())[:8],
            content=result.content,
            model=use_model,
            provider=use_provider,
            tokens_used=result.tokens_used,
            latency_ms=latency_ms,
            metadata={
                "task_description": task_description[:100],
                "cached": result.cached,
                "remote": self._connected,
                "strategy": use_strategy.value,
            }
        )

        self._generation_history.append(plan)
        logger.debug(f"Generated plan {plan.plan_id} ({result.tokens_used} tokens, remote={self._connected})")

        return plan

    async def _generate_via_http(
        self,
        prompt: str,
        model: str,
        provider: ModelProvider,
        strategy: RoutingStrategy,
    ) -> Optional[CompletionResult]:
        """Generate via HTTP to L04 service."""
        if not self._http_client:
            return None

        payload = {
            "prompt": prompt,
            "model": model,
            "provider": provider.value,
            "strategy": strategy.value,
            "max_tokens": 4096,
            "temperature": 0.7,
        }

        response = await self._http_client.post("/api/v1/inference", json=payload)

        if response.status_code == 200:
            data = response.json()
            return CompletionResult(
                content=data.get("content", ""),
                model=data.get("model", model),
                tokens_used=data.get("tokens_used", 0),
                latency_ms=data.get("latency_ms", 0),
                cached=data.get("cached", False),
            )
        else:
            logger.warning(f"L04 generation failed: {response.status_code} - {response.text}")
            return None

    async def generate_stream(
        self,
        task_description: str,
        context: Optional[Dict[str, Any]] = None,
        model: Optional[str] = None,
    ) -> AsyncIterator[str]:
        """
        Generate plan with streaming response.

        Args:
            task_description: Description of the task to plan
            context: Optional context for generation
            model: Model to use

        Yields:
            Chunks of generated content
        """
        use_model = model or self.default_model
        prompt = self._build_plan_prompt(task_description, context or {})

        if self._connected and self._http_client:
            try:
                payload = {
                    "prompt": prompt,
                    "model": use_model,
                    "stream": True,
                    "max_tokens": 4096,
                }

                async with self._http_client.stream("POST", "/api/v1/inference/stream", json=payload) as response:
                    if response.status_code == 200:
                        async for chunk in response.aiter_text():
                            yield chunk
                        return

            except Exception as e:
                logger.warning(f"Streaming failed: {e}")

        # Fallback to mock (yield all at once)
        result = self._generate_mock_plan(task_description)
        yield result.content

    async def complete_plan_async(
        self,
        partial_plan: str,
        instructions: Optional[str] = None,
    ) -> GeneratedPlan:
        """Completes a partial plan (async with remote support)."""
        context = {
            "partial_plan": partial_plan,
            "instructions": instructions or "Complete this plan",
        }
        return await self.generate_plan_async(
            task_description="Complete the following partial plan",
            context=context,
        )

    async def refine_plan_async(
        self,
        plan_content: str,
        feedback: str,
    ) -> GeneratedPlan:
        """Refines a plan based on feedback (async with remote support)."""
        context = {
            "original_plan": plan_content,
            "feedback": feedback,
        }
        return await self.generate_plan_async(
            task_description="Refine this plan based on feedback",
            context=context,
        )

    async def decompose_task_async(
        self,
        task: str,
        constraints: Optional[Dict[str, Any]] = None,
    ) -> GeneratedPlan:
        """Decomposes a task into subtasks (async with remote support)."""
        context = {
            "task": task,
            "constraints": constraints or {},
            "output_format": "atomic_units",
        }
        return await self.generate_plan_async(
            task_description="Decompose this task into atomic units",
            context=context,
        )

    def complete_plan(
        self,
        partial_plan: str,
        instructions: Optional[str] = None,
    ) -> GeneratedPlan:
        """
        Completes a partial plan.

        Args:
            partial_plan: Existing partial plan
            instructions: Optional completion instructions

        Returns:
            GeneratedPlan with completed content
        """
        context = {
            "partial_plan": partial_plan,
            "instructions": instructions or "Complete this plan",
        }
        return self.generate_plan(
            task_description="Complete the following partial plan",
            context=context,
        )

    def refine_plan(
        self,
        plan_content: str,
        feedback: str,
    ) -> GeneratedPlan:
        """
        Refines a plan based on feedback.

        Args:
            plan_content: Original plan content
            feedback: Feedback for refinement

        Returns:
            GeneratedPlan with refined content
        """
        context = {
            "original_plan": plan_content,
            "feedback": feedback,
        }
        return self.generate_plan(
            task_description="Refine this plan based on feedback",
            context=context,
        )

    def decompose_task(
        self,
        task: str,
        constraints: Optional[Dict[str, Any]] = None,
    ) -> GeneratedPlan:
        """
        Decomposes a task into subtasks.

        Args:
            task: Task to decompose
            constraints: Optional constraints for decomposition

        Returns:
            GeneratedPlan with decomposed tasks
        """
        context = {
            "task": task,
            "constraints": constraints or {},
            "output_format": "atomic_units",
        }
        return self.generate_plan(
            task_description="Decompose this task into atomic units",
            context=context,
        )

    def _build_plan_prompt(
        self,
        task_description: str,
        context: Dict[str, Any],
    ) -> str:
        """Builds the prompt for plan generation."""
        prompt_parts = [
            "Generate a detailed implementation plan for the following task:",
            "",
            f"Task: {task_description}",
            "",
        ]

        if context:
            prompt_parts.append("Context:")
            for key, value in context.items():
                prompt_parts.append(f"  {key}: {value}")
            prompt_parts.append("")

        prompt_parts.extend([
            "Requirements:",
            "- Break down into discrete, testable steps",
            "- Include acceptance criteria for each step",
            "- List files to be created or modified",
            "- Specify dependencies between steps",
            "",
            "Output the plan in markdown format.",
        ])

        return "\n".join(prompt_parts)

    def _generate_via_gateway(
        self,
        prompt: str,
        model: str,
        provider: ModelProvider,
    ) -> CompletionResult:
        """Generate via L04 gateway."""
        # This would call the actual L04 gateway
        # For now, return mock result
        return self._generate_mock_plan("via gateway")

    def _generate_mock_plan(self, task: str) -> CompletionResult:
        """Generate a mock plan for testing."""
        mock_plan = f"""## Phase 1: Implementation

### Step 1.1: Setup
Set up the initial project structure.

**Files**: main.py, config.py
**Acceptance**: Files exist and are valid Python

### Step 1.2: Core Implementation
Implement the core functionality for: {task[:50]}

**Files**: core.py, utils.py
**Acceptance**: Core logic works correctly
**Depends**: Step 1.1

### Step 1.3: Testing
Add tests for the implementation.

**Files**: test_core.py
**Acceptance**: All tests pass
**Depends**: Step 1.2
"""
        return CompletionResult(
            content=mock_plan,
            model=self.default_model,
            tokens_used=len(mock_plan.split()) * 2,  # Rough estimate
        )

    def get_available_models(self) -> Dict[ModelProvider, List[str]]:
        """Returns available models by provider."""
        return {
            ModelProvider.ANTHROPIC: [
                "claude-3-opus",
                "claude-3-sonnet",
                "claude-3-haiku",
            ],
            ModelProvider.OPENAI: [
                "gpt-4",
                "gpt-4-turbo",
                "gpt-3.5-turbo",
            ],
            ModelProvider.OLLAMA: [
                "llama2",
                "codellama",
                "mistral",
            ],
            ModelProvider.LOCAL: [
                "local-model",
            ],
        }

    def get_generation_history(
        self,
        limit: int = 10,
    ) -> List[GeneratedPlan]:
        """Returns generation history."""
        return self._generation_history[-limit:]

    def get_statistics(self) -> Dict[str, Any]:
        """Returns bridge statistics."""
        total_tokens = sum(p.tokens_used for p in self._generation_history)
        total_latency = sum(p.latency_ms for p in self._generation_history)

        return {
            "total_generations": len(self._generation_history),
            "total_tokens_used": total_tokens,
            "total_latency_ms": total_latency,
            "average_tokens": total_tokens / len(self._generation_history) if self._generation_history else 0,
            "average_latency_ms": total_latency / len(self._generation_history) if self._generation_history else 0,
            "default_model": self.default_model,
            "default_provider": self.default_provider.value,
            "default_strategy": self.default_strategy.value,
            "initialized": self._initialized,
            "connected": self._connected,
            "base_url": self.base_url,
            "remote_generation_count": self._remote_generation_count,
            "local_generation_count": self._local_generation_count,
            "failed_generation_count": self._failed_generation_count,
        }

    def is_connected(self) -> bool:
        """Returns True if connected to L04 service."""
        return self._connected

    def clear_history(self):
        """Clears generation history."""
        self._generation_history = []
