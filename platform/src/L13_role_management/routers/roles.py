"""
Role Management API Router for L13 Role Management Layer.

Provides REST endpoints for role CRUD operations, searching, dispatching,
and classification.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional, List
from uuid import UUID
import logging

from ..models import (
    Role,
    RoleCreate,
    RoleUpdate,
    RoleStatus,
    RoleType,
    RoleMatch,
    RoleContext,
    TaskRequirements,
    ClassificationResult,
    DispatchResult,
)
from ..services import (
    RoleRegistry,
    RoleDispatcher,
    RoleContextBuilder,
    ClassificationEngine,
)

router = APIRouter(prefix="/roles", tags=["roles"])
logger = logging.getLogger(__name__)

# Service instances (will be initialized via dependency injection)
_role_registry: Optional[RoleRegistry] = None
_role_dispatcher: Optional[RoleDispatcher] = None
_context_builder: Optional[RoleContextBuilder] = None
_classification_engine: Optional[ClassificationEngine] = None


def get_role_registry() -> RoleRegistry:
    """Dependency to get the role registry."""
    global _role_registry
    if _role_registry is None:
        _role_registry = RoleRegistry(use_memory_fallback=True)
    return _role_registry


def get_classification_engine() -> ClassificationEngine:
    """Dependency to get the classification engine."""
    global _classification_engine
    if _classification_engine is None:
        _classification_engine = ClassificationEngine()
    return _classification_engine


def get_context_builder() -> RoleContextBuilder:
    """Dependency to get the context builder."""
    global _context_builder
    if _context_builder is None:
        _context_builder = RoleContextBuilder()
    return _context_builder


def get_role_dispatcher(
    registry: RoleRegistry = Depends(get_role_registry),
    engine: ClassificationEngine = Depends(get_classification_engine),
    builder: RoleContextBuilder = Depends(get_context_builder),
) -> RoleDispatcher:
    """Dependency to get the role dispatcher."""
    global _role_dispatcher
    if _role_dispatcher is None:
        _role_dispatcher = RoleDispatcher(
            role_registry=registry,
            classification_engine=engine,
            context_builder=builder,
        )
    return _role_dispatcher


# =============================================================================
# Role CRUD Endpoints
# =============================================================================

@router.post("/", response_model=Role, status_code=201)
async def create_role(
    role_data: RoleCreate,
    registry: RoleRegistry = Depends(get_role_registry),
) -> Role:
    """
    Create a new role.

    Creates a role definition with the provided name, department, skills,
    and other configuration.
    """
    try:
        return await registry.register_role(role_data)
    except Exception as e:
        logger.error(f"Failed to create role: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to create role: {str(e)}")


@router.get("/", response_model=List[Role])
async def list_roles(
    status: Optional[RoleStatus] = None,
    role_type: Optional[RoleType] = None,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    registry: RoleRegistry = Depends(get_role_registry),
) -> List[Role]:
    """
    List roles with optional filters.

    Returns roles matching the specified status and/or role type.
    """
    return await registry.list_roles(
        status=status,
        role_type=role_type,
        limit=limit,
        offset=offset,
    )


@router.get("/by-department/{department}", response_model=List[Role])
async def list_roles_by_department(
    department: str,
    registry: RoleRegistry = Depends(get_role_registry),
) -> List[Role]:
    """
    List all roles in a specific department.

    Returns active roles belonging to the specified department.
    """
    return await registry.list_by_department(department)


@router.get("/search", response_model=List[RoleMatch])
async def search_roles(
    query: str = Query(..., min_length=1, description="Search query"),
    department: Optional[str] = None,
    role_type: Optional[RoleType] = None,
    tags: Optional[str] = Query(None, description="Comma-separated tags"),
    limit: int = Query(20, ge=1, le=100),
    registry: RoleRegistry = Depends(get_role_registry),
) -> List[RoleMatch]:
    """
    Search for roles matching a query.

    Returns roles with match scores based on name, skills, and keywords.
    """
    tag_list = tags.split(",") if tags else None
    return await registry.search_roles(
        query=query,
        department=department,
        role_type=role_type,
        tags=tag_list,
        limit=limit,
    )


@router.get("/statistics")
async def get_role_statistics(
    registry: RoleRegistry = Depends(get_role_registry),
):
    """
    Get role registry statistics.

    Returns counts and distributions of roles by department, type, and status.
    """
    return await registry.get_statistics()


@router.get("/{role_id}", response_model=Role)
async def get_role(
    role_id: UUID,
    registry: RoleRegistry = Depends(get_role_registry),
) -> Role:
    """
    Get a role by ID.

    Returns the complete role definition including skills and constraints.
    """
    role = await registry.get_role(role_id)
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
    return role


@router.get("/by-name/{name}", response_model=Role)
async def get_role_by_name(
    name: str,
    registry: RoleRegistry = Depends(get_role_registry),
) -> Role:
    """
    Get a role by name.

    Returns the role matching the specified name (case-insensitive).
    """
    role = await registry.get_role_by_name(name)
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
    return role


@router.patch("/{role_id}", response_model=Role)
async def update_role(
    role_id: UUID,
    role_data: RoleUpdate,
    registry: RoleRegistry = Depends(get_role_registry),
) -> Role:
    """
    Update a role.

    Updates the specified fields of the role definition.
    """
    try:
        role = await registry.update_role(role_id, role_data)
        if not role:
            raise HTTPException(status_code=404, detail="Role not found")
        return role
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update role {role_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to update role: {str(e)}")


@router.delete("/{role_id}", status_code=204)
async def delete_role(
    role_id: UUID,
    registry: RoleRegistry = Depends(get_role_registry),
):
    """
    Delete a role.

    Marks the role as deprecated rather than hard deleting.
    """
    deleted = await registry.delete_role(role_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Role not found")


# =============================================================================
# Dispatch and Classification Endpoints
# =============================================================================

@router.post("/dispatch", response_model=DispatchResult)
async def dispatch_task(
    task_id: str,
    requirements: TaskRequirements,
    preferred_role_id: Optional[UUID] = None,
    force_role_type: Optional[RoleType] = None,
    build_context: bool = True,
    dispatcher: RoleDispatcher = Depends(get_role_dispatcher),
) -> DispatchResult:
    """
    Dispatch a task to the best matching role.

    Analyzes the task requirements, classifies for human/AI routing,
    and assigns to the optimal role with assembled context.
    """
    try:
        return await dispatcher.dispatch_task(
            task_id=task_id,
            requirements=requirements,
            preferred_role_id=preferred_role_id,
            force_role_type=force_role_type,
            build_context=build_context,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to dispatch task {task_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Dispatch failed: {str(e)}")


@router.post("/classify", response_model=ClassificationResult)
async def classify_task(
    task_id: str,
    requirements: TaskRequirements,
    engine: ClassificationEngine = Depends(get_classification_engine),
) -> ClassificationResult:
    """
    Classify a task for human/AI routing.

    Analyzes the task to determine if it should be handled by
    humans, AI, or collaboratively.
    """
    return await engine.classify_task(
        task_id=task_id,
        requirements=requirements,
    )


@router.post("/find-matches", response_model=List[RoleMatch])
async def find_matching_roles(
    requirements: TaskRequirements,
    top_k: int = Query(3, ge=1, le=10),
    registry: RoleRegistry = Depends(get_role_registry),
) -> List[RoleMatch]:
    """
    Find roles matching task requirements.

    Returns the top-k roles best suited for the given task.
    """
    return await registry.dispatch_for_task(requirements, top_k=top_k)


# =============================================================================
# Context Building Endpoints
# =============================================================================

@router.post("/{role_id}/context", response_model=RoleContext)
async def build_role_context(
    role_id: UUID,
    requirements: Optional[TaskRequirements] = None,
    additional_context: Optional[str] = None,
    include_examples: bool = True,
    token_budget_override: Optional[int] = Query(None, ge=100, le=128000),
    registry: RoleRegistry = Depends(get_role_registry),
    builder: RoleContextBuilder = Depends(get_context_builder),
) -> RoleContext:
    """
    Build execution context for a role.

    Assembles a complete context including system prompt, skills,
    constraints, and examples within the token budget.
    """
    role = await registry.get_role(role_id)
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")

    return await builder.build_context(
        role=role,
        task_requirements=requirements,
        additional_context=additional_context,
        include_examples=include_examples,
        token_budget_override=token_budget_override,
    )


@router.post("/{role_id}/minimal-context", response_model=RoleContext)
async def build_minimal_context(
    role_id: UUID,
    registry: RoleRegistry = Depends(get_role_registry),
    builder: RoleContextBuilder = Depends(get_context_builder),
) -> RoleContext:
    """
    Build a minimal context for quick operations.

    Returns a lightweight context suitable for simple tasks.
    """
    role = await registry.get_role(role_id)
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")

    return await builder.build_minimal_context(role)


# =============================================================================
# Statistics and Monitoring Endpoints
# =============================================================================

@router.get("/dispatch/statistics")
async def get_dispatch_statistics(
    dispatcher: RoleDispatcher = Depends(get_role_dispatcher),
):
    """
    Get dispatch statistics.

    Returns metrics about task dispatching including counts by
    classification and role.
    """
    return await dispatcher.get_dispatch_statistics()


@router.get("/classification/statistics")
async def get_classification_statistics(
    engine: ClassificationEngine = Depends(get_classification_engine),
):
    """
    Get classification engine statistics.

    Returns configuration and metrics for the classification engine.
    """
    return engine.get_statistics()
