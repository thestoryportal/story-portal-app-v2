"""
Format Detector - Identifies Claude plan output format
Path: platform/src/L05_planning/parsers/format_detector.py
"""

import re
from dataclasses import dataclass
from enum import Enum
from typing import List, Optional


class FormatType(Enum):
    NUMBERED_LIST = "numbered_list"
    PHASE_BASED = "phase_based"
    PART_BASED = "part_based"
    SUBPLAN = "subplan"
    TABLE_BASED = "table_based"
    HIERARCHICAL = "hierarchical"
    FILES_LIST = "files_list"  # ### N. `path` format
    UNKNOWN = "unknown"


@dataclass
class FormatDetectionResult:
    format_type: FormatType
    confidence: float
    indicators: List[str]
    fallback_format: Optional[FormatType] = None


class FormatDetector:
    """Detects the format type of Claude plan markdown."""

    PATTERNS = {
        FormatType.NUMBERED_LIST: [
            (r'^\d+\.\s+\*\*[^*]+\*\*', 0.4),
            (r'^Files:\s*.+', 0.2),
            (r'^Depends:\s*.+', 0.2),
        ],
        FormatType.PHASE_BASED: [
            (r'^##\s+Phase\s+\d+:', 0.5),
            (r'^###\s+Step\s+\d+\.\d+:', 0.3),
            # Also detect ### X.Y Title format (without "Step" keyword)
            (r'^###\s+\d+\.\d+\s+\w', 0.3),
        ],
        FormatType.PART_BASED: [
            (r'^#\s+PART\s+[A-Z]+:', 0.5),
            (r'^###\s+Step\s+\d+:', 0.3),
            # Also detect ## Section within parts
            (r'^##\s+[A-Z][^#\n]+$', 0.15),
        ],
        FormatType.SUBPLAN: [
            (r'^##\s+Implementation\s+Phases', 0.4),
            (r'^###\s+Phase\s+\d+:', 0.3),
            (r'\*\*Focus:\*\*', 0.2),
            # SUB-PLAN headers
            (r'^#\s+SUB-PLAN\s+\d+:', 0.4),
        ],
        FormatType.TABLE_BASED: [
            (r'\|\s*Step\s*\|', 0.5),
            (r'\|[-:]+\|', 0.3),
            # Also detect Feature/Description tables
            (r'\|\s*Feature\s*\|', 0.3),
        ],
        FormatType.HIERARCHICAL: [
            (r'^###\s+Step\s+\d+(\.\d+)+:', 0.6),
            # Also detect ### X.Y.Z format without "Step"
            (r'^###\s+\d+\.\d+\.\d+\s+', 0.4),
        ],
        FormatType.FILES_LIST: [
            # ### N. `path/to/file.py` or ### N. path/to/file.py
            (r'^###\s+\d+\.\s+[`\']?[\w./\-]+', 0.5),
            # ## Files to Create/Modify section header
            (r'^##\s+Files\s+to\s+(Create|Modify|Change)', 0.3),
            # Multiple ### N. patterns (confidence boost)
            (r'^###\s+\d+\.\s+', 0.2),
        ],
    }

    def detect(self, markdown: str) -> FormatDetectionResult:
        """Analyzes markdown and returns detected format with confidence."""
        scores = {fmt: 0.0 for fmt in FormatType if fmt != FormatType.UNKNOWN}
        indicators = {fmt: [] for fmt in FormatType}

        lines = markdown.split('\n')

        for fmt, patterns in self.PATTERNS.items():
            for pattern, weight in patterns:
                for line in lines:
                    if re.match(pattern, line, re.MULTILINE):
                        scores[fmt] += weight
                        indicators[fmt].append(f"Matched: {pattern[:30]}...")
                        break

        # PRIORITY RULE: If # PART exists, it's the top-level structure
        # PART_BASED should take precedence over SUBPLAN since PART is the
        # primary organization and SUBPLAN structures may exist within parts
        has_parts = any(re.match(r'^#\s+PART\s+[A-Z]+:', line) for line in lines)
        if has_parts and scores[FormatType.PART_BASED] > 0:
            # Boost PART_BASED score significantly when parts are present
            scores[FormatType.PART_BASED] *= 1.5
            indicators[FormatType.PART_BASED].append("Priority: # PART headers found")

        max_score = max(scores.values()) if scores.values() else 0
        if max_score > 0:
            for fmt in scores:
                scores[fmt] = min(scores[fmt] / max(max_score, 1.0), 1.0)

        best_fmt = max(scores, key=scores.get)
        best_score = scores[best_fmt]

        fallback = None
        if best_score < 0.7:
            sorted_fmts = sorted(scores.items(), key=lambda x: x[1], reverse=True)
            if len(sorted_fmts) > 1 and sorted_fmts[1][1] > 0:
                fallback = sorted_fmts[1][0]

        if best_score < 0.3:
            best_fmt = FormatType.UNKNOWN

        return FormatDetectionResult(
            format_type=best_fmt,
            confidence=best_score,
            indicators=indicators.get(best_fmt, []),
            fallback_format=fallback
        )
