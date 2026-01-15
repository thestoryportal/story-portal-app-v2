"""L07 Learning Layer - Model Registry Service.

Manages model artifacts, versioning, lineage tracking, and stage transitions.
"""

import logging
import json
import os
from typing import List, Dict, Any, Optional
from datetime import datetime

from ..models.model_artifact import ModelArtifact, ModelType, ModelStage, ModelVersion, ModelLineage, ModelMetrics
from ..models.error_codes import LearningErrorCode, ModelRegistryError

logger = logging.getLogger(__name__)


class ModelRegistry:
    """Model artifact registry with lifecycle management.

    This service manages model artifacts through their complete lifecycle from
    development to production, including versioning, lineage tracking, and
    stage transitions with validation gates.
    """

    def __init__(self, storage_path: str = "/tmp/l07_models"):
        """Initialize Model Registry.

        Args:
            storage_path: Path to store model metadata
        """
        self.storage_path = storage_path
        self.models: Dict[str, ModelArtifact] = {}

        # Ensure storage directory exists
        os.makedirs(storage_path, exist_ok=True)

        logger.info(f"Initialized ModelRegistry with storage at {storage_path}")

    async def register_model(
        self,
        artifact: ModelArtifact
    ) -> str:
        """Register new model artifact.

        Args:
            artifact: Model artifact to register

        Returns:
            Model ID

        Raises:
            ModelRegistryError: If registration fails
        """
        if not artifact.validate():
            raise ModelRegistryError(
                LearningErrorCode.E7204,
                "Invalid model artifact: missing required fields"
            )

        # Check for version conflict
        if artifact.model_id in self.models:
            raise ModelRegistryError(
                LearningErrorCode.E7203,
                f"Model already registered: {artifact.model_id}"
            )

        # Store model
        self.models[artifact.model_id] = artifact
        await self._persist_model(artifact)

        logger.info(
            f"Registered model {artifact.model_id} ({artifact.name}) "
            f"v{artifact.version} - {artifact.model_type.value} - {artifact.stage.value}"
        )

        return artifact.model_id

    async def get_model(self, model_id: str) -> Optional[ModelArtifact]:
        """Get model by ID.

        Args:
            model_id: Model identifier

        Returns:
            Model artifact or None if not found
        """
        model = self.models.get(model_id)
        if not model:
            logger.warning(f"Model not found: {model_id}")
        return model

    async def list_models(
        self,
        model_type: Optional[ModelType] = None,
        stage: Optional[ModelStage] = None,
        tags: Optional[List[str]] = None
    ) -> List[ModelArtifact]:
        """List models with optional filters.

        Args:
            model_type: Filter by model type
            stage: Filter by deployment stage
            tags: Filter by tags

        Returns:
            List of matching models
        """
        models = list(self.models.values())

        if model_type:
            models = [m for m in models if m.model_type == model_type]

        if stage:
            models = [m for m in models if m.stage == stage]

        if tags:
            models = [m for m in models if any(tag in m.tags for tag in tags)]

        return models

    async def promote_model(
        self,
        model_id: str,
        target_stage: ModelStage,
        promoted_by: str,
        notes: str = ""
    ) -> ModelArtifact:
        """Promote model to target stage with validation.

        Args:
            model_id: Model identifier
            target_stage: Target deployment stage
            promoted_by: User/service performing promotion
            notes: Optional promotion notes

        Returns:
            Updated model artifact

        Raises:
            ModelRegistryError: If promotion not allowed or fails
        """
        model = await self.get_model(model_id)
        if not model:
            raise ModelRegistryError(
                LearningErrorCode.E7200,
                f"Model not found: {model_id}"
            )

        # Check if transition is allowed
        can_transition, reason = model.can_transition_to(target_stage)
        if not can_transition:
            raise ModelRegistryError(
                LearningErrorCode.E7202,
                f"Cannot promote model: {reason}"
            )

        # Perform transition
        approval_required = target_stage == ModelStage.PRODUCTION
        model.transition_stage(
            new_stage=target_stage,
            transitioned_by=promoted_by,
            notes=notes,
            approval_required=approval_required,
            approver=promoted_by if approval_required else None
        )

        # Persist updated model
        await self._persist_model(model)

        logger.info(
            f"Promoted model {model_id} to {target_stage.value} by {promoted_by}"
        )

        return model

    async def update_model_metrics(
        self,
        model_id: str,
        metrics: ModelMetrics
    ) -> ModelArtifact:
        """Update model performance metrics.

        Args:
            model_id: Model identifier
            metrics: Updated metrics

        Returns:
            Updated model artifact

        Raises:
            ModelRegistryError: If model not found
        """
        model = await self.get_model(model_id)
        if not model:
            raise ModelRegistryError(
                LearningErrorCode.E7200,
                f"Model not found: {model_id}"
            )

        model.metrics = metrics
        model.updated_at = datetime.utcnow()
        await self._persist_model(model)

        logger.info(f"Updated metrics for model {model_id}")

        return model

    async def sign_model(
        self,
        model_id: str,
        signing_key_version: str
    ) -> ModelArtifact:
        """Sign model artifact for integrity verification.

        Args:
            model_id: Model identifier
            signing_key_version: Version of signing key used

        Returns:
            Signed model artifact

        Raises:
            ModelRegistryError: If model not found or signing fails
        """
        model = await self.get_model(model_id)
        if not model:
            raise ModelRegistryError(
                LearningErrorCode.E7200,
                f"Model not found: {model_id}"
            )

        if not os.path.exists(model.artifact_path):
            raise ModelRegistryError(
                LearningErrorCode.E7200,
                f"Model artifact file not found: {model.artifact_path}"
            )

        # Compute checksum
        try:
            checksum = model.compute_checksum(model.artifact_path)
            model.checksum_sha256 = checksum
            model.signed = True
            model.signing_key_version = signing_key_version
            model.signature = f"sig_{checksum[:16]}"  # Stub signature
            model.updated_at = datetime.utcnow()

            await self._persist_model(model)

            logger.info(f"Signed model {model_id} with key {signing_key_version}")

            return model

        except Exception as e:
            raise ModelRegistryError(
                LearningErrorCode.E7201,
                f"Failed to sign model: {e}"
            )

    async def verify_model(self, model_id: str) -> bool:
        """Verify model artifact integrity.

        Args:
            model_id: Model identifier

        Returns:
            True if verification passes, False otherwise

        Raises:
            ModelRegistryError: If model not found
        """
        model = await self.get_model(model_id)
        if not model:
            raise ModelRegistryError(
                LearningErrorCode.E7200,
                f"Model not found: {model_id}"
            )

        if not model.signed:
            logger.warning(f"Model {model_id} is not signed")
            return False

        if not os.path.exists(model.artifact_path):
            logger.error(f"Model artifact file not found: {model.artifact_path}")
            return False

        try:
            return model.verify_checksum(model.artifact_path)
        except Exception as e:
            logger.error(f"Verification failed for model {model_id}: {e}")
            return False

    async def archive_model(
        self,
        model_id: str,
        archived_by: str,
        reason: str = ""
    ) -> ModelArtifact:
        """Archive model (move to ARCHIVED stage).

        Args:
            model_id: Model identifier
            archived_by: User/service performing archival
            reason: Reason for archival

        Returns:
            Archived model artifact

        Raises:
            ModelRegistryError: If model not found
        """
        return await self.promote_model(
            model_id=model_id,
            target_stage=ModelStage.ARCHIVED,
            promoted_by=archived_by,
            notes=f"Archived: {reason}"
        )

    async def quarantine_model(
        self,
        model_id: str,
        quarantined_by: str,
        reason: str
    ) -> ModelArtifact:
        """Quarantine model due to issues.

        Args:
            model_id: Model identifier
            quarantined_by: User/service performing quarantine
            reason: Reason for quarantine

        Returns:
            Quarantined model artifact

        Raises:
            ModelRegistryError: If model not found
        """
        return await self.promote_model(
            model_id=model_id,
            target_stage=ModelStage.QUARANTINED,
            promoted_by=quarantined_by,
            notes=f"Quarantined: {reason}"
        )

    async def get_production_models(self) -> List[ModelArtifact]:
        """Get all models in production.

        Returns:
            List of production models
        """
        return await self.list_models(stage=ModelStage.PRODUCTION)

    async def get_model_lineage(
        self,
        model_id: str
    ) -> Optional[ModelLineage]:
        """Get model lineage information.

        Args:
            model_id: Model identifier

        Returns:
            Model lineage or None if not found
        """
        model = await self.get_model(model_id)
        return model.lineage if model else None

    async def get_model_history(
        self,
        model_id: str
    ) -> List[Dict[str, Any]]:
        """Get stage transition history for model.

        Args:
            model_id: Model identifier

        Returns:
            List of stage transitions

        Raises:
            ModelRegistryError: If model not found
        """
        model = await self.get_model(model_id)
        if not model:
            raise ModelRegistryError(
                LearningErrorCode.E7200,
                f"Model not found: {model_id}"
            )

        return model.stage_history

    async def _persist_model(self, model: ModelArtifact) -> None:
        """Persist model metadata to storage.

        Args:
            model: Model artifact to persist
        """
        try:
            file_path = f"{self.storage_path}/{model.model_id}.json"
            with open(file_path, 'w') as f:
                json.dump(model.to_dict(), f, indent=2)

            logger.debug(f"Persisted model {model.model_id} to {file_path}")

        except Exception as e:
            logger.error(f"Failed to persist model: {e}")
            # Non-fatal - model still in memory

    async def load_model_from_storage(self, model_id: str) -> Optional[ModelArtifact]:
        """Load model from storage.

        Args:
            model_id: Model identifier

        Returns:
            Model artifact or None if not found
        """
        try:
            file_path = f"{self.storage_path}/{model_id}.json"
            if not os.path.exists(file_path):
                return None

            with open(file_path, 'r') as f:
                data = json.load(f)

            model = ModelArtifact.from_dict(data)
            self.models[model_id] = model

            logger.debug(f"Loaded model {model_id} from storage")
            return model

        except Exception as e:
            logger.error(f"Failed to load model from storage: {e}")
            return None

    def get_statistics(self) -> Dict[str, Any]:
        """Get registry statistics.

        Returns:
            Statistics dictionary
        """
        models_by_stage = {}
        for stage in ModelStage:
            count = len([m for m in self.models.values() if m.stage == stage])
            models_by_stage[stage.value] = count

        models_by_type = {}
        for model_type in ModelType:
            count = len([m for m in self.models.values() if m.model_type == model_type])
            models_by_type[model_type.value] = count

        return {
            'total_models': len(self.models),
            'models_by_stage': models_by_stage,
            'models_by_type': models_by_type,
            'production_models': models_by_stage.get(ModelStage.PRODUCTION.value, 0)
        }
