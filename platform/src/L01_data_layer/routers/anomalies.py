"""Anomalies API router for L06 Evaluation integration."""

from datetime import datetime
from fastapi import APIRouter, HTTPException
from typing import Optional
from uuid import UUID

from ..database import db

router = APIRouter(prefix="/anomalies", tags=["anomalies"])


@router.post("/", status_code=201)
async def create_anomaly(anomaly_data: dict):
    """Create a new anomaly record."""
    query = """
        INSERT INTO anomalies (
            anomaly_id, metric_name, severity, baseline_value, current_value,
            z_score, deviation_percent, confidence, status, detected_at,
            resolved_at, alert_sent, agent_id, agent_did, tenant_id
        ) VALUES (
            $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15
        )
        RETURNING *
    """

    async with db.pool.acquire() as conn:
        # Convert timestamp strings to datetime if needed
        detected_at = anomaly_data["detected_at"]
        if isinstance(detected_at, str):
            detected_at = datetime.fromisoformat(detected_at.replace('Z', '+00:00'))

        resolved_at = anomaly_data.get("resolved_at")
        if resolved_at and isinstance(resolved_at, str):
            resolved_at = datetime.fromisoformat(resolved_at.replace('Z', '+00:00'))

        row = await conn.fetchrow(
            query,
            anomaly_data["anomaly_id"],
            anomaly_data["metric_name"],
            anomaly_data["severity"],
            anomaly_data["baseline_value"],
            anomaly_data["current_value"],
            anomaly_data["z_score"],
            anomaly_data.get("deviation_percent"),
            anomaly_data.get("confidence", 0.95),
            anomaly_data.get("status", "alerting"),
            detected_at,
            resolved_at,
            anomaly_data.get("alert_sent", False),
            anomaly_data.get("agent_id"),
            anomaly_data.get("agent_did"),
            anomaly_data.get("tenant_id")
        )

        return dict(row)


@router.get("/{anomaly_id}")
async def get_anomaly(anomaly_id: str):
    """Get anomaly by anomaly_id."""
    query = "SELECT * FROM anomalies WHERE anomaly_id = $1"

    async with db.pool.acquire() as conn:
        row = await conn.fetchrow(query, anomaly_id)
        if not row:
            raise HTTPException(status_code=404, detail="Anomaly not found")
        return dict(row)


@router.patch("/{anomaly_id}")
async def update_anomaly(anomaly_id: str, update_data: dict):
    """Update anomaly status and resolution."""
    updates = []
    params = [anomaly_id]
    param_count = 2

    if "status" in update_data:
        updates.append(f"status = ${param_count}")
        params.append(update_data["status"])
        param_count += 1

    if "resolved_at" in update_data:
        updates.append(f"resolved_at = ${param_count}")
        resolved_at = update_data["resolved_at"]
        if isinstance(resolved_at, str):
            resolved_at = datetime.fromisoformat(resolved_at.replace('Z', '+00:00'))
        params.append(resolved_at)
        param_count += 1

    if "alert_sent" in update_data:
        updates.append(f"alert_sent = ${param_count}")
        params.append(update_data["alert_sent"])
        param_count += 1

    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")

    query = f"""
        UPDATE anomalies
        SET {", ".join(updates)}
        WHERE anomaly_id = $1
        RETURNING *
    """

    async with db.pool.acquire() as conn:
        row = await conn.fetchrow(query, *params)
        if not row:
            raise HTTPException(status_code=404, detail="Anomaly not found")
        return dict(row)


@router.get("/")
async def list_anomalies(
    metric_name: Optional[str] = None,
    severity: Optional[str] = None,
    status: Optional[str] = None,
    agent_id: Optional[UUID] = None,
    tenant_id: Optional[str] = None,
    limit: int = 100,
    offset: int = 0
):
    """List anomalies with filters."""
    conditions = []
    params = []
    param_count = 1

    if metric_name:
        conditions.append(f"metric_name = ${param_count}")
        params.append(metric_name)
        param_count += 1

    if severity:
        conditions.append(f"severity = ${param_count}")
        params.append(severity)
        param_count += 1

    if status:
        conditions.append(f"status = ${param_count}")
        params.append(status)
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
        SELECT * FROM anomalies
        WHERE {where_clause}
        ORDER BY detected_at DESC
        LIMIT ${param_count} OFFSET ${param_count + 1}
    """
    params.extend([limit, offset])

    async with db.pool.acquire() as conn:
        rows = await conn.fetch(query, *params)
        return [dict(row) for row in rows]
