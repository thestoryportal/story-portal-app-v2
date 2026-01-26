"""
Test Model Router - Tests for ModelRouter service
Path: platform/src/L05_planning/tests/test_model_router.py
"""

import asyncio
import pytest
from unittest.mock import Mock, AsyncMock, patch

from ..services.model_router import (
    ModelRouter,
    ComplexityLevel,
    TaskCategory,
    RoutingDecision,
    GenerationWithEscalation,
    MODEL_CONFIGS,
)
from ..integration.l04_bridge import L04Bridge, ModelProvider, RoutingStrategy, GeneratedPlan


@pytest.fixture
def mock_l04_bridge():
    """Create a mock L04 bridge."""
    bridge = Mock(spec=L04Bridge)
    # Mock both sync and async methods
    bridge.generate_plan_async = AsyncMock(return_value=GeneratedPlan(
        plan_id="plan-001",
        content="## Generated Plan\n\n### Acceptance Criteria\n\nThis file.py implements the solution.",
        model="mistral",
        provider=ModelProvider.OLLAMA,
        tokens_used=100,
        latency_ms=500,
    ))
    bridge.generate_plan = Mock(return_value=GeneratedPlan(
        plan_id="plan-001",
        content="## Generated Plan\n\n### Acceptance Criteria\n\nThis file.py implements the solution.",
        model="mistral",
        provider=ModelProvider.OLLAMA,
        tokens_used=100,
        latency_ms=500,
    ))
    bridge.is_connected.return_value = True
    return bridge


@pytest.fixture
def router(mock_l04_bridge):
    """Create a ModelRouter instance for testing."""
    return ModelRouter(
        l04_bridge=mock_l04_bridge,
        default_strategy=RoutingStrategy.BALANCED,
        quality_threshold=0.7,
        prefer_local=True,
    )


class TestComplexityAnalysis:
    """Tests for complexity analysis."""

    def test_analyze_simple_task(self, router):
        """Test analysis of simple tasks."""
        task = "Check if the file exists and validate its syntax"
        complexity = router.analyze_complexity(task)
        assert complexity == ComplexityLevel.SIMPLE

    def test_analyze_moderate_task(self, router):
        """Test analysis of moderate tasks."""
        task = "Generate a new module that implements the user interface"
        complexity = router.analyze_complexity(task)
        assert complexity == ComplexityLevel.MODERATE

    def test_analyze_complex_task(self, router):
        """Test analysis of complex tasks."""
        task = "Design and architect a novel distributed system"
        complexity = router.analyze_complexity(task)
        assert complexity == ComplexityLevel.COMPLEX

    def test_analyze_critical_task(self, router):
        """Test analysis of critical tasks."""
        task = "Perform critical security migration on production database"
        complexity = router.analyze_complexity(task)
        assert complexity == ComplexityLevel.CRITICAL

    def test_analyze_empty_task(self, router):
        """Test analysis of empty task defaults to simple."""
        complexity = router.analyze_complexity("")
        assert complexity == ComplexityLevel.SIMPLE

    def test_analyze_unknown_task(self, router):
        """Test analysis of task with no keywords defaults to simple."""
        complexity = router.analyze_complexity("xyz abc 123")
        assert complexity == ComplexityLevel.SIMPLE


class TestCategoryDetection:
    """Tests for task category detection."""

    def test_detect_validation_category(self, router):
        """Test detection of validation tasks."""
        task = "Validate the input format and check constraints"
        category = router.analyze_category(task)
        assert category == TaskCategory.VALIDATION

    def test_detect_generation_category(self, router):
        """Test detection of generation tasks."""
        task = "Generate a new REST API endpoint"
        category = router.analyze_category(task)
        assert category == TaskCategory.GENERATION

    def test_detect_analysis_category(self, router):
        """Test detection of analysis tasks."""
        task = "Analyze the code for potential issues"
        category = router.analyze_category(task)
        assert category == TaskCategory.ANALYSIS

    def test_detect_decomposition_category(self, router):
        """Test detection of decomposition tasks."""
        task = "Decompose the monolith into microservices"
        category = router.analyze_category(task)
        assert category == TaskCategory.DECOMPOSITION

    def test_detect_planning_category(self, router):
        """Test detection of planning tasks."""
        task = "Plan the architecture for the new system"
        category = router.analyze_category(task)
        assert category == TaskCategory.PLANNING


