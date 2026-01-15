"""Training example endpoints for L07 integration."""
from fastapi import APIRouter, Depends, HTTPException
from typing import Optional
from uuid import UUID
from ..models import TrainingExample, TrainingExampleCreate, TrainingExampleUpdate, ExampleSource
from ..services import TrainingExampleService
from ..database import db
from ..redis_client import redis_client

router = APIRouter(prefix="/training-examples", tags=["training_examples", "learning"])


def get_training_example_service():
    return TrainingExampleService(db.get_pool(), redis_client)


@router.post("/", response_model=TrainingExample, status_code=201)
async def create_training_example(
    example_data: TrainingExampleCreate,
    service: TrainingExampleService = Depends(get_training_example_service)
):
    """Create a new training example."""
    return await service.create_example(example_data)


@router.get("/", response_model=list[TrainingExample])
async def list_training_examples(
    agent_id: Optional[UUID] = None,
    domain: Optional[str] = None,
    min_quality: Optional[float] = None,
    source_type: Optional[ExampleSource] = None,
    limit: int = 100,
    offset: int = 0,
    service: TrainingExampleService = Depends(get_training_example_service)
):
    """List training examples with optional filters."""
    return await service.list_examples(
        agent_id=agent_id,
        domain=domain,
        min_quality=min_quality,
        source_type=source_type,
        limit=limit,
        offset=offset
    )


@router.get("/statistics")
async def get_statistics(
    service: TrainingExampleService = Depends(get_training_example_service)
):
    """Get training example statistics."""
    return await service.get_statistics()


@router.get("/{example_id}", response_model=TrainingExample)
async def get_training_example(
    example_id: UUID,
    service: TrainingExampleService = Depends(get_training_example_service)
):
    """Get training example by ID."""
    example = await service.get_example(example_id)
    if not example:
        raise HTTPException(status_code=404, detail="Training example not found")
    return example


@router.patch("/{example_id}", response_model=TrainingExample)
async def update_training_example(
    example_id: UUID,
    example_data: TrainingExampleUpdate,
    service: TrainingExampleService = Depends(get_training_example_service)
):
    """Update training example."""
    example = await service.update_example(example_id, example_data)
    if not example:
        raise HTTPException(status_code=404, detail="Training example not found")
    return example


@router.delete("/{example_id}", status_code=204)
async def delete_training_example(
    example_id: UUID,
    service: TrainingExampleService = Depends(get_training_example_service)
):
    """Delete training example."""
    deleted = await service.delete_example(example_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Training example not found")
