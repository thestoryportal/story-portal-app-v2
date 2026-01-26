"""
Parallel Validator - Validate independent units in parallel
Path: platform/src/L05_planning/services/parallel_validator.py

Features:
- Validate independent units in parallel
- Respect dependency graph
- Configurable max workers
- Aggregate validation results
"""

import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple
from uuid import uuid4

logger = logging.getLogger(__name__)


class ValidationStatus(Enum):
    """Status of a validation."""
    PENDING = "pending"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    ERROR = "error"


@dataclass
class UnitValidationResult:
    """Result of validating a single unit."""
    unit_id: str
    status: ValidationStatus
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_ms: int = 0
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    details: Dict[str, Any] = field(default_factory=dict)

    @property
    def passed(self) -> bool:
        """Check if validation passed."""
        return self.status == ValidationStatus.PASSED


@dataclass
class BatchValidationResult:
    """Result of validating a batch of units."""
    batch_id: str
    total_units: int
    passed_count: int
    failed_count: int
    skipped_count: int
    error_count: int
    unit_results: List[UnitValidationResult]
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    total_duration_ms: int = 0

    @property
    def success_rate(self) -> float:
        """Calculate success rate."""
        if self.total_units == 0:
            return 0.0
        return self.passed_count / self.total_units

    @property
    def all_passed(self) -> bool:
        """Check if all validations passed."""
        return self.passed_count == self.total_units


@dataclass
class DependencyInfo:
    """Dependency information for a unit."""
    unit_id: str
    depends_on: Set[str] = field(default_factory=set)
    depended_by: Set[str] = field(default_factory=set)

    @property
    def is_independent(self) -> bool:
        """Check if unit has no dependencies."""
        return len(self.depends_on) == 0


