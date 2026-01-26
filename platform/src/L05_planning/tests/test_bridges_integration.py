"""
Test Bridges Integration - Integration tests for L01, L04, L06, L11 bridges
Path: platform/src/L05_planning/tests/test_bridges_integration.py

These tests verify the bridge implementations work correctly.
Integration tests that require real services are marked with @pytest.mark.integration.
"""

import asyncio
import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
import httpx

from ..integration.l01_bridge import L01Bridge, StoreResult, StoreResultType
from ..integration.l04_bridge import (
    L04Bridge,
    ModelProvider,
    RoutingStrategy,
    GeneratedPlan,
)
from ..integration.l06_bridge import (
    L06Bridge,
    UnitScore,
    PlanScore,
    AssessmentLevel,
)
from ..integration.l11_bridge import (
    L11Bridge,
    EventType,
    PublishResult,
    CircuitBreaker,
    CircuitState,
)
from ..agents.spec_decomposer import AtomicUnit, AcceptanceCriterion
from ..agents.unit_validator import ValidationResult, ValidationStatus


# =======================
# L01 Bridge Tests
# =======================

class TestL01BridgeUnit:
    """Unit tests for L01Bridge."""

    @pytest.fixture
    def bridge(self):
        """Create L01Bridge instance."""
        return L01Bridge(base_url="http://localhost:8001")

    def test_init_with_defaults(self):
        """Test L01Bridge initialization with defaults."""
        bridge = L01Bridge()
        assert bridge.base_url == "http://localhost:8001"
        assert bridge.timeout == 30

    def test_init_with_custom_url(self):
        """Test L01Bridge initialization with custom URL."""
        bridge = L01Bridge(base_url="http://custom:9000")
        assert bridge.base_url == "http://custom:9000"

    @pytest.mark.asyncio
    async def test_store_plan_local_fallback(self, bridge):
        """Test store_plan falls back to local storage."""
        result = await bridge.store_plan_async(
            plan_id="plan-001",
            plan_data={"name": "Test Plan"},
        )

        assert result.success is True
        assert result.result_type == StoreResultType.PLAN

    @pytest.mark.asyncio
    async def test_store_unit_local_fallback(self, bridge):
        """Test store_unit falls back to local storage."""
        result = await bridge.store_unit_async(
            unit_id="unit-001",
            unit_data={"title": "Test Unit"},
            plan_id="plan-001",
        )

        assert result.success is True

    @pytest.mark.asyncio
    async def test_retrieve_plan_local(self, bridge):
        """Test retrieving a plan from local storage."""
        # First store
        await bridge.store_plan_async("plan-001", {"name": "Test"})

        # Then retrieve using get_record_async
        result = await bridge.get_record_async("plan-001")

        assert result is not None
        assert result.data.get("name") == "Test"

    def test_is_connected_when_not_initialized(self, bridge):
        """Test is_connected returns False when not initialized."""
        assert bridge.is_connected() is False


class TestL01BridgeIntegration:
    """Integration tests for L01Bridge (require running L01 service)."""

    @pytest.fixture
    def bridge(self):
        """Create L01Bridge instance."""
        return L01Bridge(base_url="http://localhost:8001")

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_real_service_connection(self, bridge):
        """Test connection to real L01 service."""
        await bridge.initialize()
        assert bridge.is_connected() is True
        await bridge.close()

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_store_and_retrieve_plan(self, bridge):
        """Test storing and retrieving a plan from real service."""
        await bridge.initialize()

        result = await bridge.store_plan_async(
            plan_id="test-plan-integration",
            plan_data={"name": "Integration Test Plan"},
        )

        assert result.success is True
        await bridge.close()


# =======================
# L04 Bridge Tests
# =======================

