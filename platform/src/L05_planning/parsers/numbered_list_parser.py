"""
Numbered List Parser - Parses 1. **Title** format
Path: platform/src/L05_planning/parsers/numbered_list_parser.py
"""

import re
from typing import List
from uuid import uuid4

from .base_parser import BaseParser, ParsedPlan, PlanStep
from .format_detector import FormatType


class NumberedListParser(BaseParser):
    """Parses plans with numbered list format: 1. **Step Title**"""

    STEP_PATTERN = re.compile(r'^(\d+)\.\s+\*\*([^*]+)\*\*', re.MULTILINE)
    FILES_PATTERN = re.compile(r'^\s*Files:\s*(.+)$', re.MULTILINE)
    DEPENDS_PATTERN = re.compile(r'^\s*Depends:\s*(.+)$', re.MULTILINE)

    def can_parse(self, markdown: str) -> bool:
        return bool(self.STEP_PATTERN.search(markdown))

    def parse(self, markdown: str) -> ParsedPlan:
        title = self._extract_title(markdown)
        steps = self._extract_steps(markdown)

        return ParsedPlan(
            plan_id=str(uuid4()),
            title=title,
            steps=steps,
            format_type=FormatType.NUMBERED_LIST
        )

    def _extract_steps(self, markdown: str) -> List[PlanStep]:
        steps = []
        matches = list(self.STEP_PATTERN.finditer(markdown))

        for i, match in enumerate(matches):
            start = match.end()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(markdown)
            content = markdown[start:end].strip()

            step_num = match.group(1)
            step_title = match.group(2).strip()

            description, files, depends = self._parse_content(content)

            step = PlanStep(
                id=f"step-{step_num}",
                title=step_title,
                description=description,
                files=files,
                dependencies=depends
            )

            if not step.acceptance_criteria:
                step.acceptance_criteria = self._generate_acceptance_criteria(step)

            steps.append(step)

        return steps

    def _parse_content(self, content: str):
        files = []
        depends = []

        files_match = self.FILES_PATTERN.search(content)
        if files_match:
            files = [f.strip() for f in files_match.group(1).split(',')]
            content = self.FILES_PATTERN.sub('', content)

        depends_match = self.DEPENDS_PATTERN.search(content)
        if depends_match:
            depends = [d.strip() for d in depends_match.group(1).split(',')]
            content = self.DEPENDS_PATTERN.sub('', content)

        description = content.strip()

        return description, files, depends
