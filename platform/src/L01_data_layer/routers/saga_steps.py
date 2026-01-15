"""Saga steps router for L11 Integration Layer."""

import json
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..database import db

router = APIRouter(prefix="/saga-steps", tags=["integration"])


class SagaStepCreate(BaseModel):
    """Saga step creation model."""
    step_id: str
    saga_id: str
    step_name: str
    step_index: int
    service_id: str
    status: str = "pending"
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    request: Optional[dict] = None
    response: Optional[dict] = None
    error_message: Optional[str] = None
    compensation_executed: bool = False
    compensation_result: Optional[dict] = None
    retry_count: int = 0
    metadata: Optional[dict] = None


class SagaStepUpdate(BaseModel):
    """Saga step update model."""
    status: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    response: Optional[dict] = None
    error_message: Optional[str] = None
    compensation_executed: Optional[bool] = None
    compensation_result: Optional[dict] = None
    retry_count: Optional[int] = None


@router.post("/", status_code=201)
async def create_saga_step(step_data: SagaStepCreate):
    """Create a new saga step record."""
    try:
        started_at = None
        if step_data.started_at:
            started_at = datetime.fromisoformat(step_data.started_at.replace('Z', '+00:00'))

        completed_at = None
        if step_data.completed_at:
            completed_at = datetime.fromisoformat(step_data.completed_at.replace('Z', '+00:00'))

        request_json = json.dumps(step_data.request or {})
        response_json = json.dumps(step_data.response) if step_data.response else None
        compensation_result_json = json.dumps(step_data.compensation_result) if step_data.compensation_result else None
        metadata_json = json.dumps(step_data.metadata or {})

        query = """
            INSERT INTO saga_steps (
                step_id, saga_id, step_name, step_index, service_id, status,
                started_at, completed_at, request, response, error_message,
                compensation_executed, compensation_result, retry_count, metadata
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15)
            RETURNING id, step_id, saga_id, step_name, step_index, status, created_at
        """

        async with db.pool.acquire() as conn:
            record = await conn.fetchrow(
                query,
                step_data.step_id,
                step_data.saga_id,
                step_data.step_name,
                step_data.step_index,
                step_data.service_id,
                step_data.status,
                started_at,
                completed_at,
                request_json,
                response_json,
                step_data.error_message,
                step_data.compensation_executed,
                compensation_result_json,
                step_data.retry_count,
                metadata_json,
            )

            return dict(record)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create saga step: {str(e)}")


@router.patch("/{step_id}")
async def update_saga_step(step_id: str, update_data: SagaStepUpdate):
    """Update a saga step."""
    try:
        updates = []
        params = []
        param_index = 1

        if update_data.status:
            updates.append(f"status = ${param_index}")
            params.append(update_data.status)
            param_index += 1

        if update_data.started_at:
            started_at = datetime.fromisoformat(update_data.started_at.replace('Z', '+00:00'))
            updates.append(f"started_at = ${param_index}")
            params.append(started_at)
            param_index += 1

        if update_data.completed_at:
            completed_at = datetime.fromisoformat(update_data.completed_at.replace('Z', '+00:00'))
            updates.append(f"completed_at = ${param_index}")
            params.append(completed_at)
            param_index += 1

        if update_data.response:
            updates.append(f"response = ${param_index}")
            params.append(json.dumps(update_data.response))
            param_index += 1

        if update_data.error_message:
            updates.append(f"error_message = ${param_index}")
            params.append(update_data.error_message)
            param_index += 1

        if update_data.compensation_executed is not None:
            updates.append(f"compensation_executed = ${param_index}")
            params.append(update_data.compensation_executed)
            param_index += 1

        if update_data.compensation_result:
            updates.append(f"compensation_result = ${param_index}")
            params.append(json.dumps(update_data.compensation_result))
            param_index += 1

        if update_data.retry_count is not None:
            updates.append(f"retry_count = ${param_index}")
            params.append(update_data.retry_count)
            param_index += 1

        if not updates:
            raise HTTPException(status_code=400, detail="No fields to update")

        updates.append(f"updated_at = NOW()")
        set_clause = ", ".join(updates)
        params.append(step_id)

        query = f"""
            UPDATE saga_steps
            SET {set_clause}
            WHERE step_id = ${param_index}
            RETURNING *
        """

        async with db.pool.acquire() as conn:
            record = await conn.fetchrow(query, *params)

            if not record:
                raise HTTPException(status_code=404, detail="Saga step not found")

            return dict(record)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{step_id}")
async def get_saga_step(step_id: str):
    """Get saga step by step_id."""
    try:
        query = "SELECT * FROM saga_steps WHERE step_id = $1"
        async with db.pool.acquire() as conn:
            record = await conn.fetchrow(query, step_id)

            if not record:
                raise HTTPException(status_code=404, detail="Saga step not found")

            return dict(record)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/")
async def list_saga_steps(
    saga_id: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 100,
    offset: int = 0
):
    """List saga steps with filters."""
    try:
        conditions = []
        params = []
        param_index = 1

        if saga_id:
            conditions.append(f"saga_id = ${param_index}")
            params.append(saga_id)
            param_index += 1

        if status:
            conditions.append(f"status = ${param_index}")
            params.append(status)
            param_index += 1

        where_clause = " AND ".join(conditions) if conditions else "TRUE"

        query = f"""
            SELECT * FROM saga_steps
            WHERE {where_clause}
            ORDER BY saga_id, step_index
            LIMIT ${param_index} OFFSET ${param_index + 1}
        """
        params.extend([limit, offset])

        async with db.pool.acquire() as conn:
            records = await conn.fetch(query, *params)
            return [dict(record) for record in records]

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
