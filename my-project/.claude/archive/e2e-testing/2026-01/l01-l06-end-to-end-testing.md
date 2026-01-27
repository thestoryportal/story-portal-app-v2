Create comprehensive E2E test suite for L01-L06 layers: Autonomous end-to-end sprint.

## CRITICAL ENVIRONMENT CONSTRAINTS

READ THESE FIRST - DO NOT VIOLATE:

1. DO NOT create docker-compose files - infrastructure ALREADY RUNNING
2. DO NOT create virtual environments (venv) - use system Python
3. DO NOT run docker-compose up - services ALREADY RUNNING
4. ALWAYS use: pip install <package> --break-system-packages
5. OUTPUT directory: /Volumes/Extreme SSD/projects/story-portal-app/platform/tests/e2e/

## Running Infrastructure

| Service | Host | Port | Status |
|---------|------|------|--------|
| PostgreSQL | localhost | 5432 | Running |
| Redis | localhost | 6379 | Running |
| Ollama | localhost | 11434 | Running |
| MCP context-orchestrator | PM2 | stdio | Running |
| MCP document-consolidator | PM2 | stdio | Running |

Verify: docker ps | grep agentic && pm2 status

## Layer Locations

| Layer | Path | Purpose |
|-------|------|---------|
| L02 Agent Runtime | platform/src/L02_runtime/ | Agent execution, lifecycle, MCP bridges |
| L03 Tool Execution | platform/src/L03_tool_execution/ | Tool registry, sandbox, execution |
| L04 Model Gateway | platform/src/L04_model_gateway/ | LLM routing, caching, providers |
| L05 Planning | platform/src/L05_planning/ | Goal decomposition, task orchestration |
| L06 Evaluation | platform/src/L06_evaluation/ | Quality scoring, metrics, anomalies |

## Objective

Create a comprehensive E2E test suite that validates:
1. Each layer initializes correctly
2. Each layer's core functions work
3. Cross-layer integrations work
4. Full pipeline flows complete successfully
5. Error handling works across layers
6. Performance meets basic thresholds

## Output Structure

Create these directories and files:

Root: platform/tests/e2e/
  - __init__.py
  - conftest.py (shared fixtures, pytest configuration)
  - pytest.ini (pytest settings)
  - README.md (test documentation)
  - run_tests.sh (test runner script)
  - RESULTS.md (test results summary - generated after run)

Test files:
  - test_layer_initialization.py
  - test_l02_runtime.py
  - test_l03_tools.py
  - test_l04_gateway.py
  - test_l05_planning.py
  - test_l06_evaluation.py
  - test_cross_layer_integration.py
  - test_full_pipeline.py
  - test_error_handling.py
  - test_performance.py

Utilities:
  - utils/__init__.py
  - utils/fixtures.py (reusable test data)
  - utils/helpers.py (test helper functions)
  - utils/mocks.py (mock objects)
  - utils/assertions.py (custom assertions)

## Phase 1: Test Infrastructure

### conftest.py
```python
import pytest
import asyncio
import sys
import os
from pathlib import Path
from datetime import datetime

# Add platform to path
PLATFORM_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PLATFORM_ROOT))

# Pytest configuration
def pytest_configure(config):
    config.addinivalue_line("markers", "slow: marks tests as slow")
    config.addinivalue_line("markers", "integration: marks integration tests")
    config.addinivalue_line("markers", "e2e: marks end-to-end tests")

@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="session")
async def infrastructure_check():
    """Verify infrastructure is running."""
    import redis
    import psycopg2
    import httpx
    
    checks = {}
    
    # Redis
    try:
        r = redis.Redis(host='localhost', port=6379)
        r.ping()
        checks['redis'] = True
    except Exception as e:
        checks['redis'] = str(e)
    
    # PostgreSQL
    try:
        conn = psycopg2.connect(
            host='localhost',
            port=5432,
            user='postgres',
            password='postgres',
            database='agentic_platform'
        )
        conn.close()
        checks['postgresql'] = True
    except Exception as e:
        checks['postgresql'] = str(e)
    
    # Ollama
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get('http://localhost:11434/api/tags', timeout=5.0)
            checks['ollama'] = resp.status_code == 200
    except Exception as e:
        checks['ollama'] = str(e)
    
    return checks

@pytest.fixture(autouse=True)
async def test_timeout():
    """Ensure tests don't hang."""
    yield
    await asyncio.sleep(0)  # Allow cleanup

@pytest.fixture
def test_agent_did():
    """Standard test agent DID."""
    return "did:agent:e2e-test-agent"

@pytest.fixture
def test_timestamp():
    """Current timestamp for tests."""
    return datetime.now()
```

