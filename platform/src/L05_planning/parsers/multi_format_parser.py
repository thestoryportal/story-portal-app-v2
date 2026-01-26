"""
Multi-Format Parser - Unified entry point
Path: platform/src/L05_planning/parsers/multi_format_parser.py
"""

from typing import Dict, Type

from .base_parser import BaseParser, ParsedPlan
from .format_detector import FormatDetector, FormatType
from .numbered_list_parser import NumberedListParser
from .phase_based_parser import PhaseBasedParser
from .part_based_parser import PartBasedParser
from .table_based_parser import TableBasedParser
from .files_list_parser import FilesListParser


class ParseError(Exception):
    """Raised when plan markdown cannot be parsed."""
    pass


class MultiFormatParser:
    """Unified parser that detects format and routes to appropriate parser."""

    def __init__(self):
        self.detector = FormatDetector()
        self._parsers: Dict[FormatType, BaseParser] = {
            FormatType.NUMBERED_LIST: NumberedListParser(),
            FormatType.PHASE_BASED: PhaseBasedParser(),
            FormatType.PART_BASED: PartBasedParser(),
            FormatType.TABLE_BASED: TableBasedParser(),
            FormatType.SUBPLAN: PhaseBasedParser(),
            FormatType.HIERARCHICAL: PhaseBasedParser(),
            FormatType.FILES_LIST: FilesListParser(),
        }

    def parse(self, markdown: str) -> ParsedPlan:
        """
        Parses plan markdown into structured ParsedPlan.

        1. Detects format type
        2. Routes to appropriate parser
        3. Returns ParsedPlan with steps

        Raises:
            ParseError: If format cannot be determined or parsing fails
        """
        detection = self.detector.detect(markdown)

        if detection.format_type == FormatType.UNKNOWN:
            if detection.fallback_format and detection.fallback_format in self._parsers:
                parser = self._parsers[detection.fallback_format]
            else:
                raise ParseError(
                    f"Could not determine plan format. "
                    f"Confidence: {detection.confidence:.2f}"
                )
        else:
            parser = self._parsers.get(detection.format_type)
            if not parser:
                raise ParseError(f"No parser available for format: {detection.format_type}")

        try:
            result = parser.parse(markdown)
            result.format_type = detection.format_type

            if not result.steps:
                raise ParseError("Parser returned no steps")

            return result

        except Exception as e:
            if isinstance(e, ParseError):
                raise
            raise ParseError(f"Parse failed: {e}") from e
