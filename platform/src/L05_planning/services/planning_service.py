"""
L05 Planning Layer - Main Planning Service.

Main orchestrator that coordinates all planning components:
- Goal decomposition
- Dependency resolution
- Plan validation
- Task orchestration
- Execution monitoring
"""

import logging
from typing import Optional, Dict, Any
from uuid import uuid4

from ..models import (
    Goal,
    GoalStatus,
    ExecutionPlan,
    PlanStatus,
    PlanningError,
    ErrorCode,
)
from .goal_decomposer import GoalDecomposer
from .dependency_resolver import DependencyResolver
from .plan_validator import PlanValidator
from .resource_estimator import ResourceEstimator
from .context_injector import ContextInjector
from .task_orchestrator import TaskOrchestrator
from .agent_assigner import AgentAssigner
from .execution_monitor import ExecutionMonitor
from .plan_cache import PlanCache
from .l01_bridge import L05Bridge

# Cross-layer imports
from src.L04_model_gateway.services.model_gateway import ModelGateway
from src.L02_runtime.services.agent_executor import AgentExecutor
from src.L03_tool_execution.services.tool_executor import ToolExecutor

logger = logging.getLogger(__name__)


class PlanningService:
    """
    Main Planning Service - coordinates all L05 components.

    Responsibilities:
    1. Accept goals and decompose into plans
    2. Validate plans before execution
    3. Orchestrate task execution
    4. Monitor execution progress
    5. Return execution results
    """

    def __init__(
        self,
        decomposer: Optional[GoalDecomposer] = None,
        resolver: Optional[DependencyResolver] = None,
        validator: Optional[PlanValidator] = None,
        orchestrator: Optional[TaskOrchestrator] = None,
        context_injector: Optional[ContextInjector] = None,
        agent_assigner: Optional[AgentAssigner] = None,
        monitor: Optional[ExecutionMonitor] = None,
        gateway_client: Optional[ModelGateway] = None,
        executor_client: Optional[AgentExecutor] = None,
        tool_executor_client: Optional[ToolExecutor] = None,
        l01_bridge: Optional[L05Bridge] = None,
    ):
        """
        Initialize Planning Service.

        Args:
            decomposer: GoalDecomposer instance
            resolver: DependencyResolver instance
            validator: PlanValidator instance
            orchestrator: TaskOrchestrator instance
            context_injector: ContextInjector instance
            agent_assigner: AgentAssigner instance
            monitor: ExecutionMonitor instance
            gateway_client: L04 Model Gateway client
            executor_client: L02 AgentExecutor client
            tool_executor_client: L03 ToolExecutor client
            l01_bridge: L05Bridge for L01 Data Layer integration
        """
        # Initialize cross-layer clients
        self.gateway = gateway_client or ModelGateway()
        self.executor = executor_client or AgentExecutor()
        # ToolExecutor requires ToolRegistry and ToolSandbox, so only use if provided
        self.tool_executor = tool_executor_client

        # Initialize L01 Data Layer bridge
        self.l01_bridge = l01_bridge or L05Bridge()

        # Initialize components with cross-layer wiring
        cache = PlanCache()
        self.decomposer = decomposer or GoalDecomposer(
            cache=cache,
            gateway_client=self.gateway,
        )
        self.resolver = resolver or DependencyResolver()
        self.resource_estimator = ResourceEstimator()
        self.validator = validator or PlanValidator(
            resource_estimator=self.resource_estimator,
            dependency_resolver=self.resolver,
        )
        self.orchestrator = orchestrator or TaskOrchestrator(
            dependency_resolver=self.resolver,
            executor_client=self.executor,
            tool_executor_client=self.tool_executor,
        )
        self.context_injector = context_injector or ContextInjector()
        self.agent_assigner = agent_assigner or AgentAssigner()
        self.monitor = monitor or ExecutionMonitor()

        # Metrics
        self.goals_received = 0
        self.plans_created = 0
        self.plans_executed = 0
        self.execution_failures = 0

        logger.info("PlanningService initialized with all components and cross-layer integrations")

    async def initialize(self) -> None:
        """Initialize service and components."""
        await self.l01_bridge.initialize()
        logger.info("PlanningService initialization complete")

    async def cleanup(self) -> None:
        """Cleanup service resources."""
        await self.l01_bridge.cleanup()
        logger.info("PlanningService cleanup complete")

    async def create_plan(self, goal: Goal) -> ExecutionPlan:
        """
        Create execution plan from goal.

        Pipeline:
        1. Validate goal input
        2. Check cache
        3. Decompose goal into tasks
        4. Resolve dependencies
        5. Validate plan
        6. Cache plan
        7. Return plan

        Args:
            goal: Goal to plan

        Returns:
            ExecutionPlan ready for execution

        Raises:
            PlanningError: On planning failure
        """
        self.goals_received += 1
        goal.status = GoalStatus.DECOMPOSING

        try:
            logger.info(f"Creating plan for goal: {goal.goal_id}")

            # Record goal in L01
            await self.l01_bridge.record_goal(goal)

            # Step 1: Decompose goal
            plan = await self.decomposer.decompose(goal)
            goal.status = GoalStatus.READY

            # Update goal status in L01
            await self.l01_bridge.update_goal_status(
                goal_id=goal.goal_id,
                status=goal.status.value,
                decomposition_strategy=goal.decomposition_strategy
            )

            # Step 2: Resolve dependencies
            dep_graph = self.resolver.resolve(plan)
            logger.debug(f"Resolved {len(plan.tasks)} tasks with dependencies")

            # Step 3: Validate plan
            validation_result = await self.validator.validate(plan)

            if not validation_result.valid:
                # Log validation errors
                for error in validation_result.errors:
                    logger.error(
                        f"Validation error [{error.code}]: {error.message}"
                    )

                raise PlanningError.from_code(
                    ErrorCode.E5600,
                    details={
                        "goal_id": goal.goal_id,
                        "errors": [
                            {
                                "code": e.code,
                                "message": e.message,
                                "level": e.level,
                            }
                            for e in validation_result.errors
                        ],
                    },
                )

            # Mark plan as validated
            plan.mark_validated()

            # Record plan in L01
            await self.l01_bridge.record_plan(plan)

            self.plans_created += 1
            logger.info(
                f"Created plan {plan.plan_id} with {len(plan.tasks)} tasks "
                f"({len(validation_result.warnings)} warnings)"
            )

            return plan

        except PlanningError:
            goal.status = GoalStatus.FAILED
            raise
        except Exception as e:
            goal.status = GoalStatus.FAILED
            logger.error(f"Plan creation failed: {e}")
            raise PlanningError.from_code(
                ErrorCode.E5100,
                details={"goal_id": goal.goal_id, "error": str(e)},
            )

    async def execute_plan(self, plan_id: str) -> Dict[str, Any]:
        """
        Execute plan by ID.

        Pipeline:
        1. Load plan
        2. Inject contexts for tasks
        3. Assign agents to tasks
        4. Orchestrate execution
        5. Monitor progress
        6. Return result

        Args:
            plan_id: Plan ID to execute

        Returns:
            Execution result dictionary

        Raises:
            PlanningError: On execution failure
        """
        # TODO: Load plan from persistence
        # For now, assume plan is passed directly via execute_plan_direct

        raise PlanningError.from_code(
            ErrorCode.E5002,
            details={"plan_id": plan_id},
            recovery_suggestion="Use execute_plan_direct() with plan object",
        )

    async def execute_plan_direct(
        self,
        plan: ExecutionPlan,
        agent_did: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Execute plan directly (with plan object).

        Args:
            plan: Execution plan to execute
            agent_did: Optional agent DID for execution

        Returns:
            Execution result dictionary

        Raises:
            PlanningError: On execution failure
        """
        self.plans_executed += 1

        try:
            logger.info(f"Executing plan {plan.plan_id}")

            # Update plan status to executing in L01
            from datetime import datetime
            execution_start = datetime.utcnow()
            await self.l01_bridge.update_plan_status(
                plan_id=plan.plan_id,
                status=PlanStatus.EXECUTING.value,
                execution_started_at=execution_start
            )

            # Start monitoring
            monitor_task = None
            # monitor_task = asyncio.create_task(
            #     self.monitor.start_monitoring(plan)
            # )

            # Execute plan
            result = await self.orchestrator.execute_plan(
                plan,
                context={"agent_did": agent_did or "did:agent:default"},
            )

            # Wait for monitoring to complete
            # if monitor_task:
            #     await monitor_task

            # Calculate execution metrics
            execution_end = datetime.utcnow()
            execution_time_ms = (execution_end - execution_start).total_seconds() * 1000

            # Count completed and failed tasks
            completed_count = sum(1 for t in plan.tasks if t.status.value in ["completed", "success"])
            failed_count = sum(1 for t in plan.tasks if t.status.value in ["failed", "error"])

            # Update plan status to completed in L01
            await self.l01_bridge.update_plan_status(
                plan_id=plan.plan_id,
                status=PlanStatus.COMPLETED.value,
                execution_completed_at=execution_end,
                execution_time_ms=execution_time_ms,
                completed_task_count=completed_count,
                failed_task_count=failed_count
            )

            logger.info(f"Plan {plan.plan_id} execution completed")
            return result

        except PlanningError as pe:
            self.execution_failures += 1
            # Update plan status to failed in L01
            await self.l01_bridge.update_plan_status(
                plan_id=plan.plan_id,
                status=PlanStatus.FAILED.value,
                error=str(pe)
            )
            raise
        except Exception as e:
            self.execution_failures += 1
            logger.error(f"Plan execution failed: {e}")
            # Update plan status to failed in L01
            await self.l01_bridge.update_plan_status(
                plan_id=plan.plan_id,
                status=PlanStatus.FAILED.value,
                error=str(e)
            )
            raise PlanningError.from_code(
                ErrorCode.E5200,
                details={"plan_id": plan.plan_id, "error": str(e)},
            )

    async def create_and_execute(
        self,
        goal: Goal,
    ) -> Dict[str, Any]:
        """
        Create plan from goal and execute immediately.

        Args:
            goal: Goal to plan and execute

        Returns:
            Execution result dictionary

        Raises:
            PlanningError: On failure
        """
        # Create plan
        plan = await self.create_plan(goal)

        # Execute plan
        result = await self.execute_plan_direct(plan, agent_did=goal.agent_did)

        return {
            "goal_id": goal.goal_id,
            "plan_id": plan.plan_id,
            "execution_result": result,
        }

    def get_stats(self) -> Dict[str, Any]:
        """
        Get service statistics from all components.

        Returns:
            Dictionary with statistics from all components
        """
        return {
            "service": {
                "goals_received": self.goals_received,
                "plans_created": self.plans_created,
                "plans_executed": self.plans_executed,
                "execution_failures": self.execution_failures,
            },
            "decomposer": self.decomposer.get_stats(),
            "cache": self.decomposer.cache.get_stats(),
            "resolver": self.resolver.get_stats(),
            "validator": self.validator.get_stats(),
            "orchestrator": self.orchestrator.get_stats(),
            "context_injector": self.context_injector.get_stats(),
            "agent_assigner": self.agent_assigner.get_stats(),
            "monitor": self.monitor.get_stats(),
            "resource_estimator": self.resource_estimator.get_stats(),
        }

    async def get_plan_status(self, plan_id: str) -> Dict[str, Any]:
        """
        Get status of plan.

        Args:
            plan_id: Plan ID

        Returns:
            Plan status dictionary
        """
        # TODO: Load plan from persistence and return status
        raise PlanningError.from_code(
            ErrorCode.E5002,
            details={"plan_id": plan_id},
        )
