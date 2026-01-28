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
import os
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
from enum import Enum

from ..models import AgentState
from .mcp_client import MCPClient, MCPToolResult


logger = logging.getLogger(__name__)


class MCPErrorMode(Enum):
    """MCP error handling mode"""
    FAIL_FAST = "fail_fast"      # Raise error if MCP unavailable
    GRACEFUL_DEGRADE = "graceful"  # Fall back to stub mode


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
                - mcp_error_mode: Error handling mode ("fail_fast" or "graceful")
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

        # MCP error handling mode
        error_mode_str = self.config.get("mcp_error_mode", "graceful")
        self.mcp_error_mode = MCPErrorMode(error_mode_str)

        # Stub mode flag (set if MCP unavailable in graceful mode)
        self._stub_mode = False

        # Retry policy
        retry_policy = self.config.get("retry_policy", {})
        self.max_retries = retry_policy.get("max_retries", 3)
        self.backoff_multiplier = retry_policy.get("backoff_multiplier", 2)

        # MCP server configuration
        mcp_base_path = self.config.get(
            "mcp_base_path",
            "/Volumes/Extreme SSD/projects/story-portal-app/platform/services/mcp-context-orchestrator"
        )
        server_script = os.path.join(mcp_base_path, "dist/server.js")

        # Initialize MCP client
        mcp_timeout = self.config.get("mcp_timeout_seconds", 30)
        self.mcp_client = MCPClient(
            server_command=["node", server_script],
            server_name="context-orchestrator",
            timeout_seconds=mcp_timeout,
            cwd=mcp_base_path,
            env=os.environ.copy()  # Pass environment to subprocess
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
        """
        Initialize session bridge.

        Raises:
            SessionError: If MCP unavailable and mcp_error_mode is FAIL_FAST
        """
        # Connect to MCP server
        try:
            connected = await self.mcp_client.connect()
            if connected:
                # Verify connection with check_recovery call
                result = await self._call_mcp_tool("check_recovery", {})
                logger.info("MCP context-orchestrator connection verified")
                self._stub_mode = False
            else:
                self._handle_mcp_unavailable("Failed to connect to MCP context-orchestrator")
        except Exception as e:
            self._handle_mcp_unavailable(f"Failed to verify MCP connection: {e}")

        logger.info(
            f"SessionBridge initialization complete "
            f"(stub_mode={self._stub_mode}, error_mode={self.mcp_error_mode.value})"
        )

    def _handle_mcp_unavailable(self, message: str) -> None:
        """
        Handle MCP unavailability based on error mode.

        Args:
            message: Error message

        Raises:
            SessionError: If error mode is FAIL_FAST
        """
        if self.mcp_error_mode == MCPErrorMode.FAIL_FAST:
            logger.error(f"MCP required but unavailable: {message}")
            raise SessionError(
                code="E2055",
                message=f"MCP context-orchestrator required but unavailable: {message}"
            )
        else:
            logger.warning(f"{message}, using stub mode")
            self._stub_mode = True

    def is_stub_mode(self) -> bool:
        """Check if bridge is operating in stub mode."""
        return self._stub_mode

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
                "started_at": datetime.now(timezone.utc),
                "last_heartbeat": datetime.now(timezone.utc),
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
        task_id: str,
        context_data: Dict[str, Any],
        change_summary: Optional[str] = None
    ) -> None:
        """
        Save context snapshot for a session.

        Args:
            task_id: Task/session identifier
            context_data: Context data to save
            change_summary: Description of changes

        Raises:
            SessionError: If snapshot save fails
        """
        logger.debug(f"Saving snapshot for task {task_id}")

        try:
            await self._call_mcp_tool(
                "save_context_snapshot",
                {
                    "taskId": task_id,
                    "updates": context_data,
                    "changeSummary": change_summary or "Context snapshot",
                }
            )

        except Exception as e:
            logger.error(f"Failed to save snapshot for task {task_id}: {e}")
            raise SessionError(
                code="E2052",
                message=f"Snapshot save failed: {str(e)}"
            )

    async def get_unified_context(
        self,
        task_id: str
    ) -> Dict[str, Any]:
        """
        Get unified context for a session.

        Args:
            task_id: Task/session identifier

        Returns:
            Unified context data

        Raises:
            SessionError: If context retrieval fails
        """
        try:
            result = await self._call_mcp_tool(
                "get_unified_context",
                {
                    "taskId": task_id,
                    "includeRelationships": True,
                    "includeVersionHistory": False,
                }
            )

            return result

        except Exception as e:
            logger.error(f"Failed to get context for task {task_id}: {e}")
            raise SessionError(
                code="E2054",
                message=f"Failed to get task context: {str(e)}"
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
                    task_id=session_id,
                    context_data={
                        "immediateContext": {
                            "lastAction": "Heartbeat",
                        },
                    },
                    change_summary="Heartbeat",
                )

                # Update last heartbeat time
                if session_id in self._sessions:
                    self._sessions[session_id]["last_heartbeat"] = datetime.now(timezone.utc)

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
            SessionError: If tool call fails and error mode is FAIL_FAST
        """
        # In stub mode, return stub response
        if self._stub_mode:
            logger.debug(f"MCP tool call in stub mode: {tool_name}")
            return self._get_stub_response(tool_name, parameters)

        logger.debug(f"MCP tool call: {tool_name} with params: {parameters}")

        try:
            # Call tool via MCP client
            result: MCPToolResult = await self.mcp_client.call_tool(
                tool_name=tool_name,
                arguments=parameters
            )

            if result.success:
                logger.debug(f"MCP tool {tool_name} succeeded in {result.execution_time_ms:.2f}ms")
                return result.result if result.result is not None else {"success": True}
            else:
                logger.error(f"MCP tool {tool_name} failed: {result.error}")
                return self._handle_tool_failure(tool_name, result.error)

        except Exception as e:
            logger.error(f"MCP tool call exception: {tool_name}: {e}")
            return self._handle_tool_failure(tool_name, str(e))

    def _handle_tool_failure(
        self,
        tool_name: str,
        error: str
    ) -> Dict[str, Any]:
        """
        Handle MCP tool failure based on error mode.

        Args:
            tool_name: Tool name
            error: Error message

        Returns:
            Stub response if graceful mode

        Raises:
            SessionError: If error mode is FAIL_FAST
        """
        if self.mcp_error_mode == MCPErrorMode.FAIL_FAST:
            raise SessionError(
                code="E2056",
                message=f"MCP tool {tool_name} failed: {error}"
            )
        else:
            # Graceful degradation - return stub response
            return {
                "success": False,
                "error": error,
                "tool": tool_name,
                "stub_mode": True,
            }

    def _get_stub_response(
        self,
        tool_name: str,
        parameters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Get stub response for MCP tool call.

        Args:
            tool_name: Tool name
            parameters: Tool parameters

        Returns:
            Stub response based on tool type
        """
        # Provide meaningful stub responses for common tools
        stub_responses = {
            "check_recovery": {"needsRecovery": [], "checked": True},
            "save_context_snapshot": {"success": True, "stub": True},
            "get_unified_context": {
                "taskId": parameters.get("taskId"),
                "context": {},
                "stub": True,
            },
        }

        return stub_responses.get(tool_name, {
            "success": True,
            "tool": tool_name,
            "stub": True,
        })

    async def get_active_sessions(self) -> List[str]:
        """
        Get list of active session IDs.

        Returns:
            List of session IDs
        """
        return list(self._sessions.keys())

    async def cleanup(self) -> None:
        """Cleanup session bridge with timeout protection"""
        logger.info("Cleaning up SessionBridge")

        # Stop all heartbeat tasks with timeout
        for session_id in list(self._heartbeat_tasks.keys()):
            try:
                await asyncio.wait_for(
                    self.stop_session(session_id, reason="cleanup"),
                    timeout=1.0
                )
            except asyncio.TimeoutError:
                logger.warning(f"Timeout stopping session {session_id}")
                # Force cancel the heartbeat task
                if session_id in self._heartbeat_tasks:
                    self._heartbeat_tasks[session_id].cancel()
            except Exception as e:
                logger.error(f"Error stopping session {session_id}: {e}")

        self._sessions.clear()
        self._heartbeat_tasks.clear()

        # Disconnect MCP client with timeout
        try:
            await asyncio.wait_for(self.mcp_client.disconnect(), timeout=1.0)
        except asyncio.TimeoutError:
            logger.warning("Timeout disconnecting MCP client")
        except Exception as e:
            logger.error(f"Error disconnecting MCP client: {e}")

        logger.info("SessionBridge cleanup complete")
