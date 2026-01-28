"""
L08 Supervision Layer - Compliance Monitor

Aggregated compliance status monitoring across policies,
constraints, and anomalies.
"""

import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from dataclasses import dataclass, field

from ..models.domain import (
    PolicyDecision,
    PolicyVerdict,
    ConstraintViolation,
    Anomaly,
    AnomalySeverity,
)
from ..models.config import SupervisionConfiguration

logger = logging.getLogger(__name__)


@dataclass
class ComplianceStatus:
    """Compliance status for an agent or system"""
    entity_id: str
    entity_type: str = "agent"  # agent, team, department, system

    # Policy compliance
    policy_evaluations: int = 0
    policy_violations: int = 0  # DENY verdicts
    policy_escalations: int = 0

    # Constraint compliance
    constraint_checks: int = 0
    constraint_violations: int = 0

    # Anomaly status
    anomalies_detected: int = 0
    critical_anomalies: int = 0
    unacknowledged_anomalies: int = 0

    # Escalation status
    pending_escalations: int = 0
    approved_escalations: int = 0
    rejected_escalations: int = 0
    timeout_escalations: int = 0

    # Computed scores
    compliance_score: float = 100.0  # 0-100
    risk_level: str = "LOW"  # LOW, MEDIUM, HIGH, CRITICAL

    # Time range
    period_start: datetime = field(default_factory=datetime.utcnow)
    period_end: datetime = field(default_factory=datetime.utcnow)
    last_updated: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "entity_id": self.entity_id,
            "entity_type": self.entity_type,
            "policy_evaluations": self.policy_evaluations,
            "policy_violations": self.policy_violations,
            "policy_escalations": self.policy_escalations,
            "constraint_checks": self.constraint_checks,
            "constraint_violations": self.constraint_violations,
            "anomalies_detected": self.anomalies_detected,
            "critical_anomalies": self.critical_anomalies,
            "unacknowledged_anomalies": self.unacknowledged_anomalies,
            "pending_escalations": self.pending_escalations,
            "approved_escalations": self.approved_escalations,
            "rejected_escalations": self.rejected_escalations,
            "timeout_escalations": self.timeout_escalations,
            "compliance_score": self.compliance_score,
            "risk_level": self.risk_level,
            "period_start": self.period_start.isoformat(),
            "period_end": self.period_end.isoformat(),
            "last_updated": self.last_updated.isoformat(),
        }


