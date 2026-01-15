"""
L05 Planning Layer - Template Registry.

Registry of predefined decomposition patterns for common goal types.
"""

import logging
import re
from dataclasses import dataclass
from typing import Optional, List, Dict, Any
from uuid import uuid4

from ..models import Task, TaskType, TaskDependency, DependencyType

logger = logging.getLogger(__name__)


@dataclass
class GoalTemplate:
    """
    Template for goal decomposition.

    Contains pattern matching rules and task generation logic.
    """

    template_id: str  # Unique template ID
    name: str  # Template name
    description: str  # Template description
    patterns: List[str]  # Regex patterns to match goal text
    task_templates: List[Dict[str, Any]]  # Task generation templates
    metadata: Dict[str, Any]  # Additional metadata


@dataclass
class TemplateMatch:
    """Result of template matching."""

    template: GoalTemplate  # Matched template
    confidence: float  # Match confidence (0.0-1.0)
    extracted_params: Dict[str, Any]  # Extracted parameters


class TemplateRegistry:
    """
    Registry of goal decomposition templates.

    Provides template matching and instantiation for common goal patterns.
    """

    def __init__(self):
        """Initialize template registry."""
        self._templates: Dict[str, GoalTemplate] = {}
        logger.info("TemplateRegistry initialized")

    def register_template(self, template: GoalTemplate) -> None:
        """
        Register a goal template.

        Args:
            template: GoalTemplate to register
        """
        self._templates[template.template_id] = template
        logger.debug(f"Registered template: {template.name}")

    def find_similar(self, goal_text: str) -> Optional[TemplateMatch]:
        """
        Find best matching template for goal text.

        Args:
            goal_text: Goal text to match

        Returns:
            TemplateMatch if found, None otherwise
        """
        best_match: Optional[TemplateMatch] = None
        best_confidence = 0.0

        for template in self._templates.values():
            match = self._match_template(template, goal_text)
            if match and match.confidence > best_confidence:
                best_match = match
                best_confidence = match.confidence

        return best_match

    def find_best_match(self, goal_text: str) -> Optional[GoalTemplate]:
        """
        Find best matching template (returns template directly).

        Args:
            goal_text: Goal text to match

        Returns:
            GoalTemplate if found, None otherwise
        """
        match = self.find_similar(goal_text)
        return match.template if match else None

    def _match_template(self, template: GoalTemplate, goal_text: str) -> Optional[TemplateMatch]:
        """
        Match template against goal text.

        Args:
            template: Template to match
            goal_text: Goal text

        Returns:
            TemplateMatch if matches, None otherwise
        """
        goal_lower = goal_text.lower()

        for pattern in template.patterns:
            # Try regex match
            match = re.search(pattern, goal_lower, re.IGNORECASE)
            if match:
                # Extract parameters from regex groups
                extracted_params = match.groupdict() if match.groupdict() else {}

                # Calculate confidence based on match quality
                confidence = self._calculate_confidence(pattern, goal_text, match)

                return TemplateMatch(
                    template=template,
                    confidence=confidence,
                    extracted_params=extracted_params,
                )

        return None

    def _calculate_confidence(self, pattern: str, goal_text: str, match: re.Match) -> float:
        """
        Calculate confidence score for pattern match.

        Args:
            pattern: Regex pattern
            goal_text: Goal text
            match: Regex match object

        Returns:
            Confidence score (0.0-1.0)
        """
        # Base confidence for any match
        confidence = 0.7

        # Boost for exact or near-exact match
        matched_text = match.group(0)
        if len(matched_text) > len(goal_text) * 0.8:
            confidence += 0.2

        # Boost for capturing groups (more specific)
        if match.groups():
            confidence += 0.1

        return min(confidence, 1.0)

    def instantiate_template(
        self,
        template: GoalTemplate,
        plan_id: str,
        params: Optional[Dict[str, Any]] = None,
    ) -> List[Task]:
        """
        Instantiate template into concrete tasks.

        Args:
            template: Template to instantiate
            plan_id: Plan ID for generated tasks
            params: Optional parameters for template instantiation

        Returns:
            List of generated Task objects
        """
        params = params or {}
        tasks: List[Task] = []
        task_id_map: Dict[str, str] = {}  # Map template task IDs to actual task IDs

        for task_template in template.task_templates:
            # Generate task ID
            template_task_id = task_template.get("id", str(uuid4()))
            actual_task_id = str(uuid4())
            task_id_map[template_task_id] = actual_task_id

            # Substitute parameters in template
            name = self._substitute_params(task_template["name"], params)
            description = self._substitute_params(task_template["description"], params)

            # Create task
            task = Task.create(
                plan_id=plan_id,
                name=name,
                description=description,
                task_type=TaskType(task_template.get("type", "atomic")),
                inputs=task_template.get("inputs", {}),
                timeout_seconds=task_template.get("timeout_seconds", 300),
                tool_name=task_template.get("tool_name"),
                llm_prompt=task_template.get("llm_prompt"),
            )

            # Override task_id with our generated one
            task.task_id = actual_task_id

            # Add dependencies (will map IDs after all tasks created)
            dep_templates = task_template.get("dependencies", [])
            for dep_template in dep_templates:
                dep_task_id = dep_template.get("task_id")
                if dep_task_id in task_id_map:
                    task.dependencies.append(
                        TaskDependency(
                            task_id=task_id_map[dep_task_id],
                            dependency_type=DependencyType(dep_template.get("type", "blocking")),
                            condition=dep_template.get("condition"),
                            output_key=dep_template.get("output_key"),
                        )
                    )

            tasks.append(task)

        logger.debug(f"Instantiated template '{template.name}' into {len(tasks)} tasks")
        return tasks

    def _substitute_params(self, template_str: str, params: Dict[str, Any]) -> str:
        """
        Substitute parameters in template string.

        Args:
            template_str: Template string with {{param}} placeholders
            params: Parameter values

        Returns:
            String with parameters substituted
        """
        result = template_str
        for key, value in params.items():
            placeholder = f"{{{{{key}}}}}"
            result = result.replace(placeholder, str(value))
        return result

    def get_all_templates(self) -> List[GoalTemplate]:
        """Get all registered templates."""
        return list(self._templates.values())

    def get_template(self, template_id: str) -> Optional[GoalTemplate]:
        """Get template by ID."""
        return self._templates.get(template_id)

    def load_default_templates(self) -> None:
        """Load default templates from CommonTemplates."""
        from .common_templates import CommonTemplates

        templates = CommonTemplates.get_all_templates()
        for template in templates:
            self.register_template(template)

        logger.info(f"Loaded {len(templates)} default templates")
