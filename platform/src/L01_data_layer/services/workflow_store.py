"""
Workflow Store Service

Persistent storage for workflow definitions, executions, triggers, and approvals.
Implements the data layer for the enhanced workflow orchestration system.
"""

import asyncpg
import json
import logging
from typing import List, Optional, Dict, Any
from uuid import UUID, uuid4
from datetime import datetime

from ..models import (
    # Enums
    WorkflowStatus,
    ExecutionStatus,
    NodeExecutionStatus,
    ApprovalStatus,
    CompensationStatus,
    # Workflow Definition
    WorkflowDefinitionCreate,
    WorkflowDefinitionUpdate,
    WorkflowDefinition,
    # Workflow Execution
    WorkflowExecutionCreate,
    WorkflowExecutionUpdate,
    WorkflowExecution,
    # Node Execution
    NodeExecutionCreate,
    NodeExecutionUpdate,
    WorkflowNodeExecution,
    # Triggers
    WorkflowTriggerCreate,
    WorkflowTriggerUpdate,
    WorkflowTrigger,
    # Approvals
    ApprovalRequestCreate,
    ApprovalResponse,
    WorkflowApprovalRequest,
    # Responses
    WorkflowExecutionResponse,
    WorkflowListResponse,
    ExecutionListResponse,
)

logger = logging.getLogger(__name__)


