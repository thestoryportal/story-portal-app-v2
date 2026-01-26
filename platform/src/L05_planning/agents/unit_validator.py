"""
Unit Validator Agent - Validates AtomicUnits via acceptance criteria
Path: platform/src/L05_planning/agents/unit_validator.py
"""

import asyncio
import logging
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from .spec_decomposer import AtomicUnit, AcceptanceCriterion

logger = logging.getLogger(__name__)


class ValidationStatus(Enum):
    """Status of a validation run."""
    PENDING = "pending"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    TIMEOUT = "timeout"


@dataclass
class CriterionResult:
    """Result of validating a single acceptance criterion."""
    criterion_id: str
    status: ValidationStatus
    command: str
    output: str = ""
    error: str = ""
    duration_ms: int = 0
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class ValidationResult:
    """Result of validating an AtomicUnit."""
    unit_id: str
    passed: bool
    status: ValidationStatus
    criterion_results: List[CriterionResult] = field(default_factory=list)
    quality_score: Optional[float] = None
    total_duration_ms: int = 0
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def failed_criteria(self) -> List[CriterionResult]:
        """Returns list of failed criterion results."""
        return [r for r in self.criterion_results
                if r.status in (ValidationStatus.FAILED, ValidationStatus.TIMEOUT)]

    @property
    def passed_criteria(self) -> List[CriterionResult]:
        """Returns list of passed criterion results."""
        return [r for r in self.criterion_results if r.status == ValidationStatus.PASSED]


