"""
L11 Integration Layer - L01 Data Layer Bridge

Bridge between L11 Integration Layer and L01 Data Layer for persistent orchestration tracking.
Records saga executions, circuit breaker events, and service registry changes.
"""

import logging
from typing import Optional, List
from datetime import datetime
from uuid import uuid4

from L01_data_layer.client import L01Client

logger = logging.getLogger(__name__)


class L11Bridge:
    """
    Bridge between L11 Integration Layer and L01 Data Layer.

    Responsibilities:
    - Record saga execution for distributed transactions
    - Track saga step execution and compensation
    - Record circuit breaker state changes
    - Track service registry events (registration, deregistration, health changes)
    """

    def __init__(self, l01_base_url: str = "http://localhost:8002"):
        """Initialize L11 bridge.

        Args:
            l01_base_url: Base URL for L01 Data Layer API
        """
        self.l01_client = L01Client(base_url=l01_base_url)
        self.enabled = True
        logger.info(f"L11Bridge initialized with base_url={l01_base_url}")

    async def initialize(self) -> None:
        """Initialize bridge (async setup if needed)."""
        logger.info("L11Bridge initialized")

    # ===================================================================
    # Saga Execution Methods
    # ===================================================================

    async def record_saga_execution(
        self,
        saga_id: str,
        saga_name: str,
        started_at: datetime,
        steps_total: int,
        status: str = "running",
        context: Optional[dict] = None,
        metadata: Optional[dict] = None
    ) -> bool:
        """Record a saga execution in L01.

        Args:
            saga_id: Unique saga identifier
            saga_name: Name of the saga
            started_at: Saga start timestamp
            steps_total: Total number of steps
            status: Saga status (running, completed, failed, compensating)
            context: Saga execution context
            metadata: Additional metadata

        Returns:
            True if recorded successfully, False otherwise
        """
        if not self.enabled:
            return False

        try:
            await self.l01_client.record_saga_execution(
                saga_id=saga_id,
                saga_name=saga_name,
                started_at=started_at.isoformat(),
                steps_total=steps_total,
                status=status,
                context=context,
                metadata=metadata
            )

            logger.info(
                f"Recorded saga execution {saga_id} in L01 "
                f"(name={saga_name}, steps={steps_total}, status={status})"
            )
            return True

        except Exception as e:
            logger.error(f"Failed to record saga execution in L01: {e}")
            return False

    async def update_saga_execution(
        self,
        saga_id: str,
        status: Optional[str] = None,
        steps_completed: Optional[int] = None,
        steps_failed: Optional[int] = None,
        current_step: Optional[str] = None,
        compensation_mode: Optional[bool] = None,
        completed_at: Optional[datetime] = None,
        error_message: Optional[str] = None
    ) -> bool:
        """Update a saga execution in L01.

        Args:
            saga_id: Saga ID to update
            status: New status
            steps_completed: Number of steps completed
            steps_failed: Number of steps failed
            current_step: Current step name
            compensation_mode: Whether in compensation mode
            completed_at: Completion timestamp
            error_message: Error message if failed

        Returns:
            True if updated successfully, False otherwise
        """
        if not self.enabled:
            return False

        try:
            await self.l01_client.update_saga_execution(
                saga_id=saga_id,
                status=status,
                steps_completed=steps_completed,
                steps_failed=steps_failed,
                current_step=current_step,
                compensation_mode=compensation_mode,
                completed_at=completed_at.isoformat() if completed_at else None,
                error_message=error_message
            )

            logger.info(f"Updated saga execution {saga_id} in L01 (status={status})")
            return True

        except Exception as e:
            logger.error(f"Failed to update saga execution in L01: {e}")
            return False

    async def record_saga_step(
        self,
        step_id: str,
        saga_id: str,
        step_name: str,
        step_index: int,
        service_id: str,
        request: Optional[dict] = None,
        status: str = "pending",
        metadata: Optional[dict] = None
    ) -> bool:
        """Record a saga step in L01.

        Args:
            step_id: Unique step identifier
            saga_id: Parent saga ID
            step_name: Name of the step
            step_index: Step index in saga
            service_id: Service executing the step
            request: Step request data
            status: Step status (pending, executing, completed, failed, compensated)
            metadata: Additional metadata

        Returns:
            True if recorded successfully, False otherwise
        """
        if not self.enabled:
            return False

        try:
            await self.l01_client.record_saga_step(
                step_id=step_id,
                saga_id=saga_id,
                step_name=step_name,
                step_index=step_index,
                service_id=service_id,
                request=request,
                status=status,
                metadata=metadata
            )

            logger.debug(
                f"Recorded saga step {step_id} in L01 "
                f"(saga={saga_id}, step={step_name}, status={status})"
            )
            return True

        except Exception as e:
            logger.error(f"Failed to record saga step in L01: {e}")
            return False

    async def update_saga_step(
        self,
        step_id: str,
        status: Optional[str] = None,
        started_at: Optional[datetime] = None,
        completed_at: Optional[datetime] = None,
        response: Optional[dict] = None,
        error_message: Optional[str] = None,
        compensation_executed: Optional[bool] = None,
        compensation_result: Optional[dict] = None,
        retry_count: Optional[int] = None
    ) -> bool:
        """Update a saga step in L01.

        Args:
            step_id: Step ID to update
            status: New status
            started_at: Step start timestamp
            completed_at: Step completion timestamp
            response: Step response data
            error_message: Error message if failed
            compensation_executed: Whether compensation was executed
            compensation_result: Compensation result
            retry_count: Number of retries

        Returns:
            True if updated successfully, False otherwise
        """
        if not self.enabled:
            return False

        try:
            await self.l01_client.update_saga_step(
                step_id=step_id,
                status=status,
                started_at=started_at.isoformat() if started_at else None,
                completed_at=completed_at.isoformat() if completed_at else None,
                response=response,
                error_message=error_message,
                compensation_executed=compensation_executed,
                compensation_result=compensation_result,
                retry_count=retry_count
            )

            logger.debug(f"Updated saga step {step_id} in L01 (status={status})")
            return True

        except Exception as e:
            logger.error(f"Failed to update saga step in L01: {e}")
            return False

    # ===================================================================
    # Circuit Breaker Methods
    # ===================================================================

    async def record_circuit_breaker_event(
        self,
        timestamp: datetime,
        service_id: str,
        circuit_name: str,
        event_type: str,
        state_to: str,
        state_from: Optional[str] = None,
        failure_count: Optional[int] = None,
        success_count: Optional[int] = None,
        failure_threshold: Optional[int] = None,
        timeout_seconds: Optional[int] = None,
        error_message: Optional[str] = None,
        metadata: Optional[dict] = None
    ) -> bool:
        """Record a circuit breaker event in L01.

        Args:
            timestamp: Event timestamp
            service_id: Service identifier
            circuit_name: Circuit breaker name
            event_type: Event type (state_change, failure, success, timeout)
            state_to: New state (closed, open, half_open)
            state_from: Previous state
            failure_count: Current failure count
            success_count: Current success count
            failure_threshold: Failure threshold for opening
            timeout_seconds: Timeout before half-open attempt
            error_message: Error message if applicable
            metadata: Additional metadata

        Returns:
            True if recorded successfully, False otherwise
        """
        if not self.enabled:
            return False

        try:
            event_id = f"cb-{uuid4()}"

            await self.l01_client.record_circuit_breaker_event(
                event_id=event_id,
                timestamp=timestamp.isoformat(),
                service_id=service_id,
                circuit_name=circuit_name,
                event_type=event_type,
                state_to=state_to,
                state_from=state_from,
                failure_count=failure_count,
                success_count=success_count,
                failure_threshold=failure_threshold,
                timeout_seconds=timeout_seconds,
                error_message=error_message,
                metadata=metadata
            )

            logger.info(
                f"Recorded circuit breaker event {event_id} in L01 "
                f"(service={service_id}, circuit={circuit_name}, "
                f"state={state_from}->{state_to})"
            )
            return True

        except Exception as e:
            logger.error(f"Failed to record circuit breaker event in L01: {e}")
            return False

    # ===================================================================
    # Service Registry Methods
    # ===================================================================

    async def record_service_registry_event(
        self,
        timestamp: datetime,
        service_id: str,
        event_type: str,
        layer: Optional[str] = None,
        host: Optional[str] = None,
        port: Optional[int] = None,
        health_status: Optional[str] = None,
        capabilities: Optional[List[str]] = None,
        metadata: Optional[dict] = None
    ) -> bool:
        """Record a service registry event in L01.

        Args:
            timestamp: Event timestamp
            service_id: Service identifier
            event_type: Event type (registered, deregistered, health_change, metadata_update)
            layer: Layer identifier (L01, L02, etc.)
            host: Service host
            port: Service port
            health_status: Health status (healthy, unhealthy, degraded)
            capabilities: Service capabilities
            metadata: Additional metadata

        Returns:
            True if recorded successfully, False otherwise
        """
        if not self.enabled:
            return False

        try:
            event_id = f"sr-{uuid4()}"

            await self.l01_client.record_service_registry_event(
                event_id=event_id,
                timestamp=timestamp.isoformat(),
                service_id=service_id,
                event_type=event_type,
                layer=layer,
                host=host,
                port=port,
                health_status=health_status,
                capabilities=capabilities,
                metadata=metadata
            )

            logger.info(
                f"Recorded service registry event {event_id} in L01 "
                f"(service={service_id}, event={event_type}, layer={layer})"
            )
            return True

        except Exception as e:
            logger.error(f"Failed to record service registry event in L01: {e}")
            return False

    async def cleanup(self) -> None:
        """Cleanup bridge resources."""
        try:
            await self.l01_client.close()
            logger.info("L11Bridge cleanup complete")
        except Exception as e:
            logger.warning(f"L11Bridge cleanup failed: {e}")
