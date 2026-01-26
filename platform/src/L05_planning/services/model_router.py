"""
Model Router - Intelligent Model Selection for L05 Planning
Path: platform/src/L05_planning/services/model_router.py

Routes tasks to appropriate models based on complexity:
- Simple tasks -> Ollama (codellama)
- Moderate tasks -> Ollama (mistral)
- Complex tasks -> Claude (sonnet)
- Critical tasks -> Claude (opus)

Features:
- Complexity analysis
- Quality-based escalation
- Cost optimization
- Latency optimization
"""

import logging
import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from ..integration.l04_bridge import L04Bridge, ModelProvider, RoutingStrategy, GeneratedPlan

logger = logging.getLogger(__name__)


class ComplexityLevel(Enum):
    """Task complexity levels."""
    SIMPLE = "simple"        # Syntax validation, file checks, basic criteria
    MODERATE = "moderate"    # Criteria generation, semantic similarity
    COMPLEX = "complex"      # Architecture, novel problems
    CRITICAL = "critical"    # High-stakes, ambiguous requirements


class TaskCategory(Enum):
    """Categories of tasks for routing."""
    VALIDATION = "validation"     # File checks, syntax validation
    GENERATION = "generation"     # Code/content generation
    ANALYSIS = "analysis"         # Code analysis, review
    DECOMPOSITION = "decomposition"  # Breaking down tasks
    PLANNING = "planning"         # High-level planning


@dataclass
class RoutingDecision:
    """Decision from the model router."""
    model: str
    provider: ModelProvider
    complexity: ComplexityLevel
    category: TaskCategory
    confidence: float  # 0-1 confidence in the routing decision
    reason: str
    estimated_cost: float = 0.0  # Relative cost estimate
    estimated_latency_ms: int = 0  # Estimated latency


@dataclass
class GenerationWithEscalation:
    """Result of generation with possible escalation."""
    plan: GeneratedPlan
    escalated: bool = False
    escalation_reason: Optional[str] = None
    attempts: int = 1
    models_tried: List[str] = field(default_factory=list)
    total_cost: float = 0.0


# Model configurations
MODEL_CONFIGS = {
    ModelProvider.OLLAMA: {
        "codellama": {
            "complexity": [ComplexityLevel.SIMPLE],
            "categories": [TaskCategory.VALIDATION, TaskCategory.GENERATION],
            "cost_factor": 0.0,  # Free (local)
            "latency_ms": 500,
            "quality_threshold": 0.6,
        },
        "mistral": {
            "complexity": [ComplexityLevel.SIMPLE, ComplexityLevel.MODERATE],
            "categories": [TaskCategory.VALIDATION, TaskCategory.GENERATION, TaskCategory.ANALYSIS],
            "cost_factor": 0.0,  # Free (local)
            "latency_ms": 800,
            "quality_threshold": 0.7,
        },
        "llama2": {
            "complexity": [ComplexityLevel.SIMPLE, ComplexityLevel.MODERATE],
            "categories": [TaskCategory.GENERATION, TaskCategory.ANALYSIS],
            "cost_factor": 0.0,
            "latency_ms": 1000,
            "quality_threshold": 0.65,
        },
    },
    ModelProvider.ANTHROPIC: {
        "claude-3-haiku": {
            "complexity": [ComplexityLevel.MODERATE, ComplexityLevel.COMPLEX],
            "categories": [TaskCategory.VALIDATION, TaskCategory.GENERATION, TaskCategory.ANALYSIS],
            "cost_factor": 0.25,
            "latency_ms": 300,
            "quality_threshold": 0.8,
        },
        "claude-3-sonnet": {
            "complexity": [ComplexityLevel.MODERATE, ComplexityLevel.COMPLEX, ComplexityLevel.CRITICAL],
            "categories": [TaskCategory.GENERATION, TaskCategory.ANALYSIS, TaskCategory.DECOMPOSITION, TaskCategory.PLANNING],
            "cost_factor": 1.0,
            "latency_ms": 500,
            "quality_threshold": 0.85,
        },
        "claude-3-opus": {
            "complexity": [ComplexityLevel.CRITICAL],
            "categories": [TaskCategory.DECOMPOSITION, TaskCategory.PLANNING],
            "cost_factor": 5.0,
            "latency_ms": 1500,
            "quality_threshold": 0.95,
        },
    },
}


