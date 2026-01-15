"""L01 Data Layer - Dataset Service

Service for managing training datasets with train/val/test splits.
Supports L07 Learning Layer integration.
"""

import asyncpg
import json
import logging
from typing import List, Optional, Dict, Any
from uuid import UUID

from ..models.dataset import (
    Dataset,
    DatasetCreate,
    DatasetUpdate,
    DatasetExampleLink,
    DatasetSplit,
)
from ..models.error_codes import L01ErrorCode
from ..redis_client import RedisClient

logger = logging.getLogger(__name__)


class DatasetService:
    """Service for dataset CRUD operations and split management."""

    def __init__(self, db_pool: asyncpg.Pool, redis_client: Optional[RedisClient] = None):
        """Initialize service.

        Args:
            db_pool: Database connection pool
            redis_client: Optional Redis client for event publishing
        """
        self.db_pool = db_pool
        self.redis_client = redis_client

    def _row_to_dataset(self, row) -> Dataset:
        """Convert database row to Dataset model.

        Args:
            row: Database row

        Returns:
            Dataset instance
        """
        dataset_dict = dict(row)

        # Parse JSONB fields
        for field in ['split_ratios', 'lineage', 'statistics']:
            if field in dataset_dict and isinstance(dataset_dict[field], str):
                dataset_dict[field] = json.loads(dataset_dict[field])

        # Parse array field
        if 'tags' in dataset_dict and isinstance(dataset_dict['tags'], str):
            dataset_dict['tags'] = json.loads(dataset_dict['tags'])

        return Dataset(**dataset_dict)

    async def create_dataset(self, dataset_data: DatasetCreate) -> Dataset:
        """Create new dataset.

        Args:
            dataset_data: Dataset creation data

        Returns:
            Created dataset

        Raises:
            Exception: If creation fails
        """
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO datasets (
                    name, version, description, tags,
                    split_ratios, lineage, statistics, created_by
                )
                VALUES ($1, $2, $3, $4, $5::jsonb, $6::jsonb, $7::jsonb, $8)
                RETURNING *
                """,
                dataset_data.name,
                dataset_data.version,
                dataset_data.description,
                dataset_data.tags,
                json.dumps(dataset_data.split_ratios),
                json.dumps({
                    "source_datasets": dataset_data.source_datasets,
                    "extraction_jobs": dataset_data.extraction_jobs,
                    "filter_configs": dataset_data.filter_configs,
                    "transformations": dataset_data.transformations,
                }),
                json.dumps(dataset_data.statistics),
                dataset_data.created_by,
            )

        dataset = self._row_to_dataset(row)

        # Publish event
        if self.redis_client:
            await self.redis_client.publish_event(
                event_type="dataset.created",
                aggregate_type="dataset",
                aggregate_id=str(dataset.id),
                payload={
                    "name": dataset.name,
                    "version": dataset.version,
                    "created_by": dataset.created_by,
                },
            )

        logger.info(f"Created dataset {dataset.id} ({dataset.name}) v{dataset.version}")
        return dataset

    async def get_dataset(self, dataset_id: UUID) -> Optional[Dataset]:
        """Get dataset by ID.

        Args:
            dataset_id: Dataset identifier

        Returns:
            Dataset or None if not found
        """
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM datasets WHERE id = $1",
                dataset_id
            )

        if not row:
            return None

        return self._row_to_dataset(row)

    async def update_dataset(
        self,
        dataset_id: UUID,
        update_data: DatasetUpdate
    ) -> Optional[Dataset]:
        """Update dataset metadata.

        Args:
            dataset_id: Dataset identifier
            update_data: Update data

        Returns:
            Updated dataset or None if not found
        """
        updates = []
        values = []
        param_idx = 1

        if update_data.description is not None:
            updates.append(f"description = ${param_idx}")
            values.append(update_data.description)
            param_idx += 1

        if update_data.tags is not None:
            updates.append(f"tags = ${param_idx}")
            values.append(update_data.tags)
            param_idx += 1

        if update_data.statistics is not None:
            updates.append(f"statistics = ${param_idx}::jsonb")
            values.append(json.dumps(update_data.statistics))
            param_idx += 1

        if not updates:
            return await self.get_dataset(dataset_id)

        updates.append(f"updated_at = NOW()")
        values.append(dataset_id)

        query = f"""
            UPDATE datasets
            SET {', '.join(updates)}
            WHERE id = ${param_idx}
            RETURNING *
        """

        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow(query, *values)

        if not row:
            return None

        dataset = self._row_to_dataset(row)

        # Publish event
        if self.redis_client:
            await self.redis_client.publish_event(
                event_type="dataset.updated",
                aggregate_type="dataset",
                aggregate_id=str(dataset.id),
                payload={"updated_fields": list(update_data.dict(exclude_unset=True).keys())},
            )

        logger.info(f"Updated dataset {dataset_id}")
        return dataset

    async def list_datasets(
        self,
        name_filter: Optional[str] = None,
        tag_filter: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dataset]:
        """List datasets with optional filters.

        Args:
            name_filter: Filter by name substring
            tag_filter: Filter by tag
            limit: Maximum results
            offset: Results offset

        Returns:
            List of datasets
        """
        conditions = []
        values = []
        param_idx = 1

        if name_filter:
            conditions.append(f"name ILIKE ${param_idx}")
            values.append(f"%{name_filter}%")
            param_idx += 1

        if tag_filter:
            conditions.append(f"${param_idx} = ANY(tags)")
            values.append(tag_filter)
            param_idx += 1

        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

        query = f"""
            SELECT * FROM datasets
            {where_clause}
            ORDER BY created_at DESC
            LIMIT ${param_idx} OFFSET ${param_idx + 1}
        """

        values.extend([limit, offset])

        async with self.db_pool.acquire() as conn:
            rows = await conn.fetch(query, *values)

        return [self._row_to_dataset(row) for row in rows]

    async def delete_dataset(self, dataset_id: UUID) -> bool:
        """Delete dataset (cascades to dataset_examples).

        Args:
            dataset_id: Dataset identifier

        Returns:
            True if deleted, False if not found
        """
        async with self.db_pool.acquire() as conn:
            result = await conn.execute(
                "DELETE FROM datasets WHERE id = $1",
                dataset_id
            )

        deleted = result == "DELETE 1"

        if deleted and self.redis_client:
            await self.redis_client.publish_event(
                event_type="dataset.deleted",
                aggregate_type="dataset",
                aggregate_id=str(dataset_id),
                payload={},
            )

        logger.info(f"Deleted dataset {dataset_id}")
        return deleted

    async def add_example_to_dataset(
        self,
        dataset_id: UUID,
        example_id: UUID,
        split: DatasetSplit
    ) -> DatasetExampleLink:
        """Add training example to dataset with split assignment.

        Args:
            dataset_id: Dataset identifier
            example_id: Training example identifier
            split: Dataset split (train/validation/test)

        Returns:
            Created dataset-example link

        Raises:
            Exception: If link creation fails
        """
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO dataset_examples (dataset_id, example_id, split)
                VALUES ($1, $2, $3)
                ON CONFLICT (dataset_id, example_id)
                DO UPDATE SET split = $3
                RETURNING *
                """,
                dataset_id,
                example_id,
                split.value,
            )

        link = DatasetExampleLink(**dict(row))

        # Publish event
        if self.redis_client:
            await self.redis_client.publish_event(
                event_type="dataset.example_added",
                aggregate_type="dataset",
                aggregate_id=str(dataset_id),
                payload={
                    "example_id": str(example_id),
                    "split": split.value,
                },
            )

        logger.info(f"Added example {example_id} to dataset {dataset_id} (split: {split.value})")
        return link

    async def remove_example_from_dataset(
        self,
        dataset_id: UUID,
        example_id: UUID
    ) -> bool:
        """Remove training example from dataset.

        Args:
            dataset_id: Dataset identifier
            example_id: Training example identifier

        Returns:
            True if removed, False if not found
        """
        async with self.db_pool.acquire() as conn:
            result = await conn.execute(
                """
                DELETE FROM dataset_examples
                WHERE dataset_id = $1 AND example_id = $2
                """,
                dataset_id,
                example_id
            )

        removed = result == "DELETE 1"

        if removed and self.redis_client:
            await self.redis_client.publish_event(
                event_type="dataset.example_removed",
                aggregate_type="dataset",
                aggregate_id=str(dataset_id),
                payload={"example_id": str(example_id)},
            )

        return removed

    async def get_dataset_examples(
        self,
        dataset_id: UUID,
        split: Optional[DatasetSplit] = None
    ) -> List[UUID]:
        """Get example IDs for a dataset, optionally filtered by split.

        Args:
            dataset_id: Dataset identifier
            split: Optional split filter

        Returns:
            List of training example IDs
        """
        if split:
            query = """
                SELECT example_id FROM dataset_examples
                WHERE dataset_id = $1 AND split = $2
                ORDER BY created_at
            """
            params = [dataset_id, split.value]
        else:
            query = """
                SELECT example_id FROM dataset_examples
                WHERE dataset_id = $1
                ORDER BY created_at
            """
            params = [dataset_id]

        async with self.db_pool.acquire() as conn:
            rows = await conn.fetch(query, *params)

        return [row["example_id"] for row in rows]

    async def get_dataset_split_counts(self, dataset_id: UUID) -> Dict[str, int]:
        """Get count of examples in each split.

        Args:
            dataset_id: Dataset identifier

        Returns:
            Dictionary mapping split name to count
        """
        async with self.db_pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT split, COUNT(*) as count
                FROM dataset_examples
                WHERE dataset_id = $1
                GROUP BY split
                """,
                dataset_id
            )

        return {row["split"]: row["count"] for row in rows}

    async def get_statistics(self) -> Dict[str, Any]:
        """Get dataset service statistics.

        Returns:
            Statistics dictionary
        """
        async with self.db_pool.acquire() as conn:
            stats = await conn.fetchrow(
                """
                SELECT
                    COUNT(*) as total_datasets,
                    COUNT(DISTINCT name) as unique_names
                FROM datasets
                """
            )

            example_stats = await conn.fetchrow(
                """
                SELECT
                    COUNT(*) as total_links,
                    COUNT(DISTINCT dataset_id) as datasets_with_examples,
                    COUNT(DISTINCT example_id) as unique_examples
                FROM dataset_examples
                """
            )

        return {
            "total_datasets": stats["total_datasets"],
            "unique_names": stats["unique_names"],
            "total_links": example_stats["total_links"],
            "datasets_with_examples": example_stats["datasets_with_examples"],
            "unique_examples_in_datasets": example_stats["unique_examples"],
        }
