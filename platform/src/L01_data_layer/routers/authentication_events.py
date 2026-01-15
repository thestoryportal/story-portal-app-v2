"""Authentication events router for L09 API Gateway integration."""

import json
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..database import db

router = APIRouter(prefix="/authentication-events", tags=["api-gateway"])


class AuthenticationEventCreate(BaseModel):
    """Authentication event creation model."""
    event_id: str
    timestamp: str
    auth_method: str
    success: bool
    consumer_id: Optional[str] = None
    tenant_id: Optional[str] = None
    failure_reason: Optional[str] = None
    client_ip: Optional[str] = None
    user_agent: Optional[str] = None
    metadata: Optional[dict] = None


@router.post("/", status_code=201)
async def create_authentication_event(event_data: AuthenticationEventCreate):
    """Create a new authentication event record."""
    try:
        timestamp = datetime.fromisoformat(event_data.timestamp.replace('Z', '+00:00'))
        metadata_json = json.dumps(event_data.metadata or {})

        query = """
            INSERT INTO authentication_events (
                event_id, timestamp, consumer_id, tenant_id, auth_method,
                success, failure_reason, client_ip, user_agent, metadata
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
            RETURNING id, event_id, timestamp, auth_method, success, created_at
        """

        async with db.pool.acquire() as conn:
            record = await conn.fetchrow(
                query,
                event_data.event_id,
                timestamp,
                event_data.consumer_id,
                event_data.tenant_id,
                event_data.auth_method,
                event_data.success,
                event_data.failure_reason,
                event_data.client_ip,
                event_data.user_agent,
                metadata_json,
            )

            return dict(record)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create authentication event: {str(e)}")


@router.get("/{event_id}")
async def get_authentication_event(event_id: str):
    """Get authentication event by event_id."""
    try:
        query = "SELECT * FROM authentication_events WHERE event_id = $1"
        async with db.pool.acquire() as conn:
            record = await conn.fetchrow(query, event_id)

            if not record:
                raise HTTPException(status_code=404, detail="Authentication event not found")

            return dict(record)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/")
async def list_authentication_events(
    consumer_id: Optional[str] = None,
    success: Optional[bool] = None,
    auth_method: Optional[str] = None,
    limit: int = 100,
    offset: int = 0
):
    """List authentication events with filters."""
    try:
        conditions = []
        params = []
        param_index = 1

        if consumer_id:
            conditions.append(f"consumer_id = ${param_index}")
            params.append(consumer_id)
            param_index += 1

        if success is not None:
            conditions.append(f"success = ${param_index}")
            params.append(success)
            param_index += 1

        if auth_method:
            conditions.append(f"auth_method = ${param_index}")
            params.append(auth_method)
            param_index += 1

        where_clause = " AND ".join(conditions) if conditions else "TRUE"

        query = f"""
            SELECT * FROM authentication_events
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
