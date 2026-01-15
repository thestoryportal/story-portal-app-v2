"""L07 Learning Layer - Model Validator Service.

Validates models before deployment through regression tests, benchmarks, and safety checks.
"""

import logging
import random
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field, asdict
from datetime import datetime

from ..models.model_artifact import ModelArtifact
from ..models.error_codes import LearningErrorCode, ValidationError

logger = logging.getLogger(__name__)


@dataclass
class StageResult:
    """Result of a validation stage."""
    stage_name: str
    passed: bool
    score: float  # 0-1
    details: Dict[str, Any] = field(default_factory=dict)
    duration_seconds: float = 0.0
    errors: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


@dataclass
class ValidationResult:
    """Complete validation result for a model."""
    model_id: str
    model_version: str
    baseline_model_id: Optional[str] = None

    # Overall result
    passed: bool = False
    recommendation: str = "REJECT"  # DEPLOY, REVIEW, REJECT
    confidence: float = 0.0

    # Stage results
    stages: Dict[str, StageResult] = field(default_factory=dict)

    # Regression detection
    regression_detected: bool = False
    regression_details: List[str] = field(default_factory=list)

    # Metadata
    validated_at: datetime = field(default_factory=datetime.utcnow)
    validated_by: str = "ModelValidator v1.0"
    total_duration_seconds: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        data = asdict(self)
        data['stages'] = {k: v.to_dict() for k, v in self.stages.items()}
        data['validated_at'] = self.validated_at.isoformat()
        return data


