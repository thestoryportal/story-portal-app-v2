"""Control operations router for L10 Human Interface integration."""

import json
from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..database import db

router = APIRouter(prefix="/control-operations", tags=["human-interface"])


class ControlOperationCreate(BaseModel):
    """Control operation creation model."""
    operation_id: str
    timestamp: str
    user_id: str
    operation_type: str
    command: str
    target_agent_id: Optional[str] = None
    target_agent_did: Optional[str] = None
    parameters: Optional[dict] = None
    status: str = "pending"
    result: Optional[dict] = None
    error_message: Optional[str] = None
    executed_at: Optional[str] = None
    completed_at: Optional[str] = None
    metadata: Optional[dict] = None


class ControlOperationUpdate(BaseModel):
    """Control operation update model."""
    status: Optional[str] = None
    result: Optional[dict] = None
    error_message: Optional[str] = None
    executed_at: Optional[str] = None
    completed_at: Optional[str] = None


@router.post("/", status_code=201)
async def create_control_operation(operation_data: ControlOperationCreate):
    """Create a new control operation record."""
    try:
        timestamp = datetime.fromisoformat(operation_data.timestamp.replace('Z', '+00:00')).replace(tzinfo=None)
        parameters_json = json.dumps(operation_data.parameters or {})
        result_json = json.dumps(operation_data.result) if operation_data.result else None
        metadata_json = json.dumps(operation_data.metadata or {})

        executed_at = None
        if operation_data.executed_at:
            executed_at = datetime.fromisoformat(operation_data.executed_at.replace('Z', '+00:00')).replace(tzinfo=None)

        completed_at = None
        if operation_data.completed_at:
            completed_at = datetime.fromisoformat(operation_data.completed_at.replace('Z', '+00:00')).replace(tzinfo=None)

        target_agent_uuid = None
        if operation_data.target_agent_id:
            try:
                target_agent_uuid = UUID(operation_data.target_agent_id)
            except ValueError:
                pass

        query = """
            INSERT INTO control_operations (
                operation_id, timestamp, user_id, operation_type, target_agent_id,
                target_agent_did, command, parameters, status, result,
                error_message, executed_at, completed_at, metadata
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14)
            RETURNING id, operation_id, timestamp, operation_type, command, status, created_at
        """

        async with db.pool.acquire() as conn:
            record = await conn.fetchrow(
                query,
                operation_data.operation_id,
                timestamp,
                operation_data.user_id,
                operation_data.operation_type,
                target_agent_uuid,
                operation_data.target_agent_did,
                operation_data.command,
                parameters_json,
                operation_data.status,
                result_json,
                operation_data.error_message,
                executed_at,
                completed_at,
                metadata_json,
            )

            return dict(record)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create control operation: {str(e)}")


@router.patch("/{operation_id}")
async def update_control_operation(operation_id: str, update_data: ControlOperationUpdate):
    """Update a control operation."""
    try:
        updates = []
        params = []
        param_index = 1

        if update_data.status:
            updates.append(f"status = ${param_index}")
            params.append(update_data.status)
            param_index += 1

        if update_data.result:
            updates.append(f"result = ${param_index}")
            params.append(json.dumps(update_data.result))
            param_index += 1

        if update_data.error_message:
            updates.append(f"error_message = ${param_index}")
            params.append(update_data.error_message)
            param_index += 1

        if update_data.executed_at:
            executed_at = datetime.fromisoformat(update_data.executed_at.replace('Z', '+00:00')).replace(tzinfo=None)
            updates.append(f"executed_at = ${param_index}")
            params.append(executed_at)
            param_index += 1

        if update_data.completed_at:
            completed_at = datetime.fromisoformat(update_data.completed_at.replace('Z', '+00:00')).replace(tzinfo=None)
            updates.append(f"completed_at = ${param_index}")
            params.append(completed_at)
            param_index += 1

        if not updates:
            raise HTTPException(status_code=400, detail="No fields to update")

        set_clause = ", ".join(updates)
        params.append(operation_id)

        query = f"""
            UPDATE control_operations
            SET {set_clause}
            WHERE operation_id = ${param_index}
            RETURNING *
        """

        async with db.pool.acquire() as conn:
            record = await conn.fetchrow(query, *params)

            if not record:
                raise HTTPException(status_code=404, detail="Control operation not found")

            return dict(record)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{operation_id}")
async def get_control_operation(operation_id: str):
    """Get control operation by operation_id."""
    try:
        query = "SELECT * FROM control_operations WHERE operation_id = $1"
        async with db.pool.acquire() as conn:
            record = await conn.fetchrow(query, operation_id)

            if not record:
                raise HTTPException(status_code=404, detail="Control operation not found")

            return dict(record)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/")
async def list_control_operations(
    user_id: Optional[str] = None,
    status: Optional[str] = None,
    operation_type: Optional[str] = None,
    limit: int = 100,
    offset: int = 0
):
    """List control operations with filters."""
    try:
        conditions = []
        params = []
        param_index = 1

        if user_id:
            conditions.append(f"user_id = ${param_index}")
            params.append(user_id)
            param_index += 1

        if status:
            conditions.append(f"status = ${param_index}")
            params.append(status)
            param_index += 1

        if operation_type:
            conditions.append(f"operation_type = ${param_index}")
            params.append(operation_type)
            param_index += 1

        where_clause = " AND ".join(conditions) if conditions else "TRUE"

        query = f"""
            SELECT * FROM control_operations
            WHERE {where_clause}
            ORDER BY timestamp DESC
            LIMIT ${param_index} OFFSET ${param_index + 1}
        """
        params.extend([limit, offset])

        async with db.pool.acquire() as conn:
            records = await conn.fetch(query, *params)
            return [dict(record) for record in records]

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
