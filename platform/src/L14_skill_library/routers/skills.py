"""
L14 Skill Library - Skills Router

FastAPI router for skill CRUD operations and management.
"""

import logging
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, Depends, Query, Body

from ..models import (
    Skill,
    SkillCreate,
    SkillUpdate,
    SkillStatus,
    SkillPriority,
    SkillCategory,
    SkillValidationResult,
    SkillGenerationRequest,
    SkillGenerationResponse,
    SkillOptimizationRequest,
    SkillOptimizationResult,
)
from ..services import SkillStore, SkillGenerator, SkillValidator, SkillOptimizer

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/skills", tags=["skills"])

# Service instances (will be initialized in main.py)
_skill_store: Optional[SkillStore] = None
_skill_generator: Optional[SkillGenerator] = None
_skill_validator: Optional[SkillValidator] = None
_skill_optimizer: Optional[SkillOptimizer] = None


def get_skill_store() -> SkillStore:
    """Get skill store instance."""
    global _skill_store
    if _skill_store is None:
        _skill_store = SkillStore()
    return _skill_store


def get_skill_generator() -> SkillGenerator:
    """Get skill generator instance."""
    global _skill_generator
    if _skill_generator is None:
        _skill_generator = SkillGenerator()
    return _skill_generator


def get_skill_validator() -> SkillValidator:
    """Get skill validator instance."""
    global _skill_validator
    if _skill_validator is None:
        _skill_validator = SkillValidator()
    return _skill_validator


def get_skill_optimizer() -> SkillOptimizer:
    """Get skill optimizer instance."""
    global _skill_optimizer
    if _skill_optimizer is None:
        _skill_optimizer = SkillOptimizer(get_skill_store())
    return _skill_optimizer


def init_services(
    skill_store: SkillStore,
    skill_generator: SkillGenerator,
    skill_validator: SkillValidator,
    skill_optimizer: SkillOptimizer,
):
    """Initialize service instances."""
    global _skill_store, _skill_generator, _skill_validator, _skill_optimizer
    _skill_store = skill_store
    _skill_generator = skill_generator
    _skill_validator = skill_validator
    _skill_optimizer = skill_optimizer


# =============================================================================
# CRUD Endpoints
# =============================================================================

