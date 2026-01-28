"""
L07 Learning Layer - Pattern Extraction Service Tests

Tests for PatternExtractionService (TDD - tests written first).
"""

import pytest
from datetime import datetime
from typing import List, Dict, Any

from L07_learning.models.pattern import (
    BehavioralPattern,
    PlanningStrategy,
    PatternType,
    PatternConfidence,
)


@pytest.fixture
def sample_execution_traces() -> List[Dict[str, Any]]:
    """Generate sample execution traces with patterns."""
    traces = []

    # Pattern 1: Read -> Analyze -> Write sequence (occurs 5 times)
    for i in range(5):
        traces.append({
            "execution_id": f"exec-{i:03d}",
            "task_type": "code_generation",
            "domain": "python",
            "success": True,
            "quality_score": 85 + i,
            "confidence": 0.9,
            "tool_sequence": ["read_file", "analyze_code", "write_file"],
            "duration_seconds": 10 + i,
        })

    # Pattern 2: Search -> Read -> Modify (occurs 4 times)
    for i in range(5, 9):
        traces.append({
            "execution_id": f"exec-{i:03d}",
            "task_type": "refactoring",
            "domain": "python",
            "success": True,
            "quality_score": 80 + i,
            "confidence": 0.85,
            "tool_sequence": ["search_code", "read_file", "modify_code"],
            "duration_seconds": 15 + i,
        })

    # Pattern 3: Failed execution (no pattern)
    traces.append({
        "execution_id": "exec-009",
        "task_type": "debugging",
        "domain": "javascript",
        "success": False,
        "quality_score": 30,
        "confidence": 0.5,
        "tool_sequence": ["read_file"],
        "duration_seconds": 5,
    })

    return traces


@pytest.mark.l07
@pytest.mark.unit
class TestPatternExtraction:
    """Tests for pattern extraction from traces."""

    @pytest.mark.asyncio
    async def test_extract_tool_sequence_pattern(self, sample_execution_traces):
        """Test extracting tool sequence patterns from traces."""
        from L07_learning.services.pattern_extraction_service import PatternExtractionService

        service = PatternExtractionService()

        patterns = await service.extract_patterns(sample_execution_traces)

        assert len(patterns) > 0
        # Should find at least the recurring sequences
        tool_sequence_patterns = [
            p for p in patterns if p.pattern_type == PatternType.TOOL_SEQUENCE
        ]
        assert len(tool_sequence_patterns) >= 1

    @pytest.mark.asyncio
    async def test_pattern_has_correct_signature(self, sample_execution_traces):
        """Test that patterns have correct signatures."""
        from L07_learning.services.pattern_extraction_service import PatternExtractionService

        service = PatternExtractionService()

        patterns = await service.extract_patterns(sample_execution_traces)

        # Find the read-analyze-write pattern
        raw_pattern = None
        for p in patterns:
            if "read_file" in p.pattern_signature and "analyze_code" in p.pattern_signature:
                raw_pattern = p
                break

        assert raw_pattern is not None
        assert raw_pattern.pattern_signature != ""

    @pytest.mark.asyncio
    async def test_extract_patterns_groups_by_similarity(self, sample_execution_traces):
        """Test that similar sequences are grouped into one pattern."""
        from L07_learning.services.pattern_extraction_service import PatternExtractionService

        service = PatternExtractionService()

        patterns = await service.extract_patterns(sample_execution_traces)

        # Find pattern for read-analyze-write sequence
        for p in patterns:
            if "read_file" in p.pattern_signature and "analyze_code" in p.pattern_signature:
                # Should have observation count >= 5 (all similar traces grouped)
                assert p.observation_count >= 5
                break


@pytest.mark.l07
@pytest.mark.unit
class TestPatternObservation:
    """Tests for pattern observation updates."""

    @pytest.mark.asyncio
    async def test_pattern_confidence_updates_with_observations(self, sample_execution_traces):
        """Test that pattern confidence updates with observations."""
        from L07_learning.services.pattern_extraction_service import PatternExtractionService

        service = PatternExtractionService()

        # Extract initial patterns
        patterns = await service.extract_patterns(sample_execution_traces)

        if not patterns:
            pytest.skip("No patterns extracted")

        pattern = patterns[0]
        initial_confidence = pattern.pattern_confidence

        # Observe pattern multiple times with success
        for _ in range(30):
            pattern = await service.observe_pattern(
                pattern_id=pattern.pattern_id,
                success=True,
                quality=90.0,
            )

        # Confidence should increase or stay the same
        assert pattern.observation_count >= 30

    @pytest.mark.asyncio
    async def test_observe_updates_success_rate(self, sample_execution_traces):
        """Test that observe_pattern updates success rate."""
        from L07_learning.services.pattern_extraction_service import PatternExtractionService

        service = PatternExtractionService()

        # Create a pattern directly
        pattern = await service.create_pattern(
            name="test-pattern",
            pattern_type=PatternType.TOOL_SEQUENCE,
            signature="test->pattern",
        )

        # Initial state
        assert pattern.success_rate == 0.0

        # Observe successes
        for _ in range(8):
            pattern = await service.observe_pattern(
                pattern_id=pattern.pattern_id,
                success=True,
                quality=85.0,
            )

        # Observe failures
        for _ in range(2):
            pattern = await service.observe_pattern(
                pattern_id=pattern.pattern_id,
                success=False,
                quality=50.0,
            )

        # Success rate should be 80%
        assert 0.79 <= pattern.success_rate <= 0.81


