"""Performance tests for all layers."""
import pytest
import asyncio
import time
from uuid import uuid4

class TestPerformance:
    """Test performance characteristics of all layers."""

    @pytest.mark.asyncio
    async def test_layer_initialization_time(self):
        """All layers initialize within acceptable time."""
        from src.L02_runtime.services.agent_executor import AgentExecutor
        from src.L03_tool_execution.services.tool_executor import ToolExecutor
        from src.L04_model_gateway.services.model_gateway import ModelGateway
        from src.L05_planning.services.planning_service import PlanningService
        from src.L06_evaluation.services.evaluation_service import EvaluationService

        max_init_time = 5.0  # seconds per layer

        from src.L03_tool_execution.services.tool_registry import ToolRegistry
        from src.L03_tool_execution.services.tool_sandbox import ToolSandbox

        layers_with_init = [
            ("L02", AgentExecutor()),
            ("L05", PlanningService()),
            ("L06", EvaluationService()),
        ]

        db_string = "postgresql://postgres:postgres@localhost:5432/agentic_platform"

        layers_without_init = [
            ("L03", lambda: ToolExecutor(tool_registry=ToolRegistry(db_connection_string=db_string), tool_sandbox=ToolSandbox())),
            ("L04", ModelGateway),
        ]

        results = []

        # Test layers with initialize()
        for name, layer in layers_with_init:
            start = time.time()
            await layer.initialize()
            elapsed = time.time() - start
            results.append((name, elapsed))
            await layer.cleanup()

        # Test layers without initialize() - just measure construction
        for name, layer_factory in layers_without_init:
            start = time.time()
            layer = layer_factory()
            elapsed = time.time() - start
            results.append((name, elapsed))

        print("\nInitialization times:")
        for name, elapsed in results:
            status = "✓" if elapsed < max_init_time else "✗"
            print(f"  {name}: {elapsed:.3f}s {status}")

        # All should initialize within limit
        for name, elapsed in results:
            assert elapsed < max_init_time, f"{name} took {elapsed:.3f}s"

    @pytest.mark.asyncio
    async def test_plan_creation_latency(self):
        """Plan creation completes within acceptable time."""
        from src.L05_planning.services.planning_service import PlanningService
        from src.L05_planning.models.goal import Goal

        planner = PlanningService()
        await planner.initialize()

        max_latency = 30.0  # seconds (includes LLM call)

        try:
            goal = Goal(
                goal_id=str(uuid4()),
                agent_did="did:agent:perf-test",
                goal_text="Simple test task"
            )

            start = time.time()
            plan = await planner.create_plan(goal)
            elapsed = time.time() - start

            print(f"\nPlan creation: {elapsed:.3f}s")

            assert elapsed < max_latency, f"Plan creation took {elapsed:.3f}s"
            assert plan is not None

        finally:
            await planner.cleanup()

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_concurrent_plan_creation(self):
        """Multiple plans can be created concurrently."""
        from src.L05_planning.services.planning_service import PlanningService
        from src.L05_planning.models.goal import Goal

        planner = PlanningService()
        await planner.initialize()

        num_concurrent = 3
        max_total_time = 60.0  # seconds

        try:
            goals = [
                Goal(
                    goal_id=str(uuid4()),
                    agent_did=f"did:agent:concurrent-{i}",
                    goal_text=f"Test task number {i}"
                )
                for i in range(num_concurrent)
            ]

            start = time.time()
            plans = await asyncio.gather(
                *[planner.create_plan(g) for g in goals]
            )
            elapsed = time.time() - start

            print(f"\n{num_concurrent} concurrent plans: {elapsed:.3f}s")

            assert elapsed < max_total_time
            assert len(plans) == num_concurrent
            assert all(p is not None for p in plans)

        finally:
            await planner.cleanup()

    @pytest.mark.asyncio
    async def test_event_processing_throughput(self):
        """L06 can process events at acceptable rate."""
        from src.L06_evaluation.services.evaluation_service import EvaluationService
        from src.L06_evaluation.models.cloud_event import CloudEvent
        from datetime import datetime

        evaluator = EvaluationService()
        await evaluator.initialize()

        num_events = 100
        max_time = 5.0  # seconds

        try:
            events = [
                CloudEvent(
                    id=str(uuid4()),
                    source="perf-test",
                    type="task.completed",
                    subject=f"task-{i}",
                    time=datetime.now(),
                    data={"task_id": str(i), "success": True}
                )
                for i in range(num_events)
            ]

            start = time.time()
            for event in events:
                await evaluator.process_event(event)
            elapsed = time.time() - start

            throughput = num_events / elapsed
            print(f"\nEvent throughput: {throughput:.1f} events/sec")

            assert elapsed < max_time, f"Processing {num_events} events took {elapsed:.3f}s"

        finally:
            await evaluator.cleanup()

    @pytest.mark.asyncio
    @pytest.mark.slow
    @pytest.mark.integration
    async def test_llm_completion_latency(self):
        """LLM completion via L04 completes within acceptable time."""
        from src.L04_model_gateway.services.model_gateway import ModelGateway
        from src.L04_model_gateway.models.inference_request import (
            InferenceRequest, LogicalPrompt, ModelRequirements, RequestConstraints
        )

        gateway = ModelGateway()

        max_latency = 30.0  # seconds (Ollama can be slow)

        request = InferenceRequest(
            request_id=str(uuid4()),
            agent_did="did:agent:latency-test",
            logical_prompt=LogicalPrompt(
                system="You are a helpful assistant.",
                user="Say 'test' and nothing else."
            ),
            requirements=ModelRequirements(capabilities=[]),
            constraints=RequestConstraints(max_latency_ms=30000)
        )

        start = time.time()
        response = await gateway.complete(request)
        elapsed = time.time() - start

        print(f"\nLLM completion: {elapsed:.3f}s")
        print(f"Response length: {len(response.content)} chars")

        assert elapsed < max_latency
        assert response is not None
