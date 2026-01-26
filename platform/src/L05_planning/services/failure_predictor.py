"""
Failure Predictor - Predict failures before execution
Path: platform/src/L05_planning/services/failure_predictor.py

Features:
- Analyze risk factors for units
- Predict likelihood of failure
- Suggest mitigations
- Integration with FailureLearner and L06 scoring
"""

import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)


class RiskLevel(Enum):
    """Risk levels for predictions."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class RiskCategory(Enum):
    """Categories of risk factors."""
    FILE_OPERATION = "file_operation"
    COMMAND_EXECUTION = "command_execution"
    DEPENDENCY = "dependency"
    RESOURCE = "resource"
    NETWORK = "network"
    PERMISSIONS = "permissions"
    COMPLEXITY = "complexity"
    HISTORY = "history"


@dataclass
class RiskFactor:
    """A specific risk factor identified."""
    category: RiskCategory
    description: str
    severity: float  # 0.0 to 1.0
    mitigation: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class FailurePrediction:
    """Prediction of failure likelihood for a unit."""
    unit_id: str
    risk_level: RiskLevel
    failure_probability: float  # 0.0 to 1.0
    risk_factors: List[RiskFactor]
    mitigations: List[str]
    similar_failure_count: int = 0
    confidence: float = 0.5  # Confidence in the prediction

    @property
    def should_checkpoint(self) -> bool:
        """Whether to create checkpoint before this unit."""
        return self.risk_level in (RiskLevel.HIGH, RiskLevel.CRITICAL)

    @property
    def top_risk(self) -> Optional[RiskFactor]:
        """Get the highest severity risk factor."""
        if not self.risk_factors:
            return None
        return max(self.risk_factors, key=lambda r: r.severity)


@dataclass
class PlanPrediction:
    """Aggregate prediction for an entire plan."""
    plan_id: str
    overall_risk: RiskLevel
    unit_predictions: List[FailurePrediction]
    critical_path_units: List[str]
    recommended_checkpoints: List[str]
    estimated_success_rate: float

    @property
    def high_risk_units(self) -> List[FailurePrediction]:
        """Get units with high or critical risk."""
        return [p for p in self.unit_predictions
                if p.risk_level in (RiskLevel.HIGH, RiskLevel.CRITICAL)]


class FailurePredictor:
    """
    Predict failures before execution.

    Features:
    - Analyze risk factors for units
    - Predict likelihood of failure based on multiple signals
    - Suggest mitigations
    - Integration with FailureLearner for historical data
    - Integration with L06 for quality scoring
    """

    def __init__(
        self,
        failure_learner: Optional[Any] = None,
        l06_bridge: Optional[Any] = None,
        risk_weights: Optional[Dict[RiskCategory, float]] = None,
    ):
        """
        Initialize failure predictor.

        Args:
            failure_learner: FailureLearner instance for historical data
            l06_bridge: L06Bridge instance for quality scoring
            risk_weights: Custom weights for risk categories
        """
        self.failure_learner = failure_learner
        self.l06_bridge = l06_bridge

        # Default weights for risk categories
        self.risk_weights = risk_weights or {
            RiskCategory.FILE_OPERATION: 0.7,
            RiskCategory.COMMAND_EXECUTION: 0.9,
            RiskCategory.DEPENDENCY: 0.8,
            RiskCategory.RESOURCE: 0.6,
            RiskCategory.NETWORK: 0.85,
            RiskCategory.PERMISSIONS: 0.8,
            RiskCategory.COMPLEXITY: 0.5,
            RiskCategory.HISTORY: 1.0,
        }

        # Risk analyzers
        self._analyzers: List[Callable] = [
            self._analyze_file_operations,
            self._analyze_command_execution,
            self._analyze_dependencies,
            self._analyze_resources,
            self._analyze_network,
            self._analyze_permissions,
            self._analyze_complexity,
            self._analyze_history,
        ]

        # High-risk patterns
        self._high_risk_patterns = {
            "rm -rf": "Recursive deletion can cause irreversible damage",
            "sudo": "Elevated privileges increase impact of errors",
            "chmod 777": "Overly permissive permissions create security risks",
            "DROP TABLE": "Database operations are hard to reverse",
            "DELETE FROM": "Database deletions may lose data",
            "force": "Force flags bypass safety checks",
            "--no-verify": "Skipping verification increases risk",
        }

        # Resource-intensive patterns
        self._resource_patterns = {
            "npm install": "Package installation can be slow and fail",
            "pip install": "Package installation may have conflicts",
            "docker build": "Container builds can be resource-intensive",
            "make": "Build processes may fail due to missing dependencies",
        }

    def predict_unit(
        self,
        unit: Any,
        context: Optional[Dict[str, Any]] = None,
    ) -> FailurePrediction:
        """
        Predict failure likelihood for a single unit.

        Args:
            unit: AtomicUnit to analyze
            context: Execution context

        Returns:
            FailurePrediction
        """
        context = context or {}
        risk_factors: List[RiskFactor] = []

        # Run all analyzers
        for analyzer in self._analyzers:
            try:
                factors = analyzer(unit, context)
                risk_factors.extend(factors)
            except Exception as e:
                logger.warning(f"Analyzer {analyzer.__name__} failed: {e}")

        # Calculate failure probability
        failure_probability = self._calculate_probability(risk_factors)

        # Determine risk level
        risk_level = self._determine_risk_level(failure_probability, risk_factors)

        # Collect mitigations
        mitigations = []
        for factor in risk_factors:
            if factor.mitigation and factor.mitigation not in mitigations:
                mitigations.append(factor.mitigation)

        # Add preventions from failure learner if available
        if self.failure_learner:
            similar_count = self._get_similar_failure_count(unit)
        else:
            similar_count = 0

        # Calculate confidence
        confidence = self._calculate_confidence(risk_factors, similar_count)

        unit_id = getattr(unit, 'id', None) or getattr(unit, 'unit_id', str(id(unit)))

        return FailurePrediction(
            unit_id=unit_id,
            risk_level=risk_level,
            failure_probability=failure_probability,
            risk_factors=risk_factors,
            mitigations=mitigations,
            similar_failure_count=similar_count,
            confidence=confidence,
        )

    def predict_plan(
        self,
        plan: Any,
        context: Optional[Dict[str, Any]] = None,
    ) -> PlanPrediction:
        """
        Predict failure likelihood for an entire plan.

        Args:
            plan: ParsedPlan or similar with units
            context: Execution context

        Returns:
            PlanPrediction
        """
        context = context or {}

        # Get units from plan
        units = self._extract_units(plan)

        # Predict each unit
        unit_predictions = []
        for unit in units:
            prediction = self.predict_unit(unit, context)
            unit_predictions.append(prediction)

        # Identify critical path (units that block others)
        critical_path = self._identify_critical_path(units, unit_predictions)

        # Recommend checkpoints
        checkpoints = self._recommend_checkpoints(unit_predictions)

        # Calculate overall risk
        overall_risk = self._calculate_overall_risk(unit_predictions)

        # Estimate success rate
        success_rate = self._estimate_success_rate(unit_predictions)

        plan_id = getattr(plan, 'id', None) or getattr(plan, 'plan_id', str(id(plan)))

        return PlanPrediction(
            plan_id=plan_id,
            overall_risk=overall_risk,
            unit_predictions=unit_predictions,
            critical_path_units=critical_path,
            recommended_checkpoints=checkpoints,
            estimated_success_rate=success_rate,
        )

    def _analyze_file_operations(
        self,
        unit: Any,
        context: Dict[str, Any],
    ) -> List[RiskFactor]:
        """Analyze file operation risks."""
        factors = []

        # Get operation details
        operation = getattr(unit, 'operation', None) or getattr(unit, 'type', '')
        file_path = getattr(unit, 'file_path', None) or getattr(unit, 'target_file', '')
        content = getattr(unit, 'content', '') or getattr(unit, 'description', '')

        if not operation and not file_path:
            return factors

        # Check for deletion operations
        if operation in ['delete', 'remove'] or 'delete' in str(content).lower():
            factors.append(RiskFactor(
                category=RiskCategory.FILE_OPERATION,
                description="File deletion operation",
                severity=0.7,
                mitigation="Create backup before deletion",
                details={"file_path": file_path},
            ))

        # Check for modification of system files
        if file_path:
            path_str = str(file_path)
            if any(p in path_str for p in ['/etc/', '/usr/', '/bin/', '/sbin/', '/lib/']):
                factors.append(RiskFactor(
                    category=RiskCategory.FILE_OPERATION,
                    description="Modification of system file",
                    severity=0.9,
                    mitigation="Ensure proper permissions and create backup",
                    details={"file_path": path_str},
                ))

        # Check if file exists (for modifications)
        if operation in ['modify', 'update', 'edit'] and file_path:
            if not Path(file_path).exists():
                factors.append(RiskFactor(
                    category=RiskCategory.FILE_OPERATION,
                    description="Target file does not exist",
                    severity=0.6,
                    mitigation="Verify file path or create file first",
                    details={"file_path": str(file_path)},
                ))

        return factors

    def _analyze_command_execution(
        self,
        unit: Any,
        context: Dict[str, Any],
    ) -> List[RiskFactor]:
        """Analyze command execution risks."""
        factors = []

        command = getattr(unit, 'command', None) or getattr(unit, 'script', '')
        content = getattr(unit, 'content', '') or getattr(unit, 'description', '')

        combined = f"{command} {content}".lower()

        # Check for high-risk patterns
        for pattern, description in self._high_risk_patterns.items():
            if pattern.lower() in combined:
                factors.append(RiskFactor(
                    category=RiskCategory.COMMAND_EXECUTION,
                    description=f"High-risk pattern: {pattern}",
                    severity=0.9,
                    mitigation=f"Review carefully: {description}",
                    details={"pattern": pattern},
                ))

        # Check for resource-intensive operations
        for pattern, description in self._resource_patterns.items():
            if pattern.lower() in combined:
                factors.append(RiskFactor(
                    category=RiskCategory.RESOURCE,
                    description=f"Resource-intensive: {pattern}",
                    severity=0.5,
                    mitigation=description,
                    details={"pattern": pattern},
                ))

        # Check for piped commands (complex)
        if '|' in combined or '&&' in combined or '||' in combined:
            factors.append(RiskFactor(
                category=RiskCategory.COMPLEXITY,
                description="Complex command chain",
                severity=0.4,
                mitigation="Consider breaking into separate units",
            ))

        return factors

    def _analyze_dependencies(
        self,
        unit: Any,
        context: Dict[str, Any],
    ) -> List[RiskFactor]:
        """Analyze dependency risks."""
        factors = []

        dependencies = getattr(unit, 'dependencies', []) or []
        requires = getattr(unit, 'requires', []) or []
        all_deps = list(dependencies) + list(requires)

        if not all_deps:
            return factors

        # Check for missing dependencies
        context_completed = context.get('completed_units', set())

        for dep in all_deps:
            dep_id = dep if isinstance(dep, str) else getattr(dep, 'id', str(dep))
            if dep_id not in context_completed:
                factors.append(RiskFactor(
                    category=RiskCategory.DEPENDENCY,
                    description=f"Depends on incomplete unit: {dep_id}",
                    severity=0.8,
                    mitigation="Ensure dependency completes before this unit",
                    details={"dependency": dep_id},
                ))

        # Check for circular dependencies (would need full graph)
        if len(all_deps) > 3:
            factors.append(RiskFactor(
                category=RiskCategory.COMPLEXITY,
                description=f"Many dependencies ({len(all_deps)})",
                severity=0.3,
                mitigation="Review dependency chain for potential issues",
            ))

        return factors

    def _analyze_resources(
        self,
        unit: Any,
        context: Dict[str, Any],
    ) -> List[RiskFactor]:
        """Analyze resource-related risks."""
        factors = []

        content = str(getattr(unit, 'content', '')) + str(getattr(unit, 'description', ''))
        content_lower = content.lower()

        # Memory-intensive operations
        if any(kw in content_lower for kw in ['large file', 'bulk', 'batch', 'all records']):
            factors.append(RiskFactor(
                category=RiskCategory.RESOURCE,
                description="Potentially memory-intensive operation",
                severity=0.5,
                mitigation="Consider processing in chunks",
            ))

        # Long-running operations
        if any(kw in content_lower for kw in ['migrate', 'backup', 'restore', 'rebuild']):
            factors.append(RiskFactor(
                category=RiskCategory.RESOURCE,
                description="Potentially long-running operation",
                severity=0.4,
                mitigation="Set appropriate timeout and monitor progress",
            ))

        return factors

    def _analyze_network(
        self,
        unit: Any,
        context: Dict[str, Any],
    ) -> List[RiskFactor]:
        """Analyze network-related risks."""
        factors = []

        content = str(getattr(unit, 'content', '')) + str(getattr(unit, 'description', ''))
        content_lower = content.lower()

        # Network operations
        network_keywords = ['api', 'http', 'curl', 'wget', 'fetch', 'download', 'upload']
        if any(kw in content_lower for kw in network_keywords):
            factors.append(RiskFactor(
                category=RiskCategory.NETWORK,
                description="Network operation may fail due to connectivity",
                severity=0.5,
                mitigation="Implement retry logic and timeout handling",
            ))

        # External service dependencies
        if any(kw in content_lower for kw in ['external', 'third-party', 'remote']):
            factors.append(RiskFactor(
                category=RiskCategory.NETWORK,
                description="Depends on external service",
                severity=0.6,
                mitigation="Have fallback or graceful degradation",
            ))

        return factors

    def _analyze_permissions(
        self,
        unit: Any,
        context: Dict[str, Any],
    ) -> List[RiskFactor]:
        """Analyze permission-related risks."""
        factors = []

        file_path = getattr(unit, 'file_path', None) or getattr(unit, 'target_file', '')
        command = str(getattr(unit, 'command', ''))
        content = str(getattr(unit, 'content', ''))

        combined = f"{command} {content}".lower()

        # Elevated privileges
        if 'sudo' in combined or 'root' in combined:
            factors.append(RiskFactor(
                category=RiskCategory.PERMISSIONS,
                description="Requires elevated privileges",
                severity=0.7,
                mitigation="Verify operation is necessary and safe",
            ))

        # Permission changes
        if 'chmod' in combined or 'chown' in combined:
            factors.append(RiskFactor(
                category=RiskCategory.PERMISSIONS,
                description="Changes file permissions",
                severity=0.6,
                mitigation="Document original permissions for rollback",
            ))

        # Check if current user has access
        if file_path:
            path = Path(file_path)
            if path.exists():
                # Check write permission
                if not path.parent.exists():
                    factors.append(RiskFactor(
                        category=RiskCategory.PERMISSIONS,
                        description="Parent directory does not exist",
                        severity=0.5,
                        mitigation="Create parent directories first",
                    ))

        return factors

    def _analyze_complexity(
        self,
        unit: Any,
        context: Dict[str, Any],
    ) -> List[RiskFactor]:
        """Analyze complexity-related risks."""
        factors = []

        content = str(getattr(unit, 'content', '')) + str(getattr(unit, 'description', ''))
        acceptance_criteria = getattr(unit, 'acceptance_criteria', []) or []

        # Large content
        if len(content) > 5000:
            factors.append(RiskFactor(
                category=RiskCategory.COMPLEXITY,
                description="Large unit content",
                severity=0.4,
                mitigation="Consider splitting into smaller units",
            ))

        # Many acceptance criteria
        if len(acceptance_criteria) > 5:
            factors.append(RiskFactor(
                category=RiskCategory.COMPLEXITY,
                description=f"Many acceptance criteria ({len(acceptance_criteria)})",
                severity=0.3,
                mitigation="Ensure all criteria are testable",
            ))

        return factors

    def _analyze_history(
        self,
        unit: Any,
        context: Dict[str, Any],
    ) -> List[RiskFactor]:
        """Analyze historical failure data."""
        factors = []

        if not self.failure_learner:
            return factors

        # Get similar failures
        unit_type = getattr(unit, 'type', None) or getattr(unit, 'unit_type', '')
        operation = getattr(unit, 'operation', '')
        file_path = getattr(unit, 'file_path', '')

        # Search for similar past failures
        all_failures = self.failure_learner.list_failures(limit=100)
        similar_count = 0

        for failure in all_failures:
            match = False

            if unit_type and failure.unit_type == unit_type:
                match = True
            if operation and failure.operation == operation:
                match = True
            if file_path and failure.file_path and Path(file_path).suffix == Path(failure.file_path).suffix:
                match = True

            if match:
                similar_count += 1

        if similar_count > 0:
            severity = min(0.9, 0.3 + (similar_count * 0.1))
            factors.append(RiskFactor(
                category=RiskCategory.HISTORY,
                description=f"Similar operations failed {similar_count} times before",
                severity=severity,
                mitigation="Review past failures for common issues",
                details={"similar_failure_count": similar_count},
            ))

        return factors

    def _get_similar_failure_count(self, unit: Any) -> int:
        """Get count of similar historical failures."""
        if not self.failure_learner:
            return 0

        unit_type = getattr(unit, 'type', None) or getattr(unit, 'unit_type', '')
        operation = getattr(unit, 'operation', '')

        all_failures = self.failure_learner.list_failures(limit=100)
        count = 0

        for failure in all_failures:
            if (unit_type and failure.unit_type == unit_type) or \
               (operation and failure.operation == operation):
                count += 1

        return count

    def _calculate_probability(self, risk_factors: List[RiskFactor]) -> float:
        """Calculate failure probability from risk factors."""
        if not risk_factors:
            return 0.1  # Base probability

        # Weighted sum of severities
        total_weight = 0.0
        weighted_sum = 0.0

        for factor in risk_factors:
            weight = self.risk_weights.get(factor.category, 0.5)
            weighted_sum += factor.severity * weight
            total_weight += weight

        if total_weight == 0:
            return 0.1

        # Normalize to 0-1 range
        raw_probability = weighted_sum / total_weight

        # Apply diminishing returns for many risk factors
        factor_bonus = min(0.3, len(risk_factors) * 0.05)

        return min(0.95, raw_probability + factor_bonus)

    def _determine_risk_level(
        self,
        probability: float,
        risk_factors: List[RiskFactor],
    ) -> RiskLevel:
        """Determine overall risk level."""
        # Check for any critical factors
        has_critical = any(f.severity >= 0.9 for f in risk_factors)

        if has_critical or probability >= 0.7:
            return RiskLevel.CRITICAL
        elif probability >= 0.5:
            return RiskLevel.HIGH
        elif probability >= 0.3:
            return RiskLevel.MEDIUM
        else:
            return RiskLevel.LOW

    def _calculate_confidence(
        self,
        risk_factors: List[RiskFactor],
        similar_count: int,
    ) -> float:
        """Calculate confidence in the prediction."""
        # More data = higher confidence
        base_confidence = 0.5

        # Historical data increases confidence
        if similar_count > 0:
            base_confidence += min(0.3, similar_count * 0.05)

        # More risk factors analyzed increases confidence
        base_confidence += min(0.2, len(risk_factors) * 0.03)

        return min(0.95, base_confidence)

    def _extract_units(self, plan: Any) -> List[Any]:
        """Extract units from a plan object."""
        # Try different attributes
        if hasattr(plan, 'units'):
            return list(plan.units)
        if hasattr(plan, 'atomic_units'):
            return list(plan.atomic_units)
        if hasattr(plan, 'steps'):
            return list(plan.steps)
        if hasattr(plan, 'phases'):
            units = []
            for phase in plan.phases:
                if hasattr(phase, 'units'):
                    units.extend(phase.units)
                elif hasattr(phase, 'steps'):
                    units.extend(phase.steps)
            return units

        return []

    def _identify_critical_path(
        self,
        units: List[Any],
        predictions: List[FailurePrediction],
    ) -> List[str]:
        """Identify units on the critical path."""
        critical = []

        # Units with high risk that others depend on
        prediction_map = {p.unit_id: p for p in predictions}

        for unit in units:
            unit_id = getattr(unit, 'id', None) or getattr(unit, 'unit_id', str(id(unit)))

            # Check if this unit is a dependency for others
            is_dependency = False
            for other_unit in units:
                deps = getattr(other_unit, 'dependencies', []) or []
                requires = getattr(other_unit, 'requires', []) or []

                for dep in list(deps) + list(requires):
                    dep_id = dep if isinstance(dep, str) else getattr(dep, 'id', str(dep))
                    if dep_id == unit_id:
                        is_dependency = True
                        break

            # High risk and is a dependency = critical
            if is_dependency and unit_id in prediction_map:
                pred = prediction_map[unit_id]
                if pred.risk_level in (RiskLevel.HIGH, RiskLevel.CRITICAL):
                    critical.append(unit_id)

        return critical

    def _recommend_checkpoints(
        self,
        predictions: List[FailurePrediction],
    ) -> List[str]:
        """Recommend units that should have checkpoints."""
        checkpoints = []

        for pred in predictions:
            if pred.should_checkpoint:
                checkpoints.append(pred.unit_id)

        return checkpoints

    def _calculate_overall_risk(
        self,
        predictions: List[FailurePrediction],
    ) -> RiskLevel:
        """Calculate overall plan risk level."""
        if not predictions:
            return RiskLevel.LOW

        # Any critical = overall critical
        if any(p.risk_level == RiskLevel.CRITICAL for p in predictions):
            return RiskLevel.CRITICAL

        # Many high risk = overall high
        high_risk_count = sum(1 for p in predictions if p.risk_level == RiskLevel.HIGH)
        if high_risk_count >= 2 or high_risk_count / len(predictions) > 0.3:
            return RiskLevel.HIGH

        # Average probability
        avg_probability = sum(p.failure_probability for p in predictions) / len(predictions)

        if avg_probability >= 0.5:
            return RiskLevel.HIGH
        elif avg_probability >= 0.3:
            return RiskLevel.MEDIUM
        else:
            return RiskLevel.LOW

    def _estimate_success_rate(
        self,
        predictions: List[FailurePrediction],
    ) -> float:
        """Estimate overall success rate."""
        if not predictions:
            return 1.0

        # Product of individual success probabilities
        success_rate = 1.0
        for pred in predictions:
            success_rate *= (1.0 - pred.failure_probability)

        return success_rate
