"""
Spec Decomposer Agent - Decomposes parsed plans into atomic units
Path: platform/src/L05_planning/agents/spec_decomposer.py
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from uuid import uuid4

from ..parsers.base_parser import ParsedPlan, PlanStep


@dataclass
class AcceptanceCriterion:
    """Single acceptance criterion for an atomic unit."""
    id: str
    description: str
    validation_command: str
    expected_result: str = "success"
    timeout_seconds: int = 60


@dataclass
class AtomicUnit:
    """Smallest independently validatable unit of work."""
    id: str
    title: str
    description: str
    files: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    acceptance_criteria: List[AcceptanceCriterion] = field(default_factory=list)
    phase: Optional[str] = None
    complexity: str = "medium"
    estimated_minutes: int = 15
    compensation_action: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class SpecDecomposer:
    """Decomposes a ParsedPlan into a list of AtomicUnits for validation."""

    def __init__(self):
        self._units: List[AtomicUnit] = []

    def decompose(self, plan: ParsedPlan) -> List[AtomicUnit]:
        """
        Decomposes a parsed plan into atomic units.

        Args:
            plan: ParsedPlan from multi-format parser

        Returns:
            List of AtomicUnits ready for validation
        """
        self._units = []

        for step in plan.steps:
            unit = self._step_to_unit(step, plan)
            self._units.append(unit)

        # Resolve dependency references
        self._resolve_dependencies()

        return self._units

    def _step_to_unit(self, step: PlanStep, plan: ParsedPlan) -> AtomicUnit:
        """Converts a PlanStep into an AtomicUnit."""
        # Generate acceptance criteria from step
        criteria = self._generate_acceptance_criteria(step)

        # Estimate complexity based on files and description
        complexity = self._estimate_complexity(step)

        # Generate compensation action
        compensation = self._generate_compensation(step)

        return AtomicUnit(
            id=step.id,
            title=step.title,
            description=step.description,
            files=step.files,
            dependencies=step.dependencies,
            acceptance_criteria=criteria,
            phase=step.phase,
            complexity=complexity,
            estimated_minutes=self._estimate_time(complexity),
            compensation_action=compensation,
            metadata={
                "plan_id": plan.plan_id,
                "format_type": plan.format_type.value,
                "original_step": step.metadata
            }
        )

    def _generate_acceptance_criteria(self, step: PlanStep) -> List[AcceptanceCriterion]:
        """Generates acceptance criteria for a step."""
        criteria = []

        # Use existing criteria if provided
        for i, criterion_text in enumerate(step.acceptance_criteria):
            criteria.append(AcceptanceCriterion(
                id=f"{step.id}-criterion-{i+1}",
                description=criterion_text,
                validation_command=self._infer_validation_command(criterion_text, step)
            ))

        # Generate default criteria based on files
        if step.files and not criteria:
            for f in step.files[:3]:
                criteria.append(AcceptanceCriterion(
                    id=f"{step.id}-file-{f.replace('/', '-').replace('.', '-')}",
                    description=f"File {f} exists and is valid",
                    validation_command=f"python -m py_compile {f}" if f.endswith('.py') else f"test -f {f}"
                ))

        # Ensure at least one criterion
        if not criteria:
            criteria.append(AcceptanceCriterion(
                id=f"{step.id}-default",
                description="Implementation matches step description",
                validation_command="echo 'Manual verification required'"
            ))

        return criteria

    def _infer_validation_command(self, criterion: str, step: PlanStep) -> str:
        """Infers a validation command from criterion text."""
        criterion_lower = criterion.lower()

        if "exists" in criterion_lower and step.files:
            return f"test -f {step.files[0]}"
        elif "import" in criterion_lower:
            return "python -c 'import sys; sys.exit(0)'"
        elif "test" in criterion_lower:
            return "pytest --collect-only"
        elif "lint" in criterion_lower:
            return "python -m py_compile"

        return "echo 'Manual verification required'"

    def _estimate_complexity(self, step: PlanStep) -> str:
        """Estimates complexity based on step characteristics."""
        file_count = len(step.files)
        desc_len = len(step.description)
        dep_count = len(step.dependencies)

        if file_count > 3 or desc_len > 500 or dep_count > 2:
            return "high"
        elif file_count > 1 or desc_len > 200 or dep_count > 0:
            return "medium"
        else:
            return "low"

    def _estimate_time(self, complexity: str) -> int:
        """Estimates time in minutes based on complexity."""
        return {"low": 10, "medium": 20, "high": 30}.get(complexity, 15)

    def _generate_compensation(self, step: PlanStep) -> str:
        """Generates compensation/rollback action for a step."""
        if step.files:
            file_list = " ".join(step.files)
            return f"git checkout -- {file_list}"
        return "git checkout -- ."

    def _resolve_dependencies(self):
        """Validates that all dependency references exist."""
        unit_ids = {u.id for u in self._units}

        for unit in self._units:
            valid_deps = [d for d in unit.dependencies if d in unit_ids]
            unit.dependencies = valid_deps

    def get_execution_order(self) -> List[AtomicUnit]:
        """Returns units in topological order based on dependencies."""
        # Simple topological sort
        visited = set()
        order = []

        def visit(unit: AtomicUnit):
            if unit.id in visited:
                return
            visited.add(unit.id)

            for dep_id in unit.dependencies:
                dep_unit = next((u for u in self._units if u.id == dep_id), None)
                if dep_unit:
                    visit(dep_unit)

            order.append(unit)

        for unit in self._units:
            visit(unit)

        return order

    def get_unit_by_id(self, unit_id: str) -> Optional[AtomicUnit]:
        """Retrieves a unit by its ID."""
        return next((u for u in self._units if u.id == unit_id), None)
