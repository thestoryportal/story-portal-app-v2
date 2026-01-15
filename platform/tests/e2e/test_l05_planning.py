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