class UnitValidator:
    """
    Validates AtomicUnits by running acceptance criteria commands.

    Integrates with L06 QualityScorer for optional quality scoring.
    """

    def __init__(
        self,
        quality_scorer: Optional[Any] = None,
        working_dir: Optional[str] = None,
        timeout_seconds: int = 60,
    ):
        """
        Initialize unit validator.

        Args:
            quality_scorer: Optional L06 QualityScorer for quality metrics
            working_dir: Working directory for running commands
            timeout_seconds: Default timeout for validation commands
        """
        self.quality_scorer = quality_scorer
        self.working_dir = working_dir
        self.timeout_seconds = timeout_seconds
        self._validation_count = 0
        self._pass_count = 0

    def validate(self, unit: AtomicUnit) -> ValidationResult:
        """
        Validates an AtomicUnit by running all acceptance criteria.

        Args:
            unit: AtomicUnit to validate

        Returns:
            ValidationResult with passed status and criterion results
        """
        start_time = datetime.now()
        criterion_results: List[CriterionResult] = []
        all_passed = True

        logger.info(f"Validating unit: {unit.id} - {unit.title}")

        for criterion in unit.acceptance_criteria:
            result = self._validate_criterion(criterion)
            criterion_results.append(result)

            if result.status not in (ValidationStatus.PASSED, ValidationStatus.SKIPPED):
                all_passed = False
                logger.warning(
                    f"Criterion {criterion.id} failed: {result.error or result.output}"
                )

        # Calculate total duration
        end_time = datetime.now()
        total_duration_ms = int((end_time - start_time).total_seconds() * 1000)

        # Update statistics
        self._validation_count += 1
        if all_passed:
            self._pass_count += 1

        result = ValidationResult(
            unit_id=unit.id,
            passed=all_passed,
            status=ValidationStatus.PASSED if all_passed else ValidationStatus.FAILED,
            criterion_results=criterion_results,
            total_duration_ms=total_duration_ms,
            timestamp=start_time,
            metadata={
                "unit_title": unit.title,
                "complexity": unit.complexity,
                "file_count": len(unit.files),
            }
        )

        logger.info(
            f"Unit {unit.id} validation complete: "
            f"{'PASSED' if all_passed else 'FAILED'} "
            f"({len(result.passed_criteria)}/{len(criterion_results)} criteria passed)"
        )

        return result

    async def validate_async(self, unit: AtomicUnit) -> ValidationResult:
        """
        Async version of validate for integration with async quality scorer.

        Args:
            unit: AtomicUnit to validate

        Returns:
            ValidationResult with passed status and optional quality score
        """
        # Run synchronous validation
        result = self.validate(unit)

        # Add quality score if scorer available
        if self.quality_scorer and result.passed:
            try:
                # Quality scoring is typically for agent execution, but we can
                # use it for tracking validation quality over time
                score = await self._compute_quality_score(unit, result)
                result.quality_score = score
            except Exception as e:
                logger.warning(f"Quality scoring failed: {e}")

        return result

    def _validate_criterion(self, criterion: AcceptanceCriterion) -> CriterionResult:
        """
        Validates a single acceptance criterion by running its command.

        Args:
            criterion: AcceptanceCriterion to validate

        Returns:
            CriterionResult with status and output
        """
        start_time = datetime.now()

        # Handle manual verification commands
        if "Manual verification" in criterion.validation_command:
            return CriterionResult(
                criterion_id=criterion.id,
                status=ValidationStatus.SKIPPED,
                command=criterion.validation_command,
                output="Manual verification required - skipped in automated run",
                duration_ms=0,
                timestamp=start_time,
            )

        try:
            # Run the validation command
            timeout = criterion.timeout_seconds or self.timeout_seconds

            process = subprocess.run(
                criterion.validation_command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=self.working_dir,
            )

            end_time = datetime.now()
            duration_ms = int((end_time - start_time).total_seconds() * 1000)

            # Check expected result
            if criterion.expected_result == "success":
                passed = process.returncode == 0
            else:
                # Check if expected result is in output
                passed = criterion.expected_result in process.stdout

            return CriterionResult(
                criterion_id=criterion.id,
                status=ValidationStatus.PASSED if passed else ValidationStatus.FAILED,
                command=criterion.validation_command,
                output=process.stdout,
                error=process.stderr,
                duration_ms=duration_ms,
                timestamp=start_time,
            )

        except subprocess.TimeoutExpired:
            return CriterionResult(
                criterion_id=criterion.id,
                status=ValidationStatus.TIMEOUT,
                command=criterion.validation_command,
                error=f"Command timed out after {timeout} seconds",
                duration_ms=timeout * 1000,
                timestamp=start_time,
            )
        except Exception as e:
            return CriterionResult(
                criterion_id=criterion.id,
                status=ValidationStatus.FAILED,
                command=criterion.validation_command,
                error=str(e),
                duration_ms=0,
                timestamp=start_time,
            )

    async def _compute_quality_score(
        self, unit: AtomicUnit, result: ValidationResult
    ) -> Optional[float]:
        """
        Computes quality score using L06 QualityScorer.

        This is a placeholder integration - in production, would pass
        actual metrics about the validation run.
        """
        if not self.quality_scorer:
            return None

        # For now, compute a simple pass rate score
        total = len(result.criterion_results)
        passed = len(result.passed_criteria)

        if total == 0:
            return 100.0

        return (passed / total) * 100.0

    def validate_batch(self, units: List[AtomicUnit]) -> List[ValidationResult]:
        """
        Validates multiple units in sequence.

        Args:
            units: List of AtomicUnits to validate

        Returns:
            List of ValidationResults
        """
        return [self.validate(unit) for unit in units]

    async def validate_batch_async(
        self, units: List[AtomicUnit], parallel: bool = False
    ) -> List[ValidationResult]:
        """
        Validates multiple units asynchronously.

        Args:
            units: List of AtomicUnits to validate
            parallel: If True, validates units in parallel

        Returns:
            List of ValidationResults
        """
        if parallel:
            tasks = [self.validate_async(unit) for unit in units]
            return await asyncio.gather(*tasks)
        else:
            results = []
            for unit in units:
                result = await self.validate_async(unit)
                results.append(result)
            return results

    def get_statistics(self) -> Dict[str, Any]:
        """Returns validation statistics."""
        return {
            "validation_count": self._validation_count,
            "pass_count": self._pass_count,
            "pass_rate": (
                self._pass_count / self._validation_count
                if self._validation_count > 0 else 0.0
            ),
        }

    def reset_statistics(self):
        """Resets validation statistics."""
        self._validation_count = 0
        self._pass_count = 0
