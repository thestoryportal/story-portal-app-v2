"""
L10 Human Interface - L01 Data Layer Bridge

Bridge between L10 Human Interface and L01 Data Layer for persistent interaction tracking.
Records user interactions and control operations.
"""

import logging
from typing import Optional
from datetime import datetime
from uuid import UUID, uuid4

from src.L01_data_layer.client import L01Client

logger = logging.getLogger(__name__)


class L10Bridge:
    """
    Bridge between L10 Human Interface and L01 Data Layer.

    Responsibilities:
    - Record user interactions with dashboard
    - Track manual control operations on agents
    - Log human-in-the-loop workflows
    """

    def __init__(self, l01_base_url: str = "http://localhost:8002", api_key: Optional[str] = None):
        """Initialize L10 bridge.

        Args:
            l01_base_url: Base URL for L01 Data Layer API
            api_key: Optional API key for L01 authentication
        """
        self.l01_client = L01Client(base_url=l01_base_url, api_key=api_key)
        self.enabled = True
        logger.info(f"L10Bridge initialized with base_url={l01_base_url}")

    async def initialize(self) -> None:
        """Initialize bridge (async setup if needed)."""
        logger.info("L10Bridge initialized")

    async def record_user_interaction(
        self,
        timestamp: datetime,
        interaction_type: str,
        action: str,
        user_id: Optional[str] = None,
        target_type: Optional[str] = None,
        target_id: Optional[str] = None,
        parameters: Optional[dict] = None,
        result: Optional[str] = None,
        error_message: Optional[str] = None,
        client_ip: Optional[str] = None,
        user_agent: Optional[str] = None,
        session_id: Optional[str] = None,
        metadata: Optional[dict] = None
    ) -> bool:
        """Record a user interaction in L01.

        Args:
            timestamp: Interaction timestamp
            interaction_type: Type of interaction (click, view, search, etc.)
            action: Specific action taken
            user_id: User identifier
            target_type: Type of target (agent, goal, task, etc.)
            target_id: Target identifier
            parameters: Interaction parameters
            result: Interaction result (success, failure, etc.)
            error_message: Error message if interaction failed
            client_ip: Client IP address
            user_agent: Client user agent
            session_id: Session identifier
            metadata: Additional metadata

        Returns:
            True if recorded successfully, False otherwise
        """
        if not self.enabled:
            return False

        try:
            interaction_id = f"ui-{uuid4()}"

            await self.l01_client.record_user_interaction(
                interaction_id=interaction_id,
                timestamp=timestamp.isoformat(),
                interaction_type=interaction_type,
                action=action,
                user_id=user_id,
                target_type=target_type,
                target_id=target_id,
                parameters=parameters,
                result=result,
                error_message=error_message,
                client_ip=client_ip,
                user_agent=user_agent,
                session_id=session_id,
                metadata=metadata
            )

            logger.debug(
                f"Recorded user interaction {interaction_id} in L01 "
                f"(type={interaction_type}, action={action})"
            )
            return True

        except Exception as e:
            logger.error(f"Failed to record user interaction in L01: {e}")
            return False

    async def record_control_operation(
        self,
        timestamp: datetime,
        user_id: str,
        operation_type: str,
        command: str,
        target_agent_id: Optional[UUID] = None,
        target_agent_did: Optional[str] = None,
        parameters: Optional[dict] = None,
        status: str = "pending",
        metadata: Optional[dict] = None
    ) -> str:
        """Record a control operation in L01.

        Args:
            timestamp: Operation timestamp
            user_id: User who initiated the operation
            operation_type: Type of operation (agent_control, system_config, etc.)
            command: Specific command (start, stop, pause, resume, etc.)
            target_agent_id: Target agent UUID
            target_agent_did: Target agent DID
            parameters: Operation parameters
            status: Operation status (pending, executing, completed, failed)
            metadata: Additional metadata

        Returns:
            operation_id if recorded successfully, empty string otherwise
        """
        if not self.enabled:
            return ""

        try:
            operation_id = f"ctrl-{uuid4()}"

            await self.l01_client.record_control_operation(
                operation_id=operation_id,
                timestamp=timestamp.isoformat(),
                user_id=user_id,
                operation_type=operation_type,
                command=command,
                target_agent_id=target_agent_id,
                target_agent_did=target_agent_did,
                parameters=parameters,
                status=status,
                metadata=metadata
            )

            logger.info(
                f"Recorded control operation {operation_id} in L01 "
                f"(type={operation_type}, command={command}, status={status})"
            )
            return operation_id

        except Exception as e:
            logger.error(f"Failed to record control operation in L01: {e}")
            return ""

    async def update_control_operation(
        self,
        operation_id: str,
        status: Optional[str] = None,
        result: Optional[dict] = None,
        error_message: Optional[str] = None,
        executed_at: Optional[datetime] = None,
        completed_at: Optional[datetime] = None
    ) -> bool:
        """Update a control operation status in L01.

        Args:
            operation_id: Operation ID to update
            status: New status
            result: Operation result
            error_message: Error message if failed
            executed_at: Timestamp when execution started
            completed_at: Timestamp when execution completed

        Returns:
            True if updated successfully, False otherwise
        """
        if not self.enabled:
            return False

        try:
            await self.l01_client.update_control_operation(
                operation_id=operation_id,
                status=status,
                result=result,
                error_message=error_message,
                executed_at=executed_at.isoformat() if executed_at else None,
                completed_at=completed_at.isoformat() if completed_at else None
            )

            logger.info(
                f"Updated control operation {operation_id} in L01 (status={status})"
            )
            return True

        except Exception as e:
            logger.error(f"Failed to update control operation in L01: {e}")
            return False

    async def cleanup(self) -> None:
        """Cleanup bridge resources."""
        try:
            await self.l01_client.close()
            logger.info("L10Bridge cleanup complete")
        except Exception as e:
            logger.warning(f"L10Bridge cleanup failed: {e}")
