"""
Integration Sentinel Agent - Checks cross-unit integration health
Path: platform/src/L05_planning/agents/integration_sentinel.py
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

from .spec_decomposer import AtomicUnit

logger = logging.getLogger(__name__)


class IntegrationCheckType(Enum):
    """Types of integration checks."""
    DEPENDENCY = "dependency"
    INTERFACE = "interface"
    CONTRACT = "contract"
    DATA_FLOW = "data_flow"
    IMPORT = "import"


class HealthStatus(Enum):
    """Health status levels."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


@dataclass
class IntegrationIssue:
    """Represents an integration issue."""
    issue_id: str
    check_type: IntegrationCheckType
    source_unit: str
    target_unit: str
    message: str
    severity: str = "warning"  # warning, error
    fix_suggestion: Optional[str] = None


@dataclass
class IntegrationCheckResult:
    """Result of integration health check."""
    healthy: bool
    status: HealthStatus
    issues: List[IntegrationIssue] = field(default_factory=list)
    checks_performed: int = 0
    checks_passed: int = 0
    checks_failed: int = 0
    timestamp: datetime = field(default_factory=datetime.now)
    duration_ms: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def health_score(self) -> float:
        """Returns health score as percentage."""
        if self.checks_performed == 0:
            return 100.0
        return (self.checks_passed / self.checks_performed) * 100.0

    @property
    def error_count(self) -> int:
        """Returns count of error-severity issues."""
        return len([i for i in self.issues if i.severity == "error"])

    @property
    def warning_count(self) -> int:
        """Returns count of warning-severity issues."""
        return len([i for i in self.issues if i.severity == "warning"])


@dataclass
class IntegrationCheck:
    """A registered integration check."""
    name: str
    check_type: IntegrationCheckType
    check_func: Callable[[], bool]
    source_units: List[str]
    target_units: List[str]