### pytest.ini
```ini
[pytest]
testpaths = .
python_files = test_*.py
python_classes = Test*
python_functions = test_*
asyncio_mode = auto
timeout = 60
timeout_method = thread
markers =
    slow: marks tests as slow (deselect with '-m "not slow"')
    integration: marks tests requiring external services
    e2e: marks full end-to-end tests
addopts = -v --tb=short --strict-markers
filterwarnings =
    ignore::DeprecationWarning
```

### run_tests.sh
```bash
#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLATFORM_DIR="$(dirname "$(dirname "$SCRIPT_DIR")")"

cd "$PLATFORM_DIR"

echo "=========================================="
echo "L01-L06 End-to-End Test Suite"
echo "=========================================="
echo "Started: $(date)"
echo ""

# Check infrastructure
echo "Checking infrastructure..."
docker ps | grep -q agentic-postgres && echo "  ✓ PostgreSQL" || echo "  ✗ PostgreSQL NOT RUNNING"
docker ps | grep -q agentic-redis && echo "  ✓ Redis" || echo "  ✗ Redis NOT RUNNING"
curl -s localhost:11434/api/tags > /dev/null && echo "  ✓ Ollama" || echo "  ✗ Ollama NOT RUNNING"
echo ""

# Run tests by category
echo "Running tests..."
echo ""

echo "--- Layer Initialization Tests ---"
python3 -m pytest tests/e2e/test_layer_initialization.py -v --timeout=30 2>&1 | tee -a tests/e2e/RESULTS.md

echo ""
echo "--- L02 Runtime Tests ---"
python3 -m pytest tests/e2e/test_l02_runtime.py -v --timeout=60 2>&1 | tee -a tests/e2e/RESULTS.md

echo ""
echo "--- L03 Tool Tests ---"
python3 -m pytest tests/e2e/test_l03_tools.py -v --timeout=60 2>&1 | tee -a tests/e2e/RESULTS.md

echo ""
echo "--- L04 Gateway Tests ---"
python3 -m pytest tests/e2e/test_l04_gateway.py -v --timeout=60 2>&1 | tee -a tests/e2e/RESULTS.md

echo ""
echo "--- L05 Planning Tests ---"
python3 -m pytest tests/e2e/test_l05_planning.py -v --timeout=60 2>&1 | tee -a tests/e2e/RESULTS.md

echo ""
echo "--- L06 Evaluation Tests ---"
python3 -m pytest tests/e2e/test_l06_evaluation.py -v --timeout=60 2>&1 | tee -a tests/e2e/RESULTS.md

echo ""
echo "--- Cross-Layer Integration Tests ---"
python3 -m pytest tests/e2e/test_cross_layer_integration.py -v --timeout=120 2>&1 | tee -a tests/e2e/RESULTS.md

echo ""
echo "--- Full Pipeline Tests ---"
python3 -m pytest tests/e2e/test_full_pipeline.py -v --timeout=180 2>&1 | tee -a tests/e2e/RESULTS.md

echo ""
echo "--- Error Handling Tests ---"
python3 -m pytest tests/e2e/test_error_handling.py -v --timeout=60 2>&1 | tee -a tests/e2e/RESULTS.md

echo ""
echo "--- Performance Tests ---"
python3 -m pytest tests/e2e/test_performance.py -v -m "not slow" --timeout=120 2>&1 | tee -a tests/e2e/RESULTS.md

echo ""
echo "=========================================="
echo "Test Suite Complete: $(date)"
echo "=========================================="

# Summary
python3 -m pytest tests/e2e/ --collect-only -q 2>/dev/null | tail -1
```

