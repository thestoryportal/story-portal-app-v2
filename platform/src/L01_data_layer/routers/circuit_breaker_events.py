"""Circuit breaker events router for L11 Integration Layer."""

import json
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..database import db

router = APIRouter(prefix="/circuit-breaker-events", tags=["integration"])


class CircuitBreakerEventCreate(BaseModel):
    """Circuit breaker event creation model."""
    event_id: str
    timestamp: str
    service_id: str
    circuit_name: str
    event_type: str
    state_to: str
    state_from: Optional[str] = None
    failure_count: Optional[int] = None
    success_count: Optional[int] = None
    failure_threshold: Optional[int] = None
    timeout_seconds: Optional[int] = None
    error_message: Optional[str] = None
    metadata: Optional[dict] = None


@router.post("/", status_code=201)
async def create_circuit_breaker_event(event_data: CircuitBreakerEventCreate):
    """Create a new circuit breaker event record."""
    try:
        timestamp = datetime.fromisoformat(event_data.timestamp.replace('Z', '+00:00'))
        metadata_json = json.dumps(event_data.metadata or {})

        query = """
            INSERT INTO circuit_breaker_events (
                event_id, timestamp, service_id, circuit_name, event_type, state_from,
                state_to, failure_count, success_count, failure_threshold,
                timeout_seconds, error_message, metadata
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)
            RETURNING id, event_id, timestamp, service_id, circuit_name, event_type, state_to, created_at
        """

        async with db.pool.acquire() as conn:
            record = await conn.fetchrow(
                query,
                event_data.event_id,
                timestamp,
                event_data.service_id,
                event_data.circuit_name,
                event_data.event_type,
                event_data.state_from,
                event_data.state_to,
                event_data.failure_count,
                event_data.success_count,
                event_data.failure_threshold,
                event_data.timeout_seconds,
                event_data.error_message,
                metadata_json,
            )

            return dict(record)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create circuit breaker event: {str(e)}")


@router.get("/{event_id}")
async def get_circuit_breaker_event(event_id: str):
    """Get circuit breaker event by event_id."""
    try:
        query = "SELECT * FROM circuit_breaker_events WHERE event_id = $1"
        async with db.pool.acquire() as conn:
            record = await conn.fetchrow(query, event_id)

            if not record:
                raise HTTPException(status_code=404, detail="Circuit breaker event not found")

            return dict(record)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/")
async def list_circuit_breaker_events(
    service_id: Optional[str] = None,
    circuit_name: Optional[str] = None,
    event_type: Optional[str] = None,
    state_to: Optional[str] = None,
    limit: int = 100,
    offset: int = 0
):
    """List circuit breaker events with filters."""
    try:
        conditions = []
        params = []
        param_index = 1

        if service_id:
            conditions.append(f"service_id = ${param_index}")
            params.append(service_id)
            param_index += 1

        if circuit_name:
            conditions.append(f"circuit_name = ${param_index}")
            params.append(circuit_name)
            param_index += 1

        if event_type:
            conditions.append(f"event_type = ${param_index}")
            params.append(event_type)
            param_index += 1

        if state_to:
            conditions.append(f"state_to = ${param_index}")
            params.append(state_to)
            param_index += 1

        where_clause = " AND ".join(conditions) if conditions else "TRUE"

        query = f"""
            SELECT * FROM circuit_breaker_events
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
