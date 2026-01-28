"""
L07 Learning Layer - Job Routes

REST API endpoints for training job management.
"""

import logging
from typing import List, Optional
from datetime import datetime
import uuid

from fastapi import APIRouter, HTTPException, Request, Query, BackgroundTasks
from pydantic import BaseModel, Field

from ..models.training_job import TrainingJob, JobStatus, JobType, JobConfig
from .datasets import get_datasets


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/jobs", tags=["jobs"])


# =============================================================================
# Request/Response Models
# =============================================================================

class CreateJobRequest(BaseModel):
    """Request to create a new training job."""
    dataset_id: str
    base_model_id: str = "gpt2"
    job_type: str = "sft"
    job_name: Optional[str] = None
    config: Optional[dict] = None


class JobResponse(BaseModel):
    """Training job response model."""
    job_id: str
    job_name: str
    job_type: str
    status: str
    status_message: str
    dataset_id: str
    base_model_id: str
    output_model_id: Optional[str]
    created_at: str
    started_at: Optional[str]
    completed_at: Optional[str]
    error_message: Optional[str]

    model_config = {"from_attributes": True}


class JobProgressResponse(BaseModel):
    """Job progress response model."""
    job_id: str
    status: str
    progress_percent: float
    current_epoch: int
    total_epochs: int
    current_step: int
    total_steps: int
    metrics: Optional[dict]


class JobListResponse(BaseModel):
    """Response for listing jobs."""
    jobs: List[JobResponse]
    total: int


# =============================================================================
# In-Memory Storage
# =============================================================================

_jobs: dict = {}


# =============================================================================
# Helper Functions
# =============================================================================

def _job_type_from_str(job_type: str) -> JobType:
    """Convert string to JobType."""
    mapping = {
        "sft": JobType.SFT,
        "supervised_fine_tuning": JobType.SFT,
        "rlhf": JobType.RLHF,
        "reinforcement_learning_human_feedback": JobType.RLHF,
        "distillation": JobType.DISTILLATION,
        "knowledge_distillation": JobType.DISTILLATION,
        "curriculum": JobType.CURRICULUM,
        "curriculum_learning": JobType.CURRICULUM,
    }
    return mapping.get(job_type.lower(), JobType.SFT)


async def _simulate_training(job_id: str):
    """Simulate training (for development)."""
    import asyncio

    job = _jobs.get(job_id)
    if not job:
        return

    # Update to training status
    job.update_status(JobStatus.TRAINING, "Training in progress")

    # Simulate epochs
    for epoch in range(job.config.num_epochs):
        await asyncio.sleep(0.1)  # Simulate work

        if job.status == JobStatus.CANCELLED:
            return

    # Complete job
    job.update_status(JobStatus.COMPLETED, "Training completed successfully")
    job.output_model_id = f"model-{job.job_id[:8]}"


# =============================================================================
# Endpoints
# =============================================================================

@router.post("", status_code=202, response_model=JobResponse)
async def create_job(
    request: CreateJobRequest,
    background_tasks: BackgroundTasks,
):
    """
    Create and start a new training job.

    Args:
        request: Job creation request

    Returns:
        Created job (accepted for processing)
    """
    logger.info(f"Creating training job for dataset: {request.dataset_id}")

    # Verify dataset exists
    datasets = get_datasets()
    if request.dataset_id not in datasets:
        raise HTTPException(
            status_code=404,
            detail=f"Dataset {request.dataset_id} not found"
        )

    # Create job
    job = TrainingJob(
        job_id=str(uuid.uuid4()),
        job_name=request.job_name or f"job-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}",
        job_type=_job_type_from_str(request.job_type),
        dataset_id=request.dataset_id,
        base_model_id=request.base_model_id,
        status=JobStatus.PENDING,
    )

    # Apply custom config if provided
    if request.config:
        for key, value in request.config.items():
            if hasattr(job.config, key):
                setattr(job.config, key, value)

    # Store job
    _jobs[job.job_id] = job

    # Start training in background
    job.update_status(JobStatus.INITIALIZING, "Initializing training")
    background_tasks.add_task(_simulate_training, job.job_id)

    logger.info(f"Created job {job.job_id}")

    return JobResponse(
        job_id=job.job_id,
        job_name=job.job_name,
        job_type=job.job_type.value,
        status=job.status.value,
        status_message=job.status_message,
        dataset_id=job.dataset_id,
        base_model_id=job.base_model_id,
        output_model_id=job.output_model_id,
        created_at=job.created_at.isoformat(),
        started_at=job.started_at.isoformat() if job.started_at else None,
        completed_at=job.completed_at.isoformat() if job.completed_at else None,
        error_message=job.error_message,
    )


