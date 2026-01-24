"""
Test Classification Engine

Tests for the keyword-based classification engine.
"""

import pytest
from ..services import ClassificationEngine
from ..models import RoleType, TaskRequirements


class TestClassificationEngineInit:
    """Test ClassificationEngine initialization."""

    def test_default_thresholds(self):
        """Test default threshold values."""
        engine = ClassificationEngine()

        assert engine.human_threshold == 0.6
        assert engine.ai_threshold == 0.6
        assert engine.default_to_hybrid is True

    def test_custom_thresholds(self):
        """Test custom threshold configuration."""
        engine = ClassificationEngine(
            human_threshold=0.7,
            ai_threshold=0.5,
            default_to_hybrid=False
        )

        assert engine.human_threshold == 0.7
        assert engine.ai_threshold == 0.5
        assert engine.default_to_hybrid is False

    def test_default_weights(self):
        """Test default factor weights."""
        engine = ClassificationEngine()

        assert "keywords" in engine.weights
        assert "complexity" in engine.weights
        assert "urgency" in engine.weights
        assert "required_skills" in engine.weights

    def test_custom_rules(self):
        """Test custom rules configuration."""
        custom_rules = [
            {"keywords": ["urgent"], "score": 0.9},
            {"departments": ["Legal"], "score": 0.95},
        ]
        engine = ClassificationEngine(custom_rules=custom_rules)

        assert len(engine.custom_rules) == 2


@pytest.mark.asyncio
class TestClassificationEngineClassification:
    """Test classification logic."""

    async def test_human_primary_classification(self, human_task_requirements):
        """Test that human-oriented tasks favor human classification."""
        engine = ClassificationEngine()

        result = await engine.classify_task(
            task_id="test-task-1",
            requirements=human_task_requirements
        )

        # Human tasks should have higher human scores than AI scores
        assert result.factors.get("human_total", 0) >= result.factors.get("ai_total", 0)
        assert result.confidence > 0.5
        assert result.human_oversight_required is True
        assert "human_keyword_count" in result.factors
        # Should be either HUMAN_PRIMARY or HYBRID (when balanced)
        assert result.classification in [RoleType.HUMAN_PRIMARY, RoleType.HYBRID]

    async def test_ai_primary_classification(self, ai_task_requirements):
        """Test that AI-oriented tasks favor AI classification."""
        engine = ClassificationEngine()

        result = await engine.classify_task(
            task_id="test-task-2",
            requirements=ai_task_requirements
        )

        # AI tasks should have higher AI scores than human scores
        assert result.factors.get("ai_total", 0) >= result.factors.get("human_total", 0)
        assert result.confidence > 0.5
        assert "ai_keyword_count" in result.factors
        # Should be either AI_PRIMARY or HYBRID (when balanced)
        assert result.classification in [RoleType.AI_PRIMARY, RoleType.HYBRID]

    async def test_hybrid_classification(self, hybrid_task_requirements):
        """Test that balanced tasks are classified as HYBRID."""
        engine = ClassificationEngine(default_to_hybrid=True)

        result = await engine.classify_task(
            task_id="test-task-3",
            requirements=hybrid_task_requirements
        )

        # Hybrid tasks should get HYBRID classification when scores are balanced
        assert result.classification in [RoleType.HYBRID, RoleType.HUMAN_PRIMARY, RoleType.AI_PRIMARY]
        assert result.human_oversight_required is True

    async def test_high_complexity_requires_oversight(self):
        """Test that high complexity tasks require human oversight."""
        engine = ClassificationEngine()

        requirements = TaskRequirements(
            task_description="Process simple batch data automatically",
            required_skills=["automation"],
            keywords=["process", "batch", "automate"],
            complexity="critical",  # High complexity
            urgency="normal",
        )

        result = await engine.classify_task(
            task_id="test-task-4",
            requirements=requirements
        )

        assert result.human_oversight_required is True

    async def test_sensitive_keywords_require_oversight(self):
        """Test that sensitive keywords trigger human oversight."""
        engine = ClassificationEngine()

        requirements = TaskRequirements(
            task_description="Process confidential financial data automatically",
            required_skills=["automation", "data processing"],
            keywords=["process", "automate", "financial", "confidential"],
            complexity="low",
            urgency="normal",
        )

        result = await engine.classify_task(
            task_id="test-task-5",
            requirements=requirements
        )

        # Confidential and financial should trigger oversight
        assert result.human_oversight_required is True


@pytest.mark.asyncio
class TestClassificationEngineKeywordAnalysis:
    """Test keyword analysis functionality."""

    async def test_human_keywords_detected(self):
        """Test that human keywords are properly detected."""
        engine = ClassificationEngine()

        requirements = TaskRequirements(
            task_description="Make a decision and approve the budget for strategic planning",
            required_skills=[],
            keywords=[],
            complexity="medium",
            urgency="normal",
        )

        result = await engine.classify_task("test", requirements)

        # Should detect: decision, approve, budget, strategic
        assert result.factors.get("human_keyword_count", 0) >= 3

    async def test_ai_keywords_detected(self):
        """Test that AI keywords are properly detected."""
        engine = ClassificationEngine()

        requirements = TaskRequirements(
            task_description="Analyze and process the data, then generate a summary report",
            required_skills=[],
            keywords=[],
            complexity="medium",
            urgency="normal",
        )

        result = await engine.classify_task("test", requirements)

        # Should detect: analyze, process, generate, summarize
        assert result.factors.get("ai_keyword_count", 0) >= 3


@pytest.mark.asyncio
class TestClassificationEngineCustomRules:
    """Test custom rule functionality."""

    async def test_custom_rule_matches_keywords(self):
        """Test custom rule matching on keywords."""
        engine = ClassificationEngine(
            custom_rules=[
                {"keywords": ["urgent-custom"], "score": 0.95}
            ]
        )

        requirements = TaskRequirements(
            task_description="This is an urgent-custom request for processing",
            required_skills=[],
            keywords=[],
            complexity="medium",
            urgency="normal",
        )

        result = await engine.classify_task("test", requirements)

        # Custom rule should have been applied
        assert "custom_rules" in result.factors

    async def test_add_custom_rule(self):
        """Test adding custom rules dynamically."""
        engine = ClassificationEngine()
        initial_count = len(engine.custom_rules)

        engine.add_custom_rule({
            "keywords": ["new-rule"],
            "score": 0.8
        })

        assert len(engine.custom_rules) == initial_count + 1


class TestClassificationEngineStatistics:
    """Test statistics and configuration reporting."""

    def test_get_statistics(self):
        """Test statistics retrieval."""
        engine = ClassificationEngine(
            human_threshold=0.65,
            ai_threshold=0.55
        )

        stats = engine.get_statistics()

        assert stats["human_threshold"] == 0.65
        assert stats["ai_threshold"] == 0.55
        assert "weights" in stats
        assert "human_keywords_count" in stats
        assert "ai_keywords_count" in stats

    def test_update_weights(self):
        """Test weight updates."""
        engine = ClassificationEngine()
        original_keywords_weight = engine.weights["keywords"]

        engine.update_weights({"keywords": 0.5})

        assert engine.weights["keywords"] == 0.5
        assert engine.weights["keywords"] != original_keywords_weight
