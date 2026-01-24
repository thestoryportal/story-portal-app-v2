"""L07 Learning Layer - Dataset Curator Service.

Manages dataset versions, creates train/val/test splits, and computes statistics.
Includes semantic deduplication and configurable quality filtering.
"""

import logging
import numpy as np
from typing import List, Dict, Any, Optional, Tuple, TYPE_CHECKING
from datetime import datetime, timezone
from uuid import UUID
import json
import hashlib
from dataclasses import dataclass, field

from ..models.dataset import Dataset, DatasetSplit, DatasetVersion, DatasetLineage, DatasetStatistics
from ..models.training_example import TrainingExample
from ..models.error_codes import LearningErrorCode, LearningLayerException

if TYPE_CHECKING:
    from .l01_bridge import L07Bridge

logger = logging.getLogger(__name__)


@dataclass
class QualityThresholds:
    """Configurable quality thresholds for dataset curation."""
    min_input_length: int = 10
    max_input_length: int = 10000
    min_output_length: int = 5
    max_output_length: int = 5000
    min_difficulty: float = 0.0
    max_difficulty: float = 1.0
    min_quality_score: float = 0.5
    dedupe_similarity_threshold: float = 0.95
    require_metadata: bool = False
    required_fields: List[str] = field(default_factory=list)


@dataclass
class DeduplicationResult:
    """Result of deduplication operation."""
    original_count: int
    deduplicated_count: int
    duplicates_removed: int
    duplicate_groups: List[List[str]] = field(default_factory=list)


