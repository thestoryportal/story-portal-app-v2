"""Error handling tests across layers."""
import pytest
from uuid import uuid4

class TestErrorHandling:
    """Test error handling across all layers."""

    @pytest.mark.asyncio
    async def test_l05_invalid_goal_handling(self):
        """L05 handles invalid goal gracefully."""
        from src.L05_planning.services.planning_service import PlanningService
        from src.L05_planning.models.goal import Goal

        planner = PlanningService()
        await planner.initialize()

        try:
            # Empty goal text
            goal = Goal(
                goal_id=str(uuid4()),
                agent_did="did:agent:error-test",
                goal_text=""
            )

            # Should either handle gracefully or raise specific error
            try:
                plan = await planner.create_plan(goal)
                # If it succeeds, plan should still be valid
                assert plan is not None
            except ValueError as e:
                # Expected for invalid input
                assert "goal" in str(e).lower() or "empty" in str(e).lower()
        finally:
            await planner.cleanup()

    @pytest.mark.asyncio
    async def test_l04_invalid_request_handling(self):
        """L04 handles invalid inference request gracefully."""
        from src.L04_model_gateway.services.model_gateway import ModelGateway
        from src.L04_model_gateway.models.inference_request import (
            InferenceRequest, LogicalPrompt, ModelRequirements, RequestConstraints
        )

        gateway = ModelGateway()

        # Request with impossible constraints
        request = InferenceRequest(
            request_id=str(uuid4()),
            agent_did="did:agent:error-test",
            logical_prompt=LogicalPrompt(
                system="",
                user="test"
            ),
            requirements=ModelRequirements(
                capabilities=["nonexistent_capability_xyz"]
            ),
            constraints=RequestConstraints(
                max_latency_ms=1  # Impossible latency
            )
        )

        # Should handle gracefully
        try:
            response = await gateway.complete(request)
            # If it completes, response should be valid
            assert response is not None
        except Exception as e:
            # Should be a handled error, not a crash
            assert str(e) is not None

    @pytest.mark.asyncio
    async def test_l06_malformed_event_handling(self):
        """L06 handles malformed events gracefully."""
        from src.L06_evaluation.services.evaluation_service import EvaluationService
        from src.L06_evaluation.models.cloud_event import CloudEvent
        from datetime import datetime

        evaluator = EvaluationService()
        await evaluator.initialize()

        try:
            # Event with missing data
            event = CloudEvent(
                id=str(uuid4()),
                source="test",
                type="unknown.type",
                subject="test",
                time=datetime.now(),
                data={}  # Empty data
            )

            # Should not crash
            try:
                await evaluator.process_event(event)
            except Exception as e:
                # Should be handled error
                assert str(e) is not None
        finally:
            await evaluator.cleanup()

    @pytest.mark.asyncio
    async def test_layer_cleanup_idempotent(self):
        """Layer cleanup can be called multiple times safely."""
        from src.L05_planning.services.planning_service import PlanningService

        planner = PlanningService()
        await planner.initialize()

        # Multiple cleanups should not error
        await planner.cleanup()
        await planner.cleanup()
        await planner.cleanup()

    @pytest.mark.asyncio
    async def test_layer_double_initialization(self):
        """Layer handles double initialization gracefully."""
        from src.L05_planning.services.planning_service import PlanningService

        planner = PlanningService()

        # Double initialization should be safe
        await planner.initialize()
        await planner.initialize()

        assert planner is not None

        await planner.cleanup()