class TestRouting:
    """Tests for model routing."""

    def test_route_simple_validation(self, router):
        """Test routing of simple validation task."""
        decision = router.route("Check if file exists", strategy=RoutingStrategy.BALANCED)

        assert decision.complexity == ComplexityLevel.SIMPLE
        assert decision.provider == ModelProvider.OLLAMA
        assert decision.confidence > 0.5

    def test_route_complex_planning(self, router):
        """Test routing of complex planning task."""
        router.prefer_local = False  # Disable local preference
        decision = router.route(
            "Design a novel distributed architecture for critical production system",
            strategy=RoutingStrategy.QUALITY,
        )

        assert decision.complexity in [ComplexityLevel.COMPLEX, ComplexityLevel.CRITICAL]
        assert decision.provider == ModelProvider.ANTHROPIC

    def test_route_with_cost_strategy(self, router):
        """Test routing with cost optimization strategy."""
        decision = router.route("Create a simple function", strategy=RoutingStrategy.COST)

        # Cost strategy should prefer Ollama (free)
        assert decision.provider == ModelProvider.OLLAMA
        assert decision.estimated_cost == 0.0

    def test_route_with_latency_strategy(self, router):
        """Test routing with latency optimization strategy."""
        decision = router.route("Quick syntax check", strategy=RoutingStrategy.LATENCY)

        # Latency strategy should prefer fastest model
        assert decision.estimated_latency_ms > 0

    def test_route_with_complexity_hint(self, router):
        """Test routing with explicit complexity hint."""
        decision = router.route(
            "Some task",
            complexity_hint=ComplexityLevel.CRITICAL,
        )

        assert decision.complexity == ComplexityLevel.CRITICAL

    def test_route_with_category_hint(self, router):
        """Test routing with explicit category hint."""
        decision = router.route(
            "Some task",
            category_hint=TaskCategory.PLANNING,
        )

        assert decision.category == TaskCategory.PLANNING


class TestModelSelection:
    """Tests for model selection logic via routing."""

    def test_select_ollama_for_simple(self, router):
        """Test that Ollama is selected for simple tasks."""
        decision = router.route(
            "Check if file exists",
            complexity_hint=ComplexityLevel.SIMPLE,
            category_hint=TaskCategory.VALIDATION,
            strategy=RoutingStrategy.BALANCED,
        )

        assert decision.provider == ModelProvider.OLLAMA
        assert decision.model in ["codellama", "mistral", "llama2"]

    def test_select_claude_for_critical(self, router):
        """Test that Claude is selected for critical tasks."""
        router.prefer_local = False
        decision = router.route(
            "Critical production planning task",
            complexity_hint=ComplexityLevel.CRITICAL,
            category_hint=TaskCategory.PLANNING,
            strategy=RoutingStrategy.QUALITY,
        )

        assert decision.provider == ModelProvider.ANTHROPIC
        assert "claude" in decision.model.lower()

    def test_prefer_local_option(self, router):
        """Test prefer_local option."""
        router.prefer_local = True
        decision = router.route(
            "Generate a simple function",
            complexity_hint=ComplexityLevel.MODERATE,
            category_hint=TaskCategory.GENERATION,
            strategy=RoutingStrategy.BALANCED,
        )

        # With prefer_local, should try Ollama first
        assert decision.provider == ModelProvider.OLLAMA


class TestQualityEscalation:
    """Tests for quality-based escalation."""

    @pytest.mark.asyncio
    async def test_no_escalation_on_good_quality(self, router, mock_l04_bridge):
        """Test that no escalation occurs when quality is good."""
        result = await router.generate_with_escalation(
            "Generate a simple function",
            min_quality=0.6,
        )

        assert result.escalated is False
        assert result.attempts == 1
        assert len(result.models_tried) == 1

    @pytest.mark.asyncio
    async def test_escalation_on_low_quality(self, router, mock_l04_bridge):
        """Test escalation when quality is low."""
        # First call returns low quality (short content), second returns good quality (longer with structure)
        mock_l04_bridge.generate_plan = Mock(side_effect=[
            GeneratedPlan(
                plan_id="plan-low",
                content="Low quality",
                model="codellama",
                provider=ModelProvider.OLLAMA,
                tokens_used=50,
                latency_ms=300,
            ),
            GeneratedPlan(
                plan_id="plan-high",
                content="## High Quality Plan\n\n### Acceptance Criteria\n\nThis file.py solution has multiple sections and proper structure.",
                model="claude-3-sonnet",
                provider=ModelProvider.ANTHROPIC,
                tokens_used=200,
                latency_ms=600,
            ),
        ])

        result = await router.generate_with_escalation(
            "Generate a function",
            min_quality=0.7,
        )

        assert result.escalated is True
        assert result.attempts == 2

    @pytest.mark.asyncio
    async def test_max_escalation_attempts(self, router, mock_l04_bridge):
        """Test that escalation stops after max attempts."""
        # All calls return low quality content (short, no structure)
        mock_l04_bridge.generate_plan = Mock(return_value=GeneratedPlan(
            plan_id="plan-low",
            content="Low quality",
            model="codellama",
            provider=ModelProvider.OLLAMA,
            tokens_used=50,
            latency_ms=300,
        ))

        result = await router.generate_with_escalation(
            "Generate a function",
            min_quality=0.9,
            max_escalations=2,
        )

        assert result.attempts <= 3


