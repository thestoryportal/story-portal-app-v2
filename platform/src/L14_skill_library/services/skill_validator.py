"""
L14 Skill Library - Skill Validator Service

Validates skill files against the schema and checks for common issues.
"""

import logging
import yaml
from typing import List, Optional, Dict, Any
from uuid import UUID

from ..models import (
    Skill,
    SkillDefinition,
    SkillValidationResult,
    ValidationIssue,
    ValidationSeverity,
    SKILL_FILE_SCHEMA,
)

logger = logging.getLogger(__name__)


class SkillValidator:
    """
    Skill Validator Service

    Validates skill files for schema compliance, content quality,
    and potential issues.
    """

    def __init__(self):
        """Initialize the Skill Validator."""
        self._schema = SKILL_FILE_SCHEMA
        self._required_sections = self._schema.get("required_sections", [])
        self._optional_sections = self._schema.get("optional_sections", [])
        logger.info("SkillValidator initialized")

    async def validate(self, skill: Skill) -> SkillValidationResult:
        """
        Validate a skill object.

        Args:
            skill: Skill to validate

        Returns:
            SkillValidationResult with validation status and issues
        """
        issues: List[ValidationIssue] = []

        # Validate definition structure
        issues.extend(self._validate_definition(skill.definition))

        # Validate content quality
        issues.extend(self._validate_content_quality(skill.definition))

        # Validate dependencies
        issues.extend(self._validate_dependencies(skill.definition))

        # Check for common issues
        issues.extend(self._check_common_issues(skill))

        return SkillValidationResult.failure(
            issues=issues,
            skill_id=skill.id,
            skill_name=skill.name,
        ) if issues else SkillValidationResult.success(
            skill_id=skill.id,
            skill_name=skill.name,
        )

    async def validate_yaml(self, yaml_content: str) -> SkillValidationResult:
        """
        Validate skill file from YAML content.

        Args:
            yaml_content: YAML string content

        Returns:
            SkillValidationResult
        """
        issues: List[ValidationIssue] = []

        # Try to parse YAML
        try:
            data = yaml.safe_load(yaml_content)
        except yaml.YAMLError as e:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                code="YAML_PARSE_ERROR",
                message=f"Failed to parse YAML: {str(e)}",
                suggestion="Check YAML syntax and formatting",
            ))
            return SkillValidationResult.failure(issues=issues)

        if not isinstance(data, dict):
            issues.append(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                code="INVALID_STRUCTURE",
                message="Skill file must be a YAML dictionary",
                suggestion="Ensure the file starts with valid YAML structure",
            ))
            return SkillValidationResult.failure(issues=issues)

        # Extract skill name and ID from parsed content
        metadata = data.get("metadata", {})
        skill_name = metadata.get("name")
        skill_id = metadata.get("skill_id")

        # Validate required sections
        issues.extend(self._validate_required_sections(data))

        # Validate each section
        issues.extend(self._validate_metadata_section(data.get("metadata", {})))
        issues.extend(self._validate_role_section(data.get("role", {})))
        issues.extend(self._validate_responsibilities_section(data.get("responsibilities", {})))

        # Validate optional sections if present
        if "tools" in data:
            issues.extend(self._validate_tools_section(data["tools"]))

        if "procedures" in data:
            issues.extend(self._validate_procedures_section(data["procedures"]))

        if "examples" in data:
            issues.extend(self._validate_examples_section(data["examples"]))

        if "constraints" in data:
            issues.extend(self._validate_constraints_section(data["constraints"]))

        return SkillValidationResult.failure(
            issues=issues,
            skill_name=skill_name,
        ) if issues else SkillValidationResult.success(skill_name=skill_name)

    def _validate_required_sections(self, data: Dict[str, Any]) -> List[ValidationIssue]:
        """Validate that all required sections are present."""
        issues = []

        for section in self._required_sections:
            if section not in data:
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    code="MISSING_REQUIRED_SECTION",
                    message=f"Missing required section: '{section}'",
                    path=section,
                    suggestion=f"Add the '{section}' section to your skill file",
                ))
            elif data[section] is None:
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    code="EMPTY_REQUIRED_SECTION",
                    message=f"Required section '{section}' is empty",
                    path=section,
                    suggestion=f"Add content to the '{section}' section",
                ))

        return issues

    def _validate_metadata_section(self, metadata: Dict[str, Any]) -> List[ValidationIssue]:
        """Validate the metadata section."""
        issues = []

        if not metadata:
            return issues  # Already handled by required sections check

        # Check required metadata fields
        required_fields = ["name"]
        for field in required_fields:
            if field not in metadata or not metadata[field]:
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    code="MISSING_METADATA_FIELD",
                    message=f"Missing required metadata field: '{field}'",
                    path=f"metadata.{field}",
                    suggestion=f"Add '{field}' to the metadata section",
                ))

        # Validate name format
        name = metadata.get("name", "")
        if name and not name.replace("_", "").replace("-", "").isalnum():
            issues.append(ValidationIssue(
                severity=ValidationSeverity.WARNING,
                code="INVALID_NAME_FORMAT",
                message="Skill name should contain only alphanumeric characters, underscores, and hyphens",
                path="metadata.name",
                suggestion="Use snake_case or kebab-case for skill names",
            ))

        # Validate priority if present
        valid_priorities = ["critical", "high", "medium", "low", "optional"]
        priority = metadata.get("priority", "medium")
        if priority and priority not in valid_priorities:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.WARNING,
                code="INVALID_PRIORITY",
                message=f"Invalid priority: '{priority}'",
                path="metadata.priority",
                suggestion=f"Use one of: {', '.join(valid_priorities)}",
            ))

        # Validate tags
        tags = metadata.get("tags", [])
        if tags and not isinstance(tags, list):
            issues.append(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                code="INVALID_TAGS_FORMAT",
                message="Tags must be a list",
                path="metadata.tags",
                suggestion="Use a YAML list format for tags",
            ))

        return issues

    def _validate_role_section(self, role: Dict[str, Any]) -> List[ValidationIssue]:
        """Validate the role section."""
        issues = []

        if not role:
            return issues

        # Check required role fields
        if not role.get("title"):
            issues.append(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                code="MISSING_ROLE_TITLE",
                message="Role section missing 'title'",
                path="role.title",
                suggestion="Add a title to the role section",
            ))

        if not role.get("description"):
            issues.append(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                code="MISSING_ROLE_DESCRIPTION",
                message="Role section missing 'description'",
                path="role.description",
                suggestion="Add a description to the role section",
            ))

        # Check description length
        description = role.get("description", "")
        if len(description) < 20:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.WARNING,
                code="SHORT_ROLE_DESCRIPTION",
                message="Role description is too short (< 20 characters)",
                path="role.description",
                suggestion="Provide a more detailed role description",
            ))

        # Validate expertise areas
        expertise = role.get("expertise_areas", [])
        if expertise and not isinstance(expertise, list):
            issues.append(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                code="INVALID_EXPERTISE_FORMAT",
                message="Expertise areas must be a list",
                path="role.expertise_areas",
                suggestion="Use a YAML list format for expertise areas",
            ))

        return issues

    def _validate_responsibilities_section(self, responsibilities: Dict[str, Any]) -> List[ValidationIssue]:
        """Validate the responsibilities section."""
        issues = []

        if not responsibilities:
            return issues

        # Check primary responsibilities
        primary = responsibilities.get("primary", [])
        if not primary:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                code="MISSING_PRIMARY_RESPONSIBILITIES",
                message="No primary responsibilities defined",
                path="responsibilities.primary",
                suggestion="Add at least one primary responsibility",
            ))
        elif not isinstance(primary, list):
            issues.append(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                code="INVALID_RESPONSIBILITIES_FORMAT",
                message="Primary responsibilities must be a list",
                path="responsibilities.primary",
                suggestion="Use a YAML list format for responsibilities",
            ))

        return issues

    def _validate_tools_section(self, tools: Dict[str, Any]) -> List[ValidationIssue]:
        """Validate the tools section."""
        issues = []

        if not isinstance(tools, dict):
            issues.append(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                code="INVALID_TOOLS_FORMAT",
                message="Tools section must be a dictionary",
                path="tools",
                suggestion="Structure tools with 'required' and 'optional' keys",
            ))
            return issues

        for key in ["required", "optional"]:
            if key in tools and not isinstance(tools[key], list):
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    code=f"INVALID_TOOLS_{key.upper()}_FORMAT",
                    message=f"Tools '{key}' must be a list",
                    path=f"tools.{key}",
                    suggestion=f"Use a YAML list for {key} tools",
                ))

        return issues

    def _validate_procedures_section(self, procedures: Any) -> List[ValidationIssue]:
        """Validate the procedures section."""
        issues = []

        if not isinstance(procedures, list):
            issues.append(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                code="INVALID_PROCEDURES_FORMAT",
                message="Procedures must be a list",
                path="procedures",
                suggestion="Use a YAML list for procedures",
            ))
            return issues

        for i, proc in enumerate(procedures):
            if not isinstance(proc, dict):
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    code="INVALID_PROCEDURE_FORMAT",
                    message=f"Procedure {i} must be a dictionary",
                    path=f"procedures[{i}]",
                ))
                continue

            if not proc.get("name"):
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.WARNING,
                    code="MISSING_PROCEDURE_NAME",
                    message=f"Procedure {i} missing name",
                    path=f"procedures[{i}].name",
                    suggestion="Add a name to identify this procedure",
                ))

            steps = proc.get("steps", [])
            if not steps:
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.WARNING,
                    code="EMPTY_PROCEDURE_STEPS",
                    message=f"Procedure '{proc.get('name', i)}' has no steps",
                    path=f"procedures[{i}].steps",
                    suggestion="Add steps to define the procedure workflow",
                ))

        return issues

    def _validate_examples_section(self, examples: Any) -> List[ValidationIssue]:
        """Validate the examples section."""
        issues = []

        if not isinstance(examples, list):
            issues.append(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                code="INVALID_EXAMPLES_FORMAT",
                message="Examples must be a list",
                path="examples",
                suggestion="Use a YAML list for examples",
            ))
            return issues

        for i, example in enumerate(examples):
            if not isinstance(example, dict):
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    code="INVALID_EXAMPLE_FORMAT",
                    message=f"Example {i} must be a dictionary",
                    path=f"examples[{i}]",
                ))
                continue

            required_fields = ["user_input", "expected_response"]
            for field in required_fields:
                if not example.get(field):
                    issues.append(ValidationIssue(
                        severity=ValidationSeverity.WARNING,
                        code=f"MISSING_EXAMPLE_{field.upper()}",
                        message=f"Example {i} missing '{field}'",
                        path=f"examples[{i}].{field}",
                    ))

        return issues

    def _validate_constraints_section(self, constraints: Dict[str, Any]) -> List[ValidationIssue]:
        """Validate the constraints section."""
        issues = []

        if not isinstance(constraints, dict):
            issues.append(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                code="INVALID_CONSTRAINTS_FORMAT",
                message="Constraints must be a dictionary",
                path="constraints",
            ))
            return issues

        # Validate token budget
        token_budget = constraints.get("token_budget", 0)
        if token_budget and token_budget < 100:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.WARNING,
                code="LOW_TOKEN_BUDGET",
                message="Token budget is very low (< 100)",
                path="constraints.token_budget",
                suggestion="Consider a higher token budget for better context",
            ))

        if token_budget and token_budget > 50000:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.WARNING,
                code="HIGH_TOKEN_BUDGET",
                message="Token budget is very high (> 50000)",
                path="constraints.token_budget",
                suggestion="Consider reducing token budget to improve performance",
            ))

        return issues

    def _validate_definition(self, definition: SkillDefinition) -> List[ValidationIssue]:
        """Validate a SkillDefinition object."""
        issues = []

        # Validate metadata
        if not definition.metadata.name:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                code="MISSING_NAME",
                message="Skill name is required",
                path="metadata.name",
            ))

        # Validate role
        if not definition.role.title:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                code="MISSING_ROLE_TITLE",
                message="Role title is required",
                path="role.title",
            ))

        if not definition.role.description:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                code="MISSING_ROLE_DESCRIPTION",
                message="Role description is required",
                path="role.description",
            ))

        # Validate responsibilities
        if not definition.responsibilities.primary:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.ERROR,
                code="MISSING_PRIMARY_RESPONSIBILITIES",
                message="At least one primary responsibility is required",
                path="responsibilities.primary",
            ))

        return issues

    def _validate_content_quality(self, definition: SkillDefinition) -> List[ValidationIssue]:
        """Validate content quality of the skill definition."""
        issues = []

        # Check role description length
        if len(definition.role.description) < 20:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.WARNING,
                code="SHORT_DESCRIPTION",
                message="Role description is too short",
                path="role.description",
                suggestion="Provide a more detailed description (at least 20 characters)",
            ))

        # Check if expertise areas are provided
        if not definition.role.expertise_areas:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.INFO,
                code="NO_EXPERTISE_AREAS",
                message="No expertise areas defined",
                path="role.expertise_areas",
                suggestion="Consider adding expertise areas for better role clarity",
            ))

        # Check if tools are specified
        if not definition.tools.required and not definition.tools.optional:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.INFO,
                code="NO_TOOLS_SPECIFIED",
                message="No tools specified",
                path="tools",
                suggestion="Consider specifying required or optional tools",
            ))

        # Check if examples are provided
        if not definition.examples:
            issues.append(ValidationIssue(
                severity=ValidationSeverity.INFO,
                code="NO_EXAMPLES",
                message="No examples provided",
                path="examples",
                suggestion="Consider adding examples for better clarity",
            ))

        return issues

    def _validate_dependencies(self, definition: SkillDefinition) -> List[ValidationIssue]:
        """Validate skill dependencies."""
        issues = []

        # Check for circular dependencies (would need external context)
        # For now, just validate format

        for dep in definition.dependencies.skills:
            if not dep:
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.WARNING,
                    code="EMPTY_SKILL_DEPENDENCY",
                    message="Empty skill dependency found",
                    path="dependencies.skills",
                    suggestion="Remove empty dependencies",
                ))

        return issues

    def _check_common_issues(self, skill: Skill) -> List[ValidationIssue]:
        """Check for common issues in skills."""
        issues = []

        # Check if raw content matches definition
        if skill.raw_content:
            try:
                parsed = yaml.safe_load(skill.raw_content)
                if parsed.get("metadata", {}).get("name") != skill.definition.metadata.name:
                    issues.append(ValidationIssue(
                        severity=ValidationSeverity.WARNING,
                        code="NAME_MISMATCH",
                        message="Skill name in raw content doesn't match definition",
                        suggestion="Regenerate raw content or update definition",
                    ))
            except yaml.YAMLError:
                issues.append(ValidationIssue(
                    severity=ValidationSeverity.ERROR,
                    code="INVALID_RAW_CONTENT",
                    message="Raw content is not valid YAML",
                    suggestion="Regenerate raw content",
                ))

        return issues