class ComplianceMonitor:
    """
    Compliance monitoring service.

    Features:
    - Aggregated compliance metrics per agent/team/department
    - Compliance score calculation
    - Risk level classification
    - Trend analysis
    """

    def __init__(self, config: SupervisionConfiguration):
        """
        Initialize Compliance Monitor.

        Args:
            config: Supervision configuration
        """
        self.config = config

        # Compliance status cache
        self._status_cache: Dict[str, ComplianceStatus] = {}

        # Event tracking for score calculation
        self._policy_decisions: List[PolicyDecision] = []
        self._constraint_violations: List[ConstraintViolation] = []
        self._anomalies: List[Anomaly] = []

        logger.info("ComplianceMonitor initialized")

    async def record_policy_decision(self, decision: PolicyDecision) -> None:
        """Record a policy decision for compliance tracking"""
        self._policy_decisions.append(decision)

        # Update status for agent
        status = self._get_or_create_status(decision.agent_id)
        status.policy_evaluations += 1

        if decision.verdict == PolicyVerdict.DENY:
            status.policy_violations += 1
        elif decision.verdict == PolicyVerdict.ESCALATE:
            status.policy_escalations += 1

        self._update_score(status)

    async def record_constraint_violation(self, violation: ConstraintViolation) -> None:
        """Record a constraint violation for compliance tracking"""
        self._constraint_violations.append(violation)

        status = self._get_or_create_status(violation.agent_id)
        status.constraint_checks += 1
        status.constraint_violations += 1

        self._update_score(status)

    async def record_anomaly(self, anomaly: Anomaly) -> None:
        """Record an anomaly for compliance tracking"""
        self._anomalies.append(anomaly)

        status = self._get_or_create_status(anomaly.agent_id)
        status.anomalies_detected += 1

        if anomaly.severity == AnomalySeverity.CRITICAL:
            status.critical_anomalies += 1

        if not anomaly.acknowledged:
            status.unacknowledged_anomalies += 1

        self._update_score(status)

    async def get_compliance_status(
        self,
        entity_id: str,
        entity_type: str = "agent"
    ) -> ComplianceStatus:
        """
        Get compliance status for an entity.

        Args:
            entity_id: Entity identifier (agent ID, team ID, etc.)
            entity_type: Type of entity

        Returns:
            ComplianceStatus for the entity
        """
        key = f"{entity_type}:{entity_id}"

        if key not in self._status_cache:
            self._status_cache[key] = ComplianceStatus(
                entity_id=entity_id,
                entity_type=entity_type,
                period_start=datetime.utcnow() - timedelta(hours=24),
                period_end=datetime.utcnow(),
            )

        status = self._status_cache[key]
        status.last_updated = datetime.utcnow()
        return status

    async def get_system_compliance(self) -> ComplianceStatus:
        """Get overall system compliance status"""
        status = ComplianceStatus(
            entity_id="system",
            entity_type="system",
            period_start=datetime.utcnow() - timedelta(hours=24),
            period_end=datetime.utcnow(),
        )

        # Aggregate from all cached statuses
        for entity_status in self._status_cache.values():
            status.policy_evaluations += entity_status.policy_evaluations
            status.policy_violations += entity_status.policy_violations
            status.policy_escalations += entity_status.policy_escalations
            status.constraint_checks += entity_status.constraint_checks
            status.constraint_violations += entity_status.constraint_violations
            status.anomalies_detected += entity_status.anomalies_detected
            status.critical_anomalies += entity_status.critical_anomalies
            status.unacknowledged_anomalies += entity_status.unacknowledged_anomalies
            status.pending_escalations += entity_status.pending_escalations

        self._update_score(status)
        return status

    async def get_compliance_report(
        self,
        entity_id: Optional[str] = None,
        period_hours: int = 24
    ) -> Dict[str, Any]:
        """
        Generate compliance report.

        Args:
            entity_id: Specific entity or None for system-wide
            period_hours: Time period for report

        Returns:
            Compliance report dictionary
        """
        if entity_id:
            status = await self.get_compliance_status(entity_id)
        else:
            status = await self.get_system_compliance()

        report = {
            "summary": status.to_dict(),
            "period_hours": period_hours,
            "generated_at": datetime.utcnow().isoformat(),
            "metrics": {
                "policy_compliance_rate": self._calc_rate(
                    status.policy_evaluations - status.policy_violations,
                    status.policy_evaluations
                ),
                "constraint_compliance_rate": self._calc_rate(
                    status.constraint_checks - status.constraint_violations,
                    status.constraint_checks
                ),
                "escalation_resolution_rate": self._calc_rate(
                    status.approved_escalations + status.rejected_escalations,
                    status.approved_escalations + status.rejected_escalations + status.pending_escalations + status.timeout_escalations
                ),
            },
            "recommendations": self._generate_recommendations(status),
        }

        return report

    def _get_or_create_status(self, entity_id: str) -> ComplianceStatus:
        """Get or create status for an entity"""
        key = f"agent:{entity_id}"
        if key not in self._status_cache:
            self._status_cache[key] = ComplianceStatus(
                entity_id=entity_id,
                entity_type="agent",
                period_start=datetime.utcnow() - timedelta(hours=24),
                period_end=datetime.utcnow(),
            )
        return self._status_cache[key]

    def _update_score(self, status: ComplianceStatus) -> None:
        """
        Update compliance score and risk level.

        Score calculation:
        - Start at 100
        - -5 per policy violation
        - -3 per constraint violation
        - -2 per anomaly (-10 per critical)
        - -5 per pending escalation
        - Minimum 0

        Risk levels:
        - CRITICAL: score < 40 or any critical anomaly
        - HIGH: score < 60
        - MEDIUM: score < 80
        - LOW: score >= 80
        """
        score = 100.0

        # Policy violations
        score -= status.policy_violations * 5

        # Constraint violations
        score -= status.constraint_violations * 3

        # Anomalies
        score -= (status.anomalies_detected - status.critical_anomalies) * 2
        score -= status.critical_anomalies * 10

        # Pending escalations
        score -= status.pending_escalations * 5

        # Clamp to 0-100
        score = max(0, min(100, score))
        status.compliance_score = score

        # Determine risk level
        if status.critical_anomalies > 0 or score < 40:
            status.risk_level = "CRITICAL"
        elif score < 60:
            status.risk_level = "HIGH"
        elif score < 80:
            status.risk_level = "MEDIUM"
        else:
            status.risk_level = "LOW"

    def _calc_rate(self, numerator: int, denominator: int) -> float:
        """Calculate rate as percentage"""
        if denominator == 0:
            return 100.0
        return (numerator / denominator) * 100

    def _generate_recommendations(self, status: ComplianceStatus) -> List[str]:
        """Generate recommendations based on compliance status"""
        recommendations = []

        if status.critical_anomalies > 0:
            recommendations.append(
                f"URGENT: {status.critical_anomalies} critical anomalies require immediate investigation"
            )

        if status.pending_escalations > 0:
            recommendations.append(
                f"Review {status.pending_escalations} pending escalations to avoid timeouts"
            )

        if status.constraint_violations > 5:
            recommendations.append(
                "High constraint violation rate - consider reviewing resource limits"
            )

        if status.policy_violations > status.policy_evaluations * 0.1:
            recommendations.append(
                "Policy violation rate exceeds 10% - review agent permissions and training"
            )

        if status.unacknowledged_anomalies > 0:
            recommendations.append(
                f"Acknowledge {status.unacknowledged_anomalies} anomalies to maintain oversight"
            )

        if not recommendations:
            recommendations.append("System operating within normal parameters")

        return recommendations

    def get_stats(self) -> Dict[str, Any]:
        """Get compliance monitor statistics"""
        return {
            "entities_tracked": len(self._status_cache),
            "total_decisions": len(self._policy_decisions),
            "total_violations": len(self._constraint_violations),
            "total_anomalies": len(self._anomalies),
        }

    async def health_check(self) -> Dict[str, Any]:
        """Health check for compliance monitor"""
        return {
            "status": "healthy",
            "stats": self.get_stats(),
        }
