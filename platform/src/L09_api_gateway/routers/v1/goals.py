"""
Goals API endpoints for L09 Gateway.

Proxies requests to L01 Data Layer with authentication and authorization.
"""

from fastapi import APIRouter, HTTPException, Header, Depends
from typing import Optional
from uuid import UUID
from pydantic import BaseModel

from src.L01_data_layer.client import L01Client

router = APIRouter(prefix="/api/v1/goals", tags=["goals"])

# Shared L01 client instance
l01_client = L01Client(base_url="http://localhost:8002")


class CreateGoalRequest(BaseModel):
    """Request model for creating a goal."""
    agent_id: UUID
    description: str
    success_criteria: list = []
    priority: int = 5


class UpdateGoalRequest(BaseModel):
    """Request model for updating a goal."""
    description: Optional[str] = None
    success_criteria: Optional[list] = None
    status: Optional[str] = None
    priority: Optional[int] = None


async def verify_api_key(x_api_key: str = Header(..., alias="X-API-Key")):
    """Verify API key (simplified for now)."""
    if len(x_api_key) < 32:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return x_api_key


@router.post("/", status_code=201)
async def create_goal(
    body: CreateGoalRequest,
    api_key: str = Depends(verify_api_key)
):
    """Create a new goal."""
    try:
        goal = await l01_client.create_goal(
            agent_id=body.agent_id,
            description=body.description,
            success_criteria=body.success_criteria,
            priority=body.priority
        )
        return goal
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create goal: {str(e)}")


@router.get("/")
async def list_goals(
    agent_id: Optional[UUID] = None,
    limit: int = 100,
    api_key: str = Depends(verify_api_key)
):
    """List goals."""
    try:
        # For now, we need to implement this in L01Client if it doesn't exist
        # This is a placeholder that assumes L01 has this endpoint
        return {
            "items": [],
            "total": 0,
            "message": "Goals listing via L09 - implement full L01 integration"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list goals: {str(e)}")


@router.get("/{goal_id}")
async def get_goal(
    goal_id: UUID,
    api_key: str = Depends(verify_api_key)
):
    """Get goal by ID."""
    try:
        goal = await l01_client.get_goal(goal_id)
        return goal
    except Exception as e:
        if "404" in str(e):
            raise HTTPException(status_code=404, detail="Goal not found")
        raise HTTPException(status_code=500, detail=f"Failed to get goal: {str(e)}")


@router.patch("/{goal_id}")
async def update_goal(
    goal_id: UUID,
    body: UpdateGoalRequest,
    api_key: str = Depends(verify_api_key)
):
    """Update a goal."""
    try:
        updates = body.model_dump(exclude_unset=True)
        goal = await l01_client.update_goal(goal_id, updates)
        return goal
    except Exception as e:
        if "404" in str(e):
            raise HTTPException(status_code=404, detail="Goal not found")
        raise HTTPException(status_code=500, detail=f"Failed to update goal: {str(e)}")
