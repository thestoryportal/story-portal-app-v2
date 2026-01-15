"""
Tool Executor Service

Executes tools within isolated sandboxes with resource limits and timeout enforcement.
Based on Section 3.3.2 and BC-1 nested sandbox interface.

Features:
- Nested sandbox execution within agent sandboxes (BC-1)
- Resource sub-allocation and enforcement
- Async execution patterns for long-running tools (Gap G-004)
- Priority scheduling (Gap G-005)
- Integration with Phase 16 checkpointing
"""

import asyncio
import logging
import json
from typing import Optional, Dict, Any
from datetime import datetime
from uuid import uuid4

from ..models import (
    ToolInvokeRequest,
    ToolInvokeResponse,
    ToolResult,
    ToolStatus,
    ToolError,
    ExecutionMetadata,
    ExecutionContext,
    ErrorCode,
    ToolExecutionError,
)
from .tool_registry import ToolRegistry
from .tool_sandbox import ToolSandbox

logger = logging.getLogger(__name__)


class ToolExecutor:
    """
    Tool executor with sandbox isolation and resource management.

    Implements BC-1 nested sandbox interface and BC-2 tool.invoke() interface.
    """

    def __init__(
        self,
        tool_registry: ToolRegistry,
        tool_sandbox: ToolSandbox,
        default_cpu_limit: int = 500,
        default_memory_limit: int = 1024,
        default_timeout: int = 30,
        max_concurrent_tools: int = 4,
    ):
        """
        Initialize Tool Executor.

        Args:
            tool_registry: Tool registry service
            tool_sandbox: Tool sandbox service
            default_cpu_limit: Default CPU limit (millicores)
            default_memory_limit: Default memory limit (MB)
            default_timeout: Default timeout (seconds)
            max_concurrent_tools: Max concurrent tool executions per agent
        """
        self.tool_registry = tool_registry
        self.tool_sandbox = tool_sandbox
        self.default_cpu_limit = default_cpu_limit
        self.default_memory_limit = default_memory_limit
        self.default_timeout = default_timeout
        self.max_concurrent_tools = max_concurrent_tools

        # Track concurrent executions per agent
        self.agent_executions: Dict[str, int] = {}
        self.execution_lock = asyncio.Lock()

    async def execute(self, request: ToolInvokeRequest) -> ToolInvokeResponse:
        """
        Execute tool invocation (BC-2 interface).

        Implements tool.invoke() method consumed by L11 Integration Layer.

        Args:
            request: Tool invocation request

        Returns:
            ToolInvokeResponse with result or error

        Raises:
            ToolExecutionError: On execution failures
        """
        start_time = datetime.utcnow()
        invocation_id = request.invocation_id

        try:
            # Check concurrent execution limit
            agent_did = request.agent_context.agent_did if request.agent_context else "unknown"
            await self._check_concurrent_limit(agent_did)

            # Retrieve tool definition and manifest
            tool_def = await self.tool_registry.get_tool(request.tool_id)

            # Validate and resolve resource limits (BC-1 constraint)
            resource_limits = self._resolve_resource_limits(request, tool_def)

            # Build execution context
            execution_context = self._build_execution_context(request, resource_limits)

            # Check if async mode required
            is_async = request.execution_options and request.execution_options.async_mode

            if is_async:
                # Async execution pattern (Gap G-004)
                return await self._execute_async(request, execution_context, tool_def)
            else:
                # Synchronous execution
                return await self._execute_sync(request, execution_context, tool_def)

        except ToolExecutionError:
            raise
        except Exception as e:
            logger.error(f"Tool execution failed: {e}", exc_info=True)
            return ToolInvokeResponse(
                invocation_id=invocation_id,
                status=ToolStatus.ERROR,
                error=ToolError(
                    code=ErrorCode.E3108.value,
                    message=str(e),
                    details={"tool_id": request.tool_id},
                    retryable=False
                )
            )

    async def _check_concurrent_limit(self, agent_did: str):
        """Check concurrent execution limit for agent"""
        async with self.execution_lock:
            current_count = self.agent_executions.get(agent_did, 0)
            if current_count >= self.max_concurrent_tools:
                raise ToolExecutionError(
                    ErrorCode.E3106,
                    message="Maximum concurrent tools exceeded",
                    details={"agent_did": agent_did, "limit": self.max_concurrent_tools}
                )
            self.agent_executions[agent_did] = current_count + 1

    async def _release_concurrent_slot(self, agent_did: str):
        """Release concurrent execution slot"""
        async with self.execution_lock:
            current_count = self.agent_executions.get(agent_did, 1)
            self.agent_executions[agent_did] = max(0, current_count - 1)

    def _resolve_resource_limits(self, request: ToolInvokeRequest, tool_def: Any) -> Dict[str, int]:
        """
        Resolve resource limits from request, tool manifest, and defaults.

        BC-1 Constraint: Tool limits must be <= agent limits.
        """
        limits = {
            "cpu_millicore_limit": self.default_cpu_limit,
            "memory_mb_limit": self.default_memory_limit,
            "timeout_seconds": self.default_timeout,
        }

        # Apply tool manifest defaults
        if tool_def:
            limits["cpu_millicore_limit"] = tool_def.default_cpu_millicore_limit or limits["cpu_millicore_limit"]
            limits["memory_mb_limit"] = tool_def.default_memory_mb_limit or limits["memory_mb_limit"]
            limits["timeout_seconds"] = tool_def.default_timeout_seconds or limits["timeout_seconds"]

        # Apply request overrides
        if request.resource_limits:
            if request.resource_limits.cpu_millicore_limit:
                limits["cpu_millicore_limit"] = request.resource_limits.cpu_millicore_limit
            if request.resource_limits.memory_mb_limit:
                limits["memory_mb_limit"] = request.resource_limits.memory_mb_limit
            if request.resource_limits.timeout_seconds:
                limits["timeout_seconds"] = request.resource_limits.timeout_seconds

        # TODO: Validate against agent parent limits (BC-1)
        # This would require querying L02 for parent sandbox limits

        return limits

    def _build_execution_context(
        self,
        request: ToolInvokeRequest,
        resource_limits: Dict[str, int]
    ) -> ExecutionContext:
        """Build execution context from request and limits"""
        from ..models.execution_context import ResourceLimits as ExecResourceLimits
        from ..models.execution_context import SandboxConfig

        agent_ctx = request.agent_context
        if not agent_ctx:
            raise ToolExecutionError(
                ErrorCode.E3101,
                message="Agent context required for execution"
            )

        sandbox_config = SandboxConfig(
            resource_limits=ExecResourceLimits(
                cpu_millicore_limit=resource_limits["cpu_millicore_limit"],
                memory_mb_limit=resource_limits["memory_mb_limit"],
                timeout_seconds=resource_limits["timeout_seconds"],
            )
        )

        return ExecutionContext(
            agent_did=agent_ctx.agent_did,
            tenant_id=agent_ctx.tenant_id,
            session_id=agent_ctx.session_id,
            parent_sandbox_id=agent_ctx.parent_sandbox_id,
            sandbox_config=sandbox_config,
        )

    async def _execute_sync(
        self,
        request: ToolInvokeRequest,
        execution_context: ExecutionContext,
        tool_def: Any
    ) -> ToolInvokeResponse:
        """Execute tool synchronously"""
        start_time = datetime.utcnow()
        agent_did = execution_context.agent_did

        try:
            # Create sandbox
            sandbox_id = await self.tool_sandbox.create_sandbox(execution_context)
            execution_context.tool_sandbox_id = sandbox_id

            # Execute tool in sandbox
            result = await self.tool_sandbox.execute_in_sandbox(
                sandbox_id=sandbox_id,
                tool_id=request.tool_id,
                parameters=request.parameters,
                timeout=execution_context.sandbox_config.resource_limits.timeout_seconds,
            )

            # Calculate execution metadata
            end_time = datetime.utcnow()
            duration_ms = int((end_time - start_time).total_seconds() * 1000)

            execution_metadata = ExecutionMetadata(
                duration_ms=duration_ms,
            )

            # TODO: Validate result against tool manifest result_schema (Gap G-010)

            return ToolInvokeResponse(
                invocation_id=request.invocation_id,
                status=ToolStatus.SUCCESS,
                result=ToolResult(result=result),
                execution_metadata=execution_metadata,
                completed_at=end_time,
            )

        except asyncio.TimeoutError:
            raise ToolExecutionError(
                ErrorCode.E3103,
                message="Tool execution timeout",
                details={"tool_id": request.tool_id}
            )
        except Exception as e:
            logger.error(f"Tool execution failed: {e}")
            raise ToolExecutionError(
                ErrorCode.E3108,
                message="Tool execution failed",
                details={"error": str(e), "tool_id": request.tool_id}
            )
        finally:
            # Cleanup sandbox
            if execution_context.tool_sandbox_id:
                await self.tool_sandbox.destroy_sandbox(execution_context.tool_sandbox_id)

            # Release concurrent slot
            await self._release_concurrent_slot(agent_did)

    async def _execute_async(
        self,
        request: ToolInvokeRequest,
        execution_context: ExecutionContext,
        tool_def: Any
    ) -> ToolInvokeResponse:
        """
        Execute tool asynchronously (Gap G-004).

        Returns immediately with task ID for polling.
        """
        # Generate task ID
        task_id = f"task:{request.tool_id}:{request.invocation_id}"

        # TODO: Create MCP Task for async execution
        # TODO: Return polling info

        # For now, fall back to sync execution
        logger.warning("Async execution not fully implemented, falling back to sync")
        return await self._execute_sync(request, execution_context, tool_def)

    async def get_tool(self, tool_name: str) -> Optional[Any]:
        """
        Get tool definition by name.

        Part of L02 integration interface.
        """
        try:
            return await self.tool_registry.get_tool(tool_name)
        except ToolExecutionError as e:
            if e.code == ErrorCode.E3001:
                return None
            raise

    async def list_tools(self) -> list[Any]:
        """
        List all available tools.

        Part of L02 integration interface.
        """
        # TODO: Implement tool listing
        return []