@router.get("", response_model=JobListResponse)
async def list_jobs(
    status: Optional[str] = Query(default=None, description="Filter by status"),
    limit: int = Query(default=100, ge=1, le=1000),
    offset: int = Query(default=0, ge=0),
):
    """
    List all training jobs.

    Args:
        status: Filter by job status
        limit: Maximum number of jobs to return
        offset: Number of jobs to skip

    Returns:
        List of jobs
    """
    all_jobs = list(_jobs.values())

    # Filter by status
    if status:
        all_jobs = [j for j in all_jobs if j.status.value == status]

    # Sort by created_at descending
    all_jobs.sort(key=lambda j: j.created_at, reverse=True)

    # Paginate
    paginated = all_jobs[offset:offset + limit]

    return JobListResponse(
        jobs=[
            JobResponse(
                job_id=job.job_id,
                job_name=job.job_name,
                job_type=job.job_type.value,
                status=job.status.value,
                status_message=job.status_message,
                dataset_id=job.dataset_id,
                base_model_id=job.base_model_id,
                output_model_id=job.output_model_id,
                created_at=job.created_at.isoformat(),
                started_at=job.started_at.isoformat() if job.started_at else None,
                completed_at=job.completed_at.isoformat() if job.completed_at else None,
                error_message=job.error_message,
            )
            for job in paginated
        ],
        total=len(all_jobs),
    )


@router.get("/{job_id}", response_model=JobResponse)
async def get_job(job_id: str):
    """
    Get a job by ID.

    Args:
        job_id: Job identifier

    Returns:
        Job details
    """
    job = _jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    return JobResponse(
        job_id=job.job_id,
        job_name=job.job_name,
        job_type=job.job_type.value,
        status=job.status.value,
        status_message=job.status_message,
        dataset_id=job.dataset_id,
        base_model_id=job.base_model_id,
        output_model_id=job.output_model_id,
        created_at=job.created_at.isoformat(),
        started_at=job.started_at.isoformat() if job.started_at else None,
        completed_at=job.completed_at.isoformat() if job.completed_at else None,
        error_message=job.error_message,
    )


@router.get("/{job_id}/progress", response_model=JobProgressResponse)
async def get_job_progress(job_id: str):
    """
    Get job training progress.

    Args:
        job_id: Job identifier

    Returns:
        Job progress information
    """
    job = _jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    # Calculate progress
    if job.is_terminal():
        progress = 100.0
    elif job.status == JobStatus.PENDING:
        progress = 0.0
    elif job.status == JobStatus.INITIALIZING:
        progress = 5.0
    elif job.status == JobStatus.PREPARING_DATA:
        progress = 10.0
    elif job.status == JobStatus.TRAINING:
        # Estimate based on epochs
        if job.training_metrics:
            last_metric = job.training_metrics[-1]
            progress = 10 + (last_metric.epoch / job.config.num_epochs) * 80
        else:
            progress = 15.0
    elif job.status == JobStatus.VALIDATING:
        progress = 95.0
    else:
        progress = 0.0

    # Get latest metrics
    metrics = None
    if job.training_metrics:
        last = job.training_metrics[-1]
        metrics = {
            "train_loss": last.train_loss,
            "eval_loss": last.eval_loss,
            "learning_rate": last.learning_rate,
        }

    return JobProgressResponse(
        job_id=job.job_id,
        status=job.status.value,
        progress_percent=min(progress, 100.0),
        current_epoch=job.training_metrics[-1].epoch if job.training_metrics else 0,
        total_epochs=job.config.num_epochs,
        current_step=job.training_metrics[-1].step if job.training_metrics else 0,
        total_steps=job.config.max_steps or 0,
        metrics=metrics,
    )


@router.post("/{job_id}/cancel")
async def cancel_job(job_id: str):
    """
    Cancel a running training job.

    Args:
        job_id: Job identifier

    Returns:
        Cancellation status
    """
    job = _jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

    if job.is_terminal():
        raise HTTPException(
            status_code=409,
            detail=f"Job {job_id} is already in terminal state: {job.status.value}"
        )

    job.update_status(JobStatus.CANCELLED, "Cancelled by user")
    logger.info(f"Cancelled job {job_id}")

    return {"message": f"Job {job_id} cancelled", "status": job.status.value}


# Export storage for use in other routes
def get_jobs():
    """Get all jobs."""
    return _jobs
