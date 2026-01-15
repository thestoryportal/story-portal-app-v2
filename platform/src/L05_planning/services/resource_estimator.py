"""
L05 Planning Layer - Resource Estimator Service.

Estimates resource requirements for tasks and plans:
- CPU cores
- Memory (MB)
- Execution time (seconds)
- Token count (for LLM tasks)
- Disk space
- Network transfer
- Cost (USD)
"""

import logging
from typing import Dict, Any

from ..models import (
    Task,
    ExecutionPlan,
    ResourceEstimate,
    ResourceConstraints,
    TaskType,
)

logger = logging.getLogger(__name__)


class ResourceEstimator:
    """
    Estimates resource requirements for tasks and plans.

    Uses heuristics based on task type, inputs, and historical data.
    """

    def __init__(
        self,
        default_cpu_cores: float = 1.0,
        default_memory_mb: int = 512,
        default_execution_time_sec: int = 60,
        token_cost_per_1k: float = 0.002,  # $0.002 per 1K tokens (typical)
    ):
        """
        Initialize Resource Estimator.

        Args:
            default_cpu_cores: Default CPU estimate
            default_memory_mb: Default memory estimate
            default_execution_time_sec: Default execution time estimate
            token_cost_per_1k: Cost per 1K tokens
        """
        self.default_cpu_cores = default_cpu_cores
        self.default_memory_mb = default_memory_mb
        self.default_execution_time_sec = default_execution_time_sec
        self.token_cost_per_1k = token_cost_per_1k

        # Metrics
        self.tasks_estimated = 0
        self.plans_estimated = 0

        logger.info("ResourceEstimator initialized")

    def estimate_task(self, task: Task) -> ResourceEstimate:
        """
        Estimate resources for a single task.

        Args:
            task: Task to estimate

        Returns:
            ResourceEstimate with predicted requirements
        """
        self.tasks_estimated += 1

        # Base estimates by task type
        if task.task_type == TaskType.LLM_CALL:
            return self._estimate_llm_task(task)
        elif task.task_type == TaskType.TOOL_CALL:
            return self._estimate_tool_task(task)
        elif task.task_type == TaskType.COMPOUND:
            return self._estimate_compound_task(task)
        else:
            return self._estimate_atomic_task(task)

    def _estimate_llm_task(self, task: Task) -> ResourceEstimate:
        """Estimate resources for LLM task."""
        # Estimate token count from prompt
        prompt = task.llm_prompt or ""
        input_tokens = len(prompt.split()) * 1.3  # Rough heuristic: 1.3 tokens per word
        output_tokens = 500  # Default output estimate

        total_tokens = int(input_tokens + output_tokens)
        cost_usd = (total_tokens / 1000) * self.token_cost_per_1k

        return ResourceEstimate(
            cpu_cores=0.5,  # LLM tasks are I/O bound
            memory_mb=256,
            execution_time_sec=max(30, int(total_tokens / 20)),  # ~20 tokens/sec
            token_count=total_tokens,
            disk_mb=10,
            network_mb=1,
            cost_usd=cost_usd,
        )

    def _estimate_tool_task(self, task: Task) -> ResourceEstimate:
        """Estimate resources for tool execution task."""
        # Tool-specific estimates (could be refined by tool type)
        return ResourceEstimate(
            cpu_cores=1.0,
            memory_mb=512,
            execution_time_sec=task.timeout_seconds or 60,
            token_count=0,
            disk_mb=100,
            network_mb=10,
            cost_usd=0.001,  # Nominal cost
        )

    def _estimate_atomic_task(self, task: Task) -> ResourceEstimate:
        """Estimate resources for atomic task."""
        return ResourceEstimate(
            cpu_cores=self.default_cpu_cores,
            memory_mb=self.default_memory_mb,
            execution_time_sec=task.timeout_seconds or self.default_execution_time_sec,
            token_count=0,
            disk_mb=50,
            network_mb=5,
            cost_usd=0.0005,
        )

    def _estimate_compound_task(self, task: Task) -> ResourceEstimate:
        """Estimate resources for compound task."""
        # Compound tasks typically require more resources
        return ResourceEstimate(
            cpu_cores=2.0,
            memory_mb=1024,
            execution_time_sec=task.timeout_seconds or 300,
            token_count=0,
            disk_mb=200,
            network_mb=20,
            cost_usd=0.01,
        )

    def estimate_plan(self, plan: ExecutionPlan) -> ResourceEstimate:
        """
        Estimate total resources for entire plan.

        Aggregates estimates across all tasks.

        Args:
            plan: Execution plan to estimate

        Returns:
            ResourceEstimate with total requirements
        """
        self.plans_estimated += 1

        # Aggregate estimates
        total_estimate = ResourceEstimate(
            cpu_cores=0.0,
            memory_mb=0,
            execution_time_sec=0,
            token_count=0,
            disk_mb=0,
            network_mb=0,
            cost_usd=0.0,
        )

        for task in plan.tasks:
            task_estimate = self.estimate_task(task)

            # Sum resources (note: CPU and memory are peak, not cumulative)
            total_estimate.cpu_cores = max(total_estimate.cpu_cores, task_estimate.cpu_cores)
            total_estimate.memory_mb = max(total_estimate.memory_mb, task_estimate.memory_mb)
            total_estimate.execution_time_sec += task_estimate.execution_time_sec
            total_estimate.token_count += task_estimate.token_count
            total_estimate.disk_mb += task_estimate.disk_mb
            total_estimate.network_mb += task_estimate.network_mb
            total_estimate.cost_usd += task_estimate.cost_usd

        logger.debug(
            f"Estimated plan {plan.plan_id}: "
            f"{total_estimate.execution_time_sec}s, "
            f"{total_estimate.token_count} tokens, "
            f"${total_estimate.cost_usd:.4f}"
        )

        return total_estimate

    def check_budget(
        self,
        estimate: ResourceEstimate,
        budget: ResourceConstraints,
    ) -> tuple[bool, list[str]]:
        """
        Check if estimate fits within budget.

        Args:
            estimate: Resource estimate
            budget: Resource constraints/budget

        Returns:
            (is_within_budget, list of violations)
        """
        violations = []

        is_valid, error_msg = budget.is_within_budget(estimate)
        if not is_valid:
            violations.append(error_msg)

        return len(violations) == 0, violations

    def get_stats(self) -> Dict[str, Any]:
        """Get estimator statistics."""
        return {
            "tasks_estimated": self.tasks_estimated,
            "plans_estimated": self.plans_estimated,
        }
