"""
L11 Integration Layer - Saga Orchestrator.

Multi-step workflow orchestration with automatic compensation (rollback).
"""

import asyncio
import logging
from typing import Dict, Optional, Any

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


class SagaOrchestrator:
    """
    Saga orchestrator for multi-step workflows.

    Executes multi-step operations across layers with automatic
    compensation (rollback) on failure.
    """

    def __init__(self, request_orchestrator: RequestOrchestrator):
        """
        Initialize saga orchestrator.

        Args:
            request_orchestrator: RequestOrchestrator instance
        """
        self.request_orchestrator = request_orchestrator
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

                logger.debug(f"Step completed: {step.step_name}")
                break

            except Exception as e:
                step.retry_count += 1
                step.fail(str(e))

                # Check if can retry
                if step.can_retry():
                    logger.warning(
                        f"Retrying step: {step.step_name} "
                        f"(attempt {step.retry_count}/{step.max_retries})"
                    )
                    await asyncio.sleep(1)  # Backoff
                else:
                    logger.error(
                        f"Step exhausted retries: {step.step_name}"
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
