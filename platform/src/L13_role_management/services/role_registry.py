"""
Role Registry Service for L13 Role Management Layer.

Provides role registration, retrieval, search, and management functionality.
Designed to work with PostgreSQL via L01 bridge with in-memory fallback.
"""

import logging
from typing import List, Optional, Dict, Any
from uuid import UUID, uuid4
from datetime import datetime
import json

from ..models import (
    Role,
    RoleCreate,
    RoleUpdate,
    RoleStatus,
    RoleType,
    RoleMatch,
    TaskRequirements,
    Skill,
)

logger = logging.getLogger(__name__)


class RoleRegistry:
    """
    Role registry service for managing role definitions.

    Supports database persistence via L01 bridge with in-memory fallback
    for development and testing scenarios.
    """

    def __init__(
        self,
        db_pool=None,
        redis_client=None,
        use_memory_fallback: bool = True
    ):
        """
        Initialize the role registry.

        Args:
            db_pool: AsyncPG connection pool (optional)
            redis_client: Redis client for event publishing (optional)
            use_memory_fallback: Use in-memory storage if no database
        """
        self.db_pool = db_pool
        self.redis_client = redis_client
        self.use_memory_fallback = use_memory_fallback

        # In-memory storage fallback
        self._roles: Dict[UUID, Role] = {}
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize the registry, loading any existing roles."""
        if self._initialized:
            return

        if self.db_pool:
            try:
                await self._load_from_database()
            except Exception as e:
                logger.warning(f"Failed to load from database, using memory: {e}")

        self._initialized = True
        logger.info("RoleRegistry initialized")

    async def _load_from_database(self) -> None:
        """Load roles from database into memory cache."""
        if not self.db_pool:
            return

        async with self.db_pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT * FROM roles WHERE status != 'deprecated'
                ORDER BY priority DESC, created_at DESC
                """
            )
            for row in rows:
                role = self._row_to_role(row)
                self._roles[role.id] = role

        logger.info(f"Loaded {len(self._roles)} roles from database")

    def _row_to_role(self, row) -> Role:
        """Convert database row to Role model."""
        role_dict = dict(row)
        # Parse JSON fields
        for field in ['skills', 'responsibilities', 'constraints', 'tags', 'metadata']:
            if field in role_dict and isinstance(role_dict[field], str):
                role_dict[field] = json.loads(role_dict[field])

        # Convert skills dicts to Skill objects
        if 'skills' in role_dict and role_dict['skills']:
            role_dict['skills'] = [
                Skill(**s) if isinstance(s, dict) else s
                for s in role_dict['skills']
            ]

        return Role(**role_dict)

    async def register_role(self, role_data: RoleCreate) -> Role:
        """
        Register a new role in the registry.

        Args:
            role_data: Role creation data

        Returns:
            The created Role
        """
        role = Role(
            id=uuid4(),
            name=role_data.name,
            department=role_data.department,
            description=role_data.description,
            role_type=role_data.role_type,
            status=RoleStatus.ACTIVE,
            skills=role_data.skills,
            responsibilities=role_data.responsibilities,
            constraints=role_data.constraints,
            token_budget=role_data.token_budget,
            priority=role_data.priority,
            tags=role_data.tags,
            metadata=role_data.metadata,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )

        # Persist to database if available
        if self.db_pool:
            await self._persist_role(role)

        # Store in memory
        self._roles[role.id] = role

        # Publish event if Redis available
        if self.redis_client:
            await self._publish_event(
                "role.registered",
                str(role.id),
                {"name": role.name, "department": role.department}
            )

        logger.info(f"Registered role: {role.name} ({role.id})")
        return role

    async def _persist_role(self, role: Role) -> None:
        """Persist role to database."""
        if not self.db_pool:
            return

        async with self.db_pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO roles (
                    id, name, department, description, role_type, status,
                    skills, responsibilities, constraints, token_budget,
                    priority, tags, metadata, created_at, updated_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15)
                ON CONFLICT (id) DO UPDATE SET
                    name = EXCLUDED.name,
                    department = EXCLUDED.department,
                    description = EXCLUDED.description,
                    role_type = EXCLUDED.role_type,
                    status = EXCLUDED.status,
                    skills = EXCLUDED.skills,
                    responsibilities = EXCLUDED.responsibilities,
                    constraints = EXCLUDED.constraints,
                    token_budget = EXCLUDED.token_budget,
                    priority = EXCLUDED.priority,
                    tags = EXCLUDED.tags,
                    metadata = EXCLUDED.metadata,
                    updated_at = EXCLUDED.updated_at
                """,
                role.id,
                role.name,
                role.department,
                role.description,
                role.role_type.value,
                role.status.value,
                json.dumps([s.model_dump() for s in role.skills]),
                json.dumps(role.responsibilities),
                json.dumps(role.constraints),
                role.token_budget,
                role.priority,
                json.dumps(role.tags),
                json.dumps(role.metadata),
                role.created_at,
                role.updated_at,
            )

    async def get_role(self, role_id: UUID) -> Optional[Role]:
        """
        Get a role by its ID.

        Args:
            role_id: The role's UUID

        Returns:
            The Role if found, None otherwise
        """
        # Check memory first
        if role_id in self._roles:
            return self._roles[role_id]

        # Try database
        if self.db_pool:
            async with self.db_pool.acquire() as conn:
                row = await conn.fetchrow(
                    "SELECT * FROM roles WHERE id = $1",
                    role_id
                )
                if row:
                    role = self._row_to_role(row)
                    self._roles[role_id] = role
                    return role

        return None

    async def get_role_by_name(self, name: str) -> Optional[Role]:
        """
        Get a role by its name.

        Args:
            name: The role name

        Returns:
            The Role if found, None otherwise
        """
        # Check memory
        for role in self._roles.values():
            if role.name.lower() == name.lower():
                return role

        # Try database
        if self.db_pool:
            async with self.db_pool.acquire() as conn:
                row = await conn.fetchrow(
                    "SELECT * FROM roles WHERE LOWER(name) = LOWER($1)",
                    name
                )
                if row:
                    role = self._row_to_role(row)
                    self._roles[role.id] = role
                    return role

        return None

    async def update_role(self, role_id: UUID, update_data: RoleUpdate) -> Optional[Role]:
        """
        Update an existing role.

        Args:
            role_id: The role's UUID
            update_data: Fields to update

        Returns:
            The updated Role if found, None otherwise
        """
        role = await self.get_role(role_id)
        if not role:
            return None

        # Apply updates
        update_dict = update_data.model_dump(exclude_unset=True)
        for field, value in update_dict.items():
            if value is not None:
                setattr(role, field, value)

        role.updated_at = datetime.utcnow()

        # Persist
        if self.db_pool:
            await self._persist_role(role)

        # Update memory
        self._roles[role_id] = role

        # Publish event
        if self.redis_client:
            await self._publish_event(
                "role.updated",
                str(role_id),
                {"updates": list(update_dict.keys())}
            )

        logger.info(f"Updated role: {role.name} ({role_id})")
        return role

    async def delete_role(self, role_id: UUID) -> bool:
        """
        Delete a role (marks as deprecated).

        Args:
            role_id: The role's UUID

        Returns:
            True if deleted, False if not found
        """
        role = await self.get_role(role_id)
        if not role:
            return False

        # Mark as deprecated rather than hard delete
        role.status = RoleStatus.DEPRECATED
        role.updated_at = datetime.utcnow()

        if self.db_pool:
            async with self.db_pool.acquire() as conn:
                await conn.execute(
                    """
                    UPDATE roles SET status = $1, updated_at = $2 WHERE id = $3
                    """,
                    RoleStatus.DEPRECATED.value,
                    role.updated_at,
                    role_id
                )

        # Remove from active memory cache
        if role_id in self._roles:
            del self._roles[role_id]

        if self.redis_client:
            await self._publish_event("role.deleted", str(role_id), {})

        logger.info(f"Deleted role: {role.name} ({role_id})")
        return True

    async def list_roles(
        self,
        status: Optional[RoleStatus] = None,
        role_type: Optional[RoleType] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Role]:
        """
        List roles with optional filters.

        Args:
            status: Filter by status
            role_type: Filter by role type
            limit: Maximum results
            offset: Pagination offset

        Returns:
            List of matching roles
        """
        roles = list(self._roles.values())

        # Apply filters
        if status:
            roles = [r for r in roles if r.status == status]
        if role_type:
            roles = [r for r in roles if r.role_type == role_type]

        # Sort by priority (desc) then created_at (desc)
        roles.sort(key=lambda r: (-r.priority, r.created_at), reverse=False)

        # Apply pagination
        return roles[offset:offset + limit]

    async def list_by_department(self, department: str) -> List[Role]:
        """
        List all roles in a specific department.

        Args:
            department: Department name

        Returns:
            List of roles in the department
        """
        return [
            role for role in self._roles.values()
            if role.department.lower() == department.lower()
            and role.status == RoleStatus.ACTIVE
        ]

    async def search_roles(
        self,
        query: str,
        department: Optional[str] = None,
        role_type: Optional[RoleType] = None,
        tags: Optional[List[str]] = None,
        limit: int = 20
    ) -> List[RoleMatch]:
        """
        Search for roles matching a query.

        Args:
            query: Search query string
            department: Optional department filter
            role_type: Optional role type filter
            tags: Optional tags filter
            limit: Maximum results

        Returns:
            List of RoleMatch objects with scores
        """
        query_lower = query.lower()
        query_terms = set(query_lower.split())
        matches: List[RoleMatch] = []

        for role in self._roles.values():
            if role.status != RoleStatus.ACTIVE:
                continue

            # Apply filters
            if department and role.department.lower() != department.lower():
                continue
            if role_type and role.role_type != role_type:
                continue
            if tags and not any(t in role.tags for t in tags):
                continue

            # Calculate match score
            score = 0.0
            matching_skills = []
            matching_keywords = []

            # Name match (high weight)
            if query_lower in role.name.lower():
                score += 0.3

            # Description match
            if query_lower in role.description.lower():
                score += 0.2

            # Skill matching
            for skill in role.skills:
                skill_name_lower = skill.name.lower()
                if query_lower in skill_name_lower:
                    score += 0.15 * skill.weight
                    matching_skills.append(skill.name)

                # Check skill keywords
                for keyword in skill.keywords:
                    if keyword.lower() in query_terms:
                        score += 0.1 * skill.weight
                        matching_keywords.append(keyword)

            # Tag matching
            for tag in role.tags:
                if tag.lower() in query_terms:
                    score += 0.1
                    matching_keywords.append(tag)

            # Responsibility matching
            for resp in role.responsibilities:
                if query_lower in resp.lower():
                    score += 0.05

            if score > 0:
                # Normalize score to 0-1 range
                normalized_score = min(score, 1.0)
                matches.append(RoleMatch(
                    role=role,
                    score=normalized_score,
                    matching_skills=list(set(matching_skills)),
                    matching_keywords=list(set(matching_keywords)),
                    confidence=normalized_score * 0.9,  # Confidence slightly lower than score
                    reasoning=f"Matched on: skills={matching_skills}, keywords={matching_keywords}"
                ))

        # Sort by score descending
        matches.sort(key=lambda m: m.score, reverse=True)
        return matches[:limit]

    async def dispatch_for_task(
        self,
        requirements: TaskRequirements,
        top_k: int = 3
    ) -> List[RoleMatch]:
        """
        Find the best roles for a given task.

        Args:
            requirements: Task requirements for matching
            top_k: Number of top matches to return

        Returns:
            List of RoleMatch objects ranked by suitability
        """
        # Build search query from requirements
        query_parts = [requirements.task_description]
        query_parts.extend(requirements.required_skills)
        query_parts.extend(requirements.keywords)
        query = " ".join(query_parts)

        # Search with filters
        matches = await self.search_roles(
            query=query,
            department=requirements.department_hint,
            role_type=requirements.role_type_preference,
            limit=top_k * 2  # Get extra for filtering
        )

        # Re-rank based on additional factors
        for match in matches:
            # Boost for matching complexity
            if requirements.complexity == "high" and match.role.priority >= 7:
                match.score = min(match.score + 0.1, 1.0)
            elif requirements.complexity == "low" and match.role.priority <= 4:
                match.score = min(match.score + 0.05, 1.0)

            # Boost for urgency alignment with role type
            if requirements.urgency == "critical" and match.role.role_type == RoleType.AI_PRIMARY:
                match.score = min(match.score + 0.1, 1.0)  # AI can respond faster

            # Update confidence
            match.confidence = match.score * 0.95

        # Re-sort and return top_k
        matches.sort(key=lambda m: m.score, reverse=True)
        return matches[:top_k]

    async def _publish_event(
        self,
        event_type: str,
        aggregate_id: str,
        payload: Dict[str, Any]
    ) -> None:
        """Publish event to Redis if available."""
        if not self.redis_client:
            return

        try:
            await self.redis_client.publish_event(
                event_type=event_type,
                aggregate_type="role",
                aggregate_id=aggregate_id,
                payload=payload
            )
        except Exception as e:
            logger.warning(f"Failed to publish event: {e}")

    async def get_statistics(self) -> Dict[str, Any]:
        """
        Get registry statistics.

        Returns:
            Dictionary of statistics
        """
        roles = list(self._roles.values())

        by_department: Dict[str, int] = {}
        by_type: Dict[str, int] = {}
        by_status: Dict[str, int] = {}

        for role in roles:
            by_department[role.department] = by_department.get(role.department, 0) + 1
            by_type[role.role_type.value] = by_type.get(role.role_type.value, 0) + 1
            by_status[role.status.value] = by_status.get(role.status.value, 0) + 1

        return {
            "total_roles": len(roles),
            "active_roles": len([r for r in roles if r.status == RoleStatus.ACTIVE]),
            "by_department": by_department,
            "by_type": by_type,
            "by_status": by_status,
            "average_priority": sum(r.priority for r in roles) / len(roles) if roles else 0,
        }