## Phase 2: Layer Initialization Tests

### test_layer_initialization.py
```python
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
        executor = ToolExecutor()
        await executor.initialize()
        assert executor is not None
        await executor.cleanup()
    
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
        await gateway.initialize()
        assert gateway is not None
        await gateway.cleanup()
    
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
        from src.L04_model_gateway.services.model_gateway import ModelGateway
        from src.L05_planning.services.planning_service import PlanningService
        from src.L06_evaluation.services.evaluation_service import EvaluationService
        
        l02 = AgentExecutor()
        l03 = ToolExecutor()
        l04 = ModelGateway()
        l05 = PlanningService()
        l06 = EvaluationService()
        
        # Initialize all
        await l02.initialize()
        await l03.initialize()
        await l04.initialize()
        await l05.initialize()
        await l06.initialize()
        
        # Verify all running
        assert l02 is not None
        assert l03 is not None
        assert l04 is not None
        assert l05 is not None
        assert l06 is not None
        
        # Cleanup all
        await l06.cleanup()
        await l05.cleanup()
        await l04.cleanup()
        await l03.cleanup()
        await l02.cleanup()
```

## Phase 3: Individual Layer Tests

### test_l02_runtime.py
```python
"""L02 Agent Runtime layer tests."""
import pytest
from datetime import datetime

class TestL02AgentRuntime:
    """Test L02 Agent Runtime functionality."""
    
    @pytest.fixture
    async def executor(self):
        """Initialize agent executor."""
        from src.L02_runtime.services.agent_executor import AgentExecutor
        executor = AgentExecutor()
        await executor.initialize()
        yield executor
        await executor.cleanup()
    
    @pytest.fixture
    async def session_bridge(self):
        """Initialize session bridge."""
        from src.L02_runtime.services.session_bridge import SessionBridge
        bridge = SessionBridge()
        await bridge.initialize()
        yield bridge
        await bridge.cleanup()
    
    @pytest.fixture
    async def document_bridge(self):
        """Initialize document bridge."""
        from src.L02_runtime.services.document_bridge import DocumentBridge
        bridge = DocumentBridge()
        await bridge.initialize()
        yield bridge
        await bridge.cleanup()
    
    @pytest.mark.asyncio
    async def test_executor_initialization(self, executor):
        """Executor initializes correctly."""
        assert executor is not None
    
    @pytest.mark.asyncio
    async def test_session_bridge_connection(self, session_bridge):
        """Session bridge connects to MCP."""
        # Connection may be stub mode, but should not error
        assert session_bridge is not None
    
    @pytest.mark.asyncio
    async def test_document_bridge_connection(self, document_bridge):
        """Document bridge connects to MCP."""
        # Connection may be stub mode, but should not error
        assert document_bridge is not None
    
    @pytest.mark.asyncio
    async def test_session_save_snapshot(self, session_bridge):
        """Session bridge can save context snapshot."""
        result = await session_bridge.save_snapshot(
            task_id="test-task-001",
            context_data={"key": "value", "timestamp": str(datetime.now())}
        )
        # Result may be None in stub mode, but should not error
        assert result is None or isinstance(result, dict)
    
    @pytest.mark.asyncio
    async def test_session_get_context(self, session_bridge):
        """Session bridge can retrieve context."""
        result = await session_bridge.get_unified_context(task_id="test-task-001")
        # Result may be None in stub mode
        assert result is None or isinstance(result, dict)
    
    @pytest.mark.asyncio
    async def test_document_query(self, document_bridge):
        """Document bridge can query documents."""
        result = await document_bridge.query_documents(query="architecture")
        # Result may be empty list in stub mode
        assert isinstance(result, list)
    
    @pytest.mark.asyncio
    async def test_document_find_source(self, document_bridge):
        """Document bridge can find source of truth."""
        result = await document_bridge.find_source_of_truth(query="specification")
        # Result may be None in stub mode
        assert result is None or isinstance(result, dict)
```

