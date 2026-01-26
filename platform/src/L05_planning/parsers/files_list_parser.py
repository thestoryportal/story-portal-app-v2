"""
Files List Parser - Parses ### N. `path` format
Path: platform/src/L05_planning/parsers/files_list_parser.py

This format is common when Claude writes plans that enumerate files to create:
  ### 1. `path/to/file.py`
  Description of what to do

  ### 2. `path/to/another.py`
  More description
"""

import re
from typing import List, Tuple
from uuid import uuid4

from .base_parser import BaseParser, ParsedPlan, PlanStep
from .format_detector import FormatType


class FilesListParser(BaseParser):
    """Parses plans with numbered H3 headers containing file paths."""

    # Match ### N. followed by optional backtick and path
    # Examples: ### 1. `path/file.py`, ### 2. path/file.py, ### 3. `../relative/path`
    STEP_PATTERN = re.compile(
        r'^###\s+(\d+)\.\s+[`\']?([^\s`\']+(?:\.[a-zA-Z]+)?)[`\']?',
        re.MULTILINE
    )

    # Alternative pattern for ### N. **title** format (without path in header)
    STEP_TITLE_PATTERN = re.compile(
        r'^###\s+(\d+)\.\s+\*\*([^*]+)\*\*',
        re.MULTILINE
    )

    def can_parse(self, markdown: str) -> bool:
        """Check if markdown contains ### N. pattern."""
        return bool(self.STEP_PATTERN.search(markdown)) or bool(self.STEP_TITLE_PATTERN.search(markdown))

    def parse(self, markdown: str) -> ParsedPlan:
        """Parse the files list format into a structured plan."""
        title = self._extract_title(markdown)
        overview = self._extract_overview(markdown)
        steps = self._extract_steps(markdown)

        return ParsedPlan(
            plan_id=str(uuid4()),
            title=title,
            steps=steps,
            format_type=FormatType.FILES_LIST,
            overview=overview,
        )

    def _extract_overview(self, markdown: str) -> str:
        """Extract overview/context from the plan."""
        # Look for ## Overview or ## Context sections
        overview_match = re.search(
            r'^##\s+(Overview|Context|Summary)\s*\n(.*?)(?=^##|\Z)',
            markdown,
            re.MULTILINE | re.DOTALL
        )
        if overview_match:
            return overview_match.group(2).strip()
        return ""

    def _extract_steps(self, markdown: str) -> List[PlanStep]:
        """Extract steps from ### N. headers."""
        steps = []

        # Try file path pattern first
        matches = list(self.STEP_PATTERN.finditer(markdown))

        # If no matches, try title pattern
        if not matches:
            matches = list(self.STEP_TITLE_PATTERN.finditer(markdown))

        if not matches:
            return steps

        for i, match in enumerate(matches):
            step_num = match.group(1)
            step_header = match.group(2).strip()

            # Determine if header is a file path or title
            is_file_path = '/' in step_header or step_header.endswith('.py') or step_header.endswith('.ts')

            # Extract content between this match and next (or end)
            start = match.end()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(markdown)
            content = markdown[start:end].strip()

            # Clean up content - remove section headers that aren't part of this step
            if '## ' in content:
                content = content.split('## ')[0].strip()

            # Extract description (first paragraph or all content if short)
            description = self._extract_description(content)

            # Extract files from the header or content
            files = []
            if is_file_path:
                # Clean the path
                clean_path = step_header.strip('`\'"')
                files = [clean_path]
                title = self._generate_title_from_path(clean_path)
            else:
                title = step_header
                files = self._extract_files_from_content(content)

            step = PlanStep(
                id=f"step-{step_num}",
                title=title,
                description=description,
                files=files,
                dependencies=self._extract_dependencies(i, matches),
                estimated_complexity=self._estimate_complexity(content),
            )

            # Generate acceptance criteria if none provided
            if not step.acceptance_criteria:
                step.acceptance_criteria = self._generate_acceptance_criteria(step)

            steps.append(step)

        return steps

    def _extract_description(self, content: str) -> str:
        """Extract meaningful description from content."""
        # Remove code blocks for description
        desc = re.sub(r'```[\s\S]*?```', '', content)
        # Take first substantial paragraph
        paragraphs = [p.strip() for p in desc.split('\n\n') if p.strip()]
        if paragraphs:
            return paragraphs[0][:500]  # Limit length
        return content[:500] if content else "Implementation step"

    def _generate_title_from_path(self, path: str) -> str:
        """Generate a readable title from a file path."""
        # Extract filename and parent directory
        parts = path.rstrip('/').split('/')
        filename = parts[-1] if parts else 'file'
        parent = parts[-2] if len(parts) > 1 else 'package'

        # Handle __init__.py specially
        if '__init__' in filename:
            return f"Create {parent} package"

        # Remove extension
        name = filename.rsplit('.', 1)[0]
        # Convert to title case with spaces
        title = re.sub(r'[_-]', ' ', name).title()

        # Add context based on path
        if 'test' in path.lower() and 'test' not in title.lower():
            return f"Create {title} tests"
        else:
            return f"Create {title}"

    def _extract_files_from_content(self, content: str) -> List[str]:
        """Extract file paths mentioned in the content."""
        files = []
        # Match paths like src/foo/bar.py or ./relative/path.ts
        path_pattern = re.compile(r'[\w./\-]+\.[a-zA-Z]{2,4}')
        for match in path_pattern.finditer(content):
            path = match.group()
            if path not in files and not path.startswith('http'):
                files.append(path)
        return files[:5]  # Limit to 5 files per step

    def _extract_dependencies(self, index: int, matches: List) -> List[str]:
        """Infer dependencies based on step order."""
        # Simple heuristic: each step depends on previous step
        if index > 0:
            prev_num = matches[index - 1].group(1)
            return [f"step-{prev_num}"]
        return []

    def _estimate_complexity(self, content: str) -> str:
        """Estimate step complexity based on content."""
        content_lower = content.lower()

        # High complexity indicators
        if any(word in content_lower for word in ['complex', 'integration', 'refactor', 'architecture']):
            return "high"

        # Low complexity indicators
        if any(word in content_lower for word in ['simple', 'empty', 'init', 'stub', 'basic']):
            return "low"

        # Medium by default
        return "medium"
