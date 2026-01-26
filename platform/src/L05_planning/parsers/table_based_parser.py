"""
Table-Based Parser - Parses markdown table format
Path: platform/src/L05_planning/parsers/table_based_parser.py
"""

import re
from typing import Dict, List, Optional
from uuid import uuid4

from .base_parser import BaseParser, ParsedPlan, PlanStep
from .format_detector import FormatType


class TableBasedParser(BaseParser):
    """Parses plans with table format: | Step | Description | ... |"""

    TABLE_ROW_PATTERN = re.compile(r'^\|(.+)\|$', re.MULTILINE)
    SEPARATOR_PATTERN = re.compile(r'^[\|\s\-:]+$')

    COLUMN_MAPPINGS = {
        'step': 'title',
        'title': 'title',
        'name': 'title',
        'description': 'description',
        'desc': 'description',
        'details': 'description',
        'files': 'files',
        'file': 'files',
        'depends': 'dependencies',
        'dependencies': 'dependencies',
        'requires': 'dependencies',
    }

    def can_parse(self, markdown: str) -> bool:
        rows = self.TABLE_ROW_PATTERN.findall(markdown)
        return len(rows) >= 2 and any(self.SEPARATOR_PATTERN.match(r.strip()) for r in rows)

    def parse(self, markdown: str) -> ParsedPlan:
        title = self._extract_title(markdown)
        steps = self._extract_steps(markdown)

        return ParsedPlan(
            plan_id=str(uuid4()),
            title=title,
            steps=steps,
            format_type=FormatType.TABLE_BASED
        )

    def _extract_steps(self, markdown: str) -> List[PlanStep]:
        rows = self.TABLE_ROW_PATTERN.findall(markdown)
        if len(rows) < 2:
            return []

        headers = [h.strip().lower() for h in rows[0].split('|') if h.strip()]

        column_map = {}
        for i, header in enumerate(headers):
            for key, field in self.COLUMN_MAPPINGS.items():
                if key in header:
                    column_map[i] = field
                    break

        steps = []
        for row_idx, row in enumerate(rows[1:], 1):
            if self.SEPARATOR_PATTERN.match(row.strip()):
                continue

            cells = [c.strip() for c in row.split('|') if c.strip()]
            if not cells:
                continue

            step_data = {'title': '', 'description': '', 'files': [], 'dependencies': []}

            for i, cell in enumerate(cells):
                if i in column_map:
                    field = column_map[i]
                    if field in ('files', 'dependencies'):
                        step_data[field] = [x.strip() for x in cell.split(',') if x.strip()]
                    else:
                        step_data[field] = cell

            if not step_data['title']:
                step_data['title'] = cells[0] if cells else f"Step {row_idx}"

            step = PlanStep(
                id=f"step-{row_idx}",
                title=step_data['title'],
                description=step_data['description'],
                files=step_data['files'],
                dependencies=step_data['dependencies']
            )

            if not step.acceptance_criteria:
                step.acceptance_criteria = self._generate_acceptance_criteria(step)

            steps.append(step)

        return steps