### test_l03_tools.py
```python
"""L03 Tool Execution layer tests."""
import pytest

class TestL03ToolExecution:
    """Test L03 Tool Execution functionality."""
    
    @pytest.fixture
    async def tool_executor(self):
        """Initialize tool executor."""
        from src.L03_tool_execution.services.tool_executor import ToolExecutor
        executor = ToolExecutor()
        await executor.initialize()
        yield executor
        await executor.cleanup()
    
    @pytest.fixture
    async def tool_registry(self):
        """Initialize tool registry."""
        from src.L03_tool_execution.services.tool_registry import ToolRegistry
        registry = ToolRegistry()
        await registry.initialize()
        yield registry
        await registry.cleanup()
    
    @pytest.mark.asyncio
    async def test_registry_initialization(self, tool_registry):
        """Tool registry initializes correctly."""
        assert tool_registry is not None
    
    @pytest.mark.asyncio
    async def test_executor_initialization(self, tool_executor):
        """Tool executor initializes correctly."""
        assert tool_executor is not None
    
    @pytest.mark.asyncio
    async def test_list_available_tools(self, tool_registry):
        """Can list available tools."""
        tools = await tool_registry.list_tools()
        assert isinstance(tools, list)
    
    @pytest.mark.asyncio
    async def test_get_tool_by_name(self, tool_registry):
        """Can get tool by name."""
        # First list tools to get a valid name
        tools = await tool_registry.list_tools()
        if tools:
            tool_name = tools[0].name if hasattr(tools[0], 'name') else tools[0].get('name')
            if tool_name:
                tool = await tool_registry.get_tool(tool_name)
                assert tool is not None
    
    @pytest.mark.asyncio
    async def test_execute_mock_tool(self, tool_executor):
        """Can execute a mock tool."""
        # This test depends on available tools
        # If no tools registered, skip gracefully
        try:
            result = await tool_executor.execute(
                tool_name="echo",  # Common test tool
                arguments={"message": "test"}
            )
            assert result is not None
        except Exception as e:
            # Tool may not exist, which is acceptable
            pytest.skip(f"Echo tool not available: {e}")
```

### test_l04_gateway.py
```python
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
        await gateway.initialize()
        yield gateway
        await gateway.cleanup()
    
    @pytest.fixture
    async def model_registry(self):
        """Initialize model registry."""
        from src.L04_model_gateway.services.model_registry import ModelRegistry
        registry = ModelRegistry()
        await registry.initialize()
        yield registry
        await registry.cleanup()
    
    @pytest.fixture
    async def llm_router(self):
        """Initialize LLM router."""
        from src.L04_model_gateway.services.llm_router import LLMRouter
        router = LLMRouter()
        await router.initialize()
        yield router
        await router.cleanup()
    
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
        await cache.initialize()
        
        # Cache operations may be stubbed
        assert cache is not None
        
        await cache.cleanup()
    
    @pytest.mark.asyncio
    async def test_rate_limiter(self, gateway):
        """Rate limiter tracks requests."""
        from src.L04_model_gateway.services.rate_limiter import RateLimiter
        limiter = RateLimiter()
        
        allowed = await limiter.check_limit(agent_id="test-agent", tokens=100)
        assert isinstance(allowed, bool)
```

