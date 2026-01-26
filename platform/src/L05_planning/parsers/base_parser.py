"""
Base Parser - Abstract base and shared structures
Path: platform/src/L05_planning/parsers/base_parser.py
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from .format_detector import FormatType


@dataclass
class PlanStep:
    id: str
    title: str
    description: str
    files: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    phase: Optional[str] = None
    estimated_complexity: str = "medium"
    acceptance_criteria: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ParsedPlan:
    plan_id: str
    title: str
    steps: List[PlanStep]
    format_type: FormatType = FormatType.UNKNOWN
    overview: str = ""
    phases: List[str] = field(default_factory=list)
    total_estimated_time: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class BaseParser(ABC):
    """Abstract base class for format-specific parsers."""

    @abstractmethod
    def can_parse(self, markdown: str) -> bool:
        """Returns True if this parser can handle the given markdown."""
        pass

    @abstractmethod
    def parse(self, markdown: str) -> ParsedPlan:
        """Parses markdown into a ParsedPlan."""
        pass

    def _generate_step_id(self, index: int, phase: Optional[str] = None) -> str:
        """Generates a unique step ID."""
        if phase:
            return f"{phase}-{index}"
        return f"step-{index}"

    def _extract_title(self, markdown: str) -> str:
        """Extracts plan title from first heading."""
        import re
        match = re.search(r'^#\s+(.+)$', markdown, re.MULTILINE)
        return match.group(1).strip() if match else "Untitled Plan"

    def _generate_acceptance_criteria(self, step: PlanStep) -> List[str]:
        """Generates default acceptance criteria if none provided."""
        criteria = []

        if step.files:
            for f in step.files[:3]:
                criteria.append(f"File {f} exists and passes linting")

        if "test" in step.description.lower():
            criteria.append("All related tests pass")

        if not criteria:
            criteria.append("Implementation matches step description")

        return criteria