class DatasetCurator:
    """Curate and version training datasets.

    This service creates versioned datasets with train/validation/test splits,
    computes statistics, and handles incremental updates.

    Features:
    - Configurable quality thresholds
    - Semantic deduplication using embeddings
    - Stratified sampling by domain and difficulty
    - Version management with semantic versioning

    When L01Bridge is provided, datasets and training examples are persisted
    to L01 Data Layer. Otherwise, falls back to local file storage and in-memory cache.
    """

    def __init__(
        self,
        storage_path: str = "/tmp/l07_datasets",
        l01_bridge: Optional["L07Bridge"] = None,
        quality_thresholds: Optional[QualityThresholds] = None,
        embedding_service: Optional[Any] = None
    ):
        """Initialize Dataset Curator.

        Args:
            storage_path: Path to store dataset metadata (fallback when bridge unavailable)
            l01_bridge: Optional bridge to L01 Data Layer for persistent storage
            quality_thresholds: Quality thresholds for filtering
            embedding_service: Optional embedding service for semantic deduplication
        """
        self.storage_path = storage_path
        self.l01_bridge = l01_bridge
        self.quality_thresholds = quality_thresholds or QualityThresholds()
        self.embedding_service = embedding_service
        self.datasets: Dict[str, Dataset] = {}

        # Caching for embeddings
        self._embedding_cache: Dict[str, np.ndarray] = {}

        # Metrics
        self._examples_filtered = 0
        self._duplicates_removed = 0

        logger.info(
            f"Initialized DatasetCurator with storage at {storage_path} "
            f"(L01Bridge={'enabled' if l01_bridge else 'disabled'}, "
            f"embedding={'enabled' if embedding_service else 'disabled'})"
        )

    async def create_dataset(
        self,
        name: str,
        examples: List[TrainingExample],
        split_ratios: Optional[Dict[str, float]] = None,
        description: str = "",
        tags: Optional[List[str]] = None
    ) -> Dataset:
        """Create new versioned dataset with splits.

        Args:
            name: Dataset name
            examples: List of training examples
            split_ratios: Split ratios (default: 0.8/0.1/0.1)
            description: Dataset description
            tags: Optional tags

        Returns:
            Created Dataset

        Raises:
            LearningLayerException: If dataset creation fails
        """
        if not examples:
            raise LearningLayerException(
                LearningErrorCode.E7100,
                "Cannot create dataset from empty example list"
            )

        logger.info(f"Creating dataset '{name}' with {len(examples)} examples")

        # Default split ratios
        if split_ratios is None:
            split_ratios = {
                "train": 0.8,
                "validation": 0.1,
                "test": 0.1
            }

        # Validate split ratios
        ratio_sum = sum(split_ratios.values())
        if abs(ratio_sum - 1.0) > 0.01:
            raise LearningLayerException(
                LearningErrorCode.E7500,
                f"Split ratios must sum to 1.0, got {ratio_sum}"
            )

        # Create dataset
        dataset = Dataset(
            name=name,
            version="1.0.0",
            description=description,
            tags=tags or [],
            split_ratios=split_ratios
        )

        # Create splits
        splits = await self._create_splits(examples, split_ratios)
        dataset.splits = splits

        # Add example IDs
        dataset.example_ids = [ex.example_id for ex in examples]

        # Compute statistics
        dataset.compute_statistics(examples)

        # Store dataset
        self.datasets[dataset.dataset_id] = dataset

        # Persist dataset (with examples for L01 bridge)
        l01_dataset_id = await self._persist_dataset(dataset, examples)
        if l01_dataset_id:
            # Store L01 ID for future reference
            dataset.metadata = dataset.metadata or {}
            dataset.metadata['l01_dataset_id'] = str(l01_dataset_id)

        logger.info(
            f"Created dataset {dataset.dataset_id} ({name}) v{dataset.version} "
            f"with {len(dataset.example_ids)} examples "
            f"(L01={'enabled' if l01_dataset_id else 'disabled'})"
        )

        return dataset

    async def _create_splits(
        self,
        examples: List[TrainingExample],
        split_ratios: Dict[str, float]
    ) -> Dict[str, List[str]]:
        """Create stratified train/validation/test splits.

        Args:
            examples: List of training examples
            split_ratios: Desired split ratios

        Returns:
            Dictionary mapping split names to example IDs
        """
        # Stratified split by domain and difficulty
        strata: Dict[tuple, List[TrainingExample]] = {}
        for ex in examples:
            # Bin difficulty into easy/medium/hard
            if ex.difficulty < 0.33:
                difficulty_bin = "easy"
            elif ex.difficulty < 0.66:
                difficulty_bin = "medium"
            else:
                difficulty_bin = "hard"

            key = (ex.domain, difficulty_bin)
            if key not in strata:
                strata[key] = []
            strata[key].append(ex)

        # Create splits for each stratum
        splits = {
            "train": [],
            "validation": [],
            "test": []
        }

        for stratum_key, stratum_examples in strata.items():
            # Shuffle stratum
            indices = np.random.permutation(len(stratum_examples))
            shuffled = [stratum_examples[i] for i in indices]

            # Split according to ratios
            train_size = int(len(shuffled) * split_ratios.get("train", 0.8))
            val_size = int(len(shuffled) * split_ratios.get("validation", 0.1))

            train_examples = shuffled[:train_size]
            val_examples = shuffled[train_size:train_size + val_size]
            test_examples = shuffled[train_size + val_size:]

            splits["train"].extend([ex.example_id for ex in train_examples])
            splits["validation"].extend([ex.example_id for ex in val_examples])
            splits["test"].extend([ex.example_id for ex in test_examples])

        logger.info(
            f"Created splits: train={len(splits['train'])}, "
            f"val={len(splits['validation'])}, test={len(splits['test'])}"
        )

        return splits

    async def add_examples(
        self,
        dataset_id: str,
        examples: List[TrainingExample]
    ) -> Dataset:
        """Add examples to existing dataset (creates new version).

        Args:
            dataset_id: Dataset identifier
            examples: New examples to add

        Returns:
            Updated dataset with new version

        Raises:
            LearningLayerException: If dataset not found
        """
        if dataset_id not in self.datasets:
            raise LearningLayerException(
                LearningErrorCode.E7200,
                f"Dataset not found: {dataset_id}"
            )

        logger.info(f"Adding {len(examples)} examples to dataset {dataset_id}")

        # Get current dataset
        current = self.datasets[dataset_id]

        # Create new version
        new_version = self._increment_version(current.version)

        # Combine examples (would need to fetch old examples in production)
        all_example_ids = current.example_ids + [ex.example_id for ex in examples]

        # Create new dataset version
        new_dataset = Dataset(
            name=current.name,
            version=new_version,
            example_ids=all_example_ids,
            description=current.description,
            tags=current.tags,
            split_ratios=current.split_ratios
        )

        # Re-create splits with all examples
        # In production, would fetch existing examples and combine
        new_dataset.splits = await self._create_splits(examples, current.split_ratios)

        # Compute statistics
        new_dataset.compute_statistics(examples)

        # Update lineage
        new_dataset.lineage.source_datasets = [dataset_id]

        # Store new version
        self.datasets[new_dataset.dataset_id] = new_dataset
        await self._persist_dataset(new_dataset)

        logger.info(f"Created dataset version {new_version} with {len(all_example_ids)} examples")

        return new_dataset

    async def get_dataset(self, dataset_id: str) -> Optional[Dataset]:
        """Get dataset by ID.

        Args:
            dataset_id: Dataset identifier

        Returns:
            Dataset or None if not found
        """
        return self.datasets.get(dataset_id)

    async def list_datasets(
        self,
        name_filter: Optional[str] = None,
        tag_filter: Optional[str] = None
    ) -> List[Dataset]:
        """List all datasets with optional filters.

        Args:
            name_filter: Filter by name substring
            tag_filter: Filter by tag

        Returns:
            List of matching datasets
        """
        datasets = list(self.datasets.values())

        if name_filter:
            datasets = [d for d in datasets if name_filter.lower() in d.name.lower()]

        if tag_filter:
            datasets = [d for d in datasets if tag_filter in d.tags]

        return datasets

    async def get_split_examples(
        self,
        dataset_id: str,
        split: DatasetSplit
    ) -> List[str]:
        """Get example IDs for a specific split.

        Args:
            dataset_id: Dataset identifier
            split: Split type

        Returns:
            List of example IDs

        Raises:
            LearningLayerException: If dataset not found
        """
        if dataset_id not in self.datasets:
            raise LearningLayerException(
                LearningErrorCode.E7200,
                f"Dataset not found: {dataset_id}"
            )

        dataset = self.datasets[dataset_id]
        return dataset.splits.get(split.value, [])

    async def validate_dataset(self, dataset_id: str) -> bool:
        """Validate dataset integrity.

        Args:
            dataset_id: Dataset identifier

        Returns:
            True if valid, False otherwise
        """
        if dataset_id not in self.datasets:
            return False

        dataset = self.datasets[dataset_id]
        return dataset.validate()

    async def _persist_dataset(
        self,
        dataset: Dataset,
        examples: Optional[List[TrainingExample]] = None
    ) -> Optional[UUID]:
        """Persist dataset metadata to storage.

        Args:
            dataset: Dataset to persist
            examples: Training examples to link to dataset (for L01 persistence)

        Returns:
            L01 dataset ID if persisted via bridge, None otherwise
        """
        l01_dataset_id = None

        # Try L01 Bridge first
        if self.l01_bridge and examples:
            try:
                l01_dataset_id = await self.l01_bridge.create_dataset(
                    dataset=dataset,
                    examples=examples
                )

                if l01_dataset_id:
                    logger.info(
                        f"Persisted dataset {dataset.dataset_id} to L01 as {l01_dataset_id}"
                    )
                    return l01_dataset_id

            except Exception as e:
                logger.warning(
                    f"Failed to persist dataset to L01, falling back to file storage: {e}"
                )

        # Fallback to file storage
        try:
            import os
            os.makedirs(self.storage_path, exist_ok=True)

            file_path = f"{self.storage_path}/{dataset.dataset_id}.json"
            with open(file_path, 'w') as f:
                json.dump(dataset.to_dict(), f, indent=2)

            logger.debug(f"Persisted dataset {dataset.dataset_id} to {file_path}")

        except Exception as e:
            logger.error(f"Failed to persist dataset to file storage: {e}")
            # Non-fatal - dataset still in memory

        return l01_dataset_id

    def _increment_version(self, version: str) -> str:
        """Increment semantic version.

        Args:
            version: Current version (e.g., "1.0.0")

        Returns:
            Incremented version (e.g., "1.0.1")
        """
        try:
            parts = version.split('.')
            parts[-1] = str(int(parts[-1]) + 1)
            return '.'.join(parts)
        except Exception:
            return "1.0.1"

    async def compute_dataset_statistics(
        self,
        dataset_id: str,
        examples: List[TrainingExample]
    ) -> DatasetStatistics:
        """Compute comprehensive dataset statistics.

        Args:
            dataset_id: Dataset identifier
            examples: List of training examples

        Returns:
            Dataset statistics
        """
        if dataset_id not in self.datasets:
            raise LearningLayerException(
                LearningErrorCode.E7200,
                f"Dataset not found: {dataset_id}"
            )

        dataset = self.datasets[dataset_id]
        return dataset.compute_statistics(examples)

    def get_statistics(self) -> Dict[str, Any]:
        """Get curator statistics.

        Returns:
            Statistics dictionary
        """
        return {
            'total_datasets': len(self.datasets),
            'total_examples': sum(len(d.example_ids) for d in self.datasets.values()),
            'datasets_by_name': {d.name: d.dataset_id for d in self.datasets.values()},
            'examples_filtered': self._examples_filtered,
            'duplicates_removed': self._duplicates_removed,
        }

    # ==================== Quality Filtering ====================

    async def filter_by_quality(
        self,
        examples: List[TrainingExample],
        thresholds: Optional[QualityThresholds] = None
    ) -> Tuple[List[TrainingExample], List[TrainingExample]]:
        """Filter examples by quality thresholds.

        Args:
            examples: List of training examples
            thresholds: Optional custom thresholds (uses defaults if not provided)

        Returns:
            Tuple of (passed_examples, filtered_examples)
        """
        thresholds = thresholds or self.quality_thresholds
        passed = []
        filtered = []

        for example in examples:
            if self._passes_quality_check(example, thresholds):
                passed.append(example)
            else:
                filtered.append(example)

        self._examples_filtered += len(filtered)

        logger.info(
            f"Quality filter: {len(passed)} passed, {len(filtered)} filtered "
            f"(of {len(examples)} total)"
        )

        return passed, filtered

    def _passes_quality_check(
        self,
        example: TrainingExample,
        thresholds: QualityThresholds
    ) -> bool:
        """Check if an example passes quality thresholds.

        Args:
            example: Training example to check
            thresholds: Quality thresholds

        Returns:
            True if passes all checks
        """
        # Input length check
        input_len = len(example.input_text) if hasattr(example, 'input_text') else 0
        if input_len < thresholds.min_input_length or input_len > thresholds.max_input_length:
            return False

        # Output length check
        output_len = len(example.output_text) if hasattr(example, 'output_text') else 0
        if output_len < thresholds.min_output_length or output_len > thresholds.max_output_length:
            return False

        # Difficulty check
        if hasattr(example, 'difficulty'):
            if example.difficulty < thresholds.min_difficulty or example.difficulty > thresholds.max_difficulty:
                return False

        # Quality score check
        if hasattr(example, 'quality_score'):
            if example.quality_score < thresholds.min_quality_score:
                return False

        # Required fields check
        if thresholds.require_metadata and thresholds.required_fields:
            metadata = getattr(example, 'metadata', {}) or {}
            for field in thresholds.required_fields:
                if field not in metadata:
                    return False

        return True

    def update_quality_thresholds(
        self,
        thresholds: QualityThresholds
    ) -> None:
        """Update quality thresholds.

        Args:
            thresholds: New quality thresholds
        """
        self.quality_thresholds = thresholds
        logger.info(f"Updated quality thresholds: {thresholds}")

    # ==================== Semantic Deduplication ====================

    async def deduplicate_semantic(
        self,
        examples: List[TrainingExample],
        similarity_threshold: Optional[float] = None
    ) -> DeduplicationResult:
        """Deduplicate examples using semantic similarity.

        Uses embeddings to find semantically similar examples and
        removes duplicates based on similarity threshold.

        Args:
            examples: List of training examples
            similarity_threshold: Similarity threshold (0-1)

        Returns:
            DeduplicationResult with deduplicated examples and stats
        """
        threshold = similarity_threshold or self.quality_thresholds.dedupe_similarity_threshold

        if not examples:
            return DeduplicationResult(
                original_count=0,
                deduplicated_count=0,
                duplicates_removed=0
            )

        logger.info(
            f"Starting semantic deduplication: {len(examples)} examples, "
            f"threshold={threshold}"
        )

        # Get embeddings for all examples
        embeddings = await self._get_embeddings_batch(examples)

        if embeddings is None:
            # Fall back to hash-based deduplication
            return await self.deduplicate_hash(examples)

        # Find duplicates using cosine similarity
        duplicate_groups = []
        kept_indices = set(range(len(examples)))
        removed_indices = set()

        for i in range(len(examples)):
            if i in removed_indices:
                continue

            group = [examples[i].example_id]

            for j in range(i + 1, len(examples)):
                if j in removed_indices:
                    continue

                # Calculate cosine similarity
                similarity = self._cosine_similarity(embeddings[i], embeddings[j])

                if similarity >= threshold:
                    group.append(examples[j].example_id)
                    removed_indices.add(j)
                    kept_indices.discard(j)

            if len(group) > 1:
                duplicate_groups.append(group)

        # Build deduplicated list
        deduplicated = [examples[i] for i in sorted(kept_indices)]

        self._duplicates_removed += len(removed_indices)

        result = DeduplicationResult(
            original_count=len(examples),
            deduplicated_count=len(deduplicated),
            duplicates_removed=len(removed_indices),
            duplicate_groups=duplicate_groups
        )

        logger.info(
            f"Semantic deduplication complete: "
            f"{result.duplicates_removed} duplicates removed, "
            f"{len(duplicate_groups)} duplicate groups found"
        )

        return result

    async def deduplicate_hash(
        self,
        examples: List[TrainingExample]
    ) -> DeduplicationResult:
        """Deduplicate examples using hash-based comparison.

        Fallback when embedding service is not available.

        Args:
            examples: List of training examples

        Returns:
            DeduplicationResult
        """
        seen_hashes: Dict[str, str] = {}
        deduplicated = []
        duplicate_groups: Dict[str, List[str]] = {}

        for example in examples:
            # Create hash from input + output
            content = f"{getattr(example, 'input_text', '')}:{getattr(example, 'output_text', '')}"
            content_hash = hashlib.sha256(content.encode()).hexdigest()[:16]

            if content_hash in seen_hashes:
                # Duplicate found
                original_id = seen_hashes[content_hash]
                if original_id not in duplicate_groups:
                    duplicate_groups[original_id] = [original_id]
                duplicate_groups[original_id].append(example.example_id)
            else:
                seen_hashes[content_hash] = example.example_id
                deduplicated.append(example)

        duplicates_removed = len(examples) - len(deduplicated)
        self._duplicates_removed += duplicates_removed

        return DeduplicationResult(
            original_count=len(examples),
            deduplicated_count=len(deduplicated),
            duplicates_removed=duplicates_removed,
            duplicate_groups=list(duplicate_groups.values())
        )

    async def _get_embeddings_batch(
        self,
        examples: List[TrainingExample]
    ) -> Optional[np.ndarray]:
        """Get embeddings for a batch of examples.

        Args:
            examples: List of training examples

        Returns:
            Numpy array of embeddings or None if service unavailable
        """
        if not self.embedding_service:
            return None

        try:
            texts = [
                f"{getattr(ex, 'input_text', '')} {getattr(ex, 'output_text', '')}"
                for ex in examples
            ]

            # Check cache first
            embeddings = []
            texts_to_embed = []
            indices_to_embed = []

            for i, text in enumerate(texts):
                text_hash = hashlib.sha256(text.encode()).hexdigest()
                if text_hash in self._embedding_cache:
                    embeddings.append((i, self._embedding_cache[text_hash]))
                else:
                    texts_to_embed.append(text)
                    indices_to_embed.append(i)

            # Embed uncached texts
            if texts_to_embed:
                new_embeddings = await self.embedding_service.embed_batch(texts_to_embed)

                for idx, text, emb in zip(indices_to_embed, texts_to_embed, new_embeddings):
                    text_hash = hashlib.sha256(text.encode()).hexdigest()
                    self._embedding_cache[text_hash] = emb
                    embeddings.append((idx, emb))

            # Sort by original index and extract embeddings
            embeddings.sort(key=lambda x: x[0])
            return np.array([emb for _, emb in embeddings])

        except Exception as e:
            logger.warning(f"Failed to get embeddings: {e}")
            return None

    def _cosine_similarity(
        self,
        vec1: np.ndarray,
        vec2: np.ndarray
    ) -> float:
        """Calculate cosine similarity between two vectors.

        Args:
            vec1: First vector
            vec2: Second vector

        Returns:
            Cosine similarity (0-1)
        """
        dot_product = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)

        if norm1 == 0 or norm2 == 0:
            return 0.0

        return float(dot_product / (norm1 * norm2))

    # ==================== Dataset Curation Pipeline ====================

    async def curate_dataset(
        self,
        name: str,
        examples: List[TrainingExample],
        deduplicate: bool = True,
        filter_quality: bool = True,
        split_ratios: Optional[Dict[str, float]] = None,
        description: str = "",
        tags: Optional[List[str]] = None
    ) -> Tuple[Dataset, Dict[str, Any]]:
        """Full curation pipeline: filter, deduplicate, split.

        Args:
            name: Dataset name
            examples: Raw training examples
            deduplicate: Enable deduplication
            filter_quality: Enable quality filtering
            split_ratios: Custom split ratios
            description: Dataset description
            tags: Optional tags

        Returns:
            Tuple of (Dataset, curation_report)
        """
        report = {
            "original_count": len(examples),
            "quality_filtered": 0,
            "duplicates_removed": 0,
            "final_count": 0,
        }

        current_examples = examples

        # Quality filtering
        if filter_quality:
            passed, filtered = await self.filter_by_quality(current_examples)
            report["quality_filtered"] = len(filtered)
            current_examples = passed

        # Deduplication
        if deduplicate:
            dedupe_result = await self.deduplicate_semantic(current_examples)
            report["duplicates_removed"] = dedupe_result.duplicates_removed
            report["duplicate_groups"] = len(dedupe_result.duplicate_groups)
            # Get deduplicated examples
            kept_ids = set(
                ex.example_id for ex in current_examples
            ) - set(
                id for group in dedupe_result.duplicate_groups
                for id in group[1:]  # Keep first, remove rest
            )
            current_examples = [
                ex for ex in current_examples
                if ex.example_id in kept_ids
            ]

        report["final_count"] = len(current_examples)

        # Create dataset
        dataset = await self.create_dataset(
            name=name,
            examples=current_examples,
            split_ratios=split_ratios,
            description=description,
            tags=tags
        )

        logger.info(
            f"Curation complete: {name} - "
            f"{report['original_count']} -> {report['final_count']} examples"
        )

        return dataset, report
