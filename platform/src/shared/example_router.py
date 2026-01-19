"""
Example Router with Standardized Error Handling

Demonstrates proper usage of error handling across different scenarios.
"""

import logging
from typing import List, Optional
from fastapi import APIRouter, Query, Path
from pydantic import BaseModel, Field

# Import shared error handling
from . import (
    NotFoundError,
    AlreadyExistsError,
    InvalidInputError,
    ValidationError,
    DatabaseError,
    AuthorizationError,
    ErrorContext,
    handle_database_error,
)


logger = logging.getLogger(__name__)


# Example models
class Agent(BaseModel):
    """Agent model."""
    id: str
    name: str
    type: str
    status: str = "active"


class AgentCreate(BaseModel):
    """Agent creation request."""
    name: str = Field(..., min_length=1, max_length=100)
    type: str = Field(..., pattern="^(planning|execution|evaluation)$")


class AgentUpdate(BaseModel):
    """Agent update request."""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    status: Optional[str] = Field(None, pattern="^(active|inactive|paused)$")


# Create router
router = APIRouter(prefix="/agents", tags=["agents"])


# Mock database (replace with actual database in production)
MOCK_DB = {}


@router.get("/", response_model=List[Agent])
async def list_agents(
    limit: int = Query(10, ge=1, le=100),
    offset: int = Query(0, ge=0),
) -> List[Agent]:
    """
    List all agents with pagination.

    Example of basic endpoint with validation.
    """
    logger.info(
        "Listing agents",
        extra={
            'event': 'list_agents',
            'limit': limit,
            'offset': offset,
        }
    )

    # Simulate database query
    agents = list(MOCK_DB.values())
    return agents[offset:offset + limit]


@router.get("/{agent_id}", response_model=Agent)
@handle_database_error("fetch agent")
async def get_agent(
    agent_id: str = Path(..., description="Agent ID"),
) -> Agent:
    """
    Get agent by ID.

    Example of NotFoundError usage.

    Raises:
        NotFoundError: If agent not found
    """
    logger.info(
        "Getting agent",
        extra={
            'event': 'get_agent',
            'agent_id': agent_id,
        }
    )

    # Simulate database query
    agent = MOCK_DB.get(agent_id)

    if not agent:
        # Automatically returns 404 with standardized error response
        raise NotFoundError("Agent", agent_id)

    return agent


@router.post("/", response_model=Agent, status_code=201)
async def create_agent(
    agent_data: AgentCreate,
) -> Agent:
    """
    Create new agent.

    Example of validation and AlreadyExistsError usage.

    Raises:
        AlreadyExistsError: If agent with same name exists
        ValidationError: If validation fails
    """
    logger.info(
        "Creating agent",
        extra={
            'event': 'create_agent',
            'agent_name': agent_data.name,
            'agent_type': agent_data.type,
        }
    )

    # Check if agent with same name exists
    for existing_agent in MOCK_DB.values():
        if existing_agent['name'] == agent_data.name:
            # Automatically returns 409 with standardized error response
            raise AlreadyExistsError("Agent", agent_data.name)

    # Custom validation example
    if agent_data.name.lower() == "system":
        # Returns 422 with validation error details
        raise InvalidInputError(
            field="name",
            message="Agent name 'system' is reserved",
            expected="non-reserved name",
        )

    # Create agent
    import uuid
    agent_id = str(uuid.uuid4())

    agent = Agent(
        id=agent_id,
        name=agent_data.name,
        type=agent_data.type,
    )

    # Save to database
    with ErrorContext("database", operation="insert agent"):
        # Any exception here automatically becomes DatabaseError
        MOCK_DB[agent_id] = agent.dict()

    logger.info(
        "Agent created successfully",
        extra={
            'event': 'agent_created',
            'agent_id': agent_id,
        }
    )

    return agent


@router.patch("/{agent_id}", response_model=Agent)
@handle_database_error("update agent")
async def update_agent(
    agent_id: str = Path(..., description="Agent ID"),
    agent_data: AgentUpdate = None,
) -> Agent:
    """
    Update agent.

    Example of partial update with validation.

    Raises:
        NotFoundError: If agent not found
        ValidationError: If update fails validation
    """
    logger.info(
        "Updating agent",
        extra={
            'event': 'update_agent',
            'agent_id': agent_id,
        }
    )

    # Get existing agent
    agent_dict = MOCK_DB.get(agent_id)
    if not agent_dict:
        raise NotFoundError("Agent", agent_id)

    agent = Agent(**agent_dict)

    # Apply updates
    if agent_data.name is not None:
        # Check for name conflicts
        for existing_id, existing_agent in MOCK_DB.items():
            if existing_id != agent_id and existing_agent['name'] == agent_data.name:
                raise AlreadyExistsError("Agent", agent_data.name)

        agent.name = agent_data.name

    if agent_data.status is not None:
        # Business logic validation
        if agent.status == "inactive" and agent_data.status == "active":
            # Example: Require authorization for reactivation
            # raise AuthorizationError(required_permission="agents:activate")
            pass

        agent.status = agent_data.status

    # Save changes
    MOCK_DB[agent_id] = agent.dict()

    logger.info(
        "Agent updated successfully",
        extra={
            'event': 'agent_updated',
            'agent_id': agent_id,
        }
    )

    return agent


@router.delete("/{agent_id}", status_code=204)
@handle_database_error("delete agent")
async def delete_agent(
    agent_id: str = Path(..., description="Agent ID"),
) -> None:
    """
    Delete agent.

    Example of delete operation with authorization.

    Raises:
        NotFoundError: If agent not found
        AuthorizationError: If insufficient permissions
    """
    logger.info(
        "Deleting agent",
        extra={
            'event': 'delete_agent',
            'agent_id': agent_id,
        }
    )

    # Get agent
    agent = MOCK_DB.get(agent_id)
    if not agent:
        raise NotFoundError("Agent", agent_id)

    # Example: Check permissions (in real app, check from auth context)
    # if not has_permission("agents:delete"):
    #     raise AuthorizationError(required_permission="agents:delete")

    # Delete agent
    del MOCK_DB[agent_id]

    logger.info(
        "Agent deleted successfully",
        extra={
            'event': 'agent_deleted',
            'agent_id': agent_id,
        }
    )


# Example: Custom business logic error
@router.post("/{agent_id}/execute", response_model=dict)
async def execute_agent(
    agent_id: str = Path(..., description="Agent ID"),
) -> dict:
    """
    Execute agent task.

    Example of business logic error handling.

    Raises:
        NotFoundError: If agent not found
        InvalidStateError: If agent not in valid state
    """
    logger.info(
        "Executing agent",
        extra={
            'event': 'execute_agent',
            'agent_id': agent_id,
        }
    )

    # Get agent
    agent_dict = MOCK_DB.get(agent_id)
    if not agent_dict:
        raise NotFoundError("Agent", agent_id)

    agent = Agent(**agent_dict)

    # Check if agent can be executed
    if agent.status != "active":
        from .errors import InvalidStateError
        raise InvalidStateError(
            message="Agent must be in 'active' state to execute",
            current_state=agent.status,
            required_state="active",
        )

    logger.info(
        "Agent execution started",
        extra={
            'event': 'agent_execution_started',
            'agent_id': agent_id,
        }
    )

    return {
        "status": "executing",
        "agent_id": agent_id,
        "message": "Agent execution started successfully",
    }
