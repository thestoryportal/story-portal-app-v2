"""
Tasks API endpoints for L09 Gateway.

Proxies requests to L01 Data Layer with authentication and authorization.
"""

import os
from fastapi import APIRouter, HTTPException, Header, Depends
from typing import Optional
from uuid import UUID
from pydantic import BaseModel

from shared.clients import L01Client

router = APIRouter(prefix="/api/v1/tasks", tags=["tasks"])

# Shared L01 client instance
l01_client = L01Client(
    base_url=os.getenv("L01_URL", "http://l01-data-layer:8001"),
    api_key=os.getenv("L01_DEFAULT_API_KEY", "dev_key_CHANGE_IN_PRODUCTION")
)


class CreateTaskRequest(BaseModel):
    """Request model for creating a task."""
    plan_id: UUID
    agent_id: UUID
    description: str
    task_type: Optional[str] = None
    input_data: dict = {}


class UpdateTaskRequest(BaseModel):
    """Request model for updating a task."""
    status: Optional[str] = None
    output_data: Optional[dict] = None


async def verify_api_key(x_api_key: str = Header(..., alias="X-API-Key")):
    """Verify API key (simplified for now)."""
    if len(x_api_key) < 32:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return x_api_key


@router.post("/", status_code=201)
async def create_task(
    body: CreateTaskRequest,
    api_key: str = Depends(verify_api_key)
):
    """Create a new task."""
    try:
        task = await l01_client.create_task(
            plan_id=body.plan_id,
            agent_id=body.agent_id,
            description=body.description,
            task_type=body.task_type,
            input_data=body.input_data
        )
        return task
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create task: {str(e)}")


@router.get("/{task_id}")
async def get_task(
    task_id: UUID,
    api_key: str = Depends(verify_api_key)
):
    """Get task by ID."""
    try:
        # This would need to be implemented in L01Client
        return {
            "message": "Task retrieval - implement full L01 integration"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get task: {str(e)}")


@router.patch("/{task_id}")
async def update_task(
    task_id: UUID,
    body: UpdateTaskRequest,
    api_key: str = Depends(verify_api_key)
):
    """Update a task."""
    try:
        updates = body.model_dump(exclude_unset=True)
        task = await l01_client.update_task(task_id, updates)
        return task
    except Exception as e:
        if "404" in str(e):
            raise HTTPException(status_code=404, detail="Task not found")
        raise HTTPException(status_code=500, detail=f"Failed to update task: {str(e)}")