class TestRoutingHistory:
    """Tests for routing history tracking."""

    def test_routing_history_recorded(self, router):
        """Test that routing decisions are recorded."""
        router.route("Task 1")
        router.route("Task 2")

        assert len(router._routing_history) == 2

    def test_get_routing_statistics(self, router):
        """Test getting routing statistics."""
        router.route("Simple check task")
        router.route("Complex design task")

        stats = router.get_statistics()

        assert stats["total_routings"] == 2
        assert "by_provider" in stats
        assert "by_complexity" in stats


class TestCostTracking:
    """Tests for cost tracking."""

    @pytest.mark.asyncio
    async def test_cost_accumulation(self, router, mock_l04_bridge):
        """Test that costs are accumulated."""
        # Ensure generate_plan returns proper content
        mock_l04_bridge.generate_plan = Mock(return_value=GeneratedPlan(
            plan_id="plan-001",
            content="## Generated Plan\n\n### Acceptance Criteria\n\nThis file.py implements the solution properly.",
            model="mistral",
            provider=ModelProvider.OLLAMA,
            tokens_used=100,
            latency_ms=500,
        ))

        await router.generate_with_escalation("Task 1")
        await router.generate_with_escalation("Task 2")

        stats = router.get_statistics()
        # Ollama is free, so cost should be 0
        assert stats["total_cost"] >= 0


class TestModelConfigs:
    """Tests for MODEL_CONFIGS."""

    def test_ollama_configs_exist(self):
        """Test that Ollama model configs exist."""
        assert ModelProvider.OLLAMA in MODEL_CONFIGS
        assert "codellama" in MODEL_CONFIGS[ModelProvider.OLLAMA]
        assert "mistral" in MODEL_CONFIGS[ModelProvider.OLLAMA]

    def test_anthropic_configs_exist(self):
        """Test that Anthropic model configs exist."""
        assert ModelProvider.ANTHROPIC in MODEL_CONFIGS
        assert "claude-3-sonnet" in MODEL_CONFIGS[ModelProvider.ANTHROPIC]

    def test_config_has_required_fields(self):
        """Test that configs have required fields."""
        for provider_configs in MODEL_CONFIGS.values():
            for model_config in provider_configs.values():
                assert "complexity" in model_config
                assert "categories" in model_config
                assert "cost_factor" in model_config
                assert "latency_ms" in model_config


class TestEdgeCases:
    """Tests for edge cases."""

    def test_route_with_none_strategy(self, router):
        """Test routing with None strategy uses default."""
        decision = router.route("Test task", strategy=None)
        assert decision is not None

    def test_route_very_long_task(self, router):
        """Test routing with very long task description."""
        long_task = "Create " * 1000 + "a function"
        decision = router.route(long_task)
        assert decision is not None

    def test_route_unicode_task(self, router):
        """Test routing with unicode characters."""
        task = "Create a function for handling 日本語 text"
        decision = router.route(task)
        assert decision is not None

    @pytest.mark.asyncio
    async def test_generate_with_zero_min_quality(self, router, mock_l04_bridge):
        """Test generation with zero minimum quality."""
        # Ensure generate_plan returns proper content
        mock_l04_bridge.generate_plan = Mock(return_value=GeneratedPlan(
            plan_id="plan-001",
            content="Some generated content",
            model="mistral",
            provider=ModelProvider.OLLAMA,
            tokens_used=100,
            latency_ms=500,
        ))

        result = await router.generate_with_escalation(
            "Generate something",
            min_quality=0.0,
        )
        assert result.escalated is False


class TestRoutingDecision:
    """Tests for RoutingDecision dataclass."""

    def test_routing_decision_fields(self):
        """Test RoutingDecision has all required fields."""
        decision = RoutingDecision(
            model="codellama",
            provider=ModelProvider.OLLAMA,
            complexity=ComplexityLevel.SIMPLE,
            category=TaskCategory.VALIDATION,
            confidence=0.9,
            reason="Simple validation task",
        )

        assert decision.model == "codellama"
        assert decision.provider == ModelProvider.OLLAMA
        assert decision.complexity == ComplexityLevel.SIMPLE
        assert decision.category == TaskCategory.VALIDATION
        assert decision.confidence == 0.9
        assert decision.estimated_cost == 0.0
        assert decision.estimated_latency_ms == 0


class TestGenerationWithEscalation:
    """Tests for GenerationWithEscalation dataclass."""

    def test_generation_result_fields(self):
        """Test GenerationWithEscalation has all required fields."""
        result = GenerationWithEscalation(
            plan=GeneratedPlan(
                plan_id="plan-001",
                content="test",
                model="mistral",
                provider=ModelProvider.OLLAMA,
                tokens_used=100,
                latency_ms=500,
            ),
            escalated=True,
            escalation_reason="Low quality",
            attempts=2,
            models_tried=["codellama", "mistral"],
            total_cost=0.0,
        )

        assert result.escalated is True
        assert result.attempts == 2
        assert len(result.models_tried) == 2
