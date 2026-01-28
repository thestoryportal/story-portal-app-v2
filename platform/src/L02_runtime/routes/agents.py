"""
L02 Agent Runtime - Agent HTTP API Routes

Provides HTTP endpoints for agent lifecycle management.
These endpoints expose the AgentRuntime operations via REST API.
"""

import logging
from typing import Optional
from datetime import datetime

from fastapi import APIRouter, HTTPException, Request

from ..dtos import (
    SpawnRequestDTO,
    SpawnResponseDTO,
    TerminateRequestDTO,
    SuspendRequestDTO,
    SuspendResponseDTO,
    ResumeRequestDTO,
    ResumeResponseDTO,
    AgentStateResponseDTO,
    ErrorResponseDTO,
)
from ..models import (
    AgentConfig,
    TrustLevel,
    ResourceLimits,
    ToolDefinition,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/agents", tags=["agents"])


# ============================================================================
# Helper Functions
# ============================================================================

def dto_to_agent_config(dto: SpawnRequestDTO) -> AgentConfig:
    """Convert HTTP DTO to internal AgentConfig"""
    # Parse trust level
    trust_level_map = {
        "trusted": TrustLevel.TRUSTED,
        "standard": TrustLevel.STANDARD,
        "untrusted": TrustLevel.UNTRUSTED,
        "confidential": TrustLevel.CONFIDENTIAL,
    }
    trust_level = trust_level_map.get(dto.trust_level.lower(), TrustLevel.STANDARD)

    # Parse resource limits
    resource_limits = ResourceLimits()
    if dto.resource_limits:
        resource_limits = ResourceLimits(
            cpu=dto.resource_limits.cpu,
            memory=dto.resource_limits.memory,
            tokens_per_hour=dto.resource_limits.tokens_per_hour,
        )

    # Parse tools
    tools = [
        ToolDefinition(
            name=t.name,
            description=t.description,
            parameters=t.parameters,
        )
        for t in dto.tools
    ]

    return AgentConfig(
        agent_id=dto.agent_id,
        trust_level=trust_level,
        resource_limits=resource_limits,
        tools=tools,
        environment=dto.environment,
        initial_context=dto.initial_context,
        recovery_checkpoint_id=dto.recovery_checkpoint_id,
    )


# ============================================================================
# Endpoints
# ============================================================================

@router.post(
    "/spawn",
    response_model=SpawnResponseDTO,
    responses={
        400: {"model": ErrorResponseDTO, "description": "Invalid request"},
        500: {"model": ErrorResponseDTO, "description": "Internal error"},
        503: {"model": ErrorResponseDTO, "description": "Service unavailable"},
    }
)
async def spawn_agent(
    request_dto: SpawnRequestDTO,
    request: Request
) -> SpawnResponseDTO:
    """
    Spawn a new agent instance.

    Creates a new agent with the specified configuration and returns
    the spawn result with agent identifiers and initial state.
    """
    runtime = getattr(request.app.state, "runtime", None)
    if not runtime:
        raise HTTPException(
            status_code=503,
            detail=ErrorResponseDTO(
                error_code="E2000",
                message="AgentRuntime not initialized"
            ).model_dump()
        )

    try:
        logger.info(f"Spawn request for agent {request_dto.agent_id}")

        # Convert DTO to internal config
        config = dto_to_agent_config(request_dto)

        # Spawn agent
        result = await runtime.spawn(config, request_dto.initial_context)

        return SpawnResponseDTO(
            agent_id=result.agent_id,
            session_id=result.session_id,
            state=result.state.value,
            sandbox_type=result.sandbox_type,
            container_id=result.container_id,
            pod_name=result.pod_name,
            created_at=result.created_at,
        )

    except Exception as e:
        logger.exception(f"Failed to spawn agent {request_dto.agent_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=ErrorResponseDTO(
                error_code="E2001",
                message=f"Failed to spawn agent: {str(e)}"
            ).model_dump()
        )


@router.post(
    "/{agent_id}/terminate",
    responses={
        200: {"description": "Agent terminated successfully"},
        404: {"model": ErrorResponseDTO, "description": "Agent not found"},
        500: {"model": ErrorResponseDTO, "description": "Internal error"},
    }
)
async def terminate_agent(
    agent_id: str,
    request_dto: TerminateRequestDTO,
    request: Request
):
    """
    Terminate an agent instance.

    Gracefully terminates the agent or force kills if force=True.
    """
    runtime = getattr(request.app.state, "runtime", None)
    if not runtime:
        raise HTTPException(
            status_code=503,
            detail=ErrorResponseDTO(
                error_code="E2000",
                message="AgentRuntime not initialized"
            ).model_dump()
        )

    try:
        logger.info(
            f"Terminate request for agent {agent_id}: "
            f"reason={request_dto.reason}, force={request_dto.force}"
        )

        await runtime.terminate(
            agent_id=agent_id,
            reason=request_dto.reason,
            force=request_dto.force
        )

        return {"status": "terminated", "agent_id": agent_id}

    except Exception as e:
        error_msg = str(e)
        if "not found" in error_msg.lower():
            raise HTTPException(
                status_code=404,
                detail=ErrorResponseDTO(
                    error_code="E2002",
                    message=f"Agent {agent_id} not found"
                ).model_dump()
            )
        logger.exception(f"Failed to terminate agent {agent_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=ErrorResponseDTO(
                error_code="E2003",
                message=f"Failed to terminate agent: {error_msg}"
            ).model_dump()
        )


