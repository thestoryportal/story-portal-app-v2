"""
Role Dispatcher Service for L13 Role Management Layer.

Handles task-to-role mapping and dispatch decisions, coordinating with
the ClassificationEngine and RoleRegistry to assign optimal roles.
"""

import logging
from typing import List, Optional, Dict, Any
from uuid import UUID, uuid4
from datetime import datetime

from ..models import (
    Role,
    RoleMatch,
    RoleType,
    TaskRequirements,
    ClassificationResult,
    DispatchResult,
    RoleContext,
)
from .role_registry import RoleRegistry
from .classification_engine import ClassificationEngine
from .role_context_builder import RoleContextBuilder

logger = logging.getLogger(__name__)


class RoleDispatcher:
    """
    Dispatcher service for assigning tasks to roles.

    Coordinates between the RoleRegistry, ClassificationEngine, and
    RoleContextBuilder to make optimal dispatch decisions.
    """

    def __init__(
        self,
        role_registry: RoleRegistry,
        classification_engine: Optional['ClassificationEngine'] = None,
        context_builder: Optional['RoleContextBuilder'] = None,
    ):
        """
        Initialize the role dispatcher.

        Args:
            role_registry: The role registry for role lookups
            classification_engine: Engine for human/AI classification
            context_builder: Builder for assembling role contexts
        """
        self.role_registry = role_registry
        self.classification_engine = classification_engine
        self.context_builder = context_builder

        # Track dispatch history for analytics
        self._dispatch_history: List[DispatchResult] = []
        self._max_history = 1000

    async def dispatch_task(
        self,
        task_id: str,
        requirements: TaskRequirements,
        preferred_role_id: Optional[UUID] = None,
        force_role_type: Optional[RoleType] = None,
        build_context: bool = True,
    ) -> DispatchResult:
        """
        Dispatch a task to the best matching role.

        Args:
            task_id: Unique task identifier
            requirements: Task requirements for matching
            preferred_role_id: Optional preferred role to use
            force_role_type: Force a specific role type classification
            build_context: Whether to build full context

        Returns:
            DispatchResult with assigned role and context
        """
        logger.info(f"Dispatching task {task_id}")

        # Step 1: Classify the task
        classification = await self._classify_task(
            task_id=task_id,
            requirements=requirements,
            force_role_type=force_role_type,
        )

        # Step 2: Find matching roles
        if preferred_role_id:
            role = await self.role_registry.get_role(preferred_role_id)
            if role:
                matches = [RoleMatch(
                    role=role,
                    score=1.0,
                    matching_skills=[],
                    matching_keywords=[],
                    confidence=1.0,
                    reasoning="Preferred role specified by caller"
                )]
            else:
                logger.warning(f"Preferred role {preferred_role_id} not found, searching")
                matches = await self.role_registry.dispatch_for_task(requirements)
        else:
            # Apply role type filter from classification
            req_dict = requirements.model_dump()
            req_dict["role_type_preference"] = classification.classification
            requirements_with_type = TaskRequirements(**req_dict)
            matches = await self.role_registry.dispatch_for_task(requirements_with_type)

            # Fall back to no role_type filter if no matches found
            if not matches:
                logger.info(f"No roles found for type {classification.classification}, searching all types")
                matches = await self.role_registry.dispatch_for_task(requirements)

        if not matches:
            raise ValueError(f"No matching roles found for task {task_id}")

        # Step 3: Select best role
        selected_match = matches[0]
        selected_role = selected_match.role

        # Update classification with recommended roles
        classification.recommended_roles = matches[:3]

        # Step 4: Build context if requested
        if build_context and self.context_builder:
            context = await self.context_builder.build_context(
                role=selected_role,
                task_requirements=requirements,
            )
        else:
            # Create minimal context
            context = RoleContext(
                role=selected_role,
                system_prompt=f"You are acting as: {selected_role.name}",
                skill_context=", ".join(s.name for s in selected_role.skills),
                token_count=100,
                token_budget=selected_role.token_budget,
                budget_utilization=100 / selected_role.token_budget,
            )

        # Step 5: Create dispatch result
        result = DispatchResult(
            task_id=task_id,
            assigned_role=selected_role,
            classification=classification,
            context=context,
            dispatch_time=datetime.utcnow(),
            metadata={
                "match_score": selected_match.score,
                "match_confidence": selected_match.confidence,
                "candidates_considered": len(matches),
            }
        )

        # Track in history
        self._add_to_history(result)

        logger.info(
            f"Dispatched task {task_id} to role {selected_role.name} "
            f"(type={classification.classification.value}, score={selected_match.score:.2f})"
        )

        return result

    async def _classify_task(
        self,
        task_id: str,
        requirements: TaskRequirements,
        force_role_type: Optional[RoleType] = None,
    ) -> ClassificationResult:
        """
        Classify a task for routing.

        Args:
            task_id: Task identifier
            requirements: Task requirements
            force_role_type: Force a specific classification

        Returns:
            ClassificationResult
        """
        if force_role_type:
            return ClassificationResult(
                task_id=task_id,
                classification=force_role_type,
                confidence=1.0,
                reasoning="Classification forced by caller",
                factors={"forced": 1.0},
                human_oversight_required=force_role_type == RoleType.HUMAN_PRIMARY,
            )

        if self.classification_engine:
            return await self.classification_engine.classify_task(
                task_id=task_id,
                requirements=requirements,
            )

        # Default classification logic
        return await self._default_classification(task_id, requirements)

    async def _default_classification(
        self,
        task_id: str,
        requirements: TaskRequirements,
    ) -> ClassificationResult:
        """
        Default classification when no engine is available.

        Uses heuristics based on task complexity and keywords.
        """
        factors: Dict[str, float] = {}

        # Complexity factor
        complexity_scores = {"low": 0.2, "medium": 0.5, "high": 0.8}
        factors["complexity"] = complexity_scores.get(requirements.complexity, 0.5)

        # Keywords that suggest human involvement
        human_keywords = {
            "decision", "approve", "review", "sensitive", "confidential",
            "strategic", "creative", "negotiate", "interview", "counsel"
        }
        ai_keywords = {
            "analyze", "generate", "automate", "process", "calculate",
            "transform", "extract", "summarize", "classify", "monitor"
        }

        task_text = requirements.task_description.lower()
        keywords_all = requirements.keywords + requirements.required_skills

        human_score = sum(1 for k in human_keywords if k in task_text or k in keywords_all)
        ai_score = sum(1 for k in ai_keywords if k in task_text or k in keywords_all)

        factors["human_keywords"] = min(human_score * 0.15, 0.45)
        factors["ai_keywords"] = min(ai_score * 0.15, 0.45)

        # Urgency factor - urgent tasks might benefit from AI speed
        urgency_scores = {"low": 0.1, "normal": 0.3, "high": 0.5, "critical": 0.7}
        factors["urgency_ai_boost"] = urgency_scores.get(requirements.urgency, 0.3)

        # Calculate final scores
        human_total = factors["complexity"] * 0.3 + factors["human_keywords"]
        ai_total = (1 - factors["complexity"]) * 0.2 + factors["ai_keywords"] + factors["urgency_ai_boost"] * 0.2

        # Determine classification
        if human_total > ai_total + 0.2:
            classification = RoleType.HUMAN_PRIMARY
            confidence = min((human_total - ai_total) / 0.5, 0.95)
        elif ai_total > human_total + 0.2:
            classification = RoleType.AI_PRIMARY
            confidence = min((ai_total - human_total) / 0.5, 0.95)
        else:
            classification = RoleType.HYBRID
            confidence = 1 - abs(human_total - ai_total)

        return ClassificationResult(
            task_id=task_id,
            classification=classification,
            confidence=confidence,
            reasoning=f"Heuristic classification based on complexity ({requirements.complexity}) "
                     f"and keyword analysis (human={human_score}, ai={ai_score})",
            factors=factors,
            human_oversight_required=classification in [RoleType.HUMAN_PRIMARY, RoleType.HYBRID],
        )

    async def batch_dispatch(
        self,
        tasks: List[Dict[str, Any]],
        build_contexts: bool = True,
    ) -> List[DispatchResult]:
        """
        Dispatch multiple tasks in batch.

        Args:
            tasks: List of task dicts with 'task_id' and 'requirements'
            build_contexts: Whether to build full contexts

        Returns:
            List of DispatchResult objects
        """
        results = []

        for task in tasks:
            try:
                task_id = task.get("task_id", str(uuid4()))
                requirements = TaskRequirements(**task.get("requirements", {}))

                result = await self.dispatch_task(
                    task_id=task_id,
                    requirements=requirements,
                    preferred_role_id=task.get("preferred_role_id"),
                    force_role_type=task.get("force_role_type"),
                    build_context=build_contexts,
                )
                results.append(result)

            except Exception as e:
                logger.error(f"Failed to dispatch task: {e}")
                # Continue with other tasks

        return results

    async def reassign_task(
        self,
        task_id: str,
        from_role_id: UUID,
        reason: str,
        new_requirements: Optional[TaskRequirements] = None,
    ) -> DispatchResult:
        """
        Reassign a task to a different role.

        Args:
            task_id: Task identifier
            from_role_id: Current role ID
            reason: Reason for reassignment
            new_requirements: Updated requirements (optional)

        Returns:
            New DispatchResult
        """
        logger.info(f"Reassigning task {task_id} from role {from_role_id}: {reason}")

        # Find the original dispatch
        original = None
        for dispatch in self._dispatch_history:
            if dispatch.task_id == task_id:
                original = dispatch
                break

        if not original and not new_requirements:
            raise ValueError(f"Cannot reassign task {task_id}: no history and no new requirements")

        requirements = new_requirements or TaskRequirements(
            task_description=f"Reassigned task: {reason}",
            required_skills=[],
            keywords=[],
        )

        # Exclude the current role from consideration
        matches = await self.role_registry.dispatch_for_task(requirements, top_k=5)
        matches = [m for m in matches if m.role.id != from_role_id]

        if not matches:
            raise ValueError(f"No alternative roles found for task {task_id}")

        # Dispatch to the best alternative
        result = await self.dispatch_task(
            task_id=task_id,
            requirements=requirements,
            preferred_role_id=matches[0].role.id,
        )

        result.metadata["reassigned"] = True
        result.metadata["reassignment_reason"] = reason
        result.metadata["previous_role_id"] = str(from_role_id)

        return result

    def _add_to_history(self, result: DispatchResult) -> None:
        """Add dispatch result to history, maintaining max size."""
        self._dispatch_history.append(result)
        if len(self._dispatch_history) > self._max_history:
            self._dispatch_history = self._dispatch_history[-self._max_history:]

    async def get_dispatch_statistics(self) -> Dict[str, Any]:
        """
        Get dispatch statistics.

        Returns:
            Dictionary of statistics
        """
        if not self._dispatch_history:
            return {
                "total_dispatches": 0,
                "by_classification": {},
                "by_role": {},
                "average_confidence": 0,
            }

        by_classification: Dict[str, int] = {}
        by_role: Dict[str, int] = {}
        total_confidence = 0.0

        for dispatch in self._dispatch_history:
            # By classification
            cls = dispatch.classification.classification.value
            by_classification[cls] = by_classification.get(cls, 0) + 1

            # By role
            role_name = dispatch.assigned_role.name
            by_role[role_name] = by_role.get(role_name, 0) + 1

            # Confidence
            total_confidence += dispatch.classification.confidence

        return {
            "total_dispatches": len(self._dispatch_history),
            "by_classification": by_classification,
            "by_role": by_role,
            "average_confidence": total_confidence / len(self._dispatch_history),
            "recent_dispatches": len([
                d for d in self._dispatch_history
                if (datetime.utcnow() - d.dispatch_time).total_seconds() < 3600
            ]),
        }
