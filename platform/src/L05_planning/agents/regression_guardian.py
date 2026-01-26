"""
Regression Guardian Agent - Re-runs prior unit tests to ensure no regressions
Path: platform/src/L05_planning/agents/regression_guardian.py
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple

from .spec_decomposer import AtomicUnit
from .unit_validator import UnitValidator, ValidationResult, ValidationStatus

logger = logging.getLogger(__name__)


class RegressionScope(Enum):
    """Scope of regression testing."""
    ALL = "all"  # Run all prior tests
    AFFECTED = "affected"  # Run tests affected by changes
    CRITICAL = "critical"  # Run only critical path tests
    SMOKE = "smoke"  # Quick smoke tests only


@dataclass
class RegressionResult:
    """Result of a regression test run."""
    all_passed: bool
    total_tests: int
    passed_tests: int
    failed_tests: int
    skipped_tests: int
    results: List[ValidationResult] = field(default_factory=list)
    failed_units: List[str] = field(default_factory=list)
    duration_ms: int = 0
    timestamp: datetime = field(default_factory=datetime.now)
    scope: RegressionScope = RegressionScope.ALL
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def pass_rate(self) -> float:
        """Returns pass rate as a percentage."""
        if self.total_tests == 0:
            return 100.0
        return (self.passed_tests / self.total_tests) * 100.0


@dataclass
class RegressionTest:
    """A registered regression test."""
    name: str
    unit_id: str
    test_func: Callable[[], bool]
    critical: bool = False
    tags: List[str] = field(default_factory=list)


class RegressionGuardian:
    """
    Manages and runs regression tests for completed units.

    Ensures that new changes don't break previously validated functionality.
    """

    def __init__(
        self,
        validator: Optional[UnitValidator] = None,
        fail_fast: bool = False,
    ):
        """
        Initialize regression guardian.

        Args:
            validator: UnitValidator for running validations
            fail_fast: If True, stop on first failure
        """
        self.validator = validator or UnitValidator()
        self.fail_fast = fail_fast
        self._completed_units: List[AtomicUnit] = []
        self._regression_tests: List[RegressionTest] = []
        self._last_result: Optional[RegressionResult] = None

    def register_completed_unit(self, unit: AtomicUnit):
        """
        Registers a completed unit for regression testing.

        Args:
            unit: AtomicUnit that has been validated and completed
        """
        if unit not in self._completed_units:
            self._completed_units.append(unit)
            logger.info(f"Registered unit for regression: {unit.id}")

    def register_test(
        self,
        name: str,
        unit_id: str,
        test_func: Callable[[], bool],
        critical: bool = False,
        tags: Optional[List[str]] = None,
    ):
        """
        Registers a custom regression test.

        Args:
            name: Test name
            unit_id: Associated unit ID
            test_func: Callable that returns True if test passes
            critical: If True, marks test as critical path
            tags: Optional tags for filtering
        """
        test = RegressionTest(
            name=name,
            unit_id=unit_id,
            test_func=test_func,
            critical=critical,
            tags=tags or [],
        )
        self._regression_tests.append(test)
        logger.debug(f"Registered regression test: {name}")

    def run_regression(
        self,
        scope: RegressionScope = RegressionScope.ALL,
        tags: Optional[List[str]] = None,
    ) -> RegressionResult:
        """
        Runs regression tests based on scope.

        Args:
            scope: Scope of regression testing
            tags: Optional tag filter

        Returns:
            RegressionResult with test outcomes
        """
        start_time = datetime.now()
        results: List[ValidationResult] = []
        failed_units: List[str] = []

        logger.info(f"Running regression tests (scope={scope.value})")

        # Select tests based on scope
        tests_to_run = self._select_tests(scope, tags)

        passed = 0
        failed = 0
        skipped = 0

        for test in tests_to_run:
            try:
                if test.test_func():
                    passed += 1
                    logger.debug(f"Regression test PASSED: {test.name}")
                else:
                    failed += 1
                    failed_units.append(test.unit_id)
                    logger.warning(f"Regression test FAILED: {test.name}")
                    if self.fail_fast:
                        break
            except Exception as e:
                failed += 1
                failed_units.append(test.unit_id)
                logger.error(f"Regression test ERROR: {test.name} - {e}")
                if self.fail_fast:
                    break

        # Also validate registered units
        units_to_validate = self._select_units(scope)
        for unit in units_to_validate:
            result = self.validator.validate(unit)
            results.append(result)

            if result.passed:
                passed += 1
            else:
                failed += 1
                failed_units.append(unit.id)
                if self.fail_fast:
                    break

        end_time = datetime.now()
        duration_ms = int((end_time - start_time).total_seconds() * 1000)

        total = passed + failed + skipped
        self._last_result = RegressionResult(
            all_passed=(failed == 0),
            total_tests=total,
            passed_tests=passed,
            failed_tests=failed,
            skipped_tests=skipped,
            results=results,
            failed_units=list(set(failed_units)),
            duration_ms=duration_ms,
            timestamp=start_time,
            scope=scope,
        )

        logger.info(
            f"Regression complete: {passed}/{total} passed "
            f"({'PASS' if failed == 0 else 'FAIL'})"
        )

        return self._last_result

    def _select_tests(
        self,
        scope: RegressionScope,
        tags: Optional[List[str]] = None,
    ) -> List[RegressionTest]:
        """Selects tests based on scope and tags."""
        tests = self._regression_tests

        if scope == RegressionScope.CRITICAL:
            tests = [t for t in tests if t.critical]
        elif scope == RegressionScope.SMOKE:
            tests = [t for t in tests if "smoke" in t.tags]

        if tags:
            tests = [t for t in tests if any(tag in t.tags for tag in tags)]

        return tests

    def _select_units(self, scope: RegressionScope) -> List[AtomicUnit]:
        """Selects units to validate based on scope."""
        if scope == RegressionScope.SMOKE:
            # Return first and last unit for smoke testing
            if len(self._completed_units) > 1:
                return [self._completed_units[0], self._completed_units[-1]]
            return self._completed_units[:1]

        if scope == RegressionScope.CRITICAL:
            # Return units marked as high complexity
            return [u for u in self._completed_units if u.complexity == "high"]

        # ALL and AFFECTED return all units
        return self._completed_units

    def get_affected_units(self, changed_files: List[str]) -> List[AtomicUnit]:
        """
        Returns units affected by file changes.

        Args:
            changed_files: List of changed file paths

        Returns:
            List of AtomicUnits that reference any changed files
        """
        affected = []
        for unit in self._completed_units:
            for unit_file in unit.files:
                for changed in changed_files:
                    if changed.endswith(unit_file) or unit_file in changed:
                        affected.append(unit)
                        break
        return affected

    def run_affected_regression(
        self, changed_files: List[str]
    ) -> RegressionResult:
        """
        Runs regression tests only for units affected by changes.

        Args:
            changed_files: List of changed file paths

        Returns:
            RegressionResult for affected units
        """
        affected = self.get_affected_units(changed_files)

        if not affected:
            logger.info("No affected units found - skipping regression")
            return RegressionResult(
                all_passed=True,
                total_tests=0,
                passed_tests=0,
                failed_tests=0,
                skipped_tests=0,
                scope=RegressionScope.AFFECTED,
                metadata={"changed_files": changed_files},
            )

        # Temporarily swap completed units
        original_units = self._completed_units
        self._completed_units = affected

        result = self.run_regression(scope=RegressionScope.AFFECTED)
        result.metadata["changed_files"] = changed_files
        result.metadata["affected_units"] = [u.id for u in affected]

        # Restore
        self._completed_units = original_units

        return result

    def get_last_result(self) -> Optional[RegressionResult]:
        """Returns the last regression result."""
        return self._last_result

    def get_statistics(self) -> Dict[str, Any]:
        """Returns guardian statistics."""
        return {
            "registered_units": len(self._completed_units),
            "registered_tests": len(self._regression_tests),
            "critical_tests": len([t for t in self._regression_tests if t.critical]),
            "last_result": {
                "all_passed": self._last_result.all_passed,
                "pass_rate": self._last_result.pass_rate,
                "timestamp": self._last_result.timestamp.isoformat(),
            } if self._last_result else None,
        }

    def clear(self):
        """Clears all registered units and tests."""
        self._completed_units = []
        self._regression_tests = []
        self._last_result = None