### test_l05_planning.py
```python
"""L05 Planning layer tests."""
import pytest
from uuid import uuid4

class TestL05Planning:
    """Test L05 Planning functionality."""
    
    @pytest.fixture
    async def planning_service(self):
        """Initialize planning service."""
        from src.L05_planning.services.planning_service import PlanningService
        service = PlanningService()
        await service.initialize()
        yield service
        await service.cleanup()
    
    @pytest.fixture
    async def goal_decomposer(self):
        """Initialize goal decomposer."""
        from src.L05_planning.services.goal_decomposer import GoalDecomposer
        decomposer = GoalDecomposer()
        await decomposer.initialize()
        yield decomposer
        await decomposer.cleanup()
    
    @pytest.fixture
    async def dependency_resolver(self):
        """Initialize dependency resolver."""
        from src.L05_planning.services.dependency_resolver import DependencyResolver
        resolver = DependencyResolver()
        yield resolver
    
    @pytest.fixture
    def sample_goal(self):
        """Create sample goal for testing."""
        from src.L05_planning.models.goal import Goal
        return Goal(
            goal_id=str(uuid4()),
            agent_did="did:agent:e2e-test",
            goal_text="List files in the current directory"
        )
    
    @pytest.mark.asyncio
    async def test_planning_service_initialization(self, planning_service):
        """Planning service initializes correctly."""
        assert planning_service is not None
    
    @pytest.mark.asyncio
    async def test_goal_decomposer_initialization(self, goal_decomposer):
        """Goal decomposer initializes correctly."""
        assert goal_decomposer is not None
    
    @pytest.mark.asyncio
    async def test_create_simple_plan(self, planning_service, sample_goal):
        """Can create a plan from a simple goal."""
        plan = await planning_service.create_plan(sample_goal)
        
        assert plan is not None
        assert plan.plan_id is not None
        assert plan.goal_id == sample_goal.goal_id
        assert len(plan.tasks) >= 1
    
    @pytest.mark.asyncio
    async def test_plan_has_tasks(self, planning_service, sample_goal):
        """Created plan contains tasks."""
        plan = await planning_service.create_plan(sample_goal)
        
        assert plan.tasks is not None
        assert isinstance(plan.tasks, list)
        for task in plan.tasks:
            assert task.task_id is not None
            assert task.name is not None
    
    @pytest.mark.asyncio
    async def test_dependency_cycle_detection(self, dependency_resolver):
        """Dependency resolver detects cycles."""
        from src.L05_planning.models.task import Task, TaskDependency
        
        # Create tasks with circular dependency
        task_a = Task(task_id="a", name="Task A", dependencies=[
            TaskDependency(task_id="b", dependency_type="blocking")
        ])
        task_b = Task(task_id="b", name="Task B", dependencies=[
            TaskDependency(task_id="a", dependency_type="blocking")
        ])
        
        has_cycle = await dependency_resolver.detect_cycle([task_a, task_b])
        assert has_cycle is True
    
    @pytest.mark.asyncio
    async def test_topological_sort(self, dependency_resolver):
        """Dependency resolver produces valid topological order."""
        from src.L05_planning.models.task import Task, TaskDependency
        
        # Create tasks with valid dependencies: A -> B -> C
        task_a = Task(task_id="a", name="Task A", dependencies=[])
        task_b = Task(task_id="b", name="Task B", dependencies=[
            TaskDependency(task_id="a", dependency_type="blocking")
        ])
        task_c = Task(task_id="c", name="Task C", dependencies=[
            TaskDependency(task_id="b", dependency_type="blocking")
        ])
        
        order = await dependency_resolver.topological_sort([task_a, task_b, task_c])
        
        # A should come before B, B before C
        assert order.index("a") < order.index("b")
        assert order.index("b") < order.index("c")
    
    @pytest.mark.asyncio
    async def test_plan_validation(self, planning_service, sample_goal):
        """Created plans pass validation."""
        from src.L05_planning.services.plan_validator import PlanValidator
        
        plan = await planning_service.create_plan(sample_goal)
        validator = PlanValidator()
        
        result = await validator.validate(plan)
        assert result.valid is True or len(result.errors) >= 0
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_goal_decomposition_with_llm(self, planning_service):
        """Goal decomposition uses L04 for LLM-based decomposition."""
        from src.L05_planning.models.goal import Goal
        
        complex_goal = Goal(
            goal_id=str(uuid4()),
            agent_did="did:agent:e2e-test",
            goal_text="Create a summary report of the project status including milestones, risks, and next steps"
        )
        
        plan = await planning_service.create_plan(complex_goal)
        
        # Complex goal should produce multiple tasks
        assert len(plan.tasks) >= 1
```

