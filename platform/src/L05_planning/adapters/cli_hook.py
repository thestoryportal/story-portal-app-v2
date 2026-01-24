"""
L05 Planning Layer - CLI Plan Mode Hook.

Post-approval hook for CLI plan mode that offers execution path choices.
Implements Gate 2 of the two-gate approval flow.

Gate 1: User approves plan content (handled by CLI)
Gate 2: User chooses execution method (Traditional/L05/Hybrid)
"""

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Dict, Any, List

from .cli_plan_adapter import CLIPlanAdapter, ParsedPlan
from ..models import ExecutionPlan, Goal
from ..services.planning_service import PlanningService

logger = logging.getLogger(__name__)


class ExecutionChoice(str, Enum):
    """User's choice for plan execution method."""

    TRADITIONAL = "traditional"  # Claude implements step-by-step
    L05_AUTOMATED = "l05_automated"  # Full L05 stack execution
    HYBRID = "hybrid"  # L05 handles simple steps, Claude handles complex


@dataclass
class ExecutionOption:
    """Represents one execution option for Gate 2."""

    id: ExecutionChoice
    label: str
    description: str
    recommended: bool = False


@dataclass
class ExecutionAnalysis:
    """Analysis of plan for execution options presentation."""

    total_steps: int
    parallel_phases: int
    parallel_groups: List[List[str]]
    parallelizable_steps: int
    sequential_steps: int
    inferred_capabilities: List[str]
    file_targets: List[str]
    estimated_speedup: float

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ExecutionAnalysis":
        """Create from dictionary."""
        return cls(
            total_steps=data.get("total_steps", 0),
            parallel_phases=data.get("parallel_phases", 0),
            parallel_groups=data.get("parallel_groups", []),
            parallelizable_steps=data.get("parallelizable_steps", 0),
            sequential_steps=data.get("sequential_steps", 0),
            inferred_capabilities=data.get("inferred_capabilities", []),
            file_targets=data.get("file_targets", []),
            estimated_speedup=data.get("estimated_speedup", 1.0),
        )


@dataclass
class Gate2Response:
    """Response from Gate 2 (execution method choice)."""

    options: List[ExecutionOption]
    analysis: ExecutionAnalysis
    parsed_plan: ParsedPlan
    execution_plan: ExecutionPlan
    goal: Goal
    recommended_choice: ExecutionChoice = ExecutionChoice.L05_AUTOMATED


@dataclass
class HybridExecutionResult:
    """Result of hybrid execution routing."""

    l05_steps: List[str]  # Task IDs for L05 execution
    claude_steps: List[str]  # Task IDs for Claude implementation
    l05_tasks: List[Dict[str, Any]]  # Full task details for L05
    claude_tasks: List[Dict[str, Any]]  # Full task details for Claude
    message: str


