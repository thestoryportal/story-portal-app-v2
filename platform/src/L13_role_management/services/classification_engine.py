"""
Classification Engine for L13 Role Management Layer.

Provides intelligent classification of tasks for human/AI routing decisions.
Determines whether a task should be handled by humans, AI, or collaboratively.
"""

import logging
from typing import Dict, Any, List, Optional, Set
from datetime import datetime
import re

from ..models import (
    RoleType,
    TaskRequirements,
    ClassificationResult,
    RoleMatch,
)

logger = logging.getLogger(__name__)


class ClassificationEngine:
    """
    Engine for classifying tasks into human_primary, hybrid, or ai_primary categories.

    Uses a combination of rule-based heuristics and configurable weights to
    determine the optimal routing for tasks.
    """

    # Keywords strongly suggesting human involvement
    HUMAN_KEYWORDS: Set[str] = {
        # Decision making
        "decision", "decide", "approve", "authorization", "authorize", "sign-off",
        # Sensitive operations
        "sensitive", "confidential", "private", "security", "compliance",
        "legal", "financial", "budget", "salary", "personnel",
        # Strategic work
        "strategy", "strategic", "planning", "vision", "roadmap",
        # Creative/subjective
        "creative", "design", "innovate", "brainstorm", "ideate",
        # Interpersonal
        "negotiate", "interview", "counsel", "mentor", "mediate",
        "facilitate", "present", "pitch", "communicate",
        # Judgment calls
        "evaluate", "assess", "judge", "prioritize", "triage",
        # Ethics and risk
        "ethical", "risk", "impact", "consequence", "controversial",
    }

    # Keywords strongly suggesting AI suitability
    AI_KEYWORDS: Set[str] = {
        # Data processing
        "analyze", "process", "transform", "parse", "extract",
        "aggregate", "calculate", "compute", "statistics",
        # Generation
        "generate", "create", "produce", "synthesize", "draft",
        # Automation
        "automate", "schedule", "batch", "bulk", "repetitive",
        # Classification
        "classify", "categorize", "tag", "label", "sort",
        # Summarization
        "summarize", "condense", "distill", "abstract", "outline",
        # Search and retrieval
        "search", "find", "locate", "query", "retrieve", "lookup",
        # Monitoring
        "monitor", "track", "observe", "alert", "detect", "scan",
        # Formatting
        "format", "convert", "translate", "reformat", "standardize",
    }

    # Complexity indicators
    HIGH_COMPLEXITY_INDICATORS: Set[str] = {
        "complex", "complicated", "intricate", "nuanced", "multifaceted",
        "ambiguous", "uncertain", "unclear", "vague", "judgment",
        "context-dependent", "subjective", "opinion", "interpretation",
    }

    LOW_COMPLEXITY_INDICATORS: Set[str] = {
        "simple", "straightforward", "routine", "standard", "basic",
        "clear", "defined", "structured", "template", "predetermined",
        "automated", "mechanical", "formulaic", "procedural",
    }

    def __init__(
        self,
        human_threshold: float = 0.6,
        ai_threshold: float = 0.6,
        default_to_hybrid: bool = True,
        custom_rules: Optional[List[Dict[str, Any]]] = None,
    ):
        """
        Initialize the classification engine.

        Args:
            human_threshold: Score threshold for human_primary classification
            ai_threshold: Score threshold for ai_primary classification
            default_to_hybrid: If true, ambiguous cases default to hybrid
            custom_rules: Optional list of custom classification rules
        """
        self.human_threshold = human_threshold
        self.ai_threshold = ai_threshold
        self.default_to_hybrid = default_to_hybrid
        self.custom_rules = custom_rules or []

        # Weights for different factors
        self.weights = {
            "keywords": 0.3,
            "complexity": 0.25,
            "urgency": 0.15,
            "required_skills": 0.15,
            "custom_rules": 0.15,
        }

        logger.info(
            f"ClassificationEngine initialized: "
            f"human_threshold={human_threshold}, ai_threshold={ai_threshold}"
        )

    async def classify_task(
        self,
        task_id: str,
        requirements: TaskRequirements,
        context: Optional[Dict[str, Any]] = None,
    ) -> ClassificationResult:
        """
        Classify a task for human/AI routing.

        Args:
            task_id: Task identifier
            requirements: Task requirements
            context: Optional additional context

        Returns:
            ClassificationResult with routing decision
        """
        context = context or {}
        factors: Dict[str, float] = {}

        # Analyze keywords
        keyword_scores = self._analyze_keywords(requirements)
        factors.update(keyword_scores)

        # Analyze complexity
        complexity_score = self._analyze_complexity(requirements)
        factors["complexity"] = complexity_score

        # Analyze urgency
        urgency_score = self._analyze_urgency(requirements)
        factors["urgency"] = urgency_score

        # Analyze required skills
        skill_score = self._analyze_skills(requirements)
        factors["skill_alignment"] = skill_score

        # Apply custom rules
        custom_score = self._apply_custom_rules(requirements, context)
        factors["custom_rules"] = custom_score

        # Calculate weighted scores
        human_score = (
            factors.get("human_keyword_score", 0) * self.weights["keywords"] +
            complexity_score * self.weights["complexity"] +
            (1 - skill_score) * self.weights["required_skills"] * 0.5 +
            custom_score * self.weights["custom_rules"] if custom_score > 0.5 else 0
        )

        ai_score = (
            factors.get("ai_keyword_score", 0) * self.weights["keywords"] +
            (1 - complexity_score) * self.weights["complexity"] +
            urgency_score * self.weights["urgency"] * 0.5 +
            skill_score * self.weights["required_skills"] * 0.5 +
            (1 - custom_score) * self.weights["custom_rules"] if custom_score < 0.5 else 0
        )

        factors["human_total"] = human_score
        factors["ai_total"] = ai_score

        # Determine classification
        classification, confidence, reasoning = self._determine_classification(
            human_score=human_score,
            ai_score=ai_score,
            factors=factors,
            requirements=requirements,
        )

        # Determine if human oversight is required
        human_oversight = self._requires_human_oversight(
            classification=classification,
            requirements=requirements,
            factors=factors,
        )

        return ClassificationResult(
            task_id=task_id,
            classification=classification,
            confidence=confidence,
            reasoning=reasoning,
            factors=factors,
            recommended_roles=[],  # Will be populated by dispatcher
            human_oversight_required=human_oversight,
            metadata={
                "engine_version": "1.0",
                "thresholds": {
                    "human": self.human_threshold,
                    "ai": self.ai_threshold,
                },
            },
        )

    def _analyze_keywords(self, requirements: TaskRequirements) -> Dict[str, float]:
        """
        Analyze task text for human/AI keywords.

        Returns scores for human and AI keyword presence.
        """
        text = requirements.task_description.lower()
        all_keywords = [k.lower() for k in requirements.keywords + requirements.required_skills]
        text_words = set(re.findall(r'\b\w+\b', text))
        all_text = text_words.union(set(all_keywords))

        # Count keyword matches
        human_matches = len(all_text.intersection(self.HUMAN_KEYWORDS))
        ai_matches = len(all_text.intersection(self.AI_KEYWORDS))

        # Normalize to 0-1 range
        total_matches = human_matches + ai_matches
        if total_matches == 0:
            return {"human_keyword_score": 0.0, "ai_keyword_score": 0.0}

        human_score = min(human_matches / 5, 1.0)  # Cap at 5 matches = 1.0
        ai_score = min(ai_matches / 5, 1.0)

        return {
            "human_keyword_score": human_score,
            "ai_keyword_score": ai_score,
            "human_keyword_count": human_matches,
            "ai_keyword_count": ai_matches,
        }

    def _analyze_complexity(self, requirements: TaskRequirements) -> float:
        """
        Analyze task complexity (higher = more human involvement needed).

        Returns a score from 0 (simple/AI-suitable) to 1 (complex/human-needed).
        """
        # Start with explicit complexity level
        complexity_map = {
            "low": 0.2,
            "medium": 0.5,
            "high": 0.8,
            "critical": 0.9,
        }
        base_score = complexity_map.get(requirements.complexity, 0.5)

        # Adjust based on indicators in text
        text = requirements.task_description.lower()
        text_words = set(re.findall(r'\b\w+\b', text))

        high_indicators = len(text_words.intersection(self.HIGH_COMPLEXITY_INDICATORS))
        low_indicators = len(text_words.intersection(self.LOW_COMPLEXITY_INDICATORS))

        # Adjust score
        adjustment = (high_indicators - low_indicators) * 0.1
        final_score = max(0.0, min(1.0, base_score + adjustment))

        return final_score

    def _analyze_urgency(self, requirements: TaskRequirements) -> float:
        """
        Analyze task urgency (higher urgency may favor AI for speed).

        Returns a score from 0 (low urgency) to 1 (critical urgency).
        """
        urgency_map = {
            "low": 0.1,
            "normal": 0.3,
            "high": 0.7,
            "critical": 0.95,
        }
        return urgency_map.get(requirements.urgency, 0.3)

    def _analyze_skills(self, requirements: TaskRequirements) -> float:
        """
        Analyze required skills for AI suitability.

        Returns a score from 0 (human skills needed) to 1 (AI-friendly skills).
        """
        if not requirements.required_skills:
            return 0.5  # Neutral

        # Skills that AI handles well
        ai_friendly_skills = {
            "programming", "coding", "data analysis", "automation",
            "testing", "documentation", "formatting", "translation",
            "summarization", "search", "classification", "calculation",
        }

        # Skills that require human judgment
        human_skills = {
            "leadership", "management", "negotiation", "counseling",
            "design", "strategy", "innovation", "creativity",
            "communication", "presentation", "mentoring",
        }

        skills_lower = [s.lower() for s in requirements.required_skills]

        ai_count = sum(1 for s in skills_lower if any(a in s for a in ai_friendly_skills))
        human_count = sum(1 for s in skills_lower if any(h in s for h in human_skills))

        total = ai_count + human_count
        if total == 0:
            return 0.5

        return ai_count / total

    def _apply_custom_rules(
        self,
        requirements: TaskRequirements,
        context: Dict[str, Any],
    ) -> float:
        """
        Apply custom classification rules.

        Returns a score where >0.5 favors human, <0.5 favors AI.
        """
        if not self.custom_rules:
            return 0.5  # Neutral

        scores = []

        for rule in self.custom_rules:
            try:
                if self._rule_matches(rule, requirements, context):
                    scores.append(rule.get("score", 0.5))
            except Exception as e:
                logger.warning(f"Error applying custom rule: {e}")

        if not scores:
            return 0.5

        return sum(scores) / len(scores)

    def _rule_matches(
        self,
        rule: Dict[str, Any],
        requirements: TaskRequirements,
        context: Dict[str, Any],
    ) -> bool:
        """Check if a custom rule matches the requirements."""
        # Check keyword matches
        if "keywords" in rule:
            text = requirements.task_description.lower()
            if not any(k.lower() in text for k in rule["keywords"]):
                return False

        # Check department matches
        if "departments" in rule:
            dept = requirements.department_hint or ""
            if dept.lower() not in [d.lower() for d in rule["departments"]]:
                return False

        # Check complexity matches
        if "complexity" in rule:
            if requirements.complexity != rule["complexity"]:
                return False

        return True

    def _determine_classification(
        self,
        human_score: float,
        ai_score: float,
        factors: Dict[str, float],
        requirements: TaskRequirements,
    ) -> tuple[RoleType, float, str]:
        """
        Determine the final classification based on scores.

        Returns (classification, confidence, reasoning).
        """
        score_diff = human_score - ai_score
        max_score = max(human_score, ai_score)

        # Strong human preference
        if score_diff > 0.3 and human_score >= self.human_threshold:
            confidence = min(0.95, 0.6 + score_diff)
            reasoning = self._build_reasoning(
                RoleType.HUMAN_PRIMARY, factors, requirements
            )
            return RoleType.HUMAN_PRIMARY, confidence, reasoning

        # Strong AI preference
        if score_diff < -0.3 and ai_score >= self.ai_threshold:
            confidence = min(0.95, 0.6 + abs(score_diff))
            reasoning = self._build_reasoning(
                RoleType.AI_PRIMARY, factors, requirements
            )
            return RoleType.AI_PRIMARY, confidence, reasoning

        # Hybrid - scores are close or both moderate
        if self.default_to_hybrid:
            confidence = max(0.5, 1 - abs(score_diff))
            reasoning = self._build_reasoning(
                RoleType.HYBRID, factors, requirements
            )
            return RoleType.HYBRID, confidence, reasoning

        # Fallback to stronger score if not defaulting to hybrid
        if human_score > ai_score:
            return RoleType.HUMAN_PRIMARY, max_score, self._build_reasoning(
                RoleType.HUMAN_PRIMARY, factors, requirements
            )
        else:
            return RoleType.AI_PRIMARY, max_score, self._build_reasoning(
                RoleType.AI_PRIMARY, factors, requirements
            )

    def _build_reasoning(
        self,
        classification: RoleType,
        factors: Dict[str, float],
        requirements: TaskRequirements,
    ) -> str:
        """Build a human-readable explanation of the classification."""
        parts = [f"Classification: {classification.value}"]

        if classification == RoleType.HUMAN_PRIMARY:
            reasons = []
            if factors.get("human_keyword_count", 0) > 0:
                reasons.append(f"{int(factors['human_keyword_count'])} human-oriented keywords detected")
            if factors.get("complexity", 0) > 0.6:
                reasons.append(f"high complexity ({requirements.complexity})")
            if factors.get("skill_alignment", 1) < 0.4:
                reasons.append("skills require human judgment")
            parts.append("Reasons: " + "; ".join(reasons) if reasons else "Balanced toward human involvement")

        elif classification == RoleType.AI_PRIMARY:
            reasons = []
            if factors.get("ai_keyword_count", 0) > 0:
                reasons.append(f"{int(factors['ai_keyword_count'])} automation-friendly keywords detected")
            if factors.get("complexity", 1) < 0.4:
                reasons.append(f"straightforward complexity ({requirements.complexity})")
            if factors.get("urgency", 0) > 0.6:
                reasons.append(f"urgency favors AI speed ({requirements.urgency})")
            if factors.get("skill_alignment", 0) > 0.6:
                reasons.append("skills align with AI capabilities")
            parts.append("Reasons: " + "; ".join(reasons) if reasons else "Task suitable for AI automation")

        else:  # HYBRID
            parts.append(
                f"Reasons: Balanced scores (human={factors.get('human_total', 0):.2f}, "
                f"ai={factors.get('ai_total', 0):.2f}) suggest collaborative approach"
            )

        return " | ".join(parts)

    def _requires_human_oversight(
        self,
        classification: RoleType,
        requirements: TaskRequirements,
        factors: Dict[str, float],
    ) -> bool:
        """Determine if human oversight is required regardless of classification."""
        # Always require oversight for human_primary and hybrid
        if classification in [RoleType.HUMAN_PRIMARY, RoleType.HYBRID]:
            return True

        # Require oversight for high complexity even if AI-primary
        if factors.get("complexity", 0) > 0.7:
            return True

        # Require oversight for critical urgency (high stakes)
        if requirements.urgency == "critical":
            return True

        # Check for sensitive keywords even in AI-primary tasks
        text = requirements.task_description.lower()
        sensitive_words = {"sensitive", "confidential", "financial", "legal", "security"}
        if any(word in text for word in sensitive_words):
            return True

        return False

    def add_custom_rule(self, rule: Dict[str, Any]) -> None:
        """
        Add a custom classification rule.

        Rule format:
        {
            "keywords": ["word1", "word2"],  # Optional
            "departments": ["dept1"],  # Optional
            "complexity": "high",  # Optional
            "score": 0.8,  # 0-1, >0.5 favors human
        }
        """
        self.custom_rules.append(rule)
        logger.info(f"Added custom rule: {rule}")

    def update_weights(self, new_weights: Dict[str, float]) -> None:
        """Update the factor weights."""
        self.weights.update(new_weights)
        logger.info(f"Updated weights: {self.weights}")

    def get_statistics(self) -> Dict[str, Any]:
        """Get engine configuration and statistics."""
        return {
            "human_threshold": self.human_threshold,
            "ai_threshold": self.ai_threshold,
            "default_to_hybrid": self.default_to_hybrid,
            "weights": self.weights,
            "custom_rules_count": len(self.custom_rules),
            "human_keywords_count": len(self.HUMAN_KEYWORDS),
            "ai_keywords_count": len(self.AI_KEYWORDS),
        }
