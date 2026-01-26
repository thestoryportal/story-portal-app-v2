"""
L05 Planning Layer - L01 Data Layer Bridge

Bridge between L05 Planning Layer and L01 Data Layer for persistent goal, plan, and task tracking.

This bridge records planning activities in L01 for monitoring, analytics, and execution tracking
across the platform.
"""

import logging
from typing import Optional, Dict, Any
from datetime import datetime

from shared.clients import L01Client
from ..models.goal import Goal
from ..models.plan import ExecutionPlan, PlanStatus
from ..models.task import Task


logger = logging.getLogger(__name__)


class L05Bridge:
    """
    Bridge between L05 Planning Layer and L01 Data Layer.

    Responsibilities:
    - Record goals and their decomposition in L01
    - Track execution plans with metadata (strategy, tokens, latency)
    - Update plan and task status during execution
    - Support agent context and resource tracking
    - Publish planning events via L01 event stream
    """

    def __init__(self, l01_base_url: str = "http://localhost:8001"):
        """Initialize L05 bridge.

        Args:
            l01_base_url: Base URL for L01 Data Layer API (default: port 8001)
        """
        self.l01_client = L01Client(base_url=l01_base_url)
        self.enabled = True
        logger.info(f"L05Bridge initialized with base_url={l01_base_url}")

    async def initialize(self) -> None:
        """Initialize bridge (async setup if needed)."""
        logger.info("L05Bridge initialized")

    async def record_goal(
        self,
        goal: Goal,
        agent_id: Optional[str] = None
    ) -> bool:
        """Record a goal in L01.

        Args:
            goal: Goal instance to record
            agent_id: Optional UUID of agent (if known)

        Returns:
            True if recorded successfully, False otherwise
        """
        if not self.enabled:
            return False

        try:
            # Build constraints dict from Goal.constraints
            constraints = {}
            if goal.constraints:
                if goal.constraints.max_token_budget:
                    constraints["max_token_budget"] = goal.constraints.max_token_budget
                if goal.constraints.max_execution_time_sec:
                    constraints["max_execution_time_sec"] = goal.constraints.max_execution_time_sec
                if goal.constraints.max_parallelism:
                    constraints["max_parallelism"] = goal.constraints.max_parallelism
                if goal.constraints.deadline_unix_ms:
                    constraints["deadline_unix_ms"] = goal.constraints.deadline_unix_ms
                if goal.constraints.priority:
                    constraints["priority"] = goal.constraints.priority
                if goal.constraints.require_approval is not None:
                    constraints["require_approval"] = goal.constraints.require_approval
                if goal.constraints.allowed_agent_types:
                    constraints["allowed_agent_types"] = goal.constraints.allowed_agent_types
                if goal.constraints.forbidden_tools:
                    constraints["forbidden_tools"] = goal.constraints.forbidden_tools
                if goal.constraints.cost_limit_usd:
                    constraints["cost_limit_usd"] = goal.constraints.cost_limit_usd

            # Record in L01
            await self.l01_client.record_goal(
                goal_id=goal.goal_id,
                agent_did=goal.agent_did,
                goal_text=goal.goal_text,
                agent_id=agent_id,
                goal_type=goal.goal_type.value,
                status=goal.status.value,
                constraints=constraints if constraints else None,
                metadata=goal.metadata,
                parent_goal_id=goal.parent_goal_id,
                decomposition_strategy=goal.decomposition_strategy
            )

            logger.info(
                f"Recorded goal {goal.goal_id} in L01 "
                f"(type={goal.goal_type.value}, status={goal.status.value})"
            )
            return True

        except Exception as e:
            logger.error(f"Failed to record goal in L01: {e}")
            return False

    async def update_goal_status(
        self,
        goal_id: str,
        status: str,
        decomposition_strategy: Optional[str] = None
    ) -> bool:
        """Update goal status in L01.

        Args:
            goal_id: Goal ID to update
            status: New status value
            decomposition_strategy: Optional decomposition strategy

        Returns:
            True if updated successfully, False otherwise
        """
        if not self.enabled:
            return False

        try:
            await self.l01_client.update_goal_status(
                goal_id=goal_id,
                status=status,
                decomposition_strategy=decomposition_strategy
            )

            logger.info(f"Updated goal {goal_id} status to {status} in L01")
            return True

        except Exception as e:
            logger.error(f"Failed to update goal status in L01: {e}")
            return False

    async def record_plan(
        self,
        plan: ExecutionPlan,
        agent_id: Optional[str] = None
    ) -> bool:
        """Record an execution plan in L01.

        Args:
            plan: ExecutionPlan instance to record
            agent_id: Optional UUID of agent (if known)

        Returns:
            True if recorded successfully, False otherwise
        """
        if not self.enabled:
            return False

        try:
            # Serialize tasks to dict format
            tasks_data = []
            for task in plan.tasks:
                task_dict = {
                    "task_id": task.task_id,
                    "name": task.name,
                    "description": task.description,
                    "task_type": task.task_type.value,
                    "status": task.status.value,
                    "dependencies": [dep.task_id for dep in task.dependencies],
                    "inputs": task.inputs,
                    "outputs": task.outputs,
                    "assigned_agent": task.assigned_agent,
                    "timeout_seconds": task.timeout_seconds,
                    "retry_count": task.retry_count,
                    "tool_name": task.tool_name,
                    "llm_prompt": task.llm_prompt,
                    "metadata": task.metadata
                }
                if task.retry_policy:
                    task_dict["retry_policy"] = {
                        "max_retries": task.retry_policy.max_retries,
                        "backoff_multiplier": task.retry_policy.backoff_multiplier,
                        "max_delay_sec": task.retry_policy.max_delay_sec
                    }
                tasks_data.append(task_dict)

            # Serialize resource budget if present
            resource_budget = None
            if plan.resource_budget:
                resource_budget = {
                    "max_token_count": plan.resource_budget.max_token_count,
                    "max_execution_time_sec": plan.resource_budget.max_execution_time_sec,
                    "max_parallel_tasks": plan.resource_budget.max_parallel_tasks,
                    "max_cpu_cores": plan.resource_budget.max_cpu_cores,
                    "max_memory_mb": plan.resource_budget.max_memory_mb,
                    "max_disk_mb": plan.resource_budget.max_disk_mb,
                    "max_network_mb": plan.resource_budget.max_network_mb,
                    "max_cost_usd": plan.resource_budget.max_cost_usd
                }

            # Record in L01
            await self.l01_client.record_plan(
                plan_id=plan.plan_id,
                goal_id=plan.goal_id,
                agent_id=agent_id,
                tasks=tasks_data,
                dependency_graph=plan.dependency_graph,
                status=plan.status.value,
                resource_budget=resource_budget,
                decomposition_strategy=plan.metadata.decomposition_strategy,
                decomposition_latency_ms=plan.metadata.decomposition_latency_ms,
                cache_hit=plan.metadata.cache_hit,
                llm_provider=plan.metadata.llm_provider,
                llm_model=plan.metadata.llm_model,
                total_tokens_used=plan.metadata.total_tokens_used,
                validation_time_ms=plan.metadata.validation_time_ms,
                tags=plan.metadata.tags,
                metadata={}  # Additional metadata if needed
            )

            logger.info(
                f"Recorded plan {plan.plan_id} in L01 "
                f"(goal={plan.goal_id}, tasks={len(plan.tasks)}, "
                f"strategy={plan.metadata.decomposition_strategy})"
            )
            return True

        except Exception as e:
            logger.error(f"Failed to record plan in L01: {e}")
            return False

    async def update_plan_status(
        self,
        plan_id: str,
        status: str,
        validated_at: Optional[datetime] = None,
        execution_started_at: Optional[datetime] = None,
        execution_completed_at: Optional[datetime] = None,
        execution_time_ms: Optional[float] = None,
        parallelism_achieved: Optional[int] = None,
        error: Optional[str] = None,
        completed_task_count: Optional[int] = None,
        failed_task_count: Optional[int] = None
    ) -> bool:
        """Update plan status and execution details in L01.

        Args:
            plan_id: Plan ID to update
            status: New status value
            validated_at: Timestamp when plan was validated
            execution_started_at: Timestamp when execution started
            execution_completed_at: Timestamp when execution completed
            execution_time_ms: Total execution time in milliseconds
            parallelism_achieved: Number of parallel tasks executed
            error: Error message if failed
            completed_task_count: Number of completed tasks
            failed_task_count: Number of failed tasks

        Returns:
            True if updated successfully, False otherwise
        """
        if not self.enabled:
            return False

        try:
            # Convert datetime objects to ISO strings
            validated_at_str = validated_at.isoformat() if validated_at else None
            execution_started_at_str = execution_started_at.isoformat() if execution_started_at else None
            execution_completed_at_str = execution_completed_at.isoformat() if execution_completed_at else None

            await self.l01_client.update_plan_status(
                plan_id=plan_id,
                status=status,
                validated_at=validated_at_str,
                execution_started_at=execution_started_at_str,
                execution_completed_at=execution_completed_at_str,
                execution_time_ms=execution_time_ms,
                parallelism_achieved=parallelism_achieved,
                error=error,
                completed_task_count=completed_task_count,
                failed_task_count=failed_task_count
            )

            logger.info(f"Updated plan {plan_id} status to {status} in L01")
            return True

        except Exception as e:
            logger.error(f"Failed to update plan status in L01: {e}")
            return False

    async def get_plan(self, plan_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a plan from L01.

        Args:
            plan_id: Plan ID to retrieve

        Returns:
            Plan data dict or None if not found
        """
        if not self.enabled:
            return None

        try:
            plan_data = await self.l01_client.get_plan(plan_id)
            logger.info(f"Retrieved plan {plan_id} from L01")
            return plan_data

        except Exception as e:
            logger.error(f"Failed to get plan from L01: {e}")
            return None

    async def list_plans(
        self,
        goal_id: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 100
    ) -> list:
        """List plans with optional filtering.

        Args:
            goal_id: Filter by goal ID
            status: Filter by status
            limit: Maximum number of plans to return

        Returns:
            List of plan dictionaries
        """
        if not self.enabled:
            return []

        try:
            params = {"limit": limit}
            if goal_id:
                params["goal_id"] = goal_id
            if status:
                params["status"] = status

            client = await self.l01_client._get_client()
            response = await client.get("/plans/", params=params)
            response.raise_for_status()
            return response.json()

        except Exception as e:
            logger.error(f"Failed to list plans from L01: {e}")
            return []

    async def cleanup(self) -> None:
        """Cleanup bridge resources."""
        try:
            await self.l01_client.close()
            logger.info("L05Bridge cleanup complete")
        except Exception as e:
            logger.warning(f"L05Bridge cleanup failed: {e}")
