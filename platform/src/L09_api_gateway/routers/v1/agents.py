"""
Agents API endpoints for L09 Gateway.

Proxies requests to L01 Data Layer with authentication and authorization.
"""

from fastapi import APIRouter, HTTPException, Header, Depends
from typing import Optional, List
from uuid import UUID
from pydantic import BaseModel

from shared.clients import L01Client

router = APIRouter(prefix="/api/v1/agents", tags=["agents"])

# Shared L01 client instance
l01_client = L01Client(base_url="http://localhost:8002")


class CreateAgentRequest(BaseModel):
    """Request model for creating an agent."""
    name: str
    agent_type: str = "general"
    configuration: dict = {}
    metadata: dict = {}


class UpdateAgentRequest(BaseModel):
    """Request model for updating an agent."""
    name: Optional[str] = None
    agent_type: Optional[str] = None
    status: Optional[str] = None
    configuration: Optional[dict] = None
    metadata: Optional[dict] = None


async def verify_api_key(x_api_key: str = Header(..., alias="X-API-Key")):
    """Verify API key (simplified for now)."""
    # TODO: Implement proper API key validation
    if len(x_api_key) < 32:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return x_api_key


@router.post("/", status_code=201)
async def create_agent(
    body: CreateAgentRequest,
    api_key: str = Depends(verify_api_key)
):
    """Create a new agent."""
    try:
        agent = await l01_client.create_agent(
            name=body.name,
            agent_type=body.agent_type,
            configuration=body.configuration,
            metadata=body.metadata
        )
        return agent
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create agent: {str(e)}")


@router.get("/")
async def list_agents(
    status: Optional[str] = None,
    limit: int = 100,
    api_key: str = Depends(verify_api_key)
):
    """List all agents."""
    try:
        agents = await l01_client.list_agents(status=status, limit=limit)
        return {
            "items": agents,
            "total": len(agents),
            "limit": limit
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list agents: {str(e)}")


@router.get("/{agent_id}")
async def get_agent(
    agent_id: UUID,
    api_key: str = Depends(verify_api_key)
):
    """Get agent by ID."""
    try:
        agent = await l01_client.get_agent(agent_id)
        return agent
    except Exception as e:
        if "404" in str(e):
            raise HTTPException(status_code=404, detail="Agent not found")
        raise HTTPException(status_code=500, detail=f"Failed to get agent: {str(e)}")


@router.patch("/{agent_id}")
async def update_agent(
    agent_id: UUID,
    body: UpdateAgentRequest,
    api_key: str = Depends(verify_api_key)
):
    """Update an agent."""
    try:
        updates = body.model_dump(exclude_unset=True)
        agent = await l01_client.update_agent(agent_id, updates)
        return agent
    except Exception as e:
        if "404" in str(e):
            raise HTTPException(status_code=404, detail="Agent not found")
        raise HTTPException(status_code=500, detail=f"Failed to update agent: {str(e)}")


@router.delete("/{agent_id}", status_code=204)
async def delete_agent(
    agent_id: UUID,
    api_key: str = Depends(verify_api_key)
):
    """Delete an agent."""
    try:
        deleted = await l01_client.delete_agent(agent_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Agent not found")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete agent: {str(e)}")