class WorkflowStore:
    """
    Persistent storage for the workflow orchestration system.

    Manages:
    - Workflow definitions (CRUD, versioning)
    - Workflow executions (lifecycle, checkpointing)
    - Node executions (individual step tracking)
    - Triggers (event, schedule, webhook)
    - Approval requests (human-in-the-loop)
    """

    def __init__(self, db_pool: asyncpg.Pool):
        """Initialize with database connection pool."""
        self.db_pool = db_pool

    # =========================================================================
    # Workflow Definitions
    # =========================================================================

    async def create_workflow(self, data: WorkflowDefinitionCreate) -> WorkflowDefinition:
        """Create a new workflow definition."""
        workflow_id = f"wf_{uuid4().hex[:12]}"

        # Build the definition JSONB from the structured input
        definition = {
            "paradigm": data.paradigm.value,
            "nodes": [node.model_dump() for node in data.nodes],
            "edges": [edge.model_dump() for edge in data.edges],
            "entry_node_id": data.entry_node_id,
            "parameters": [param.model_dump() for param in data.parameters],
            "generated_from": data.generated_from,
            "ai_optimizations": data.ai_optimizations,
        }

        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO workflow_definitions
                (workflow_id, name, description, version, definition, category, tags,
                 status, visibility, metadata)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
                RETURNING id, workflow_id, name, description, version, definition,
                          category, tags, status, owner_agent_id, visibility, metadata,
                          created_at, updated_at
                """,
                workflow_id,
                data.name,
                data.description,
                data.version,
                json.dumps(definition),
                data.category,
                data.tags,
                WorkflowStatus.DRAFT.value,
                data.visibility.value,
                json.dumps(data.metadata),
            )

        return self._row_to_workflow_definition(row)

    async def get_workflow(self, workflow_id: str) -> Optional[WorkflowDefinition]:
        """Get a workflow definition by ID."""
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT id, workflow_id, name, description, version, definition,
                       category, tags, status, owner_agent_id, visibility, metadata,
                       created_at, updated_at
                FROM workflow_definitions
                WHERE workflow_id = $1
                """,
                workflow_id,
            )
        return self._row_to_workflow_definition(row) if row else None

    async def get_workflow_by_uuid(self, uuid: UUID) -> Optional[WorkflowDefinition]:
        """Get a workflow definition by UUID."""
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT id, workflow_id, name, description, version, definition,
                       category, tags, status, owner_agent_id, visibility, metadata,
                       created_at, updated_at
                FROM workflow_definitions
                WHERE id = $1
                """,
                uuid,
            )
        return self._row_to_workflow_definition(row) if row else None

    async def update_workflow(
        self, workflow_id: str, data: WorkflowDefinitionUpdate
    ) -> Optional[WorkflowDefinition]:
        """Update a workflow definition."""
        updates = []
        params = []
        param_idx = 1

        update_data = data.model_dump(exclude_unset=True)

        for field, value in update_data.items():
            if value is not None:
                if field in ("status", "visibility"):
                    value = value.value if hasattr(value, "value") else value
                elif field in ("nodes", "edges", "parameters", "metadata"):
                    value = json.dumps(value if isinstance(value, (list, dict)) else [v.model_dump() for v in value])
                updates.append(f"{field} = ${param_idx}")
                params.append(value)
                param_idx += 1

        if not updates:
            return await self.get_workflow(workflow_id)

        updates.append("updated_at = NOW()")
        params.append(workflow_id)

        query = f"""
            UPDATE workflow_definitions
            SET {', '.join(updates)}
            WHERE workflow_id = ${param_idx}
            RETURNING id, workflow_id, name, description, version, definition,
                      category, tags, status, owner_agent_id, visibility, metadata,
                      created_at, updated_at
        """

        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow(query, *params)

        return self._row_to_workflow_definition(row) if row else None

    async def delete_workflow(self, workflow_id: str) -> bool:
        """Delete a workflow definition (soft delete by archiving)."""
        async with self.db_pool.acquire() as conn:
            result = await conn.execute(
                """
                UPDATE workflow_definitions
                SET status = $1, updated_at = NOW()
                WHERE workflow_id = $2
                """,
                WorkflowStatus.ARCHIVED.value,
                workflow_id,
            )
        return "UPDATE 1" in result

    async def list_workflows(
        self,
        status: Optional[WorkflowStatus] = None,
        category: Optional[str] = None,
        owner_agent_id: Optional[UUID] = None,
        tags: Optional[List[str]] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> WorkflowListResponse:
        """List workflow definitions with filtering."""
        conditions = ["status != 'archived'"]
        params = []
        param_idx = 1

        if status:
            conditions.append(f"status = ${param_idx}")
            params.append(status.value)
            param_idx += 1

        if category:
            conditions.append(f"category = ${param_idx}")
            params.append(category)
            param_idx += 1

        if owner_agent_id:
            conditions.append(f"owner_agent_id = ${param_idx}")
            params.append(owner_agent_id)
            param_idx += 1

        if tags:
            conditions.append(f"tags && ${param_idx}")
            params.append(tags)
            param_idx += 1

        where_clause = " AND ".join(conditions)

        # Get total count
        count_query = f"SELECT COUNT(*) FROM workflow_definitions WHERE {where_clause}"

        # Get paginated results
        query = f"""
            SELECT id, workflow_id, name, description, version, definition,
                   category, tags, status, owner_agent_id, visibility, metadata,
                   created_at, updated_at
            FROM workflow_definitions
            WHERE {where_clause}
            ORDER BY created_at DESC
            LIMIT ${param_idx} OFFSET ${param_idx + 1}
        """
        params.extend([limit, offset])

        async with self.db_pool.acquire() as conn:
            total = await conn.fetchval(count_query, *params[:-2])
            rows = await conn.fetch(query, *params)

        workflows = [self._row_to_workflow_definition(row) for row in rows]
        return WorkflowListResponse(
            workflows=workflows,
            total=total,
            offset=offset,
            limit=limit,
        )

    # =========================================================================
    # Workflow Executions
    # =========================================================================

    async def create_execution(self, data: WorkflowExecutionCreate) -> WorkflowExecution:
        """Create a new workflow execution."""
        execution_id = f"exec_{uuid4().hex[:12]}"

        # Get workflow version
        workflow = await self.get_workflow(data.workflow_id)
        if not workflow:
            raise ValueError(f"Workflow not found: {data.workflow_id}")

        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO workflow_executions
                (execution_id, workflow_id, workflow_version, agent_id, session_id,
                 parent_execution_id, input_parameters, status, trace_id)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                RETURNING id, execution_id, workflow_id, workflow_version, agent_id,
                          session_id, parent_execution_id, input_parameters, output_result,
                          status, current_node_id, execution_state, checkpoint_id,
                          error_code, error_message, compensation_required,
                          compensation_status, compensated_nodes, started_at,
                          completed_at, duration_ms, trace_id, created_at
                """,
                execution_id,
                data.workflow_id,
                workflow.version,
                data.agent_id,
                data.session_id,
                data.parent_execution_id,
                json.dumps(data.parameters),
                ExecutionStatus.PENDING.value,
                data.trace_id or f"trace_{uuid4().hex[:8]}",
            )

        return self._row_to_workflow_execution(row)

    async def get_execution(self, execution_id: str) -> Optional[WorkflowExecution]:
        """Get a workflow execution by ID."""
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT id, execution_id, workflow_id, workflow_version, agent_id,
                       session_id, parent_execution_id, input_parameters, output_result,
                       status, current_node_id, execution_state, checkpoint_id,
                       error_code, error_message, compensation_required,
                       compensation_status, compensated_nodes, started_at,
                       completed_at, duration_ms, trace_id, created_at
                FROM workflow_executions
                WHERE execution_id = $1
                """,
                execution_id,
            )
        return self._row_to_workflow_execution(row) if row else None

    async def update_execution(
        self, execution_id: str, data: WorkflowExecutionUpdate
    ) -> Optional[WorkflowExecution]:
        """Update a workflow execution."""
        updates = []
        params = []
        param_idx = 1

        update_data = data.model_dump(exclude_unset=True)

        for field, value in update_data.items():
            if value is not None:
                if field in ("status", "compensation_status"):
                    value = value.value if hasattr(value, "value") else value
                elif field in ("execution_state", "output_result"):
                    value = json.dumps(value)
                updates.append(f"{field} = ${param_idx}")
                params.append(value)
                param_idx += 1

        if not updates:
            return await self.get_execution(execution_id)

        params.append(execution_id)
        query = f"""
            UPDATE workflow_executions
            SET {', '.join(updates)}
            WHERE execution_id = ${param_idx}
            RETURNING id, execution_id, workflow_id, workflow_version, agent_id,
                      session_id, parent_execution_id, input_parameters, output_result,
                      status, current_node_id, execution_state, checkpoint_id,
                      error_code, error_message, compensation_required,
                      compensation_status, compensated_nodes, started_at,
                      completed_at, duration_ms, trace_id, created_at
        """

        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow(query, *params)

        return self._row_to_workflow_execution(row) if row else None

    async def start_execution(self, execution_id: str) -> Optional[WorkflowExecution]:
        """Mark an execution as started."""
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                UPDATE workflow_executions
                SET status = $1, started_at = NOW()
                WHERE execution_id = $2
                RETURNING id, execution_id, workflow_id, workflow_version, agent_id,
                          session_id, parent_execution_id, input_parameters, output_result,
                          status, current_node_id, execution_state, checkpoint_id,
                          error_code, error_message, compensation_required,
                          compensation_status, compensated_nodes, started_at,
                          completed_at, duration_ms, trace_id, created_at
                """,
                ExecutionStatus.RUNNING.value,
                execution_id,
            )
        return self._row_to_workflow_execution(row) if row else None

    async def complete_execution(
        self, execution_id: str, output: Dict[str, Any]
    ) -> Optional[WorkflowExecution]:
        """Mark an execution as completed."""
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                UPDATE workflow_executions
                SET status = $1, output_result = $2, completed_at = NOW(),
                    duration_ms = EXTRACT(EPOCH FROM (NOW() - started_at)) * 1000
                WHERE execution_id = $3
                RETURNING id, execution_id, workflow_id, workflow_version, agent_id,
                          session_id, parent_execution_id, input_parameters, output_result,
                          status, current_node_id, execution_state, checkpoint_id,
                          error_code, error_message, compensation_required,
                          compensation_status, compensated_nodes, started_at,
                          completed_at, duration_ms, trace_id, created_at
                """,
                ExecutionStatus.COMPLETED.value,
                json.dumps(output),
                execution_id,
            )
        return self._row_to_workflow_execution(row) if row else None

    async def fail_execution(
        self, execution_id: str, error_code: str, error_message: str
    ) -> Optional[WorkflowExecution]:
        """Mark an execution as failed."""
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                UPDATE workflow_executions
                SET status = $1, error_code = $2, error_message = $3,
                    completed_at = NOW(),
                    duration_ms = EXTRACT(EPOCH FROM (NOW() - started_at)) * 1000
                WHERE execution_id = $4
                RETURNING id, execution_id, workflow_id, workflow_version, agent_id,
                          session_id, parent_execution_id, input_parameters, output_result,
                          status, current_node_id, execution_state, checkpoint_id,
                          error_code, error_message, compensation_required,
                          compensation_status, compensated_nodes, started_at,
                          completed_at, duration_ms, trace_id, created_at
                """,
                ExecutionStatus.FAILED.value,
                error_code,
                error_message,
                execution_id,
            )
        return self._row_to_workflow_execution(row) if row else None

    async def list_executions(
        self,
        workflow_id: Optional[str] = None,
        status: Optional[ExecutionStatus] = None,
        agent_id: Optional[UUID] = None,
        session_id: Optional[str] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> ExecutionListResponse:
        """List workflow executions with filtering."""
        conditions = ["1=1"]
        params = []
        param_idx = 1

        if workflow_id:
            conditions.append(f"workflow_id = ${param_idx}")
            params.append(workflow_id)
            param_idx += 1

        if status:
            conditions.append(f"status = ${param_idx}")
            params.append(status.value)
            param_idx += 1

        if agent_id:
            conditions.append(f"agent_id = ${param_idx}")
            params.append(agent_id)
            param_idx += 1

        if session_id:
            conditions.append(f"session_id = ${param_idx}")
            params.append(session_id)
            param_idx += 1

        where_clause = " AND ".join(conditions)

        count_query = f"SELECT COUNT(*) FROM workflow_executions WHERE {where_clause}"
        query = f"""
            SELECT id, execution_id, workflow_id, workflow_version, agent_id,
                   session_id, parent_execution_id, input_parameters, output_result,
                   status, current_node_id, execution_state, checkpoint_id,
                   error_code, error_message, compensation_required,
                   compensation_status, compensated_nodes, started_at,
                   completed_at, duration_ms, trace_id, created_at
            FROM workflow_executions
            WHERE {where_clause}
            ORDER BY created_at DESC
            LIMIT ${param_idx} OFFSET ${param_idx + 1}
        """
        params.extend([limit, offset])

        async with self.db_pool.acquire() as conn:
            total = await conn.fetchval(count_query, *params[:-2])
            rows = await conn.fetch(query, *params)

        executions = [self._row_to_workflow_execution(row) for row in rows]
        return ExecutionListResponse(
            executions=executions,
            total=total,
            offset=offset,
            limit=limit,
        )

    # =========================================================================
    # Checkpointing
    # =========================================================================

    async def save_checkpoint(
        self, execution_id: str, state: Dict[str, Any]
    ) -> str:
        """Save an execution checkpoint for resume capability."""
        checkpoint_id = f"ckpt_{uuid4().hex[:8]}"

        async with self.db_pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE workflow_executions
                SET checkpoint_id = $1, execution_state = $2
                WHERE execution_id = $3
                """,
                checkpoint_id,
                json.dumps(state),
                execution_id,
            )

        logger.info(f"Saved checkpoint {checkpoint_id} for execution {execution_id}")
        return checkpoint_id

    async def restore_checkpoint(
        self, execution_id: str, checkpoint_id: str
    ) -> Optional[Dict[str, Any]]:
        """Restore execution state from a checkpoint."""
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT execution_state FROM workflow_executions
                WHERE execution_id = $1 AND checkpoint_id = $2
                """,
                execution_id,
                checkpoint_id,
            )

        if row and row["execution_state"]:
            return json.loads(row["execution_state"]) if isinstance(row["execution_state"], str) else row["execution_state"]
        return None

    # =========================================================================
    # Node Executions
    # =========================================================================

    async def record_node_execution(self, data: NodeExecutionCreate) -> WorkflowNodeExecution:
        """Record the start of a node execution."""
        node_execution_id = f"node_{uuid4().hex[:12]}"

        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO workflow_node_executions
                (node_execution_id, execution_id, node_id, node_type, status,
                 input_data, started_at)
                VALUES ($1, $2, $3, $4, $5, $6, NOW())
                RETURNING id, node_execution_id, execution_id, node_id, node_type,
                          status, input_data, output_data, error_code, error_message,
                          retry_count, max_retries, compensation_action, compensated,
                          started_at, completed_at, duration_ms, created_at
                """,
                node_execution_id,
                data.execution_id,
                data.node_id,
                data.node_type.value,
                NodeExecutionStatus.RUNNING.value,
                json.dumps(data.input_data),
            )

        return self._row_to_node_execution(row)

    async def update_node_execution(
        self, node_execution_id: str, data: NodeExecutionUpdate
    ) -> Optional[WorkflowNodeExecution]:
        """Update a node execution."""
        updates = []
        params = []
        param_idx = 1

        update_data = data.model_dump(exclude_unset=True)

        for field, value in update_data.items():
            if value is not None:
                if field == "status":
                    value = value.value if hasattr(value, "value") else value
                elif field == "output_data":
                    value = json.dumps(value)
                updates.append(f"{field} = ${param_idx}")
                params.append(value)
                param_idx += 1

        if not updates:
            return await self.get_node_execution(node_execution_id)

        params.append(node_execution_id)
        query = f"""
            UPDATE workflow_node_executions
            SET {', '.join(updates)}
            WHERE node_execution_id = ${param_idx}
            RETURNING id, node_execution_id, execution_id, node_id, node_type,
                      status, input_data, output_data, error_code, error_message,
                      retry_count, max_retries, compensation_action, compensated,
                      started_at, completed_at, duration_ms, created_at
        """

        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow(query, *params)

        return self._row_to_node_execution(row) if row else None

    async def complete_node_execution(
        self, node_execution_id: str, output: Dict[str, Any]
    ) -> Optional[WorkflowNodeExecution]:
        """Mark a node execution as completed."""
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                UPDATE workflow_node_executions
                SET status = $1, output_data = $2, completed_at = NOW(),
                    duration_ms = EXTRACT(EPOCH FROM (NOW() - started_at)) * 1000
                WHERE node_execution_id = $3
                RETURNING id, node_execution_id, execution_id, node_id, node_type,
                          status, input_data, output_data, error_code, error_message,
                          retry_count, max_retries, compensation_action, compensated,
                          started_at, completed_at, duration_ms, created_at
                """,
                NodeExecutionStatus.COMPLETED.value,
                json.dumps(output),
                node_execution_id,
            )
        return self._row_to_node_execution(row) if row else None

    async def fail_node_execution(
        self, node_execution_id: str, error_code: str, error_message: str
    ) -> Optional[WorkflowNodeExecution]:
        """Mark a node execution as failed."""
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                UPDATE workflow_node_executions
                SET status = $1, error_code = $2, error_message = $3,
                    completed_at = NOW(),
                    duration_ms = EXTRACT(EPOCH FROM (NOW() - started_at)) * 1000
                WHERE node_execution_id = $4
                RETURNING id, node_execution_id, execution_id, node_id, node_type,
                          status, input_data, output_data, error_code, error_message,
                          retry_count, max_retries, compensation_action, compensated,
                          started_at, completed_at, duration_ms, created_at
                """,
                NodeExecutionStatus.FAILED.value,
                error_code,
                error_message,
                node_execution_id,
            )
        return self._row_to_node_execution(row) if row else None

    async def get_node_execution(
        self, node_execution_id: str
    ) -> Optional[WorkflowNodeExecution]:
        """Get a node execution by ID."""
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT id, node_execution_id, execution_id, node_id, node_type,
                       status, input_data, output_data, error_code, error_message,
                       retry_count, max_retries, compensation_action, compensated,
                       started_at, completed_at, duration_ms, created_at
                FROM workflow_node_executions
                WHERE node_execution_id = $1
                """,
                node_execution_id,
            )
        return self._row_to_node_execution(row) if row else None

    async def list_node_executions(
        self, execution_id: str
    ) -> List[WorkflowNodeExecution]:
        """List all node executions for a workflow execution."""
        async with self.db_pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT id, node_execution_id, execution_id, node_id, node_type,
                       status, input_data, output_data, error_code, error_message,
                       retry_count, max_retries, compensation_action, compensated,
                       started_at, completed_at, duration_ms, created_at
                FROM workflow_node_executions
                WHERE execution_id = $1
                ORDER BY created_at ASC
                """,
                execution_id,
            )
        return [self._row_to_node_execution(row) for row in rows]

    # =========================================================================
    # Triggers
    # =========================================================================

    async def create_trigger(self, data: WorkflowTriggerCreate) -> WorkflowTrigger:
        """Create a workflow trigger."""
        trigger_id = f"trig_{uuid4().hex[:12]}"

        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO workflow_triggers
                (trigger_id, workflow_id, trigger_type, trigger_config, enabled, metadata)
                VALUES ($1, $2, $3, $4, $5, $6)
                RETURNING id, trigger_id, workflow_id, trigger_type, trigger_config,
                          enabled, last_triggered_at, trigger_count, metadata,
                          created_at, updated_at
                """,
                trigger_id,
                data.workflow_id,
                data.trigger_type.value,
                json.dumps(data.trigger_config),
                data.enabled,
                json.dumps(data.metadata),
            )

        return self._row_to_trigger(row)

    async def get_trigger(self, trigger_id: str) -> Optional[WorkflowTrigger]:
        """Get a trigger by ID."""
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT id, trigger_id, workflow_id, trigger_type, trigger_config,
                       enabled, last_triggered_at, trigger_count, metadata,
                       created_at, updated_at
                FROM workflow_triggers
                WHERE trigger_id = $1
                """,
                trigger_id,
            )
        return self._row_to_trigger(row) if row else None

    async def update_trigger(
        self, trigger_id: str, data: WorkflowTriggerUpdate
    ) -> Optional[WorkflowTrigger]:
        """Update a trigger."""
        updates = []
        params = []
        param_idx = 1

        update_data = data.model_dump(exclude_unset=True)

        for field, value in update_data.items():
            if value is not None:
                if field in ("trigger_config", "metadata"):
                    value = json.dumps(value)
                updates.append(f"{field} = ${param_idx}")
                params.append(value)
                param_idx += 1

        if not updates:
            return await self.get_trigger(trigger_id)

        updates.append("updated_at = NOW()")
        params.append(trigger_id)

        query = f"""
            UPDATE workflow_triggers
            SET {', '.join(updates)}
            WHERE trigger_id = ${param_idx}
            RETURNING id, trigger_id, workflow_id, trigger_type, trigger_config,
                      enabled, last_triggered_at, trigger_count, metadata,
                      created_at, updated_at
        """

        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow(query, *params)

        return self._row_to_trigger(row) if row else None

    async def record_trigger_fired(self, trigger_id: str) -> None:
        """Record that a trigger has fired."""
        async with self.db_pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE workflow_triggers
                SET last_triggered_at = NOW(), trigger_count = trigger_count + 1
                WHERE trigger_id = $1
                """,
                trigger_id,
            )

    async def list_triggers(
        self, workflow_id: Optional[str] = None, enabled: Optional[bool] = None
    ) -> List[WorkflowTrigger]:
        """List triggers with optional filtering."""
        conditions = ["1=1"]
        params = []
        param_idx = 1

        if workflow_id:
            conditions.append(f"workflow_id = ${param_idx}")
            params.append(workflow_id)
            param_idx += 1

        if enabled is not None:
            conditions.append(f"enabled = ${param_idx}")
            params.append(enabled)
            param_idx += 1

        where_clause = " AND ".join(conditions)
        query = f"""
            SELECT id, trigger_id, workflow_id, trigger_type, trigger_config,
                   enabled, last_triggered_at, trigger_count, metadata,
                   created_at, updated_at
            FROM workflow_triggers
            WHERE {where_clause}
            ORDER BY created_at DESC
        """

        async with self.db_pool.acquire() as conn:
            rows = await conn.fetch(query, *params)

        return [self._row_to_trigger(row) for row in rows]

    async def delete_trigger(self, trigger_id: str) -> bool:
        """Delete a trigger."""
        async with self.db_pool.acquire() as conn:
            result = await conn.execute(
                "DELETE FROM workflow_triggers WHERE trigger_id = $1",
                trigger_id,
            )
        return "DELETE 1" in result

    # =========================================================================
    # Approval Requests
    # =========================================================================

    async def create_approval_request(
        self, data: ApprovalRequestCreate
    ) -> WorkflowApprovalRequest:
        """Create an approval request for human-in-the-loop."""
        approval_id = f"appr_{uuid4().hex[:12]}"

        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO workflow_approval_requests
                (approval_id, execution_id, node_id, request_type, request_message,
                 request_data, status, expires_at)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                RETURNING id, approval_id, execution_id, node_id, request_type,
                          request_message, request_data, status, responded_by,
                          response_data, responded_at, expires_at, created_at
                """,
                approval_id,
                data.execution_id,
                data.node_id,
                data.request_type.value,
                data.request_message,
                json.dumps(data.request_data),
                ApprovalStatus.PENDING.value,
                data.expires_at,
            )

        # Update execution status to waiting_approval
        await self.update_execution(
            data.execution_id,
            WorkflowExecutionUpdate(status=ExecutionStatus.WAITING_APPROVAL),
        )

        return self._row_to_approval(row)

    async def get_approval_request(
        self, approval_id: str
    ) -> Optional[WorkflowApprovalRequest]:
        """Get an approval request by ID."""
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT id, approval_id, execution_id, node_id, request_type,
                       request_message, request_data, status, responded_by,
                       response_data, responded_at, expires_at, created_at
                FROM workflow_approval_requests
                WHERE approval_id = $1
                """,
                approval_id,
            )
        return self._row_to_approval(row) if row else None

    async def respond_to_approval(
        self, approval_id: str, response: ApprovalResponse
    ) -> Optional[WorkflowApprovalRequest]:
        """Record a response to an approval request."""
        status = ApprovalStatus.APPROVED if response.approved else ApprovalStatus.REJECTED

        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                UPDATE workflow_approval_requests
                SET status = $1, responded_by = $2, response_data = $3,
                    responded_at = NOW()
                WHERE approval_id = $4
                RETURNING id, approval_id, execution_id, node_id, request_type,
                          request_message, request_data, status, responded_by,
                          response_data, responded_at, expires_at, created_at
                """,
                status.value,
                response.responded_by,
                json.dumps(response.response_data),
                approval_id,
            )

        if row:
            # Resume execution if approved
            execution_id = row["execution_id"]
            if response.approved:
                await self.update_execution(
                    execution_id,
                    WorkflowExecutionUpdate(status=ExecutionStatus.RUNNING),
                )

        return self._row_to_approval(row) if row else None

    async def list_pending_approvals(
        self, execution_id: Optional[str] = None
    ) -> List[WorkflowApprovalRequest]:
        """List pending approval requests."""
        if execution_id:
            query = """
                SELECT id, approval_id, execution_id, node_id, request_type,
                       request_message, request_data, status, responded_by,
                       response_data, responded_at, expires_at, created_at
                FROM workflow_approval_requests
                WHERE execution_id = $1 AND status = 'pending'
                ORDER BY created_at ASC
            """
            params = [execution_id]
        else:
            query = """
                SELECT id, approval_id, execution_id, node_id, request_type,
                       request_message, request_data, status, responded_by,
                       response_data, responded_at, expires_at, created_at
                FROM workflow_approval_requests
                WHERE status = 'pending'
                ORDER BY created_at ASC
            """
            params = []

        async with self.db_pool.acquire() as conn:
            rows = await conn.fetch(query, *params)

        return [self._row_to_approval(row) for row in rows]

    async def expire_old_approvals(self) -> int:
        """Expire approval requests past their deadline."""
        async with self.db_pool.acquire() as conn:
            result = await conn.execute(
                """
                UPDATE workflow_approval_requests
                SET status = 'expired'
                WHERE status = 'pending' AND expires_at < NOW()
                """
            )
        # Parse "UPDATE N" to get count
        count = int(result.split()[-1]) if result else 0
        return count

    # =========================================================================
    # Saga/Compensation
    # =========================================================================

    async def mark_for_compensation(self, execution_id: str) -> Optional[WorkflowExecution]:
        """Mark an execution as requiring compensation."""
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                UPDATE workflow_executions
                SET compensation_required = true,
                    compensation_status = $1,
                    status = $2
                WHERE execution_id = $3
                RETURNING id, execution_id, workflow_id, workflow_version, agent_id,
                          session_id, parent_execution_id, input_parameters, output_result,
                          status, current_node_id, execution_state, checkpoint_id,
                          error_code, error_message, compensation_required,
                          compensation_status, compensated_nodes, started_at,
                          completed_at, duration_ms, trace_id, created_at
                """,
                CompensationStatus.PENDING.value,
                ExecutionStatus.COMPENSATING.value,
                execution_id,
            )
        return self._row_to_workflow_execution(row) if row else None

    async def record_compensated_node(
        self, execution_id: str, node_id: str
    ) -> None:
        """Record that a node has been compensated."""
        async with self.db_pool.acquire() as conn:
            # Get current compensated nodes
            row = await conn.fetchrow(
                "SELECT compensated_nodes FROM workflow_executions WHERE execution_id = $1",
                execution_id,
            )
            current = json.loads(row["compensated_nodes"]) if row and row["compensated_nodes"] else []
            current.append(node_id)

            await conn.execute(
                """
                UPDATE workflow_executions
                SET compensated_nodes = $1
                WHERE execution_id = $2
                """,
                json.dumps(current),
                execution_id,
            )

            # Also mark the node execution as compensated
            await conn.execute(
                """
                UPDATE workflow_node_executions
                SET compensated = true, status = 'compensated'
                WHERE execution_id = $1 AND node_id = $2
                """,
                execution_id,
                node_id,
            )

    async def complete_compensation(
        self, execution_id: str
    ) -> Optional[WorkflowExecution]:
        """Mark compensation as complete."""
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                UPDATE workflow_executions
                SET compensation_status = $1, completed_at = NOW()
                WHERE execution_id = $2
                RETURNING id, execution_id, workflow_id, workflow_version, agent_id,
                          session_id, parent_execution_id, input_parameters, output_result,
                          status, current_node_id, execution_state, checkpoint_id,
                          error_code, error_message, compensation_required,
                          compensation_status, compensated_nodes, started_at,
                          completed_at, duration_ms, trace_id, created_at
                """,
                CompensationStatus.COMPLETED.value,
                execution_id,
            )
        return self._row_to_workflow_execution(row) if row else None

    # =========================================================================
    # Response Builders
    # =========================================================================

    async def get_execution_response(
        self, execution_id: str
    ) -> Optional[WorkflowExecutionResponse]:
        """Get full execution details with node executions and approvals."""
        execution = await self.get_execution(execution_id)
        if not execution:
            return None

        node_executions = await self.list_node_executions(execution_id)
        pending_approvals = await self.list_pending_approvals(execution_id)

        return WorkflowExecutionResponse(
            execution=execution,
            node_executions=node_executions,
            pending_approvals=pending_approvals,
        )

    # =========================================================================
    # Row Converters
    # =========================================================================

    def _row_to_workflow_definition(self, row) -> WorkflowDefinition:
        """Convert a database row to WorkflowDefinition."""
        data = dict(row)

        # Parse JSONB fields
        if isinstance(data.get("definition"), str):
            data["definition"] = json.loads(data["definition"])
        if isinstance(data.get("metadata"), str):
            data["metadata"] = json.loads(data["metadata"])

        # Handle tags array
        if data.get("tags") is None:
            data["tags"] = []

        return WorkflowDefinition(**data)

    def _row_to_workflow_execution(self, row) -> WorkflowExecution:
        """Convert a database row to WorkflowExecution."""
        data = dict(row)

        # Parse JSONB fields
        for field in ("input_parameters", "output_result", "execution_state", "compensated_nodes"):
            if isinstance(data.get(field), str):
                data[field] = json.loads(data[field])
            elif data.get(field) is None:
                if field == "compensated_nodes":
                    data[field] = []
                elif field in ("input_parameters", "execution_state"):
                    data[field] = {}

        return WorkflowExecution(**data)

    def _row_to_node_execution(self, row) -> WorkflowNodeExecution:
        """Convert a database row to WorkflowNodeExecution."""
        data = dict(row)

        # Parse JSONB fields
        for field in ("input_data", "output_data", "compensation_action"):
            if isinstance(data.get(field), str):
                data[field] = json.loads(data[field])
            elif data.get(field) is None and field == "input_data":
                data[field] = {}

        return WorkflowNodeExecution(**data)

    def _row_to_trigger(self, row) -> WorkflowTrigger:
        """Convert a database row to WorkflowTrigger."""
        data = dict(row)

        # Parse JSONB fields
        for field in ("trigger_config", "metadata"):
            if isinstance(data.get(field), str):
                data[field] = json.loads(data[field])
            elif data.get(field) is None:
                data[field] = {}

        return WorkflowTrigger(**data)

    def _row_to_approval(self, row) -> WorkflowApprovalRequest:
        """Convert a database row to WorkflowApprovalRequest."""
        data = dict(row)

        # Parse JSONB fields
        for field in ("request_data", "response_data"):
            if isinstance(data.get(field), str):
                data[field] = json.loads(data[field])
            elif data.get(field) is None:
                data[field] = {}

        return WorkflowApprovalRequest(**data)