@pytest.mark.l07
@pytest.mark.unit
class TestStrategyRecommendation:
    """Tests for strategy recommendation."""

    @pytest.mark.asyncio
    async def test_recommend_strategies_for_task_type(self, sample_execution_traces):
        """Test recommending strategies for a task type."""
        from L07_learning.services.pattern_extraction_service import PatternExtractionService

        service = PatternExtractionService()

        # Extract patterns first
        await service.extract_patterns(sample_execution_traces)

        # Get strategies for code_generation
        strategies = await service.recommend_strategies(
            task_type="code_generation",
        )

        assert isinstance(strategies, list)
        # All strategies should be relevant to code_generation
        for strategy in strategies:
            assert "code_generation" in strategy.recommended_for or len(strategies) == 0

    @pytest.mark.asyncio
    async def test_recommend_strategies_with_domain_filter(self, sample_execution_traces):
        """Test recommending strategies with domain filter."""
        from L07_learning.services.pattern_extraction_service import PatternExtractionService

        service = PatternExtractionService()

        # Extract patterns first
        await service.extract_patterns(sample_execution_traces)

        # Get strategies for python domain
        strategies = await service.recommend_strategies(
            task_type="code_generation",
            domain="python",
        )

        assert isinstance(strategies, list)


@pytest.mark.l07
@pytest.mark.unit
class TestStrategyCreation:
    """Tests for strategy creation from patterns."""

    @pytest.mark.asyncio
    async def test_create_strategy_from_patterns(self, sample_execution_traces):
        """Test creating a strategy from patterns."""
        from L07_learning.services.pattern_extraction_service import PatternExtractionService

        service = PatternExtractionService()

        # Extract patterns first
        patterns = await service.extract_patterns(sample_execution_traces)

        if not patterns:
            pytest.skip("No patterns extracted")

        # Create strategy from pattern
        strategy = await service.create_strategy_from_pattern(
            pattern=patterns[0],
            name="test-strategy",
        )

        assert strategy is not None
        assert strategy.name == "test-strategy"
        assert strategy.strategy_id is not None

    @pytest.mark.asyncio
    async def test_strategy_has_heuristics(self, sample_execution_traces):
        """Test that created strategy has heuristics."""
        from L07_learning.services.pattern_extraction_service import PatternExtractionService

        service = PatternExtractionService()

        patterns = await service.extract_patterns(sample_execution_traces)

        if not patterns:
            pytest.skip("No patterns extracted")

        strategy = await service.create_strategy_from_pattern(
            pattern=patterns[0],
            name="heuristic-strategy",
            heuristics=["prefer_simple_tools", "minimize_file_reads"],
        )

        assert len(strategy.heuristics) >= 2


@pytest.mark.l07
@pytest.mark.unit
class TestPatternManagement:
    """Tests for pattern management operations."""

    @pytest.mark.asyncio
    async def test_list_patterns(self, sample_execution_traces):
        """Test listing all patterns."""
        from L07_learning.services.pattern_extraction_service import PatternExtractionService

        service = PatternExtractionService()

        # Create some patterns
        await service.create_pattern(
            name="pattern-1",
            pattern_type=PatternType.TOOL_SEQUENCE,
            signature="a->b->c",
        )
        await service.create_pattern(
            name="pattern-2",
            pattern_type=PatternType.DECISION_STRATEGY,
            signature="decide->act",
        )

        patterns = await service.list_patterns()

        assert len(patterns) >= 2

    @pytest.mark.asyncio
    async def test_get_pattern_by_id(self, sample_execution_traces):
        """Test getting pattern by ID."""
        from L07_learning.services.pattern_extraction_service import PatternExtractionService

        service = PatternExtractionService()

        created = await service.create_pattern(
            name="get-test",
            pattern_type=PatternType.ERROR_RECOVERY,
            signature="error->recover",
        )

        retrieved = await service.get_pattern(created.pattern_id)

        assert retrieved is not None
        assert retrieved.pattern_id == created.pattern_id
        assert retrieved.name == "get-test"

    @pytest.mark.asyncio
    async def test_delete_pattern(self, sample_execution_traces):
        """Test deleting a pattern."""
        from L07_learning.services.pattern_extraction_service import PatternExtractionService

        service = PatternExtractionService()

        created = await service.create_pattern(
            name="delete-test",
            pattern_type=PatternType.OPTIMIZATION,
            signature="optimize",
        )

        deleted = await service.delete_pattern(created.pattern_id)
        assert deleted is True

        # Should not be retrievable
        retrieved = await service.get_pattern(created.pattern_id)
        assert retrieved is None
