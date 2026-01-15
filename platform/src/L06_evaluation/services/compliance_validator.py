"""Compliance validator for constraint checking"""

import logging
from datetime import datetime
from typing import List

from ..models.compliance import ComplianceResult, Constraint, Violation, ConstraintType
from ..models.error_codes import ErrorCode

logger = logging.getLogger(__name__)


class ComplianceValidator:
    """
    Validates execution against constraints.

    Per spec Section 3.2 (Component Responsibilities #6):
    - Deadline violations
    - Budget violations
    - Error rate violations
    - Policy violations
    """

    def __init__(self, metrics_engine: any):
        """
        Initialize compliance validator.

        Args:
            metrics_engine: MetricsEngine for querying metrics
        """
        self.metrics_engine = metrics_engine
        self.violations_detected = 0

    async def validate_compliance(
        self,
        execution_id: str,
        agent_id: str,
        tenant_id: str,
        constraints: List[Constraint],
    ) -> ComplianceResult:
        """
        Validate execution against constraints.

        Args:
            execution_id: Execution identifier
            agent_id: Agent identifier
            tenant_id: Tenant identifier
            constraints: List of constraints to check

        Returns:
            ComplianceResult with violations
        """
        result = ComplianceResult(
            result_id="",  # Auto-generated
            execution_id=execution_id,
            agent_id=agent_id,
            tenant_id=tenant_id,
            timestamp=datetime.utcnow(),
            constraints_checked=constraints,
        )

        for constraint in constraints:
            violation = await self._check_constraint(
                constraint, agent_id, tenant_id, execution_id
            )
            if violation:
                result.add_violation(violation)
                self.violations_detected += 1

        return result

    async def _check_constraint(
        self,
        constraint: Constraint,
        agent_id: str,
        tenant_id: str,
        execution_id: str,
    ) -> Optional[Violation]:
        """Check single constraint"""
        try:
            if constraint.constraint_type == ConstraintType.DEADLINE:
                return await self._check_deadline(constraint, agent_id, tenant_id, execution_id)
            elif constraint.constraint_type == ConstraintType.BUDGET:
                return await self._check_budget(constraint, agent_id, tenant_id, execution_id)
            elif constraint.constraint_type == ConstraintType.ERROR_RATE:
                return await self._check_error_rate(constraint, agent_id, tenant_id, execution_id)
            elif constraint.constraint_type == ConstraintType.POLICY:
                return await self._check_policy(constraint, agent_id, tenant_id, execution_id)
            return None
        except Exception as e:
            logger.error(f"Constraint check failed: {e}")
            return None

    async def _check_deadline(
        self,
        constraint: Constraint,
        agent_id: str,
        tenant_id: str,
        execution_id: str,
    ) -> Optional[Violation]:
        """Check deadline constraint"""
        # Query actual duration from metrics
        # For now, stub implementation
        actual_duration = 0.0  # Would query from metrics

        if actual_duration > constraint.limit:
            violation = Violation(
                violation_id="",
                constraint=constraint,
                timestamp=datetime.utcnow(),
                actual=actual_duration,
                agent_id=agent_id,
                tenant_id=tenant_id,
                task_id=execution_id,
            )
            violation.severity = violation.calculate_severity()
            violation.remediation_suggested = "Optimize execution or increase timeout"
            return violation

        return None

    async def _check_budget(
        self,
        constraint: Constraint,
        agent_id: str,
        tenant_id: str,
        execution_id: str,
    ) -> Optional[Violation]:
        """Check budget constraint"""
        # Stub implementation
        return None

    async def _check_error_rate(
        self,
        constraint: Constraint,
        agent_id: str,
        tenant_id: str,
        execution_id: str,
    ) -> Optional[Violation]:
        """Check error rate constraint"""
        # Stub implementation
        return None

    async def _check_policy(
        self,
        constraint: Constraint,
        agent_id: str,
        tenant_id: str,
        execution_id: str,
    ) -> Optional[Violation]:
        """Check policy constraint"""
        # Stub implementation
        return None

    def get_statistics(self) -> dict:
        """Get compliance statistics"""
        return {"violations_detected": self.violations_detected}
