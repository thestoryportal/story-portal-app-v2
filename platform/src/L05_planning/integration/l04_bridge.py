"""
L04 Bridge - Connects L05 Planning to L04 Model Gateway
Path: platform/src/L05_planning/integration/l04_bridge.py
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import uuid4

logger = logging.getLogger(__name__)


class ModelProvider(Enum):
    """Available model providers."""
    ANTHROPIC = "anthropic"
    OPENAI = "openai"
    OLLAMA = "ollama"
    LOCAL = "local"


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
        default_model: str = "claude-3-sonnet",
        default_provider: ModelProvider = ModelProvider.ANTHROPIC,
    ):
        """
        Initialize L04 bridge.

        Args:
            model_gateway: Optional L04 gateway instance
            base_url: Optional base URL for L04 service
            default_model: Default model for generation
            default_provider: Default model provider
        """
        self.model_gateway = model_gateway
        self.base_url = base_url or "http://localhost:8004"
        self.default_model = default_model
        self.default_provider = default_provider
        self._initialized = False
        self._generation_history: List[GeneratedPlan] = []

    async def initialize(self):
        """Initialize connection to L04."""
        if self._initialized:
            return

        # In production, would establish connection to L04
        logger.info(f"L04Bridge initialized (base_url={self.base_url})")
        self._initialized = True

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
            "initialized": self._initialized,
        }

    def clear_history(self):
        """Clears generation history."""
        self._generation_history = []
