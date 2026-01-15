"""Compliance scorer for policy adherence"""

import logging
from datetime import datetime

from .base import Scorer
from ..models.quality_score import DimensionScore

logger = logging.getLogger(__name__)


class ComplianceScorer(Scorer):
    """
    Scores compliance based on policy violations.

    Metrics used:
    - Number of policy violations
    - Severity of violations
    """

    def __init__(
        self,
        compliance_validator: any,
        weight: float = 0.1,
    ):
        """
        Initialize compliance scorer.

        Args:
            compliance_validator: ComplianceValidator for checking violations
            weight: Weight for compliance dimension (default: 0.1)
        """
        super().__init__("compliance", weight)
        self.compliance_validator = compliance_validator

    async def compute_score(
        self,
        agent_id: str,
        tenant_id: str,
        time_window: tuple[datetime, datetime],
    ) -> DimensionScore:
        """Compute compliance score"""
        try:
            start, end = time_window

            # Get violations in time window
            # Note: This is a stub - in real implementation, would query
            # violation database or compliance validator's history
            violations = []  # await self.compliance_validator.get_violations(agent_id, start, end)

            if not violations:
                # No violations = perfect score
                return self._create_dimension_score(
                    100.0,
                    {
                        "violation_count": 0,
                        "critical_violations": 0,
                        "warning_violations": 0,
                    },
                )

            # Count violations by severity
            critical_count = sum(1 for v in violations if v.severity == "critical")
            warning_count = sum(1 for v in violations if v.severity == "warning")
            info_count = len(violations) - critical_count - warning_count

            # Calculate score
            # Critical violations: -20 points each
            # Warning violations: -10 points each
            # Info violations: -5 points each
            penalty = (critical_count * 20) + (warning_count * 10) + (info_count * 5)
            score = max(0.0, 100.0 - penalty)

            raw_metrics = {
                "violation_count": len(violations),
                "critical_violations": critical_count,
                "warning_violations": warning_count,
                "info_violations": info_count,
                "penalty_points": penalty,
            }

            return self._create_dimension_score(score, raw_metrics)

        except Exception as e:
            logger.error(f"Compliance scoring failed: {e}")
            return self._create_dimension_score(
                50.0,
                {"error": str(e)},
            )
