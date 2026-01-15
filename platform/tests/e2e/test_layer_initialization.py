"""Test that all layers initialize correctly."""
import pytest

class TestLayerInitialization:
    """Verify each layer can be imported and initialized."""

    @pytest.mark.asyncio
    async def test_l02_runtime_imports(self):
        """L02 Agent Runtime imports successfully."""
        from src.L02_runtime import __init__
        from src.L02_runtime.services.agent_executor import AgentExecutor
        from src.L02_runtime.services.session_bridge import SessionBridge
        from src.L02_runtime.services.document_bridge import DocumentBridge
        assert AgentExecutor is not None
        assert SessionBridge is not None
        assert DocumentBridge is not None

    @pytest.mark.asyncio
    async def test_l02_runtime_initializes(self):
        """L02 Agent Runtime initializes without error."""
        from src.L02_runtime.services.agent_executor import AgentExecutor
        executor = AgentExecutor()
        await executor.initialize()
        assert executor is not None
        await executor.cleanup()

    @pytest.mark.asyncio
    async def test_l03_tools_imports(self):
        """L03 Tool Execution imports successfully."""
        from src.L03_tool_execution import __init__
        from src.L03_tool_execution.services.tool_executor import ToolExecutor
        from src.L03_tool_execution.services.tool_registry import ToolRegistry
        assert ToolExecutor is not None
        assert ToolRegistry is not None

    @pytest.mark.asyncio
    async def test_l03_tools_initializes(self):
        """L03 Tool Execution initializes without error."""
        from src.L03_tool_execution.services.tool_executor import ToolExecutor
        from src.L03_tool_execution.services.tool_registry import ToolRegistry
        from src.L03_tool_execution.services.tool_sandbox import ToolSandbox

        db_string = "postgresql://postgres:postgres@localhost:5432/agentic_platform"
        registry = ToolRegistry(db_connection_string=db_string)
        sandbox = ToolSandbox()
        executor = ToolExecutor(tool_registry=registry, tool_sandbox=sandbox)
        assert executor is not None

    @pytest.mark.asyncio
    async def test_l04_gateway_imports(self):
        """L04 Model Gateway imports successfully."""
        from src.L04_model_gateway import __init__
        from src.L04_model_gateway.services.model_gateway import ModelGateway
        from src.L04_model_gateway.services.model_registry import ModelRegistry
        from src.L04_model_gateway.services.llm_router import LLMRouter
        assert ModelGateway is not None
        assert ModelRegistry is not None
        assert LLMRouter is not None

    @pytest.mark.asyncio
    async def test_l04_gateway_initializes(self):
        """L04 Model Gateway initializes without error."""
        from src.L04_model_gateway.services.model_gateway import ModelGateway
        gateway = ModelGateway()
        assert gateway is not None

    @pytest.mark.asyncio
    async def test_l05_planning_imports(self):
        """L05 Planning imports successfully."""
        from src.L05_planning import __init__
        from src.L05_planning.services.planning_service import PlanningService
        from src.L05_planning.services.goal_decomposer import GoalDecomposer
        from src.L05_planning.services.task_orchestrator import TaskOrchestrator
        assert PlanningService is not None
        assert GoalDecomposer is not None
        assert TaskOrchestrator is not None

    @pytest.mark.asyncio
    async def test_l05_planning_initializes(self):
        """L05 Planning initializes without error."""
        from src.L05_planning.services.planning_service import PlanningService
        service = PlanningService()
        await service.initialize()
        assert service is not None
        await service.cleanup()

    @pytest.mark.asyncio
    async def test_l06_evaluation_imports(self):
        """L06 Evaluation imports successfully."""
        from src.L06_evaluation import __init__
        from src.L06_evaluation.services.evaluation_service import EvaluationService
        from src.L06_evaluation.services.quality_scorer import QualityScorer
        from src.L06_evaluation.services.metrics_engine import MetricsEngine
        assert EvaluationService is not None
        assert QualityScorer is not None
        assert MetricsEngine is not None

    @pytest.mark.asyncio
    async def test_l06_evaluation_initializes(self):
        """L06 Evaluation initializes without error."""
        from src.L06_evaluation.services.evaluation_service import EvaluationService
        service = EvaluationService()
        await service.initialize()
        assert service is not None
        await service.cleanup()

    @pytest.mark.asyncio
    async def test_all_layers_initialize_together(self):
        """All layers can be initialized simultaneously."""
        from src.L02_runtime.services.agent_executor import AgentExecutor
        from src.L03_tool_execution.services.tool_executor import ToolExecutor
        from src.L03_tool_execution.services.tool_registry import ToolRegistry
        from src.L03_tool_execution.services.tool_sandbox import ToolSandbox
        from src.L04_model_gateway.services.model_gateway import ModelGateway
        from src.L05_planning.services.planning_service import PlanningService
        from src.L06_evaluation.services.evaluation_service import EvaluationService

        l02 = AgentExecutor()
        db_string = "postgresql://postgres:postgres@localhost:5432/agentic_platform"
        registry = ToolRegistry(db_connection_string=db_string)
        sandbox = ToolSandbox()
        l03 = ToolExecutor(tool_registry=registry, tool_sandbox=sandbox)
        l04 = ModelGateway()
        l05 = PlanningService()
        l06 = EvaluationService()

        # Initialize layers that have initialize()
        await l02.initialize()
        await l05.initialize()
        await l06.initialize()

        # Verify all exist
        assert l02 is not None
        assert l03 is not None
        assert l04 is not None
        assert l05 is not None
        assert l06 is not None

        # Cleanup layers that have cleanup()
        await l06.cleanup()
        await l05.cleanup()
        await l02.cleanup()