@router.post(
    "/{agent_id}/suspend",
    response_model=SuspendResponseDTO,
    responses={
        404: {"model": ErrorResponseDTO, "description": "Agent not found"},
        500: {"model": ErrorResponseDTO, "description": "Internal error"},
    }
)
async def suspend_agent(
    agent_id: str,
    request_dto: SuspendRequestDTO,
    request: Request
) -> SuspendResponseDTO:
    """
    Suspend an agent and optionally create a checkpoint.

    Returns the checkpoint ID if checkpoint=True.
    """
    runtime = getattr(request.app.state, "runtime", None)
    if not runtime:
        raise HTTPException(
            status_code=503,
            detail=ErrorResponseDTO(
                error_code="E2000",
                message="AgentRuntime not initialized"
            ).model_dump()
        )

    try:
        logger.info(
            f"Suspend request for agent {agent_id}: checkpoint={request_dto.checkpoint}"
        )

        checkpoint_id = await runtime.suspend(
            agent_id=agent_id,
            checkpoint=request_dto.checkpoint
        )

        # Get current state
        state = await runtime.get_state(agent_id)

        return SuspendResponseDTO(
            agent_id=agent_id,
            checkpoint_id=checkpoint_id if request_dto.checkpoint else None,
            state=state.value,
        )

    except Exception as e:
        error_msg = str(e)
        if "not found" in error_msg.lower():
            raise HTTPException(
                status_code=404,
                detail=ErrorResponseDTO(
                    error_code="E2002",
                    message=f"Agent {agent_id} not found"
                ).model_dump()
            )
        logger.exception(f"Failed to suspend agent {agent_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=ErrorResponseDTO(
                error_code="E2004",
                message=f"Failed to suspend agent: {error_msg}"
            ).model_dump()
        )


@router.post(
    "/{agent_id}/resume",
    response_model=ResumeResponseDTO,
    responses={
        404: {"model": ErrorResponseDTO, "description": "Agent not found"},
        500: {"model": ErrorResponseDTO, "description": "Internal error"},
    }
)
async def resume_agent(
    agent_id: str,
    request_dto: ResumeRequestDTO,
    request: Request
) -> ResumeResponseDTO:
    """
    Resume a suspended agent.

    Optionally restores from a specific checkpoint.
    """
    runtime = getattr(request.app.state, "runtime", None)
    if not runtime:
        raise HTTPException(
            status_code=503,
            detail=ErrorResponseDTO(
                error_code="E2000",
                message="AgentRuntime not initialized"
            ).model_dump()
        )

    try:
        logger.info(
            f"Resume request for agent {agent_id}: "
            f"checkpoint_id={request_dto.checkpoint_id}"
        )

        state = await runtime.resume(
            agent_id=agent_id,
            checkpoint_id=request_dto.checkpoint_id
        )

        return ResumeResponseDTO(
            agent_id=agent_id,
            state=state.value,
            restored_from_checkpoint=request_dto.checkpoint_id is not None,
        )

    except Exception as e:
        error_msg = str(e)
        if "not found" in error_msg.lower():
            raise HTTPException(
                status_code=404,
                detail=ErrorResponseDTO(
                    error_code="E2002",
                    message=f"Agent {agent_id} not found"
                ).model_dump()
            )
        logger.exception(f"Failed to resume agent {agent_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=ErrorResponseDTO(
                error_code="E2005",
                message=f"Failed to resume agent: {error_msg}"
            ).model_dump()
        )


@router.get(
    "/{agent_id}/state",
    response_model=AgentStateResponseDTO,
    responses={
        404: {"model": ErrorResponseDTO, "description": "Agent not found"},
        500: {"model": ErrorResponseDTO, "description": "Internal error"},
    }
)
async def get_agent_state(
    agent_id: str,
    request: Request
) -> AgentStateResponseDTO:
    """
    Get current agent state and metadata.
    """
    runtime = getattr(request.app.state, "runtime", None)
    if not runtime:
        raise HTTPException(
            status_code=503,
            detail=ErrorResponseDTO(
                error_code="E2000",
                message="AgentRuntime not initialized"
            ).model_dump()
        )

    try:
        # Get agent instance from lifecycle manager
        instance = await runtime.lifecycle_manager.get_instance(agent_id)
        if not instance:
            raise HTTPException(
                status_code=404,
                detail=ErrorResponseDTO(
                    error_code="E2002",
                    message=f"Agent {agent_id} not found"
                ).model_dump()
            )

        return AgentStateResponseDTO(
            agent_id=instance.agent_id,
            state=instance.state.value,
            session_id=instance.session_id,
            sandbox_type=instance.sandbox.runtime_class.value,
            resource_usage=instance.resource_usage.to_dict(),
            created_at=instance.created_at,
            updated_at=instance.updated_at,
            terminated_at=instance.terminated_at,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to get state for agent {agent_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=ErrorResponseDTO(
                error_code="E2006",
                message=f"Failed to get agent state: {str(e)}"
            ).model_dump()
        )