class ModelValidator:
    """Model validation suite for pre-deployment testing.

    Validates models through multiple stages: regression tests, performance
    benchmarks, safety analysis, diversity testing, and latency profiling.
    """

    def __init__(
        self,
        regression_test_threshold: float = 0.95,
        performance_degradation_threshold: float = 0.05,
        enable_safety_checks: bool = True
    ):
        """Initialize Model Validator.

        Args:
            regression_test_threshold: Minimum pass rate for regression tests
            performance_degradation_threshold: Maximum allowed performance drop
            enable_safety_checks: Whether to run safety analysis
        """
        self.regression_test_threshold = regression_test_threshold
        self.performance_degradation_threshold = performance_degradation_threshold
        self.enable_safety_checks = enable_safety_checks
        self.validation_count = 0

        logger.info(
            f"Initialized ModelValidator: "
            f"regression_threshold={regression_test_threshold}, "
            f"degradation_threshold={performance_degradation_threshold}"
        )

    async def validate_model(
        self,
        model: ModelArtifact,
        baseline_model: Optional[ModelArtifact] = None
    ) -> ValidationResult:
        """Run complete validation pipeline on model.

        Args:
            model: Model to validate
            baseline_model: Optional baseline for comparison

        Returns:
            Validation result with all stage results

        Raises:
            ValidationError: If validation fails critically
        """
        logger.info(
            f"Validating model {model.model_id} ({model.name}) v{model.version}"
        )

        start_time = datetime.utcnow()

        result = ValidationResult(
            model_id=model.model_id,
            model_version=model.version,
            baseline_model_id=baseline_model.model_id if baseline_model else None
        )

        # Stage 1: Regression Testing
        regression_result = await self.run_regression_tests(model)
        result.stages['regression'] = regression_result

        # Stage 2: Performance Benchmarking
        if baseline_model:
            perf_result = await self.run_performance_benchmarks(model, baseline_model)
            result.stages['performance'] = perf_result
        else:
            logger.info("Skipping performance comparison (no baseline)")

        # Stage 3: Safety Analysis
        if self.enable_safety_checks:
            safety_result = await self.run_safety_analysis(model)
            result.stages['safety'] = safety_result

        # Stage 4: Diversity Testing
        diversity_result = await self.run_diversity_testing(model)
        result.stages['diversity'] = diversity_result

        # Stage 5: Latency Profiling
        latency_result = await self.run_latency_profiling(model)
        result.stages['latency'] = latency_result

        # Compute overall result
        all_passed = all(stage.passed for stage in result.stages.values())
        critical_passed = (
            result.stages.get('regression', StageResult('', False, 0)).passed and
            result.stages.get('safety', StageResult('', True, 1)).passed
        )

        result.passed = all_passed
        result.confidence = sum(s.score for s in result.stages.values()) / len(result.stages)

        # Determine recommendation
        if all_passed:
            result.recommendation = "DEPLOY"
        elif critical_passed:
            result.recommendation = "REVIEW"
        else:
            result.recommendation = "REJECT"

        # Check for regressions
        if 'performance' in result.stages:
            perf_stage = result.stages['performance']
            if not perf_stage.passed:
                result.regression_detected = True
                result.regression_details.append(
                    f"Performance degradation detected: {perf_stage.details.get('degradation', 0):.2%}"
                )

        # Calculate total duration
        end_time = datetime.utcnow()
        result.total_duration_seconds = (end_time - start_time).total_seconds()

        self.validation_count += 1

        logger.info(
            f"Validation complete for {model.model_id}: "
            f"recommendation={result.recommendation}, "
            f"passed={result.passed}, "
            f"confidence={result.confidence:.4f}"
        )

        return result

    async def run_regression_tests(
        self,
        model: ModelArtifact
    ) -> StageResult:
        """Run regression test suite on model.

        Args:
            model: Model to test

        Returns:
            Stage result
        """
        logger.info(f"Running regression tests for {model.model_id}")

        # Simulated regression tests
        total_tests = 100
        passed_tests = random.randint(90, 100)
        pass_rate = passed_tests / total_tests

        passed = pass_rate >= self.regression_test_threshold

        result = StageResult(
            stage_name="regression",
            passed=passed,
            score=pass_rate,
            details={
                'total_tests': total_tests,
                'passed_tests': passed_tests,
                'failed_tests': total_tests - passed_tests,
                'pass_rate': pass_rate,
                'threshold': self.regression_test_threshold
            },
            duration_seconds=random.uniform(1.0, 3.0)
        )

        if not passed:
            result.errors.append(
                f"Pass rate {pass_rate:.2%} below threshold {self.regression_test_threshold:.2%}"
            )

        logger.info(
            f"Regression tests: {passed_tests}/{total_tests} passed "
            f"({pass_rate:.2%}) - {'PASS' if passed else 'FAIL'}"
        )

        return result

    async def run_performance_benchmarks(
        self,
        model: ModelArtifact,
        baseline: ModelArtifact
    ) -> StageResult:
        """Compare model performance against baseline.

        Args:
            model: Model to benchmark
            baseline: Baseline model

        Returns:
            Stage result
        """
        logger.info(
            f"Benchmarking {model.model_id} against baseline {baseline.model_id}"
        )

        # Simulated performance comparison
        model_acc = model.metrics.accuracy if model.metrics else random.uniform(0.85, 0.95)
        baseline_acc = baseline.metrics.accuracy if baseline.metrics else random.uniform(0.80, 0.90)

        degradation = max(0, baseline_acc - model_acc)
        improvement = max(0, model_acc - baseline_acc)

        passed = degradation <= self.performance_degradation_threshold

        result = StageResult(
            stage_name="performance",
            passed=passed,
            score=1.0 - degradation if passed else 0.5,
            details={
                'model_accuracy': model_acc,
                'baseline_accuracy': baseline_acc,
                'degradation': degradation,
                'improvement': improvement,
                'threshold': self.performance_degradation_threshold
            },
            duration_seconds=random.uniform(2.0, 5.0)
        )

        if not passed:
            result.errors.append(
                f"Performance degradation {degradation:.2%} exceeds threshold "
                f"{self.performance_degradation_threshold:.2%}"
            )

        logger.info(
            f"Performance: model={model_acc:.4f}, baseline={baseline_acc:.4f}, "
            f"change={improvement - degradation:+.4f} - {'PASS' if passed else 'FAIL'}"
        )

        return result

    async def run_safety_analysis(
        self,
        model: ModelArtifact
    ) -> StageResult:
        """Run safety checks on model.

        Args:
            model: Model to analyze

        Returns:
            Stage result
        """
        logger.info(f"Running safety analysis for {model.model_id}")

        # Simulated safety checks
        backdoor_detected = random.random() < 0.02
        prompt_injection_vulnerable = random.random() < 0.05
        pii_leakage_detected = random.random() < 0.01

        issues = []
        if backdoor_detected:
            issues.append("Potential backdoor pattern detected")
        if prompt_injection_vulnerable:
            issues.append("Vulnerable to prompt injection attacks")
        if pii_leakage_detected:
            issues.append("Possible PII leakage in outputs")

        passed = len(issues) == 0
        safety_score = 1.0 - (len(issues) * 0.3)

        result = StageResult(
            stage_name="safety",
            passed=passed,
            score=max(0, safety_score),
            details={
                'backdoor_detected': backdoor_detected,
                'prompt_injection_vulnerable': prompt_injection_vulnerable,
                'pii_leakage_detected': pii_leakage_detected,
                'issues_found': len(issues)
            },
            duration_seconds=random.uniform(3.0, 6.0),
            errors=issues
        )

        logger.info(
            f"Safety analysis: {len(issues)} issues found - "
            f"{'PASS' if passed else 'FAIL'}"
        )

        if not passed:
            logger.warning(
                f"Safety issues detected in {model.model_id}: {issues}",
                extra={'error_code': LearningErrorCode.E7907.name}
            )

        return result

    async def run_diversity_testing(
        self,
        model: ModelArtifact
    ) -> StageResult:
        """Test model across diverse inputs.

        Args:
            model: Model to test

        Returns:
            Stage result
        """
        logger.info(f"Running diversity tests for {model.model_id}")

        # Simulated diversity testing across domains
        domains = ['travel', 'coding', 'qa', 'planning']
        domain_scores = {
            domain: random.uniform(0.75, 0.95)
            for domain in domains
        }

        min_score = min(domain_scores.values())
        avg_score = sum(domain_scores.values()) / len(domain_scores)
        passed = min_score >= 0.80

        result = StageResult(
            stage_name="diversity",
            passed=passed,
            score=avg_score,
            details={
                'domain_scores': domain_scores,
                'min_score': min_score,
                'avg_score': avg_score,
                'threshold': 0.80
            },
            duration_seconds=random.uniform(1.5, 3.0)
        )

        if not passed:
            worst_domain = min(domain_scores.items(), key=lambda x: x[1])
            result.errors.append(
                f"Low performance in {worst_domain[0]} domain: {worst_domain[1]:.2%}"
            )

        logger.info(
            f"Diversity: avg={avg_score:.4f}, min={min_score:.4f} - "
            f"{'PASS' if passed else 'FAIL'}"
        )

        return result

    async def run_latency_profiling(
        self,
        model: ModelArtifact
    ) -> StageResult:
        """Profile model inference latency.

        Args:
            model: Model to profile

        Returns:
            Stage result
        """
        logger.info(f"Profiling latency for {model.model_id}")

        # Simulated latency measurements
        p50 = random.uniform(1.5, 3.0)
        p95 = random.uniform(4.0, 7.0)
        p99 = random.uniform(8.0, 12.0)

        # Check if within acceptable range (p99 < 15ms)
        passed = p99 < 15.0

        result = StageResult(
            stage_name="latency",
            passed=passed,
            score=max(0, 1.0 - (p99 / 30.0)),  # Normalize to 30ms max
            details={
                'p50_ms': p50,
                'p95_ms': p95,
                'p99_ms': p99,
                'threshold_p99_ms': 15.0
            },
            duration_seconds=random.uniform(2.0, 4.0)
        )

        if not passed:
            result.errors.append(
                f"P99 latency {p99:.2f}ms exceeds threshold 15.0ms"
            )

        logger.info(
            f"Latency: p50={p50:.2f}ms, p95={p95:.2f}ms, p99={p99:.2f}ms - "
            f"{'PASS' if passed else 'FAIL'}"
        )

        return result

    def get_statistics(self) -> Dict[str, Any]:
        """Get validator statistics.

        Returns:
            Statistics dictionary
        """
        return {
            'total_validations': self.validation_count,
            'regression_threshold': self.regression_test_threshold,
            'degradation_threshold': self.performance_degradation_threshold,
            'safety_checks_enabled': self.enable_safety_checks
        }