class CLIPlanModeHook:
    """
    Post-approval hook for CLI plan mode.

    After user approves a plan (Gate 1), this hook:
    1. Parses the plan
    2. Analyzes it for execution options
    3. Presents Gate 2 choices (Traditional/L05/Hybrid)
    4. Executes based on user's choice

    Usage:
        hook = CLIPlanModeHook(adapter, planning_service)

        # After plan approval (Gate 1)
        response = hook.on_plan_approved(plan_markdown)

        # Present options to user, get choice

        # Execute based on choice
        result = await hook.execute_choice(
            choice=ExecutionChoice.L05_AUTOMATED,
            execution_plan=response.execution_plan,
            goal=response.goal,
        )
    """

    # Complexity thresholds for hybrid routing
    HIGH_COMPLEXITY_DESCRIPTION_LENGTH = 500
    HIGH_COMPLEXITY_FILE_COUNT = 5
    MEDIUM_COMPLEXITY_DESCRIPTION_LENGTH = 200
    MEDIUM_COMPLEXITY_FILE_COUNT = 2

    def __init__(
        self,
        adapter: CLIPlanAdapter,
        planning_service: Optional[PlanningService] = None,
        complexity_threshold: str = "medium",
    ):
        """
        Initialize CLI Plan Mode Hook.

        Args:
            adapter: CLIPlanAdapter instance
            planning_service: PlanningService for L05 execution
            complexity_threshold: Threshold for hybrid routing ("low", "medium", "high")
        """
        self.adapter = adapter
        self.planning_service = planning_service or adapter.planning_service
        self.complexity_threshold = complexity_threshold

        logger.info("CLIPlanModeHook initialized")

    def on_plan_approved(
        self,
        plan_markdown: str,
        plan_file_path: Optional[str] = None,
    ) -> Gate2Response:
        """
        Called when user approves CLI plan mode plan (Gate 1 complete).

        Parses plan, analyzes it, and returns execution options for Gate 2.

        Args:
            plan_markdown: Approved plan markdown content
            plan_file_path: Optional path to plan file

        Returns:
            Gate2Response with options and analysis
        """
        # Parse plan
        parsed = self.adapter.parse_plan_markdown(plan_markdown)

        # Convert to L05 structures
        goal = self.adapter.to_goal(parsed)
        execution_plan = self.adapter.to_execution_plan(parsed, goal=goal)

        # Analyze for execution options
        analysis_dict = self.adapter.analyze_plan(parsed, execution_plan)
        analysis = ExecutionAnalysis.from_dict(analysis_dict)

        # Build execution options
        options = self._build_execution_options(analysis)

        # Determine recommended choice
        recommended = self._recommend_choice(analysis)

        logger.info(
            f"Plan approved, offering {len(options)} execution options. "
            f"Recommended: {recommended.value}"
        )

        return Gate2Response(
            options=options,
            analysis=analysis,
            parsed_plan=parsed,
            execution_plan=execution_plan,
            goal=goal,
            recommended_choice=recommended,
        )

    async def execute_choice(
        self,
        choice: ExecutionChoice,
        execution_plan: ExecutionPlan,
        goal: Goal,
        agent_did: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Execute based on user's Gate 2 choice.

        Args:
            choice: User's execution method choice
            execution_plan: ExecutionPlan from Gate 2 response
            goal: Goal from Gate 2 response
            agent_did: Optional agent DID for execution

        Returns:
            Execution result dictionary
        """
        logger.info(f"Executing plan via {choice.value} method")

        if choice == ExecutionChoice.L05_AUTOMATED:
            return await self._execute_l05(execution_plan, agent_did)

        elif choice == ExecutionChoice.HYBRID:
            return await self._execute_hybrid(execution_plan, goal, agent_did)

        else:  # TRADITIONAL
            return self._prepare_traditional(execution_plan, goal)

    async def _execute_l05(
        self,
        plan: ExecutionPlan,
        agent_did: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Execute plan fully via L05 stack."""
        if not self.planning_service:
            raise RuntimeError("PlanningService not configured for L05 execution")

        result = await self.planning_service.execute_plan_direct(
            plan,
            agent_did=agent_did,
        )

        return {
            "method": "l05_automated",
            "status": "executed",
            "plan_id": plan.plan_id,
            "result": result,
        }

    async def _execute_hybrid(
        self,
        plan: ExecutionPlan,
        goal: Goal,
        agent_did: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Hybrid execution: route simple steps to L05, complex to Claude.

        Returns information about which steps go where.
        """
        routing = self._route_for_hybrid(plan)

        # If we have L05 steps and a planning service, execute them
        l05_result = None
        if routing.l05_tasks and self.planning_service:
            # Create a sub-plan with just L05 tasks
            # For now, return routing info - full implementation would
            # create and execute a filtered plan
            logger.info(
                f"Hybrid: {len(routing.l05_tasks)} steps to L05, "
                f"{len(routing.claude_tasks)} to Claude"
            )

        return {
            "method": "hybrid",
            "status": "routed",
            "plan_id": plan.plan_id,
            "goal_id": goal.goal_id,
            "routing": {
                "l05_step_count": len(routing.l05_tasks),
                "claude_step_count": len(routing.claude_tasks),
                "l05_tasks": routing.l05_tasks,
                "claude_tasks": routing.claude_tasks,
            },
            "message": routing.message,
            "l05_result": l05_result,
        }

    def _prepare_traditional(
        self,
        plan: ExecutionPlan,
        goal: Goal,
    ) -> Dict[str, Any]:
        """
        Prepare for traditional Claude implementation.

        Returns structured information for Claude to implement step-by-step.
        """
        tasks_info = []
        for task in plan.tasks:
            tasks_info.append({
                "task_id": task.task_id,
                "name": task.name,
                "description": task.description,
                "file_targets": task.inputs.get("file_targets", []),
                "dependencies": [dep.task_id for dep in task.dependencies],
            })

        return {
            "method": "traditional",
            "status": "ready_for_implementation",
            "plan_id": plan.plan_id,
            "goal_id": goal.goal_id,
            "goal_text": goal.goal_text,
            "tasks": tasks_info,
            "task_count": len(tasks_info),
            "message": (
                f"Ready for traditional implementation. "
                f"{len(tasks_info)} tasks to implement sequentially."
            ),
        }

    def _build_execution_options(
        self,
        analysis: ExecutionAnalysis,
    ) -> List[ExecutionOption]:
        """Build execution options for Gate 2 presentation."""
        options = []

        # Traditional option
        options.append(ExecutionOption(
            id=ExecutionChoice.TRADITIONAL,
            label="Traditional (Claude implements)",
            description=f"I implement {analysis.total_steps} steps sequentially",
        ))

        # L05 Automated option
        speedup_note = ""
        if analysis.estimated_speedup > 1.5:
            speedup_note = f" (~{analysis.estimated_speedup:.1f}x faster)"

        options.append(ExecutionOption(
            id=ExecutionChoice.L05_AUTOMATED,
            label="L05 Automated Execution",
            description=(
                f"{analysis.total_steps} steps in {analysis.parallel_phases} "
                f"parallel phases, auto-recovery, multi-agent{speedup_note}"
            ),
        ))

        # Hybrid option (only if there's a mix of complexity)
        if analysis.parallelizable_steps > 0 and analysis.sequential_steps > 0:
            options.append(ExecutionOption(
                id=ExecutionChoice.HYBRID,
                label="Hybrid (Claude + L05)",
                description=(
                    f"L05 handles {analysis.parallelizable_steps} simple steps, "
                    f"I handle {analysis.sequential_steps} complex ones"
                ),
            ))

        return options

    def _recommend_choice(self, analysis: ExecutionAnalysis) -> ExecutionChoice:
        """Determine recommended execution choice based on analysis."""
        # Recommend L05 if:
        # - Multiple parallel phases (good parallelization potential)
        # - More than 3 steps (worth the overhead)
        # - Speedup > 1.3

        if analysis.total_steps <= 2:
            return ExecutionChoice.TRADITIONAL

        if analysis.parallel_phases > 1 and analysis.estimated_speedup > 1.3:
            return ExecutionChoice.L05_AUTOMATED

        if analysis.parallelizable_steps > analysis.sequential_steps:
            return ExecutionChoice.L05_AUTOMATED

        # If mixed complexity, recommend hybrid
        if (
            analysis.parallelizable_steps > 0
            and analysis.sequential_steps > 0
            and analysis.total_steps > 4
        ):
            return ExecutionChoice.HYBRID

        return ExecutionChoice.TRADITIONAL

    def _route_for_hybrid(self, plan: ExecutionPlan) -> HybridExecutionResult:
        """
        Route tasks for hybrid execution.

        Simple/parallelizable → L05
        Complex → Claude
        """
        l05_tasks: List[Dict[str, Any]] = []
        claude_tasks: List[Dict[str, Any]] = []

        for task in plan.tasks:
            complexity = self._assess_task_complexity(task)
            task_info = {
                "task_id": task.task_id,
                "name": task.name,
                "description": task.description,
                "complexity": complexity,
                "file_targets": task.inputs.get("file_targets", []),
            }

            if complexity == "low":
                l05_tasks.append(task_info)
            else:
                claude_tasks.append(task_info)

        return HybridExecutionResult(
            l05_steps=[t["task_id"] for t in l05_tasks],
            claude_steps=[t["task_id"] for t in claude_tasks],
            l05_tasks=l05_tasks,
            claude_tasks=claude_tasks,
            message=(
                f"L05 will handle {len(l05_tasks)} simple steps automatically. "
                f"I'll implement {len(claude_tasks)} complex steps with you."
            ),
        )

    def _assess_task_complexity(self, task) -> str:
        """Assess task complexity for hybrid routing."""
        desc_length = len(task.description)
        file_count = len(task.inputs.get("file_targets", []))
        capabilities = task.metadata.get("capabilities", [])

        # High complexity indicators
        if desc_length > self.HIGH_COMPLEXITY_DESCRIPTION_LENGTH:
            return "high"
        if file_count > self.HIGH_COMPLEXITY_FILE_COUNT:
            return "high"
        if "general" in capabilities and len(capabilities) == 1:
            # Only "general" capability means we couldn't infer specifics
            return "high"

        # Medium complexity
        if desc_length > self.MEDIUM_COMPLEXITY_DESCRIPTION_LENGTH:
            return "medium"
        if file_count > self.MEDIUM_COMPLEXITY_FILE_COUNT:
            return "medium"

        return "low"

    def format_gate2_prompt(self, response: Gate2Response) -> str:
        """
        Format Gate 2 options for display to user.

        Returns a formatted string presenting execution options.
        """
        lines = [
            "## Execution Method",
            "",
            "How should this plan be executed?",
            "",
        ]

        for option in response.options:
            marker = "●" if option.id == response.recommended_choice else "○"
            rec_label = " (Recommended)" if option.id == response.recommended_choice else ""
            lines.append(f"{marker} **{option.label}**{rec_label}")
            lines.append(f"  {option.description}")
            lines.append("")

        # Analysis summary
        analysis = response.analysis
        lines.extend([
            "### Analysis",
            "",
            f"- **Total steps:** {analysis.total_steps}",
            f"- **Parallel phases:** {analysis.parallel_phases}",
            f"- **Estimated speedup:** {analysis.estimated_speedup:.1f}x",
            f"- **Capabilities needed:** {', '.join(analysis.inferred_capabilities)}",
        ])

        if analysis.file_targets:
            lines.append(f"- **Files affected:** {len(analysis.file_targets)}")

        return "\n".join(lines)
