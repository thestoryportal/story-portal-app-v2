"""Tool registry service."""

import asyncpg
from typing import List, Optional, Union, Any
from uuid import UUID
import logging
from datetime import datetime

from ..models import Tool, ToolCreate, ToolUpdate, ToolExecution, ToolExecutionCreate, ToolExecutionUpdate
import json
from ..redis_client import RedisClient

logger = logging.getLogger(__name__)


class ToolRegistry:
    """Tool registry service."""

    def __init__(
        self,
        db_pool: Union[asyncpg.Pool, Any],
        redis_client: Union[RedisClient, Any]
    ):
        """Initialize ToolRegistry.

        Args:
            db_pool: Either an asyncpg.Pool directly, or a DatabasePool wrapper
                     that has a .pool property
            redis_client: Either a RedisClient directly, or a RedisPool wrapper
                          that has a .client property
        """
        # Support both direct pool and wrapper with .pool property
        if hasattr(db_pool, 'pool'):
            self.db_pool = db_pool.pool
        else:
            self.db_pool = db_pool

        # Support both direct client and wrapper with .client property
        if hasattr(redis_client, 'client'):
            self.redis_client = redis_client.client
        else:
            self.redis_client = redis_client

    async def register_tool(self, tool_data: ToolCreate) -> Tool:
        """Register a new tool."""
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO tools (name, description, tool_type, schema_def, permissions, enabled)
                VALUES ($1, $2, $3, $4, $5, $6)
                RETURNING id, name, description, tool_type, schema_def, permissions, enabled, created_at, updated_at
                """,
                tool_data.name,
                tool_data.description,
                tool_data.tool_type.value,
                tool_data.schema_def,
                tool_data.permissions,
                tool_data.enabled,
            )

        tool = Tool(**dict(row))

        await self.redis_client.publish_event(
            event_type="tool.registered",
            aggregate_type="tool",
            aggregate_id=str(tool.id),
            payload={"name": tool.name, "tool_type": tool.tool_type},
        )

        logger.info(f"Registered tool {tool.id} ({tool.name})")
        return tool

    async def get_tool(self, tool_id: UUID) -> Optional[Tool]:
        """Get tool by ID."""
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT id, name, description, tool_type, schema_def, permissions, enabled, created_at, updated_at
                FROM tools WHERE id = $1
                """,
                tool_id,
            )

        if not row:
            return None

        return Tool(**dict(row))

    async def list_tools(self, enabled_only: bool = False, limit: int = 100) -> List[Tool]:
        """List tools."""
        if enabled_only:
            query = """
                SELECT id, name, description, tool_type, schema_def, permissions, enabled, created_at, updated_at
                FROM tools WHERE enabled = TRUE ORDER BY name LIMIT $1
            """
            params = [limit]
        else:
            query = """
                SELECT id, name, description, tool_type, schema_def, permissions, enabled, created_at, updated_at
                FROM tools ORDER BY name LIMIT $1
            """
            params = [limit]

        async with self.db_pool.acquire() as conn:
            rows = await conn.fetch(query, *params)

        return [Tool(**dict(row)) for row in rows]

    async def update_tool(self, tool_id: UUID, tool_data: ToolUpdate) -> Optional[Tool]:
        """Update a tool."""
        update_fields = []
        params = []
        param_count = 1

        for field, value in tool_data.model_dump(exclude_unset=True).items():
            if value is not None:
                update_fields.append(f"{field} = ${param_count}")
                params.append(value)
                param_count += 1

        if not update_fields:
            return await self.get_tool(tool_id)

        update_fields.append("updated_at = NOW()")

        query = f"""
            UPDATE tools SET {', '.join(update_fields)}
            WHERE id = ${param_count}
            RETURNING id, name, description, tool_type, schema_def, permissions, enabled, created_at, updated_at
        """
        params.append(tool_id)

        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow(query, *params)

        if not row:
            return None

        return Tool(**dict(row))

    async def record_execution(self, execution_data: ToolExecutionCreate) -> ToolExecution:
        """Record a tool execution with rich metadata."""
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO tool_executions (
                    invocation_id, tool_id, tool_name, tool_version,
                    agent_id, agent_did, tenant_id, session_id, parent_sandbox_id,
                    input_params, status,
                    async_mode, priority, idempotency_key, require_approval,
                    cpu_millicore_limit, memory_mb_limit, timeout_seconds
                )
                VALUES (
                    $1, $2, $3, $4,
                    $5, $6, $7, $8, $9,
                    $10::jsonb, $11,
                    $12, $13, $14, $15,
                    $16, $17, $18
                )
                RETURNING *
                """,
                execution_data.invocation_id,
                execution_data.tool_id,
                execution_data.tool_name,
                execution_data.tool_version,
                execution_data.agent_id,
                execution_data.agent_did,
                execution_data.tenant_id,
                execution_data.session_id,
                execution_data.parent_sandbox_id,
                json.dumps(execution_data.input_params),
                execution_data.status.value,
                execution_data.async_mode,
                execution_data.priority,
                execution_data.idempotency_key,
                execution_data.require_approval,
                execution_data.cpu_millicore_limit,
                execution_data.memory_mb_limit,
                execution_data.timeout_seconds,
            )

        execution = self._row_to_execution(row)

        await self.redis_client.publish_event(
            event_type="tool.execution.created",
            aggregate_type="tool_execution",
            aggregate_id=str(execution.invocation_id),
            payload={
                "tool_name": execution.tool_name,
                "agent_id": str(execution.agent_id) if execution.agent_id else None,
                "status": execution.status.value,
                "session_id": execution.session_id,
            },
        )

        logger.info(f"Recorded tool execution {execution.invocation_id} ({execution.tool_name})")
        return execution

    def _row_to_execution(self, row) -> ToolExecution:
        """Convert database row to ToolExecution model with JSON parsing."""
        execution_dict = dict(row)
        # Parse JSONB fields
        for field in ['input_params', 'output_result', 'error_details', 'documents_accessed', 'checkpoints_created']:
            if field in execution_dict and isinstance(execution_dict[field], str):
                execution_dict[field] = json.loads(execution_dict[field])
            elif field not in execution_dict:
                if field in ['documents_accessed', 'checkpoints_created']:
                    execution_dict[field] = []
                elif field in ['input_params', 'output_result', 'error_details']:
                    execution_dict[field] = None if field != 'input_params' else {}
        return ToolExecution(**execution_dict)

    async def get_execution(self, execution_id: UUID) -> Optional[ToolExecution]:
        """Get tool execution by ID."""
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM tool_executions WHERE id = $1",
                execution_id,
            )

        if not row:
            return None

        return self._row_to_execution(row)

    async def get_execution_by_invocation(self, invocation_id: UUID) -> Optional[ToolExecution]:
        """Get tool execution by invocation ID."""
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM tool_executions WHERE invocation_id = $1",
                invocation_id,
            )

        if not row:
            return None

        return self._row_to_execution(row)

    async def update_execution(
        self,
        invocation_id: UUID,
        update_data: ToolExecutionUpdate
    ) -> Optional[ToolExecution]:
        """Update tool execution with results and metadata."""
        update_fields = []
        params = []
        param_count = 1

        updates_dict = update_data.model_dump(exclude_unset=True)

        for field, value in updates_dict.items():
            if value is not None:
                # Handle JSONB fields
                if field in ['output_result', 'error_details', 'documents_accessed', 'checkpoints_created']:
                    update_fields.append(f"{field} = ${param_count}::jsonb")
                    params.append(json.dumps(value))
                elif field == 'status':
                    update_fields.append(f"{field} = ${param_count}")
                    params.append(value.value)
                else:
                    update_fields.append(f"{field} = ${param_count}")
                    params.append(value)
                param_count += 1

        if not update_fields:
            return await self.get_execution_by_invocation(invocation_id)

        query = f"""
            UPDATE tool_executions
            SET {', '.join(update_fields)}
            WHERE invocation_id = ${param_count}
            RETURNING *
        """
        params.append(invocation_id)

        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow(query, *params)

        if not row:
            return None

        execution = self._row_to_execution(row)

        # Publish status update event
        await self.redis_client.publish_event(
            event_type="tool.execution.updated",
            aggregate_type="tool_execution",
            aggregate_id=str(execution.invocation_id),
            payload={
                "tool_name": execution.tool_name,
                "status": execution.status.value,
                "duration_ms": execution.duration_ms,
            },
        )

        logger.info(f"Updated tool execution {invocation_id} - status: {execution.status.value}")
        return execution

    async def list_executions(
        self,
        agent_id: Optional[UUID] = None,
        tool_name: Optional[str] = None,
        session_id: Optional[str] = None,
        tenant_id: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[ToolExecution]:
        """List tool executions with filters."""
        conditions = []
        params = []
        param_count = 1

        if agent_id:
            conditions.append(f"agent_id = ${param_count}")
            params.append(agent_id)
            param_count += 1

        if tool_name:
            conditions.append(f"tool_name = ${param_count}")
            params.append(tool_name)
            param_count += 1

        if session_id:
            conditions.append(f"session_id = ${param_count}")
            params.append(session_id)
            param_count += 1

        if tenant_id:
            conditions.append(f"tenant_id = ${param_count}")
            params.append(tenant_id)
            param_count += 1

        if status:
            conditions.append(f"status = ${param_count}")
            params.append(status)
            param_count += 1

        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

        query = f"""
            SELECT * FROM tool_executions
            {where_clause}
            ORDER BY created_at DESC
            LIMIT ${param_count} OFFSET ${param_count + 1}
        """
        params.extend([limit, offset])

        async with self.db_pool.acquire() as conn:
            rows = await conn.fetch(query, *params)

        return [self._row_to_execution(row) for row in rows]