@router.post("/", response_model=Skill, status_code=201)
async def create_skill(
    skill_data: SkillCreate,
    store: SkillStore = Depends(get_skill_store),
) -> Skill:
    """
    Create a new skill.

    Creates a skill from the provided definition data.
    """
    try:
        return await store.create(skill_data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to create skill: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create skill: {str(e)}")


@router.get("/", response_model=List[Skill])
async def list_skills(
    status: Optional[SkillStatus] = Query(None, description="Filter by status"),
    category: Optional[SkillCategory] = Query(None, description="Filter by category"),
    priority: Optional[SkillPriority] = Query(None, description="Filter by priority"),
    agent_id: Optional[UUID] = Query(None, description="Filter by agent ID"),
    tags: Optional[str] = Query(None, description="Comma-separated tags to filter by"),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    store: SkillStore = Depends(get_skill_store),
) -> List[Skill]:
    """
    List skills with optional filtering.

    Supports filtering by status, category, priority, agent, and tags.
    """
    tag_list = tags.split(",") if tags else None
    return await store.list(
        status=status,
        category=category,
        priority=priority,
        agent_id=agent_id,
        tags=tag_list,
        limit=limit,
        offset=offset,
    )


@router.get("/{skill_id}", response_model=Skill)
async def get_skill(
    skill_id: UUID,
    store: SkillStore = Depends(get_skill_store),
) -> Skill:
    """
    Get a skill by ID.
    """
    skill = await store.get(skill_id)
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")
    return skill


@router.get("/by-name/{name}", response_model=Skill)
async def get_skill_by_name(
    name: str,
    store: SkillStore = Depends(get_skill_store),
) -> Skill:
    """
    Get a skill by name.
    """
    skill = await store.get_by_name(name)
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")
    return skill


@router.patch("/{skill_id}", response_model=Skill)
async def update_skill(
    skill_id: UUID,
    update_data: SkillUpdate,
    store: SkillStore = Depends(get_skill_store),
) -> Skill:
    """
    Update a skill.

    Allows partial updates of skill fields.
    """
    try:
        skill = await store.update(skill_id, update_data)
        if not skill:
            raise HTTPException(status_code=404, detail="Skill not found")
        return skill
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to update skill: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update skill: {str(e)}")


@router.delete("/{skill_id}", status_code=204)
async def delete_skill(
    skill_id: UUID,
    store: SkillStore = Depends(get_skill_store),
):
    """
    Delete a skill.
    """
    deleted = await store.delete(skill_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Skill not found")


# =============================================================================
# Status Management Endpoints
# =============================================================================

@router.post("/{skill_id}/activate", response_model=Skill)
async def activate_skill(
    skill_id: UUID,
    store: SkillStore = Depends(get_skill_store),
) -> Skill:
    """
    Activate a skill.

    Changes skill status from draft to active.
    """
    skill = await store.activate(skill_id)
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")
    return skill


@router.post("/{skill_id}/deprecate", response_model=Skill)
async def deprecate_skill(
    skill_id: UUID,
    store: SkillStore = Depends(get_skill_store),
) -> Skill:
    """
    Deprecate a skill.

    Marks a skill as deprecated but still accessible.
    """
    skill = await store.deprecate(skill_id)
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")
    return skill


# =============================================================================
# Agent Assignment Endpoints
# =============================================================================

@router.post("/{skill_id}/assign/{agent_id}", response_model=Skill)
async def assign_skill_to_agent(
    skill_id: UUID,
    agent_id: UUID,
    store: SkillStore = Depends(get_skill_store),
) -> Skill:
    """
    Assign a skill to an agent.
    """
    skill = await store.assign_to_agent(skill_id, agent_id)
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")
    return skill


@router.get("/agent/{agent_id}", response_model=List[Skill])
async def get_agent_skills(
    agent_id: UUID,
    active_only: bool = Query(True, description="Only return active skills"),
    store: SkillStore = Depends(get_skill_store),
) -> List[Skill]:
    """
    Get all skills assigned to an agent.
    """
    return await store.get_agent_skills(agent_id, active_only=active_only)


# =============================================================================
# Validation Endpoints
# =============================================================================

@router.post("/{skill_id}/validate", response_model=SkillValidationResult)
async def validate_skill(
    skill_id: UUID,
    store: SkillStore = Depends(get_skill_store),
    validator: SkillValidator = Depends(get_skill_validator),
) -> SkillValidationResult:
    """
    Validate a skill.

    Checks the skill against the schema and returns validation results.
    """
    skill = await store.get(skill_id)
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")

    return await validator.validate(skill)


@router.post("/validate/yaml", response_model=SkillValidationResult)
async def validate_yaml(
    yaml_content: str = Body(..., media_type="text/plain"),
    validator: SkillValidator = Depends(get_skill_validator),
) -> SkillValidationResult:
    """
    Validate skill YAML content.

    Validates raw YAML content against the skill schema.
    """
    return await validator.validate_yaml(yaml_content)


# =============================================================================
# Generation Endpoints
# =============================================================================

@router.post("/generate", response_model=SkillGenerationResponse)
async def generate_skill(
    request: SkillGenerationRequest,
    generator: SkillGenerator = Depends(get_skill_generator),
    store: SkillStore = Depends(get_skill_store),
    validator: SkillValidator = Depends(get_skill_validator),
) -> SkillGenerationResponse:
    """
    Generate a skill from role responsibilities.

    Uses LLM to generate a complete skill file from the provided
    role description and responsibilities.
    """
    response = await generator.generate(request)

    if response.success and response.skill:
        # Validate the generated skill
        validation = await validator.validate(response.skill)
        response.validation_result = validation

        # Store the skill if valid
        if validation.is_valid:
            try:
                # Create the skill in the store
                skill_data = SkillCreate(
                    name=response.skill.name,
                    role_title=response.skill.definition.role.title,
                    role_description=response.skill.definition.role.description,
                    expertise_areas=response.skill.definition.role.expertise_areas,
                    primary_responsibilities=response.skill.definition.responsibilities.primary,
                    secondary_responsibilities=response.skill.definition.responsibilities.secondary,
                    required_tools=response.skill.definition.tools.required,
                    optional_tools=response.skill.definition.tools.optional,
                    tags=response.skill.definition.metadata.tags,
                    priority=response.skill.definition.metadata.priority,
                    category=response.skill.definition.metadata.category,
                    token_budget=response.skill.definition.constraints.token_budget,
                )
                stored_skill = await store.create(skill_data)
                response.skill = stored_skill
            except Exception as e:
                logger.warning(f"Failed to store generated skill: {e}")

    return response


@router.post("/generate/template/{template_name}", response_model=SkillGenerationResponse)
async def generate_skill_from_template(
    template_name: str,
    customizations: dict = Body(default={}),
    generator: SkillGenerator = Depends(get_skill_generator),
) -> SkillGenerationResponse:
    """
    Generate a skill from a predefined template.

    Available templates: developer, reviewer, analyst
    """
    return await generator.generate_from_template(template_name, customizations)


# =============================================================================
# Optimization Endpoints
# =============================================================================

@router.post("/optimize", response_model=SkillOptimizationResult)
async def optimize_skills(
    request: SkillOptimizationRequest,
    optimizer: SkillOptimizer = Depends(get_skill_optimizer),
) -> SkillOptimizationResult:
    """
    Optimize skills for loading.

    Applies optimization strategy to reduce token usage
    or prioritize skill loading.
    """
    return await optimizer.optimize(request)


@router.post("/loading-order", response_model=List[Skill])
async def get_loading_order(
    skill_ids: List[UUID] = Body(...),
    context: Optional[str] = Body(None),
    store: SkillStore = Depends(get_skill_store),
    optimizer: SkillOptimizer = Depends(get_skill_optimizer),
) -> List[Skill]:
    """
    Get optimal loading order for skills.

    Returns skills in the optimal order for loading based on
    priority and optional context relevance.
    """
    skills = []
    for skill_id in skill_ids:
        skill = await store.get(skill_id)
        if skill:
            skills.append(skill)

    return await optimizer.get_loading_order(skills, context)


@router.post("/estimate-tokens")
async def estimate_total_tokens(
    skill_ids: List[UUID] = Body(...),
    store: SkillStore = Depends(get_skill_store),
    optimizer: SkillOptimizer = Depends(get_skill_optimizer),
) -> dict:
    """
    Estimate total token count for a set of skills.
    """
    skills = []
    for skill_id in skill_ids:
        skill = await store.get(skill_id)
        if skill:
            skills.append(skill)

    total = await optimizer.estimate_total_tokens(skills)
    return {
        "total_tokens": total,
        "skill_count": len(skills),
    }


# =============================================================================
# Statistics Endpoint
# =============================================================================

@router.get("/stats/summary")
async def get_stats(
    store: SkillStore = Depends(get_skill_store),
) -> dict:
    """
    Get skill library statistics.

    Returns summary of skills by status, category, and priority.
    """
    return await store.get_stats()
