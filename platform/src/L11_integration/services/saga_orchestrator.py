"""
L11 Integration Layer - Saga Orchestrator.

Multi-step workflow orchestration with automatic compensation (rollback).
Includes exponential backoff, distributed tracing, and timeout enforcement.
"""

import asyncio
import logging
import random
from typing import Dict, Optional, Any, List
from datetime import datetime, timezone

from .request_orchestrator import RequestOrchestrator
from ..models import (
    SagaDefinition,
    SagaExecution,
    SagaStatus,
    SagaStep,
    StepStatus,
    RequestContext,
    IntegrationError,
    ErrorCode,
)


logger = logging.getLogger(__name__)


def calculate_backoff(
    attempt: int,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
    jitter: bool = True
) -> float:
    """
    Calculate exponential backoff delay with optional jitter.

    Args:
        attempt: Current attempt number (1-based)
        base_delay: Base delay in seconds
        max_delay: Maximum delay cap
        jitter: Add randomization to prevent thundering herd

    Returns:
        Delay in seconds
    """
    # Exponential backoff: base * 2^(attempt-1)
    delay = base_delay * (2 ** (attempt - 1))
    delay = min(delay, max_delay)

    if jitter:
        # Add +/- 25% jitter
        jitter_range = delay * 0.25
        delay += random.uniform(-jitter_range, jitter_range)

    return max(0.1, delay)  # Minimum 100ms


