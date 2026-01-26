"""Agent endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from typing import Optional
from uuid import UUID
import logging

from ..models import Agent, AgentCreate, AgentUpdate, AgentStatus
from ..services import AgentRegistry
from ..database import db
from ..redis_client import redis_client

router = APIRouter(prefix="/agents", tags=["agents"])
logger = logging.getLogger(__name__)

def get_agent_registry():
    return AgentRegistry(db.get_pool(), redis_client)

@router.post("/", response_model=Agent, status_code=201)
async def create_agent(agent_data: AgentCreate, registry: AgentRegistry = Depends(get_agent_registry)):
    return await registry.create_agent(agent_data)

@router.get("/", response_model=list[Agent])
async def list_agents(
    status: Optional[AgentStatus] = None,
    limit: int = 100,
    offset: int = 0,
    registry: AgentRegistry = Depends(get_agent_registry)
):
    return await registry.list_agents(status, limit, offset)

@router.get("/{agent_id}", response_model=Agent)
async def get_agent(agent_id: UUID, registry: AgentRegistry = Depends(get_agent_registry)):
    try:
        agent = await registry.get_agent(agent_id)
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")
        return agent
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get agent {agent_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.patch("/{agent_id}", response_model=Agent)
async def update_agent(agent_id: UUID, agent_data: dict, registry: AgentRegistry = Depends(get_agent_registry)):
    """
    Update agent with flexible dict input.

    This endpoint accepts a generic dict and validates only known fields to avoid
    strict Pydantic validation errors during load testing and development.
    """
    try:
        # Validate and extract only known fields
        allowed_fields = {
            "name", "agent_type", "status", "configuration",
            "metadata", "resource_limits"
        }
        updates = {k: v for k, v in agent_data.items() if k in allowed_fields}

        if not updates:
            raise HTTPException(status_code=400, detail="No valid fields to update")

        # Convert dict to AgentUpdate model for type safety
        agent_update = AgentUpdate(**updates)

        agent = await registry.update_agent(agent_id, agent_update)
        if not agent:
            raise HTTPException(status_code=404, detail="Agent not found")
        return agent
    except HTTPException:
        raise
    except ValueError as e:
        # Pydantic validation error
        raise HTTPException(status_code=422, detail=f"Validation error: {str(e)}")
    except Exception as e:
        logger.error(f"Failed to update agent {agent_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@router.delete("/{agent_id}", status_code=204)
async def delete_agent(agent_id: UUID, registry: AgentRegistry = Depends(get_agent_registry)):
    deleted = await registry.delete_agent(agent_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Agent not found")
