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
        gateway_client=None,  # L04 Model Gateway
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
        """
        # Initialize components
        cache = PlanCache()
        self.decomposer = decomposer or GoalDecomposer(
            cache=cache,
            gateway_client=gateway_client,
        )
        self.resolver = resolver or DependencyResolver()
        self.resource_estimator = ResourceEstimator()
        self.validator = validator or PlanValidator(
            resource_estimator=self.resource_estimator,
            dependency_resolver=self.resolver,
        )
        self.orchestrator = orchestrator or TaskOrchestrator(
            dependency_resolver=self.resolver,
        )
        self.context_injector = context_injector or ContextInjector()
        self.agent_assigner = agent_assigner or AgentAssigner()
        self.monitor = monitor or ExecutionMonitor()

        # Metrics
        self.goals_received = 0
        self.plans_created = 0
        self.plans_executed = 0
        self.execution_failures = 0

        logger.info("PlanningService initialized with all components")

    async def initialize(self) -> None:
        """Initialize service and components."""
        logger.info("PlanningService initialization complete")

    async def cleanup(self) -> None:
        """Cleanup service resources."""
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

            # Step 1: Decompose goal
            plan = await self.decomposer.decompose(goal)
            goal.status = GoalStatus.READY

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

            logger.info(f"Plan {plan.plan_id} execution completed")
            return result

        except PlanningError:
            self.execution_failures += 1
            raise
        except Exception as e:
            self.execution_failures += 1
            logger.error(f"Plan execution failed: {e}")
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