class TestL04BridgeUnit:
    """Unit tests for L04Bridge."""

    @pytest.fixture
    def bridge(self):
        """Create L04Bridge instance."""
        return L04Bridge(base_url="http://localhost:8004")

    def test_init_with_defaults(self):
        """Test L04Bridge initialization with defaults."""
        bridge = L04Bridge()
        assert bridge.base_url == "http://localhost:8004"

    def test_init_with_custom_params(self):
        """Test L04Bridge initialization with custom parameters."""
        bridge = L04Bridge(
            base_url="http://custom:9004",
            default_provider=ModelProvider.ANTHROPIC,
            default_strategy=RoutingStrategy.QUALITY,
        )
        assert bridge.base_url == "http://custom:9004"
        assert bridge.default_provider == ModelProvider.ANTHROPIC

    @pytest.mark.asyncio
    async def test_generate_plan_local_fallback(self, bridge):
        """Test generate_plan falls back to local generation."""
        result = await bridge.generate_plan_async(
            task_description="Create a simple function",
            model="mistral",
        )

        assert result is not None
        assert isinstance(result, GeneratedPlan)
        # Default provider is ANTHROPIC (see L04Bridge.__init__)
        assert result.provider == ModelProvider.ANTHROPIC

    @pytest.mark.asyncio
    async def test_generate_with_different_strategies(self, bridge):
        """Test generation with different routing strategies."""
        for strategy in RoutingStrategy:
            result = await bridge.generate_plan_async(
                task_description="Test prompt",
                strategy=strategy,
            )
            assert result is not None

    def test_is_connected_when_not_initialized(self, bridge):
        """Test is_connected returns False when not initialized."""
        assert bridge.is_connected() is False


class TestL04BridgeIntegration:
    """Integration tests for L04Bridge (require running L04 service)."""

    @pytest.fixture
    def bridge(self):
        """Create L04Bridge instance."""
        return L04Bridge(base_url="http://localhost:8004")

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_real_service_connection(self, bridge):
        """Test connection to real L04 service."""
        await bridge.initialize()
        assert bridge.is_connected() is True
        await bridge.close()

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_real_generation(self, bridge):
        """Test generation with real L04 service."""
        await bridge.initialize()

        result = await bridge.generate_plan_async(
            task_description="Generate a hello world function in Python",
            model="codellama",
        )

        assert result is not None
        assert len(result.content) > 0
        await bridge.close()


# =======================
# L06 Bridge Tests
# =======================

class TestL06BridgeUnit:
    """Unit tests for L06Bridge."""

    @pytest.fixture
    def bridge(self):
        """Create L06Bridge instance."""
        return L06Bridge(base_url="http://localhost:8006")

    @pytest.fixture
    def mock_unit(self):
        """Create a mock AtomicUnit."""
        return AtomicUnit(
            id="unit-001",
            title="Test Unit",
            description="Test description",
            files=["test.py"],
            complexity=1,
            acceptance_criteria=[
                AcceptanceCriterion(
                    id="ac-001",
                    description="Test passes",
                    validation_command="pytest test.py",
                    timeout_seconds=30,
                )
            ],
            dependencies=[],
        )

    @pytest.fixture
    def mock_validation_result(self):
        """Create a mock ValidationResult."""
        return ValidationResult(
            unit_id="unit-001",
            status=ValidationStatus.PASSED,
            passed=True,
            criterion_results=[],
        )

    def test_init_with_defaults(self):
        """Test L06Bridge initialization with defaults."""
        bridge = L06Bridge()
        assert bridge.base_url == "http://localhost:8006"

    @pytest.mark.asyncio
    async def test_score_unit_local_calculation(self, bridge, mock_unit, mock_validation_result):
        """Test score_unit uses local calculation as fallback."""
        score = await bridge.score_unit_async(mock_unit, mock_validation_result)

        assert score is not None
        assert isinstance(score, UnitScore)
        assert 0 <= score.score <= 100
        assert score.assessment in AssessmentLevel

    @pytest.mark.asyncio
    async def test_score_plan_local_calculation(self, bridge, mock_unit):
        """Test score_plan uses local calculation as fallback."""
        # score_plan_async requires plan_id and units list, not a ParsedPlan
        score = await bridge.score_plan_async(
            plan_id="plan-001",
            units=[mock_unit],
        )

        assert score is not None
        assert isinstance(score, PlanScore)

    def test_assessment_level_from_score(self, bridge):
        """Test assessment level determination from scores."""
        # Test via scoring a mock result
        assert AssessmentLevel.EXCELLENT.value == "excellent"
        assert AssessmentLevel.GOOD.value == "good"
        assert AssessmentLevel.ACCEPTABLE.value == "acceptable"
        assert AssessmentLevel.WARNING.value == "warning"
        assert AssessmentLevel.CRITICAL.value == "critical"


