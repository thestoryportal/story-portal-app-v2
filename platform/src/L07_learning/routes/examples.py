"""
L07 Learning Layer - Example Routes

REST API endpoints for training example management.
"""

import logging
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from .datasets import get_examples


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/examples", tags=["examples"])


# =============================================================================
# Response Models
# =============================================================================

class ExampleResponse(BaseModel):
    """Training example response model."""
    example_id: str
    execution_id: str
    task_id: str
    source_type: str
    input_text: str
    output_text: str
    domain: str
    task_type: str
    quality_score: float
    confidence: float
    difficulty: float
    created_at: str

    model_config = {"from_attributes": True}


class ExampleListResponse(BaseModel):
    """Response for listing examples."""
    examples: List[ExampleResponse]
    total: int


# =============================================================================
# Endpoints
# =============================================================================

@router.get("", response_model=ExampleListResponse)
async def list_examples(
    domain: Optional[str] = Query(default=None, description="Filter by domain"),
    source_type: Optional[str] = Query(default=None, description="Filter by source type"),
    min_quality: Optional[float] = Query(default=None, ge=0, le=100, description="Minimum quality score"),
    max_quality: Optional[float] = Query(default=None, ge=0, le=100, description="Maximum quality score"),
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
):
    """
    List training examples with optional filtering.

    Args:
        domain: Filter by domain (e.g., "code_generation")
        source_type: Filter by source type (e.g., "execution_trace")
        min_quality: Minimum quality score filter
        max_quality: Maximum quality score filter
        limit: Maximum number of examples to return
        offset: Number of examples to skip

    Returns:
        List of examples
    """
    examples = get_examples()
    all_examples = list(examples.values())

    # Apply filters
    if domain:
        all_examples = [e for e in all_examples if e.domain == domain]

    if source_type:
        all_examples = [e for e in all_examples if e.source_type.value == source_type]

    if min_quality is not None:
        all_examples = [e for e in all_examples if e.quality_score >= min_quality]

    if max_quality is not None:
        all_examples = [e for e in all_examples if e.quality_score <= max_quality]

    # Sort by created_at descending
    all_examples.sort(key=lambda e: e.created_at, reverse=True)

    # Paginate
    paginated = all_examples[offset:offset + limit]

    return ExampleListResponse(
        examples=[
            ExampleResponse(
                example_id=ex.example_id,
                execution_id=ex.execution_id,
                task_id=ex.task_id,
                source_type=ex.source_type.value,
                input_text=ex.input_text[:500] if ex.input_text else "",
                output_text=ex.output_text[:500] if ex.output_text else "",
                domain=ex.domain,
                task_type=ex.task_type.value if hasattr(ex.task_type, 'value') else str(ex.task_type),
                quality_score=ex.quality_score,
                confidence=ex.confidence,
                difficulty=ex.difficulty,
                created_at=ex.created_at.isoformat(),
            )
            for ex in paginated
        ],
        total=len(all_examples),
    )


@router.get("/{example_id}", response_model=ExampleResponse)
async def get_example(example_id: str):
    """
    Get a training example by ID.

    Args:
        example_id: Example identifier

    Returns:
        Example details
    """
    examples = get_examples()
    example = examples.get(example_id)

    if not example:
        raise HTTPException(status_code=404, detail=f"Example {example_id} not found")

    return ExampleResponse(
        example_id=example.example_id,
        execution_id=example.execution_id,
        task_id=example.task_id,
        source_type=example.source_type.value,
        input_text=example.input_text,
        output_text=example.output_text,
        domain=example.domain,
        task_type=example.task_type.value if hasattr(example.task_type, 'value') else str(example.task_type),
        quality_score=example.quality_score,
        confidence=example.confidence,
        difficulty=example.difficulty,
        created_at=example.created_at.isoformat(),
    )


@router.delete("/{example_id}", status_code=204)
async def delete_example(example_id: str):
    """
    Delete a training example.

    Args:
        example_id: Example identifier
    """
    examples = get_examples()

    if example_id not in examples:
        raise HTTPException(status_code=404, detail=f"Example {example_id} not found")

    del examples[example_id]
    logger.info(f"Deleted example {example_id}")
