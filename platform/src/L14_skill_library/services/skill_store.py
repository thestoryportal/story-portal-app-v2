"""
L14 Skill Library - Skill Store Service

Provides CRUD operations for skill management with in-memory storage
and optional persistence to L01 Data Layer.
"""

import logging
from typing import Dict, List, Optional
from uuid import UUID
from datetime import datetime

from ..models import (
    Skill,
    SkillCreate,
    SkillUpdate,
    SkillDefinition,
    SkillMetadata,
    SkillRole,
    SkillResponsibilities,
    SkillTools,
    SkillConstraints,
    SkillDependencies,
    SkillStatus,
    SkillPriority,
    SkillCategory,
)

logger = logging.getLogger(__name__)


class SkillStore:
    """
    Skill Store Service

    Manages CRUD operations for skills with in-memory caching
    and optional persistence to L01 Data Layer.
    """

    def __init__(self, l01_client=None):
        """
        Initialize the Skill Store.

        Args:
            l01_client: Optional L01Client for persistence
        """
        self._skills: Dict[UUID, Skill] = {}
        self._name_index: Dict[str, UUID] = {}
        self._agent_index: Dict[UUID, List[UUID]] = {}
        self._category_index: Dict[SkillCategory, List[UUID]] = {}
        self._l01_client = l01_client
        logger.info("SkillStore initialized")

    async def create(self, skill_data: SkillCreate) -> Skill:
        """
        Create a new skill.

        Args:
            skill_data: Skill creation data

        Returns:
            Created Skill object

        Raises:
            ValueError: If skill with same name exists
        """
        if skill_data.name in self._name_index:
            raise ValueError(f"Skill with name '{skill_data.name}' already exists")

        # Build skill definition
        metadata = SkillMetadata(
            name=skill_data.name,
            tags=skill_data.tags,
            priority=skill_data.priority,
            category=skill_data.category,
            author=skill_data.author or "L14_skill_library",
        )

        role = SkillRole(
            title=skill_data.role_title,
            description=skill_data.role_description,
            expertise_areas=skill_data.expertise_areas,
        )

        responsibilities = SkillResponsibilities(
            primary=skill_data.primary_responsibilities,
            secondary=skill_data.secondary_responsibilities,
        )

        tools = SkillTools(
            required=skill_data.required_tools,
            optional=skill_data.optional_tools,
        )

        constraints = SkillConstraints(
            token_budget=skill_data.token_budget,
        )

        definition = SkillDefinition(
            metadata=metadata,
            role=role,
            responsibilities=responsibilities,
            tools=tools,
            constraints=constraints,
            dependencies=SkillDependencies(),
        )

        # Create skill entity
        skill = Skill(
            name=skill_data.name,
            status=SkillStatus.DRAFT,
            definition=definition,
        )

        # Update indexes
        self._skills[skill.id] = skill
        self._name_index[skill.name] = skill.id

        # Update category index
        if skill_data.category not in self._category_index:
            self._category_index[skill_data.category] = []
        self._category_index[skill_data.category].append(skill.id)

        logger.info(f"Created skill: {skill.id} ({skill.name})")
        return skill

    async def get(self, skill_id: UUID) -> Optional[Skill]:
        """
        Get a skill by ID.

        Args:
            skill_id: Skill UUID

        Returns:
            Skill if found, None otherwise
        """
        return self._skills.get(skill_id)

    async def get_by_name(self, name: str) -> Optional[Skill]:
        """
        Get a skill by name.

        Args:
            name: Skill name

        Returns:
            Skill if found, None otherwise
        """
        skill_id = self._name_index.get(name)
        if skill_id:
            return self._skills.get(skill_id)
        return None

    async def list(
        self,
        status: Optional[SkillStatus] = None,
        category: Optional[SkillCategory] = None,
        priority: Optional[SkillPriority] = None,
        agent_id: Optional[UUID] = None,
        tags: Optional[List[str]] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Skill]:
        """
        List skills with optional filtering.

        Args:
            status: Filter by status
            category: Filter by category
            priority: Filter by priority
            agent_id: Filter by associated agent
            tags: Filter by tags (any match)
            limit: Maximum number of results
            offset: Offset for pagination

        Returns:
            List of matching skills
        """
        skills = list(self._skills.values())

        # Apply filters
        if status:
            skills = [s for s in skills if s.status == status]

        if category:
            skills = [s for s in skills if s.definition.metadata.category == category]

        if priority:
            skills = [s for s in skills if s.definition.metadata.priority == priority]

        if agent_id:
            skills = [s for s in skills if s.agent_id == agent_id]

        if tags:
            skills = [
                s for s in skills
                if any(tag in s.definition.metadata.tags for tag in tags)
            ]

        # Sort by priority and creation date
        priority_order = {
            SkillPriority.CRITICAL: 0,
            SkillPriority.HIGH: 1,
            SkillPriority.MEDIUM: 2,
            SkillPriority.LOW: 3,
            SkillPriority.OPTIONAL: 4,
        }
        skills.sort(
            key=lambda s: (
                priority_order.get(s.definition.metadata.priority, 5),
                s.created_at,
            )
        )

        # Apply pagination
        return skills[offset:offset + limit]

    async def update(self, skill_id: UUID, update_data: SkillUpdate) -> Optional[Skill]:
        """
        Update an existing skill.

        Args:
            skill_id: Skill UUID
            update_data: Update data

        Returns:
            Updated Skill if found, None otherwise
        """
        skill = self._skills.get(skill_id)
        if not skill:
            return None

        # Track old name for index update
        old_name = skill.name

        # Update fields
        update_dict = update_data.model_dump(exclude_unset=True)

        if "name" in update_dict and update_dict["name"]:
            new_name = update_dict["name"]
            if new_name != old_name and new_name in self._name_index:
                raise ValueError(f"Skill with name '{new_name}' already exists")
            skill.name = new_name
            skill.definition.metadata.name = new_name
            # Update name index
            del self._name_index[old_name]
            self._name_index[new_name] = skill_id

        if "role_title" in update_dict and update_dict["role_title"]:
            skill.definition.role.title = update_dict["role_title"]

        if "role_description" in update_dict and update_dict["role_description"]:
            skill.definition.role.description = update_dict["role_description"]

        if "expertise_areas" in update_dict and update_dict["expertise_areas"] is not None:
            skill.definition.role.expertise_areas = update_dict["expertise_areas"]

        if "primary_responsibilities" in update_dict and update_dict["primary_responsibilities"] is not None:
            skill.definition.responsibilities.primary = update_dict["primary_responsibilities"]

        if "secondary_responsibilities" in update_dict and update_dict["secondary_responsibilities"] is not None:
            skill.definition.responsibilities.secondary = update_dict["secondary_responsibilities"]

        if "required_tools" in update_dict and update_dict["required_tools"] is not None:
            skill.definition.tools.required = update_dict["required_tools"]

        if "optional_tools" in update_dict and update_dict["optional_tools"] is not None:
            skill.definition.tools.optional = update_dict["optional_tools"]

        if "tags" in update_dict and update_dict["tags"] is not None:
            skill.definition.metadata.tags = update_dict["tags"]

        if "priority" in update_dict and update_dict["priority"]:
            skill.definition.metadata.priority = update_dict["priority"]

        if "category" in update_dict and update_dict["category"]:
            old_category = skill.definition.metadata.category
            new_category = update_dict["category"]
            skill.definition.metadata.category = new_category
            # Update category index
            if old_category in self._category_index:
                self._category_index[old_category].remove(skill_id)
            if new_category not in self._category_index:
                self._category_index[new_category] = []
            self._category_index[new_category].append(skill_id)

        if "status" in update_dict and update_dict["status"]:
            skill.status = update_dict["status"]

        if "token_budget" in update_dict and update_dict["token_budget"]:
            skill.definition.constraints.token_budget = update_dict["token_budget"]

        # Update timestamps
        skill.updated_at = datetime.utcnow()
        skill.definition.metadata.updated_at = datetime.utcnow()

        logger.info(f"Updated skill: {skill_id}")
        return skill

    async def delete(self, skill_id: UUID) -> bool:
        """
        Delete a skill.

        Args:
            skill_id: Skill UUID

        Returns:
            True if deleted, False if not found
        """
        skill = self._skills.get(skill_id)
        if not skill:
            return False

        # Remove from indexes
        del self._skills[skill_id]
        if skill.name in self._name_index:
            del self._name_index[skill.name]

        category = skill.definition.metadata.category
        if category in self._category_index and skill_id in self._category_index[category]:
            self._category_index[category].remove(skill_id)

        if skill.agent_id and skill.agent_id in self._agent_index:
            if skill_id in self._agent_index[skill.agent_id]:
                self._agent_index[skill.agent_id].remove(skill_id)

        logger.info(f"Deleted skill: {skill_id}")
        return True

    async def assign_to_agent(self, skill_id: UUID, agent_id: UUID) -> Optional[Skill]:
        """
        Assign a skill to an agent.

        Args:
            skill_id: Skill UUID
            agent_id: Agent UUID

        Returns:
            Updated Skill if found, None otherwise
        """
        skill = self._skills.get(skill_id)
        if not skill:
            return None

        # Update agent assignment
        old_agent_id = skill.agent_id
        skill.agent_id = agent_id
        skill.updated_at = datetime.utcnow()

        # Update agent index
        if old_agent_id and old_agent_id in self._agent_index:
            if skill_id in self._agent_index[old_agent_id]:
                self._agent_index[old_agent_id].remove(skill_id)

        if agent_id not in self._agent_index:
            self._agent_index[agent_id] = []
        self._agent_index[agent_id].append(skill_id)

        logger.info(f"Assigned skill {skill_id} to agent {agent_id}")
        return skill

    async def get_agent_skills(
        self,
        agent_id: UUID,
        active_only: bool = True,
    ) -> List[Skill]:
        """
        Get all skills assigned to an agent.

        Args:
            agent_id: Agent UUID
            active_only: Only return active skills

        Returns:
            List of skills
        """
        skill_ids = self._agent_index.get(agent_id, [])
        skills = [self._skills[sid] for sid in skill_ids if sid in self._skills]

        if active_only:
            skills = [s for s in skills if s.status == SkillStatus.ACTIVE]

        return skills

    async def activate(self, skill_id: UUID) -> Optional[Skill]:
        """
        Activate a skill.

        Args:
            skill_id: Skill UUID

        Returns:
            Updated Skill if found, None otherwise
        """
        return await self.update(
            skill_id,
            SkillUpdate(status=SkillStatus.ACTIVE)
        )

    async def deprecate(self, skill_id: UUID) -> Optional[Skill]:
        """
        Deprecate a skill.

        Args:
            skill_id: Skill UUID

        Returns:
            Updated Skill if found, None otherwise
        """
        return await self.update(
            skill_id,
            SkillUpdate(status=SkillStatus.DEPRECATED)
        )

    async def get_stats(self) -> Dict:
        """
        Get skill store statistics.

        Returns:
            Dictionary with store statistics
        """
        skills = list(self._skills.values())

        status_counts = {}
        for status in SkillStatus:
            status_counts[status.value] = sum(
                1 for s in skills if s.status == status
            )

        category_counts = {}
        for category in SkillCategory:
            category_counts[category.value] = len(
                self._category_index.get(category, [])
            )

        priority_counts = {}
        for priority in SkillPriority:
            priority_counts[priority.value] = sum(
                1 for s in skills
                if s.definition.metadata.priority == priority
            )

        return {
            "total_skills": len(skills),
            "by_status": status_counts,
            "by_category": category_counts,
            "by_priority": priority_counts,
            "agents_with_skills": len(self._agent_index),
        }