### test_l06_evaluation.py
```python
"""L06 Evaluation layer tests."""
import pytest
from datetime import datetime, timedelta
from uuid import uuid4

class TestL06Evaluation:
    """Test L06 Evaluation functionality."""
    
    @pytest.fixture
    async def evaluation_service(self):
        """Initialize evaluation service."""
        from src.L06_evaluation.services.evaluation_service import EvaluationService
        service = EvaluationService()
        await service.initialize()
        yield service
        await service.cleanup()
    
    @pytest.fixture
    async def quality_scorer(self):
        """Initialize quality scorer."""
        from src.L06_evaluation.services.quality_scorer import QualityScorer
        scorer = QualityScorer()
        await scorer.initialize()
        yield scorer
        await scorer.cleanup()
    
    @pytest.fixture
    async def metrics_engine(self):
        """Initialize metrics engine."""
        from src.L06_evaluation.services.metrics_engine import MetricsEngine
        engine = MetricsEngine()
        await engine.initialize()
        yield engine
        await engine.cleanup()
    
    @pytest.fixture
    def sample_cloud_event(self):
        """Create sample CloudEvent for testing."""
        from src.L06_evaluation.models.cloud_event import CloudEvent
        return CloudEvent(
            id=str(uuid4()),
            source="l02.agent-runtime",
            type="task.completed",
            subject=f"task-{uuid4()}",
            time=datetime.now(),
            data={
                "agent_id": "agent-001",
                "task_id": str(uuid4()),
                "duration_ms": 1500,
                "success": True,
                "token_count": 250
            }
        )
    
    @pytest.mark.asyncio
    async def test_evaluation_service_initialization(self, evaluation_service):
        """Evaluation service initializes correctly."""
        assert evaluation_service is not None
    
    @pytest.mark.asyncio
    async def test_quality_scorer_initialization(self, quality_scorer):
        """Quality scorer initializes correctly."""
        assert quality_scorer is not None
    
    @pytest.mark.asyncio
    async def test_metrics_engine_initialization(self, metrics_engine):
        """Metrics engine initializes correctly."""
        assert metrics_engine is not None
    
    @pytest.mark.asyncio
    async def test_process_cloud_event(self, evaluation_service, sample_cloud_event):
        """Can process a CloudEvent."""
        await evaluation_service.process_event(sample_cloud_event)
        # Should not raise exception
    
    @pytest.mark.asyncio
    async def test_quality_score_computation(self, quality_scorer):
        """Can compute quality scores."""
        score = await quality_scorer.compute_score(
            agent_id="agent-001",
            tenant_id="tenant-001",
            time_window=(datetime.now() - timedelta(hours=1), datetime.now())
        )
        
        # Score may be None if no data, or a QualityScore object
        if score is not None:
            assert 0 <= score.overall_score <= 100
            assert len(score.dimensions) >= 1
    
    @pytest.mark.asyncio
    async def test_quality_dimensions(self, quality_scorer):
        """Quality scorer uses 5 dimensions."""
        expected_dimensions = ['accuracy', 'latency', 'cost', 'reliability', 'compliance']
        
        # Verify dimensions are configured
        assert hasattr(quality_scorer, 'dimensions') or hasattr(quality_scorer, 'config')
    
    @pytest.mark.asyncio
    async def test_dimension_weights_sum_to_one(self, quality_scorer):
        """Quality dimension weights sum to 1.0."""
        if hasattr(quality_scorer, 'weights'):
            weights = quality_scorer.weights
            total = sum(weights.values())
            assert abs(total - 1.0) < 0.001, f"Weights sum to {total}, expected 1.0"
    
    @pytest.mark.asyncio
    async def test_metrics_ingestion(self, metrics_engine):
        """Can ingest metrics."""
        from src.L06_evaluation.models.metric import MetricPoint, MetricType
        
        metric = MetricPoint(
            metric_name="task_duration_ms",
            value=1500.0,
            timestamp=datetime.now(),
            labels={"agent_id": "agent-001", "task_type": "summarization"},
            metric_type=MetricType.GAUGE
        )
        
        await metrics_engine.ingest(metric)
        # Should not raise exception
    
    @pytest.mark.asyncio
    async def test_metrics_query(self, metrics_engine):
        """Can query metrics."""
        results = await metrics_engine.query(
            metric_name="task_duration_ms",
            start=datetime.now() - timedelta(hours=1),
            end=datetime.now(),
            labels={},
            aggregation="avg"
        )
        
        assert isinstance(results, list)
    
    @pytest.mark.asyncio
    async def test_anomaly_detection(self, evaluation_service):
        """Anomaly detector identifies outliers."""
        from src.L06_evaluation.services.anomaly_detector import AnomalyDetector
        
        detector = AnomalyDetector()
        await detector.initialize()
        
        # Anomaly detection requires baseline data
        # This test verifies the detector initializes
        assert detector is not None
        
        await detector.cleanup()
```

