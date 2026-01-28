"""
L07 Learning Layer - Pattern Extraction Service

Service for extracting behavioral patterns from execution traces
and recommending strategies based on observed patterns.
"""

import logging
from datetime import datetime
from typing import List, Optional, Dict, Any
from collections import defaultdict
import uuid
import hashlib

from ..models.pattern import (
    BehavioralPattern,
    PlanningStrategy,
    PatternType,
    PatternConfidence,
)


logger = logging.getLogger(__name__)


class PatternExtractionService:
    """
    Service for extracting and managing behavioral patterns.

    Analyzes execution traces to identify recurring decision-making
    patterns that can be used to improve future executions.
    """

    def __init__(
        self,
        min_observations: int = 2,
        similarity_threshold: float = 0.8,
    ):
        """
        Initialize PatternExtractionService.

        Args:
            min_observations: Minimum observations to consider a pattern
            similarity_threshold: Threshold for grouping similar sequences
        """
        self.min_observations = min_observations
        self.similarity_threshold = similarity_threshold
        self._patterns: Dict[str, BehavioralPattern] = {}
        self._strategies: Dict[str, PlanningStrategy] = {}

        logger.info(
            f"Initialized PatternExtractionService "
            f"(min_obs={min_observations}, similarity={similarity_threshold})"
        )

    def _compute_signature(self, tool_sequence: List[str]) -> str:
        """
        Compute a unique signature for a tool sequence.

        Args:
            tool_sequence: List of tool names

        Returns:
            Signature string
        """
        if not tool_sequence:
            return ""
        return "->".join(tool_sequence)

    def _signature_hash(self, signature: str) -> str:
        """Create a short hash of a signature for ID purposes."""
        return hashlib.md5(signature.encode()).hexdigest()[:8]

    async def extract_patterns(
        self,
        traces: List[Dict[str, Any]],
    ) -> List[BehavioralPattern]:
        """
        Extract behavioral patterns from execution traces.

        Args:
            traces: List of execution trace dictionaries

        Returns:
            List of extracted patterns
        """
        logger.info(f"Extracting patterns from {len(traces)} traces")

        # Group traces by tool sequence
        sequence_groups: Dict[str, List[Dict]] = defaultdict(list)

        for trace in traces:
            tool_sequence = trace.get("tool_sequence", [])
            if not tool_sequence:
                continue

            signature = self._compute_signature(tool_sequence)
            sequence_groups[signature].append(trace)

        # Create patterns from groups that meet minimum observations
        extracted = []
        for signature, group_traces in sequence_groups.items():
            if len(group_traces) < self.min_observations:
                continue

            # Check if pattern already exists
            existing = self._find_pattern_by_signature(signature)
            if existing:
                # Update existing pattern
                for trace in group_traces:
                    existing.update_statistics(
                        success=trace.get("success", False),
                        quality_score=trace.get("quality_score", 0.0),
                        confidence=trace.get("confidence", 0.0),
                    )
                    if trace.get("execution_id"):
                        if trace["execution_id"] not in existing.example_execution_ids:
                            existing.example_execution_ids.append(trace["execution_id"])
                extracted.append(existing)
            else:
                # Create new pattern
                pattern = await self._create_pattern_from_traces(signature, group_traces)
                self._patterns[pattern.pattern_id] = pattern
                extracted.append(pattern)

        logger.info(f"Extracted {len(extracted)} patterns")
        return extracted

    async def _create_pattern_from_traces(
        self,
        signature: str,
        traces: List[Dict[str, Any]],
    ) -> BehavioralPattern:
        """
        Create a pattern from a group of similar traces.

        Args:
            signature: Tool sequence signature
            traces: List of traces with this signature

        Returns:
            Created pattern
        """
        # Determine pattern type from first trace
        first_trace = traces[0]
        pattern_type = PatternType.TOOL_SEQUENCE

        # Collect domains and task types
        domains = list(set(t.get("domain", "general") for t in traces))
        task_types = list(set(t.get("task_type", "unknown") for t in traces))

        # Calculate aggregate statistics
        successes = sum(1 for t in traces if t.get("success", False))
        total = len(traces)
        success_rate = successes / total if total > 0 else 0.0

        avg_quality = sum(t.get("quality_score", 0.0) for t in traces) / total if total > 0 else 0.0
        avg_confidence = sum(t.get("confidence", 0.0) for t in traces) / total if total > 0 else 0.0

        # Determine confidence level
        if total >= 100 and success_rate >= 0.9:
            confidence_level = PatternConfidence.VERY_HIGH
        elif total >= 50 and success_rate >= 0.8:
            confidence_level = PatternConfidence.HIGH
        elif total >= 20 and success_rate >= 0.7:
            confidence_level = PatternConfidence.MEDIUM
        else:
            confidence_level = PatternConfidence.LOW

        pattern = BehavioralPattern(
            pattern_id=str(uuid.uuid4()),
            name=f"Pattern: {signature[:50]}",
            description=f"Tool sequence pattern observed {total} times",
            pattern_type=pattern_type,
            pattern_signature=signature,
            pattern_template={"sequence": signature.split("->")},
            observation_count=total,
            success_count=successes,
            failure_count=total - successes,
            success_rate=success_rate,
            average_quality_score=avg_quality,
            average_confidence=avg_confidence,
            pattern_confidence=confidence_level,
            domains=domains,
            task_types=task_types,
            example_execution_ids=[t.get("execution_id") for t in traces if t.get("execution_id")],
        )

        return pattern

    def _find_pattern_by_signature(self, signature: str) -> Optional[BehavioralPattern]:
        """Find an existing pattern by signature."""
        for pattern in self._patterns.values():
            if pattern.pattern_signature == signature:
                return pattern
        return None

    async def create_pattern(
        self,
        name: str,
        pattern_type: PatternType,
        signature: str,
        description: str = "",
        domains: Optional[List[str]] = None,
        task_types: Optional[List[str]] = None,
    ) -> BehavioralPattern:
        """
        Create a new pattern manually.

        Args:
            name: Pattern name
            pattern_type: Type of pattern
            signature: Pattern signature
            description: Optional description
            domains: Optional list of domains
            task_types: Optional list of task types

        Returns:
            Created pattern
        """
        pattern = BehavioralPattern(
            pattern_id=str(uuid.uuid4()),
            name=name,
            description=description,
            pattern_type=pattern_type,
            pattern_signature=signature,
            pattern_template={"sequence": signature.split("->")},
            domains=domains or [],
            task_types=task_types or [],
        )

        self._patterns[pattern.pattern_id] = pattern
        logger.info(f"Created pattern {pattern.pattern_id}: {name}")

        return pattern

    async def observe_pattern(
        self,
        pattern_id: str,
        success: bool,
        quality: float,
        confidence: float = 0.8,
        execution_id: Optional[str] = None,
    ) -> BehavioralPattern:
        """
        Record an observation of a pattern.

        Args:
            pattern_id: Pattern identifier
            success: Whether the observation was successful
            quality: Quality score of the execution
            confidence: Confidence in the quality score
            execution_id: Optional execution ID to track

        Returns:
            Updated pattern
        """
        pattern = self._patterns.get(pattern_id)
        if not pattern:
            raise ValueError(f"Pattern {pattern_id} not found")

        pattern.update_statistics(
            success=success,
            quality_score=quality,
            confidence=confidence,
        )

        if execution_id and execution_id not in pattern.example_execution_ids:
            pattern.example_execution_ids.append(execution_id)

        return pattern

    async def recommend_strategies(
        self,
        task_type: str,
        domain: Optional[str] = None,
        top_k: int = 5,
    ) -> List[PlanningStrategy]:
        """
        Recommend strategies for a given task type.

        Args:
            task_type: Type of task
            domain: Optional domain filter
            top_k: Maximum number of strategies to return

        Returns:
            List of recommended strategies
        """
        logger.info(f"Recommending strategies for task_type={task_type}, domain={domain}")

        # Filter strategies by task type and domain
        candidates = []
        for strategy in self._strategies.values():
            if task_type in strategy.recommended_for:
                if domain is None or domain in strategy.domains:
                    candidates.append(strategy)

        # If no strategies exist, try to create from patterns
        if not candidates:
            matching_patterns = [
                p for p in self._patterns.values()
                if task_type in p.task_types and (domain is None or domain in p.domains)
            ]

            for pattern in matching_patterns[:top_k]:
                strategy = await self.create_strategy_from_pattern(
                    pattern=pattern,
                    name=f"Strategy from {pattern.name}",
                )
                candidates.append(strategy)

        # Sort by confidence score and success rate
        candidates.sort(
            key=lambda s: (s.confidence_score, s.average_success_rate),
            reverse=True,
        )

        return candidates[:top_k]

    async def create_strategy_from_pattern(
        self,
        pattern: BehavioralPattern,
        name: str,
        description: str = "",
        heuristics: Optional[List[str]] = None,
    ) -> PlanningStrategy:
        """
        Create a planning strategy from a pattern.

        Args:
            pattern: Source pattern
            name: Strategy name
            description: Optional description
            heuristics: Optional list of heuristics

        Returns:
            Created strategy
        """
        # Determine strategy type
        strategy_type = "sequential"
        if pattern.pattern_type == PatternType.DECISION_STRATEGY:
            strategy_type = "adaptive"
        elif pattern.pattern_type == PatternType.OPTIMIZATION:
            strategy_type = "parallel"

        # Build decision tree from pattern template
        decision_tree = {
            "type": strategy_type,
            "steps": pattern.pattern_template.get("sequence", []),
            "conditions": pattern.applicable_conditions,
        }

        strategy = PlanningStrategy(
            strategy_id=str(uuid.uuid4()),
            name=name,
            description=description or f"Strategy derived from pattern: {pattern.name}",
            strategy_type=strategy_type,
            decision_tree=decision_tree,
            heuristics=heuristics or [],
            average_success_rate=pattern.success_rate,
            average_quality_score=pattern.average_quality_score,
            domains=pattern.domains.copy(),
            recommended_for=pattern.task_types.copy(),
            confidence_score=0.5 + (pattern.success_rate * 0.5),  # Scale to 0.5-1.0
        )

        self._strategies[strategy.strategy_id] = strategy
        logger.info(f"Created strategy {strategy.strategy_id} from pattern {pattern.pattern_id}")

        return strategy

    async def list_patterns(
        self,
        pattern_type: Optional[PatternType] = None,
        min_confidence: Optional[PatternConfidence] = None,
    ) -> List[BehavioralPattern]:
        """
        List all patterns with optional filtering.

        Args:
            pattern_type: Filter by pattern type
            min_confidence: Filter by minimum confidence level

        Returns:
            List of patterns
        """
        patterns = list(self._patterns.values())

        if pattern_type:
            patterns = [p for p in patterns if p.pattern_type == pattern_type]

        if min_confidence:
            confidence_order = [
                PatternConfidence.LOW,
                PatternConfidence.MEDIUM,
                PatternConfidence.HIGH,
                PatternConfidence.VERY_HIGH,
            ]
            min_idx = confidence_order.index(min_confidence)
            patterns = [
                p for p in patterns
                if confidence_order.index(p.pattern_confidence) >= min_idx
            ]

        return patterns

    async def get_pattern(self, pattern_id: str) -> Optional[BehavioralPattern]:
        """
        Get a pattern by ID.

        Args:
            pattern_id: Pattern identifier

        Returns:
            Pattern or None if not found
        """
        return self._patterns.get(pattern_id)

    async def delete_pattern(self, pattern_id: str) -> bool:
        """
        Delete a pattern.

        Args:
            pattern_id: Pattern identifier

        Returns:
            True if deleted, False if not found
        """
        if pattern_id in self._patterns:
            del self._patterns[pattern_id]
            logger.info(f"Deleted pattern {pattern_id}")
            return True
        return False

    async def list_strategies(self) -> List[PlanningStrategy]:
        """
        List all strategies.

        Returns:
            List of strategies
        """
        return list(self._strategies.values())

    async def get_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about patterns and strategies.

        Returns:
            Dictionary of statistics
        """
        pattern_types = defaultdict(int)
        confidence_levels = defaultdict(int)

        for pattern in self._patterns.values():
            pattern_types[pattern.pattern_type.value] += 1
            confidence_levels[pattern.pattern_confidence.value] += 1

        return {
            "total_patterns": len(self._patterns),
            "total_strategies": len(self._strategies),
            "pattern_types": dict(pattern_types),
            "confidence_levels": dict(confidence_levels),
            "average_success_rate": (
                sum(p.success_rate for p in self._patterns.values()) / len(self._patterns)
                if self._patterns else 0.0
            ),
        }
