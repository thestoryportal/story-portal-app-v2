"""
State Manager

Manages agent state checkpointing, serialization, and recovery.
Uses PostgreSQL for durable checkpoints and Redis for hot state.

Based on Section 3.3.4 of agent-runtime-layer-specification-v1.2-final-ASCII.md
"""

import asyncio
import json
import gzip
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta, timezone
from dataclasses import dataclass, asdict

try:
    import asyncpg
except ImportError:
    asyncpg = None  # Optional dependency

try:
    import redis.asyncio as redis
except ImportError:
    redis = None  # Optional dependency

from ..models import AgentState
from ..models.checkpoint_models import Checkpoint, CheckpointMetadata


logger = logging.getLogger(__name__)


class StateError(Exception):
    """State management error"""
    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(f"[{code}] {message}")


@dataclass
class StateSnapshot:
    """Agent state snapshot"""
    agent_id: str
    session_id: str
    state: AgentState
    context: Dict[str, Any]
    timestamp: datetime
    metadata: Dict[str, Any]


class StateManager:
    """
    Manages agent state persistence and recovery.

    Responsibilities:
    - Create and restore checkpoints
    - Manage hot state in Redis
    - Persist durable state in PostgreSQL
    - Auto-checkpoint at intervals
    - Compress and validate checkpoints
    - Clean up old checkpoints
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize StateManager.

        Args:
            config: Configuration dict with:
                - checkpoint_backend: Backend storage (postgresql)
                - hot_state_backend: Hot state cache (redis)
                - auto_checkpoint_interval_seconds: Auto-checkpoint interval
                - max_checkpoint_size_mb: Maximum checkpoint size
                - checkpoint_compression: Compression algorithm (gzip)
                - retention_days: Checkpoint retention period
                - postgresql_dsn: PostgreSQL connection string
                - redis_url: Redis connection URL
        """
        self.config = config or {}

        # Configuration
        self.checkpoint_backend = self.config.get("checkpoint_backend", "postgresql")
        self.hot_state_backend = self.config.get("hot_state_backend", "redis")
        self.auto_checkpoint_interval = self.config.get(
            "auto_checkpoint_interval_seconds", 60
        )
        self.max_checkpoint_size_mb = self.config.get("max_checkpoint_size_mb", 100)
        self.checkpoint_compression = self.config.get("checkpoint_compression", "gzip")
        self.retention_days = self.config.get("retention_days", 30)

        # Connection strings
        self.postgresql_dsn = self.config.get(
            "postgresql_dsn",
            "postgresql://postgres:postgres@localhost:5432/agentic_platform"
        )
        self.redis_url = self.config.get("redis_url", "redis://localhost:6379/0")

        # Backend connections
        self._pg_pool: Optional[Any] = None
        self._redis_client: Optional[Any] = None

        # Background tasks
        self._auto_checkpoint_task: Optional[asyncio.Task] = None

        logger.info(
            f"StateManager initialized: "
            f"checkpoint_backend={self.checkpoint_backend}, "
            f"hot_state_backend={self.hot_state_backend}"
        )

    async def initialize(self) -> None:
        """Initialize state manager and backend connections"""
        # Initialize PostgreSQL connection pool
        if self.checkpoint_backend == "postgresql" and asyncpg:
            try:
                self._pg_pool = await asyncpg.create_pool(
                    self.postgresql_dsn,
                    min_size=2,
                    max_size=10,
                )
                logger.info("PostgreSQL connection pool initialized")

                # Create checkpoints table if not exists
                await self._create_checkpoint_table()

            except Exception as e:
                logger.warning(f"Failed to initialize PostgreSQL: {e}")
                self._pg_pool = None

        # Initialize Redis connection
        if self.hot_state_backend == "redis" and redis:
            try:
                self._redis_client = redis.from_url(self.redis_url)
                await self._redis_client.ping()
                logger.info("Redis connection initialized")

            except Exception as e:
                logger.warning(f"Failed to initialize Redis: {e}")
                self._redis_client = None

        # Start auto-checkpoint background task
        self._auto_checkpoint_task = asyncio.create_task(
            self._auto_checkpoint_loop()
        )

        logger.info("StateManager initialization complete")

    async def _create_checkpoint_table(self) -> None:
        """Create l02_runtime schema and required tables in PostgreSQL"""
        if not self._pg_pool:
            return

        create_schema_sql = """
        -- Create schema
        CREATE SCHEMA IF NOT EXISTS l02_runtime;

        -- Create checkpoints table
        CREATE TABLE IF NOT EXISTS l02_runtime.checkpoints (
            checkpoint_id TEXT PRIMARY KEY,
            agent_id TEXT NOT NULL,
            session_id TEXT NOT NULL,
            state TEXT NOT NULL,
            context_data BYTEA,
            metadata JSONB,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            size_bytes INTEGER,
            compressed BOOLEAN DEFAULT false
        );

        -- Create agent_state table
        CREATE TABLE IF NOT EXISTS l02_runtime.agent_state (
            agent_id TEXT PRIMARY KEY,
            session_id TEXT NOT NULL,
            state TEXT NOT NULL,
            context JSONB,
            last_updated TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            metadata JSONB
        );

        -- Create indexes for checkpoints table
        CREATE INDEX IF NOT EXISTS idx_checkpoints_agent_id
            ON l02_runtime.checkpoints(agent_id);
        CREATE INDEX IF NOT EXISTS idx_checkpoints_session_id
            ON l02_runtime.checkpoints(session_id);
        CREATE INDEX IF NOT EXISTS idx_checkpoints_created_at
            ON l02_runtime.checkpoints(created_at);

        -- Create indexes for agent_state table
        CREATE INDEX IF NOT EXISTS idx_agent_state_session_id
            ON l02_runtime.agent_state(session_id);
        CREATE INDEX IF NOT EXISTS idx_agent_state_last_updated
            ON l02_runtime.agent_state(last_updated);
        """

        async with self._pg_pool.acquire() as conn:
            await conn.execute(create_schema_sql)

        logger.info("L02 runtime schema and tables created/verified")

    async def create_checkpoint(
        self,
        agent_id: str,
        session_id: str,
        state: AgentState,
        context: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Create a checkpoint for an agent.

        Args:
            agent_id: Agent identifier
            session_id: Session identifier
            state: Current agent state
            context: Execution context to checkpoint
            metadata: Optional checkpoint metadata

        Returns:
            Checkpoint ID

        Raises:
            StateError: If checkpoint creation fails
        """
        checkpoint_id = f"ckpt_{agent_id}_{datetime.now(timezone.utc).timestamp()}"

        logger.info(f"Creating checkpoint {checkpoint_id} for agent {agent_id}")

        try:
            # Serialize context
            context_json = json.dumps(context)
            context_bytes = context_json.encode('utf-8')

            # Check size before compression
            size_mb = len(context_bytes) / (1024 * 1024)
            if size_mb > self.max_checkpoint_size_mb:
                raise StateError(
                    code="E2031",
                    message=f"Checkpoint size {size_mb:.2f}MB exceeds limit "
                            f"{self.max_checkpoint_size_mb}MB"
                )

            # Compress if enabled
            compressed = False
            if self.checkpoint_compression == "gzip":
                context_bytes = gzip.compress(context_bytes)
                compressed = True

            # Store in PostgreSQL
            if self._pg_pool:
                await self._store_checkpoint_pg(
                    checkpoint_id=checkpoint_id,
                    agent_id=agent_id,
                    session_id=session_id,
                    state=state.value,
                    context_data=context_bytes,
                    metadata=metadata or {},
                    size_bytes=len(context_bytes),
                    compressed=compressed,
                )

            logger.info(
                f"Checkpoint {checkpoint_id} created successfully "
                f"(size={len(context_bytes)} bytes, compressed={compressed})"
            )

            return checkpoint_id

        except StateError:
            raise
        except Exception as e:
            logger.error(f"Failed to create checkpoint {checkpoint_id}: {e}")
            raise StateError(
                code="E2030",
                message=f"Checkpoint creation failed: {str(e)}"
            )

    async def _store_checkpoint_pg(
        self,
        checkpoint_id: str,
        agent_id: str,
        session_id: str,
        state: str,
        context_data: bytes,
        metadata: Dict[str, Any],
        size_bytes: int,
        compressed: bool
    ) -> None:
        """Store checkpoint in PostgreSQL"""
        if not self._pg_pool:
            logger.warning("PostgreSQL not available, skipping checkpoint storage")
            return

        insert_sql = """
        INSERT INTO l02_runtime.checkpoints
            (checkpoint_id, agent_id, session_id, state, context_data,
             metadata, size_bytes, compressed)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
        """

        async with self._pg_pool.acquire() as conn:
            await conn.execute(
                insert_sql,
                checkpoint_id,
                agent_id,
                session_id,
                state,
                context_data,
                json.dumps(metadata),
                size_bytes,
                compressed,
            )

    async def restore_checkpoint(
        self,
        checkpoint_id: str
    ) -> StateSnapshot:
        """
        Restore agent state from checkpoint.

        Args:
            checkpoint_id: Checkpoint identifier

        Returns:
            StateSnapshot

        Raises:
            StateError: If restore fails
        """
        logger.info(f"Restoring checkpoint {checkpoint_id}")

        try:
            # Load from PostgreSQL
            if self._pg_pool:
                snapshot = await self._load_checkpoint_pg(checkpoint_id)
                logger.info(f"Checkpoint {checkpoint_id} restored successfully")
                return snapshot
            else:
                raise StateError(
                    code="E2032",
                    message="No checkpoint backend available"
                )

        except StateError:
            raise
        except Exception as e:
            logger.error(f"Failed to restore checkpoint {checkpoint_id}: {e}")
            raise StateError(
                code="E2032",
                message=f"State restoration failed: {str(e)}"
            )

    async def _load_checkpoint_pg(self, checkpoint_id: str) -> StateSnapshot:
        """Load checkpoint from PostgreSQL"""
        if not self._pg_pool:
            raise StateError(
                code="E2032",
                message="PostgreSQL not available"
            )

        select_sql = """
        SELECT agent_id, session_id, state, context_data, metadata,
               created_at, compressed
        FROM l02_runtime.checkpoints
        WHERE checkpoint_id = $1
        """

        async with self._pg_pool.acquire() as conn:
            row = await conn.fetchrow(select_sql, checkpoint_id)

            if not row:
                raise StateError(
                    code="E2032",
                    message=f"Checkpoint {checkpoint_id} not found"
                )

            # Decompress if needed
            context_bytes = row['context_data']
            if row['compressed']:
                context_bytes = gzip.decompress(context_bytes)

            # Deserialize context
            context_json = context_bytes.decode('utf-8')
            context = json.loads(context_json)

            # Parse metadata
            metadata = json.loads(row['metadata']) if row['metadata'] else {}

            return StateSnapshot(
                agent_id=row['agent_id'],
                session_id=row['session_id'],
                state=AgentState(row['state']),
                context=context,
                timestamp=row['created_at'],
                metadata=metadata,
            )

    async def save_hot_state(
        self,
        agent_id: str,
        state_data: Dict[str, Any]
    ) -> None:
        """
        Save hot state to Redis.

        Args:
            agent_id: Agent identifier
            state_data: State data to cache
        """
        if not self._redis_client:
            logger.debug("Redis not available, skipping hot state save")
            return

        try:
            key = f"l02:state:{agent_id}"
            value = json.dumps(state_data)
            await self._redis_client.setex(
                key,
                timedelta(seconds=3600),  # 3600s TTL
                value
            )
            logger.debug(f"Hot state saved for agent {agent_id}")

        except Exception as e:
            logger.warning(f"Failed to save hot state for agent {agent_id}: {e}")

    async def load_hot_state(
        self,
        agent_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Load hot state from Redis.

        Args:
            agent_id: Agent identifier

        Returns:
            State data or None if not found
        """
        if not self._redis_client:
            logger.debug("Redis not available")
            return None

        try:
            key = f"l02:state:{agent_id}"
            value = await self._redis_client.get(key)
            if value:
                return json.loads(value)
            return None

        except Exception as e:
            logger.warning(f"Failed to load hot state for agent {agent_id}: {e}")
            return None

    async def save_agent_state(
        self,
        agent_id: str,
        session_id: str,
        state: AgentState,
        context: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Save agent state to PostgreSQL agent_state table.

        Args:
            agent_id: Agent identifier
            session_id: Session identifier
            state: Current agent state
            context: Execution context
            metadata: Optional metadata
        """
        if not self._pg_pool:
            logger.debug("PostgreSQL not available, skipping agent state save")
            return

        try:
            upsert_sql = """
            INSERT INTO l02_runtime.agent_state
                (agent_id, session_id, state, context, last_updated, metadata)
            VALUES ($1, $2, $3, $4, $5, $6)
            ON CONFLICT (agent_id)
            DO UPDATE SET
                session_id = EXCLUDED.session_id,
                state = EXCLUDED.state,
                context = EXCLUDED.context,
                last_updated = EXCLUDED.last_updated,
                metadata = EXCLUDED.metadata
            """

            async with self._pg_pool.acquire() as conn:
                await conn.execute(
                    upsert_sql,
                    agent_id,
                    session_id,
                    state.value,
                    json.dumps(context),
                    datetime.now(timezone.utc),
                    json.dumps(metadata or {}),
                )

            logger.debug(f"Agent state saved for {agent_id}")

        except Exception as e:
            logger.warning(f"Failed to save agent state for {agent_id}: {e}")

    async def load_agent_state(
        self,
        agent_id: str
    ) -> Optional[StateSnapshot]:
        """
        Load agent state from PostgreSQL agent_state table.

        Args:
            agent_id: Agent identifier

        Returns:
            StateSnapshot or None if not found
        """
        if not self._pg_pool:
            logger.debug("PostgreSQL not available")
            return None

        try:
            select_sql = """
            SELECT agent_id, session_id, state, context, last_updated, metadata
            FROM l02_runtime.agent_state
            WHERE agent_id = $1
            """

            async with self._pg_pool.acquire() as conn:
                row = await conn.fetchrow(select_sql, agent_id)

                if not row:
                    return None

                context = json.loads(row['context']) if row['context'] else {}
                metadata = json.loads(row['metadata']) if row['metadata'] else {}

                return StateSnapshot(
                    agent_id=row['agent_id'],
                    session_id=row['session_id'],
                    state=AgentState(row['state']),
                    context=context,
                    timestamp=row['last_updated'],
                    metadata=metadata,
                )

        except Exception as e:
            logger.warning(f"Failed to load agent state for {agent_id}: {e}")
            return None

    async def list_checkpoints(
        self,
        agent_id: str,
        limit: int = 10
    ) -> List[CheckpointMetadata]:
        """
        List checkpoints for an agent.

        Args:
            agent_id: Agent identifier
            limit: Maximum number of checkpoints to return

        Returns:
            List of checkpoint metadata
        """
        if not self._pg_pool:
            return []

        select_sql = """
        SELECT checkpoint_id, session_id, state, created_at, size_bytes, metadata
        FROM l02_runtime.checkpoints
        WHERE agent_id = $1
        ORDER BY created_at DESC
        LIMIT $2
        """

        async with self._pg_pool.acquire() as conn:
            rows = await conn.fetch(select_sql, agent_id, limit)

            return [
                CheckpointMetadata(
                    checkpoint_id=row['checkpoint_id'],
                    agent_id=agent_id,
                    session_id=row['session_id'],
                    state=AgentState(row['state']),
                    created_at=row['created_at'],
                    size_bytes=row['size_bytes'],
                    metadata=json.loads(row['metadata']) if row['metadata'] else {},
                )
                for row in rows
            ]

    async def cleanup_old_checkpoints(self) -> int:
        """
        Delete checkpoints older than retention period.

        Returns:
            Number of checkpoints deleted
        """
        if not self._pg_pool:
            return 0

        cutoff_date = datetime.now(timezone.utc) - timedelta(days=self.retention_days)

        delete_sql = """
        DELETE FROM l02_runtime.checkpoints
        WHERE created_at < $1
        """

        async with self._pg_pool.acquire() as conn:
            result = await conn.execute(delete_sql, cutoff_date)
            # Extract count from result string like "DELETE 5"
            count = int(result.split()[-1]) if result else 0

        logger.info(f"Cleaned up {count} old checkpoints")
        return count

    async def _auto_checkpoint_loop(self) -> None:
        """Background task for periodic checkpoint cleanup"""
        logger.info("Starting auto-checkpoint cleanup loop")

        while True:
            try:
                await asyncio.sleep(self.auto_checkpoint_interval * 10)  # 10x interval
                await self.cleanup_old_checkpoints()

            except asyncio.CancelledError:
                logger.info("Auto-checkpoint loop cancelled")
                break
            except Exception as e:
                logger.error(f"Error in auto-checkpoint loop: {e}")

    async def get_checkpoint_stats(self) -> Dict[str, Any]:
        """
        Get checkpoint statistics.

        Returns:
            Statistics about stored checkpoints
        """
        stats = {
            "total_checkpoints": 0,
            "total_size_bytes": 0,
            "oldest_checkpoint": None,
            "newest_checkpoint": None,
            "checkpoints_by_agent": {},
        }

        if not self._pg_pool:
            return stats

        try:
            async with self._pg_pool.acquire() as conn:
                # Get total count and size
                result = await conn.fetchrow("""
                    SELECT
                        COUNT(*) as total,
                        COALESCE(SUM(size_bytes), 0) as total_size,
                        MIN(created_at) as oldest,
                        MAX(created_at) as newest
                    FROM l02_runtime.checkpoints
                """)

                if result:
                    stats["total_checkpoints"] = result["total"]
                    stats["total_size_bytes"] = result["total_size"]
                    stats["oldest_checkpoint"] = (
                        result["oldest"].isoformat() if result["oldest"] else None
                    )
                    stats["newest_checkpoint"] = (
                        result["newest"].isoformat() if result["newest"] else None
                    )

                # Get counts by agent
                agent_counts = await conn.fetch("""
                    SELECT agent_id, COUNT(*) as count
                    FROM l02_runtime.checkpoints
                    GROUP BY agent_id
                    ORDER BY count DESC
                    LIMIT 20
                """)

                stats["checkpoints_by_agent"] = {
                    row["agent_id"]: row["count"] for row in agent_counts
                }

        except Exception as e:
            logger.warning(f"Failed to get checkpoint stats: {e}")

        return stats

    async def get_hot_state_keys(self, pattern: str = "*") -> List[str]:
        """
        List hot state keys in Redis.

        Args:
            pattern: Key pattern to match

        Returns:
            List of matching keys
        """
        if not self._redis_client:
            return []

        try:
            keys = []
            cursor = 0
            full_pattern = f"l02:state:{pattern}"

            while True:
                cursor, batch = await self._redis_client.scan(
                    cursor=cursor,
                    match=full_pattern,
                    count=100
                )
                keys.extend([k.decode() if isinstance(k, bytes) else k for k in batch])
                if cursor == 0:
                    break

            return keys

        except Exception as e:
            logger.warning(f"Failed to get hot state keys: {e}")
            return []

    async def delete_hot_state(self, agent_id: str) -> bool:
        """
        Delete hot state for an agent.

        Args:
            agent_id: Agent identifier

        Returns:
            True if deleted, False otherwise
        """
        if not self._redis_client:
            return False

        try:
            key = f"l02:state:{agent_id}"
            result = await self._redis_client.delete(key)
            return result > 0
        except Exception as e:
            logger.warning(f"Failed to delete hot state for {agent_id}: {e}")
            return False

    async def delete_checkpoint(self, checkpoint_id: str) -> bool:
        """
        Delete a specific checkpoint.

        Args:
            checkpoint_id: Checkpoint to delete

        Returns:
            True if deleted, False otherwise
        """
        if not self._pg_pool:
            return False

        try:
            async with self._pg_pool.acquire() as conn:
                result = await conn.execute(
                    "DELETE FROM l02_runtime.checkpoints WHERE checkpoint_id = $1",
                    checkpoint_id
                )
                return "DELETE 1" in result
        except Exception as e:
            logger.warning(f"Failed to delete checkpoint {checkpoint_id}: {e}")
            return False

    def get_health_status(self) -> Dict[str, Any]:
        """
        Get health status of state manager.

        Returns:
            Health status information
        """
        return {
            "healthy": True,
            "postgresql_connected": self._pg_pool is not None,
            "redis_connected": self._redis_client is not None,
            "auto_checkpoint_running": (
                self._auto_checkpoint_task is not None and
                not self._auto_checkpoint_task.done()
            ),
            "config": {
                "checkpoint_backend": self.checkpoint_backend,
                "hot_state_backend": self.hot_state_backend,
                "auto_checkpoint_interval": self.auto_checkpoint_interval,
                "max_checkpoint_size_mb": self.max_checkpoint_size_mb,
                "compression": self.checkpoint_compression,
                "retention_days": self.retention_days,
            }
        }

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get state manager statistics.

        Returns:
            Statistics dictionary
        """
        return {
            "postgresql_available": self._pg_pool is not None,
            "redis_available": self._redis_client is not None,
            "retention_days": self.retention_days,
            "compression_enabled": self.checkpoint_compression == "gzip",
        }

    async def cleanup(self) -> None:
        """Cleanup state manager and close connections"""
        logger.info("Cleaning up StateManager")

        # Cancel background tasks
        if self._auto_checkpoint_task:
            self._auto_checkpoint_task.cancel()
            try:
                await self._auto_checkpoint_task
            except asyncio.CancelledError:
                pass

        # Close PostgreSQL pool
        if self._pg_pool:
            await self._pg_pool.close()
            logger.info("PostgreSQL pool closed")

        # Close Redis connection
        if self._redis_client:
            await self._redis_client.close()
            logger.info("Redis connection closed")

        logger.info("StateManager cleanup complete")
