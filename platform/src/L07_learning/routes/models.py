"""
L07 Learning Layer - Model Routes

REST API endpoints for model artifact management.
"""

import logging
from typing import List, Optional
from datetime import datetime
import uuid

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from ..models.model_artifact import ModelArtifact, ModelType, ModelStage, ModelLineage, ModelMetrics


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/models", tags=["models"])


# =============================================================================
# Request/Response Models
# =============================================================================

class RegisterModelRequest(BaseModel):
    """Request to register a new model."""
    name: str
    model_type: str = "fine_tuned"
    artifact_path: str
    description: str = ""
    tags: Optional[List[str]] = None
    training_job_id: Optional[str] = None
    dataset_id: Optional[str] = None
    base_model_id: Optional[str] = None


class TransitionStageRequest(BaseModel):
    """Request to transition model stage."""
    stage: str
    notes: str = ""
    transitioned_by: str = "api"


class ModelResponse(BaseModel):
    """Model artifact response model."""
    model_id: str
    name: str
    version: str
    model_type: str
    stage: str
    artifact_path: str
    description: str
    tags: List[str]
    created_at: str
    updated_at: str
    deployed_at: Optional[str]

    model_config = {"from_attributes": True}


class ModelListResponse(BaseModel):
    """Response for listing models."""
    models: List[ModelResponse]
    total: int


# =============================================================================
# In-Memory Storage
# =============================================================================

_models: dict = {}


# =============================================================================
# Helper Functions
# =============================================================================

def _model_type_from_str(model_type: str) -> ModelType:
    """Convert string to ModelType."""
    mapping = {
        "base": ModelType.BASE,
        "fine_tuned": ModelType.FINE_TUNED,
        "lora_adapter": ModelType.LORA_ADAPTER,
        "distilled": ModelType.DISTILLED,
        "reward_model": ModelType.REWARD_MODEL,
    }
    return mapping.get(model_type.lower(), ModelType.FINE_TUNED)


def _model_stage_from_str(stage: str) -> ModelStage:
    """Convert string to ModelStage."""
    mapping = {
        "development": ModelStage.DEVELOPMENT,
        "staging": ModelStage.STAGING,
        "production": ModelStage.PRODUCTION,
        "archived": ModelStage.ARCHIVED,
        "quarantined": ModelStage.QUARANTINED,
    }
    return mapping.get(stage.lower(), ModelStage.DEVELOPMENT)


# =============================================================================
# Endpoints
# =============================================================================

@router.post("", status_code=201, response_model=ModelResponse)
async def register_model(request: RegisterModelRequest):
    """
    Register a new model artifact.

    Args:
        request: Model registration request

    Returns:
        Registered model
    """
    logger.info(f"Registering model: {request.name}")

    # Create model artifact
    model = ModelArtifact(
        model_id=str(uuid.uuid4()),
        name=request.name,
        model_type=_model_type_from_str(request.model_type),
        artifact_path=request.artifact_path,
        description=request.description,
        tags=request.tags or [],
    )

    # Set lineage if provided
    if request.training_job_id or request.dataset_id or request.base_model_id:
        model.lineage = ModelLineage(
            training_job_id=request.training_job_id,
            dataset_id=request.dataset_id,
            base_model_id=request.base_model_id,
        )

    # Store model
    _models[model.model_id] = model

    logger.info(f"Registered model {model.model_id}")

    return ModelResponse(
        model_id=model.model_id,
        name=model.name,
        version=model.version,
        model_type=model.model_type.value,
        stage=model.stage.value,
        artifact_path=model.artifact_path,
        description=model.description,
        tags=model.tags,
        created_at=model.created_at.isoformat(),
        updated_at=model.updated_at.isoformat(),
        deployed_at=model.deployed_at.isoformat() if model.deployed_at else None,
    )


