"""
L05 Planning Layer - Task Orchestrator Service.

Orchestrates task execution with state machine management:
PENDING → READY → EXECUTING → COMPLETED | FAILED | BLOCKED

Handles:
- Task state transitions
- Parallel execution
- Task dispatch to L02
- Completion monitoring
- Retry logic
- Output propagation
"""

import asyncio
import logging
from typing import Optional, Dict, Any, Set, List
from datetime import datetime
from uuid import uuid4

from ..models import (
    Task,
    TaskStatus,
    ExecutionPlan,
    PlanStatus,
    PlanningError,
    ErrorCode,
    ExecutionContext,
)
from .dependency_resolver import DependencyResolver, DependencyGraph

logger = logging.getLogger(__name__)


class TaskResult:
    """Result of task execution."""

    def __init__(
        self,
        task_id: str,
        success: bool,
        outputs: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None,
        execution_time_sec: float = 0.0,
    ):
        self.task_id = task_id
        self.success = success
        self.outputs = outputs or {}
        self.error = error
        self.execution_time_sec = execution_time_sec


class TaskOrchestrator:
    """
    Orchestrates task execution with state machine management.

    Coordinates parallel task execution, monitors completion, handles failures.
    """

    def __init__(
        self,
        dependency_resolver: Optional[DependencyResolver] = None,
        executor_client=None,  # L02 AgentExecutor client
        tool_executor_client=None,  # L03 ToolExecutor client
        max_parallel_tasks: int = 10,
        task_timeout_sec: int = 300,
    ):
        """
        Initialize Task Orchestrator.

        Args:
            dependency_resolver: DependencyResolver instance
            executor_client: L02 AgentExecutor client for task dispatch
            tool_executor_client: L03 ToolExecutor client for tool execution
            max_parallel_tasks: Maximum concurrent tasks
            task_timeout_sec: Default task timeout
        """
        self.dependency_resolver = dependency_resolver or DependencyResolver()
        self.executor_client = executor_client
        self.tool_executor_client = tool_executor_client
        self.max_parallel_tasks = max_parallel_tasks
        self.task_timeout_sec = task_timeout_sec

        # Execution state tracking
        self._executing_tasks: Dict[str, asyncio.Task] = {}
        self._task_outputs: Dict[str, Dict[str, Any]] = {}  # Store outputs from completed tasks

        # Metrics
        self.plans_executed = 0
        self.tasks_executed = 0
        self.tasks_completed = 0
        self.tasks_failed = 0
        self.tasks_retried = 0

        logger.info(f"TaskOrchestrator initialized (max_parallel: {max_parallel_tasks})")

    async def execute_plan(
        self,
        plan: ExecutionPlan,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Execute entire plan with parallel task execution.

        Args:
            plan: Execution plan to execute
            context: Optional execution context

        Returns:
            Dictionary with execution results

        Raises:
            PlanningError: On execution failure
        """
        self.plans_executed += 1
        plan.mark_executing()

        try:
            # Resolve dependencies
            dep_graph = self.dependency_resolver.resolve(plan)

            # Initialize tracking
            completed_tasks: Set[str] = set()
            failed_tasks: Set[str] = set()
            executing_tasks: Set[str] = set()

            # Mark all tasks as PENDING initially
            for task in plan.tasks:
                task.status = TaskStatus.PENDING

            logger.info(
                f"Executing plan {plan.plan_id} with {len(plan.tasks)} tasks "
                f"(max_parallel: {self.max_parallel_tasks})"
            )

            # Execute until all tasks done
            while True:
                # Get ready tasks
                ready_tasks = self.dependency_resolver.get_ready_tasks(
                    dep_graph, completed_tasks, executing_tasks
                )

                # Mark ready tasks
                for task in ready_tasks:
                    task.mark_ready()

                # Execute ready tasks (up to max parallel)
                available_slots = self.max_parallel_tasks - len(executing_tasks)
                tasks_to_execute = ready_tasks[:available_slots]

                for task in tasks_to_execute:
                    task.mark_executing()
                    executing_tasks.add(task.task_id)
                    self.tasks_executed += 1

                    # Start task execution
                    exec_task = asyncio.create_task(self._execute_task(task, plan, context))
                    self._executing_tasks[task.task_id] = exec_task

                # Wait for at least one task to complete (if any executing)
                if executing_tasks:
                    # Wait for first completion
                    done, pending = await asyncio.wait(
                        self._executing_tasks.values(),
                        return_when=asyncio.FIRST_COMPLETED,
                    )

                    # Process completed tasks
                    for completed_task_future in done:
                        result: TaskResult = await completed_task_future

                        # Find corresponding task
                        task = plan.get_task(result.task_id)
                        if not task:
                            logger.error(f"Task {result.task_id} not found in plan")
                            continue

                        # Update task state
                        executing_tasks.remove(result.task_id)
                        del self._executing_tasks[result.task_id]

                        if result.success:
                            task.mark_completed(result.outputs)
                            completed_tasks.add(result.task_id)
                            self.tasks_completed += 1
                            self._task_outputs[result.task_id] = result.outputs
                            logger.info(f"Task {task.name} completed successfully")
                        else:
                            # Check if should retry
                            if task.should_retry():
                                self.tasks_retried += 1
                                task.retry_count += 1
                                task.status = TaskStatus.PENDING  # Reset to pending for retry
                                logger.warning(
                                    f"Task {task.name} failed, retrying "
                                    f"({task.retry_count}/{task.retry_policy.max_retries})"
                                )
                                # Wait before retry
                                await asyncio.sleep(task.get_retry_delay())
                            else:
                                task.mark_failed(result.error or "Unknown error")
                                failed_tasks.add(result.task_id)
                                self.tasks_failed += 1
                                logger.error(f"Task {task.name} failed: {result.error}")

                                # Mark dependent tasks as blocked
                                for dependent_id in dep_graph.get_dependents(result.task_id):
                                    dependent_task = plan.get_task(dependent_id)
                                    if dependent_task:
                                        dependent_task.mark_blocked()

                # Check if all tasks are done
                terminal_states = {TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.BLOCKED}
                all_done = all(task.status in terminal_states for task in plan.tasks)

                if all_done:
                    break

                # Safety check: no progress
                if not executing_tasks and not ready_tasks:
                    logger.error("No tasks executing and none ready - deadlock detected")
                    break

            # Mark plan complete or failed
            if failed_tasks:
                plan.mark_failed(f"Plan failed: {len(failed_tasks)} tasks failed")
                raise PlanningError.from_code(
                    ErrorCode.E5204,
                    details={
                        "plan_id": plan.plan_id,
                        "failed_tasks": len(failed_tasks),
                        "completed_tasks": len(completed_tasks),
                    },
                )
            else:
                plan.mark_completed()

            logger.info(
                f"Plan {plan.plan_id} completed: "
                f"{len(completed_tasks)} succeeded, {len(failed_tasks)} failed"
            )

            return {
                "plan_id": plan.plan_id,
                "status": plan.status.value,
                "completed_tasks": len(completed_tasks),
                "failed_tasks": len(failed_tasks),
                "outputs": self._task_outputs,
            }

        except PlanningError:
            raise
        except Exception as e:
            logger.error(f"Plan execution failed: {e}")
            plan.mark_failed(str(e))
            raise PlanningError.from_code(
                ErrorCode.E5200,
                details={"plan_id": plan.plan_id, "error": str(e)},
            )

    async def _execute_task(
        self,
        task: Task,
        plan: ExecutionPlan,
        context: Optional[Dict[str, Any]] = None,
    ) -> TaskResult:
        """
        Execute single task.

        Args:
            task: Task to execute
            plan: Parent plan
            context: Optional execution context

        Returns:
            TaskResult with execution outcome
        """
        start_time = datetime.utcnow()

        try:
            logger.info(f"Executing task: {task.name} ({task.task_id})")

            # Prepare task inputs (bind outputs from dependencies)
            task_inputs = self._prepare_task_inputs(task)

            # Execute based on task type
            if task.task_type == "tool_call":
                outputs = await self._execute_tool_call(task, task_inputs)
            elif task.task_type == "llm_call":
                outputs = await self._execute_llm_call(task, task_inputs)
            elif task.task_type == "atomic":
                outputs = await self._execute_atomic(task, task_inputs)
            else:
                # Compound tasks not yet supported
                outputs = {"result": "Task executed (mock)"}

            # Calculate execution time
            execution_time = (datetime.utcnow() - start_time).total_seconds()

            return TaskResult(
                task_id=task.task_id,
                success=True,
                outputs=outputs,
                execution_time_sec=execution_time,
            )

        except asyncio.TimeoutError:
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            logger.error(f"Task {task.name} timed out after {execution_time}s")
            return TaskResult(
                task_id=task.task_id,
                success=False,
                error=f"Task timed out after {execution_time}s",
                execution_time_sec=execution_time,
            )

        except Exception as e:
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            logger.error(f"Task {task.name} failed: {e}")
            return TaskResult(
                task_id=task.task_id,
                success=False,
                error=str(e),
                execution_time_sec=execution_time,
            )

    def _prepare_task_inputs(self, task: Task) -> Dict[str, Any]:
        """
        Prepare task inputs by binding outputs from dependencies.

        Args:
            task: Task to prepare inputs for

        Returns:
            Dictionary of input values
        """
        inputs = dict(task.inputs)  # Start with static inputs

        # Bind outputs from dependencies
        for dep in task.dependencies:
            if dep.dependency_type == "data" and dep.output_key:
                # Get output from dependency
                if dep.task_id in self._task_outputs:
                    dep_outputs = self._task_outputs[dep.task_id]
                    if dep.output_key in dep_outputs:
                        inputs[dep.output_key] = dep_outputs[dep.output_key]

        return inputs

    async def _execute_tool_call(
        self,
        task: Task,
        inputs: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Execute tool call task via L03 Tool Execution Layer.

        Args:
            task: Task with tool_name
            inputs: Task inputs

        Returns:
            Tool outputs
        """
        if not self.tool_executor_client:
            logger.warning(f"No L03 tool executor configured, using mock for {task.tool_name}")
            return {"result": f"Tool {task.tool_name} executed (mock)", "status": "success"}

        if not task.tool_name:
            raise ValueError(f"Task {task.task_id} has no tool_name specified")

        logger.info(f"Executing tool: {task.tool_name} via L03")

        # Execute tool via L03 ToolExecutor
        result = await self.tool_executor_client.execute(
            tool_name=task.tool_name,
            arguments=inputs,
        )

        if not result.success:
            raise Exception(f"Tool execution failed: {result.error}")

        return result.data or {"result": "Tool executed successfully"}

    async def _execute_llm_call(
        self,
        task: Task,
        inputs: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Execute LLM call task via L02 AgentExecutor.

        Args:
            task: Task with llm_prompt
            inputs: Task inputs

        Returns:
            LLM outputs
        """
        if not self.executor_client:
            logger.warning(f"No L02 executor configured, using mock for LLM call")
            return {"result": "LLM call completed (mock)", "response": "Mock response"}

        logger.info(f"Executing LLM call via L02: {(task.llm_prompt or '')[:50]}...")

        # Dispatch to L02 for execution
        # L02 API: execute(agent_id, input_data, stream=False) -> Dict
        result = await self.executor_client.execute(
            agent_id=task.assigned_agent or "default",
            input_data={
                "content": task.llm_prompt or task.description,
                "task_id": task.task_id,
                "task_name": task.name,
                "task_type": "llm_call",
                "inputs": inputs,
                "timeout": task.timeout_seconds,
            },
        )

        # L02 returns dict with response, not TaskResult object
        return {
            "result": "LLM call completed",
            "response": result.get("response", ""),
            "agent_id": result.get("agent_id"),
            "tokens_used": result.get("tokens_used", 0),
        }

    async def _execute_atomic(
        self,
        task: Task,
        inputs: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Execute atomic task via L02 AgentExecutor.

        Args:
            task: Atomic task
            inputs: Task inputs

        Returns:
            Task outputs
        """
        if not self.executor_client:
            logger.warning(f"No L02 executor configured, using mock for atomic task")
            await asyncio.sleep(0.1)  # Simulate work
            return {"result": f"Atomic task {task.name} completed (mock)", "status": "success"}

        logger.info(f"Executing atomic task via L02: {task.name}")

        # Dispatch to L02 for execution
        # L02 API: execute(agent_id, input_data, stream=False) -> Dict
        result = await self.executor_client.execute(
            agent_id=task.assigned_agent or "default",
            input_data={
                "content": task.description,
                "task_id": task.task_id,
                "task_name": task.name,
                "task_type": "atomic",
                "inputs": inputs,
                "timeout": task.timeout_seconds,
            },
        )

        # L02 returns dict with response, not TaskResult object
        return {
            "result": f"Atomic task {task.name} completed",
            "response": result.get("response", ""),
            "status": "success",
        }

    def get_stats(self) -> Dict[str, Any]:
        """Get orchestrator statistics."""
        return {
            "plans_executed": self.plans_executed,
            "tasks_executed": self.tasks_executed,
            "tasks_completed": self.tasks_completed,
            "tasks_failed": self.tasks_failed,
            "tasks_retried": self.tasks_retried,
            "success_rate": self.tasks_completed / max(1, self.tasks_executed),
            "failure_rate": self.tasks_failed / max(1, self.tasks_executed),
            "retry_rate": self.tasks_retried / max(1, self.tasks_executed),
        }
