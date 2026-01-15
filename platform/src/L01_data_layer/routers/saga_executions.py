"""Saga executions router for L11 Integration Layer."""

import json
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..database import db

router = APIRouter(prefix="/saga-executions", tags=["integration"])


class SagaExecutionCreate(BaseModel):
    """Saga execution creation model."""
    saga_id: str
    saga_name: str
    started_at: str
    steps_total: int
    status: str = "running"
    steps_completed: int = 0
    steps_failed: int = 0
    current_step: Optional[str] = None
    context: Optional[dict] = None
    compensation_mode: bool = False
    completed_at: Optional[str] = None
    error_message: Optional[str] = None
    metadata: Optional[dict] = None


class SagaExecutionUpdate(BaseModel):
    """Saga execution update model."""
    status: Optional[str] = None
    steps_completed: Optional[int] = None
    steps_failed: Optional[int] = None
    current_step: Optional[str] = None
    compensation_mode: Optional[bool] = None
    completed_at: Optional[str] = None
    error_message: Optional[str] = None


@router.post("/", status_code=201)
async def create_saga_execution(saga_data: SagaExecutionCreate):
    """Create a new saga execution record."""
    try:
        started_at = datetime.fromisoformat(saga_data.started_at.replace('Z', '+00:00'))
        completed_at = None
        if saga_data.completed_at:
            completed_at = datetime.fromisoformat(saga_data.completed_at.replace('Z', '+00:00'))

        context_json = json.dumps(saga_data.context or {})
        metadata_json = json.dumps(saga_data.metadata or {})

        query = """
            INSERT INTO saga_executions (
                saga_id, saga_name, status, started_at, completed_at,
                steps_total, steps_completed, steps_failed, current_step,
                context, compensation_mode, error_message, metadata
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)
            RETURNING id, saga_id, saga_name, status, started_at, steps_total, created_at
        """

        async with db.pool.acquire() as conn:
            record = await conn.fetchrow(
                query,
                saga_data.saga_id,
                saga_data.saga_name,
                saga_data.status,
                started_at,
                completed_at,
                saga_data.steps_total,
                saga_data.steps_completed,
                saga_data.steps_failed,
                saga_data.current_step,
                context_json,
                saga_data.compensation_mode,
                saga_data.error_message,
                metadata_json,
            )

            return dict(record)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create saga execution: {str(e)}")


@router.patch("/{saga_id}")
async def update_saga_execution(saga_id: str, update_data: SagaExecutionUpdate):
    """Update a saga execution."""
    try:
        updates = []
        params = []
        param_index = 1

        if update_data.status:
            updates.append(f"status = ${param_index}")
            params.append(update_data.status)
            param_index += 1

        if update_data.steps_completed is not None:
            updates.append(f"steps_completed = ${param_index}")
            params.append(update_data.steps_completed)
            param_index += 1

        if update_data.steps_failed is not None:
            updates.append(f"steps_failed = ${param_index}")
            params.append(update_data.steps_failed)
            param_index += 1

        if update_data.current_step:
            updates.append(f"current_step = ${param_index}")
            params.append(update_data.current_step)
            param_index += 1

        if update_data.compensation_mode is not None:
            updates.append(f"compensation_mode = ${param_index}")
            params.append(update_data.compensation_mode)
            param_index += 1

        if update_data.completed_at:
            completed_at = datetime.fromisoformat(update_data.completed_at.replace('Z', '+00:00'))
            updates.append(f"completed_at = ${param_index}")
            params.append(completed_at)
            param_index += 1

        if update_data.error_message:
            updates.append(f"error_message = ${param_index}")
            params.append(update_data.error_message)
            param_index += 1

        if not updates:
            raise HTTPException(status_code=400, detail="No fields to update")

        updates.append(f"updated_at = NOW()")
        set_clause = ", ".join(updates)
        params.append(saga_id)

        query = f"""
            UPDATE saga_executions
            SET {set_clause}
            WHERE saga_id = ${param_index}
            RETURNING *
        """

        async with db.pool.acquire() as conn:
            record = await conn.fetchrow(query, *params)

            if not record:
                raise HTTPException(status_code=404, detail="Saga execution not found")

            return dict(record)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{saga_id}")
async def get_saga_execution(saga_id: str):
    """Get saga execution by saga_id."""
    try:
        query = "SELECT * FROM saga_executions WHERE saga_id = $1"
        async with db.pool.acquire() as conn:
            record = await conn.fetchrow(query, saga_id)

            if not record:
                raise HTTPException(status_code=404, detail="Saga execution not found")

            return dict(record)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/")
async def list_saga_executions(
    status: Optional[str] = None,
    saga_name: Optional[str] = None,
    limit: int = 100,
    offset: int = 0
):
    """List saga executions with filters."""
    try:
        conditions = []
        params = []
        param_index = 1

        if status:
            conditions.append(f"status = ${param_index}")
            params.append(status)
            param_index += 1

        if saga_name:
            conditions.append(f"saga_name = ${param_index}")
            params.append(saga_name)
            param_index += 1

        where_clause = " AND ".join(conditions) if conditions else "TRUE"

        query = f"""
            SELECT * FROM saga_executions
            WHERE {where_clause}
            ORDER BY started_at DESC
            LIMIT ${param_index} OFFSET ${param_index + 1}
        """
        params.extend([limit, offset])

        async with db.pool.acquire() as conn:
            records = await conn.fetch(query, *params)
            return [dict(record) for record in records]

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
