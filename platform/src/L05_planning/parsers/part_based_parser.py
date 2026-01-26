"""
Part-Based Parser - Parses # PART A: format
Path: platform/src/L05_planning/parsers/part_based_parser.py
"""

import re
from typing import List
from uuid import uuid4

from .base_parser import BaseParser, ParsedPlan, PlanStep
from .format_detector import FormatType


class PartBasedParser(BaseParser):
    """Parses plans with part-based format: # PART A: Title"""

    PART_PATTERN = re.compile(r'^#\s+PART\s+([A-Z]+):\s*(.+)$', re.MULTILINE)
    STEP_PATTERN = re.compile(r'^###\s+Step\s+(\d+):\s*(.+)$', re.MULTILINE)
    # Alternative patterns for numbered subsections
    NUMBERED_STEP_PATTERN = re.compile(r'^###\s+(\d+)\.(\d+)\s+(.+)$', re.MULTILINE)
    # Section headers within parts (## Section Title)
    SECTION_PATTERN = re.compile(r'^##\s+([^#\n]+)$', re.MULTILINE)
    # Generic ### header as fallback
    GENERIC_HEADER_PATTERN = re.compile(r'^###\s+([^#\n]+)$', re.MULTILINE)

    def can_parse(self, markdown: str) -> bool:
        return bool(self.PART_PATTERN.search(markdown))

    def parse(self, markdown: str) -> ParsedPlan:
        title = self._extract_title(markdown)
        parts = self._extract_parts(markdown)
        steps = self._extract_steps(markdown)

        return ParsedPlan(
            plan_id=str(uuid4()),
            title=title,
            steps=steps,
            phases=parts,
            format_type=FormatType.PART_BASED
        )

    def _extract_parts(self, markdown: str) -> List[str]:
        parts = []
        for match in self.PART_PATTERN.finditer(markdown):
            part_letter = match.group(1)
            part_title = match.group(2).strip()
            parts.append(f"PART {part_letter}: {part_title}")
        return parts

    def _extract_steps(self, markdown: str) -> List[PlanStep]:
        steps = []
        global_step_counter = 0

        part_matches = list(self.PART_PATTERN.finditer(markdown))

        for pi, part_match in enumerate(part_matches):
            part_letter = part_match.group(1)
            part_start = part_match.end()
            part_end = part_matches[pi + 1].start() if pi + 1 < len(part_matches) else len(markdown)

            part_content = markdown[part_start:part_end]

            # Try Step N: pattern first
            step_matches = list(self.STEP_PATTERN.finditer(part_content))

            if step_matches:
                # Use Step N: format
                for si, step_match in enumerate(step_matches):
                    step_num = step_match.group(1)
                    step_title = step_match.group(2).strip()

                    start = step_match.end()
                    end = step_matches[si + 1].start() if si + 1 < len(step_matches) else len(part_content)
                    description = part_content[start:end].strip()

                    step_id = f"{part_letter}-{step_num}"
                    dependencies = []
                    if int(step_num) > 1:
                        dependencies.append(f"{part_letter}-{int(step_num)-1}")

                    step = PlanStep(
                        id=step_id,
                        title=step_title,
                        description=description,
                        phase=f"PART {part_letter}",
                        dependencies=dependencies
                    )

                    if not step.acceptance_criteria:
                        step.acceptance_criteria = self._generate_acceptance_criteria(step)

                    steps.append(step)
            else:
                # Try numbered X.Y format
                numbered_matches = list(self.NUMBERED_STEP_PATTERN.finditer(part_content))

                if numbered_matches:
                    for si, match in enumerate(numbered_matches):
                        phase_num = match.group(1)
                        step_num = match.group(2)
                        step_title = match.group(3).strip()

                        start = match.end()
                        end = numbered_matches[si + 1].start() if si + 1 < len(numbered_matches) else len(part_content)
                        description = part_content[start:end].strip()

                        step_id = f"{part_letter}-{phase_num}.{step_num}"
                        dependencies = []
                        if int(step_num) > 1:
                            dependencies.append(f"{part_letter}-{phase_num}.{int(step_num)-1}")

                        step = PlanStep(
                            id=step_id,
                            title=step_title,
                            description=description,
                            phase=f"PART {part_letter}",
                            dependencies=dependencies
                        )

                        if not step.acceptance_criteria:
                            step.acceptance_criteria = self._generate_acceptance_criteria(step)

                        steps.append(step)
                else:
                    # Fallback: treat ## Section headers as steps
                    section_matches = list(self.SECTION_PATTERN.finditer(part_content))

                    # Filter out sections that are just navigation (like "---")
                    section_matches = [m for m in section_matches if not m.group(1).strip().startswith('-')]

                    for si, match in enumerate(section_matches):
                        global_step_counter += 1
                        step_title = match.group(1).strip()

                        start = match.end()
                        end = section_matches[si + 1].start() if si + 1 < len(section_matches) else len(part_content)
                        description = part_content[start:end].strip()

                        step_id = f"{part_letter}-section-{global_step_counter}"
                        dependencies = []

                        step = PlanStep(
                            id=step_id,
                            title=step_title,
                            description=description,
                            phase=f"PART {part_letter}",
                            dependencies=dependencies
                        )

                        if not step.acceptance_criteria:
                            step.acceptance_criteria = self._generate_acceptance_criteria(step)

                        steps.append(step)

        return steps
