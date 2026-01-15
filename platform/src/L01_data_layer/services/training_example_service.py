"""L01 Data Layer - Training Example Service

Service for managing training examples (CRUD operations and queries).
Supports L07 Learning Layer integration.
"""

import asyncpg
import json
import logging
from typing import List, Optional, Dict, Any
from uuid import UUID

from ..models.training_example import (
    TrainingExample,
    TrainingExampleCreate,
    TrainingExampleUpdate,
    ExampleSource,
    TaskType,
)
from ..models.error_codes import L01ErrorCode
from ..redis_client import RedisClient

logger = logging.getLogger(__name__)


class TrainingExampleService:
    """Service for training example CRUD operations."""

    def __init__(self, db_pool: asyncpg.Pool, redis_client: Optional[RedisClient] = None):
        """Initialize service.

        Args:
            db_pool: Database connection pool
            redis_client: Optional Redis client for event publishing
        """
        self.db_pool = db_pool
        self.redis_client = redis_client

    def _row_to_example(self, row) -> TrainingExample:
        """Convert database row to TrainingExample model.

        Args:
            row: Database row

        Returns:
            TrainingExample instance
        """
        example_dict = dict(row)

        # Parse JSONB fields
        for field in ['input_structured', 'expected_actions', 'metadata']:
            if field in example_dict and isinstance(example_dict[field], str):
                example_dict[field] = json.loads(example_dict[field])

        # Parse array fields
        if 'labels' in example_dict and isinstance(example_dict[field], str):
            example_dict['labels'] = json.loads(example_dict['labels'])

        return TrainingExample(**example_dict)

    async def create_example(self, example_data: TrainingExampleCreate) -> TrainingExample:
        """Create new training example.

        Args:
            example_data: Training example creation data

        Returns:
            Created training example

        Raises:
            Exception: If creation fails
        """
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO training_examples (
                    execution_id, task_id, agent_id,
                    source_type, source_trace_hash,
                    input_text, input_structured,
                    output_text, expected_actions, final_answer,
                    quality_score, confidence,
                    labels, domain, task_type,
                    difficulty, metadata, extracted_by
                )
                VALUES (
                    $1, $2, $3, $4, $5, $6, $7::jsonb,
                    $8, $9::jsonb, $10, $11, $12,
                    $13, $14, $15, $16, $17::jsonb, $18
                )
                RETURNING *
                """,
                example_data.execution_id,
                example_data.task_id,
                example_data.agent_id,
                example_data.source_type.value,
                example_data.source_trace_hash,
                example_data.input_text,
                json.dumps(example_data.input_structured),
                example_data.output_text,
                json.dumps(example_data.expected_actions),
                example_data.final_answer,
                example_data.quality_score,
                example_data.confidence,
                example_data.labels,
                example_data.domain,
                example_data.task_type.value,
                example_data.difficulty,
                json.dumps(example_data.metadata),
                example_data.extracted_by,
            )

        example = self._row_to_example(row)

        # Publish event
        if self.redis_client:
            await self.redis_client.publish_event(
                event_type="training_example.created",
                aggregate_type="training_example",
                aggregate_id=str(example.id),
                payload={
                    "execution_id": example.execution_id,
                    "agent_id": str(example.agent_id) if example.agent_id else None,
                    "source_type": example.source_type.value,
                    "quality_score": example.quality_score,
                    "domain": example.domain,
                },
            )

        logger.info(f"Created training example {example.id}")
        return example

    async def get_example(self, example_id: UUID) -> Optional[TrainingExample]:
        """Get training example by ID.

        Args:
            example_id: Example identifier

        Returns:
            Training example or None if not found
        """
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM training_examples WHERE id = $1",
                example_id
            )

        if not row:
            return None

        return self._row_to_example(row)

    async def update_example(
        self,
        example_id: UUID,
        update_data: TrainingExampleUpdate
    ) -> Optional[TrainingExample]:
        """Update training example.

        Args:
            example_id: Example identifier
            update_data: Update data

        Returns:
            Updated training example or None if not found
        """
        updates = []
        values = []
        param_idx = 1

        if update_data.quality_score is not None:
            updates.append(f"quality_score = ${param_idx}")
            values.append(update_data.quality_score)
            param_idx += 1

        if update_data.confidence is not None:
            updates.append(f"confidence = ${param_idx}")
            values.append(update_data.confidence)
            param_idx += 1

        if update_data.labels is not None:
            updates.append(f"labels = ${param_idx}")
            values.append(update_data.labels)
            param_idx += 1

        if update_data.metadata is not None:
            updates.append(f"metadata = ${param_idx}::jsonb")
            values.append(json.dumps(update_data.metadata))
            param_idx += 1

        if not updates:
            return await self.get_example(example_id)

        updates.append(f"updated_at = NOW()")
        values.append(example_id)

        query = f"""
            UPDATE training_examples
            SET {', '.join(updates)}
            WHERE id = ${param_idx}
            RETURNING *
        """

        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow(query, *values)

        if not row:
            return None

        example = self._row_to_example(row)

        # Publish event
        if self.redis_client:
            await self.redis_client.publish_event(
                event_type="training_example.updated",
                aggregate_type="training_example",
                aggregate_id=str(example.id),
                payload={"updated_fields": list(update_data.dict(exclude_unset=True).keys())},
            )

        logger.info(f"Updated training example {example_id}")
        return example

    async def list_examples(
        self,
        agent_id: Optional[UUID] = None,
        domain: Optional[str] = None,
        min_quality: Optional[float] = None,
        source_type: Optional[ExampleSource] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[TrainingExample]:
        """List training examples with optional filters.

        Args:
            agent_id: Filter by agent ID
            domain: Filter by domain
            min_quality: Minimum quality score
            source_type: Filter by source type
            limit: Maximum results
            offset: Results offset

        Returns:
            List of training examples
        """
        conditions = []
        values = []
        param_idx = 1

        if agent_id:
            conditions.append(f"agent_id = ${param_idx}")
            values.append(agent_id)
            param_idx += 1

        if domain:
            conditions.append(f"domain = ${param_idx}")
            values.append(domain)
            param_idx += 1

        if min_quality is not None:
            conditions.append(f"quality_score >= ${param_idx}")
            values.append(min_quality)
            param_idx += 1

        if source_type:
            conditions.append(f"source_type = ${param_idx}")
            values.append(source_type.value)
            param_idx += 1

        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

        query = f"""
            SELECT * FROM training_examples
            {where_clause}
            ORDER BY created_at DESC
            LIMIT ${param_idx} OFFSET ${param_idx + 1}
        """

        values.extend([limit, offset])

        async with self.db_pool.acquire() as conn:
            rows = await conn.fetch(query, *values)

        return [self._row_to_example(row) for row in rows]

    async def delete_example(self, example_id: UUID) -> bool:
        """Delete training example.

        Args:
            example_id: Example identifier

        Returns:
            True if deleted, False if not found
        """
        async with self.db_pool.acquire() as conn:
            result = await conn.execute(
                "DELETE FROM training_examples WHERE id = $1",
                example_id
            )

        deleted = result == "DELETE 1"

        if deleted and self.redis_client:
            await self.redis_client.publish_event(
                event_type="training_example.deleted",
                aggregate_type="training_example",
                aggregate_id=str(example_id),
                payload={},
            )

        logger.info(f"Deleted training example {example_id}")
        return deleted

    async def get_statistics(self) -> Dict[str, Any]:
        """Get training example statistics.

        Returns:
            Statistics dictionary
        """
        async with self.db_pool.acquire() as conn:
            stats = await conn.fetchrow(
                """
                SELECT
                    COUNT(*) as total_examples,
                    AVG(quality_score) as avg_quality_score,
                    AVG(confidence) as avg_confidence,
                    AVG(difficulty) as avg_difficulty,
                    COUNT(DISTINCT domain) as unique_domains,
                    COUNT(DISTINCT agent_id) as unique_agents
                FROM training_examples
                """
            )

            domain_dist = await conn.fetch(
                """
                SELECT domain, COUNT(*) as count
                FROM training_examples
                GROUP BY domain
                ORDER BY count DESC
                LIMIT 10
                """
            )

        return {
            "total_examples": stats["total_examples"],
            "avg_quality_score": float(stats["avg_quality_score"] or 0),
            "avg_confidence": float(stats["avg_confidence"] or 0),
            "avg_difficulty": float(stats["avg_difficulty"] or 0),
            "unique_domains": stats["unique_domains"],
            "unique_agents": stats["unique_agents"],
            "domain_distribution": {row["domain"]: row["count"] for row in domain_dist},
        }
