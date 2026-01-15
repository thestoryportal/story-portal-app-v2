"""L07 Learning Layer - Fine-Tuning Engine Service.

Orchestrates supervised fine-tuning with LoRA. Uses simulation for local development.
"""

import asyncio
import logging
import time
from typing import Dict, Any, Optional
from datetime import datetime
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


class FineTuningEngine:
    """Supervised fine-tuning engine with LoRA adapters.

    For local development, implements simulated training to test pipeline flow
    without requiring GPU resources. Production would use HuggingFace + PyTorch.
    """

    def __init__(
        self,
        model_registry=None,
        dataset_curator=None,
        simulate_training: bool = True
    ):
        """Initialize Fine-Tuning Engine.

        Args:
            model_registry: Model registry service
            dataset_curator: Dataset curator service
            simulate_training: Use simulation instead of actual training
        """
        self.model_registry = model_registry
        self.dataset_curator = dataset_curator
        self.simulate_training = simulate_training
        self.active_jobs: Dict[str, TrainingJob] = {}

        logger.info(
            f"Initialized FineTuningEngine "
            f"(simulation={'ON' if simulate_training else 'OFF'})"
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

        # Start training asynchronously
        asyncio.create_task(self._execute_training(job))

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

        Args:
            job: Training job
        """
        logger.info(f"Simulating training for job {job.job_id}")

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

                # Create training metric
                metric = TrainingMetrics(
                    epoch=epoch + 1,
                    step=step + 1,
                    train_loss=train_loss,
                    learning_rate=job.config.learning_rate * (1 - progress * 0.5),
                    grad_norm=random.uniform(0.5, 1.5),
                    gpu_memory_mb=random.uniform(2000, 4000),
                    gpu_utilization_percent=random.uniform(70, 95),
                    throughput_samples_per_second=random.uniform(50, 100)
                )

                job.add_training_metric(metric)

            # Epoch evaluation
            eval_loss = train_loss * random.uniform(1.0, 1.1)
            logger.info(
                f"Job {job.job_id}: Epoch {epoch + 1} complete - "
                f"train_loss={train_loss:.4f}, eval_loss={eval_loss:.4f}"
            )

            # Add eval metric
            eval_metric = TrainingMetrics(
                epoch=epoch + 1,
                step=step + 1,
                train_loss=train_loss,
                eval_loss=eval_loss,
                learning_rate=job.config.learning_rate
            )
            job.add_training_metric(eval_metric)

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

        return {
            'total_jobs': len(jobs),
            'completed_jobs': completed,
            'failed_jobs': failed,
            'active_jobs': active,
            'success_rate': completed / max(1, completed + failed)
        }
