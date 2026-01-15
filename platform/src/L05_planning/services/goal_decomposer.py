"""
L05 Planning Layer - Goal Decomposer Service.

Decomposes high-level goals into executable task plans using hybrid strategy:
1. Check cache
2. Try template matching
3. Fall back to LLM decomposition via L04
"""

import json
import hashlib
import hmac
import logging
from typing import Optional, List
from uuid import uuid4
from datetime import datetime

from ..models import (
    Goal,
    Task,
    ExecutionPlan,
    TaskType,
    TaskDependency,
    DependencyType,
    PlanMetadata,
    PlanStatus,
    PlanningError,
    ErrorCode,
)
from ..templates import TemplateRegistry
from .plan_cache import PlanCache

logger = logging.getLogger(__name__)


class GoalDecomposer:
    """
    Decomposes goals into execution plans.

    Uses hybrid strategy: cache → template → LLM
    """

    def __init__(
        self,
        cache: Optional[PlanCache] = None,
        template_registry: Optional[TemplateRegistry] = None,
        gateway_client=None,  # L04 ModelGateway
        hmac_secret: str = "L05-planning-secret-key",  # Should come from vault
        max_goal_length: int = 100_000,
        default_strategy: str = "hybrid",
    ):
        """
        Initialize Goal Decomposer.

        Args:
            cache: Plan cache instance
            template_registry: Template registry instance
            gateway_client: L04 Model Gateway client
            hmac_secret: Secret key for plan signing
            max_goal_length: Maximum goal text length
            default_strategy: Default decomposition strategy
        """
        self.cache = cache or PlanCache()
        self.template_registry = template_registry or TemplateRegistry()
        self.gateway_client = gateway_client
        self.hmac_secret = hmac_secret.encode()
        self.max_goal_length = max_goal_length
        self.default_strategy = default_strategy

        # Load default templates
        if not self.template_registry.get_all_templates():
            self.template_registry.load_default_templates()

        # Metrics
        self.decompositions_total = 0
        self.cache_hits = 0
        self.template_decompositions = 0
        self.llm_decompositions = 0
        self.decomposition_failures = 0

        logger.info(f"GoalDecomposer initialized with strategy: {default_strategy}")

    async def decompose(self, goal: Goal) -> ExecutionPlan:
        """
        Decompose goal into execution plan.

        Full pipeline:
        1. Validate goal input
        2. Check plan cache
        3. Try template matching (if confidence > 0.85)
        4. Fall back to LLM decomposition
        5. Build execution plan
        6. Sign plan
        7. Cache plan
        8. Return plan

        Args:
            goal: Goal to decompose

        Returns:
            ExecutionPlan with tasks and dependencies

        Raises:
            PlanningError: On decomposition failure
        """
        start_time = datetime.utcnow()
        self.decompositions_total += 1

        try:
            # Step 1: Validate goal
            is_valid, error_msg = goal.validate()
            if not is_valid:
                raise PlanningError.from_code(
                    ErrorCode.E5004,
                    details={"goal_id": goal.goal_id, "error": error_msg},
                )

            # Step 2: Check cache
            cached_plan = await self.cache.get(goal.goal_text)
            if cached_plan:
                self.cache_hits += 1
                logger.info(f"Cache hit for goal {goal.goal_id}")
                cached_plan.metadata.cache_hit = True
                return cached_plan

            # Step 3: Determine strategy
            strategy = goal.decomposition_strategy or self.default_strategy

            # Step 4: Decompose using strategy
            if strategy == "hybrid":
                plan = await self._decompose_hybrid(goal)
            elif strategy == "llm":
                plan = await self._decompose_llm(goal)
            elif strategy == "template":
                plan = await self._decompose_template(goal)
            else:
                raise PlanningError.from_code(
                    ErrorCode.E5103,
                    details={"strategy": strategy},
                    recovery_suggestion="Use 'hybrid', 'llm', or 'template'",
                )

            # Step 5: Sign plan
            plan.signature = self._sign_plan(plan)

            # Step 6: Calculate metrics
            latency_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
            plan.metadata.decomposition_latency_ms = latency_ms

            # Step 7: Cache plan
            await self.cache.set(goal.goal_text, plan)

            logger.info(
                f"Decomposed goal {goal.goal_id} into {len(plan.tasks)} tasks "
                f"({plan.metadata.decomposition_strategy}) in {latency_ms:.0f}ms"
            )

            return plan

        except PlanningError:
            self.decomposition_failures += 1
            raise
        except Exception as e:
            self.decomposition_failures += 1
            logger.error(f"Decomposition failed for goal {goal.goal_id}: {e}")
            raise PlanningError.from_code(
                ErrorCode.E5100,
                details={"goal_id": goal.goal_id, "error": str(e)},
            )

    async def _decompose_hybrid(self, goal: Goal) -> ExecutionPlan:
        """
        Hybrid decomposition: Try template first, fall back to LLM.

        Args:
            goal: Goal to decompose

        Returns:
            ExecutionPlan
        """
        # Try template matching
        template_match = self.template_registry.find_similar(goal.goal_text)

        if template_match and template_match.confidence > 0.85:
            logger.info(
                f"Using template '{template_match.template.name}' "
                f"(confidence: {template_match.confidence:.2f})"
            )
            return await self._decompose_from_template(goal, template_match.template, template_match.extracted_params)

        # Fall back to LLM
        logger.info("Template confidence too low, falling back to LLM")
        return await self._decompose_llm(goal)

    async def _decompose_template(self, goal: Goal) -> ExecutionPlan:
        """
        Template-based decomposition.

        Args:
            goal: Goal to decompose

        Returns:
            ExecutionPlan

        Raises:
            PlanningError: If no template matches
        """
        template_match = self.template_registry.find_similar(goal.goal_text)

        if not template_match:
            raise PlanningError.from_code(
                ErrorCode.E5102,
                details={"goal_id": goal.goal_id},
                recovery_suggestion="Try 'hybrid' or 'llm' strategy",
            )

        return await self._decompose_from_template(goal, template_match.template, template_match.extracted_params)

    async def _decompose_from_template(
        self,
        goal: Goal,
        template,
        params: dict,
    ) -> ExecutionPlan:
        """
        Decompose using template.

        Args:
            goal: Goal to decompose
            template: Matched template
            params: Extracted parameters

        Returns:
            ExecutionPlan
        """
        self.template_decompositions += 1

        # Create plan
        plan = ExecutionPlan.create(
            goal_id=goal.goal_id,
            resource_budget=None,  # TODO: Extract from goal constraints
        )

        # Add goal text to params for substitution
        params["goal"] = goal.goal_text

        # Instantiate template into tasks
        tasks = self.template_registry.instantiate_template(
            template,
            plan.plan_id,
            params,
        )

        # Add tasks to plan
        for task in tasks:
            plan.add_task(task)

        # Update metadata
        plan.metadata.decomposition_strategy = "template"
        plan.metadata.tags.append(f"template:{template.template_id}")

        return plan

    async def _decompose_llm(self, goal: Goal) -> ExecutionPlan:
        """
        LLM-based decomposition using L04 Model Gateway.

        Args:
            goal: Goal to decompose

        Returns:
            ExecutionPlan

        Raises:
            PlanningError: If LLM decomposition fails
        """
        self.llm_decompositions += 1

        if not self.gateway_client:
            raise PlanningError.from_code(
                ErrorCode.E5101,
                details={"reason": "No L04 gateway client configured"},
                recovery_suggestion="Initialize GoalDecomposer with gateway_client",
            )

        try:
            # Import L04 models
            from src.L04_model_gateway.models import (
                InferenceRequest,
                LogicalPrompt,
                Message,
                MessageRole,
                ModelRequirements,
            )

            # Build prompt
            system_prompt = """You are a task planning assistant. Your job is to decompose high-level goals into specific, executable tasks.

For each task, provide:
- id: unique identifier
- name: brief task name
- description: detailed description
- type: one of [atomic, compound, tool_call, llm_call]
- dependencies: list of task IDs this depends on
- inputs: required inputs
- timeout_seconds: estimated timeout

Output JSON format:
{
  "tasks": [
    {
      "id": "task-1",
      "name": "Task name",
      "description": "Task description",
      "type": "atomic",
      "dependencies": [],
      "inputs": {},
      "timeout_seconds": 60
    }
  ]
}"""

            user_prompt = f"Decompose this goal into executable tasks:\n\n{goal.goal_text}"

            # Create inference request
            request = InferenceRequest.create(
                agent_did=goal.agent_did,
                messages=[
                    Message(role=MessageRole.SYSTEM, content=system_prompt),
                    Message(role=MessageRole.USER, content=user_prompt),
                ],
                temperature=0.3,  # Lower temperature for structured output
                max_tokens=2000,
                capabilities=[],  # InferenceRequest.create() will build ModelRequirements internally
            )

            # Execute via L04 gateway
            response = await self.gateway_client.execute(request)

            # Parse response
            plan = self._parse_llm_response(goal, response.content, response)

            # Update metadata
            plan.metadata.decomposition_strategy = "llm"
            plan.metadata.llm_provider = response.provider_id if hasattr(response, 'provider_id') else None
            plan.metadata.llm_model = response.model_id if hasattr(response, 'model_id') else None
            plan.metadata.total_tokens_used = response.usage.total_tokens if hasattr(response, 'usage') else 0

            return plan

        except Exception as e:
            logger.error(f"LLM decomposition failed: {e}")
            raise PlanningError.from_code(
                ErrorCode.E5101,
                details={"goal_id": goal.goal_id, "error": str(e)},
            )

    def _parse_llm_response(self, goal: Goal, content: str, response) -> ExecutionPlan:
        """
        Parse LLM response into ExecutionPlan.

        Args:
            goal: Original goal
            content: LLM response content
            response: Full inference response

        Returns:
            ExecutionPlan

        Raises:
            PlanningError: If parsing fails
        """
        try:
            # Try to extract JSON from response
            # Look for JSON block
            if "```json" in content:
                json_start = content.find("```json") + 7
                json_end = content.find("```", json_start)
                json_str = content[json_start:json_end].strip()
            elif "```" in content:
                json_start = content.find("```") + 3
                json_end = content.find("```", json_start)
                json_str = content[json_start:json_end].strip()
            else:
                # Assume entire content is JSON
                json_str = content.strip()

            # Parse JSON
            data = json.loads(json_str)

            if "tasks" not in data:
                raise ValueError("LLM response missing 'tasks' field")

            # Create plan
            plan = ExecutionPlan.create(goal_id=goal.goal_id)

            # Build tasks
            task_id_map = {}  # Map LLM task IDs to actual UUIDs

            for task_data in data["tasks"]:
                llm_task_id = task_data.get("id", str(uuid4()))
                actual_task_id = str(uuid4())
                task_id_map[llm_task_id] = actual_task_id

                task = Task.create(
                    plan_id=plan.plan_id,
                    name=task_data.get("name", "Unnamed task"),
                    description=task_data.get("description", ""),
                    task_type=TaskType(task_data.get("type", "atomic")),
                    inputs=task_data.get("inputs", {}),
                    timeout_seconds=task_data.get("timeout_seconds", 300),
                    tool_name=task_data.get("tool_name"),
                    llm_prompt=task_data.get("llm_prompt"),
                )

                task.task_id = actual_task_id

                # Parse dependencies
                dep_ids = task_data.get("dependencies", [])
                for dep_id in dep_ids:
                    if dep_id in task_id_map:
                        task.dependencies.append(
                            TaskDependency(
                                task_id=task_id_map[dep_id],
                                dependency_type=DependencyType.BLOCKING,
                            )
                        )

                plan.add_task(task)

            return plan

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response as JSON: {e}")
            raise PlanningError.from_code(
                ErrorCode.E5106,
                details={"error": str(e), "content": content[:200]},
            )
        except Exception as e:
            logger.error(f"Failed to parse LLM response: {e}")
            raise PlanningError.from_code(
                ErrorCode.E5106,
                details={"error": str(e)},
            )

    def _sign_plan(self, plan: ExecutionPlan) -> str:
        """
        Sign plan with HMAC-SHA256.

        Args:
            plan: Plan to sign

        Returns:
            Signature string (hex)
        """
        # Build message to sign
        message_parts = [
            plan.plan_id,
            plan.goal_id,
            json.dumps([t.task_id for t in plan.tasks], sort_keys=True),
            json.dumps(plan.dependency_graph, sort_keys=True),
            str(int(plan.created_at.timestamp() * 1000)),
        ]
        message = "|".join(message_parts).encode()

        # Compute HMAC-SHA256
        signature = hmac.new(self.hmac_secret, message, hashlib.sha256).hexdigest()

        return signature

    def verify_plan_signature(self, plan: ExecutionPlan) -> bool:
        """
        Verify plan signature.

        Args:
            plan: Plan to verify

        Returns:
            True if signature valid, False otherwise
        """
        if not plan.signature:
            return False

        expected_signature = self._sign_plan(plan)
        return hmac.compare_digest(plan.signature, expected_signature)

    def get_stats(self) -> dict:
        """Get decomposer statistics."""
        return {
            "decompositions_total": self.decompositions_total,
            "cache_hits": self.cache_hits,
            "cache_hit_rate": self.cache_hits / max(1, self.decompositions_total),
            "template_decompositions": self.template_decompositions,
            "llm_decompositions": self.llm_decompositions,
            "decomposition_failures": self.decomposition_failures,
            "failure_rate": self.decomposition_failures / max(1, self.decompositions_total),
        }
