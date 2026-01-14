"""
Session Bridge

Integrates with L01 Phase 16 Session Orchestration (MCP context-orchestrator)
for session lifecycle and state persistence.

Based on Section 3.3.6 of agent-runtime-layer-specification-v1.2-final-ASCII.md
"""

import asyncio
import json
import logging
import subprocess
from typing import Dict, Any, Optional, List
from datetime import datetime

from ..models import AgentState


logger = logging.getLogger(__name__)


class SessionError(Exception):
    """Session bridge error"""
    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(f"[{code}] {message}")


class SessionBridge:
    """
    Bridge to L01 Phase 16 Session Orchestration via MCP.

    Responsibilities:
    - Start and stop sessions
    - Send heartbeats to maintain session liveness
    - Save context snapshots
    - Check for recovery scenarios
    - Manage session lifecycle
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize SessionBridge.

        Args:
            config: Configuration dict with:
                - endpoint: MCP server endpoint
                - heartbeat_interval_seconds: Heartbeat interval
                - heartbeat_timeout_seconds: Heartbeat timeout
                - retry_policy: Retry configuration
                - enable_recovery_check: Enable recovery checking
                - mcp_server_path: Path to MCP server executable
        """
        self.config = config or {}

        # Configuration
        self.endpoint = self.config.get(
            "endpoint",
            "mcp-context-orchestrator"
        )
        self.heartbeat_interval = self.config.get("heartbeat_interval_seconds", 30)
        self.heartbeat_timeout = self.config.get("heartbeat_timeout_seconds", 5)
        self.enable_recovery_check = self.config.get("enable_recovery_check", True)

        # Retry policy
        retry_policy = self.config.get("retry_policy", {})
        self.max_retries = retry_policy.get("max_retries", 3)
        self.backoff_multiplier = retry_policy.get("backoff_multiplier", 2)

        # MCP server configuration
        self.mcp_server_path = self.config.get(
            "mcp_server_path",
            "node"
        )
        self.mcp_server_script = self.config.get(
            "mcp_server_script",
            "/Volumes/Extreme SSD/projects/story-portal-app/platform/services/"
            "mcp-context-orchestrator/src/index.ts"
        )

        # Active sessions: session_id -> session data
        self._sessions: Dict[str, Dict[str, Any]] = {}

        # Heartbeat tasks: session_id -> asyncio.Task
        self._heartbeat_tasks: Dict[str, asyncio.Task] = {}

        logger.info(
            f"SessionBridge initialized: endpoint={self.endpoint}, "
            f"heartbeat_interval={self.heartbeat_interval}s"
        )

    async def initialize(self) -> None:
        """Initialize session bridge"""
        # Check if MCP server is accessible
        try:
            result = await self._call_mcp_tool(
                "check_recovery",
                {}
            )
            logger.info("MCP context-orchestrator connection verified")
        except Exception as e:
            logger.warning(f"Failed to verify MCP connection: {e}")

        logger.info("SessionBridge initialization complete")

    async def start_session(
        self,
        agent_id: str,
        session_id: str,
        initial_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Start a new session.

        Args:
            agent_id: Agent identifier
            session_id: Session identifier
            initial_context: Optional initial context

        Returns:
            Session information

        Raises:
            SessionError: If session start fails
        """
        logger.info(f"Starting session {session_id} for agent {agent_id}")

        try:
            # Call MCP to initialize session
            # Using save_context_snapshot to establish the session
            result = await self._call_mcp_tool(
                "save_context_snapshot",
                {
                    "taskId": session_id,
                    "sessionId": agent_id,
                    "updates": {
                        "status": "in_progress",
                        "currentPhase": "initialization",
                        "immediateContext": {
                            "workingOn": "Agent initialization",
                            "lastAction": "Session started",
                            "nextStep": "Begin execution",
                            "blockers": [],
                        },
                    },
                    "changeSummary": f"Session started for agent {agent_id}",
                }
            )

            # Store session data
            self._sessions[session_id] = {
                "agent_id": agent_id,
                "session_id": session_id,
                "started_at": datetime.utcnow(),
                "last_heartbeat": datetime.utcnow(),
            }

            # Start heartbeat task
            self._heartbeat_tasks[session_id] = asyncio.create_task(
                self._heartbeat_loop(session_id)
            )

            logger.info(f"Session {session_id} started successfully")

            return {
                "session_id": session_id,
                "agent_id": agent_id,
                "status": "active",
            }

        except Exception as e:
            logger.error(f"Failed to start session {session_id}: {e}")
            raise SessionError(
                code="E2050",
                message=f"Session start failed: {str(e)}"
            )

    async def stop_session(
        self,
        session_id: str,
        reason: str = "normal_termination"
    ) -> None:
        """
        Stop a session.

        Args:
            session_id: Session identifier
            reason: Termination reason

        Raises:
            SessionError: If session stop fails
        """
        logger.info(f"Stopping session {session_id} (reason: {reason})")

        # Cancel heartbeat task
        if session_id in self._heartbeat_tasks:
            task = self._heartbeat_tasks[session_id]
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
            del self._heartbeat_tasks[session_id]

        # Update session status in MCP
        try:
            await self._call_mcp_tool(
                "save_context_snapshot",
                {
                    "taskId": session_id,
                    "updates": {
                        "status": "completed" if reason == "normal_termination" else "archived",
                        "immediateContext": {
                            "workingOn": None,
                            "lastAction": f"Session stopped: {reason}",
                            "nextStep": None,
                            "blockers": [],
                        },
                    },
                    "changeSummary": f"Session stopped: {reason}",
                }
            )
        except Exception as e:
            logger.warning(f"Failed to update session status in MCP: {e}")

        # Remove from active sessions
        if session_id in self._sessions:
            del self._sessions[session_id]

        logger.info(f"Session {session_id} stopped")

    async def save_snapshot(
        self,
        session_id: str,
        context: Dict[str, Any],
        change_summary: Optional[str] = None
    ) -> None:
        """
        Save context snapshot for a session.

        Args:
            session_id: Session identifier
            context: Context data to save
            change_summary: Description of changes

        Raises:
            SessionError: If snapshot save fails
        """
        logger.debug(f"Saving snapshot for session {session_id}")

        try:
            await self._call_mcp_tool(
                "save_context_snapshot",
                {
                    "taskId": session_id,
                    "updates": context,
                    "changeSummary": change_summary or "Context snapshot",
                }
            )

        except Exception as e:
            logger.error(f"Failed to save snapshot for session {session_id}: {e}")
            raise SessionError(
                code="E2052",
                message=f"Snapshot save failed: {str(e)}"
            )

    async def get_unified_context(
        self,
        session_id: str
    ) -> Dict[str, Any]:
        """
        Get unified context for a session.

        Args:
            session_id: Session identifier

        Returns:
            Unified context data

        Raises:
            SessionError: If context retrieval fails
        """
        try:
            result = await self._call_mcp_tool(
                "get_unified_context",
                {
                    "taskId": session_id,
                    "includeRelationships": True,
                    "includeVersionHistory": False,
                }
            )

            return result

        except Exception as e:
            logger.error(f"Failed to get context for session {session_id}: {e}")
            raise SessionError(
                code="E2054",
                message=f"Failed to get session context: {str(e)}"
            )

    async def check_recovery(self) -> List[Dict[str, Any]]:
        """
        Check for sessions needing recovery.

        Returns:
            List of sessions needing recovery

        Raises:
            SessionError: If recovery check fails
        """
        if not self.enable_recovery_check:
            return []

        try:
            result = await self._call_mcp_tool(
                "check_recovery",
                {
                    "includeHistory": False,
                }
            )

            # Parse recovery information
            recovery_sessions = result.get("needsRecovery", [])
            logger.info(f"Found {len(recovery_sessions)} sessions needing recovery")

            return recovery_sessions

        except Exception as e:
            logger.error(f"Failed to check recovery: {e}")
            raise SessionError(
                code="E2053",
                message=f"Recovery check failed: {str(e)}"
            )

    async def _heartbeat_loop(self, session_id: str) -> None:
        """
        Heartbeat loop for a session.

        Args:
            session_id: Session identifier
        """
        logger.info(f"Starting heartbeat loop for session {session_id}")

        while True:
            try:
                await asyncio.sleep(self.heartbeat_interval)

                # Send heartbeat via snapshot save
                await self.save_snapshot(
                    session_id=session_id,
                    context={
                        "immediateContext": {
                            "lastAction": "Heartbeat",
                        },
                    },
                    change_summary="Heartbeat",
                )

                # Update last heartbeat time
                if session_id in self._sessions:
                    self._sessions[session_id]["last_heartbeat"] = datetime.utcnow()

                logger.debug(f"Heartbeat sent for session {session_id}")

            except asyncio.CancelledError:
                logger.info(f"Heartbeat loop cancelled for session {session_id}")
                break
            except Exception as e:
                logger.error(f"Heartbeat failed for session {session_id}: {e}")
                # Continue trying

    async def _call_mcp_tool(
        self,
        tool_name: str,
        parameters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Call MCP context-orchestrator tool.

        Args:
            tool_name: Tool name
            parameters: Tool parameters

        Returns:
            Tool result

        Raises:
            Exception: If tool call fails
        """
        # For MCP integration, we would use stdio communication
        # For now, create a stub implementation that logs the call

        logger.debug(f"MCP tool call: {tool_name} with params: {parameters}")

        # TODO: Implement actual MCP stdio communication
        # This would involve:
        # 1. Start MCP server as subprocess if not running
        # 2. Send JSON-RPC request via stdin
        # 3. Read JSON-RPC response from stdout
        # 4. Parse and return result

        # Stub response
        return {
            "success": True,
            "tool": tool_name,
            "result": {},
        }

    async def get_active_sessions(self) -> List[str]:
        """
        Get list of active session IDs.

        Returns:
            List of session IDs
        """
        return list(self._sessions.keys())

    async def cleanup(self) -> None:
        """Cleanup session bridge"""
        logger.info("Cleaning up SessionBridge")

        # Stop all heartbeat tasks
        for session_id in list(self._heartbeat_tasks.keys()):
            try:
                await self.stop_session(session_id, reason="cleanup")
            except Exception as e:
                logger.error(f"Error stopping session {session_id}: {e}")

        self._sessions.clear()
        self._heartbeat_tasks.clear()

        logger.info("SessionBridge cleanup complete")
