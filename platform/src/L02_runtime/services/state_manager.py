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
from datetime import datetime, timedelta
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
            "postgresql://postgres:postgres@localhost:5432/agent_runtime"
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
        """Create checkpoints table in PostgreSQL"""
        if not self._pg_pool:
            return

        create_table_sql = """
        CREATE TABLE IF NOT EXISTS agent_checkpoints (
            checkpoint_id TEXT PRIMARY KEY,
            agent_id TEXT NOT NULL,
            session_id TEXT NOT NULL,
            state TEXT NOT NULL,
            context_data BYTEA,
            metadata JSONB,
            created_at TIMESTAMP NOT NULL DEFAULT NOW(),
            size_bytes INTEGER,
            compressed BOOLEAN DEFAULT false
        );

        CREATE INDEX IF NOT EXISTS idx_agent_checkpoints_agent_id
            ON agent_checkpoints(agent_id);
        CREATE INDEX IF NOT EXISTS idx_agent_checkpoints_session_id
            ON agent_checkpoints(session_id);
        CREATE INDEX IF NOT EXISTS idx_agent_checkpoints_created_at
            ON agent_checkpoints(created_at);
        """

        async with self._pg_pool.acquire() as conn:
            await conn.execute(create_table_sql)

        logger.info("Checkpoint table created/verified")

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
        checkpoint_id = f"ckpt_{agent_id}_{datetime.utcnow().timestamp()}"

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
        INSERT INTO agent_checkpoints
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
        FROM agent_checkpoints
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
            key = f"agent_state:{agent_id}"
            value = json.dumps(state_data)
            await self._redis_client.setex(
                key,
                timedelta(hours=1),  # 1 hour TTL
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
            key = f"agent_state:{agent_id}"
            value = await self._redis_client.get(key)
            if value:
                return json.loads(value)
            return None

        except Exception as e:
            logger.warning(f"Failed to load hot state for agent {agent_id}: {e}")
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
        FROM agent_checkpoints
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

        cutoff_date = datetime.utcnow() - timedelta(days=self.retention_days)

        delete_sql = """
        DELETE FROM agent_checkpoints
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
