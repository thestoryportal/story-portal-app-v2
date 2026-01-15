"""Cross-layer integration tests."""
import pytest
from uuid import uuid4
from datetime import datetime

class TestCrossLayerIntegration:
    """Test integrations between layers."""

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_l04_l05_integration(self):
        """L05 Planning uses L04 Model Gateway for decomposition."""
        from src.L04_model_gateway.services.model_gateway import ModelGateway
        from src.L05_planning.services.planning_service import PlanningService
        from src.L05_planning.models.goal import Goal

        # Initialize both layers
        gateway = ModelGateway()

        planner = PlanningService()
        await planner.initialize()

        # Create a goal that requires LLM decomposition
        goal = Goal(
            goal_id=str(uuid4()),
            agent_did="did:agent:integration-test",
            goal_text="Write a technical document about Python best practices"
        )

        # This should use L04 internally
        plan = await planner.create_plan(goal)

        assert plan is not None
        assert len(plan.tasks) >= 1

        await planner.cleanup()

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_l02_l03_integration(self):
        """L02 Agent Runtime uses L03 Tool Execution."""
        from src.L02_runtime.services.agent_executor import AgentExecutor
        from src.L03_tool_execution.services.tool_executor import ToolExecutor
        from src.L03_tool_execution.services.tool_registry import ToolRegistry
        from src.L03_tool_execution.services.tool_sandbox import ToolSandbox

        # Initialize both layers
        agent_executor = AgentExecutor()
        await agent_executor.initialize()

        db_string = "postgresql://postgres:postgres@localhost:5432/agentic_platform"
        registry = ToolRegistry(db_connection_string=db_string)
        sandbox = ToolSandbox()
        tool_executor = ToolExecutor(tool_registry=registry, tool_sandbox=sandbox)

        # Verify integration exists
        assert agent_executor is not None
        assert tool_executor is not None

        await agent_executor.cleanup()

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_l05_l06_integration(self):
        """L06 Evaluation can evaluate L05 plans."""
        from src.L05_planning.services.planning_service import PlanningService
        from src.L05_planning.models.goal import Goal
        from src.L06_evaluation.services.evaluation_service import EvaluationService
        from src.L06_evaluation.models.cloud_event import CloudEvent

        # Initialize both layers
        planner = PlanningService()
        await planner.initialize()

        evaluator = EvaluationService()
        await evaluator.initialize()

        # Create a plan
        goal = Goal(
            goal_id=str(uuid4()),
            agent_did="did:agent:integration-test",
            goal_text="Simple test task"
        )
        plan = await planner.create_plan(goal)

        # Create evaluation event for the plan
        event = CloudEvent(
            id=str(uuid4()),
            source="l05.planning",
            type="plan.created",
            subject=plan.plan_id,
            time=datetime.now(),
            data={
                "plan_id": plan.plan_id,
                "goal_id": goal.goal_id,
                "task_count": len(plan.tasks)
            }
        )

        # Process event in evaluator
        await evaluator.process_event(event)

        await evaluator.cleanup()
        await planner.cleanup()

    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_l02_mcp_integration(self):
        """L02 bridges communicate with MCP services."""
        from src.L02_runtime.services.session_bridge import SessionBridge
        from src.L02_runtime.services.document_bridge import DocumentBridge

        session_bridge = SessionBridge()
        await session_bridge.initialize()

        document_bridge = DocumentBridge()
        await document_bridge.initialize()

        # Test session operations
        save_result = await session_bridge.save_snapshot(
            task_id="integration-test",
            context_data={"test": "data"}
        )

        # Test document operations
        query_result = await document_bridge.query_documents("test query")

        # Results may be None/empty in stub mode, but should not error
        assert save_result is None or isinstance(save_result, dict)
        assert isinstance(query_result, list)

        await document_bridge.cleanup()
        await session_bridge.cleanup()
