"""
L05 Planning Layer - Execution Monitor Service.

Monitors plan execution:
- Track task completion events
- Detect failures and timeouts
- Trigger retries or escalation
- Emit plan-level events
"""

import logging
import asyncio
from typing import Optional, Dict, Any, Callable
from datetime import datetime
from enum import Enum

from ..models import (
    ExecutionPlan,
    Task,
    TaskStatus,
    PlanStatus,
)

logger = logging.getLogger(__name__)


class ExecutionEvent(str, Enum):
    """Execution event types."""

    PLAN_STARTED = "plan.started"
    PLAN_COMPLETED = "plan.completed"
    PLAN_FAILED = "plan.failed"
    TASK_STARTED = "task.started"
    TASK_COMPLETED = "task.completed"
    TASK_FAILED = "task.failed"
    TASK_RETRYING = "task.retrying"
    TASK_TIMEOUT = "task.timeout"


class ExecutionMonitor:
    """
    Monitors execution progress and emits events.

    Responsibilities:
    - Track task completion
    - Detect failures and timeouts
    - Emit events to L01 Event Store
    - Trigger escalation for critical failures
    """

    def __init__(
        self,
        event_store_client=None,  # L01 Event Store client (legacy)
        l01_client=None,  # L01 Data Layer client for event recording
        enable_events: bool = True,
    ):
        """
        Initialize Execution Monitor.

        Args:
            event_store_client: Client for L01 Event Store (legacy)
            l01_client: L01 Data Layer client (shared.clients.L01Client)
            enable_events: Enable event emission
        """
        self.event_store_client = event_store_client
        self.l01_client = l01_client
        self.enable_events = enable_events

        # Event callbacks
        self._callbacks: Dict[ExecutionEvent, list[Callable]] = {}

        # Metrics
        self.events_emitted = 0
        self.failures_detected = 0
        self.timeouts_detected = 0

        logger.info(f"ExecutionMonitor initialized (events: {enable_events})")

    async def start_monitoring(
        self,
        plan: ExecutionPlan,
        check_interval_sec: float = 1.0,
    ) -> None:
        """
        Start monitoring plan execution.

        Args:
            plan: Plan to monitor
            check_interval_sec: Monitoring check interval
        """
        logger.info(f"Started monitoring plan {plan.plan_id}")
        await self._emit_event(ExecutionEvent.PLAN_STARTED, plan=plan)

        # Monitoring loop runs until plan complete
        while not plan.is_complete():
            await asyncio.sleep(check_interval_sec)

            # Check for timeouts
            await self._check_timeouts(plan)

            # Check for failures
            await self._check_failures(plan)

        # Plan complete
        if plan.status == PlanStatus.COMPLETED:
            logger.info(f"Plan {plan.plan_id} completed successfully")
            await self._emit_event(ExecutionEvent.PLAN_COMPLETED, plan=plan)
        else:
            logger.error(f"Plan {plan.plan_id} failed: {plan.error}")
            await self._emit_event(
                ExecutionEvent.PLAN_FAILED,
                plan=plan,
                error=plan.error,
            )

    async def on_task_started(self, task: Task, plan: ExecutionPlan) -> None:
        """
        Handle task started event.

        Args:
            task: Task that started
            plan: Parent plan
        """
        logger.debug(f"Task started: {task.name}")
        await self._emit_event(
            ExecutionEvent.TASK_STARTED,
            plan=plan,
            task=task,
        )

    async def on_task_completed(
        self,
        task: Task,
        plan: ExecutionPlan,
        outputs: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Handle task completed event.

        Args:
            task: Task that completed
            plan: Parent plan
            outputs: Task outputs
        """
        logger.debug(f"Task completed: {task.name}")
        await self._emit_event(
            ExecutionEvent.TASK_COMPLETED,
            plan=plan,
            task=task,
            outputs=outputs,
        )

    async def on_task_failed(
        self,
        task: Task,
        plan: ExecutionPlan,
        error: str,
    ) -> None:
        """
        Handle task failed event.

        Args:
            task: Task that failed
            plan: Parent plan
            error: Error message
        """
        self.failures_detected += 1
        logger.warning(f"Task failed: {task.name} - {error}")

        await self._emit_event(
            ExecutionEvent.TASK_FAILED,
            plan=plan,
            task=task,
            error=error,
        )

        # Check if should escalate
        if self._should_escalate(task, plan):
            await self._escalate_failure(task, plan, error)

    async def on_task_retrying(
        self,
        task: Task,
        plan: ExecutionPlan,
        retry_count: int,
    ) -> None:
        """
        Handle task retry event.

        Args:
            task: Task being retried
            plan: Parent plan
            retry_count: Current retry attempt
        """
        logger.info(f"Task retrying: {task.name} (attempt {retry_count})")
        await self._emit_event(
            ExecutionEvent.TASK_RETRYING,
            plan=plan,
            task=task,
            retry_count=retry_count,
        )

    async def _check_timeouts(self, plan: ExecutionPlan) -> None:
        """
        Check for task timeouts.

        Args:
            plan: Plan to check
        """
        current_time = datetime.utcnow()

        for task in plan.tasks:
            if task.status == TaskStatus.EXECUTING and task.started_at:
                elapsed_sec = (current_time - task.started_at).total_seconds()
                if elapsed_sec > task.timeout_seconds:
                    self.timeouts_detected += 1
                    logger.error(
                        f"Task timeout detected: {task.name} "
                        f"(elapsed: {elapsed_sec}s, timeout: {task.timeout_seconds}s)"
                    )

                    await self._emit_event(
                        ExecutionEvent.TASK_TIMEOUT,
                        plan=plan,
                        task=task,
                        elapsed_seconds=elapsed_sec,
                    )

                    # Mark task as failed
                    task.mark_failed(f"Task timed out after {elapsed_sec}s")

    async def _check_failures(self, plan: ExecutionPlan) -> None:
        """
        Check for task failures.

        Args:
            plan: Plan to check
        """
        failed_tasks = plan.get_failed_tasks()

        for task in failed_tasks:
            # Check if failure is recent (not already processed)
            if task.completed_at:
                age_sec = (datetime.utcnow() - task.completed_at).total_seconds()
                if age_sec < 5:  # Recent failure (within 5 seconds)
                    await self.on_task_failed(task, plan, task.error or "Unknown error")

    def _should_escalate(self, task: Task, plan: ExecutionPlan) -> bool:
        """
        Check if task failure should be escalated.

        Args:
            task: Failed task
            plan: Parent plan

        Returns:
            True if should escalate, False otherwise
        """
        # Escalate if:
        # 1. Task is critical (no dependents would be blocking entire plan)
        # 2. Multiple retries exhausted
        # 3. Failure rate is high

        # For now, simple heuristic: escalate if max retries exhausted
        return task.retry_count >= task.retry_policy.max_retries

    async def _escalate_failure(
        self,
        task: Task,
        plan: ExecutionPlan,
        error: str,
    ) -> None:
        """
        Escalate critical failure.

        Args:
            task: Failed task
            plan: Parent plan
            error: Error message
        """
        # TODO: Integrate with L08 Supervision Layer for human escalation
        logger.critical(
            f"Escalating failure for task {task.name}: {error}"
        )

    async def _emit_event(
        self,
        event_type: ExecutionEvent,
        **kwargs,
    ) -> None:
        """
        Emit execution event.

        Args:
            event_type: Type of event
            **kwargs: Event data
        """
        if not self.enable_events:
            return

        self.events_emitted += 1

        # Build event payload
        event_data = {
            "event_type": event_type.value,
            "timestamp": datetime.utcnow().isoformat(),
            **kwargs,
        }

        # Emit to event store (L01 or legacy event_store_client)
        if self.l01_client or self.event_store_client:
            try:
                await self._publish_to_event_store(event_data)
            except Exception as e:
                logger.error(f"Failed to publish event: {e}")

        # Trigger callbacks
        if event_type in self._callbacks:
            for callback in self._callbacks[event_type]:
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(event_data)
                    else:
                        callback(event_data)
                except Exception as e:
                    logger.error(f"Callback failed: {e}")

    async def _publish_to_event_store(self, event_data: Dict[str, Any]) -> None:
        """
        Publish event to L01 Event Store.

        Args:
            event_data: Event payload
        """
        # Use L01 client if available
        if self.l01_client:
            try:
                # Extract event type for L01 format
                event_type = event_data.get("event_type", "unknown")

                # Build payload with plan/task IDs
                payload = {}
                if "plan" in event_data and hasattr(event_data["plan"], "plan_id"):
                    payload["plan_id"] = event_data["plan"].plan_id
                if "task" in event_data and hasattr(event_data["task"], "task_id"):
                    payload["task_id"] = event_data["task"].task_id
                if "error" in event_data:
                    payload["error"] = str(event_data["error"])
                if "outputs" in event_data:
                    payload["outputs"] = event_data["outputs"]
                if "retry_count" in event_data:
                    payload["retry_count"] = event_data["retry_count"]

                await self.l01_client.record_event(
                    event_type=event_type,
                    payload=payload,
                )
                logger.debug(f"Published event to L01: {event_type}")
                return
            except Exception as e:
                logger.warning(f"Failed to publish event to L01: {e}")

        # Fallback: just log
        logger.debug(f"Publishing event: {event_data['event_type']} (local only)")

    def register_callback(
        self,
        event_type: ExecutionEvent,
        callback: Callable,
    ) -> None:
        """
        Register callback for event type.

        Args:
            event_type: Event type to listen for
            callback: Callback function
        """
        if event_type not in self._callbacks:
            self._callbacks[event_type] = []
        self._callbacks[event_type].append(callback)

    def get_stats(self) -> Dict[str, Any]:
        """Get monitor statistics."""
        return {
            "events_emitted": self.events_emitted,
            "failures_detected": self.failures_detected,
            "timeouts_detected": self.timeouts_detected,
        }
