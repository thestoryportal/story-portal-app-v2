"""
Phase-Based Parser - Parses ## Phase N: format
Path: platform/src/L05_planning/parsers/phase_based_parser.py
"""

import re
from typing import List, Optional, Tuple
from uuid import uuid4

from .base_parser import BaseParser, ParsedPlan, PlanStep
from .format_detector import FormatType


class PhaseBasedParser(BaseParser):
    """Parses plans with phase-based format: ## Phase N: Title"""

    PHASE_PATTERN = re.compile(r'^##\s+Phase\s+(\d+):\s*(.+)$', re.MULTILINE)
    STEP_PATTERN = re.compile(r'^###\s+Step\s+(\d+)\.(\d+):\s*(.+)$', re.MULTILINE)

    def can_parse(self, markdown: str) -> bool:
        return bool(self.PHASE_PATTERN.search(markdown))

    def parse(self, markdown: str) -> ParsedPlan:
        title = self._extract_title(markdown)
        phases = self._extract_phases(markdown)
        steps = self._extract_steps(markdown)

        return ParsedPlan(
            plan_id=str(uuid4()),
            title=title,
            steps=steps,
            phases=phases,
            format_type=FormatType.PHASE_BASED
        )

    def _extract_phases(self, markdown: str) -> List[str]:
        phases = []
        for match in self.PHASE_PATTERN.finditer(markdown):
            phase_num = match.group(1)
            phase_title = match.group(2).strip()
            phases.append(f"Phase {phase_num}: {phase_title}")
        return phases

    def _extract_steps(self, markdown: str) -> List[PlanStep]:
        steps = []
        matches = list(self.STEP_PATTERN.finditer(markdown))

        for i, match in enumerate(matches):
            phase_num = match.group(1)
            step_num = match.group(2)
            step_title = match.group(3).strip()

            start = match.end()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(markdown)

            next_phase = self.PHASE_PATTERN.search(markdown[start:end])
            if next_phase:
                end = start + next_phase.start()

            description = markdown[start:end].strip()

            step_id = f"{phase_num}.{step_num}"
            dependencies = []
            if int(step_num) > 1:
                dependencies.append(f"{phase_num}.{int(step_num)-1}")

            step = PlanStep(
                id=step_id,
                title=step_title,
                description=description,
                phase=f"Phase {phase_num}",
                dependencies=dependencies
            )

            if not step.acceptance_criteria:
                step.acceptance_criteria = self._generate_acceptance_criteria(step)

            steps.append(step)

        return steps