class ParallelValidator:
    """
    Validate independent units in parallel.

    Features:
    - Respect dependency graph
    - Configurable max workers
    - Validate in waves (independent units first)
    - Aggregate results
    """

    def __init__(
        self,
        unit_validator: Optional[Any] = None,
        max_workers: int = 4,
        fail_fast: bool = False,
        timeout_seconds: int = 60,
    ):
        """
        Initialize parallel validator.

        Args:
            unit_validator: UnitValidator instance for single unit validation
            max_workers: Maximum parallel workers
            fail_fast: Stop on first failure
            timeout_seconds: Timeout for each validation
        """
        self.unit_validator = unit_validator
        self.max_workers = max_workers
        self.fail_fast = fail_fast
        self.timeout_seconds = timeout_seconds

        # Validation function registry
        self._validators: Dict[str, Callable] = {}

    def register_validator(
        self,
        unit_type: str,
        validator: Callable[[Any, Dict[str, Any]], UnitValidationResult],
    ):
        """
        Register a validator function for a unit type.

        Args:
            unit_type: Type of unit this validates
            validator: Function that takes (unit, context) and returns UnitValidationResult
        """
        self._validators[unit_type] = validator
        logger.info(f"Registered validator for unit type: {unit_type}")

    async def validate_units(
        self,
        units: List[Any],
        context: Optional[Dict[str, Any]] = None,
    ) -> BatchValidationResult:
        """
        Validate units in parallel, respecting dependencies.

        Args:
            units: List of units to validate
            context: Validation context

        Returns:
            BatchValidationResult
        """
        context = context or {}
        batch_id = f"batch_{uuid4().hex[:8]}"
        started_at = datetime.now()

        # Build dependency graph
        dep_graph = self._build_dependency_graph(units)

        # Get execution order (waves of independent units)
        waves = self._get_execution_waves(units, dep_graph)

        # Track results
        all_results: List[UnitValidationResult] = []
        completed_units: Set[str] = set()
        failed = False

        # Execute wave by wave
        for wave_idx, wave in enumerate(waves):
            if failed and self.fail_fast:
                # Skip remaining waves
                for unit in wave:
                    unit_id = self._get_unit_id(unit)
                    all_results.append(UnitValidationResult(
                        unit_id=unit_id,
                        status=ValidationStatus.SKIPPED,
                        details={"reason": "previous_failure"},
                    ))
                continue

            logger.info(f"Validating wave {wave_idx + 1}/{len(waves)} with {len(wave)} units")

            # Validate wave in parallel
            wave_results = await self._validate_wave(wave, context, completed_units)
            all_results.extend(wave_results)

            # Update completed units
            for result in wave_results:
                if result.passed:
                    completed_units.add(result.unit_id)
                elif result.status == ValidationStatus.FAILED:
                    failed = True

        completed_at = datetime.now()
        total_duration_ms = int((completed_at - started_at).total_seconds() * 1000)

        # Count results
        passed_count = sum(1 for r in all_results if r.status == ValidationStatus.PASSED)
        failed_count = sum(1 for r in all_results if r.status == ValidationStatus.FAILED)
        skipped_count = sum(1 for r in all_results if r.status == ValidationStatus.SKIPPED)
        error_count = sum(1 for r in all_results if r.status == ValidationStatus.ERROR)

        return BatchValidationResult(
            batch_id=batch_id,
            total_units=len(units),
            passed_count=passed_count,
            failed_count=failed_count,
            skipped_count=skipped_count,
            error_count=error_count,
            unit_results=all_results,
            started_at=started_at,
            completed_at=completed_at,
            total_duration_ms=total_duration_ms,
        )

    def validate_units_sync(
        self,
        units: List[Any],
        context: Optional[Dict[str, Any]] = None,
    ) -> BatchValidationResult:
        """
        Synchronous version of validate_units.

        Args:
            units: List of units to validate
            context: Validation context

        Returns:
            BatchValidationResult
        """
        return asyncio.run(self.validate_units(units, context))

    async def _validate_wave(
        self,
        wave: List[Any],
        context: Dict[str, Any],
        completed_units: Set[str],
    ) -> List[UnitValidationResult]:
        """Validate a wave of independent units in parallel."""
        results: List[UnitValidationResult] = []

        # Create tasks for each unit
        tasks = []
        for unit in wave:
            task = asyncio.create_task(
                self._validate_unit_with_timeout(unit, context, completed_units)
            )
            tasks.append((unit, task))

        # Wait for all tasks
        for unit, task in tasks:
            try:
                result = await task
                results.append(result)
            except asyncio.TimeoutError:
                unit_id = self._get_unit_id(unit)
                results.append(UnitValidationResult(
                    unit_id=unit_id,
                    status=ValidationStatus.ERROR,
                    errors=[f"Validation timed out after {self.timeout_seconds}s"],
                ))
            except Exception as e:
                unit_id = self._get_unit_id(unit)
                results.append(UnitValidationResult(
                    unit_id=unit_id,
                    status=ValidationStatus.ERROR,
                    errors=[str(e)],
                ))

        return results

    async def _validate_unit_with_timeout(
        self,
        unit: Any,
        context: Dict[str, Any],
        completed_units: Set[str],
    ) -> UnitValidationResult:
        """Validate a single unit with timeout."""
        return await asyncio.wait_for(
            self._validate_unit(unit, context, completed_units),
            timeout=self.timeout_seconds,
        )

    async def _validate_unit(
        self,
        unit: Any,
        context: Dict[str, Any],
        completed_units: Set[str],
    ) -> UnitValidationResult:
        """Validate a single unit."""
        unit_id = self._get_unit_id(unit)
        unit_type = self._get_unit_type(unit)
        started_at = datetime.now()

        try:
            # Check dependencies are completed
            deps = self._get_dependencies(unit)
            for dep in deps:
                if dep not in completed_units:
                    return UnitValidationResult(
                        unit_id=unit_id,
                        status=ValidationStatus.SKIPPED,
                        started_at=started_at,
                        completed_at=datetime.now(),
                        errors=[f"Dependency not completed: {dep}"],
                    )

            # Use registered validator if available
            if unit_type in self._validators:
                validator = self._validators[unit_type]
                result = await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: validator(unit, context),
                )
                return result

            # Use unit_validator if available
            if self.unit_validator:
                # Run in executor to not block
                result = await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: self._run_unit_validator(unit, context),
                )
                return result

            # Default validation: check unit has required fields
            result = self._default_validation(unit)
            result.started_at = started_at
            result.completed_at = datetime.now()
            result.duration_ms = int((result.completed_at - started_at).total_seconds() * 1000)
            return result

        except Exception as e:
            completed_at = datetime.now()
            return UnitValidationResult(
                unit_id=unit_id,
                status=ValidationStatus.ERROR,
                started_at=started_at,
                completed_at=completed_at,
                duration_ms=int((completed_at - started_at).total_seconds() * 1000),
                errors=[str(e)],
            )

    def _run_unit_validator(
        self,
        unit: Any,
        context: Dict[str, Any],
    ) -> UnitValidationResult:
        """Run the unit validator synchronously."""
        unit_id = self._get_unit_id(unit)
        started_at = datetime.now()

        try:
            # Call the unit validator
            if hasattr(self.unit_validator, 'validate_unit'):
                validation_result = self.unit_validator.validate_unit(unit, context)
            elif hasattr(self.unit_validator, 'validate'):
                validation_result = self.unit_validator.validate(unit, context)
            else:
                return UnitValidationResult(
                    unit_id=unit_id,
                    status=ValidationStatus.ERROR,
                    errors=["Unit validator has no validate method"],
                )

            completed_at = datetime.now()
            duration_ms = int((completed_at - started_at).total_seconds() * 1000)

            # Convert validation result to our format
            if hasattr(validation_result, 'is_valid'):
                status = ValidationStatus.PASSED if validation_result.is_valid else ValidationStatus.FAILED
                errors = getattr(validation_result, 'errors', [])
                warnings = getattr(validation_result, 'warnings', [])
            elif isinstance(validation_result, bool):
                status = ValidationStatus.PASSED if validation_result else ValidationStatus.FAILED
                errors = []
                warnings = []
            else:
                status = ValidationStatus.PASSED
                errors = []
                warnings = []

            return UnitValidationResult(
                unit_id=unit_id,
                status=status,
                started_at=started_at,
                completed_at=completed_at,
                duration_ms=duration_ms,
                errors=list(errors) if errors else [],
                warnings=list(warnings) if warnings else [],
            )

        except Exception as e:
            completed_at = datetime.now()
            return UnitValidationResult(
                unit_id=unit_id,
                status=ValidationStatus.ERROR,
                started_at=started_at,
                completed_at=completed_at,
                duration_ms=int((completed_at - started_at).total_seconds() * 1000),
                errors=[str(e)],
            )

    def _default_validation(self, unit: Any) -> UnitValidationResult:
        """Default validation for units without a specific validator."""
        unit_id = self._get_unit_id(unit)
        errors = []
        warnings = []

        # Check for required fields
        required_fields = ['id', 'type', 'description']
        for field in required_fields:
            if not hasattr(unit, field) or getattr(unit, field) is None:
                # Try alternate names
                alt_names = {
                    'id': ['unit_id', 'identifier'],
                    'type': ['unit_type', 'kind'],
                    'description': ['desc', 'content', 'details'],
                }
                found = False
                for alt in alt_names.get(field, []):
                    if hasattr(unit, alt) and getattr(unit, alt) is not None:
                        found = True
                        break
                if not found:
                    warnings.append(f"Missing recommended field: {field}")

        # Check for acceptance criteria
        if hasattr(unit, 'acceptance_criteria'):
            criteria = getattr(unit, 'acceptance_criteria')
            if not criteria:
                warnings.append("No acceptance criteria defined")

        status = ValidationStatus.PASSED if not errors else ValidationStatus.FAILED

        return UnitValidationResult(
            unit_id=unit_id,
            status=status,
            errors=errors,
            warnings=warnings,
        )

    def _build_dependency_graph(
        self,
        units: List[Any],
    ) -> Dict[str, DependencyInfo]:
        """Build a dependency graph from units."""
        graph: Dict[str, DependencyInfo] = {}

        # Initialize all units
        for unit in units:
            unit_id = self._get_unit_id(unit)
            graph[unit_id] = DependencyInfo(unit_id=unit_id)

        # Build dependencies
        for unit in units:
            unit_id = self._get_unit_id(unit)
            deps = self._get_dependencies(unit)

            for dep in deps:
                # Add dependency
                graph[unit_id].depends_on.add(dep)

                # Add reverse dependency
                if dep in graph:
                    graph[dep].depended_by.add(unit_id)

        return graph

    def _get_execution_waves(
        self,
        units: List[Any],
        dep_graph: Dict[str, DependencyInfo],
    ) -> List[List[Any]]:
        """
        Get execution waves - groups of units that can be validated in parallel.

        Uses topological sorting to ensure dependencies are respected.
        """
        waves: List[List[Any]] = []
        remaining = {self._get_unit_id(u): u for u in units}
        completed: Set[str] = set()

        while remaining:
            # Find units with all dependencies satisfied
            wave = []
            for unit_id, unit in remaining.items():
                deps = dep_graph.get(unit_id, DependencyInfo(unit_id=unit_id)).depends_on
                if deps <= completed:  # All dependencies completed
                    wave.append(unit)

            if not wave:
                # Circular dependency or missing dependency
                # Add remaining units in a single wave
                logger.warning(f"Possible circular dependency, adding {len(remaining)} remaining units")
                wave = list(remaining.values())

            waves.append(wave)

            # Mark wave units as completed
            for unit in wave:
                unit_id = self._get_unit_id(unit)
                completed.add(unit_id)
                del remaining[unit_id]

        return waves

    def _get_unit_id(self, unit: Any) -> str:
        """Get unit ID from unit object."""
        if hasattr(unit, 'id'):
            return str(unit.id)
        if hasattr(unit, 'unit_id'):
            return str(unit.unit_id)
        if hasattr(unit, 'identifier'):
            return str(unit.identifier)
        return str(id(unit))

    def _get_unit_type(self, unit: Any) -> str:
        """Get unit type from unit object."""
        if hasattr(unit, 'type'):
            return str(unit.type)
        if hasattr(unit, 'unit_type'):
            return str(unit.unit_type)
        if hasattr(unit, 'kind'):
            return str(unit.kind)
        return "unknown"

    def _get_dependencies(self, unit: Any) -> Set[str]:
        """Get dependencies from unit object."""
        deps: Set[str] = set()

        # Try different attribute names
        for attr in ['dependencies', 'depends_on', 'requires', 'blockers']:
            if hasattr(unit, attr):
                dep_list = getattr(unit, attr)
                if dep_list:
                    for dep in dep_list:
                        if isinstance(dep, str):
                            deps.add(dep)
                        elif hasattr(dep, 'id'):
                            deps.add(str(dep.id))
                        elif hasattr(dep, 'unit_id'):
                            deps.add(str(dep.unit_id))

        return deps

    def get_independent_units(self, units: List[Any]) -> List[Any]:
        """Get units that have no dependencies."""
        dep_graph = self._build_dependency_graph(units)
        return [u for u in units if dep_graph.get(self._get_unit_id(u), DependencyInfo("")).is_independent]

    def get_dependency_order(self, units: List[Any]) -> List[str]:
        """Get unit IDs in dependency order."""
        waves = self._get_execution_waves(units, self._build_dependency_graph(units))
        order = []
        for wave in waves:
            for unit in wave:
                order.append(self._get_unit_id(unit))
        return order
