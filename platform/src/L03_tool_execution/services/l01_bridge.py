"""
L03 Tool Execution - L01 Data Layer Bridge

Bridge between L03 Tool Execution and L01 Data Layer for persistent tool execution tracking.

This bridge records tool invocations and results in L01 for cross-layer access,
audit trails, and analytics.
"""

import logging
from typing import Optional
from uuid import UUID
from datetime import datetime

from ...L01_data_layer.client import L01Client
from ..models.tool_result import (
    ToolInvokeRequest,
    ToolInvokeResponse,
    ToolStatus
)


logger = logging.getLogger(__name__)


class L03Bridge:
    """
    Bridge between L03 Tool Execution Layer and L01 Data Layer.

    Responsibilities:
    - Record tool invocations in L01 when execution starts
    - Update execution records with results, errors, and metadata
    - Track resource usage, documents accessed, and checkpoints
    - Publish tool execution events via L01 event stream
    """

    def __init__(self, l01_base_url: str = "http://localhost:8002"):
        """Initialize L03 bridge.

        Args:
            l01_base_url: Base URL for L01 Data Layer API
        """
        self.l01_client = L01Client(base_url=l01_base_url)
        self.enabled = True
        logger.info(f"L03Bridge initialized with base_url={l01_base_url}")

    async def initialize(self) -> None:
        """Initialize bridge (async setup if needed)."""
        logger.info("L03Bridge initialized")

    async def record_invocation_start(
        self,
        request: ToolInvokeRequest
    ) -> bool:
        """Record tool invocation start in L01.

        Args:
            request: ToolInvokeRequest instance

        Returns:
            True if recorded successfully, False otherwise
        """
        if not self.enabled:
            return False

        try:
            # Extract agent context
            agent_id = None
            agent_did = None
            tenant_id = None
            session_id = None
            parent_sandbox_id = None

            if request.agent_context:
                agent_did = request.agent_context.agent_did
                tenant_id = request.agent_context.tenant_id
                session_id = request.agent_context.session_id
                parent_sandbox_id = request.agent_context.parent_sandbox_id

            # Extract resource limits
            cpu_limit = None
            memory_limit = None
            timeout = None

            if request.resource_limits:
                cpu_limit = request.resource_limits.cpu_millicore_limit
                memory_limit = request.resource_limits.memory_mb_limit
                timeout = request.resource_limits.timeout_seconds

            # Extract execution options
            async_mode = False
            priority = 5
            idempotency_key = None
            require_approval = False

            if request.execution_options:
                async_mode = request.execution_options.async_mode
                priority = request.execution_options.priority
                idempotency_key = request.execution_options.idempotency_key
                require_approval = request.execution_options.require_approval or False

            # Record in L01
            await self.l01_client.record_tool_execution(
                invocation_id=request.invocation_id,
                tool_name=request.tool_id,
                input_params=request.parameters,
                tool_version=request.tool_version,
                agent_did=agent_did,
                tenant_id=tenant_id,
                session_id=session_id,
                parent_sandbox_id=parent_sandbox_id,
                status="pending",
                async_mode=async_mode,
                priority=priority,
                idempotency_key=idempotency_key,
                require_approval=require_approval,
                cpu_millicore_limit=cpu_limit,
                memory_mb_limit=memory_limit,
                timeout_seconds=timeout
            )

            logger.info(f"Recorded tool invocation {request.invocation_id} in L01")
            return True

        except Exception as e:
            logger.error(f"Failed to record tool invocation in L01: {e}")
            return False

    async def update_invocation_status(
        self,
        invocation_id: UUID,
        status: ToolStatus
    ) -> bool:
        """Update tool invocation status in L01.

        Args:
            invocation_id: Tool invocation ID
            status: Current status

        Returns:
            True if updated successfully, False otherwise
        """
        if not self.enabled:
            return False

        try:
            await self.l01_client.update_tool_execution(
                invocation_id=invocation_id,
                status=status.value
            )

            logger.debug(f"Updated tool invocation {invocation_id} status to {status.value}")
            return True

        except Exception as e:
            logger.error(f"Failed to update tool invocation status in L01: {e}")
            return False

    async def record_invocation_result(
        self,
        response: ToolInvokeResponse,
        started_at: Optional[datetime] = None
    ) -> bool:
        """Record tool invocation result in L01.

        Args:
            response: ToolInvokeResponse instance
            started_at: Optional execution start time

        Returns:
            True if recorded successfully, False otherwise
        """
        if not self.enabled:
            return False

        try:
            # Prepare update data
            updates = {
                "status": response.status.value,
                "completed_at": response.completed_at.isoformat() if response.completed_at else None
            }

            # Add result if success
            if response.result:
                updates["output_result"] = response.result.to_dict()

            # Add error if failed
            if response.error:
                updates["error_code"] = response.error.code
                updates["error_message"] = response.error.message
                updates["error_details"] = response.error.details
                updates["retryable"] = response.error.retryable

            # Add execution metadata
            if response.execution_metadata:
                metadata = response.execution_metadata
                if metadata.duration_ms is not None:
                    updates["duration_ms"] = metadata.duration_ms
                if metadata.cpu_used_millicore_seconds is not None:
                    updates["cpu_used_millicore_seconds"] = metadata.cpu_used_millicore_seconds
                if metadata.memory_peak_mb is not None:
                    updates["memory_peak_mb"] = metadata.memory_peak_mb
                if metadata.network_bytes_sent is not None:
                    updates["network_bytes_sent"] = metadata.network_bytes_sent
                if metadata.network_bytes_received is not None:
                    updates["network_bytes_received"] = metadata.network_bytes_received
                if metadata.documents_accessed:
                    # Convert to list of strings (document IDs)
                    updates["documents_accessed"] = [
                        doc.get("document_id", "") if isinstance(doc, dict) else str(doc)
                        for doc in metadata.documents_accessed
                    ]
                if metadata.checkpoints_created:
                    # Convert to list of strings (checkpoint IDs)
                    updates["checkpoints_created"] = [
                        cp.get("checkpoint_id", "") if isinstance(cp, dict) else str(cp)
                        for cp in metadata.checkpoints_created
                    ]

            # Add checkpoint reference
            if response.checkpoint_ref:
                updates["checkpoint_ref"] = response.checkpoint_ref

            # Add started_at if provided
            if started_at:
                updates["started_at"] = started_at.isoformat()

            # Update in L01
            await self.l01_client.update_tool_execution(
                invocation_id=response.invocation_id,
                **updates
            )

            logger.info(
                f"Recorded tool invocation result {response.invocation_id} "
                f"in L01 (status={response.status.value})"
            )
            return True

        except Exception as e:
            logger.error(f"Failed to record tool invocation result in L01: {e}")
            return False

    async def get_execution_history(
        self,
        invocation_id: UUID
    ) -> Optional[dict]:
        """Get tool execution history from L01.

        Args:
            invocation_id: Tool invocation ID

        Returns:
            Execution record dict or None if not found
        """
        if not self.enabled:
            return None

        try:
            execution = await self.l01_client.get_tool_execution_by_invocation(invocation_id)
            logger.debug(f"Retrieved execution history for {invocation_id} from L01")
            return execution

        except Exception as e:
            logger.error(f"Failed to get execution history from L01: {e}")
            return None

    async def cleanup(self) -> None:
        """Cleanup bridge resources."""
        try:
            await self.l01_client.close()
            logger.info("L03Bridge cleanup complete")
        except Exception as e:
            logger.warning(f"L03Bridge cleanup failed: {e}")
