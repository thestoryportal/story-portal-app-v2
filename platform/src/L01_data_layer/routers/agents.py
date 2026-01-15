"""Agent endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from typing import Optional
from uuid import UUID

from ..models import Agent, AgentCreate, AgentUpdate, AgentStatus
from ..services import AgentRegistry
from ..database import db
from ..redis_client import redis_client

router = APIRouter(prefix="/agents", tags=["agents"])

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
    agent = await registry.get_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent

@router.patch("/{agent_id}", response_model=Agent)
async def update_agent(agent_id: UUID, agent_data: AgentUpdate, registry: AgentRegistry = Depends(get_agent_registry)):
    agent = await registry.update_agent(agent_id, agent_data)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent

@router.delete("/{agent_id}", status_code=204)
async def delete_agent(agent_id: UUID, registry: AgentRegistry = Depends(get_agent_registry)):
    deleted = await registry.delete_agent(agent_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Agent not found")
