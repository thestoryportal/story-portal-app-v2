"""
L06 Bridge - Connects L05 Planning to L06 Evaluation
Path: platform/src/L05_planning/integration/l06_bridge.py

Enhanced with real HTTP client support for connecting to L06 service.
"""

import logging
import os
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import uuid4

from ..agents.spec_decomposer import AtomicUnit
from ..agents.unit_validator import ValidationResult

logger = logging.getLogger(__name__)

# Optional httpx import for real HTTP calls
try:
    import httpx
    HTTPX_AVAILABLE = True
except ImportError:
    HTTPX_AVAILABLE = False
    logger.warning("httpx not available, L06Bridge will use local scoring only")


class ScoreDimension(Enum):
    """Dimensions for quality scoring."""
    ACCURACY = "accuracy"
    COMPLETENESS = "completeness"
    EFFICIENCY = "efficiency"
    MAINTAINABILITY = "maintainability"
    TESTABILITY = "testability"


class AssessmentLevel(Enum):
    """Assessment levels based on score."""
    EXCELLENT = "excellent"  # >= 90
    GOOD = "good"  # >= 80
    ACCEPTABLE = "acceptable"  # >= 70
    WARNING = "warning"  # >= 60
    CRITICAL = "critical"  # < 60


@dataclass
class DimensionScore:
    """Score for a single dimension."""
    dimension: ScoreDimension
    score: float  # 0-100
    weight: float
    details: str = ""


@dataclass
class UnitScore:
    """Quality score for an atomic unit."""
    unit_id: str
    score: float  # 0-100 overall score
    assessment: AssessmentLevel
    dimensions: Dict[ScoreDimension, DimensionScore] = field(default_factory=dict)
    validation_score: float = 0.0
    execution_score: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PlanScore:
    """Quality score for an entire plan."""
    plan_id: str
    score: float  # 0-100 overall score
    assessment: AssessmentLevel
    unit_scores: List[UnitScore] = field(default_factory=list)
    coverage: float = 0.0  # Percentage of units validated
    timestamp: datetime = field(default_factory=datetime.now)


