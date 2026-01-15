"""Rate limit events router for L09 API Gateway integration."""

import json
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..database import db

router = APIRouter(prefix="/rate-limit-events", tags=["api-gateway"])


class RateLimitEventCreate(BaseModel):
    """Rate limit event creation model."""
    event_id: str
    timestamp: str
    consumer_id: str
    rate_limit_tier: str
    tokens_requested: int = 1
    tokens_remaining: int
    tokens_limit: int
    window_start: str
    window_end: str
    tenant_id: Optional[str] = None
    endpoint: Optional[str] = None
    exceeded: bool = False
    metadata: Optional[dict] = None


@router.post("/", status_code=201)
async def create_rate_limit_event(event_data: RateLimitEventCreate):
    """Create a new rate limit event record."""
    try:
        timestamp = datetime.fromisoformat(event_data.timestamp.replace('Z', '+00:00'))
        window_start = datetime.fromisoformat(event_data.window_start.replace('Z', '+00:00'))
        window_end = datetime.fromisoformat(event_data.window_end.replace('Z', '+00:00'))
        metadata_json = json.dumps(event_data.metadata or {})

        query = """
            INSERT INTO rate_limit_events (
                event_id, timestamp, consumer_id, tenant_id, rate_limit_tier,
                endpoint, tokens_requested, tokens_remaining, tokens_limit,
                window_start, window_end, exceeded, metadata
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13)
            RETURNING id, event_id, timestamp, consumer_id, rate_limit_tier,
                      tokens_remaining, tokens_limit, exceeded, created_at
        """

        async with db.pool.acquire() as conn:
            record = await conn.fetchrow(
                query,
                event_data.event_id,
                timestamp,
                event_data.consumer_id,
                event_data.tenant_id,
                event_data.rate_limit_tier,
                event_data.endpoint,
                event_data.tokens_requested,
                event_data.tokens_remaining,
                event_data.tokens_limit,
                window_start,
                window_end,
                event_data.exceeded,
                metadata_json,
            )

            return dict(record)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create rate limit event: {str(e)}")


@router.get("/{event_id}")
async def get_rate_limit_event(event_id: str):
    """Get rate limit event by event_id."""
    try:
        query = "SELECT * FROM rate_limit_events WHERE event_id = $1"
        async with db.pool.acquire() as conn:
            record = await conn.fetchrow(query, event_id)

            if not record:
                raise HTTPException(status_code=404, detail="Rate limit event not found")

            return dict(record)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/")
async def list_rate_limit_events(
    consumer_id: Optional[str] = None,
    exceeded: Optional[bool] = None,
    limit: int = 100,
    offset: int = 0
):
    """List rate limit events with filters."""
    try:
        conditions = []
        params = []
        param_index = 1

        if consumer_id:
            conditions.append(f"consumer_id = ${param_index}")
            params.append(consumer_id)
            param_index += 1

        if exceeded is not None:
            conditions.append(f"exceeded = ${param_index}")
            params.append(exceeded)
            param_index += 1

        where_clause = " AND ".join(conditions) if conditions else "TRUE"

        query = f"""
            SELECT * FROM rate_limit_events
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