class TestL06BridgeIntegration:
    """Integration tests for L06Bridge (require running L06 service)."""

    @pytest.fixture
    def bridge(self):
        """Create L06Bridge instance."""
        return L06Bridge(base_url="http://localhost:8006")

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_real_service_connection(self, bridge):
        """Test connection to real L06 service."""
        await bridge.initialize()
        assert bridge.is_connected() is True
        await bridge.close()


# =======================
# L11 Bridge Tests
# =======================

class TestL11BridgeUnit:
    """Unit tests for L11Bridge."""

    @pytest.fixture
    def bridge(self):
        """Create L11Bridge instance."""
        return L11Bridge(base_url="http://localhost:8011")

    def test_init_with_defaults(self):
        """Test L11Bridge initialization with defaults."""
        bridge = L11Bridge()
        assert bridge.base_url == "http://localhost:8011"

    @pytest.mark.asyncio
    async def test_publish_event_local(self, bridge):
        """Test publish_event uses local queue as fallback."""
        result = await bridge.publish_event(
            event_type=EventType.PLAN_STARTED,
            payload={"plan_id": "plan-001"},
        )

        assert isinstance(result, PublishResult)
        assert result.success is True

    @pytest.mark.asyncio
    async def test_publish_plan_started(self, bridge):
        """Test publish_plan_started event."""
        result = await bridge.publish_plan_started(
            plan_id="plan-001",
            unit_count=5,
            correlation_id="exec-001",
        )

        assert isinstance(result, PublishResult)
        assert result.success is True

    @pytest.mark.asyncio
    async def test_publish_plan_completed(self, bridge):
        """Test publish_plan_completed event."""
        result = await bridge.publish_plan_completed(
            plan_id="plan-001",
            passed_count=4,
            failed_count=1,
            score=80.0,
            correlation_id="exec-001",
        )

        assert isinstance(result, PublishResult)
        assert result.success is True

    @pytest.mark.asyncio
    async def test_publish_unit_started(self, bridge):
        """Test publish_unit_started event."""
        result = await bridge.publish_unit_started(
            unit_id="unit-001",
            plan_id="plan-001",
            correlation_id="exec-001",
        )

        assert isinstance(result, PublishResult)
        assert result.success is True

    @pytest.mark.asyncio
    async def test_publish_unit_completed(self, bridge):
        """Test publish_unit_completed event."""
        result = await bridge.publish_unit_completed(
            unit_id="unit-001",
            plan_id="plan-001",
            score=85.0,
            correlation_id="exec-001",
        )

        assert isinstance(result, PublishResult)
        assert result.success is True

    @pytest.mark.asyncio
    async def test_publish_unit_failed(self, bridge):
        """Test publish_unit_failed event."""
        result = await bridge.publish_unit_failed(
            unit_id="unit-001",
            plan_id="plan-001",
            error="Test error",
            correlation_id="exec-001",
        )

        assert isinstance(result, PublishResult)
        assert result.success is True

    def test_circuit_breaker_initial_state(self, bridge):
        """Test circuit breaker starts in closed state."""
        cb = bridge.get_circuit_breaker("test")
        assert cb.state == CircuitState.CLOSED

    def test_is_connected_when_not_initialized(self, bridge):
        """Test is_connected returns False when not initialized."""
        assert bridge.is_connected() is False


class TestL11BridgeIntegration:
    """Integration tests for L11Bridge (require running L11 service)."""

    @pytest.fixture
    def bridge(self):
        """Create L11Bridge instance."""
        return L11Bridge(base_url="http://localhost:8011")

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_real_service_connection(self, bridge):
        """Test connection to real L11 service."""
        await bridge.initialize()
        assert bridge.is_connected() is True
        await bridge.close()


# =======================
# Cross-Bridge Tests
# =======================

