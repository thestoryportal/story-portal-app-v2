"""L07 Learning Layer - L01 Data Layer Bridge

Bridge between L07 Learning and L01 Data Layer for persistent training data storage.

This bridge replaces temporary file storage (/tmp/l07_learning) with persistent
PostgreSQL storage in L01. Training examples and datasets are stored centrally
for cross-layer access and long-term retention.

Features:
- Event subscription for execution events
- Graceful fallback when L01 unavailable
- Health checking and automatic recovery
- Metrics tracking
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional, Callable, Awaitable
from uuid import UUID
from collections import deque

from shared.clients import L01Client
from ..models.training_example import TrainingExample, ExampleSource, TaskType
from ..models.dataset import Dataset, DatasetSplit


logger = logging.getLogger(__name__)


class L07Bridge:
    """
    Bridge between L07 Learning Layer and L01 Data Layer.

    Responsibilities:
    - Persist training examples to L01 instead of temporary files
    - Store datasets with versioning and splits in L01
    - Maintain dataset-example relationships
    - Publish learning events via L01 event stream
    """

    def __init__(
        self,
        l01_base_url: str = "http://localhost:8002",
        fallback_capacity: int = 10000,
        health_check_interval: float = 30.0,
    ):
        """Initialize L07 bridge.

        Args:
            l01_base_url: Base URL for L01 Data Layer API
            fallback_capacity: Maximum items in fallback queue
            health_check_interval: Seconds between health checks
        """
        self.l01_client = L01Client(base_url=l01_base_url)
        self.enabled = True
        self._l01_available = True
        self._health_check_interval = health_check_interval

        # Fallback storage for when L01 is unavailable
        self._fallback_storage: deque = deque(maxlen=fallback_capacity)

        # Event subscriptions
        self._subscriptions: Dict[str, List[Callable[[Dict], Awaitable[None]]]] = {}

        # Metrics
        self._total_synced = 0
        self._total_stored = 0
        self._total_failed = 0

        logger.info(f"L07Bridge initialized with base_url={l01_base_url}")

    async def initialize(self) -> None:
        """Initialize bridge (async setup if needed)."""
        logger.info("L07Bridge initialized")

    async def store_training_example(
        self,
        example: TrainingExample
    ) -> Optional[UUID]:
        """Store training example in L01 with fallback support.

        Args:
            example: TrainingExample instance

        Returns:
            L01 example ID or None on failure
        """
        if not self.enabled:
            return None

        # If L01 is not available, use fallback storage
        if not self._l01_available:
            self._fallback_storage.append({
                "type": "training_example",
                "data": example
            })
            logger.warning(
                f"L01 unavailable, stored example {example.example_id} in fallback"
            )
            return None

        try:
            l01_example_id = await self._store_example_to_l01(example)

            if l01_example_id:
                self._total_stored += 1
                logger.info(
                    f"Stored training example {example.example_id} "
                    f"in L01 as {l01_example_id}"
                )
                return l01_example_id
            else:
                # L01 call failed, add to fallback
                self._fallback_storage.append({
                    "type": "training_example",
                    "data": example
                })
                self._total_failed += 1
                return None

        except Exception as e:
            logger.error(f"Failed to store training example in L01: {e}")
            # Add to fallback queue
            self._fallback_storage.append({
                "type": "training_example",
                "data": example
            })
            self._total_failed += 1
            return None

    async def get_training_example(
        self,
        l01_example_id: UUID
    ) -> Optional[TrainingExample]:
        """Retrieve training example from L01.

        Args:
            l01_example_id: L01 example identifier

        Returns:
            TrainingExample instance or None if not found
        """
        if not self.enabled:
            return None

        try:
            l01_example = await self.l01_client.get_training_example(l01_example_id)

            # Map L01 format back to L07 TrainingExample
            example = TrainingExample(
                example_id=l01_example["id"],
                execution_id=l01_example.get("execution_id"),
                task_id=l01_example.get("task_id"),
                agent_id=l01_example.get("agent_id"),
                source_type=ExampleSource(l01_example["source_type"]),
                source_trace_hash=l01_example.get("source_trace_hash"),
                input_text=l01_example["input_text"],
                input_structured=l01_example.get("input_structured", {}),
                output_text=l01_example.get("output_text", ""),
                expected_actions=l01_example.get("expected_actions", []),
                final_answer=l01_example.get("final_answer", ""),
                quality_score=l01_example["quality_score"],
                confidence=l01_example["confidence"],
                labels=l01_example.get("labels", []),
                domain=l01_example["domain"],
                task_type=TaskType(l01_example["task_type"]),
                difficulty=l01_example["difficulty"],
                metadata=l01_example.get("metadata", {}),
                extracted_by=l01_example.get("extracted_by", "L07 TrainingDataExtractor"),
            )

            return example

        except Exception as e:
            logger.error(f"Failed to retrieve training example from L01: {e}")
            return None

    async def list_training_examples(
        self,
        agent_id: Optional[UUID] = None,
        domain: Optional[str] = None,
        min_quality: Optional[float] = None,
        limit: int = 100
    ) -> List[TrainingExample]:
        """List training examples from L01 with filters.

        Args:
            agent_id: Filter by agent ID
            domain: Filter by domain
            min_quality: Minimum quality score
            limit: Maximum results

        Returns:
            List of TrainingExample instances
        """
        if not self.enabled:
            return []

        try:
            l01_examples = await self.l01_client.list_training_examples(
                agent_id=agent_id,
                domain=domain,
                min_quality=min_quality,
                limit=limit
            )

            examples = []
            for l01_ex in l01_examples:
                example = TrainingExample(
                    example_id=l01_ex["id"],
                    execution_id=l01_ex.get("execution_id"),
                    task_id=l01_ex.get("task_id"),
                    agent_id=l01_ex.get("agent_id"),
                    source_type=ExampleSource(l01_ex["source_type"]),
                    input_text=l01_ex["input_text"],
                    output_text=l01_ex.get("output_text", ""),
                    quality_score=l01_ex["quality_score"],
                    confidence=l01_ex["confidence"],
                    domain=l01_ex["domain"],
                    task_type=TaskType(l01_ex["task_type"]),
                    difficulty=l01_ex["difficulty"],
                    labels=l01_ex.get("labels", []),
                    metadata=l01_ex.get("metadata", {}),
                )
                examples.append(example)

            logger.info(f"Retrieved {len(examples)} training examples from L01")
            return examples

        except Exception as e:
            logger.error(f"Failed to list training examples from L01: {e}")
            return []

    async def create_dataset(
        self,
        dataset: Dataset,
        examples: List[TrainingExample]
    ) -> Optional[UUID]:
        """Create dataset in L01 with training examples.

        Args:
            dataset: Dataset instance with metadata
            examples: List of training examples to include

        Returns:
            L01 dataset ID or None on failure
        """
        if not self.enabled:
            return None

        try:
            # Create dataset in L01
            l01_dataset = await self.l01_client.create_dataset(
                name=dataset.name,
                version=dataset.version,
                description=dataset.description,
                tags=dataset.tags,
                split_ratios=dataset.split_ratios,
                statistics=dataset.statistics.to_dict() if dataset.statistics else {}
            )

            l01_dataset_id = UUID(l01_dataset["id"])
            logger.info(f"Created dataset {dataset.name} in L01 as {l01_dataset_id}")

            # Store training examples and link to dataset
            for example in examples:
                # Store example if not already stored
                l01_example_id = await self.store_training_example(example)

                if l01_example_id:
                    # Determine split for this example
                    split = self._get_example_split(dataset, example.example_id)

                    # Link example to dataset
                    await self.l01_client.add_example_to_dataset(
                        dataset_id=l01_dataset_id,
                        example_id=l01_example_id,
                        split=split
                    )

            logger.info(f"Linked {len(examples)} examples to dataset {l01_dataset_id}")
            return l01_dataset_id

        except Exception as e:
            logger.error(f"Failed to create dataset in L01: {e}")
            return None

    async def get_dataset(
        self,
        l01_dataset_id: UUID
    ) -> Optional[Dataset]:
        """Retrieve dataset from L01.

        Args:
            l01_dataset_id: L01 dataset identifier

        Returns:
            Dataset instance or None if not found
        """
        if not self.enabled:
            return None

        try:
            l01_dataset = await self.l01_client.get_dataset(l01_dataset_id)

            # Map L01 format back to L07 Dataset
            dataset = Dataset(
                dataset_id=l01_dataset["id"],
                name=l01_dataset["name"],
                version=l01_dataset["version"],
                description=l01_dataset.get("description", ""),
                tags=l01_dataset.get("tags", []),
                split_ratios=l01_dataset.get("split_ratios", {"train": 0.8, "validation": 0.1, "test": 0.1}),
                created_by=l01_dataset.get("created_by", "L07 DatasetCurator"),
            )

            # Get example IDs for each split
            example_ids = await self.l01_client.get_dataset_examples(l01_dataset_id)
            dataset.example_ids = [str(eid) for eid in example_ids]

            # Get split counts
            split_counts = await self.l01_client.get_dataset_split_counts(l01_dataset_id)

            # Populate splits dict
            for split_name in ["train", "validation", "test"]:
                split_examples = await self.l01_client.get_dataset_examples(
                    l01_dataset_id,
                    split=split_name
                )
                dataset.splits[split_name] = [str(eid) for eid in split_examples]

            logger.info(f"Retrieved dataset {dataset.name} from L01")
            return dataset

        except Exception as e:
            logger.error(f"Failed to retrieve dataset from L01: {e}")
            return None

    async def list_datasets(
        self,
        name_filter: Optional[str] = None,
        tag_filter: Optional[str] = None,
        limit: int = 100
    ) -> List[Dataset]:
        """List datasets from L01 with filters.

        Args:
            name_filter: Filter by name substring
            tag_filter: Filter by tag
            limit: Maximum results

        Returns:
            List of Dataset instances
        """
        if not self.enabled:
            return []

        try:
            l01_datasets = await self.l01_client.list_datasets(
                name_filter=name_filter,
                tag_filter=tag_filter,
                limit=limit
            )

            datasets = []
            for l01_ds in l01_datasets:
                dataset = Dataset(
                    dataset_id=l01_ds["id"],
                    name=l01_ds["name"],
                    version=l01_ds["version"],
                    description=l01_ds.get("description", ""),
                    tags=l01_ds.get("tags", []),
                    created_by=l01_ds.get("created_by", "L07 DatasetCurator"),
                )
                datasets.append(dataset)

            logger.info(f"Retrieved {len(datasets)} datasets from L01")
            return datasets

        except Exception as e:
            logger.error(f"Failed to list datasets from L01: {e}")
            return []

    def _get_example_split(self, dataset: Dataset, example_id: str) -> str:
        """Determine which split an example belongs to.

        Args:
            dataset: Dataset instance
            example_id: Example identifier

        Returns:
            Split name ('train', 'validation', or 'test')
        """
        for split_name, split_example_ids in dataset.splits.items():
            if example_id in split_example_ids:
                return split_name

        # Default to train if not found in any split
        return "train"

    # ==================== Event Subscription ====================

    async def subscribe_to_events(
        self,
        event_types: List[str],
        callback: Callable[[Dict], Awaitable[None]]
    ) -> None:
        """Subscribe to L01 events.

        Args:
            event_types: List of event types to subscribe to
            callback: Async callback function for events
        """
        for event_type in event_types:
            if event_type not in self._subscriptions:
                self._subscriptions[event_type] = []
            self._subscriptions[event_type].append(callback)
            logger.info(f"Subscribed to event type: {event_type}")

    async def _dispatch_event(self, event: Dict[str, Any]) -> None:
        """Dispatch event to registered callbacks.

        Args:
            event: Event data with 'type' and 'data' keys
        """
        event_type = event.get("type", "")
        callbacks = self._subscriptions.get(event_type, [])

        for callback in callbacks:
            try:
                await callback(event)
            except Exception as e:
                logger.error(f"Error in event callback: {e}")

    async def unsubscribe_from_events(self, event_types: List[str]) -> None:
        """Unsubscribe from event types.

        Args:
            event_types: Event types to unsubscribe from
        """
        for event_type in event_types:
            self._subscriptions.pop(event_type, None)
            logger.info(f"Unsubscribed from event type: {event_type}")

    # ==================== Fallback Storage ====================

    def fallback_queue_size(self) -> int:
        """Get size of fallback queue.

        Returns:
            Number of items in fallback queue
        """
        return len(self._fallback_storage)

    async def sync_fallback(self) -> int:
        """Sync fallback storage to L01.

        Returns:
            Number of items synced
        """
        if not self._l01_available:
            return 0

        synced = 0
        while self._fallback_storage:
            item = self._fallback_storage.popleft()
            item_type = item.get("type")

            try:
                if item_type == "training_example":
                    example = item.get("data")
                    await self._store_example_to_l01(example)
                    synced += 1
                elif item_type == "dataset":
                    dataset, examples = item.get("data")
                    await self._store_dataset_to_l01(dataset, examples)
                    synced += 1
            except Exception as e:
                # Put back in queue
                self._fallback_storage.appendleft(item)
                logger.error(f"Failed to sync from fallback: {e}")
                break

        self._total_synced += synced
        if synced > 0:
            logger.info(f"Synced {synced} items from fallback to L01")

        return synced

    async def _store_example_to_l01(self, example: TrainingExample) -> Optional[UUID]:
        """Internal method to store example to L01.

        Args:
            example: Training example

        Returns:
            L01 example ID or None
        """
        try:
            l01_example = await self.l01_client.create_training_example(
                input_text=example.input_text,
                execution_id=example.execution_id,
                task_id=example.task_id,
                agent_id=UUID(example.agent_id) if example.agent_id else None,
                source_type=example.source_type.value,
                output_text=example.output_text,
                expected_actions=example.expected_actions,
                final_answer=example.final_answer,
                quality_score=example.quality_score,
                confidence=example.confidence,
                labels=example.labels,
                domain=example.domain,
                task_type=example.task_type.value,
                difficulty=example.difficulty,
                metadata=example.metadata
            )
            return UUID(l01_example["id"])
        except Exception as e:
            logger.error(f"Failed to store to L01: {e}")
            return None

    async def _store_dataset_to_l01(
        self,
        dataset: Dataset,
        examples: List[TrainingExample]
    ) -> Optional[UUID]:
        """Internal method to store dataset to L01.

        Args:
            dataset: Dataset
            examples: Training examples

        Returns:
            L01 dataset ID or None
        """
        try:
            l01_dataset = await self.l01_client.create_dataset(
                name=dataset.name,
                version=dataset.version,
                description=dataset.description,
                tags=dataset.tags,
                split_ratios=dataset.split_ratios,
                statistics=dataset.statistics.to_dict() if dataset.statistics else {}
            )
            return UUID(l01_dataset["id"])
        except Exception as e:
            logger.error(f"Failed to store dataset to L01: {e}")
            return None

    # ==================== Health Check ====================

    async def check_l01_health(self) -> bool:
        """Check if L01 is healthy and available.

        Returns:
            True if L01 is available
        """
        try:
            result = await self.l01_client.health_check()
            self._l01_available = bool(result)
        except Exception as e:
            logger.warning(f"L01 health check failed: {e}")
            self._l01_available = False

        # Trigger sync if just became available
        if self._l01_available and self.fallback_queue_size() > 0:
            await self.sync_fallback()

        return self._l01_available

    # ==================== Metrics ====================

    def get_metrics(self) -> Dict[str, Any]:
        """Get bridge metrics.

        Returns:
            Dictionary of metrics
        """
        return {
            "enabled": self.enabled,
            "l01_available": self._l01_available,
            "fallback_queue_size": self.fallback_queue_size(),
            "total_synced": self._total_synced,
            "total_stored": self._total_stored,
            "total_failed": self._total_failed,
            "subscription_count": sum(len(v) for v in self._subscriptions.values()),
        }

    # ==================== Cleanup ====================

    async def cleanup(self) -> None:
        """Cleanup resources."""
        # Try to sync any remaining fallback items
        if self._l01_available:
            await self.sync_fallback()

        await self.l01_client.close()
        logger.info("L07Bridge cleanup complete")
