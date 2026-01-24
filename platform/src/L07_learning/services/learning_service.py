"""L07 Learning Layer - Main Learning Service Orchestrator.

Central orchestrator combining all L07 components for end-to-end learning pipeline.
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

from ..models.training_example import TrainingExample
from ..models.dataset import Dataset
from ..models.training_job import TrainingJob, JobConfig
from ..models.model_artifact import ModelArtifact, ModelStage

from .training_data_extractor import TrainingDataExtractor
from .example_quality_filter import ExampleQualityFilter, FilterConfig
from .dataset_curator import DatasetCurator
from .model_registry import ModelRegistry
from .fine_tuning_engine import FineTuningEngine
from .rlhf_engine import RLHFEngine
from .model_validator import ModelValidator
from .l01_bridge import L07Bridge

logger = logging.getLogger(__name__)


class LearningService:
    """Main L07 Learning Service orchestrating the complete learning pipeline.

    This service coordinates:
    - Training data extraction from execution traces
    - Example quality filtering
    - Dataset curation and versioning
    - Model fine-tuning with LoRA
    - Model validation
    - Model registry and deployment

    For local development, uses simulated training and stub implementations.

    When L01 Data Layer is available, training data and datasets are persisted
    via L07Bridge for cross-layer access and long-term retention.
    """

    def __init__(
        self,
        storage_path: str = "/tmp/l07_learning",
        enable_rlhf: bool = False,
        l01_base_url: Optional[str] = None
    ):
        """Initialize Learning Service.

        Args:
            storage_path: Base path for storage (fallback when L01 unavailable)
            enable_rlhf: Enable RLHF pipeline (stub)
            l01_base_url: Optional L01 Data Layer URL (e.g., "http://localhost:8002")
        """
        self.storage_path = storage_path

        # Initialize L01 Bridge if URL provided
        self.l01_bridge = None
        if l01_base_url:
            try:
                self.l01_bridge = L07Bridge(l01_base_url=l01_base_url)
                logger.info(f"L07Bridge initialized with L01 at {l01_base_url}")
            except Exception as e:
                logger.warning(f"Failed to initialize L07Bridge: {e}")

        # Initialize components
        self.extractor = TrainingDataExtractor()
        self.filter = ExampleQualityFilter()
        self.curator = DatasetCurator(
            storage_path=f"{storage_path}/datasets",
            l01_bridge=self.l01_bridge
        )
        self.registry = ModelRegistry(f"{storage_path}/models")
        self.fine_tuning_engine = FineTuningEngine(
            model_registry=self.registry,
            dataset_curator=self.curator,
            simulate_training=True
        )
        self.validator = ModelValidator()

        if enable_rlhf:
            self.rlhf_engine = RLHFEngine(model_registry=self.registry)
        else:
            self.rlhf_engine = None

        self.initialized = False

        logger.info(
            f"Initialized LearningService "
            f"(storage={storage_path}, rlhf={'ON' if enable_rlhf else 'OFF'}, "
            f"l01={'enabled' if self.l01_bridge else 'disabled'})"
        )

    async def initialize(self) -> None:
        """Initialize the learning service and all components."""
        if self.initialized:
            logger.warning("LearningService already initialized")
            return

        logger.info("Initializing LearningService components...")

        # Initialize L01 Bridge if available
        if self.l01_bridge:
            try:
                await self.l01_bridge.initialize()
                logger.info("L07Bridge initialized successfully")
            except Exception as e:
                logger.warning(f"L07Bridge initialization failed: {e}")
                self.l01_bridge = None

        self.initialized = True
        logger.info("LearningService initialized successfully")

    async def cleanup(self) -> None:
        """Clean up resources."""
        logger.info("Cleaning up LearningService...")

        # Cleanup L01 Bridge if available
        if self.l01_bridge:
            try:
                await self.l01_bridge.cleanup()
                logger.info("L07Bridge cleanup complete")
            except Exception as e:
                logger.warning(f"L07Bridge cleanup failed: {e}")

        self.initialized = False
        logger.info("LearningService cleanup complete")

    async def process_event(self, event: Dict[str, Any]) -> Optional[TrainingExample]:
        """Process single event from L01 event stream.

        Args:
            event: CloudEvent from L01

        Returns:
            Extracted training example or None
        """
        return await self.extractor.extract_from_event(event)

    async def process_events_batch(
        self,
        events: List[Dict[str, Any]]
    ) -> List[TrainingExample]:
        """Process batch of events from L01.

        Args:
            events: List of CloudEvents

        Returns:
            List of extracted training examples
        """
        logger.info(f"Processing batch of {len(events)} events")
        return await self.extractor.extract_batch(events)

    async def filter_examples(
        self,
        examples: List[TrainingExample]
    ) -> List[TrainingExample]:
        """Filter examples by quality.

        Args:
            examples: Training examples to filter

        Returns:
            Filtered examples
        """
        logger.info(f"Filtering {len(examples)} examples")
        filtered, metadata = await self.filter.filter_examples(examples)
        logger.info(f"Filtered to {len(filtered)} examples (metadata={metadata})")
        return filtered

    async def create_training_dataset(
        self,
        name: str,
        examples: List[TrainingExample],
        description: str = "",
        tags: Optional[List[str]] = None
    ) -> Dataset:
        """Create versioned training dataset.

        Args:
            name: Dataset name
            examples: Training examples
            description: Dataset description
            tags: Optional tags

        Returns:
            Created dataset
        """
        logger.info(f"Creating dataset '{name}' with {len(examples)} examples")

        dataset = await self.curator.create_dataset(
            name=name,
            examples=examples,
            description=description,
            tags=tags
        )

        logger.info(
            f"Created dataset {dataset.dataset_id} ({name}) v{dataset.version}"
        )

        return dataset

    async def train_model(
        self,
        dataset_id: str,
        base_model_id: str = "gpt-4-turbo-2024-04",
        config: Optional[JobConfig] = None
    ) -> TrainingJob:
        """Start model training job.

        Args:
            dataset_id: Dataset to train on
            base_model_id: Base model identifier
            config: Training configuration

        Returns:
            Training job
        """
        logger.info(
            f"Starting training: dataset={dataset_id}, base_model={base_model_id}"
        )

        job = await self.fine_tuning_engine.start_training(
            dataset_id=dataset_id,
            base_model_id=base_model_id,
            config=config
        )

        logger.info(f"Started training job {job.job_id}")

        return job

    async def validate_model(
        self,
        model_id: str,
        baseline_model_id: Optional[str] = None
    ):
        """Validate model before deployment.

        Args:
            model_id: Model to validate
            baseline_model_id: Optional baseline for comparison

        Returns:
            Validation result
        """
        logger.info(f"Validating model {model_id}")

        model = await self.registry.get_model(model_id)
        if not model:
            raise ValueError(f"Model not found: {model_id}")

        baseline = None
        if baseline_model_id:
            baseline = await self.registry.get_model(baseline_model_id)

        result = await self.validator.validate_model(model, baseline)

        logger.info(
            f"Validation result for {model_id}: "
            f"recommendation={result.recommendation}, passed={result.passed}"
        )

        return result

    async def deploy_model(
        self,
        model_id: str,
        validate: bool = True
    ) -> ModelArtifact:
        """Deploy model to production (promote to PRODUCTION stage).

        Args:
            model_id: Model to deploy
            validate: Whether to validate before deployment

        Returns:
            Deployed model artifact
        """
        logger.info(f"Deploying model {model_id} (validate={validate})")

        model = await self.registry.get_model(model_id)
        if not model:
            raise ValueError(f"Model not found: {model_id}")

        # Validate if requested
        if validate:
            validation_result = await self.validate_model(model_id)

            if validation_result.recommendation == "REJECT":
                raise ValueError(
                    f"Model {model_id} failed validation: "
                    f"{validation_result.regression_details}"
                )

            if validation_result.recommendation == "REVIEW":
                logger.warning(
                    f"Model {model_id} requires manual review before deployment"
                )

        # Sign model
        await self.registry.sign_model(model_id, "signing-key-v1")

        # Promote through stages
        if model.stage == ModelStage.DEVELOPMENT:
            await self.registry.promote_model(
                model_id=model_id,
                target_stage=ModelStage.STAGING,
                promoted_by="LearningService",
                notes="Automated promotion to staging"
            )

        if model.stage == ModelStage.STAGING:
            await self.registry.promote_model(
                model_id=model_id,
                target_stage=ModelStage.PRODUCTION,
                promoted_by="LearningService",
                notes="Validated and deployed to production"
            )

        logger.info(f"Deployed model {model_id} to production")

        return model

    async def end_to_end_pipeline(
        self,
        events: List[Dict[str, Any]],
        dataset_name: str,
        base_model_id: str = "gpt-4-turbo-2024-04"
    ) -> Dict[str, Any]:
        """Run complete end-to-end learning pipeline.

        Args:
            events: Execution events from L01
            dataset_name: Name for created dataset
            base_model_id: Base model to fine-tune

        Returns:
            Dictionary with pipeline results
        """
        logger.info(
            f"Running end-to-end pipeline: "
            f"{len(events)} events -> {dataset_name}"
        )

        # Step 1: Extract training examples
        examples = await self.process_events_batch(events)
        logger.info(f"Extracted {len(examples)} training examples")

        if not examples:
            return {
                'status': 'failed',
                'reason': 'No examples extracted',
                'examples_extracted': 0
            }

        # Step 2: Filter examples
        filtered_examples = await self.filter_examples(examples)
        logger.info(f"Filtered to {len(filtered_examples)} examples")

        if len(filtered_examples) < 100:
            logger.warning(f"Only {len(filtered_examples)} examples after filtering")

        # Step 3: Create dataset
        dataset = await self.create_training_dataset(
            name=dataset_name,
            examples=filtered_examples,
            description=f"Auto-generated dataset from {len(events)} events",
            tags=['auto-generated', 'e2e-pipeline']
        )

        # Step 4: Train model
        job = await self.train_model(
            dataset_id=dataset.dataset_id,
            base_model_id=base_model_id
        )

        # Wait for training to complete (in real system would be async)
        import asyncio
        while not job.is_terminal():
            await asyncio.sleep(0.5)
            job = await self.fine_tuning_engine.get_job_status(job.job_id)

        if job.status.value != "completed":
            return {
                'status': 'failed',
                'reason': f'Training failed: {job.error_message}',
                'job_id': job.job_id,
                'examples_extracted': len(examples),
                'examples_filtered': len(filtered_examples),
                'dataset_id': dataset.dataset_id
            }

        # Step 5: Validate model
        model_id = job.output_model_id
        if not model_id:
            return {
                'status': 'failed',
                'reason': 'No model produced',
                'job_id': job.job_id
            }

        validation_result = await self.validate_model(model_id)

        return {
            'status': 'success',
            'examples_extracted': len(examples),
            'examples_filtered': len(filtered_examples),
            'dataset_id': dataset.dataset_id,
            'dataset_size': len(filtered_examples),
            'training_job_id': job.job_id,
            'model_id': model_id,
            'validation_passed': validation_result.passed,
            'validation_recommendation': validation_result.recommendation,
            'final_loss': job.final_loss,
            'accuracy': job.validation_metrics.accuracy if job.validation_metrics else 0.0
        }

    async def create_curriculum(
        self,
        name: str,
        stages: List[Dict[str, Any]],
        description: str = ""
    ) -> Dict[str, Any]:
        """
        Create a curriculum learning plan with progressive stages.

        Args:
            name: Curriculum name
            stages: List of stage configurations, each containing:
                - dataset_id: Dataset for this stage
                - epochs: Number of training epochs
                - learning_rate: Learning rate for this stage
                - difficulty: Difficulty level (easy, medium, hard)
            description: Curriculum description

        Returns:
            Curriculum definition
        """
        import uuid

        curriculum_id = str(uuid.uuid4())

        curriculum = {
            "curriculum_id": curriculum_id,
            "name": name,
            "description": description,
            "stages": stages,
            "created_at": datetime.utcnow().isoformat(),
            "status": "created",
            "current_stage": 0,
            "completed_stages": [],
        }

        logger.info(f"Created curriculum '{name}' with {len(stages)} stages")

        return curriculum

    async def run_curriculum(
        self,
        curriculum: Dict[str, Any],
        base_model_id: str = "gpt-4-turbo-2024-04"
    ) -> Dict[str, Any]:
        """
        Execute a curriculum learning pipeline.

        Args:
            curriculum: Curriculum definition
            base_model_id: Base model to fine-tune

        Returns:
            Curriculum execution results
        """
        logger.info(
            f"Running curriculum {curriculum['curriculum_id']} "
            f"with {len(curriculum['stages'])} stages"
        )

        results = {
            "curriculum_id": curriculum["curriculum_id"],
            "stages_completed": 0,
            "stage_results": [],
            "final_model_id": None,
        }

        current_model_id = base_model_id

        for i, stage in enumerate(curriculum["stages"]):
            logger.info(f"Starting curriculum stage {i + 1}/{len(curriculum['stages'])}")

            try:
                # Create training job for this stage
                job_config = JobConfig(
                    epochs=stage.get("epochs", 3),
                    learning_rate=stage.get("learning_rate", 1e-4),
                    batch_size=stage.get("batch_size", 8),
                )

                job = await self.train_model(
                    dataset_id=stage["dataset_id"],
                    base_model_id=current_model_id,
                    config=job_config
                )

                # Wait for training
                while not job.is_terminal():
                    await asyncio.sleep(0.5)
                    job = await self.fine_tuning_engine.get_job_status(job.job_id)

                stage_result = {
                    "stage": i + 1,
                    "dataset_id": stage["dataset_id"],
                    "job_id": job.job_id,
                    "status": job.status.value,
                    "output_model_id": job.output_model_id,
                    "final_loss": job.final_loss,
                }

                results["stage_results"].append(stage_result)

                if job.status.value == "completed" and job.output_model_id:
                    current_model_id = job.output_model_id
                    results["stages_completed"] += 1
                    results["final_model_id"] = current_model_id
                else:
                    logger.warning(f"Stage {i + 1} failed, stopping curriculum")
                    break

            except Exception as e:
                logger.error(f"Curriculum stage {i + 1} failed: {e}")
                results["stage_results"].append({
                    "stage": i + 1,
                    "error": str(e),
                    "status": "failed"
                })
                break

        logger.info(
            f"Curriculum complete: {results['stages_completed']}/{len(curriculum['stages'])} stages"
        )

        return results

    async def record_feedback(
        self,
        example_id: str,
        feedback_type: str,
        feedback_value: Any,
        feedback_source: str = "human"
    ) -> bool:
        """
        Record feedback for a training example.

        Args:
            example_id: Training example ID
            feedback_type: Type of feedback (rating, correction, preference)
            feedback_value: Feedback value
            feedback_source: Source of feedback (human, model, automated)

        Returns:
            True if recorded successfully
        """
        try:
            feedback = {
                "example_id": example_id,
                "feedback_type": feedback_type,
                "feedback_value": feedback_value,
                "feedback_source": feedback_source,
                "recorded_at": datetime.utcnow().isoformat(),
            }

            # Store via L01 bridge if available
            if self.l01_bridge:
                await self.l01_bridge.record_feedback(feedback)

            # If RLHF is enabled, queue for preference learning
            if self.rlhf_engine and feedback_type == "preference":
                await self.rlhf_engine.add_preference(
                    example_id=example_id,
                    preference=feedback_value
                )

            logger.info(f"Recorded {feedback_type} feedback for example {example_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to record feedback: {e}")
            return False

    async def get_feedback_summary(
        self,
        dataset_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get summary of recorded feedback.

        Args:
            dataset_id: Optional dataset to filter by

        Returns:
            Feedback summary
        """
        try:
            if self.l01_bridge:
                return await self.l01_bridge.get_feedback_summary(dataset_id)

            return {
                "total_feedback": 0,
                "by_type": {},
                "by_source": {},
            }

        except Exception as e:
            logger.error(f"Failed to get feedback summary: {e}")
            return {"error": str(e)}

    def get_health_status(self) -> Dict[str, Any]:
        """Get service health status."""
        return {
            "healthy": self.initialized,
            "initialized": self.initialized,
            "components": {
                "extractor": True,
                "filter": True,
                "curator": True,
                "registry": True,
                "fine_tuning_engine": True,
                "validator": True,
                "rlhf_engine": self.rlhf_engine is not None,
            },
            "l01_bridge_available": self.l01_bridge is not None,
            "storage_path": self.storage_path,
        }

    def get_statistics(self) -> Dict[str, Any]:
        """Get comprehensive statistics from all components.

        Returns:
            Statistics dictionary
        """
        stats = {
            'learning_service': {
                'initialized': self.initialized,
                'storage_path': self.storage_path,
                'rlhf_enabled': self.rlhf_engine is not None
            },
            'extractor': self.extractor.get_statistics(),
            'filter': self.filter.get_statistics(),
            'curator': self.curator.get_statistics(),
            'registry': self.registry.get_statistics(),
            'fine_tuning': self.fine_tuning_engine.get_statistics(),
            'validator': self.validator.get_statistics()
        }

        if self.rlhf_engine:
            stats['rlhf'] = self.rlhf_engine.get_statistics()

        return stats
