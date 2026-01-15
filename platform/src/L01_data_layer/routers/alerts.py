"""Alerts API router for L06 Evaluation integration."""

import json
from datetime import datetime
from fastapi import APIRouter, HTTPException
from typing import Optional
from uuid import UUID

from ..database import db

router = APIRouter(prefix="/alerts", tags=["alerts"])


@router.post("/", status_code=201)
async def create_alert(alert_data: dict):
    """Create a new alert record."""
    query = """
        INSERT INTO alerts (
            alert_id, timestamp, severity, type, metric, message,
            channels, delivery_attempts, delivered, last_attempt,
            agent_id, agent_did, tenant_id, metadata
        ) VALUES (
            $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14
        )
        RETURNING *
    """

    async with db.pool.acquire() as conn:
        # Convert timestamp string to datetime if needed
        timestamp = alert_data["timestamp"]
        if isinstance(timestamp, str):
            timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))

        last_attempt = alert_data.get("last_attempt")
        if last_attempt and isinstance(last_attempt, str):
            last_attempt = datetime.fromisoformat(last_attempt.replace('Z', '+00:00'))

        # Convert metadata to JSON string
        metadata_json = json.dumps(alert_data.get("metadata", {}))

        row = await conn.fetchrow(
            query,
            alert_data["alert_id"],
            timestamp,
            alert_data["severity"],
            alert_data["type"],
            alert_data["metric"],
            alert_data["message"],
            alert_data.get("channels", []),
            alert_data.get("delivery_attempts", 0),
            alert_data.get("delivered", False),
            last_attempt,
            alert_data.get("agent_id"),
            alert_data.get("agent_did"),
            alert_data.get("tenant_id"),
            metadata_json
        )

        return dict(row)


@router.get("/{alert_id}")
async def get_alert(alert_id: str):
    """Get alert by alert_id."""
    query = "SELECT * FROM alerts WHERE alert_id = $1"

    async with db.pool.acquire() as conn:
        row = await conn.fetchrow(query, alert_id)
        if not row:
            raise HTTPException(status_code=404, detail="Alert not found")
        return dict(row)


@router.patch("/{alert_id}")
async def update_alert(alert_id: str, update_data: dict):
    """Update alert delivery tracking."""
    updates = []
    params = [alert_id]
    param_count = 2

    if "delivery_attempts" in update_data:
        updates.append(f"delivery_attempts = ${param_count}")
        params.append(update_data["delivery_attempts"])
        param_count += 1

    if "delivered" in update_data:
        updates.append(f"delivered = ${param_count}")
        params.append(update_data["delivered"])
        param_count += 1

    if "last_attempt" in update_data:
        updates.append(f"last_attempt = ${param_count}")
        last_attempt = update_data["last_attempt"]
        if isinstance(last_attempt, str):
            last_attempt = datetime.fromisoformat(last_attempt.replace('Z', '+00:00'))
        params.append(last_attempt)
        param_count += 1

    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")

    query = f"""
        UPDATE alerts
        SET {", ".join(updates)}
        WHERE alert_id = $1
        RETURNING *
    """

    async with db.pool.acquire() as conn:
        row = await conn.fetchrow(query, *params)
        if not row:
            raise HTTPException(status_code=404, detail="Alert not found")
        return dict(row)


@router.get("/")
async def list_alerts(
    severity: Optional[str] = None,
    alert_type: Optional[str] = None,
    delivered: Optional[bool] = None,
    agent_id: Optional[UUID] = None,
    tenant_id: Optional[str] = None,
    limit: int = 100,
    offset: int = 0
):
    """List alerts with filters."""
    conditions = []
    params = []
    param_count = 1

    if severity:
        conditions.append(f"severity = ${param_count}")
        params.append(severity)
        param_count += 1

    if alert_type:
        conditions.append(f"type = ${param_count}")
        params.append(alert_type)
        param_count += 1

    if delivered is not None:
        conditions.append(f"delivered = ${param_count}")
        params.append(delivered)
        param_count += 1

    if agent_id:
        conditions.append(f"agent_id = ${param_count}")
        params.append(agent_id)
        param_count += 1

    if tenant_id:
        conditions.append(f"tenant_id = ${param_count}")
        params.append(tenant_id)
        param_count += 1

    where_clause = " AND ".join(conditions) if conditions else "TRUE"
    query = f"""
        SELECT * FROM alerts
        WHERE {where_clause}
        ORDER BY timestamp DESC
        LIMIT ${param_count} OFFSET ${param_count + 1}
    """
    params.extend([limit, offset])

    async with db.pool.acquire() as conn:
        rows = await conn.fetch(query, *params)
        return [dict(row) for row in rows]
