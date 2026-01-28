"""
L07 Learning Layer - Dataset Routes

REST API endpoints for dataset management.
"""

import logging
from typing import List, Optional
from datetime import datetime
import uuid

from fastapi import APIRouter, HTTPException, Request, Query
from pydantic import BaseModel, Field

from ..models.dataset import Dataset, DatasetStatistics
from ..models.training_example import TrainingExample, ExampleSource, TaskType


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/datasets", tags=["datasets"])


# =============================================================================
# Request/Response Models
# =============================================================================

class ExampleInput(BaseModel):
    """Example input for dataset creation."""
    input_text: str
    output_text: str
    domain: str = "general"
    quality_score: float = Field(default=80.0, ge=0, le=100)
    confidence: float = Field(default=0.8, ge=0, le=1)


class CreateDatasetRequest(BaseModel):
    """Request to create a new dataset."""
    name: str
    description: str = ""
    examples: Optional[List[ExampleInput]] = None
    tags: Optional[List[str]] = None
    split_ratios: Optional[dict] = None


class DatasetResponse(BaseModel):
    """Dataset response model."""
    dataset_id: str
    name: str
    version: str
    description: str
    total_examples: int
    splits: dict
    created_at: str
    updated_at: str

    model_config = {"from_attributes": True}


class DatasetListResponse(BaseModel):
    """Response for listing datasets."""
    datasets: List[DatasetResponse]
    total: int


# =============================================================================
# In-Memory Storage (for initial implementation)
# =============================================================================

# Simple in-memory storage - will be replaced with L01 integration
_datasets: dict = {}
_examples: dict = {}


# =============================================================================
# Endpoints
# =============================================================================

@router.post("", status_code=201, response_model=DatasetResponse)
async def create_dataset(request: CreateDatasetRequest, req: Request):
    """
    Create a new dataset.

    Args:
        request: Dataset creation request

    Returns:
        Created dataset
    """
    logger.info(f"Creating dataset: {request.name}")

    # Create dataset
    dataset = Dataset(
        dataset_id=str(uuid.uuid4()),
        name=request.name,
        description=request.description,
        tags=request.tags or [],
    )

    if request.split_ratios:
        dataset.split_ratios = request.split_ratios

    # Process examples if provided
    if request.examples:
        for i, ex_input in enumerate(request.examples):
            example = TrainingExample(
                example_id=str(uuid.uuid4()),
                execution_id=f"api-{dataset.dataset_id}",
                task_id=f"task-{i}",
                source_type=ExampleSource.HUMAN_ANNOTATED,
                input_text=ex_input.input_text,
                output_text=ex_input.output_text,
                domain=ex_input.domain,
                quality_score=ex_input.quality_score,
                confidence=ex_input.confidence,
                task_type=TaskType.SINGLE_STEP,
            )
            _examples[example.example_id] = example
            dataset.example_ids.append(example.example_id)

        # Create splits
        total = len(dataset.example_ids)
        train_end = int(total * dataset.split_ratios.get("train", 0.8))
        val_end = train_end + int(total * dataset.split_ratios.get("validation", 0.1))

        dataset.splits = {
            "train": dataset.example_ids[:train_end],
            "validation": dataset.example_ids[train_end:val_end],
            "test": dataset.example_ids[val_end:],
        }

    # Store dataset
    _datasets[dataset.dataset_id] = dataset

    logger.info(f"Created dataset {dataset.dataset_id} with {len(dataset.example_ids)} examples")

    return DatasetResponse(
        dataset_id=dataset.dataset_id,
        name=dataset.name,
        version=dataset.version,
        description=dataset.description,
        total_examples=len(dataset.example_ids),
        splits={k: len(v) for k, v in dataset.splits.items()},
        created_at=dataset.created_at.isoformat(),
        updated_at=dataset.updated_at.isoformat(),
    )


@router.get("", response_model=DatasetListResponse)
async def list_datasets(
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
):
    """
    List all datasets.

    Args:
        limit: Maximum number of datasets to return
        offset: Number of datasets to skip

    Returns:
        List of datasets
    """
    all_datasets = list(_datasets.values())
    paginated = all_datasets[offset:offset + limit]

    return DatasetListResponse(
        datasets=[
            DatasetResponse(
                dataset_id=ds.dataset_id,
                name=ds.name,
                version=ds.version,
                description=ds.description,
                total_examples=len(ds.example_ids),
                splits={k: len(v) for k, v in ds.splits.items()},
                created_at=ds.created_at.isoformat(),
                updated_at=ds.updated_at.isoformat(),
            )
            for ds in paginated
        ],
        total=len(all_datasets),
    )


@router.get("/{dataset_id}", response_model=DatasetResponse)
async def get_dataset(dataset_id: str):
    """
    Get a dataset by ID.

    Args:
        dataset_id: Dataset identifier

    Returns:
        Dataset details
    """
    dataset = _datasets.get(dataset_id)
    if not dataset:
        raise HTTPException(status_code=404, detail=f"Dataset {dataset_id} not found")

    return DatasetResponse(
        dataset_id=dataset.dataset_id,
        name=dataset.name,
        version=dataset.version,
        description=dataset.description,
        total_examples=len(dataset.example_ids),
        splits={k: len(v) for k, v in dataset.splits.items()},
        created_at=dataset.created_at.isoformat(),
        updated_at=dataset.updated_at.isoformat(),
    )


@router.delete("/{dataset_id}", status_code=204)
async def delete_dataset(dataset_id: str):
    """
    Delete a dataset.

    Args:
        dataset_id: Dataset identifier
    """
    if dataset_id not in _datasets:
        raise HTTPException(status_code=404, detail=f"Dataset {dataset_id} not found")

    del _datasets[dataset_id]
    logger.info(f"Deleted dataset {dataset_id}")


# Export storage for use in other routes
def get_datasets():
    """Get all datasets."""
    return _datasets


def get_examples():
    """Get all examples."""
    return _examples
