"""Compliance and constraint validation models"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
import uuid


class ConstraintType(str, Enum):
    """Types of constraints that can be validated"""
    DEADLINE = "deadline"
    BUDGET = "budget"
    ERROR_RATE = "error_rate"
    POLICY = "policy"


@dataclass
class Constraint:
    """
    Constraint definition for compliance validation.

    Defines limits and thresholds for agent execution.
    """
    constraint_id: str
    constraint_type: ConstraintType
    name: str
    limit: float
    unit: str
    description: str = ""

    def __post_init__(self):
        """Generate ID if not provided"""
        if not self.constraint_id:
            self.constraint_id = f"const-{uuid.uuid4()}"

    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            "constraint_id": self.constraint_id,
            "constraint_type": self.constraint_type.value,
            "name": self.name,
            "limit": self.limit,
            "unit": self.unit,
            "description": self.description,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Constraint":
        """Create Constraint from dictionary"""
        return cls(
            constraint_id=data.get("constraint_id", ""),
            constraint_type=ConstraintType(data["constraint_type"]),
            name=data["name"],
            limit=data["limit"],
            unit=data["unit"],
            description=data.get("description", ""),
        )


@dataclass
class Violation:
    """
    Constraint violation instance.

    Records when and how a constraint was violated.
    """
    violation_id: str
    constraint: Constraint
    timestamp: datetime
    actual: float
    agent_id: str
    task_id: Optional[str] = None
    tenant_id: Optional[str] = None
    severity: str = "warning"
    violation_duration_seconds: float = 0.0
    remediation_suggested: str = ""

    def __post_init__(self):
        """Generate ID and validate"""
        if not self.violation_id:
            self.violation_id = f"viol-{uuid.uuid4()}"

        if isinstance(self.timestamp, str):
            self.timestamp = datetime.fromisoformat(self.timestamp.replace('Z', '+00:00'))

    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            "violation_id": self.violation_id,
            "constraint": self.constraint.to_dict() if isinstance(self.constraint, Constraint) else self.constraint,
            "timestamp": self.timestamp.isoformat() + "Z" if isinstance(self.timestamp, datetime) else self.timestamp,
            "actual": self.actual,
            "agent_id": self.agent_id,
            "task_id": self.task_id,
            "tenant_id": self.tenant_id,
            "severity": self.severity,
            "violation_duration_seconds": self.violation_duration_seconds,
            "remediation_suggested": self.remediation_suggested,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Violation":
        """Create Violation from dictionary"""
        constraint_data = data["constraint"]
        if isinstance(constraint_data, dict):
            constraint = Constraint.from_dict(constraint_data)
        else:
            constraint = constraint_data

        return cls(
            violation_id=data.get("violation_id", ""),
            constraint=constraint,
            timestamp=data["timestamp"],
            actual=data["actual"],
            agent_id=data["agent_id"],
            task_id=data.get("task_id"),
            tenant_id=data.get("tenant_id"),
            severity=data.get("severity", "warning"),
            violation_duration_seconds=data.get("violation_duration_seconds", 0.0),
            remediation_suggested=data.get("remediation_suggested", ""),
        )

    def exceeds_limit(self) -> bool:
        """Check if actual value exceeds constraint limit"""
        return self.actual > self.constraint.limit

    def calculate_severity(self) -> str:
        """Calculate violation severity based on how much limit was exceeded"""
        if not self.exceeds_limit():
            return "info"

        excess_percent = ((self.actual - self.constraint.limit) / self.constraint.limit) * 100

        if excess_percent >= 50:
            return "critical"
        elif excess_percent >= 20:
            return "warning"
        else:
            return "info"


@dataclass
class ComplianceResult:
    """
    Result of compliance validation.

    Contains all violations found during validation.
    """
    result_id: str
    execution_id: str
    agent_id: str
    tenant_id: str
    timestamp: datetime
    violations: List[Violation] = field(default_factory=list)
    constraints_checked: List[Constraint] = field(default_factory=list)
    compliant: bool = True

    def __post_init__(self):
        """Generate ID and determine compliance"""
        if not self.result_id:
            self.result_id = f"comp-{uuid.uuid4()}"

        if isinstance(self.timestamp, str):
            self.timestamp = datetime.fromisoformat(self.timestamp.replace('Z', '+00:00'))

        # Compliant if no violations
        self.compliant = len(self.violations) == 0

    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            "result_id": self.result_id,
            "execution_id": self.execution_id,
            "agent_id": self.agent_id,
            "tenant_id": self.tenant_id,
            "timestamp": self.timestamp.isoformat() + "Z" if isinstance(self.timestamp, datetime) else self.timestamp,
            "violations": [v.to_dict() for v in self.violations],
            "constraints_checked": [c.to_dict() for c in self.constraints_checked],
            "compliant": self.compliant,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ComplianceResult":
        """Create ComplianceResult from dictionary"""
        violations = [Violation.from_dict(v) if isinstance(v, dict) else v for v in data.get("violations", [])]
        constraints = [Constraint.from_dict(c) if isinstance(c, dict) else c for c in data.get("constraints_checked", [])]

        return cls(
            result_id=data.get("result_id", ""),
            execution_id=data["execution_id"],
            agent_id=data["agent_id"],
            tenant_id=data["tenant_id"],
            timestamp=data["timestamp"],
            violations=violations,
            constraints_checked=constraints,
            compliant=data.get("compliant", True),
        )

    def add_violation(self, violation: Violation):
        """Add violation to result"""
        self.violations.append(violation)
        self.compliant = False

    def get_violations_by_severity(self, severity: str) -> List[Violation]:
        """Get violations by severity level"""
        return [v for v in self.violations if v.severity == severity]

    def get_violations_by_type(self, constraint_type: ConstraintType) -> List[Violation]:
        """Get violations by constraint type"""
        return [v for v in self.violations if v.constraint.constraint_type == constraint_type]