class L06Bridge:
    """
    Bridge to L06 Evaluation for quality scoring.

    Features:
    - Real HTTP connection to L06 service (localhost:8006)
    - Health check on initialization
    - Graceful fallback to local scoring when L06 unavailable

    Provides abstraction for:
    - Scoring atomic units
    - Scoring plans
    - Tracking quality metrics
    - Assessment determination
    """

    def __init__(
        self,
        quality_scorer: Optional[Any] = None,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        timeout: float = 30.0,
    ):
        """
        Initialize L06 bridge.

        Args:
            quality_scorer: Optional L06 QualityScorer instance (for dependency injection)
            base_url: Base URL for L06 service (default: http://localhost:8006)
            api_key: API key for L06 authentication
            timeout: HTTP request timeout in seconds
        """
        self.quality_scorer = quality_scorer
        self.base_url = base_url or os.getenv("L06_BASE_URL", "http://localhost:8006")
        self.api_key = api_key or os.getenv("L06_API_KEY", "test_token_123")
        self.timeout = timeout

        self._score_history: List[UnitScore] = []
        self._dimension_weights = {
            ScoreDimension.ACCURACY: 0.25,
            ScoreDimension.COMPLETENESS: 0.25,
            ScoreDimension.EFFICIENCY: 0.20,
            ScoreDimension.MAINTAINABILITY: 0.15,
            ScoreDimension.TESTABILITY: 0.15,
        }
        self._initialized = False
        self._connected = False
        self._http_client: Optional["httpx.AsyncClient"] = None

        # Statistics
        self._remote_score_count = 0
        self._local_score_count = 0

    async def initialize(self):
        """Initialize connection to L06 with health check."""
        if self._initialized:
            return

        logger.info(f"Initializing L06Bridge (base_url={self.base_url})")

        if HTTPX_AVAILABLE:
            try:
                self._http_client = httpx.AsyncClient(
                    base_url=self.base_url,
                    timeout=self.timeout,
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                )

                # Health check
                response = await self._http_client.get("/health/live")
                if response.status_code == 200:
                    self._connected = True
                    logger.info("L06Bridge connected to L06 service")
                else:
                    logger.warning(f"L06 health check failed: {response.status_code}")
                    self._connected = False

            except Exception as e:
                logger.warning(f"Failed to connect to L06: {e}. Using local scoring.")
                self._connected = False
                if self._http_client:
                    await self._http_client.aclose()
                    self._http_client = None
        else:
            logger.info("httpx not available, using local scoring only")
            self._connected = False

        self._initialized = True
        logger.info(f"L06Bridge initialized (connected={self._connected})")

    async def close(self):
        """Close HTTP client connection."""
        if self._http_client:
            await self._http_client.aclose()
            self._http_client = None
        self._connected = False

    def score_unit(
        self,
        unit: AtomicUnit,
        validation_result: Optional[ValidationResult] = None,
    ) -> UnitScore:
        """
        Scores an atomic unit based on quality dimensions.

        Args:
            unit: AtomicUnit to score
            validation_result: Optional validation result for bonus scoring

        Returns:
            UnitScore with overall score and dimension scores
        """
        logger.debug(f"Scoring unit: {unit.id}")

        # Calculate dimension scores
        dimensions = self._calculate_dimension_scores(unit, validation_result)

        # Calculate overall score
        overall_score = sum(
            dim.score * dim.weight for dim in dimensions.values()
        )

        # Calculate validation score bonus
        validation_score = 0.0
        if validation_result:
            total_criteria = len(validation_result.criterion_results)
            passed_criteria = len(validation_result.passed_criteria)
            if total_criteria > 0:
                validation_score = (passed_criteria / total_criteria) * 100

        # Factor in validation
        if validation_score > 0:
            overall_score = (overall_score * 0.7) + (validation_score * 0.3)

        # Determine assessment level
        assessment = self._determine_assessment(overall_score)

        score = UnitScore(
            unit_id=unit.id,
            score=overall_score,
            assessment=assessment,
            dimensions=dimensions,
            validation_score=validation_score,
            metadata={
                "complexity": unit.complexity,
                "file_count": len(unit.files),
                "dependency_count": len(unit.dependencies),
            }
        )

        self._score_history.append(score)
        self._local_score_count += 1
        logger.info(f"Unit {unit.id} scored: {overall_score:.1f} ({assessment.value})")

        return score

    async def score_unit_async(
        self,
        unit: AtomicUnit,
        validation_result: Optional[ValidationResult] = None,
    ) -> UnitScore:
        """
        Scores an atomic unit (async with remote support).

        Args:
            unit: AtomicUnit to score
            validation_result: Optional validation result for bonus scoring

        Returns:
            UnitScore with overall score and dimension scores
        """
        logger.debug(f"Scoring unit async: {unit.id}")

        # Try remote scoring first
        if self._connected and self._http_client:
            try:
                remote_score = await self._score_unit_remote(unit, validation_result)
                if remote_score:
                    self._score_history.append(remote_score)
                    self._remote_score_count += 1
                    return remote_score
            except Exception as e:
                logger.warning(f"Remote scoring failed, falling back to local: {e}")

        # Fall back to local scoring
        return self.score_unit(unit, validation_result)

    async def _score_unit_remote(
        self,
        unit: AtomicUnit,
        validation_result: Optional[ValidationResult],
    ) -> Optional[UnitScore]:
        """Score unit via HTTP to L06 service."""
        if not self._http_client:
            return None

        # Prepare payload
        payload = {
            "unit_id": unit.id,
            "title": unit.title,
            "description": unit.description,
            "files": unit.files,
            "complexity": unit.complexity,
            "acceptance_criteria": [
                {"description": c.description, "validation_command": c.validation_command}
                for c in unit.acceptance_criteria
            ],
            "dependencies": list(unit.dependencies),
        }

        if validation_result:
            payload["validation"] = {
                "passed": validation_result.passed,
                "status": validation_result.status.value,
                "passed_count": len(validation_result.passed_criteria),
                "failed_count": len(validation_result.failed_criteria),
            }

        response = await self._http_client.post("/api/evaluations/score", json=payload)

        if response.status_code == 200:
            data = response.json()

            # Parse dimension scores
            dimensions = {}
            for dim_data in data.get("dimensions", []):
                dim_type = ScoreDimension(dim_data["dimension"])
                dimensions[dim_type] = DimensionScore(
                    dimension=dim_type,
                    score=dim_data["score"],
                    weight=dim_data.get("weight", self._dimension_weights.get(dim_type, 0.2)),
                    details=dim_data.get("details", ""),
                )

            return UnitScore(
                unit_id=unit.id,
                score=data.get("score", 0.0),
                assessment=AssessmentLevel(data.get("assessment", "acceptable")),
                dimensions=dimensions,
                validation_score=data.get("validation_score", 0.0),
                execution_score=data.get("execution_score", 0.0),
                metadata=data.get("metadata", {"remote": True}),
            )
        else:
            logger.warning(f"L06 scoring failed: {response.status_code} - {response.text}")
            return None

    def score_plan(
        self,
        plan_id: str,
        units: List[AtomicUnit],
        validation_results: Optional[Dict[str, ValidationResult]] = None,
    ) -> PlanScore:
        """
        Scores an entire plan.

        Args:
            plan_id: Plan identifier
            units: List of AtomicUnits in the plan
            validation_results: Optional map of unit_id -> ValidationResult

        Returns:
            PlanScore with overall and unit scores
        """
        logger.info(f"Scoring plan: {plan_id} ({len(units)} units)")

        validation_results = validation_results or {}
        unit_scores = []

        for unit in units:
            validation = validation_results.get(unit.id)
            unit_score = self.score_unit(unit, validation)
            unit_scores.append(unit_score)

        # Calculate overall plan score
        if unit_scores:
            overall_score = sum(s.score for s in unit_scores) / len(unit_scores)
        else:
            overall_score = 0.0

        # Calculate coverage
        validated_count = len([s for s in unit_scores if s.validation_score > 0])
        coverage = (validated_count / len(units) * 100) if units else 0.0

        assessment = self._determine_assessment(overall_score)

        return PlanScore(
            plan_id=plan_id,
            score=overall_score,
            assessment=assessment,
            unit_scores=unit_scores,
            coverage=coverage,
        )

    async def score_plan_async(
        self,
        plan_id: str,
        units: List[AtomicUnit],
        validation_results: Optional[Dict[str, ValidationResult]] = None,
    ) -> PlanScore:
        """
        Scores an entire plan (async with remote support).

        Args:
            plan_id: Plan identifier
            units: List of AtomicUnits in the plan
            validation_results: Optional map of unit_id -> ValidationResult

        Returns:
            PlanScore with overall and unit scores
        """
        logger.info(f"Scoring plan async: {plan_id} ({len(units)} units)")

        validation_results = validation_results or {}
        unit_scores = []

        for unit in units:
            validation = validation_results.get(unit.id)
            unit_score = await self.score_unit_async(unit, validation)
            unit_scores.append(unit_score)

        # Calculate overall plan score
        if unit_scores:
            overall_score = sum(s.score for s in unit_scores) / len(unit_scores)
        else:
            overall_score = 0.0

        # Calculate coverage
        validated_count = len([s for s in unit_scores if s.validation_score > 0])
        coverage = (validated_count / len(units) * 100) if units else 0.0

        assessment = self._determine_assessment(overall_score)

        return PlanScore(
            plan_id=plan_id,
            score=overall_score,
            assessment=assessment,
            unit_scores=unit_scores,
            coverage=coverage,
        )

    def _calculate_dimension_scores(
        self,
        unit: AtomicUnit,
        validation_result: Optional[ValidationResult],
    ) -> Dict[ScoreDimension, DimensionScore]:
        """Calculates scores for each quality dimension."""
        scores = {}

        # Accuracy - based on acceptance criteria coverage
        accuracy = self._score_accuracy(unit, validation_result)
        scores[ScoreDimension.ACCURACY] = DimensionScore(
            dimension=ScoreDimension.ACCURACY,
            score=accuracy,
            weight=self._dimension_weights[ScoreDimension.ACCURACY],
            details="Based on acceptance criteria coverage",
        )

        # Completeness - based on description and metadata
        completeness = self._score_completeness(unit)
        scores[ScoreDimension.COMPLETENESS] = DimensionScore(
            dimension=ScoreDimension.COMPLETENESS,
            score=completeness,
            weight=self._dimension_weights[ScoreDimension.COMPLETENESS],
            details="Based on specification completeness",
        )

        # Efficiency - based on complexity estimate
        efficiency = self._score_efficiency(unit)
        scores[ScoreDimension.EFFICIENCY] = DimensionScore(
            dimension=ScoreDimension.EFFICIENCY,
            score=efficiency,
            weight=self._dimension_weights[ScoreDimension.EFFICIENCY],
            details="Based on complexity analysis",
        )

        # Maintainability - based on structure
        maintainability = self._score_maintainability(unit)
        scores[ScoreDimension.MAINTAINABILITY] = DimensionScore(
            dimension=ScoreDimension.MAINTAINABILITY,
            score=maintainability,
            weight=self._dimension_weights[ScoreDimension.MAINTAINABILITY],
            details="Based on code structure",
        )

        # Testability - based on acceptance criteria
        testability = self._score_testability(unit)
        scores[ScoreDimension.TESTABILITY] = DimensionScore(
            dimension=ScoreDimension.TESTABILITY,
            score=testability,
            weight=self._dimension_weights[ScoreDimension.TESTABILITY],
            details="Based on test coverage potential",
        )

        return scores

    def _score_accuracy(
        self,
        unit: AtomicUnit,
        validation_result: Optional[ValidationResult],
    ) -> float:
        """Score accuracy dimension."""
        base_score = 70.0

        # Bonus for having acceptance criteria
        if unit.acceptance_criteria:
            base_score += min(len(unit.acceptance_criteria) * 5, 15)

        # Bonus for validation results
        if validation_result and validation_result.passed:
            base_score += 15

        return min(base_score, 100.0)

    def _score_completeness(self, unit: AtomicUnit) -> float:
        """Score completeness dimension."""
        base_score = 60.0

        # Description quality
        if len(unit.description) > 50:
            base_score += 10
        if len(unit.description) > 100:
            base_score += 5

        # File specification
        if unit.files:
            base_score += min(len(unit.files) * 5, 15)

        # Dependencies specified
        if unit.dependencies:
            base_score += 5

        # Phase specified
        if unit.phase:
            base_score += 5

        return min(base_score, 100.0)

    def _score_efficiency(self, unit: AtomicUnit) -> float:
        """Score efficiency dimension."""
        # Start with baseline
        if unit.complexity == "low":
            base_score = 90.0
        elif unit.complexity == "medium":
            base_score = 75.0
        else:  # high
            base_score = 60.0

        # Penalize for too many files
        if len(unit.files) > 5:
            base_score -= 10

        # Penalize for too many dependencies
        if len(unit.dependencies) > 3:
            base_score -= 10

        return max(base_score, 30.0)

    def _score_maintainability(self, unit: AtomicUnit) -> float:
        """Score maintainability dimension."""
        base_score = 70.0

        # Small units are more maintainable
        if unit.complexity == "low":
            base_score += 15
        elif unit.complexity == "medium":
            base_score += 5

        # Clear compensation action
        if unit.compensation_action:
            base_score += 10

        return min(base_score, 100.0)

    def _score_testability(self, unit: AtomicUnit) -> float:
        """Score testability dimension."""
        base_score = 60.0

        # Acceptance criteria are testable
        criteria_count = len(unit.acceptance_criteria)
        if criteria_count > 0:
            base_score += min(criteria_count * 10, 30)

        # Specific files are more testable
        if unit.files:
            base_score += 10

        return min(base_score, 100.0)

    def _determine_assessment(self, score: float) -> AssessmentLevel:
        """Determines assessment level from score."""
        if score >= 90:
            return AssessmentLevel.EXCELLENT
        elif score >= 80:
            return AssessmentLevel.GOOD
        elif score >= 70:
            return AssessmentLevel.ACCEPTABLE
        elif score >= 60:
            return AssessmentLevel.WARNING
        else:
            return AssessmentLevel.CRITICAL

    def get_score_history(
        self,
        unit_id: Optional[str] = None,
        limit: int = 100,
    ) -> List[UnitScore]:
        """Gets scoring history."""
        history = self._score_history
        if unit_id:
            history = [s for s in history if s.unit_id == unit_id]
        return history[-limit:]

    def get_statistics(self) -> Dict[str, Any]:
        """Returns bridge statistics."""
        if not self._score_history:
            return {
                "total_scores": 0,
                "average_score": 0.0,
                "initialized": self._initialized,
                "connected": self._connected,
                "base_url": self.base_url,
                "remote_score_count": self._remote_score_count,
                "local_score_count": self._local_score_count,
            }

        scores = [s.score for s in self._score_history]

        return {
            "total_scores": len(self._score_history),
            "average_score": sum(scores) / len(scores),
            "min_score": min(scores),
            "max_score": max(scores),
            "assessment_distribution": self._get_assessment_distribution(),
            "initialized": self._initialized,
            "connected": self._connected,
            "base_url": self.base_url,
            "remote_score_count": self._remote_score_count,
            "local_score_count": self._local_score_count,
        }

    def is_connected(self) -> bool:
        """Returns True if connected to L06 service."""
        return self._connected

    def _get_assessment_distribution(self) -> Dict[str, int]:
        """Gets distribution of assessment levels."""
        distribution = {level.value: 0 for level in AssessmentLevel}
        for score in self._score_history:
            distribution[score.assessment.value] += 1
        return distribution

    def clear_history(self):
        """Clears score history."""
        self._score_history = []
