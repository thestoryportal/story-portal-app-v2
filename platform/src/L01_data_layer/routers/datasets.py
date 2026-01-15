"""Dataset endpoints for L07 integration."""
from fastapi import APIRouter, Depends, HTTPException
from typing import Optional, List
from uuid import UUID
from ..models import Dataset, DatasetCreate, DatasetUpdate, DatasetSplit
from ..services import DatasetService
from ..database import db
from ..redis_client import redis_client

router = APIRouter(prefix="/datasets", tags=["datasets", "learning"])


def get_dataset_service():
    return DatasetService(db.get_pool(), redis_client)


@router.post("/", response_model=Dataset, status_code=201)
async def create_dataset(
    dataset_data: DatasetCreate,
    service: DatasetService = Depends(get_dataset_service)
):
    """Create a new dataset."""
    return await service.create_dataset(dataset_data)


@router.get("/", response_model=list[Dataset])
async def list_datasets(
    name_filter: Optional[str] = None,
    tag_filter: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    service: DatasetService = Depends(get_dataset_service)
):
    """List datasets with optional filters."""
    return await service.list_datasets(
        name_filter=name_filter,
        tag_filter=tag_filter,
        limit=limit,
        offset=offset
    )


@router.get("/statistics")
async def get_statistics(
    service: DatasetService = Depends(get_dataset_service)
):
    """Get dataset service statistics."""
    return await service.get_statistics()


@router.get("/{dataset_id}", response_model=Dataset)
async def get_dataset(
    dataset_id: UUID,
    service: DatasetService = Depends(get_dataset_service)
):
    """Get dataset by ID."""
    dataset = await service.get_dataset(dataset_id)
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
    return dataset


@router.patch("/{dataset_id}", response_model=Dataset)
async def update_dataset(
    dataset_id: UUID,
    dataset_data: DatasetUpdate,
    service: DatasetService = Depends(get_dataset_service)
):
    """Update dataset metadata."""
    dataset = await service.update_dataset(dataset_id, dataset_data)
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
    return dataset


@router.delete("/{dataset_id}", status_code=204)
async def delete_dataset(
    dataset_id: UUID,
    service: DatasetService = Depends(get_dataset_service)
):
    """Delete dataset."""
    deleted = await service.delete_dataset(dataset_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Dataset not found")


@router.post("/{dataset_id}/examples/{example_id}")
async def add_example_to_dataset(
    dataset_id: UUID,
    example_id: UUID,
    split: DatasetSplit,
    service: DatasetService = Depends(get_dataset_service)
):
    """Add training example to dataset with split assignment."""
    return await service.add_example_to_dataset(dataset_id, example_id, split)


@router.delete("/{dataset_id}/examples/{example_id}", status_code=204)
async def remove_example_from_dataset(
    dataset_id: UUID,
    example_id: UUID,
    service: DatasetService = Depends(get_dataset_service)
):
    """Remove training example from dataset."""
    removed = await service.remove_example_from_dataset(dataset_id, example_id)
    if not removed:
        raise HTTPException(status_code=404, detail="Link not found")


@router.get("/{dataset_id}/examples", response_model=List[UUID])
async def get_dataset_examples(
    dataset_id: UUID,
    split: Optional[DatasetSplit] = None,
    service: DatasetService = Depends(get_dataset_service)
):
    """Get example IDs for a dataset, optionally filtered by split."""
    return await service.get_dataset_examples(dataset_id, split)


@router.get("/{dataset_id}/split-counts")
async def get_dataset_split_counts(
    dataset_id: UUID,
    service: DatasetService = Depends(get_dataset_service)
):
    """Get count of examples in each split."""
    return await service.get_dataset_split_counts(dataset_id)
