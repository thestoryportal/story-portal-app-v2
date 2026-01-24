"""L07 Learning Layer - Fine-Tuning Engine Service.

Orchestrates supervised fine-tuning with LoRA. Uses simulation for local development.
Includes checkpoint management, training progress tracking, and recovery support.
"""

import asyncio
import logging
import time
import os
import json
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
from dataclasses import dataclass, field, asdict
import random
import math

from ..models.training_job import (
    TrainingJob,
    JobStatus,
    JobType,
    JobConfig,
    TrainingMetrics,
    ValidationMetrics
)
from ..models.model_artifact import (
    ModelArtifact,
    ModelType,
    ModelStage,
    ModelLineage,
    ModelMetrics
)
from ..models.error_codes import LearningErrorCode, TrainingError

logger = logging.getLogger(__name__)


@dataclass
class TrainingCheckpoint:
    """Checkpoint during training."""
    checkpoint_id: str
    job_id: str
    epoch: int
    step: int
    train_loss: float
    eval_loss: Optional[float]
    created_at: str
    checkpoint_path: str
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TrainingProgress:
    """Real-time training progress."""
    job_id: str
    status: str
    current_epoch: int
    total_epochs: int
    current_step: int
    steps_per_epoch: int
    train_loss: float
    eval_loss: Optional[float]
    learning_rate: float
    elapsed_seconds: float
    estimated_remaining_seconds: float
    checkpoints_saved: int
    gpu_utilization_percent: float
    throughput_samples_per_second: float


