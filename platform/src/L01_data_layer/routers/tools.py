"""Tool endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from typing import Optional
from uuid import UUID

from ..models import Tool, ToolCreate, ToolUpdate, ToolExecution, ToolExecutionCreate, ToolExecutionUpdate
from ..services import ToolRegistry
from ..database import db
from ..redis_client import redis_client

router = APIRouter(prefix="/tools", tags=["tools"])

def get_tool_registry():
    return ToolRegistry(db.get_pool(), redis_client)

@router.post("/", response_model=Tool, status_code=201)
async def register_tool(tool_data: ToolCreate, registry: ToolRegistry = Depends(get_tool_registry)):
    return await registry.register_tool(tool_data)

@router.get("/", response_model=list[Tool])
async def list_tools(enabled_only: bool = False, limit: int = 100, registry: ToolRegistry = Depends(get_tool_registry)):
    return await registry.list_tools(enabled_only, limit)

@router.get("/{tool_id}", response_model=Tool)
async def get_tool(tool_id: UUID, registry: ToolRegistry = Depends(get_tool_registry)):
    tool = await registry.get_tool(tool_id)
    if not tool:
        raise HTTPException(status_code=404, detail="Tool not found")
    return tool

@router.patch("/{tool_id}", response_model=Tool)
async def update_tool(tool_id: UUID, tool_data: ToolUpdate, registry: ToolRegistry = Depends(get_tool_registry)):
    tool = await registry.update_tool(tool_id, tool_data)
    if not tool:
        raise HTTPException(status_code=404, detail="Tool not found")
    return tool

@router.post("/tool-executions", response_model=ToolExecution, status_code=201)
async def record_tool_execution(exec_data: ToolExecutionCreate, registry: ToolRegistry = Depends(get_tool_registry)):
    return await registry.record_execution(exec_data)

@router.get("/tool-executions/{execution_id}", response_model=ToolExecution)
async def get_tool_execution(execution_id: UUID, registry: ToolRegistry = Depends(get_tool_registry)):
    execution = await registry.get_execution(execution_id)
    if not execution:
        raise HTTPException(status_code=404, detail="Tool execution not found")
    return execution

@router.get("/executions/by-invocation/{invocation_id}", response_model=ToolExecution)
async def get_execution_by_invocation(invocation_id: UUID, registry: ToolRegistry = Depends(get_tool_registry)):
    """Get tool execution by invocation ID."""
    execution = await registry.get_execution_by_invocation(invocation_id)
    if not execution:
        raise HTTPException(status_code=404, detail="Tool execution not found")
    return execution

@router.patch("/executions/{invocation_id}", response_model=ToolExecution)
async def update_execution(
    invocation_id: UUID,
    update_data: ToolExecutionUpdate,
    registry: ToolRegistry = Depends(get_tool_registry)
):
    """Update tool execution by invocation ID."""
    execution = await registry.update_execution(invocation_id, update_data)
    if not execution:
        raise HTTPException(status_code=404, detail="Tool execution not found")
    return execution

@router.get("/executions", response_model=list[ToolExecution])
async def list_executions(
    agent_id: Optional[UUID] = None,
    tool_name: Optional[str] = None,
    session_id: Optional[str] = None,
    tenant_id: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    registry: ToolRegistry = Depends(get_tool_registry)
):
    """List tool executions with filters."""
    return await registry.list_executions(
        agent_id=agent_id,
        tool_name=tool_name,
        session_id=session_id,
        tenant_id=tenant_id,
        status=status,
        limit=limit,
        offset=offset
    )
