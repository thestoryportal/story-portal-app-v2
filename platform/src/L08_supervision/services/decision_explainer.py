"""
L08 Supervision Layer - Decision Explainer

Generate human-readable explanations for policy decisions,
constraint violations, and escalation requirements.
"""

import logging
from typing import Dict, Any, List, Optional

from ..models.domain import (
    PolicyDecision,
    PolicyVerdict,
    ConstraintViolation,
    Anomaly,
    EscalationWorkflow,
)

logger = logging.getLogger(__name__)


class DecisionExplainer:
    """
    Decision explainer for supervision layer decisions.

    Features:
    - Human-readable policy decision explanations
    - Constraint violation descriptions
    - Escalation context summarization
    - Anomaly impact analysis
    """

    def __init__(self):
        """Initialize Decision Explainer"""
        logger.info("DecisionExplainer initialized")

    async def explain_decision(
        self,
        decision: PolicyDecision,
        matched_rule_details: Optional[List[Dict[str, Any]]] = None
    ) -> str:
        """
        Generate human-readable explanation for a policy decision.

        Args:
            decision: Policy decision to explain
            matched_rule_details: Optional details about matched rules

        Returns:
            Human-readable explanation
        """
        lines = []

        # Header
        if decision.verdict == PolicyVerdict.ALLOW:
            lines.append("ACCESS ALLOWED")
        elif decision.verdict == PolicyVerdict.DENY:
            lines.append("ACCESS DENIED")
        else:
            lines.append("ESCALATION REQUIRED")

        lines.append("")

        # Summary
        if not decision.matched_rules:
            lines.append("No policies matched this request. Default ALLOW applied.")
        else:
            lines.append(f"Matched {len(decision.matched_rules)} policy rule(s):")
            lines.append("")

            if matched_rule_details:
                for detail in matched_rule_details:
                    action = detail.get("action", "ALLOW")
                    rule_name = detail.get("rule_name") or detail.get("rule_id", "Unknown")
                    policy_name = detail.get("policy_name", "Unknown Policy")

                    icon = self._get_verdict_icon(action)
                    lines.append(f"  {icon} [{action}] {rule_name} (from '{policy_name}')")

        lines.append("")

        # Context summary
        if decision.request_context:
            lines.append("Request Context:")
            operation = decision.request_context.get("operation", "Unknown")
            resource = decision.request_context.get("resource", {})
            lines.append(f"  Operation: {operation}")
            if resource:
                lines.append(f"  Resource: {resource.get('type', 'Unknown')} / {resource.get('id', 'N/A')}")

        lines.append("")
        lines.append(f"Decision ID: {decision.decision_id}")
        lines.append(f"Confidence: {decision.confidence * 100:.0f}%")
        lines.append(f"Latency: {decision.evaluation_latency_ms:.2f}ms")

        return "\n".join(lines)

    async def explain_violation(
        self,
        violation: ConstraintViolation
    ) -> str:
        """
        Generate human-readable explanation for a constraint violation.

        Args:
            violation: Constraint violation to explain

        Returns:
            Human-readable explanation
        """
        lines = []

        lines.append("CONSTRAINT VIOLATION")
        lines.append("")
        lines.append(f"Constraint: {violation.constraint_name or violation.constraint_id}")
        lines.append(f"Type: {violation.violation_type}")
        lines.append("")
        lines.append(f"Current Usage: {violation.current_usage:.2f}")
        lines.append(f"Limit: {violation.limit:.2f}")
        lines.append(f"Overage: {violation.current_usage - violation.limit:.2f}")
        lines.append("")

        # Provide remediation advice
        if violation.violation_type == "RATE_LIMIT":
            lines.append("Remediation: Wait for the rate limit window to reset, or request a limit increase.")
        elif violation.violation_type == "QUOTA":
            lines.append("Remediation: Request additional quota allocation from an administrator.")
        elif violation.violation_type == "RESOURCE_CAP":
            lines.append("Remediation: Release unused resources or request a higher resource cap.")

        return "\n".join(lines)

    async def explain_escalation(
        self,
        workflow: EscalationWorkflow
    ) -> str:
        """
        Generate human-readable explanation for an escalation.

        Args:
            workflow: Escalation workflow to explain

        Returns:
            Human-readable explanation
        """
        lines = []

        lines.append("ESCALATION REQUIRED")
        lines.append("")
        lines.append(f"Reason: {workflow.reason}")
        lines.append(f"Status: {workflow.status.value}")
        lines.append(f"Level: {workflow.escalation_level}")
        lines.append("")

        if workflow.context:
            lines.append("Context:")
            for key, value in workflow.context.items():
                lines.append(f"  {key}: {value}")
            lines.append("")

        if workflow.approvers:
            lines.append(f"Pending approval from: {', '.join(workflow.approvers)}")

        if workflow.assigned_to:
            lines.append(f"Assigned to: {workflow.assigned_to}")

        if workflow.timeout_at:
            lines.append(f"Timeout: {workflow.timeout_at.isoformat()}")

        return "\n".join(lines)

    async def explain_anomaly(
        self,
        anomaly: Anomaly
    ) -> str:
        """
        Generate human-readable explanation for an anomaly.

        Args:
            anomaly: Anomaly to explain

        Returns:
            Human-readable explanation
        """
        lines = []

        lines.append(f"ANOMALY DETECTED - Severity: {anomaly.severity.value}")
        lines.append("")
        lines.append(anomaly.description)
        lines.append("")
        lines.append(f"Metric: {anomaly.metric_name}")
        lines.append(f"Agent: {anomaly.agent_id}")
        lines.append("")
        lines.append(f"Baseline Value: {anomaly.baseline_value:.4f}")
        lines.append(f"Observed Value: {anomaly.observed_value:.4f}")
        lines.append(f"Z-Score: {anomaly.z_score:.2f}")
        lines.append(f"Detection Method: {anomaly.detection_method}")
        lines.append(f"Confidence: {anomaly.confidence * 100:.0f}%")
        lines.append("")

        # Provide severity context
        if anomaly.severity.value == "CRITICAL":
            lines.append("CRITICAL: Immediate investigation recommended. "
                         "This deviation is significantly outside normal operating parameters.")
        elif anomaly.severity.value == "HIGH":
            lines.append("HIGH: Prompt investigation recommended. "
                         "This deviation exceeds the 3-sigma threshold.")
        elif anomaly.severity.value == "MEDIUM":
            lines.append("MEDIUM: Monitor for persistence. "
                         "This deviation is notable but within acceptable variance.")
        else:
            lines.append("LOW: Minor deviation detected. "
                         "Consider reviewing if pattern continues.")

        return "\n".join(lines)

    async def generate_summary(
        self,
        decisions: List[PolicyDecision],
        violations: List[ConstraintViolation],
        anomalies: List[Anomaly]
    ) -> str:
        """
        Generate summary report of supervision activity.

        Args:
            decisions: Recent policy decisions
            violations: Recent constraint violations
            anomalies: Detected anomalies

        Returns:
            Summary report
        """
        lines = []

        lines.append("SUPERVISION SUMMARY")
        lines.append("=" * 40)
        lines.append("")

        # Policy decisions
        allow_count = len([d for d in decisions if d.verdict == PolicyVerdict.ALLOW])
        deny_count = len([d for d in decisions if d.verdict == PolicyVerdict.DENY])
        escalate_count = len([d for d in decisions if d.verdict == PolicyVerdict.ESCALATE])

        lines.append(f"Policy Decisions: {len(decisions)}")
        lines.append(f"  - Allowed: {allow_count}")
        lines.append(f"  - Denied: {deny_count}")
        lines.append(f"  - Escalated: {escalate_count}")
        lines.append("")

        # Violations
        lines.append(f"Constraint Violations: {len(violations)}")
        if violations:
            by_type = {}
            for v in violations:
                by_type[v.violation_type] = by_type.get(v.violation_type, 0) + 1
            for vtype, count in by_type.items():
                lines.append(f"  - {vtype}: {count}")
        lines.append("")

        # Anomalies
        lines.append(f"Anomalies Detected: {len(anomalies)}")
        if anomalies:
            by_severity = {}
            for a in anomalies:
                by_severity[a.severity.value] = by_severity.get(a.severity.value, 0) + 1
            for severity, count in by_severity.items():
                lines.append(f"  - {severity}: {count}")

        return "\n".join(lines)

    def _get_verdict_icon(self, verdict: str) -> str:
        """Get icon for verdict"""
        if verdict == "ALLOW":
            return "[+]"
        elif verdict == "DENY":
            return "[X]"
        else:
            return "[!]"
