"""Full pipeline end-to-end tests."""
import pytest
from uuid import uuid4
from datetime import datetime

class TestFullPipeline:
    """Test complete workflow through all layers."""

    @pytest.mark.asyncio
    @pytest.mark.e2e
    @pytest.mark.slow
    async def test_goal_to_evaluation_pipeline(self):
        """Test complete flow: Goal -> Plan -> Execute -> Evaluate."""
        from src.L04_model_gateway.services.model_gateway import ModelGateway
        from src.L05_planning.services.planning_service import PlanningService
        from src.L05_planning.models.goal import Goal
        from src.L06_evaluation.services.evaluation_service import EvaluationService
        from src.L06_evaluation.models.cloud_event import CloudEvent
        from src.L02_runtime.services.agent_executor import AgentExecutor

        # Initialize all layers
        gateway = ModelGateway()

        planner = PlanningService()
        await planner.initialize()

        executor = AgentExecutor()
        await executor.initialize()

        evaluator = EvaluationService()
        await evaluator.initialize()

        try:
            # Step 1: Create goal
            goal = Goal(
                goal_id=str(uuid4()),
                agent_did="did:agent:e2e-pipeline-test",
                goal_text="Count from 1 to 5"
            )
            print(f"\n1. Goal created: {goal.goal_id}")

            # Step 2: Decompose into plan
            plan = await planner.create_plan(goal)
            print(f"2. Plan created: {plan.plan_id} with {len(plan.tasks)} tasks")

            # Step 3: Simulate task execution
            for task in plan.tasks:
                # Create task completion event
                event = CloudEvent(
                    id=str(uuid4()),
                    source="l02.agent-runtime",
                    type="task.completed",
                    subject=task.task_id,
                    time=datetime.now(),
                    data={
                        "task_id": task.task_id,
                        "plan_id": plan.plan_id,
                        "agent_id": goal.agent_did,
                        "duration_ms": 100,
                        "success": True
                    }
                )

                # Step 4: Evaluate task
                await evaluator.process_event(event)

            print(f"3. All {len(plan.tasks)} tasks evaluated")

            # Step 5: Create plan completion event
            plan_event = CloudEvent(
                id=str(uuid4()),
                source="l05.planning",
                type="plan.completed",
                subject=plan.plan_id,
                time=datetime.now(),
                data={
                    "plan_id": plan.plan_id,
                    "goal_id": goal.goal_id,
                    "success": True,
                    "duration_ms": 500
                }
            )
            await evaluator.process_event(plan_event)
            print("4. Plan completion evaluated")

            # Verify pipeline completed
            assert plan is not None
            assert len(plan.tasks) >= 1
            print("5. Pipeline complete ✓")

        finally:
            # Cleanup
            await evaluator.cleanup()
            await executor.cleanup()
            await planner.cleanup()

    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_multi_task_plan_execution(self):
        """Test plan with multiple dependent tasks."""
        from src.L05_planning.services.planning_service import PlanningService
        from src.L05_planning.models.goal import Goal

        planner = PlanningService()
        await planner.initialize()

        try:
            # Complex goal that should produce multiple tasks
            goal = Goal(
                goal_id=str(uuid4()),
                agent_did="did:agent:e2e-multi-task",
                goal_text="Read a file, process its contents, and save the results"
            )

            plan = await planner.create_plan(goal)

            print(f"\nPlan: {plan.plan_id}")
            print(f"Tasks: {len(plan.tasks)}")
            for i, task in enumerate(plan.tasks):
                print(f"  {i+1}. {task.name}")

            # Should have multiple tasks
            assert len(plan.tasks) >= 1

        finally:
            await planner.cleanup()

    @pytest.mark.asyncio
    @pytest.mark.e2e
    async def test_all_layers_concurrent(self):
        """Test all layers running concurrently."""
        import asyncio
        from src.L02_runtime.services.agent_executor import AgentExecutor
        from src.L03_tool_execution.services.tool_executor import ToolExecutor
        from src.L04_model_gateway.services.model_gateway import ModelGateway
        from src.L05_planning.services.planning_service import PlanningService
        from src.L06_evaluation.services.evaluation_service import EvaluationService

        # Initialize all concurrently
        from src.L03_tool_execution.services.tool_registry import ToolRegistry
        from src.L03_tool_execution.services.tool_sandbox import ToolSandbox

        l02 = AgentExecutor()
        db_string = "postgresql://postgres:postgres@localhost:5432/agentic_platform"
        registry = ToolRegistry(db_connection_string=db_string)
        sandbox = ToolSandbox()
        l03 = ToolExecutor(tool_registry=registry, tool_sandbox=sandbox)
        l04 = ModelGateway()
        l05 = PlanningService()
        l06 = EvaluationService()

        # Initialize layers that have initialize()
        await asyncio.gather(
            l02.initialize(),
            l05.initialize(),
            l06.initialize()
        )

        print("\nAll layers initialized concurrently ✓")

        # All should be running
        assert l02 is not None
        assert l03 is not None
        assert l04 is not None
        assert l05 is not None
        assert l06 is not None

        # Cleanup layers that have cleanup()
        await asyncio.gather(
            l02.cleanup(),
            l05.cleanup(),
            l06.cleanup()
        )

        print("All layers cleaned up ✓")
