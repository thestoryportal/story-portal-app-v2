"""Service registry events router for L11 Integration Layer."""

import json
from datetime import datetime
from typing import Optional, List

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..database import db

router = APIRouter(prefix="/service-registry-events", tags=["integration"])


class ServiceRegistryEventCreate(BaseModel):
    """Service registry event creation model."""
    event_id: str
    timestamp: str
    service_id: str
    event_type: str
    layer: Optional[str] = None
    host: Optional[str] = None
    port: Optional[int] = None
    health_status: Optional[str] = None
    capabilities: Optional[List[str]] = None
    metadata: Optional[dict] = None


@router.post("/", status_code=201)
async def create_service_registry_event(event_data: ServiceRegistryEventCreate):
    """Create a new service registry event record."""
    try:
        timestamp = datetime.fromisoformat(event_data.timestamp.replace('Z', '+00:00'))
        metadata_json = json.dumps(event_data.metadata or {})

        query = """
            INSERT INTO service_registry_events (
                event_id, timestamp, service_id, event_type, layer, host, port,
                health_status, capabilities, metadata
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
            RETURNING id, event_id, timestamp, service_id, event_type, created_at
        """

        async with db.pool.acquire() as conn:
            record = await conn.fetchrow(
                query,
                event_data.event_id,
                timestamp,
                event_data.service_id,
                event_data.event_type,
                event_data.layer,
                event_data.host,
                event_data.port,
                event_data.health_status,
                event_data.capabilities or [],
                metadata_json,
            )

            return dict(record)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create service registry event: {str(e)}")


@router.get("/{event_id}")
async def get_service_registry_event(event_id: str):
    """Get service registry event by event_id."""
    try:
        query = "SELECT * FROM service_registry_events WHERE event_id = $1"
        async with db.pool.acquire() as conn:
            record = await conn.fetchrow(query, event_id)

            if not record:
                raise HTTPException(status_code=404, detail="Service registry event not found")

            return dict(record)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/")
async def list_service_registry_events(
    service_id: Optional[str] = None,
    event_type: Optional[str] = None,
    layer: Optional[str] = None,
    limit: int = 100,
    offset: int = 0
):
    """List service registry events with filters."""
    try:
        conditions = []
        params = []
        param_index = 1

        if service_id:
            conditions.append(f"service_id = ${param_index}")
            params.append(service_id)
            param_index += 1

        if event_type:
            conditions.append(f"event_type = ${param_index}")
            params.append(event_type)
            param_index += 1

        if layer:
            conditions.append(f"layer = ${param_index}")
            params.append(layer)
            param_index += 1

        where_clause = " AND ".join(conditions) if conditions else "TRUE"

        query = f"""
            SELECT * FROM service_registry_events
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
