"""
L14 Skill Library - Skill Optimizer Service

Optimizes skills for token compression and priority-based loading.
"""

import logging
from typing import List, Optional, Dict, Any, Set
from uuid import UUID

from ..models import (
    Skill,
    SkillDefinition,
    SkillOptimizationRequest,
    SkillOptimizationResult,
    OptimizationStrategy,
    SkillPriority,
    SkillStatus,
)

logger = logging.getLogger(__name__)


class SkillOptimizer:
    """
    Skill Optimizer Service

    Provides optimization strategies for skill loading including:
    - Token reduction through content compression
    - Priority-based loading for context management
    - Context-aware skill selection
    """

    def __init__(self, skill_store=None):
        """
        Initialize the Skill Optimizer.

        Args:
            skill_store: Optional SkillStore for fetching skills
        """
        self._skill_store = skill_store
        self._priority_weights = {
            SkillPriority.CRITICAL: 1.0,
            SkillPriority.HIGH: 0.8,
            SkillPriority.MEDIUM: 0.5,
            SkillPriority.LOW: 0.3,
            SkillPriority.OPTIONAL: 0.1,
        }
        logger.info("SkillOptimizer initialized")

    async def optimize(
        self,
        request: SkillOptimizationRequest,
        skills: Optional[List[Skill]] = None,
    ) -> SkillOptimizationResult:
        """
        Optimize skills based on the specified strategy.

        Args:
            request: Optimization request
            skills: Optional list of skills (fetched from store if not provided)

        Returns:
            SkillOptimizationResult with optimized skills
        """
        try:
            # Fetch skills if not provided
            if skills is None and self._skill_store:
                skills = []
                for skill_id in request.skill_ids:
                    skill = await self._skill_store.get(skill_id)
                    if skill:
                        skills.append(skill)
            elif skills is None:
                return SkillOptimizationResult(
                    success=False,
                    original_token_count=0,
                    optimized_token_count=0,
                    reduction_percentage=0,
                    optimization_details={"error": "No skills provided and no store available"},
                )

            # Calculate original token count
            original_tokens = sum(
                skill.definition.metadata.token_count or self._estimate_tokens(skill)
                for skill in skills
            )

            # Apply optimization strategy
            if request.strategy == OptimizationStrategy.TOKEN_REDUCTION:
                result = await self._optimize_token_reduction(
                    skills, request.target_token_budget, request.preserve_sections
                )
            elif request.strategy == OptimizationStrategy.PRIORITY_LOADING:
                result = await self._optimize_priority_loading(
                    skills, request.target_token_budget
                )
            elif request.strategy == OptimizationStrategy.CONTEXT_AWARE:
                result = await self._optimize_context_aware(
                    skills, request.target_token_budget, request.context
                )
            elif request.strategy == OptimizationStrategy.MINIMAL:
                result = await self._optimize_minimal(
                    skills, request.target_token_budget
                )
            else:
                result = {
                    "skills": skills,
                    "dropped": [],
                    "details": {},
                }

            # Calculate optimized token count
            optimized_tokens = sum(
                skill.definition.metadata.token_count or self._estimate_tokens(skill)
                for skill in result["skills"]
            )

            # Calculate reduction percentage
            reduction = 0.0
            if original_tokens > 0:
                reduction = ((original_tokens - optimized_tokens) / original_tokens) * 100

            return SkillOptimizationResult(
                success=True,
                original_token_count=original_tokens,
                optimized_token_count=optimized_tokens,
                reduction_percentage=round(reduction, 2),
                optimized_skills=result["skills"],
                dropped_skills=result["dropped"],
                optimization_details=result["details"],
            )

        except Exception as e:
            logger.error(f"Optimization failed: {e}")
            return SkillOptimizationResult(
                success=False,
                original_token_count=0,
                optimized_token_count=0,
                reduction_percentage=0,
                optimization_details={"error": str(e)},
            )

    async def _optimize_token_reduction(
        self,
        skills: List[Skill],
        target_budget: int,
        preserve_sections: List[str],
    ) -> Dict[str, Any]:
        """
        Optimize by reducing token count through content compression.

        Strategies:
        1. Remove examples if not in preserve_sections
        2. Shorten descriptions
        3. Remove optional sections
        4. Merge similar procedures
        """
        optimized_skills = []
        dropped_skills = []
        details = {"actions": []}

        current_tokens = 0

        for skill in skills:
            # Create a copy for optimization
            optimized = self._copy_skill(skill)

            # Apply token reduction strategies
            if "examples" not in preserve_sections:
                if optimized.definition.examples:
                    details["actions"].append(f"Removed examples from {skill.name}")
                    optimized.definition.examples = []

            if "procedures" not in preserve_sections:
                # Keep only first 2 procedures
                if len(optimized.definition.procedures) > 2:
                    details["actions"].append(
                        f"Reduced procedures from {len(optimized.definition.procedures)} to 2 in {skill.name}"
                    )
                    optimized.definition.procedures = optimized.definition.procedures[:2]

            if "secondary_responsibilities" not in preserve_sections:
                if optimized.definition.responsibilities.secondary:
                    details["actions"].append(f"Removed secondary responsibilities from {skill.name}")
                    optimized.definition.responsibilities.secondary = []

            # Recalculate token count
            new_tokens = self._estimate_tokens(optimized)
            optimized.definition.metadata.token_count = new_tokens

            # Check if within budget
            if current_tokens + new_tokens <= target_budget:
                current_tokens += new_tokens
                optimized_skills.append(optimized)
            else:
                dropped_skills.append(skill.id)
                details["actions"].append(f"Dropped {skill.name} due to token budget")

        details["total_actions"] = len(details["actions"])
        details["preserved_sections"] = preserve_sections

        return {
            "skills": optimized_skills,
            "dropped": dropped_skills,
            "details": details,
        }

    async def _optimize_priority_loading(
        self,
        skills: List[Skill],
        target_budget: int,
    ) -> Dict[str, Any]:
        """
        Optimize by loading skills based on priority.

        Higher priority skills are loaded first until budget is exhausted.
        """
        # Sort by priority
        priority_order = {
            SkillPriority.CRITICAL: 0,
            SkillPriority.HIGH: 1,
            SkillPriority.MEDIUM: 2,
            SkillPriority.LOW: 3,
            SkillPriority.OPTIONAL: 4,
        }

        sorted_skills = sorted(
            skills,
            key=lambda s: priority_order.get(s.definition.metadata.priority, 5)
        )

        optimized_skills = []
        dropped_skills = []
        current_tokens = 0
        details = {
            "loading_order": [],
            "priority_distribution": {},
        }

        for skill in sorted_skills:
            tokens = skill.definition.metadata.token_count or self._estimate_tokens(skill)
            priority = skill.definition.metadata.priority.value

            if current_tokens + tokens <= target_budget:
                current_tokens += tokens
                optimized_skills.append(skill)
                details["loading_order"].append({
                    "name": skill.name,
                    "priority": priority,
                    "tokens": tokens,
                })

                # Track priority distribution
                if priority not in details["priority_distribution"]:
                    details["priority_distribution"][priority] = 0
                details["priority_distribution"][priority] += 1
            else:
                dropped_skills.append(skill.id)

        return {
            "skills": optimized_skills,
            "dropped": dropped_skills,
            "details": details,
        }

    async def _optimize_context_aware(
        self,
        skills: List[Skill],
        target_budget: int,
        context: Optional[str],
    ) -> Dict[str, Any]:
        """
        Optimize by selecting skills relevant to the current context.

        Uses keyword matching and tag relevance to score skills.
        """
        if not context:
            # Fall back to priority loading
            return await self._optimize_priority_loading(skills, target_budget)

        # Extract keywords from context
        context_keywords = self._extract_keywords(context)

        # Score skills by relevance
        scored_skills = []
        for skill in skills:
            score = self._calculate_relevance_score(skill, context_keywords)
            scored_skills.append((skill, score))

        # Sort by score (highest first)
        scored_skills.sort(key=lambda x: x[1], reverse=True)

        optimized_skills = []
        dropped_skills = []
        current_tokens = 0
        details = {
            "context_keywords": list(context_keywords),
            "relevance_scores": {},
        }

        for skill, score in scored_skills:
            tokens = skill.definition.metadata.token_count or self._estimate_tokens(skill)

            details["relevance_scores"][skill.name] = round(score, 3)

            if current_tokens + tokens <= target_budget:
                current_tokens += tokens
                optimized_skills.append(skill)
            else:
                dropped_skills.append(skill.id)

        return {
            "skills": optimized_skills,
            "dropped": dropped_skills,
            "details": details,
        }

    async def _optimize_minimal(
        self,
        skills: List[Skill],
        target_budget: int,
    ) -> Dict[str, Any]:
        """
        Optimize by loading only critical and high-priority skills.

        Also strips all non-essential content.
        """
        # Filter to only critical and high priority
        essential_skills = [
            s for s in skills
            if s.definition.metadata.priority in [SkillPriority.CRITICAL, SkillPriority.HIGH]
        ]

        optimized_skills = []
        dropped_skills = []
        current_tokens = 0
        details = {"mode": "minimal", "stripped_sections": []}

        for skill in essential_skills:
            # Create minimal copy
            minimal = self._create_minimal_skill(skill)
            tokens = self._estimate_tokens(minimal)

            if current_tokens + tokens <= target_budget:
                current_tokens += tokens
                optimized_skills.append(minimal)
            else:
                dropped_skills.append(skill.id)

        # Track dropped non-essential skills
        for skill in skills:
            if skill.id not in [s.id for s in optimized_skills] and skill.id not in dropped_skills:
                dropped_skills.append(skill.id)

        details["stripped_sections"] = ["examples", "procedures", "secondary_responsibilities"]

        return {
            "skills": optimized_skills,
            "dropped": dropped_skills,
            "details": details,
        }

    def _copy_skill(self, skill: Skill) -> Skill:
        """Create a deep copy of a skill."""
        return Skill(
            id=skill.id,
            name=skill.name,
            status=skill.status,
            definition=SkillDefinition(
                metadata=skill.definition.metadata.model_copy(deep=True),
                role=skill.definition.role.model_copy(deep=True),
                responsibilities=skill.definition.responsibilities.model_copy(deep=True),
                tools=skill.definition.tools.model_copy(deep=True),
                procedures=[p.model_copy(deep=True) for p in skill.definition.procedures],
                examples=[e.model_copy(deep=True) for e in skill.definition.examples],
                constraints=skill.definition.constraints.model_copy(deep=True),
                dependencies=skill.definition.dependencies.model_copy(deep=True),
            ),
            raw_content=skill.raw_content,
            agent_id=skill.agent_id,
            created_at=skill.created_at,
            updated_at=skill.updated_at,
        )

    def _create_minimal_skill(self, skill: Skill) -> Skill:
        """Create a minimal version of a skill with only essential content."""
        minimal = self._copy_skill(skill)

        # Strip non-essential content
        minimal.definition.examples = []
        minimal.definition.procedures = []
        minimal.definition.responsibilities.secondary = []

        # Keep only first 3 expertise areas
        minimal.definition.role.expertise_areas = (
            minimal.definition.role.expertise_areas[:3]
        )

        # Recalculate token count
        minimal.definition.metadata.token_count = self._estimate_tokens(minimal)

        return minimal

    def _estimate_tokens(self, skill: Skill) -> int:
        """Estimate token count for a skill."""
        # Rough estimation: count characters and divide by 4
        content_parts = [
            skill.name,
            skill.definition.role.title,
            skill.definition.role.description,
            " ".join(skill.definition.role.expertise_areas),
            " ".join(skill.definition.responsibilities.primary),
            " ".join(skill.definition.responsibilities.secondary),
            " ".join(skill.definition.tools.required),
            " ".join(skill.definition.tools.optional),
        ]

        # Add procedures
        for proc in skill.definition.procedures:
            content_parts.extend([
                proc.name,
                proc.description,
                " ".join(proc.steps),
            ])

        # Add examples
        for ex in skill.definition.examples:
            content_parts.extend([
                ex.name,
                ex.user_input,
                ex.expected_response,
            ])

        total_chars = sum(len(p) for p in content_parts if p)
        return total_chars // 4

    def _extract_keywords(self, context: str) -> Set[str]:
        """Extract keywords from context for relevance matching."""
        # Simple keyword extraction (could be enhanced with NLP)
        # Remove common words and extract significant terms
        stop_words = {
            "the", "a", "an", "is", "are", "was", "were", "be", "been",
            "being", "have", "has", "had", "do", "does", "did", "will",
            "would", "could", "should", "may", "might", "must", "shall",
            "can", "need", "dare", "ought", "used", "to", "of", "in",
            "for", "on", "with", "at", "by", "from", "as", "into",
            "through", "during", "before", "after", "above", "below",
            "between", "under", "again", "further", "then", "once",
            "and", "but", "or", "nor", "so", "yet", "both", "either",
            "neither", "not", "only", "own", "same", "than", "too",
            "very", "just", "also", "now", "here", "there", "when",
            "where", "why", "how", "all", "each", "every", "both",
            "few", "more", "most", "other", "some", "such", "no",
            "any", "this", "that", "these", "those", "i", "me", "my",
            "we", "our", "you", "your", "he", "him", "his", "she",
            "her", "it", "its", "they", "them", "their", "what",
            "which", "who", "whom", "whose", "if", "unless", "until",
        }

        # Tokenize and filter
        words = context.lower().split()
        keywords = {
            word.strip(".,!?;:\"'()[]{}")
            for word in words
            if word not in stop_words and len(word) > 2
        }

        return keywords

    def _calculate_relevance_score(self, skill: Skill, keywords: Set[str]) -> float:
        """Calculate relevance score for a skill based on keywords."""
        score = 0.0

        # Check tags
        tags = set(t.lower() for t in skill.definition.metadata.tags)
        tag_matches = len(tags & keywords)
        score += tag_matches * 0.3

        # Check expertise areas
        expertise = set(
            e.lower() for e in skill.definition.role.expertise_areas
        )
        expertise_matches = len(expertise & keywords)
        score += expertise_matches * 0.25

        # Check role title and description
        role_words = set(skill.definition.role.title.lower().split())
        role_words.update(skill.definition.role.description.lower().split())
        role_matches = len(role_words & keywords)
        score += role_matches * 0.1

        # Check responsibilities
        resp_words = set()
        for r in skill.definition.responsibilities.primary:
            resp_words.update(r.lower().split())
        resp_matches = len(resp_words & keywords)
        score += resp_matches * 0.1

        # Apply priority weight
        priority_weight = self._priority_weights.get(
            skill.definition.metadata.priority, 0.5
        )
        score *= priority_weight

        return score

    async def get_loading_order(
        self,
        skills: List[Skill],
        context: Optional[str] = None,
    ) -> List[Skill]:
        """
        Get the optimal loading order for skills.

        Args:
            skills: List of skills to order
            context: Optional context for context-aware ordering

        Returns:
            Ordered list of skills
        """
        if context:
            keywords = self._extract_keywords(context)
            scored = [
                (skill, self._calculate_relevance_score(skill, keywords))
                for skill in skills
            ]
            scored.sort(key=lambda x: (-x[1], self._priority_weights.get(x[0].definition.metadata.priority, 0.5)))
            return [s[0] for s in scored]
        else:
            # Sort by priority only
            priority_order = {
                SkillPriority.CRITICAL: 0,
                SkillPriority.HIGH: 1,
                SkillPriority.MEDIUM: 2,
                SkillPriority.LOW: 3,
                SkillPriority.OPTIONAL: 4,
            }
            return sorted(
                skills,
                key=lambda s: priority_order.get(s.definition.metadata.priority, 5)
            )

    async def estimate_total_tokens(self, skills: List[Skill]) -> int:
        """
        Estimate total token count for a list of skills.

        Args:
            skills: List of skills

        Returns:
            Total estimated tokens
        """
        return sum(
            skill.definition.metadata.token_count or self._estimate_tokens(skill)
            for skill in skills
        )