class FineTuningEngine:
    """Supervised fine-tuning engine with LoRA adapters.

    For local development, implements simulated training to test pipeline flow
    without requiring GPU resources. Production would use HuggingFace + PyTorch.

    Features:
    - Checkpoint management during training
    - Real-time progress tracking
    - Training recovery from checkpoints
    - Configurable evaluation intervals
    """

    def __init__(
        self,
        model_registry=None,
        dataset_curator=None,
        simulate_training: bool = True,
        checkpoint_dir: str = "/tmp/l07_checkpoints",
        checkpoint_interval_epochs: int = 1,
        evaluation_interval_steps: int = 100
    ):
        """Initialize Fine-Tuning Engine.

        Args:
            model_registry: Model registry service
            dataset_curator: Dataset curator service
            simulate_training: Use simulation instead of actual training
            checkpoint_dir: Directory for checkpoints
            checkpoint_interval_epochs: Epochs between checkpoints
            evaluation_interval_steps: Steps between evaluations
        """
        self.model_registry = model_registry
        self.dataset_curator = dataset_curator
        self.simulate_training = simulate_training
        self.checkpoint_dir = checkpoint_dir
        self.checkpoint_interval_epochs = checkpoint_interval_epochs
        self.evaluation_interval_steps = evaluation_interval_steps

        self.active_jobs: Dict[str, TrainingJob] = {}
        self._checkpoints: Dict[str, List[TrainingCheckpoint]] = {}
        self._progress: Dict[str, TrainingProgress] = {}
        self._job_tasks: Dict[str, asyncio.Task] = {}

        # Ensure checkpoint directory exists
        os.makedirs(checkpoint_dir, exist_ok=True)

        logger.info(
            f"Initialized FineTuningEngine "
            f"(simulation={'ON' if simulate_training else 'OFF'}, "
            f"checkpoint_interval={checkpoint_interval_epochs} epochs)"
        )

    async def start_training(
        self,
        dataset_id: str,
        base_model_id: str,
        config: Optional[JobConfig] = None
    ) -> TrainingJob:
        """Start supervised fine-tuning job.

        Args:
            dataset_id: Training dataset identifier
            base_model_id: Base model to fine-tune
            config: Training configuration

        Returns:
            Training job

        Raises:
            TrainingError: If job fails to start
        """
        if config is None:
            config = JobConfig()

        logger.info(
            f"Starting training job: dataset={dataset_id}, "
            f"base_model={base_model_id}"
        )

        # Validate dataset exists
        if self.dataset_curator:
            dataset = await self.dataset_curator.get_dataset(dataset_id)
            if not dataset:
                raise TrainingError(
                    LearningErrorCode.E7905,
                    f"Dataset not found: {dataset_id}"
                )
            logger.info(f"Using dataset with {len(dataset.example_ids)} examples")

        # Create training job
        job = TrainingJob(
            job_name=f"sft_{dataset_id}_{int(time.time())}",
            job_type=JobType.SFT,
            config=config,
            dataset_id=dataset_id,
            base_model_id=base_model_id
        )

        # Update status to initializing
        job.update_status(JobStatus.INITIALIZING, "Acquiring resources")

        # Store job
        self.active_jobs[job.job_id] = job
        self._checkpoints[job.job_id] = []

        # Start training asynchronously and track task
        task = asyncio.create_task(self._execute_training(job))
        self._job_tasks[job.job_id] = task

        logger.info(f"Started training job {job.job_id}")

        return job

    async def _execute_training(self, job: TrainingJob) -> None:
        """Execute training job (simulated or real).

        Args:
            job: Training job to execute
        """
        try:
            if self.simulate_training:
                await self._simulate_training_loop(job)
            else:
                await self._execute_real_training(job)

        except Exception as e:
            logger.error(f"Training job {job.job_id} failed: {e}")
            job.update_status(JobStatus.FAILED, str(e))
            job.error_code = LearningErrorCode.E7906.name
            job.error_message = str(e)

    async def _simulate_training_loop(self, job: TrainingJob) -> None:
        """Simulate training loop for local development.

        Includes checkpoint management and real-time progress updates.

        Args:
            job: Training job
        """
        logger.info(f"Simulating training for job {job.job_id}")
        start_time = time.time()

        # Preparation phase
        job.update_status(JobStatus.PREPARING_DATA, "Loading dataset")
        await asyncio.sleep(0.5)

        # Training phase
        job.update_status(JobStatus.TRAINING, "Training model")

        num_epochs = job.config.num_epochs
        steps_per_epoch = 100  # Simulated

        # Simulate training with decreasing loss
        initial_loss = 2.5
        target_loss = 0.3
        eval_loss = None

        for epoch in range(num_epochs):
            logger.info(f"Job {job.job_id}: Epoch {epoch + 1}/{num_epochs}")

            for step in range(steps_per_epoch):
                # Simulate training step
                await asyncio.sleep(0.01)  # Small delay for realism

                # Calculate decreasing loss with some noise
                progress = (epoch * steps_per_epoch + step) / (num_epochs * steps_per_epoch)
                base_loss = initial_loss - (initial_loss - target_loss) * progress
                noise = random.gauss(0, 0.05)
                train_loss = max(0.1, base_loss + noise)
                current_lr = job.config.learning_rate * (1 - progress * 0.5)
                gpu_util = random.uniform(70, 95)
                throughput = random.uniform(50, 100)

                # Create training metric
                metric = TrainingMetrics(
                    epoch=epoch + 1,
                    step=step + 1,
                    train_loss=train_loss,
                    learning_rate=current_lr,
                    grad_norm=random.uniform(0.5, 1.5),
                    gpu_memory_mb=random.uniform(2000, 4000),
                    gpu_utilization_percent=gpu_util,
                    throughput_samples_per_second=throughput
                )

                job.add_training_metric(metric)

                # Update progress
                elapsed = time.time() - start_time
                total_steps = num_epochs * steps_per_epoch
                current_total_step = epoch * steps_per_epoch + step
                estimated_total = (elapsed / max(1, current_total_step)) * total_steps
                remaining = max(0, estimated_total - elapsed)

                self._progress[job.job_id] = TrainingProgress(
                    job_id=job.job_id,
                    status=job.status.value if hasattr(job.status, 'value') else str(job.status),
                    current_epoch=epoch + 1,
                    total_epochs=num_epochs,
                    current_step=step + 1,
                    steps_per_epoch=steps_per_epoch,
                    train_loss=train_loss,
                    eval_loss=eval_loss,
                    learning_rate=current_lr,
                    elapsed_seconds=elapsed,
                    estimated_remaining_seconds=remaining,
                    checkpoints_saved=len(self._checkpoints.get(job.job_id, [])),
                    gpu_utilization_percent=gpu_util,
                    throughput_samples_per_second=throughput
                )

                # Periodic evaluation
                if step > 0 and step % self.evaluation_interval_steps == 0:
                    eval_loss = train_loss * random.uniform(1.0, 1.1)

            # End of epoch evaluation
            eval_loss = train_loss * random.uniform(1.0, 1.1)
            logger.info(
                f"Job {job.job_id}: Epoch {epoch + 1} complete - "
                f"train_loss={train_loss:.4f}, eval_loss={eval_loss:.4f}"
            )

            # Add eval metric
            eval_metric = TrainingMetrics(
                epoch=epoch + 1,
                step=steps_per_epoch,
                train_loss=train_loss,
                eval_loss=eval_loss,
                learning_rate=current_lr
            )
            job.add_training_metric(eval_metric)

            # Save checkpoint at interval
            if (epoch + 1) % self.checkpoint_interval_epochs == 0:
                await self._save_checkpoint(
                    job=job,
                    epoch=epoch + 1,
                    step=steps_per_epoch,
                    train_loss=train_loss,
                    eval_loss=eval_loss
                )

        # Validation phase
        job.update_status(JobStatus.VALIDATING, "Running validation")
        await asyncio.sleep(0.5)

        # Create validation metrics
        job.validation_metrics = ValidationMetrics(
            accuracy=random.uniform(0.85, 0.95),
            eval_loss=target_loss,
            bleu_score=random.uniform(0.75, 0.85),
            latency_p50_ms=random.uniform(2.0, 3.0),
            latency_p95_ms=random.uniform(4.0, 6.0),
            latency_p99_ms=random.uniform(7.0, 10.0),
            regression_tests_passed=98,
            regression_tests_failed=2,
            regression_tests_total=100
        )
        job.final_loss = target_loss

        # Create model artifact
        output_model_id = await self._create_model_artifact(job)
        job.output_model_id = output_model_id

        # Complete job
        job.update_status(JobStatus.COMPLETED, "Training completed successfully")

        logger.info(
            f"Job {job.job_id} completed successfully - "
            f"final_loss={job.final_loss:.4f}, "
            f"accuracy={job.validation_metrics.accuracy:.4f}"
        )

    async def _execute_real_training(self, job: TrainingJob) -> None:
        """Execute real training with HuggingFace (stub).

        Args:
            job: Training job
        """
        # This would implement actual training with:
        # - Load base model
        # - Initialize LoRA adapters
        # - Load and tokenize dataset
        # - Training loop with gradient updates
        # - Validation and checkpointing
        raise NotImplementedError("Real training not implemented in local dev mode")

    async def _create_model_artifact(self, job: TrainingJob) -> str:
        """Create model artifact from training job.

        Args:
            job: Completed training job

        Returns:
            Model ID
        """
        # Create artifact path (simulated)
        artifact_path = f"/tmp/l07_models/{job.job_id}/model.safetensors"

        # Create lineage
        lineage = ModelLineage(
            base_model_id=job.base_model_id,
            training_job_id=job.job_id,
            dataset_id=job.dataset_id,
            dataset_version=job.dataset_version,
            training_config=job.config.to_dict(),
            training_metrics={
                'final_loss': job.final_loss,
                'epochs': job.config.num_epochs
            }
        )

        # Create metrics
        metrics = ModelMetrics(
            final_train_loss=job.final_loss or 0.0,
            final_eval_loss=job.validation_metrics.eval_loss if job.validation_metrics else 0.0,
            training_duration_seconds=job.get_duration_seconds() or 0.0,
            accuracy=job.validation_metrics.accuracy if job.validation_metrics else 0.0,
            latency_p50_ms=job.validation_metrics.latency_p50_ms if job.validation_metrics else 0.0,
            latency_p95_ms=job.validation_metrics.latency_p95_ms if job.validation_metrics else 0.0,
            latency_p99_ms=job.validation_metrics.latency_p99_ms if job.validation_metrics else 0.0,
            model_size_mb=random.uniform(500, 1000),
            gpu_memory_mb=random.uniform(2000, 4000),
            regression_test_pass_rate=(
                job.validation_metrics.regression_tests_passed /
                max(1, job.validation_metrics.regression_tests_total)
                if job.validation_metrics else 0.0
            ),
            safety_score=random.uniform(0.95, 1.0)
        )

        # Create model artifact
        artifact = ModelArtifact(
            name=job.job_name,
            version="1.0.0",
            model_type=ModelType.LORA_ADAPTER,
            stage=ModelStage.DEVELOPMENT,
            artifact_path=artifact_path,
            artifact_format="safetensors",
            artifact_size_bytes=random.randint(500_000_000, 1_000_000_000),
            lineage=lineage,
            metrics=metrics,
            description=f"Fine-tuned model from job {job.job_id}",
            tags=[f"dataset_{job.dataset_id}", f"base_{job.base_model_id}"]
        )

        # Register with model registry
        if self.model_registry:
            model_id = await self.model_registry.register_model(artifact)
            logger.info(f"Created model artifact {model_id} for job {job.job_id}")
            return model_id
        else:
            logger.warning("No model registry available, model not registered")
            return artifact.model_id

    async def get_job_status(self, job_id: str) -> Optional[TrainingJob]:
        """Get training job status.

        Args:
            job_id: Job identifier

        Returns:
            Training job or None if not found
        """
        return self.active_jobs.get(job_id)

    async def cancel_job(self, job_id: str) -> bool:
        """Cancel running training job.

        Args:
            job_id: Job identifier

        Returns:
            True if cancelled, False if not found or already terminal
        """
        job = self.active_jobs.get(job_id)
        if not job:
            return False

        if job.is_terminal():
            logger.warning(f"Job {job_id} is already in terminal state: {job.status}")
            return False

        job.update_status(JobStatus.CANCELLED, "Cancelled by user")
        logger.info(f"Cancelled job {job_id}")

        return True

    async def list_jobs(
        self,
        status_filter: Optional[JobStatus] = None
    ) -> list[TrainingJob]:
        """List training jobs with optional filter.

        Args:
            status_filter: Optional status filter

        Returns:
            List of training jobs
        """
        jobs = list(self.active_jobs.values())

        if status_filter:
            jobs = [j for j in jobs if j.status == status_filter]

        return jobs

    def get_statistics(self) -> Dict[str, Any]:
        """Get training statistics.

        Returns:
            Statistics dictionary
        """
        jobs = list(self.active_jobs.values())

        completed = len([j for j in jobs if j.status == JobStatus.COMPLETED])
        failed = len([j for j in jobs if j.status == JobStatus.FAILED])
        active = len([j for j in jobs if j.status == JobStatus.TRAINING])

        total_checkpoints = sum(
            len(chkpts) for chkpts in self._checkpoints.values()
        )

        return {
            'total_jobs': len(jobs),
            'completed_jobs': completed,
            'failed_jobs': failed,
            'active_jobs': active,
            'success_rate': completed / max(1, completed + failed),
            'total_checkpoints': total_checkpoints
        }

    # ==================== Checkpoint Management ====================

    async def _save_checkpoint(
        self,
        job: TrainingJob,
        epoch: int,
        step: int,
        train_loss: float,
        eval_loss: Optional[float]
    ) -> TrainingCheckpoint:
        """Save a training checkpoint.

        Args:
            job: Training job
            epoch: Current epoch
            step: Current step
            train_loss: Training loss
            eval_loss: Evaluation loss

        Returns:
            TrainingCheckpoint
        """
        checkpoint_id = f"{job.job_id}_epoch{epoch}_step{step}"
        checkpoint_path = os.path.join(
            self.checkpoint_dir,
            job.job_id,
            f"checkpoint_epoch{epoch}.json"
        )

        # Create checkpoint directory
        os.makedirs(os.path.dirname(checkpoint_path), exist_ok=True)

        checkpoint = TrainingCheckpoint(
            checkpoint_id=checkpoint_id,
            job_id=job.job_id,
            epoch=epoch,
            step=step,
            train_loss=train_loss,
            eval_loss=eval_loss,
            created_at=datetime.now(timezone.utc).isoformat(),
            checkpoint_path=checkpoint_path,
            metadata={
                "learning_rate": job.config.learning_rate,
                "batch_size": job.config.batch_size,
                "base_model_id": job.base_model_id,
            }
        )

        # Save checkpoint metadata
        try:
            with open(checkpoint_path, 'w') as f:
                json.dump(asdict(checkpoint), f, indent=2)
        except Exception as e:
            logger.warning(f"Failed to save checkpoint file: {e}")

        # Track checkpoint
        if job.job_id not in self._checkpoints:
            self._checkpoints[job.job_id] = []
        self._checkpoints[job.job_id].append(checkpoint)

        logger.info(
            f"Saved checkpoint: {checkpoint_id} "
            f"(train_loss={train_loss:.4f}, eval_loss={eval_loss:.4f if eval_loss else 'N/A'})"
        )

        return checkpoint

    async def get_checkpoints(
        self,
        job_id: str
    ) -> List[TrainingCheckpoint]:
        """Get all checkpoints for a job.

        Args:
            job_id: Job identifier

        Returns:
            List of checkpoints
        """
        return self._checkpoints.get(job_id, [])

    async def get_latest_checkpoint(
        self,
        job_id: str
    ) -> Optional[TrainingCheckpoint]:
        """Get the latest checkpoint for a job.

        Args:
            job_id: Job identifier

        Returns:
            Latest checkpoint or None
        """
        checkpoints = self._checkpoints.get(job_id, [])
        if not checkpoints:
            return None
        return checkpoints[-1]

    async def resume_from_checkpoint(
        self,
        job_id: str,
        checkpoint_id: Optional[str] = None
    ) -> TrainingJob:
        """Resume training from a checkpoint.

        Args:
            job_id: Original job ID
            checkpoint_id: Specific checkpoint (uses latest if not provided)

        Returns:
            New training job

        Raises:
            TrainingError: If job or checkpoint not found
        """
        original_job = self.active_jobs.get(job_id)
        if not original_job:
            raise TrainingError(
                LearningErrorCode.E7900,
                f"Job not found: {job_id}"
            )

        checkpoints = self._checkpoints.get(job_id, [])
        if not checkpoints:
            raise TrainingError(
                LearningErrorCode.E7903,
                f"No checkpoints for job: {job_id}"
            )

        # Find checkpoint
        if checkpoint_id:
            checkpoint = next(
                (c for c in checkpoints if c.checkpoint_id == checkpoint_id),
                None
            )
            if not checkpoint:
                raise TrainingError(
                    LearningErrorCode.E7903,
                    f"Checkpoint not found: {checkpoint_id}"
                )
        else:
            checkpoint = checkpoints[-1]

        logger.info(
            f"Resuming job {job_id} from checkpoint: {checkpoint.checkpoint_id}"
        )

        # Create resumed job with adjusted config
        remaining_epochs = original_job.config.num_epochs - checkpoint.epoch
        resumed_config = JobConfig(
            num_epochs=remaining_epochs,
            batch_size=original_job.config.batch_size,
            learning_rate=original_job.config.learning_rate,
            optimizer=original_job.config.optimizer,
            warmup_steps=0,  # Skip warmup on resume
        )

        # Start new job
        return await self.start_training(
            dataset_id=original_job.dataset_id,
            base_model_id=original_job.base_model_id,
            config=resumed_config
        )

    # ==================== Progress Tracking ====================

    async def get_training_progress(
        self,
        job_id: str
    ) -> Optional[TrainingProgress]:
        """Get real-time training progress.

        Args:
            job_id: Job identifier

        Returns:
            TrainingProgress or None
        """
        return self._progress.get(job_id)

    async def get_all_progress(self) -> Dict[str, TrainingProgress]:
        """Get progress for all active jobs.

        Returns:
            Dictionary of job_id -> TrainingProgress
        """
        return dict(self._progress)

    def get_health_status(self) -> Dict[str, Any]:
        """Get engine health status.

        Returns:
            Health status dictionary
        """
        stats = self.get_statistics()
        active_jobs = stats.get('active_jobs', 0)

        return {
            "healthy": True,
            "active_jobs": active_jobs,
            "completed_jobs": stats.get('completed_jobs', 0),
            "failed_jobs": stats.get('failed_jobs', 0),
            "success_rate_percent": round(stats.get('success_rate', 0) * 100, 2),
            "total_checkpoints": stats.get('total_checkpoints', 0),
            "simulation_mode": self.simulate_training,
        }