class ModelRouter:
    """
    Intelligent model router for L05 Planning.

    Routes tasks to appropriate models based on:
    - Task complexity
    - Task category
    - Routing strategy (cost, quality, latency, balanced)
    - Quality escalation

    Features:
    - Complexity analysis from task description
    - Quality-based escalation (try cheaper model first, escalate if quality insufficient)
    - Cost tracking
    - Latency optimization
    """

    def __init__(
        self,
        l04_bridge: Optional[L04Bridge] = None,
        default_strategy: RoutingStrategy = RoutingStrategy.BALANCED,
        quality_threshold: float = 0.7,
        prefer_local: bool = True,
    ):
        """
        Initialize model router.

        Args:
            l04_bridge: L04Bridge for model generation
            default_strategy: Default routing strategy
            quality_threshold: Minimum quality threshold for acceptance
            prefer_local: If True, prefer Ollama over cloud models
        """
        self.l04_bridge = l04_bridge or L04Bridge()
        self.default_strategy = default_strategy
        self.quality_threshold = quality_threshold
        self.prefer_local = prefer_local

        # Routing history for analysis
        self._routing_history: List[RoutingDecision] = []
        self._escalation_count = 0
        self._total_cost = 0.0

        # Complexity indicators
        self._complexity_keywords = {
            ComplexityLevel.SIMPLE: [
                "check", "validate", "verify", "simple", "basic", "syntax",
                "format", "lint", "exists", "file",
            ],
            ComplexityLevel.MODERATE: [
                "generate", "create", "implement", "add", "modify",
                "update", "refactor", "extract", "transform",
            ],
            ComplexityLevel.COMPLEX: [
                "design", "architect", "optimize", "integrate", "migrate",
                "analyze", "review", "novel", "complex",
            ],
            ComplexityLevel.CRITICAL: [
                "critical", "security", "production", "breaking", "migration",
                "data", "schema", "api", "public",
            ],
        }

        # Category indicators
        self._category_keywords = {
            TaskCategory.VALIDATION: ["validate", "check", "verify", "test", "lint"],
            TaskCategory.GENERATION: ["generate", "create", "write", "implement", "add"],
            TaskCategory.ANALYSIS: ["analyze", "review", "examine", "inspect", "audit"],
            TaskCategory.DECOMPOSITION: ["decompose", "break", "split", "extract", "separate"],
            TaskCategory.PLANNING: ["plan", "design", "architect", "strategy", "approach"],
        }

    def analyze_complexity(self, task: str) -> ComplexityLevel:
        """
        Analyze task complexity from description.

        Args:
            task: Task description

        Returns:
            Detected complexity level
        """
        task_lower = task.lower()

        # Count keyword matches for each level
        scores = {level: 0 for level in ComplexityLevel}

        for level, keywords in self._complexity_keywords.items():
            for keyword in keywords:
                if keyword in task_lower:
                    scores[level] += 1

        # Check for complexity indicators
        # Long task = more complex
        if len(task) > 500:
            scores[ComplexityLevel.COMPLEX] += 2
        elif len(task) > 200:
            scores[ComplexityLevel.MODERATE] += 1

        # Multiple files = more complex
        file_count = len(re.findall(r'\.(py|js|ts|java|go|rs|cpp)\b', task_lower))
        if file_count > 5:
            scores[ComplexityLevel.COMPLEX] += 2
        elif file_count > 2:
            scores[ComplexityLevel.MODERATE] += 1

        # Find highest scoring level
        max_level = ComplexityLevel.SIMPLE
        max_score = 0

        for level, score in scores.items():
            if score > max_score:
                max_score = score
                max_level = level

        return max_level

    def analyze_category(self, task: str) -> TaskCategory:
        """
        Analyze task category from description.

        Args:
            task: Task description

        Returns:
            Detected task category
        """
        task_lower = task.lower()

        # Count keyword matches for each category
        scores = {cat: 0 for cat in TaskCategory}

        for category, keywords in self._category_keywords.items():
            for keyword in keywords:
                if keyword in task_lower:
                    scores[category] += 1

        # Find highest scoring category
        max_category = TaskCategory.GENERATION  # Default
        max_score = 0

        for category, score in scores.items():
            if score > max_score:
                max_score = score
                max_category = category

        return max_category

    def route(
        self,
        task: str,
        complexity_hint: Optional[ComplexityLevel] = None,
        category_hint: Optional[TaskCategory] = None,
        strategy: Optional[RoutingStrategy] = None,
    ) -> RoutingDecision:
        """
        Route a task to the appropriate model.

        Args:
            task: Task description
            complexity_hint: Optional complexity hint (overrides analysis)
            category_hint: Optional category hint (overrides analysis)
            strategy: Routing strategy (defaults to instance default)

        Returns:
            RoutingDecision with selected model
        """
        strategy = strategy or self.default_strategy

        # Analyze task if no hints provided
        complexity = complexity_hint or self.analyze_complexity(task)
        category = category_hint or self.analyze_category(task)

        logger.debug(f"Routing task: complexity={complexity.value}, category={category.value}")

        # Select model based on strategy
        if strategy == RoutingStrategy.COST:
            decision = self._route_for_cost(complexity, category)
        elif strategy == RoutingStrategy.QUALITY:
            decision = self._route_for_quality(complexity, category)
        elif strategy == RoutingStrategy.LATENCY:
            decision = self._route_for_latency(complexity, category)
        else:  # BALANCED
            decision = self._route_balanced(complexity, category)

        self._routing_history.append(decision)
        logger.info(f"Routed to {decision.model} ({decision.provider.value}): {decision.reason}")

        return decision

    def _route_for_cost(self, complexity: ComplexityLevel, category: TaskCategory) -> RoutingDecision:
        """Route prioritizing cost (prefer Ollama)."""
        # Try Ollama models first
        for model, config in MODEL_CONFIGS[ModelProvider.OLLAMA].items():
            if complexity in config["complexity"] and category in config["categories"]:
                return RoutingDecision(
                    model=model,
                    provider=ModelProvider.OLLAMA,
                    complexity=complexity,
                    category=category,
                    confidence=0.8,
                    reason=f"Cost-optimized: using local {model}",
                    estimated_cost=config["cost_factor"],
                    estimated_latency_ms=config["latency_ms"],
                )

        # Fall back to cheapest Claude
        return RoutingDecision(
            model="claude-3-haiku",
            provider=ModelProvider.ANTHROPIC,
            complexity=complexity,
            category=category,
            confidence=0.7,
            reason="Cost-optimized fallback: claude-3-haiku",
            estimated_cost=0.25,
            estimated_latency_ms=300,
        )

    def _route_for_quality(self, complexity: ComplexityLevel, category: TaskCategory) -> RoutingDecision:
        """Route prioritizing quality (prefer Claude)."""
        # Map complexity to Claude model
        if complexity == ComplexityLevel.CRITICAL:
            model = "claude-3-opus"
        elif complexity == ComplexityLevel.COMPLEX:
            model = "claude-3-sonnet"
        else:
            model = "claude-3-haiku"

        config = MODEL_CONFIGS[ModelProvider.ANTHROPIC][model]

        return RoutingDecision(
            model=model,
            provider=ModelProvider.ANTHROPIC,
            complexity=complexity,
            category=category,
            confidence=0.9,
            reason=f"Quality-optimized: using {model}",
            estimated_cost=config["cost_factor"],
            estimated_latency_ms=config["latency_ms"],
        )

    def _route_for_latency(self, complexity: ComplexityLevel, category: TaskCategory) -> RoutingDecision:
        """Route prioritizing latency (prefer fastest)."""
        # Claude haiku is fastest for cloud, Ollama codellama for local
        if complexity in [ComplexityLevel.SIMPLE]:
            return RoutingDecision(
                model="codellama",
                provider=ModelProvider.OLLAMA,
                complexity=complexity,
                category=category,
                confidence=0.85,
                reason="Latency-optimized: using local codellama",
                estimated_cost=0.0,
                estimated_latency_ms=500,
            )

        return RoutingDecision(
            model="claude-3-haiku",
            provider=ModelProvider.ANTHROPIC,
            complexity=complexity,
            category=category,
            confidence=0.85,
            reason="Latency-optimized: using claude-3-haiku",
            estimated_cost=0.25,
            estimated_latency_ms=300,
        )

    def _route_balanced(self, complexity: ComplexityLevel, category: TaskCategory) -> RoutingDecision:
        """Route with balanced strategy."""
        # Simple tasks -> Ollama
        if complexity == ComplexityLevel.SIMPLE and self.prefer_local:
            for model, config in MODEL_CONFIGS[ModelProvider.OLLAMA].items():
                if category in config["categories"]:
                    return RoutingDecision(
                        model=model,
                        provider=ModelProvider.OLLAMA,
                        complexity=complexity,
                        category=category,
                        confidence=0.8,
                        reason=f"Balanced: simple task -> local {model}",
                        estimated_cost=config["cost_factor"],
                        estimated_latency_ms=config["latency_ms"],
                    )

        # Moderate tasks -> Ollama mistral or Claude haiku
        if complexity == ComplexityLevel.MODERATE:
            if self.prefer_local:
                return RoutingDecision(
                    model="mistral",
                    provider=ModelProvider.OLLAMA,
                    complexity=complexity,
                    category=category,
                    confidence=0.75,
                    reason="Balanced: moderate task -> mistral",
                    estimated_cost=0.0,
                    estimated_latency_ms=800,
                )
            else:
                return RoutingDecision(
                    model="claude-3-haiku",
                    provider=ModelProvider.ANTHROPIC,
                    complexity=complexity,
                    category=category,
                    confidence=0.8,
                    reason="Balanced: moderate task -> claude-3-haiku",
                    estimated_cost=0.25,
                    estimated_latency_ms=300,
                )

        # Complex tasks -> Claude sonnet
        if complexity == ComplexityLevel.COMPLEX:
            return RoutingDecision(
                model="claude-3-sonnet",
                provider=ModelProvider.ANTHROPIC,
                complexity=complexity,
                category=category,
                confidence=0.85,
                reason="Balanced: complex task -> claude-3-sonnet",
                estimated_cost=1.0,
                estimated_latency_ms=500,
            )

        # Critical tasks -> Claude opus
        return RoutingDecision(
            model="claude-3-opus",
            provider=ModelProvider.ANTHROPIC,
            complexity=complexity,
            category=category,
            confidence=0.9,
            reason="Balanced: critical task -> claude-3-opus",
            estimated_cost=5.0,
            estimated_latency_ms=1500,
        )

    async def generate_with_escalation(
        self,
        task: str,
        min_quality: float = 0.7,
        max_escalations: int = 2,
        context: Optional[Dict[str, Any]] = None,
    ) -> GenerationWithEscalation:
        """
        Generate with quality-based escalation.

        Tries cheaper models first, escalates to more expensive
        models if quality threshold not met.

        Args:
            task: Task description
            min_quality: Minimum quality threshold
            max_escalations: Maximum number of escalation attempts
            context: Optional context for generation

        Returns:
            GenerationWithEscalation with result and escalation info
        """
        result = GenerationWithEscalation(
            plan=GeneratedPlan(
                plan_id="",
                content="",
                model="",
                provider=ModelProvider.OLLAMA,
            ),
            models_tried=[],
        )

        # Get initial routing decision
        decision = self.route(task)

        # Escalation chain
        escalation_chain = [
            (ModelProvider.OLLAMA, "mistral"),
            (ModelProvider.ANTHROPIC, "claude-3-haiku"),
            (ModelProvider.ANTHROPIC, "claude-3-sonnet"),
            (ModelProvider.ANTHROPIC, "claude-3-opus"),
        ]

        # Find starting point in chain
        start_idx = 0
        for i, (provider, model) in enumerate(escalation_chain):
            if provider == decision.provider and model == decision.model:
                start_idx = i
                break

        # Try models with escalation
        for attempt, (provider, model) in enumerate(escalation_chain[start_idx:]):
            if attempt >= max_escalations + 1:
                break

            result.models_tried.append(model)
            result.attempts = attempt + 1

            logger.info(f"Attempting generation with {model} (attempt {attempt + 1})")

            # Generate
            plan = self.l04_bridge.generate_plan(
                task_description=task,
                context=context,
                model=model,
                provider=provider,
            )

            result.plan = plan

            # Estimate quality (in production, would use L06 scoring)
            estimated_quality = self._estimate_quality(plan)

            # Add cost
            config = MODEL_CONFIGS.get(provider, {}).get(model, {"cost_factor": 1.0})
            result.total_cost += config.get("cost_factor", 1.0)

            if estimated_quality >= min_quality:
                logger.info(f"Quality threshold met with {model}: {estimated_quality:.2f}")
                return result

            # Need to escalate
            result.escalated = True
            result.escalation_reason = f"Quality {estimated_quality:.2f} < threshold {min_quality}"
            self._escalation_count += 1

            logger.warning(f"Escalating from {model}: {result.escalation_reason}")

        # Return best effort result
        return result

    def _estimate_quality(self, plan: GeneratedPlan) -> float:
        """
        Estimate quality of a generated plan.

        In production, this would use L06 scoring.
        For now, use simple heuristics.
        """
        content = plan.content

        # Base quality
        quality = 0.5

        # Length bonus (non-trivial content)
        if len(content) > 200:
            quality += 0.1
        if len(content) > 500:
            quality += 0.1

        # Structure bonus (has sections)
        if "##" in content:
            quality += 0.1
        if "###" in content:
            quality += 0.05

        # Has acceptance criteria
        if "acceptance" in content.lower() or "criteria" in content.lower():
            quality += 0.1

        # Has files listed
        if "file" in content.lower() or ".py" in content or ".js" in content:
            quality += 0.1

        return min(quality, 1.0)

    def get_statistics(self) -> Dict[str, Any]:
        """Returns router statistics."""
        if not self._routing_history:
            return {
                "total_routings": 0,
                "escalation_count": 0,
                "total_cost": 0.0,
            }

        # Count by provider
        by_provider = {}
        for decision in self._routing_history:
            provider = decision.provider.value
            by_provider[provider] = by_provider.get(provider, 0) + 1

        # Count by complexity
        by_complexity = {}
        for decision in self._routing_history:
            complexity = decision.complexity.value
            by_complexity[complexity] = by_complexity.get(complexity, 0) + 1

        # Calculate Ollama usage
        ollama_count = by_provider.get("ollama", 0)
        total = len(self._routing_history)
        ollama_percentage = (ollama_count / total * 100) if total > 0 else 0

        return {
            "total_routings": total,
            "by_provider": by_provider,
            "by_complexity": by_complexity,
            "escalation_count": self._escalation_count,
            "total_cost": self._total_cost,
            "ollama_percentage": ollama_percentage,
            "average_confidence": sum(d.confidence for d in self._routing_history) / total if total > 0 else 0,
            "prefer_local": self.prefer_local,
            "default_strategy": self.default_strategy.value,
        }

    def clear_history(self):
        """Clear routing history."""
        self._routing_history = []