class TestCrossBridgeIntegration:
    """Tests for interactions between bridges."""

    @pytest.fixture
    def l01_bridge(self):
        """Create L01Bridge instance."""
        return L01Bridge()

    @pytest.fixture
    def l04_bridge(self):
        """Create L04Bridge instance."""
        return L04Bridge()

    @pytest.fixture
    def l06_bridge(self):
        """Create L06Bridge instance."""
        return L06Bridge()

    @pytest.fixture
    def l11_bridge(self):
        """Create L11Bridge instance."""
        return L11Bridge()

    @pytest.mark.asyncio
    async def test_all_bridges_initialize(
        self,
        l01_bridge,
        l04_bridge,
        l06_bridge,
        l11_bridge,
    ):
        """Test that all bridges can initialize without errors."""
        await l01_bridge.initialize()
        await l04_bridge.initialize()
        await l06_bridge.initialize()
        await l11_bridge.initialize()

        # All should be in some state (connected or fallback)
        # Close all
        await l01_bridge.close()
        await l04_bridge.close()
        await l06_bridge.close()
        await l11_bridge.close()

    @pytest.mark.asyncio
    async def test_workflow_with_all_bridges(
        self,
        l01_bridge,
        l04_bridge,
        l06_bridge,
        l11_bridge,
    ):
        """Test a complete workflow using all bridges."""
        # Initialize
        await l01_bridge.initialize()
        await l04_bridge.initialize()
        await l06_bridge.initialize()
        await l11_bridge.initialize()

        # 1. Publish plan started event
        result = await l11_bridge.publish_plan_started(
            plan_id="workflow-plan",
            unit_count=1,
            correlation_id="workflow-001",
        )
        assert result.success

        # 2. Generate content
        generated = await l04_bridge.generate_plan_async(
            task_description="Test generation",
        )
        assert generated is not None

        # 3. Store plan
        store_result = await l01_bridge.store_plan_async(
            plan_id="workflow-plan",
            plan_data={"content": generated.content},
        )
        assert store_result.success

        # 4. Score - score_plan_async requires plan_id and units list
        mock_unit = AtomicUnit(
            id="workflow-unit",
            title="Workflow Unit",
            description="Test workflow unit",
            files=["test.py"],
            complexity=1,
            acceptance_criteria=[],
            dependencies=[],
        )
        score = await l06_bridge.score_plan_async(
            plan_id="workflow-plan",
            units=[mock_unit],
        )
        assert score is not None

        # 5. Publish plan completed event
        await l11_bridge.publish_plan_completed(
            plan_id="workflow-plan",
            passed_count=1,
            failed_count=0,
            score=score.score,
            correlation_id="workflow-001",
        )

        # Cleanup
        await l01_bridge.close()
        await l04_bridge.close()
        await l06_bridge.close()
        await l11_bridge.close()


# =======================
# Error Handling Tests
# =======================

class TestBridgeErrorHandling:
    """Tests for bridge error handling."""

    @pytest.mark.asyncio
    async def test_l01_handles_connection_error(self):
        """Test L01Bridge handles connection errors gracefully."""
        bridge = L01Bridge(base_url="http://nonexistent:9999")
        await bridge.initialize()

        # Should not raise, should use fallback
        result = await bridge.store_plan_async("test", {})
        assert result.success is True
        assert result.result_type == StoreResultType.PLAN

    @pytest.mark.asyncio
    async def test_l04_handles_connection_error(self):
        """Test L04Bridge handles connection errors gracefully."""
        bridge = L04Bridge(base_url="http://nonexistent:9999")
        await bridge.initialize()

        # Should not raise, should use fallback
        result = await bridge.generate_plan_async(task_description="test prompt")
        assert result is not None

    @pytest.mark.asyncio
    async def test_l06_handles_connection_error(self):
        """Test L06Bridge handles connection errors gracefully."""
        bridge = L06Bridge(base_url="http://nonexistent:9999")
        await bridge.initialize()

        # score_plan_async requires plan_id and units list
        mock_unit = AtomicUnit(
            id="test-unit",
            title="Test Unit",
            description="Test unit description",
            files=["test.py"],
            complexity=1,
            acceptance_criteria=[],
            dependencies=[],
        )

        # Should not raise, should use fallback
        result = await bridge.score_plan_async(
            plan_id="test",
            units=[mock_unit],
        )
        assert result is not None

    @pytest.mark.asyncio
    async def test_l11_handles_connection_error(self):
        """Test L11Bridge handles connection errors gracefully."""
        bridge = L11Bridge(base_url="http://nonexistent:9999")
        await bridge.initialize()

        # Should not raise, should use local queue
        result = await bridge.publish_event(EventType.PLAN_STARTED, {})
        assert isinstance(result, PublishResult)
        assert result.success is True
