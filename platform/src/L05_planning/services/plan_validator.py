"""
L05 Planning Layer - Plan Validator Service.

Three-level plan validation:
1. Syntax validation - Task format, field types, required fields
2. Semantic validation - All tasks executable, inputs available
3. Feasibility validation - Resources available, within budget
"""

import logging
from typing import List, Dict, Any
from dataclasses import dataclass

from ..models import (
    ExecutionPlan,
    Task,
    TaskType,
    TaskStatus,
    PlanningError,
    ErrorCode,
)
from .resource_estimator import ResourceEstimator
from .dependency_resolver import DependencyResolver

logger = logging.getLogger(__name__)


@dataclass
class ValidationError:
    """Validation error details."""

    level: str  # "syntax", "semantic", "feasibility", "security"
    code: str  # Error code
    message: str  # Error message
    task_id: str = None  # Optional task ID
    details: Dict[str, Any] = None  # Additional details


@dataclass
class ValidationResult:
    """Result of plan validation."""

    valid: bool  # Overall validation result
    errors: List[ValidationError]  # List of errors found
    warnings: List[str] = None  # Optional warnings

    def __post_init__(self):
        if self.warnings is None:
            self.warnings = []


class PlanValidator:
    """
    Validates execution plans at multiple levels.

    Validation levels:
    1. Syntax - Format, types, required fields
    2. Semantic - Task executability, input availability
    3. Feasibility - Resource availability, budget compliance
    4. Security - Authorization, constraint compliance
    """

    def __init__(
        self,
        resource_estimator: ResourceEstimator = None,
        dependency_resolver: DependencyResolver = None,
    ):
        """
        Initialize Plan Validator.

        Args:
            resource_estimator: ResourceEstimator instance
            dependency_resolver: DependencyResolver instance
        """
        self.resource_estimator = resource_estimator or ResourceEstimator()
        self.dependency_resolver = dependency_resolver or DependencyResolver()

        # Metrics
        self.plans_validated = 0
        self.validation_failures = 0

        logger.info("PlanValidator initialized")

    async def validate(self, plan: ExecutionPlan) -> ValidationResult:
        """
        Perform complete plan validation.

        Args:
            plan: Execution plan to validate

        Returns:
            ValidationResult with errors and warnings
        """
        self.plans_validated += 1
        errors: List[ValidationError] = []
        warnings: List[str] = []

        # Level 1: Syntax validation
        syntax_errors = self._validate_syntax(plan)
        errors.extend(syntax_errors)

        # If syntax invalid, don't proceed
        if syntax_errors:
            self.validation_failures += 1
            return ValidationResult(valid=False, errors=errors, warnings=warnings)

        # Level 2: Semantic validation
        semantic_errors = self._validate_semantics(plan)
        errors.extend(semantic_errors)

        # Level 3: Feasibility validation
        feasibility_errors = await self._validate_feasibility(plan)
        errors.extend(feasibility_errors)

        # Level 4: Security validation (basic)
        security_errors = self._validate_security(plan)
        errors.extend(security_errors)

        # Collect warnings
        warnings.extend(self._collect_warnings(plan))

        # Overall result
        is_valid = len(errors) == 0

        if not is_valid:
            self.validation_failures += 1

        logger.info(
            f"Validated plan {plan.plan_id}: "
            f"{'PASS' if is_valid else 'FAIL'} "
            f"({len(errors)} errors, {len(warnings)} warnings)"
        )

        return ValidationResult(valid=is_valid, errors=errors, warnings=warnings)

    def _validate_syntax(self, plan: ExecutionPlan) -> List[ValidationError]:
        """
        Validate plan syntax and format.

        Args:
            plan: Plan to validate

        Returns:
            List of validation errors
        """
        errors = []

        # Check plan has tasks
        if not plan.tasks:
            errors.append(
                ValidationError(
                    level="syntax",
                    code="E5606",
                    message="Plan has no tasks",
                )
            )
            return errors  # Can't proceed without tasks

        # Validate each task
        for task in plan.tasks:
            # Check required fields
            if not task.task_id:
                errors.append(
                    ValidationError(
                        level="syntax",
                        code="E5606",
                        message="Task missing task_id",
                        task_id=task.name or "unknown",
                    )
                )

            if not task.name:
                errors.append(
                    ValidationError(
                        level="syntax",
                        code="E5606",
                        message="Task missing name",
                        task_id=task.task_id,
                    )
                )

            if not task.description:
                errors.append(
                    ValidationError(
                        level="syntax",
                        code="E5606",
                        message="Task missing description",
                        task_id=task.task_id,
                    )
                )

            # Check task type valid
            if task.task_type not in TaskType:
                errors.append(
                    ValidationError(
                        level="syntax",
                        code="E5605",
                        message=f"Invalid task type: {task.task_type}",
                        task_id=task.task_id,
                    )
                )

            # Check timeout reasonable
            if task.timeout_seconds <= 0:
                errors.append(
                    ValidationError(
                        level="syntax",
                        code="E5504",
                        message=f"Invalid timeout: {task.timeout_seconds}",
                        task_id=task.task_id,
                    )
                )

        return errors

    def _validate_semantics(self, plan: ExecutionPlan) -> List[ValidationError]:
        """
        Validate plan semantics and executability.

        Args:
            plan: Plan to validate

        Returns:
            List of validation errors
        """
        errors = []

        # Check for circular dependencies
        try:
            self.dependency_resolver.resolve(plan)
        except PlanningError as e:
            if e.code == ErrorCode.E5301:
                errors.append(
                    ValidationError(
                        level="semantic",
                        code="E5301",
                        message="Circular dependencies detected",
                        details=e.details,
                    )
                )

        # Check all dependencies reference existing tasks
        task_ids = {task.task_id for task in plan.tasks}
        for task in plan.tasks:
            for dep in task.dependencies:
                if dep.task_id not in task_ids:
                    errors.append(
                        ValidationError(
                            level="semantic",
                            code="E5302",
                            message=f"Dependency references non-existent task: {dep.task_id}",
                            task_id=task.task_id,
                        )
                    )

        # Check tool tasks have tool_name
        for task in plan.tasks:
            if task.task_type == TaskType.TOOL_CALL and not task.tool_name:
                errors.append(
                    ValidationError(
                        level="semantic",
                        code="E5606",
                        message="Tool call task missing tool_name",
                        task_id=task.task_id,
                    )
                )

            # Check LLM tasks have prompt
            if task.task_type == TaskType.LLM_CALL and not task.llm_prompt:
                errors.append(
                    ValidationError(
                        level="semantic",
                        code="E5606",
                        message="LLM call task missing llm_prompt",
                        task_id=task.task_id,
                    )
                )

        return errors

    async def _validate_feasibility(self, plan: ExecutionPlan) -> List[ValidationError]:
        """
        Validate plan feasibility (resource availability).

        Args:
            plan: Plan to validate

        Returns:
            List of validation errors
        """
        errors = []

        # Estimate resources
        try:
            total_estimate = self.resource_estimator.estimate_plan(plan)

            # Check against budget (if set)
            if plan.resource_budget:
                is_within, violations = self.resource_estimator.check_budget(
                    total_estimate,
                    plan.resource_budget,
                )

                if not is_within:
                    for violation in violations:
                        errors.append(
                            ValidationError(
                                level="feasibility",
                                code="E5603",
                                message=violation,
                            )
                        )

        except Exception as e:
            logger.error(f"Resource estimation failed: {e}")
            errors.append(
                ValidationError(
                    level="feasibility",
                    code="E5500",
                    message=f"Resource estimation failed: {e}",
                )
            )

        return errors

    def _validate_security(self, plan: ExecutionPlan) -> List[ValidationError]:
        """
        Validate plan security and authorization.

        Args:
            plan: Plan to validate

        Returns:
            List of validation errors
        """
        errors = []

        # Basic security checks
        # (More comprehensive checks would integrate with L00/L08)

        # Check for excessively long task chains
        if len(plan.tasks) > 100:
            errors.append(
                ValidationError(
                    level="security",
                    code="E5604",
                    message=f"Plan has excessive task count: {len(plan.tasks)} (max 100)",
                )
            )

        return errors

    def _collect_warnings(self, plan: ExecutionPlan) -> List[str]:
        """
        Collect non-critical warnings about plan.

        Args:
            plan: Plan to check

        Returns:
            List of warning messages
        """
        warnings = []

        # Warn about long execution time
        try:
            total_estimate = self.resource_estimator.estimate_plan(plan)
            if total_estimate.execution_time_sec > 3600:  # 1 hour
                warnings.append(
                    f"Plan estimated execution time is high: {total_estimate.execution_time_sec}s"
                )

            # Warn about high cost
            if total_estimate.cost_usd > 1.0:
                warnings.append(
                    f"Plan estimated cost is high: ${total_estimate.cost_usd:.2f}"
                )

            # Warn about high token usage
            if total_estimate.token_count > 100_000:
                warnings.append(
                    f"Plan estimated token usage is high: {total_estimate.token_count}"
                )

        except Exception:
            pass  # Don't fail on warning collection

        # Warn about tasks with no dependencies (might be parallelizable)
        root_tasks = [t for t in plan.tasks if not t.dependencies]
        if len(root_tasks) > 10:
            warnings.append(
                f"Plan has many independent tasks ({len(root_tasks)}), "
                "consider reviewing for parallelization opportunities"
            )

        return warnings

    def get_stats(self) -> Dict[str, Any]:
        """Get validator statistics."""
        return {
            "plans_validated": self.plans_validated,
            "validation_failures": self.validation_failures,
            "failure_rate": self.validation_failures / max(1, self.plans_validated),
        }