## Phase 4: Cross-Layer Integration Tests

### test_cross_layer_integration.py
```python
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
        await gateway.initialize()
        
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
        await gateway.cleanup()
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_l02_l03_integration(self):
        """L02 Agent Runtime uses L03 Tool Execution."""
        from src.L02_runtime.services.agent_executor import AgentExecutor
        from src.L03_tool_execution.services.tool_executor import ToolExecutor
        
        # Initialize both layers
        agent_executor = AgentExecutor()
        await agent_executor.initialize()
        
        tool_executor = ToolExecutor()
        await tool_executor.initialize()
        
        # Verify integration exists
        assert agent_executor is not None
        assert tool_executor is not None
        
        await tool_executor.cleanup()
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
```

## Phase 5: Full Pipeline Tests

### test_full_pipeline.py
```python
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
        await gateway.initialize()
        
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
            await gateway.cleanup()
    
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
        l02 = AgentExecutor()
        l03 = ToolExecutor()
        l04 = ModelGateway()
        l05 = PlanningService()
        l06 = EvaluationService()
        
        await asyncio.gather(
            l02.initialize(),
            l03.initialize(),
            l04.initialize(),
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
        
        # Cleanup concurrently
        await asyncio.gather(
            l02.cleanup(),
            l03.cleanup(),
            l04.cleanup(),
            l05.cleanup(),
            l06.cleanup()
        )
        
        print("All layers cleaned up ✓")
```

## Phase 6: Error Handling Tests

### test_error_handling.py
```python
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
        await gateway.initialize()
        
        try:
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
        finally:
            await gateway.cleanup()
    
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
        from src.L04_model_gateway.services.model_gateway import ModelGateway
        
        gateway = ModelGateway()
        
        # Double initialization should be safe
        await gateway.initialize()
        await gateway.initialize()
        
        assert gateway is not None
        
        await gateway.cleanup()
```

## Phase 7: Performance Tests

### test_performance.py
```python
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
        
        layers = [
            ("L02", AgentExecutor()),
            ("L03", ToolExecutor()),
            ("L04", ModelGateway()),
            ("L05", PlanningService()),
            ("L06", EvaluationService()),
        ]
        
        results = []
        
        for name, layer in layers:
            start = time.time()
            await layer.initialize()
            elapsed = time.time() - start
            results.append((name, elapsed))
            await layer.cleanup()
        
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
        await gateway.initialize()
        
        max_latency = 30.0  # seconds (Ollama can be slow)
        
        try:
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
            
        finally:
            await gateway.cleanup()
```

## Phase 8: Utilities

