"""
Role Context Builder Service for L13 Role Management Layer.

Assembles comprehensive role contexts including skills, project context,
and constraints within specified token budgets.
"""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime

from ..models import (
    Role,
    RoleContext,
    TaskRequirements,
    Skill,
    SkillLevel,
)

logger = logging.getLogger(__name__)


class RoleContextBuilder:
    """
    Builder service for assembling role execution contexts.

    Constructs complete context packages that include role information,
    skill descriptions, project context, and constraints, all fitted
    within the specified token budget.
    """

    # Approximate tokens per character (conservative estimate)
    CHARS_PER_TOKEN = 4

    def __init__(
        self,
        project_context_provider=None,
        example_provider=None,
        default_token_budget: int = 4000,
    ):
        """
        Initialize the context builder.

        Args:
            project_context_provider: Optional service for project context
            example_provider: Optional service for example retrieval
            default_token_budget: Default token budget if not specified
        """
        self.project_context_provider = project_context_provider
        self.example_provider = example_provider
        self.default_token_budget = default_token_budget

    async def build_context(
        self,
        role: Role,
        task_requirements: Optional[TaskRequirements] = None,
        additional_context: Optional[str] = None,
        include_examples: bool = True,
        token_budget_override: Optional[int] = None,
    ) -> RoleContext:
        """
        Build a complete context for a role.

        Args:
            role: The role to build context for
            task_requirements: Optional task-specific requirements
            additional_context: Optional additional context to include
            include_examples: Whether to include behavioral examples
            token_budget_override: Override the role's token budget

        Returns:
            Complete RoleContext
        """
        token_budget = token_budget_override or role.token_budget or self.default_token_budget
        logger.debug(f"Building context for role {role.name} with budget {token_budget}")

        # Track token usage
        token_usage: Dict[str, int] = {}
        remaining_budget = token_budget

        # Step 1: Build system prompt (priority)
        system_prompt = self._build_system_prompt(role, task_requirements)
        system_tokens = self._estimate_tokens(system_prompt)
        token_usage["system_prompt"] = system_tokens
        remaining_budget -= system_tokens

        # Step 2: Build skill context
        skill_context = self._build_skill_context(role.skills, remaining_budget // 3)
        skill_tokens = self._estimate_tokens(skill_context)
        token_usage["skill_context"] = skill_tokens
        remaining_budget -= skill_tokens

        # Step 3: Build constraints context
        constraints_context = self._build_constraints_context(role.constraints, remaining_budget // 4)
        constraints_tokens = self._estimate_tokens(constraints_context)
        token_usage["constraints_context"] = constraints_tokens
        remaining_budget -= constraints_tokens

        # Step 4: Get project context if available
        project_context = ""
        if self.project_context_provider and remaining_budget > 200:
            try:
                project_context = await self._get_project_context(
                    role=role,
                    task_requirements=task_requirements,
                    max_tokens=remaining_budget // 2,
                )
                project_tokens = self._estimate_tokens(project_context)
                token_usage["project_context"] = project_tokens
                remaining_budget -= project_tokens
            except Exception as e:
                logger.warning(f"Failed to get project context: {e}")

        # Step 5: Get examples if requested and budget allows
        examples: List[str] = []
        if include_examples and remaining_budget > 300:
            examples = await self._get_examples(
                role=role,
                task_requirements=task_requirements,
                max_tokens=remaining_budget,
            )
            example_tokens = sum(self._estimate_tokens(e) for e in examples)
            token_usage["examples"] = example_tokens
            remaining_budget -= example_tokens

        # Step 6: Add additional context if provided and budget allows
        if additional_context and remaining_budget > 100:
            additional_tokens = self._estimate_tokens(additional_context)
            if additional_tokens <= remaining_budget:
                # Append to project context
                if project_context:
                    project_context = f"{project_context}\n\n{additional_context}"
                else:
                    project_context = additional_context
                token_usage["additional_context"] = additional_tokens
                remaining_budget -= additional_tokens

        # Calculate totals
        total_tokens = sum(token_usage.values())
        budget_utilization = total_tokens / token_budget if token_budget > 0 else 0

        return RoleContext(
            role=role,
            system_prompt=system_prompt,
            skill_context=skill_context,
            project_context=project_context,
            constraints_context=constraints_context,
            examples=examples,
            token_count=total_tokens,
            token_budget=token_budget,
            budget_utilization=budget_utilization,
            metadata={
                "token_breakdown": token_usage,
                "remaining_budget": remaining_budget,
                "task_description": task_requirements.task_description if task_requirements else None,
            },
            created_at=datetime.utcnow(),
        )

    def _build_system_prompt(
        self,
        role: Role,
        task_requirements: Optional[TaskRequirements] = None,
    ) -> str:
        """
        Build the system prompt for a role.

        Args:
            role: The role
            task_requirements: Optional task requirements

        Returns:
            System prompt string
        """
        lines = [
            f"# Role: {role.name}",
            f"Department: {role.department}",
            "",
            "## Description",
            role.description,
            "",
        ]

        if role.responsibilities:
            lines.extend([
                "## Responsibilities",
                *[f"- {r}" for r in role.responsibilities],
                "",
            ])

        if task_requirements:
            lines.extend([
                "## Current Task",
                task_requirements.task_description,
                "",
            ])

            if task_requirements.required_skills:
                lines.extend([
                    "### Required Skills for This Task",
                    ", ".join(task_requirements.required_skills),
                    "",
                ])

        lines.extend([
            "## Role Classification",
            f"Type: {role.role_type.value}",
            f"Priority: {role.priority}/10",
            "",
        ])

        return "\n".join(lines)

    def _build_skill_context(
        self,
        skills: List[Skill],
        max_tokens: int,
    ) -> str:
        """
        Build skill context string within token budget.

        Args:
            skills: List of skills
            max_tokens: Maximum tokens to use

        Returns:
            Skill context string
        """
        if not skills:
            return ""

        lines = ["## Skills and Expertise", ""]

        # Sort by weight (importance) descending
        sorted_skills = sorted(skills, key=lambda s: s.weight, reverse=True)

        current_tokens = self._estimate_tokens("\n".join(lines))

        for skill in sorted_skills:
            skill_line = f"### {skill.name} ({skill.level.value})"
            skill_desc = skill.description or f"Proficient in {skill.name}"
            skill_block = f"{skill_line}\n{skill_desc}\n"

            if skill.keywords:
                skill_block += f"Keywords: {', '.join(skill.keywords)}\n"

            block_tokens = self._estimate_tokens(skill_block)

            if current_tokens + block_tokens > max_tokens:
                # Try to add a summary instead
                remaining = max_tokens - current_tokens
                if remaining > 50:
                    remaining_skills = [s.name for s in sorted_skills if s.name not in "\n".join(lines)]
                    summary = f"\nAdditional skills: {', '.join(remaining_skills[:5])}"
                    if len(remaining_skills) > 5:
                        summary += f" (+{len(remaining_skills) - 5} more)"
                    lines.append(summary)
                break

            lines.append(skill_block)
            current_tokens += block_tokens

        return "\n".join(lines)

    def _build_constraints_context(
        self,
        constraints: Dict[str, Any],
        max_tokens: int,
    ) -> str:
        """
        Build constraints context string.

        Args:
            constraints: Constraints dictionary
            max_tokens: Maximum tokens to use

        Returns:
            Constraints context string
        """
        if not constraints:
            return ""

        lines = ["## Constraints and Guidelines", ""]

        current_tokens = self._estimate_tokens("\n".join(lines))

        # Common constraint categories
        categories = {
            "must": "Must Do",
            "must_not": "Must Not Do",
            "should": "Should Do",
            "avoid": "Avoid",
            "limits": "Limits",
            "permissions": "Permissions",
        }

        for key, label in categories.items():
            if key in constraints:
                value = constraints[key]
                if isinstance(value, list):
                    section = f"### {label}\n" + "\n".join(f"- {item}" for item in value)
                else:
                    section = f"### {label}\n{value}"

                section_tokens = self._estimate_tokens(section)
                if current_tokens + section_tokens > max_tokens:
                    break

                lines.append(section)
                lines.append("")
                current_tokens += section_tokens

        # Handle remaining constraints
        remaining = {k: v for k, v in constraints.items() if k not in categories}
        if remaining and current_tokens < max_tokens - 100:
            lines.append("### Other Constraints")
            for key, value in remaining.items():
                line = f"- {key}: {value}"
                line_tokens = self._estimate_tokens(line)
                if current_tokens + line_tokens > max_tokens:
                    break
                lines.append(line)
                current_tokens += line_tokens

        return "\n".join(lines)

    async def _get_project_context(
        self,
        role: Role,
        task_requirements: Optional[TaskRequirements],
        max_tokens: int,
    ) -> str:
        """
        Get relevant project context.

        Args:
            role: The role
            task_requirements: Task requirements
            max_tokens: Maximum tokens

        Returns:
            Project context string
        """
        if not self.project_context_provider:
            return ""

        try:
            # Call the provider with role and task info
            context = await self.project_context_provider.get_context(
                role_name=role.name,
                department=role.department,
                task_description=task_requirements.task_description if task_requirements else None,
                max_chars=max_tokens * self.CHARS_PER_TOKEN,
            )
            return context or ""
        except Exception as e:
            logger.warning(f"Project context retrieval failed: {e}")
            return ""

    async def _get_examples(
        self,
        role: Role,
        task_requirements: Optional[TaskRequirements],
        max_tokens: int,
    ) -> List[str]:
        """
        Get behavioral examples for the role.

        Args:
            role: The role
            task_requirements: Task requirements
            max_tokens: Maximum tokens

        Returns:
            List of example strings
        """
        examples: List[str] = []

        # Use example provider if available
        if self.example_provider:
            try:
                provider_examples = await self.example_provider.get_examples(
                    role_name=role.name,
                    skills=[s.name for s in role.skills],
                    max_examples=5,
                )
                examples.extend(provider_examples)
            except Exception as e:
                logger.warning(f"Example retrieval failed: {e}")

        # Generate default examples based on skills if none provided
        if not examples:
            examples = self._generate_default_examples(role)

        # Trim to fit budget
        current_tokens = 0
        trimmed_examples: List[str] = []

        for example in examples:
            example_tokens = self._estimate_tokens(example)
            if current_tokens + example_tokens > max_tokens:
                break
            trimmed_examples.append(example)
            current_tokens += example_tokens

        return trimmed_examples

    def _generate_default_examples(self, role: Role) -> List[str]:
        """
        Generate default examples based on role definition.

        Args:
            role: The role

        Returns:
            List of example strings
        """
        examples = []

        # Generate skill-based examples
        for skill in role.skills[:3]:  # Top 3 skills
            level_adverb = {
                SkillLevel.NOVICE: "basic",
                SkillLevel.INTERMEDIATE: "competent",
                SkillLevel.ADVANCED: "advanced",
                SkillLevel.EXPERT: "expert-level",
            }.get(skill.level, "competent")

            example = f"Example: When working with {skill.name}, demonstrate {level_adverb} proficiency."
            examples.append(example)

        # Add responsibility-based examples
        for resp in role.responsibilities[:2]:
            example = f"Example behavior: {resp}"
            examples.append(example)

        return examples

    def _estimate_tokens(self, text: str) -> int:
        """
        Estimate token count for text.

        Uses a simple character-based estimation.

        Args:
            text: Text to estimate

        Returns:
            Estimated token count
        """
        if not text:
            return 0
        return len(text) // self.CHARS_PER_TOKEN + 1

    async def build_minimal_context(self, role: Role) -> RoleContext:
        """
        Build a minimal context for quick operations.

        Args:
            role: The role

        Returns:
            Minimal RoleContext
        """
        system_prompt = f"You are: {role.name} ({role.department})\n{role.description}"
        skill_context = ", ".join(s.name for s in role.skills)

        return RoleContext(
            role=role,
            system_prompt=system_prompt,
            skill_context=skill_context,
            project_context="",
            constraints_context="",
            examples=[],
            token_count=self._estimate_tokens(system_prompt + skill_context),
            token_budget=role.token_budget,
            budget_utilization=0.1,
            metadata={"minimal": True},
            created_at=datetime.utcnow(),
        )

    async def extend_context(
        self,
        context: RoleContext,
        additional_content: str,
        section: str = "project",
    ) -> RoleContext:
        """
        Extend an existing context with additional content.

        Args:
            context: Existing context
            additional_content: Content to add
            section: Which section to add to (project, examples, constraints)

        Returns:
            Extended RoleContext
        """
        additional_tokens = self._estimate_tokens(additional_content)
        new_total = context.token_count + additional_tokens

        if new_total > context.token_budget:
            # Truncate to fit
            available_chars = (context.token_budget - context.token_count) * self.CHARS_PER_TOKEN
            additional_content = additional_content[:available_chars]
            additional_tokens = self._estimate_tokens(additional_content)
            new_total = context.token_count + additional_tokens

        # Create new context with additions
        new_context = RoleContext(
            role=context.role,
            system_prompt=context.system_prompt,
            skill_context=context.skill_context,
            project_context=context.project_context,
            constraints_context=context.constraints_context,
            examples=list(context.examples),
            token_count=new_total,
            token_budget=context.token_budget,
            budget_utilization=new_total / context.token_budget,
            metadata={**context.metadata, "extended": True},
            created_at=context.created_at,
        )

        if section == "project":
            new_context.project_context = f"{context.project_context}\n\n{additional_content}".strip()
        elif section == "examples":
            new_context.examples.append(additional_content)
        elif section == "constraints":
            new_context.constraints_context = f"{context.constraints_context}\n\n{additional_content}".strip()

        return new_context
