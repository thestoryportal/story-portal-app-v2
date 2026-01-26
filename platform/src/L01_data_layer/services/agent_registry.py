"""Agent registry service."""

import asyncpg
from typing import List, Optional
from uuid import UUID, uuid4
import logging
import json

from ..models import Agent, AgentCreate, AgentUpdate, AgentStatus
from ..redis_client import RedisClient

logger = logging.getLogger(__name__)


class AgentRegistry:
    """Agent registry service."""

    def __init__(self, db_pool: asyncpg.Pool, redis_client: RedisClient):
        self.db_pool = db_pool
        self.redis_client = redis_client

    def _row_to_agent(self, row) -> Agent:
        """Convert database row to Agent model, parsing JSON fields."""
        agent_dict = dict(row)
        # Parse JSON fields that might be returned as strings
        for field in ['configuration', 'metadata', 'resource_limits']:
            if field in agent_dict and isinstance(agent_dict[field], str):
                agent_dict[field] = json.loads(agent_dict[field])
        return Agent(**agent_dict)

    async def create_agent(self, agent_data: AgentCreate) -> Agent:
        """Create a new agent."""
        # Generate DID from name
        did = f"did:agent:{agent_data.name}:{uuid4().hex[:8]}"

        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO agents (did, name, agent_type, configuration, metadata, resource_limits)
                VALUES ($1, $2, $3, $4::jsonb, $5::jsonb, $6::jsonb)
                RETURNING id, did, name, agent_type, status, configuration, metadata, resource_limits, created_at, updated_at
                """,
                did,
                agent_data.name,
                agent_data.agent_type,
                json.dumps(agent_data.configuration),
                json.dumps(agent_data.metadata),
                json.dumps(agent_data.resource_limits),
            )

        agent = self._row_to_agent(row)

        # Publish event
        await self.redis_client.publish_event(
            event_type="agent.created",
            aggregate_type="agent",
            aggregate_id=str(agent.id),
            payload={"name": agent.name, "agent_type": agent.agent_type, "did": agent.did},
        )

        logger.info(f"Created agent {agent.id} ({agent.name})")
        return agent

    async def get_agent(self, agent_id: UUID) -> Optional[Agent]:
        """Get agent by ID."""
        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT id, did, name, agent_type, status, configuration, metadata, resource_limits, created_at, updated_at
                FROM agents WHERE id = $1
                """,
                agent_id,
            )

        if not row:
            return None

        return self._row_to_agent(row)

    async def list_agents(
        self, status: Optional[AgentStatus] = None, limit: int = 100, offset: int = 0
    ) -> List[Agent]:
        """List agents with optional status filter."""
        if status:
            query = """
                SELECT id, did, name, agent_type, status, configuration, metadata, resource_limits, created_at, updated_at
                FROM agents WHERE status = $1 ORDER BY created_at DESC LIMIT $2 OFFSET $3
            """
            params = [status.value, limit, offset]
        else:
            query = """
                SELECT id, did, name, agent_type, status, configuration, metadata, resource_limits, created_at, updated_at
                FROM agents ORDER BY created_at DESC LIMIT $1 OFFSET $2
            """
            params = [limit, offset]

        async with self.db_pool.acquire() as conn:
            rows = await conn.fetch(query, *params)

        return [self._row_to_agent(row) for row in rows]

    async def update_agent(self, agent_id: UUID, agent_data: AgentUpdate) -> Optional[Agent]:
        """Update an agent."""
        update_fields = []
        params = []
        param_count = 1

        for field, value in agent_data.model_dump(exclude_unset=True).items():
            if value is not None:
                update_fields.append(f"{field} = ${param_count}")
                # JSON serialize dict/list values for JSONB columns
                if isinstance(value, (dict, list)):
                    params.append(json.dumps(value))
                elif isinstance(value, AgentStatus):
                    params.append(value.value)
                else:
                    params.append(value)
                param_count += 1

        if not update_fields:
            return await self.get_agent(agent_id)

        update_fields.append(f"updated_at = NOW()")

        query = f"""
            UPDATE agents SET {', '.join(update_fields)}
            WHERE id = ${param_count}
            RETURNING id, did, name, agent_type, status, configuration, metadata, resource_limits, created_at, updated_at
        """
        params.append(agent_id)

        async with self.db_pool.acquire() as conn:
            row = await conn.fetchrow(query, *params)

        if not row:
            return None

        agent = self._row_to_agent(row)

        # Publish event
        await self.redis_client.publish_event(
            event_type="agent.updated",
            aggregate_type="agent",
            aggregate_id=str(agent.id),
            payload={"updates": agent_data.model_dump(exclude_unset=True)},
        )

        logger.info(f"Updated agent {agent.id}")
        return agent

    async def delete_agent(self, agent_id: UUID) -> bool:
        """Delete an agent."""
        async with self.db_pool.acquire() as conn:
            result = await conn.execute("DELETE FROM agents WHERE id = $1", agent_id)

        deleted = result.split()[-1] == "1"

        if deleted:
            await self.redis_client.publish_event(
                event_type="agent.deleted",
                aggregate_type="agent",
                aggregate_id=str(agent_id),
                payload={},
            )
            logger.info(f"Deleted agent {agent_id}")

        return deleted
