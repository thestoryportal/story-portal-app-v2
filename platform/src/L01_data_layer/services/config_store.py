"""Configuration store service."""

import asyncpg
from typing import Optional, List, Dict, Any
import logging

from ..models import Configuration, ConfigCreate

logger = logging.getLogger(__name__)


class ConfigStore:
    """Configuration store service."""

    def __init__(self, db_pool: asyncpg.Pool):
        self.db_pool = db_pool

    async def get_config(self, namespace: str, key: str) -> Optional[Configuration]:
        """Get configuration value."""
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT id, namespace, key, value, version, created_at, updated_at
                FROM configurations WHERE namespace = $1 AND key = $2
                """,
                namespace,
                key,
            )

        if not row:
            return None

        return Configuration(**dict(row))

    async def set_config(self, config_data: ConfigCreate) -> Configuration:
        """Set configuration value (upsert)."""
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO configurations (namespace, key, value)
                VALUES ($1, $2, $3)
                ON CONFLICT (namespace, key) DO UPDATE
                SET value = EXCLUDED.value, version = configurations.version + 1, updated_at = NOW()
                RETURNING id, namespace, key, value, version, created_at, updated_at
                """,
                config_data.namespace,
                config_data.key,
                config_data.value,
            )

        return Configuration(**dict(row))

    async def list_configs(self, namespace: str) -> List[Configuration]:
        """List all configurations in a namespace."""
        async with self.db_pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT id, namespace, key, value, version, created_at, updated_at
                FROM configurations WHERE namespace = $1 ORDER BY key
                """,
                namespace,
            )

        return [Configuration(**dict(row)) for row in rows]
