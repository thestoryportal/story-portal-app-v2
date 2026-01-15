"""User interactions router for L10 Human Interface integration."""

import json
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..database import db

router = APIRouter(prefix="/user-interactions", tags=["human-interface"])


class UserInteractionCreate(BaseModel):
    """User interaction creation model."""
    interaction_id: str
    timestamp: str
    interaction_type: str
    action: str
    user_id: Optional[str] = None
    target_type: Optional[str] = None
    target_id: Optional[str] = None
    parameters: Optional[dict] = None
    result: Optional[str] = None
    error_message: Optional[str] = None
    client_ip: Optional[str] = None
    user_agent: Optional[str] = None
    session_id: Optional[str] = None
    metadata: Optional[dict] = None


@router.post("/", status_code=201)
async def create_user_interaction(interaction_data: UserInteractionCreate):
    """Create a new user interaction record."""
    try:
        timestamp = datetime.fromisoformat(interaction_data.timestamp.replace('Z', '+00:00'))
        parameters_json = json.dumps(interaction_data.parameters or {})
        metadata_json = json.dumps(interaction_data.metadata or {})

        query = """
            INSERT INTO user_interactions (
                interaction_id, timestamp, user_id, interaction_type, target_type,
                target_id, action, parameters, result, error_message,
                client_ip, user_agent, session_id, metadata
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14)
            RETURNING id, interaction_id, timestamp, interaction_type, action, created_at
        """

        async with db.pool.acquire() as conn:
            record = await conn.fetchrow(
                query,
                interaction_data.interaction_id,
                timestamp,
                interaction_data.user_id,
                interaction_data.interaction_type,
                interaction_data.target_type,
                interaction_data.target_id,
                interaction_data.action,
                parameters_json,
                interaction_data.result,
                interaction_data.error_message,
                interaction_data.client_ip,
                interaction_data.user_agent,
                interaction_data.session_id,
                metadata_json,
            )

            return dict(record)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create user interaction: {str(e)}")


@router.get("/{interaction_id}")
async def get_user_interaction(interaction_id: str):
    """Get user interaction by interaction_id."""
    try:
        query = "SELECT * FROM user_interactions WHERE interaction_id = $1"
        async with db.pool.acquire() as conn:
            record = await conn.fetchrow(query, interaction_id)

            if not record:
                raise HTTPException(status_code=404, detail="User interaction not found")

            return dict(record)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/")
async def list_user_interactions(
    user_id: Optional[str] = None,
    interaction_type: Optional[str] = None,
    session_id: Optional[str] = None,
    limit: int = 100,
    offset: int = 0
):
    """List user interactions with filters."""
    try:
        conditions = []
        params = []
        param_index = 1

        if user_id:
            conditions.append(f"user_id = ${param_index}")
            params.append(user_id)
            param_index += 1

        if interaction_type:
            conditions.append(f"interaction_type = ${param_index}")
            params.append(interaction_type)
            param_index += 1

        if session_id:
            conditions.append(f"session_id = ${param_index}")
            params.append(session_id)
            param_index += 1

        where_clause = " AND ".join(conditions) if conditions else "TRUE"

        query = f"""
            SELECT * FROM user_interactions
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