@router.get("", response_model=ModelListResponse)
async def list_models(
    stage: Optional[str] = Query(default=None, description="Filter by stage"),
    model_type: Optional[str] = Query(default=None, description="Filter by type"),
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
):
    """
    List all models.

    Args:
        stage: Filter by deployment stage
        model_type: Filter by model type
        limit: Maximum number of models to return
        offset: Number of models to skip

    Returns:
        List of models
    """
    all_models = list(_models.values())

    # Filter by stage
    if stage:
        target_stage = _model_stage_from_str(stage)
        all_models = [m for m in all_models if m.stage == target_stage]

    # Filter by type
    if model_type:
        target_type = _model_type_from_str(model_type)
        all_models = [m for m in all_models if m.model_type == target_type]

    # Sort by created_at descending
    all_models.sort(key=lambda m: m.created_at, reverse=True)

    # Paginate
    paginated = all_models[offset:offset + limit]

    return ModelListResponse(
        models=[
            ModelResponse(
                model_id=model.model_id,
                name=model.name,
                version=model.version,
                model_type=model.model_type.value,
                stage=model.stage.value,
                artifact_path=model.artifact_path,
                description=model.description,
                tags=model.tags,
                created_at=model.created_at.isoformat(),
                updated_at=model.updated_at.isoformat(),
                deployed_at=model.deployed_at.isoformat() if model.deployed_at else None,
            )
            for model in paginated
        ],
        total=len(all_models),
    )


@router.get("/{model_id}", response_model=ModelResponse)
async def get_model(model_id: str):
    """
    Get a model by ID.

    Args:
        model_id: Model identifier

    Returns:
        Model details
    """
    model = _models.get(model_id)
    if not model:
        raise HTTPException(status_code=404, detail=f"Model {model_id} not found")

    return ModelResponse(
        model_id=model.model_id,
        name=model.name,
        version=model.version,
        model_type=model.model_type.value,
        stage=model.stage.value,
        artifact_path=model.artifact_path,
        description=model.description,
        tags=model.tags,
        created_at=model.created_at.isoformat(),
        updated_at=model.updated_at.isoformat(),
        deployed_at=model.deployed_at.isoformat() if model.deployed_at else None,
    )


@router.patch("/{model_id}/stage", response_model=ModelResponse)
async def transition_stage(model_id: str, request: TransitionStageRequest):
    """
    Transition model to a new deployment stage.

    Args:
        model_id: Model identifier
        request: Stage transition request

    Returns:
        Updated model
    """
    model = _models.get(model_id)
    if not model:
        raise HTTPException(status_code=404, detail=f"Model {model_id} not found")

    target_stage = _model_stage_from_str(request.stage)

    # Check if transition is allowed
    can_transition, reason = model.can_transition_to(target_stage)
    if not can_transition:
        raise HTTPException(status_code=400, detail=reason)

    # Perform transition
    model.transition_stage(
        new_stage=target_stage,
        transitioned_by=request.transitioned_by,
        notes=request.notes,
    )

    logger.info(f"Transitioned model {model_id} to {target_stage.value}")

    return ModelResponse(
        model_id=model.model_id,
        name=model.name,
        version=model.version,
        model_type=model.model_type.value,
        stage=model.stage.value,
        artifact_path=model.artifact_path,
        description=model.description,
        tags=model.tags,
        created_at=model.created_at.isoformat(),
        updated_at=model.updated_at.isoformat(),
        deployed_at=model.deployed_at.isoformat() if model.deployed_at else None,
    )


@router.delete("/{model_id}", status_code=204)
async def delete_model(model_id: str):
    """
    Delete a model (moves to archived stage).

    Args:
        model_id: Model identifier
    """
    model = _models.get(model_id)
    if not model:
        raise HTTPException(status_code=404, detail=f"Model {model_id} not found")

    # Archive instead of delete
    if model.stage != ModelStage.ARCHIVED:
        can_archive, reason = model.can_transition_to(ModelStage.ARCHIVED)
        if can_archive:
            model.transition_stage(
                new_stage=ModelStage.ARCHIVED,
                transitioned_by="api",
                notes="Deleted via API",
            )

    del _models[model_id]
    logger.info(f"Deleted model {model_id}")


# Export storage for use in other routes
def get_models():
    """Get all models."""
    return _models