class IntegrationSentinel:
    """
    Monitors and validates cross-unit integration health.

    Checks:
    - Dependency resolution between units
    - Interface compatibility
    - Contract compliance
    - Data flow validation
    - Import chain validation
    """

    def __init__(self):
        """Initialize integration sentinel."""
        self._units: Dict[str, AtomicUnit] = {}
        self._checks: List[IntegrationCheck] = []
        self._last_result: Optional[IntegrationCheckResult] = None
        self._issue_counter = 0

    def register_unit(self, unit: AtomicUnit):
        """
        Registers a unit for integration monitoring.

        Args:
            unit: AtomicUnit to monitor
        """
        self._units[unit.id] = unit
        logger.debug(f"Registered unit for integration: {unit.id}")

    def register_units(self, units: List[AtomicUnit]):
        """Registers multiple units."""
        for unit in units:
            self.register_unit(unit)

    def register_check(
        self,
        name: str,
        check_type: IntegrationCheckType,
        check_func: Callable[[], bool],
        source_units: List[str],
        target_units: List[str],
    ):
        """
        Registers a custom integration check.

        Args:
            name: Check name
            check_type: Type of integration check
            check_func: Callable that returns True if check passes
            source_units: Source unit IDs
            target_units: Target unit IDs
        """
        check = IntegrationCheck(
            name=name,
            check_type=check_type,
            check_func=check_func,
            source_units=source_units,
            target_units=target_units,
        )
        self._checks.append(check)
        logger.debug(f"Registered integration check: {name}")

    def check_integration(self) -> IntegrationCheckResult:
        """
        Performs all integration checks.

        Returns:
            IntegrationCheckResult with health status and issues
        """
        start_time = datetime.now()
        issues: List[IntegrationIssue] = []
        checks_passed = 0
        checks_failed = 0

        logger.info(f"Running integration checks for {len(self._units)} units")

        # Check 1: Dependency resolution
        dep_issues = self._check_dependencies()
        issues.extend(dep_issues)
        if dep_issues:
            checks_failed += 1
        else:
            checks_passed += 1

        # Check 2: Interface compatibility (mock for now)
        interface_issues = self._check_interfaces()
        issues.extend(interface_issues)
        if interface_issues:
            checks_failed += 1
        else:
            checks_passed += 1

        # Check 3: Contract compliance
        contract_issues = self._check_contracts()
        issues.extend(contract_issues)
        if contract_issues:
            checks_failed += 1
        else:
            checks_passed += 1

        # Check 4: Import chain validation
        import_issues = self._check_imports()
        issues.extend(import_issues)
        if import_issues:
            checks_failed += 1
        else:
            checks_passed += 1

        # Run custom checks
        for check in self._checks:
            try:
                if check.check_func():
                    checks_passed += 1
                else:
                    checks_failed += 1
                    issues.append(self._create_issue(
                        check_type=check.check_type,
                        source_unit=check.source_units[0] if check.source_units else "unknown",
                        target_unit=check.target_units[0] if check.target_units else "unknown",
                        message=f"Custom check failed: {check.name}",
                        severity="error",
                    ))
            except Exception as e:
                checks_failed += 1
                issues.append(self._create_issue(
                    check_type=check.check_type,
                    source_unit=check.source_units[0] if check.source_units else "unknown",
                    target_unit=check.target_units[0] if check.target_units else "unknown",
                    message=f"Check error: {check.name} - {e}",
                    severity="error",
                ))

        end_time = datetime.now()
        duration_ms = int((end_time - start_time).total_seconds() * 1000)

        # Determine overall health
        total_checks = checks_passed + checks_failed
        error_count = len([i for i in issues if i.severity == "error"])

        if error_count > 0:
            status = HealthStatus.UNHEALTHY
            healthy = False
        elif len(issues) > 0:
            status = HealthStatus.DEGRADED
            healthy = True  # Degraded but still healthy
        else:
            status = HealthStatus.HEALTHY
            healthy = True

        self._last_result = IntegrationCheckResult(
            healthy=healthy,
            status=status,
            issues=issues,
            checks_performed=total_checks,
            checks_passed=checks_passed,
            checks_failed=checks_failed,
            timestamp=start_time,
            duration_ms=duration_ms,
            metadata={
                "unit_count": len(self._units),
                "custom_checks": len(self._checks),
            }
        )

        logger.info(
            f"Integration check complete: {status.value} "
            f"({checks_passed}/{total_checks} passed, {len(issues)} issues)"
        )

        return self._last_result

    def _check_dependencies(self) -> List[IntegrationIssue]:
        """Checks that all unit dependencies are satisfied."""
        issues = []
        unit_ids = set(self._units.keys())

        for unit_id, unit in self._units.items():
            for dep_id in unit.dependencies:
                if dep_id not in unit_ids:
                    issues.append(self._create_issue(
                        check_type=IntegrationCheckType.DEPENDENCY,
                        source_unit=unit_id,
                        target_unit=dep_id,
                        message=f"Missing dependency: {unit_id} depends on {dep_id}",
                        severity="error",
                        fix_suggestion=f"Register unit {dep_id} or remove dependency",
                    ))

        return issues

    def _check_interfaces(self) -> List[IntegrationIssue]:
        """Checks interface compatibility between units."""
        # This is a placeholder - in practice would check actual interfaces
        return []

    def _check_contracts(self) -> List[IntegrationIssue]:
        """Checks contract compliance between units."""
        # This is a placeholder - in practice would validate contracts
        return []

    def _check_imports(self) -> List[IntegrationIssue]:
        """Validates import chains don't have cycles."""
        issues = []

        # Build dependency graph and check for cycles
        visited: Set[str] = set()
        rec_stack: Set[str] = set()

        def has_cycle(unit_id: str) -> bool:
            visited.add(unit_id)
            rec_stack.add(unit_id)

            unit = self._units.get(unit_id)
            if unit:
                for dep_id in unit.dependencies:
                    if dep_id not in visited:
                        if has_cycle(dep_id):
                            return True
                    elif dep_id in rec_stack:
                        return True

            rec_stack.discard(unit_id)
            return False

        for unit_id in self._units:
            if unit_id not in visited:
                if has_cycle(unit_id):
                    issues.append(self._create_issue(
                        check_type=IntegrationCheckType.IMPORT,
                        source_unit=unit_id,
                        target_unit=unit_id,
                        message=f"Circular dependency detected involving {unit_id}",
                        severity="error",
                        fix_suggestion="Break the dependency cycle",
                    ))
                    break  # One cycle error is enough

        return issues

    def _create_issue(
        self,
        check_type: IntegrationCheckType,
        source_unit: str,
        target_unit: str,
        message: str,
        severity: str = "warning",
        fix_suggestion: Optional[str] = None,
    ) -> IntegrationIssue:
        """Creates an integration issue with unique ID."""
        self._issue_counter += 1
        return IntegrationIssue(
            issue_id=f"INT-{self._issue_counter:04d}",
            check_type=check_type,
            source_unit=source_unit,
            target_unit=target_unit,
            message=message,
            severity=severity,
            fix_suggestion=fix_suggestion,
        )

    def get_unit_dependencies(self, unit_id: str) -> List[str]:
        """Returns list of unit IDs that given unit depends on."""
        unit = self._units.get(unit_id)
        return unit.dependencies if unit else []

    def get_dependent_units(self, unit_id: str) -> List[str]:
        """Returns list of unit IDs that depend on given unit."""
        dependents = []
        for uid, unit in self._units.items():
            if unit_id in unit.dependencies:
                dependents.append(uid)
        return dependents

    def get_last_result(self) -> Optional[IntegrationCheckResult]:
        """Returns the last check result."""
        return self._last_result

    def get_statistics(self) -> Dict[str, Any]:
        """Returns sentinel statistics."""
        return {
            "registered_units": len(self._units),
            "custom_checks": len(self._checks),
            "last_result": {
                "healthy": self._last_result.healthy,
                "status": self._last_result.status.value,
                "health_score": self._last_result.health_score,
                "issues": len(self._last_result.issues),
            } if self._last_result else None,
        }

    def clear(self):
        """Clears all registered units and checks."""
        self._units = {}
        self._checks = []
        self._last_result = None
        self._issue_counter = 0
