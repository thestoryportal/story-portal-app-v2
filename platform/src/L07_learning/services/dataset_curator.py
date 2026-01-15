"""L07 Learning Layer - Dataset Curator Service.

Manages dataset versions, creates train/val/test splits, and computes statistics.
"""

import logging
import numpy as np
from typing import List, Dict, Any, Optional
from datetime import datetime
import json

from ..models.dataset import Dataset, DatasetSplit, DatasetVersion, DatasetLineage, DatasetStatistics
from ..models.training_example import TrainingExample
from ..models.error_codes import LearningErrorCode, LearningLayerException

logger = logging.getLogger(__name__)


class DatasetCurator:
    """Curate and version training datasets.

    This service creates versioned datasets with train/validation/test splits,
    computes statistics, and handles incremental updates.
    """

    def __init__(self, storage_path: str = "/tmp/l07_datasets"):
        """Initialize Dataset Curator.

        Args:
            storage_path: Path to store dataset metadata
        """
        self.storage_path = storage_path
        self.datasets: Dict[str, Dataset] = {}

        logger.info(f"Initialized DatasetCurator with storage at {storage_path}")

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
        await self._persist_dataset(dataset)

        logger.info(
            f"Created dataset {dataset.dataset_id} ({name}) v{dataset.version} "
            f"with {len(dataset.example_ids)} examples"
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

    async def _persist_dataset(self, dataset: Dataset) -> None:
        """Persist dataset metadata to storage.

        Args:
            dataset: Dataset to persist
        """
        try:
            import os
            os.makedirs(self.storage_path, exist_ok=True)

            file_path = f"{self.storage_path}/{dataset.dataset_id}.json"
            with open(file_path, 'w') as f:
                json.dump(dataset.to_dict(), f, indent=2)

            logger.debug(f"Persisted dataset {dataset.dataset_id} to {file_path}")

        except Exception as e:
            logger.error(f"Failed to persist dataset: {e}")
            # Non-fatal - dataset still in memory

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
            'datasets_by_name': {d.name: d.dataset_id for d in self.datasets.values()}
        }