### utils/fixtures.py
```python
"""Reusable test fixtures."""
from uuid import uuid4
from datetime import datetime

def create_test_goal(goal_text: str = "Test task"):
    """Create a test goal."""
    from src.L05_planning.models.goal import Goal
    return Goal(
        goal_id=str(uuid4()),
        agent_did="did:agent:test",
        goal_text=goal_text
    )

def create_test_cloud_event(event_type: str = "task.completed", data: dict = None):
    """Create a test CloudEvent."""
    from src.L06_evaluation.models.cloud_event import CloudEvent
    return CloudEvent(
        id=str(uuid4()),
        source="test",
        type=event_type,
        subject=f"test-{uuid4()}",
        time=datetime.now(),
        data=data or {"success": True}
    )

def create_test_inference_request(prompt: str = "Test prompt"):
    """Create a test inference request."""
    from src.L04_model_gateway.models.inference_request import (
        InferenceRequest, LogicalPrompt, ModelRequirements, RequestConstraints
    )
    return InferenceRequest(
        request_id=str(uuid4()),
        agent_did="did:agent:test",
        logical_prompt=LogicalPrompt(
            system="You are a test assistant.",
            user=prompt
        ),
        requirements=ModelRequirements(capabilities=[]),
        constraints=RequestConstraints()
    )
```

### utils/helpers.py
```python
"""Test helper functions."""
import asyncio
from typing import Any, Callable, Coroutine

async def with_timeout(coro: Coroutine, timeout: float = 30.0) -> Any:
    """Run coroutine with timeout."""
    return await asyncio.wait_for(coro, timeout=timeout)

async def initialize_layer(layer_class: type, **kwargs) -> Any:
    """Initialize a layer and return it."""
    layer = layer_class(**kwargs)
    await layer.initialize()
    return layer

async def cleanup_layer(layer: Any) -> None:
    """Safely cleanup a layer."""
    if layer and hasattr(layer, 'cleanup'):
        try:
            await layer.cleanup()
        except Exception:
            pass
```

### utils/assertions.py
```python
"""Custom test assertions."""
from typing import Any

def assert_valid_plan(plan: Any) -> None:
    """Assert plan is valid."""
    assert plan is not None, "Plan is None"
    assert plan.plan_id is not None, "Plan ID is None"
    assert plan.tasks is not None, "Plan tasks is None"
    assert len(plan.tasks) >= 1, "Plan has no tasks"

def assert_valid_response(response: Any) -> None:
    """Assert inference response is valid."""
    assert response is not None, "Response is None"
    assert response.content is not None, "Response content is None"
    assert len(response.content) > 0, "Response content is empty"

def assert_valid_quality_score(score: Any) -> None:
    """Assert quality score is valid."""
    assert score is not None, "Score is None"
    assert 0 <= score.overall_score <= 100, f"Score {score.overall_score} out of range"
    assert len(score.dimensions) >= 1, "Score has no dimensions"
```

## Completion Criteria

Sprint complete when:
  - [ ] All test files created
  - [ ] conftest.py with proper fixtures
  - [ ] pytest.ini configured
  - [ ] run_tests.sh executable
  - [ ] README.md documented
  - [ ] Layer initialization tests pass
  - [ ] Individual layer tests pass
  - [ ] Cross-layer integration tests pass
  - [ ] Full pipeline tests pass
  - [ ] Error handling tests pass
  - [ ] Performance tests pass

## Validation

After creating all files:
```bash
cd /Volumes/Extreme\ SSD/projects/story-portal-app/platform

# Verify test structure
ls -la tests/e2e/

# Run quick syntax check
python3 -m py_compile $(find tests/e2e -name "*.py")

# Run tests
chmod +x tests/e2e/run_tests.sh
./tests/e2e/run_tests.sh
```

## Progress Logging

After each phase append to tests/e2e/README.md:
  Phase [N] complete: [test files] - [timestamp]

## Final Steps

1. Create RESULTS.md with test summary
2. Stage files: git add platform/tests/e2e/
3. Do NOT commit - await human review

## REMINDERS

- Tests must use existing infrastructure
- Tests must have timeouts (no hanging)
- Tests should be idempotent
- Use pytest-asyncio for async tests
- Mark slow tests with @pytest.mark.slow
- Mark integration tests with @pytest.mark.integration

## Begin

Create all test files. Execute run_tests.sh. Log results. Complete end-to-end.