class SagaOrchestrator:
    """
    Saga orchestrator for multi-step workflows.

    Executes multi-step operations across layers with automatic
    compensation (rollback) on failure.
    """

    def __init__(self, request_orchestrator: RequestOrchestrator, l11_bridge=None):
        """
        Initialize saga orchestrator.

        Args:
            request_orchestrator: RequestOrchestrator instance
            l11_bridge: L11Bridge instance for recording to L01
        """
        self.request_orchestrator = request_orchestrator
        self.l11_bridge = l11_bridge
        self._executions: Dict[str, SagaExecution] = {}
        self._lock = asyncio.Lock()

    async def execute_saga(
        self,
        saga: SagaDefinition,
        context: Optional[Dict[str, Any]] = None,
        trace_context: Optional[RequestContext] = None,
    ) -> SagaExecution:
        """
        Execute a saga workflow.

        Args:
            saga: SagaDefinition to execute
            context: Initial context data
            trace_context: Request context for tracing

        Returns:
            SagaExecution with final status

        Raises:
            IntegrationError: If saga execution fails
        """
        # Create execution
        if trace_context is None:
            trace_context = RequestContext.create()

        execution = SagaExecution.create(
            saga_definition=saga,
            context=context or {},
            trace_id=trace_context.trace_id,
            correlation_id=trace_context.correlation_id,
        )

        # Store execution
        async with self._lock:
            self._executions[execution.execution_id] = execution

        logger.info(
            f"Starting saga: {saga.saga_name} "
            f"(execution_id={execution.execution_id}, "
            f"steps={len(saga.steps)})"
        )

        try:
            # Start execution
            execution.start()

            # Record saga execution in L01
            if self.l11_bridge:
                await self.l11_bridge.record_saga_execution(
                    saga_id=execution.execution_id,
                    saga_name=saga.saga_name,
                    started_at=execution.started_at,
                    steps_total=len(saga.steps),
                    status="running",
                    context=execution.context,
                )

            # Execute steps sequentially
            for step_index, step in enumerate(saga.steps):
                execution.current_step_index = step_index

                # Check timeout
                if execution.is_timeout():
                    execution.status = SagaStatus.TIMEOUT
                    if saga.auto_compensate:
                        await self._compensate_saga(execution, trace_context)
                    raise IntegrationError.from_code(
                        ErrorCode.E11403,
                        details={
                            "saga_id": saga.saga_id,
                            "execution_id": execution.execution_id,
                            "timeout_sec": saga.timeout_sec,
                        },
                    )

                # Execute step
                try:
                    await self._execute_step(step, execution, trace_context)
                except Exception as e:
                    logger.error(
                        f"Saga step failed: saga={saga.saga_name}, "
                        f"step={step.step_name}, error={e}"
                    )

                    # Check if step is required
                    if step.required:
                        # Compensate if auto-compensate enabled
                        if saga.auto_compensate:
                            await self._compensate_saga(execution, trace_context)
                        execution.fail(str(e))
                        raise IntegrationError.from_code(
                            ErrorCode.E11401,
                            details={
                                "saga_id": saga.saga_id,
                                "step_name": step.step_name,
                                "error": str(e),
                            },
                        )
                    else:
                        # Skip non-required step
                        step.status = StepStatus.SKIPPED
                        logger.warning(
                            f"Skipped non-required step: {step.step_name}"
                        )

            # Saga completed successfully
            execution.complete()

            # Update saga execution as completed in L01
            if self.l11_bridge:
                await self.l11_bridge.update_saga_execution(
                    saga_id=execution.execution_id,
                    status="completed",
                    steps_completed=len(saga.steps),
                    completed_at=execution.completed_at,
                )

            logger.info(
                f"Saga completed successfully: {saga.saga_name} "
                f"(execution_id={execution.execution_id})"
            )

            return execution

        except Exception as e:
            logger.error(
                f"Saga execution failed: {saga.saga_name}, error={e}"
            )
            if execution.status not in (SagaStatus.FAILED, SagaStatus.TIMEOUT):
                execution.fail(str(e))
            raise

    async def _execute_step(
        self,
        step: SagaStep,
        execution: SagaExecution,
        trace_context: RequestContext,
    ) -> None:
        """
        Execute a single saga step.

        Args:
            step: SagaStep to execute
            execution: SagaExecution
            trace_context: Request context

        Raises:
            Exception: If step execution fails
        """
        logger.debug(f"Executing saga step: {step.step_name}")

        step.start()

        # Record saga step in L01
        saga_step_id = f"{execution.execution_id}-step-{execution.current_step_index}"
        if self.l11_bridge:
            await self.l11_bridge.record_saga_step(
                step_id=saga_step_id,
                saga_id=execution.execution_id,
                step_name=step.step_name,
                step_index=execution.current_step_index,
                service_id=step.service_name or "local",
                status="executing",
            )

        # Retry loop
        while True:
            try:
                # Create child context for step
                child_context = trace_context.create_child_context()

                # Execute step action
                if step.action:
                    # Custom action function
                    output = await step.action(execution.context)
                    step.complete(output)
                    # Merge output into execution context
                    execution.context.update(output)

                elif step.service_name and step.endpoint:
                    # HTTP request to service
                    response = await self.request_orchestrator.route_request(
                        service_name=step.service_name,
                        method="POST",
                        path=step.endpoint,
                        data=execution.context,
                        context=child_context,
                        timeout=step.timeout_sec,
                    )
                    step.complete(response)
                    # Merge response into execution context
                    execution.context.update(response)

                else:
                    # No action defined
                    step.complete()

                # Update saga step in L01
                if self.l11_bridge:
                    await self.l11_bridge.update_saga_step(
                        step_id=step_id,
                        status="completed",
                        completed_at=step.completed_at,
                        response=step.output,
                    )

                logger.debug(f"Step completed: {step.step_name}")
                break

            except Exception as e:
                step.retry_count += 1
                step.fail(str(e))

                # Check if can retry
                if step.can_retry():
                    # Calculate exponential backoff with jitter
                    backoff_delay = calculate_backoff(
                        attempt=step.retry_count,
                        base_delay=1.0,
                        max_delay=30.0,
                        jitter=True
                    )
                    logger.warning(
                        f"Retrying step: {step.step_name} "
                        f"(attempt {step.retry_count}/{step.max_retries}, "
                        f"backoff={backoff_delay:.2f}s)"
                    )
                    await asyncio.sleep(backoff_delay)
                else:
                    logger.error(
                        f"Step exhausted retries: {step.step_name}"
                    )
                    # Update saga step as failed in L01
                    if self.l11_bridge:
                        await self.l11_bridge.update_saga_step(
                            step_id=step_id,
                            status="failed",
                            completed_at=datetime.utcnow(),
                            error_message=str(e),
                            retry_count=step.retry_count,
                        )
                    raise

    async def _compensate_saga(
        self,
        execution: SagaExecution,
        trace_context: RequestContext,
    ) -> None:
        """
        Compensate (rollback) a saga.

        Args:
            execution: SagaExecution to compensate
            trace_context: Request context
        """
        logger.info(
            f"Starting saga compensation: {execution.saga_definition.saga_name} "
            f"(execution_id={execution.execution_id})"
        )

        execution.start_compensation()

        # Update saga to compensating mode in L01
        if self.l11_bridge:
            await self.l11_bridge.update_saga_execution(
                saga_id=execution.execution_id,
                status="compensating",
                compensation_mode=True,
            )

        # Get completed steps in reverse order
        completed_steps = execution.get_completed_steps()
        completed_steps.reverse()

        # Compensate each completed step
        for step in completed_steps:
            if step.compensation:
                try:
                    logger.debug(f"Compensating step: {step.step_name}")
                    await step.compensation(execution.context)
                    step.compensate()
                    logger.debug(f"Step compensated: {step.step_name}")
                except Exception as e:
                    logger.error(
                        f"Compensation failed for step {step.step_name}: {e}"
                    )
                    # Continue compensating other steps
                    raise IntegrationError.from_code(
                        ErrorCode.E11402,
                        details={
                            "saga_id": execution.saga_definition.saga_id,
                            "step_name": step.step_name,
                            "error": str(e),
                        },
                    )

        logger.info(
            f"Saga compensation completed: {execution.saga_definition.saga_name}"
        )

    async def get_execution(self, execution_id: str) -> Optional[SagaExecution]:
        """
        Get saga execution by ID.

        Args:
            execution_id: Execution ID

        Returns:
            SagaExecution or None if not found
        """
        async with self._lock:
            return self._executions.get(execution_id)

    async def get_all_executions(self) -> list[SagaExecution]:
        """
        Get all saga executions.

        Returns:
            List of SagaExecution
        """
        async with self._lock:
            return list(self._executions.values())

    async def cancel_execution(self, execution_id: str) -> None:
        """
        Cancel a running saga execution.

        Args:
            execution_id: Execution ID

        Raises:
            IntegrationError: If execution not found
        """
        async with self._lock:
            if execution_id not in self._executions:
                raise IntegrationError.from_code(
                    ErrorCode.E11406,
                    details={"execution_id": execution_id},
                )

            execution = self._executions[execution_id]

            # Only cancel if running
            if execution.status == SagaStatus.RUNNING:
                logger.info(f"Cancelling saga execution: {execution_id}")
                execution.fail("Cancelled by user")

                # Compensate if auto-compensate enabled
                if execution.saga_definition.auto_compensate:
                    trace_context = RequestContext(
                        trace_id=execution.trace_id or "",
                        correlation_id=execution.correlation_id or "",
                    )
                    await self._compensate_saga(execution, trace_context)

    def get_metrics(self) -> Dict[str, Any]:
        """
        Get saga orchestrator metrics.

        Returns:
            Dictionary with metrics
        """
        metrics = {
            "total_executions": len(self._executions),
            "running": 0,
            "completed": 0,
            "failed": 0,
            "timeout": 0,
            "compensating": 0,
        }

        for execution in self._executions.values():
            if execution.status == SagaStatus.RUNNING:
                metrics["running"] += 1
            elif execution.status == SagaStatus.COMPLETED:
                metrics["completed"] += 1
            elif execution.status == SagaStatus.FAILED:
                metrics["failed"] += 1
            elif execution.status == SagaStatus.TIMEOUT:
                metrics["timeout"] += 1
            elif execution.status == SagaStatus.COMPENSATING:
                metrics["compensating"] += 1

        return metrics

    async def get_execution_trace(
        self,
        execution_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get distributed trace for a saga execution.

        Provides complete visibility into saga execution including
        all steps, timings, and any errors.

        Args:
            execution_id: Execution ID to trace

        Returns:
            Trace data or None if not found
        """
        execution = await self.get_execution(execution_id)
        if not execution:
            return None

        trace = {
            "execution_id": execution_id,
            "saga_name": execution.saga_definition.saga_name,
            "trace_id": execution.trace_id,
            "correlation_id": execution.correlation_id,
            "status": execution.status.value if hasattr(execution.status, 'value') else str(execution.status),
            "started_at": execution.started_at.isoformat() if execution.started_at else None,
            "completed_at": execution.completed_at.isoformat() if execution.completed_at else None,
            "duration_ms": None,
            "steps": [],
            "context_snapshot": dict(execution.context),
        }

        # Calculate duration
        if execution.started_at and execution.completed_at:
            trace["duration_ms"] = (
                execution.completed_at - execution.started_at
            ).total_seconds() * 1000

        # Build step traces
        for step_idx, step in enumerate(execution.saga_definition.steps):
            step_trace = {
                "step_name": step.step_name,
                "step_index": step_idx,
                "status": step.status.value if hasattr(step.status, 'value') else str(step.status),
                "service_name": step.service_name,
                "endpoint": step.endpoint,
                "started_at": step.started_at.isoformat() if step.started_at else None,
                "completed_at": step.completed_at.isoformat() if step.completed_at else None,
                "retry_count": step.retry_count,
                "max_retries": step.max_retries,
                "error": step.error,
                "compensated": step.status == StepStatus.COMPENSATED,
            }

            # Calculate step duration
            if step.started_at and step.completed_at:
                step_trace["duration_ms"] = (
                    step.completed_at - step.started_at
                ).total_seconds() * 1000

            trace["steps"].append(step_trace)

        return trace

    async def list_executions(
        self,
        status_filter: Optional[SagaStatus] = None,
        saga_name_filter: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        List saga executions with optional filters.

        Args:
            status_filter: Filter by status
            saga_name_filter: Filter by saga name
            limit: Maximum results

        Returns:
            List of execution summaries
        """
        executions = list(self._executions.values())

        # Apply filters
        if status_filter:
            executions = [e for e in executions if e.status == status_filter]

        if saga_name_filter:
            executions = [
                e for e in executions
                if saga_name_filter.lower() in e.saga_definition.saga_name.lower()
            ]

        # Sort by start time (newest first)
        executions.sort(
            key=lambda e: e.started_at or datetime.min.replace(tzinfo=timezone.utc),
            reverse=True
        )

        # Build summaries
        summaries = []
        for execution in executions[:limit]:
            summaries.append({
                "execution_id": execution.execution_id,
                "saga_name": execution.saga_definition.saga_name,
                "status": execution.status.value if hasattr(execution.status, 'value') else str(execution.status),
                "started_at": execution.started_at.isoformat() if execution.started_at else None,
                "completed_at": execution.completed_at.isoformat() if execution.completed_at else None,
                "steps_total": len(execution.saga_definition.steps),
                "current_step": execution.current_step_index,
            })

        return summaries

    async def retry_failed_execution(
        self,
        execution_id: str,
        from_step: Optional[int] = None
    ) -> SagaExecution:
        """
        Retry a failed saga execution.

        Args:
            execution_id: Failed execution ID
            from_step: Step index to retry from (default: failed step)

        Returns:
            New SagaExecution

        Raises:
            IntegrationError: If execution not found or not retriable
        """
        original = await self.get_execution(execution_id)
        if not original:
            raise IntegrationError.from_code(
                ErrorCode.E11406,
                details={"execution_id": execution_id}
            )

        if original.status not in (SagaStatus.FAILED, SagaStatus.TIMEOUT):
            raise IntegrationError.from_code(
                ErrorCode.E11401,
                details={
                    "execution_id": execution_id,
                    "status": str(original.status),
                    "message": "Only failed or timeout executions can be retried"
                }
            )

        logger.info(
            f"Retrying saga execution: {execution_id} "
            f"from step {from_step or original.current_step_index}"
        )

        # Create new execution with original context
        trace_context = RequestContext(
            trace_id=original.trace_id or "",
            correlation_id=original.correlation_id or "",
        )

        # Execute saga again
        return await self.execute_saga(
            saga=original.saga_definition,
            context=original.context,
            trace_context=trace_context
        )

    def get_health_status(self) -> Dict[str, Any]:
        """
        Get orchestrator health status.

        Returns:
            Health status dictionary
        """
        metrics = self.get_metrics()

        # Calculate success rate
        completed = metrics.get("completed", 0)
        failed = metrics.get("failed", 0) + metrics.get("timeout", 0)
        total = completed + failed

        success_rate = (completed / total * 100) if total > 0 else 100.0

        return {
            "healthy": success_rate >= 90.0,  # Healthy if >= 90% success
            "success_rate_percent": round(success_rate, 2),
            "active_executions": metrics.get("running", 0) + metrics.get("compensating", 0),
            "total_executions": metrics.get("total_executions", 0),
            "l11_bridge_connected": self.l11_bridge is not None,
        }
