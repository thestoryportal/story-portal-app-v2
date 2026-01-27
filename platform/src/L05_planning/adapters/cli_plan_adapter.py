"""
L05 Planning Layer - CLI Plan Mode Adapter.

Bridges Claude CLI Plan Mode output to L05 Planning Stack.
Converts human-approved markdown plans into structured ExecutionPlans
for automated, resilient execution.

Flow (Approach A - GoalDecomposer as Enricher):
1. CLI Plan Mode creates full plan structure (markdown)
2. User approves plan content (Gate 1)
3. Adapter parses markdown into ParsedPlan
4. Adapter converts to Goal + base ExecutionPlan
5. GoalDecomposer enriches with recovery strategies, parallelization
6. User chooses execution method (Gate 2)
7. Execute via chosen path (Traditional/L05/Hybrid)
"""

import re
import logging
import hashlib
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any, Union
from uuid import uuid4

# Import the new MultiFormatParser for improved format support
from ..parsers.multi_format_parser import MultiFormatParser, ParseError as MultiFormatParseError

from ..models import (
    Goal,
    GoalType,
    GoalStatus,
    GoalConstraints,
    ExecutionPlan,
    PlanMetadata,
    Task,
    TaskType,
    TaskDependency,
    DependencyType,
)

# Lazy imports to avoid circular dependencies and heavy L02/L04 imports
# These are only needed if actually using GoalDecomposer enrichment or PlanningService execution
GoalDecomposer = None
PlanningService = None


def _get_goal_decomposer():
    """Lazy import GoalDecomposer to avoid import cycles."""
    global GoalDecomposer
    if GoalDecomposer is None:
        from ..services.goal_decomposer import GoalDecomposer as GD
        GoalDecomposer = GD
    return GoalDecomposer


def _get_planning_service():
    """Lazy import PlanningService to avoid import cycles."""
    global PlanningService
    if PlanningService is None:
        from ..services.planning_service import PlanningService as PS
        PlanningService = PS
    return PlanningService

logger = logging.getLogger(__name__)


@dataclass
class ParsedStep:
    """Step extracted from CLI plan mode markdown."""

    id: str
    title: str
    description: str = ""
    file_targets: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    parallelizable: bool = True

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "file_targets": self.file_targets,
            "dependencies": self.dependencies,
            "tags": self.tags,
            "parallelizable": self.parallelizable,
        }


@dataclass
class ParsedPlan:
    """Parsed CLI plan mode output."""

    goal: str
    context: str
    steps: List[ParsedStep]
    session_id: str
    approved_at: datetime
    raw_markdown: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "goal": self.goal,
            "context": self.context,
            "steps": [s.to_dict() for s in self.steps],
            "session_id": self.session_id,
            "approved_at": self.approved_at.isoformat(),
        }


class CLIPlanAdapter:
    """
    Bridges CLI Plan Mode output to L05 Planning Stack.

    Converts human-approved markdown plans into structured
    ExecutionPlans for automated, resilient execution.

    Usage:
        adapter = CLIPlanAdapter(goal_decomposer, planning_service)

        # Parse and convert
        parsed = adapter.parse_plan_markdown(markdown)
        execution_plan = adapter.to_execution_plan(parsed)

        # Or full pipeline
        result = await adapter.execute(markdown, dry_run=False)
    """

    # Capability inference mappings
    EXT_TO_CAPABILITY = {
        "py": "python",
        "ts": "typescript",
        "tsx": "react",
        "jsx": "react",
        "js": "javascript",
        "sql": "database",
        "yml": "devops",
        "yaml": "devops",
        "json": "config",
        "md": "documentation",
        "sh": "shell",
        "dockerfile": "docker",
    }

    TAG_TO_CAPABILITY = {
        "database": "database",
        "migration": "database",
        "api": "backend",
        "frontend": "frontend",
        "test": "testing",
        "tests": "testing",
        "deploy": "devops",
        "deployment": "devops",
        "security": "security",
        "auth": "security",
        "authentication": "security",
        "dependencies": "dependencies",
    }

    def __init__(
        self,
        goal_decomposer: Optional[Any] = None,
        planning_service: Optional[Any] = None,
        enrich_with_decomposer: bool = True,
        default_agent_did: str = "did:agent:cli-plan-mode",
    ):
        """
        Initialize CLI Plan Adapter.

        Args:
            goal_decomposer: GoalDecomposer for plan enrichment
            planning_service: PlanningService for execution
            enrich_with_decomposer: Whether to use GoalDecomposer enrichment
            default_agent_did: Default agent DID for created goals
        """
        self.goal_decomposer = goal_decomposer
        self.planning_service = planning_service
        self.enrich = enrich_with_decomposer
        self.default_agent_did = default_agent_did

        # Metrics
        self.plans_parsed = 0
        self.plans_converted = 0
        self.plans_executed = 0
        self.parse_errors = 0

        logger.info("CLIPlanAdapter initialized")

        # Initialize the multi-format parser for improved format support
        self._multi_format_parser = MultiFormatParser()

    def parse_plan_markdown(self, markdown: str) -> Union[ParsedPlan, Dict[str, Any]]:
        """
        Parse CLI plan mode markdown into structured format.

        Supports two formats:

        Format 1 (Simple Steps):
        ```
        # Plan: <goal>

        ## Context
        <context description>

        ## Steps
        1. **Step Title**
           Description of step
           Files: file1.py, file2.py
           Depends: step-1
           Tags: tag1, tag2
        ```

        Format 2 (Phased Plan):
        ```
        # <Goal Title> Plan

        ## Executive Summary
        <context description>

        ## Phase 1: Foundation (Week 1-2)
        ### 1.1 Database Schema
        Description...
        Files to create: ...

        ### 1.2 Service Layer
        ...

        ## Phase 2: Implementation (Week 3-4)
        ...
        ```

        Args:
            markdown: CLI plan mode markdown output

        Returns:
            Dict with plan_id, title, format, steps, and phases (new format)
            OR ParsedPlan with goal, context, and steps (legacy fallback)

        Raises:
            ValueError: If markdown cannot be parsed
        """
        # First, try the new MultiFormatParser for better format support
        try:
            plan = self._multi_format_parser.parse(markdown)

            # Convert to legacy ParsedPlan format for compatibility with to_goal/to_execution_plan
            legacy_steps = [
                ParsedStep(
                    id=s.id,
                    title=s.title,
                    description=s.description,
                    file_targets=s.files,
                    dependencies=s.dependencies,
                )
                for s in plan.steps
            ]

            result = ParsedPlan(
                goal=plan.title,
                context=plan.overview or "",
                steps=legacy_steps,
                session_id=str(uuid4())[:12],
                approved_at=datetime.now(timezone.utc),
                raw_markdown=markdown,
            )

            self.plans_parsed += 1
            logger.info(
                f"Parsed plan (MultiFormat): '{plan.title}' with {len(plan.steps)} steps "
                f"(format: {plan.format_type.value})"
            )
            return result

        except MultiFormatParseError as e:
            logger.debug(f"MultiFormatParser failed, falling back to legacy parser: {e}")
            # Fall through to legacy parser

        # Legacy parser (fallback for formats not yet supported by MultiFormatParser)
        try:
            lines = markdown.strip().split('\n')

            goal = ""
            context = ""
            steps: List[ParsedStep] = []
            current_section: Optional[str] = None
            current_phase: Optional[str] = None
            current_step: Optional[ParsedStep] = None
            step_description_lines: List[str] = []
            phase_count = 0
            step_count = 0
            global_step_counter = 0  # Global counter for unique step IDs

            for i, line in enumerate(lines):
                # Goal header - various formats
                if line.startswith('# Plan:'):
                    goal = line.replace('# Plan:', '').strip()
                elif line.startswith('# ') and not goal:
                    # Alternative: "# Goal Title Plan" or just "# Goal Title"
                    goal = line.replace('# ', '').strip()
                    # Clean up trailing "Plan" or "Implementation Plan"
                    if goal.endswith(' Implementation Plan'):
                        goal = goal.replace(' Implementation Plan', '')
                    elif goal.endswith(' Plan'):
                        goal = goal.replace(' Plan', '')

                # Phase headers (Format 2)
                elif re.match(r'^## Phase \d+:', line):
                    current_section = 'phase'
                    phase_match = re.match(r'^## Phase (\d+):\s*(.+?)(?:\s*\([^)]+\))?$', line)
                    if phase_match:
                        phase_count = int(phase_match.group(1))
                        current_phase = phase_match.group(2).strip()

                # Subsection headers within phases (Format 2) - ### X.Y Title
                elif current_section == 'phase' and line.startswith('### '):
                    # Save previous step
                    if current_step:
                        current_step.description = ' '.join(step_description_lines).strip()
                        steps.append(current_step)
                        step_description_lines = []

                    # Parse subsection: ### 1.1 Title or ### Title
                    subsection_match = re.match(r'^###\s+(\d+\.\d+)?\s*(.+?)$', line)
                    if subsection_match:
                        global_step_counter += 1
                        subsection_title = subsection_match.group(2).strip()

                        current_step = ParsedStep(
                            id=f"step-{global_step_counter}",
                            title=subsection_title,
                            tags=[current_phase.lower().replace(' ', '-')] if current_phase else [],
                        )

                # Section headers (Format 1)
                elif line.startswith('## Context') or line.startswith('## Executive Summary'):
                    current_section = 'context'
                elif line.startswith('## Steps') or line.startswith('## Implementation'):
                    current_section = 'steps'
                elif line.startswith('## ') and current_section not in ['phase', 'steps']:
                    # Other sections like ## Architecture Overview, ## Verification
                    if 'summary' in line.lower() or 'overview' in line.lower():
                        current_section = 'context'
                    else:
                        current_section = 'other'

                # Step parsing (Format 1)
                elif current_section == 'steps':
                    # New numbered step with bold title
                    step_match = re.match(r'^(\d+)\.\s+\*\*(.+?)\*\*', line)
                    if not step_match:
                        # Alternative: numbered without bold
                        step_match = re.match(r'^(\d+)\.\s+(.+?)$', line)

                    if step_match:
                        # Save previous step
                        if current_step:
                            current_step.description = ' '.join(step_description_lines).strip()
                            steps.append(current_step)
                            step_description_lines = []

                        global_step_counter += 1
                        step_title = step_match.group(2).strip()
                        current_step = ParsedStep(
                            id=f"step-{global_step_counter}",
                            title=step_title,
                        )

                    # Step metadata
                    elif current_step:
                        self._parse_step_metadata(line, current_step, step_description_lines)

                # Step metadata for phased plans (Format 2)
                elif current_section == 'phase' and current_step:
                    self._parse_step_metadata(line, current_step, step_description_lines)

                # Context content
                elif current_section == 'context' and line.strip():
                    if not line.startswith('#') and not line.startswith('```'):
                        context += line.strip() + ' '

            # Don't forget last step
            if current_step:
                current_step.description = ' '.join(step_description_lines).strip()
                steps.append(current_step)

            # Detect parallelizable steps (no dependencies = parallelizable)
            for step in steps:
                step.parallelizable = len(step.dependencies) == 0

            # Infer files from descriptions if not explicitly listed
            for step in steps:
                if not step.file_targets:
                    step.file_targets = self._infer_files_from_description(step.description)

            # Generate session ID
            session_id = self._generate_session_id(markdown)

            parsed_plan = ParsedPlan(
                goal=goal or "Unnamed Plan",
                context=context.strip(),
                steps=steps,
                session_id=session_id,
                approved_at=datetime.now(timezone.utc),
                raw_markdown=markdown,
            )

            self.plans_parsed += 1
            logger.info(
                f"Parsed plan: '{goal}' with {len(steps)} steps "
                f"(session: {session_id})"
            )

            return parsed_plan

        except Exception as e:
            self.parse_errors += 1
            logger.error(f"Failed to parse plan markdown: {e}")
            raise ValueError(f"Failed to parse plan markdown: {e}")

    def _parse_step_metadata(
        self,
        line: str,
        current_step: ParsedStep,
        step_description_lines: List[str],
    ) -> None:
        """Parse metadata from a step line."""
        stripped = line.strip()

        # Skip empty lines, headers, and code blocks
        if not stripped or stripped.startswith('#') or stripped.startswith('```'):
            return

        # Explicit file targets
        if stripped.startswith('Files:') or stripped.startswith('Files to create:'):
            files_text = stripped.split(':', 1)[1].strip()
            current_step.file_targets.extend([
                f.strip() for f in files_text.split(',') if f.strip()
            ])
        # Dependencies
        elif stripped.startswith('Depends:') or stripped.startswith('Dependencies:'):
            deps_text = stripped.split(':', 1)[1].strip()
            current_step.dependencies.extend([
                d.strip() for d in deps_text.split(',') if d.strip()
            ])
        # Tags
        elif stripped.startswith('Tags:'):
            tags_text = stripped.split(':', 1)[1].strip()
            current_step.tags.extend([
                t.strip().lower() for t in tags_text.split(',') if t.strip()
            ])
        # File paths in description (detect patterns like /path/to/file.py)
        elif '/' in stripped and stripped.startswith('Create:'):
            file_path = stripped.replace('Create:', '').strip().strip('`')
            current_step.file_targets.append(file_path)
        # Bullet points as description
        elif stripped.startswith('- ') or stripped.startswith('* '):
            step_description_lines.append(stripped[2:])
        # Regular description line
        elif not stripped.startswith('|') and not stripped.startswith('---'):
            step_description_lines.append(stripped)

    def _infer_files_from_description(self, description: str) -> List[str]:
        """Infer file targets from description text."""
        files = []
        # Match file paths like /path/to/file.py or `file.py`
        path_pattern = r'[`/]([a-zA-Z0-9_\-./]+\.[a-zA-Z]+)[`]?'
        matches = re.findall(path_pattern, description)
        for match in matches:
            if '.' in match and not match.startswith('.'):
                files.append(match)
        return files

    def to_goal(
        self,
        parsed_plan: ParsedPlan,
        agent_did: Optional[str] = None,
        constraints: Optional[GoalConstraints] = None,
    ) -> Goal:
        """
        Convert parsed plan to L05 Goal object.

        Args:
            parsed_plan: Parsed CLI plan output
            agent_did: Agent DID (defaults to cli-plan-mode agent)
            constraints: Optional goal constraints

        Returns:
            Goal object ready for L05 processing
        """
        goal = Goal.create(
            agent_did=agent_did or self.default_agent_did,
            goal_text=parsed_plan.goal,
            goal_type=GoalType.COMPOUND if len(parsed_plan.steps) > 1 else GoalType.SIMPLE,
            constraints=constraints or GoalConstraints(
                require_approval=False,  # Already approved in CLI
            ),
            metadata={
                "source": "cli_plan_mode",
                "original_context": parsed_plan.context,
                "step_count": len(parsed_plan.steps),
                "file_targets": self._collect_all_files(parsed_plan),
                "session_id": parsed_plan.session_id,
                "approved_at": parsed_plan.approved_at.isoformat(),
            },
        )

        goal.decomposition_strategy = "cli_adapter"

        return goal

    def to_execution_plan(
        self,
        parsed_plan: ParsedPlan,
        enrich: Optional[bool] = None,
        goal: Optional[Goal] = None,
    ) -> ExecutionPlan:
        """
        Convert parsed plan to L05 ExecutionPlan.

        Args:
            parsed_plan: Parsed CLI plan output
            enrich: Whether to enrich via GoalDecomposer (overrides instance default)
            goal: Optional pre-created Goal object

        Returns:
            ExecutionPlan ready for execution
        """
        should_enrich = enrich if enrich is not None else self.enrich

        # Create goal if not provided
        if goal is None:
            goal = self.to_goal(parsed_plan)

        # Create execution plan
        plan = ExecutionPlan.create(
            goal_id=goal.goal_id,
        )

        # Build task ID mapping for dependencies
        step_id_to_task_id: Dict[str, str] = {}

        # First pass: create tasks and map IDs
        tasks: List[Task] = []
        for step in parsed_plan.steps:
            task_id = str(uuid4())
            step_id_to_task_id[step.id] = task_id

            # Infer task type from content
            task_type = self._infer_task_type(step)

            task = Task.create(
                plan_id=plan.plan_id,
                name=step.title,
                description=step.description,
                task_type=task_type,
                inputs={
                    "file_targets": step.file_targets,
                    "tags": step.tags,
                    "original_step_id": step.id,
                },
                timeout_seconds=300,  # Default 5 minutes
                metadata={
                    "source": "cli_plan_mode",
                    "capabilities": self._infer_capabilities(step),
                    "parallelizable": step.parallelizable,
                },
            )
            task.task_id = task_id
            tasks.append(task)

        # Second pass: resolve dependencies
        for i, step in enumerate(parsed_plan.steps):
            task = tasks[i]
            for dep_id in step.dependencies:
                if dep_id in step_id_to_task_id:
                    task.dependencies.append(
                        TaskDependency(
                            task_id=step_id_to_task_id[dep_id],
                            dependency_type=DependencyType.BLOCKING,
                        )
                    )

        # Add tasks to plan
        for task in tasks:
            plan.add_task(task)

        # Compute parallel groups
        parallel_groups = self._compute_parallel_groups(parsed_plan.steps, step_id_to_task_id)

        # Update metadata
        plan.metadata.decomposition_strategy = "cli_adapter"
        plan.metadata.tags.append("cli_plan_mode")
        plan.metadata.tags.append(f"session:{parsed_plan.session_id}")

        # Store parallel groups in plan metadata (not a native field)
        # We'll access this via plan.metadata or a helper method

        self.plans_converted += 1
        logger.info(
            f"Converted plan: {len(tasks)} tasks, "
            f"{len(parallel_groups)} parallel groups"
        )

        return plan

    async def execute(
        self,
        markdown: str,
        dry_run: bool = False,
        agent_did: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Full pipeline: parse -> convert -> execute.

        Args:
            markdown: CLI plan mode output
            dry_run: If True, returns plan without executing
            agent_did: Optional agent DID for execution

        Returns:
            Execution result or dry run preview
        """
        # Parse
        parsed = self.parse_plan_markdown(markdown)

        # Convert
        goal = self.to_goal(parsed, agent_did=agent_did)
        execution_plan = self.to_execution_plan(parsed, goal=goal)

        if dry_run:
            return {
                "status": "dry_run",
                "goal": goal.to_dict(),
                "plan": execution_plan.to_dict(),
                "analysis": self.analyze_plan(parsed, execution_plan),
            }

        # Execute via L05 PlanningService
        if not self.planning_service:
            raise RuntimeError("PlanningService not configured for execution")

        self.plans_executed += 1
        result = await self.planning_service.execute_plan_direct(
            execution_plan,
            agent_did=agent_did or self.default_agent_did,
        )

        return {
            "status": "executed",
            "goal_id": goal.goal_id,
            "plan_id": execution_plan.plan_id,
            "result": result,
        }

    def analyze_plan(
        self,
        parsed: ParsedPlan,
        execution_plan: Optional[ExecutionPlan] = None,
    ) -> Dict[str, Any]:
        """
        Analyze plan for execution options presentation.

        Args:
            parsed: Parsed plan
            execution_plan: Optional execution plan (for task-level analysis)

        Returns:
            Analysis dictionary for Gate 2 presentation
        """
        # Build step ID mapping if we have execution plan
        step_to_task: Dict[str, str] = {}
        if execution_plan:
            for task in execution_plan.tasks:
                original_id = task.inputs.get("original_step_id")
                if original_id:
                    step_to_task[original_id] = task.task_id

        # Compute parallel groups
        parallel_groups = self._compute_parallel_groups(parsed.steps, step_to_task)

        # Collect all capabilities
        all_capabilities: set = set()
        for step in parsed.steps:
            all_capabilities.update(self._infer_capabilities(step))

        # Count parallelizable vs sequential
        parallelizable_count = sum(1 for s in parsed.steps if s.parallelizable)
        sequential_count = len(parsed.steps) - parallelizable_count

        return {
            "total_steps": len(parsed.steps),
            "parallel_phases": len(parallel_groups),
            "parallel_groups": parallel_groups,
            "parallelizable_steps": parallelizable_count,
            "sequential_steps": sequential_count,
            "inferred_capabilities": sorted(all_capabilities),
            "file_targets": self._collect_all_files(parsed),
            "estimated_speedup": self._estimate_speedup(parallel_groups),
        }

    def _infer_task_type(self, step: ParsedStep) -> TaskType:
        """Infer task type from step content."""
        # Check for tool-related keywords
        tool_keywords = ["run", "execute", "install", "build", "test", "deploy"]
        if any(kw in step.title.lower() for kw in tool_keywords):
            return TaskType.TOOL_CALL

        # Check for LLM-related keywords
        llm_keywords = ["write", "create", "generate", "design", "analyze"]
        if any(kw in step.title.lower() for kw in llm_keywords):
            return TaskType.LLM_CALL

        # Default to atomic
        return TaskType.ATOMIC

    def _infer_capabilities(self, step: ParsedStep) -> List[str]:
        """Infer required agent capabilities from step content."""
        capabilities: set = set()

        # File extension analysis
        for f in step.file_targets:
            # Handle paths like "src/components/Modal.tsx"
            filename = f.split('/')[-1]
            if '.' in filename:
                ext = filename.split('.')[-1].lower()
                if ext in self.EXT_TO_CAPABILITY:
                    capabilities.add(self.EXT_TO_CAPABILITY[ext])
            elif filename.lower() == 'dockerfile':
                capabilities.add('docker')

        # Tag analysis
        for tag in step.tags:
            tag_lower = tag.lower()
            if tag_lower in self.TAG_TO_CAPABILITY:
                capabilities.add(self.TAG_TO_CAPABILITY[tag_lower])

        # Title keyword analysis
        title_lower = step.title.lower()
        keyword_capabilities = {
            "test": "testing",
            "database": "database",
            "migrate": "database",
            "api": "backend",
            "component": "frontend",
            "deploy": "devops",
            "docker": "docker",
        }
        for keyword, cap in keyword_capabilities.items():
            if keyword in title_lower:
                capabilities.add(cap)

        return list(capabilities) if capabilities else ["general"]

    def _compute_parallel_groups(
        self,
        steps: List[ParsedStep],
        step_id_to_task_id: Dict[str, str],
    ) -> List[List[str]]:
        """
        Group steps that can execute in parallel.

        Steps with no dependencies can run together.
        Steps depending on group N go in group N+1.

        Returns:
            List of groups, where each group is a list of task IDs
        """
        groups: List[List[str]] = []
        assigned: set = set()

        while len(assigned) < len(steps):
            current_group: List[str] = []

            for step in steps:
                if step.id in assigned:
                    continue

                # Check if all dependencies are satisfied
                deps_satisfied = all(
                    dep in assigned for dep in step.dependencies
                )

                if deps_satisfied:
                    # Use task ID if available, otherwise step ID
                    task_id = step_id_to_task_id.get(step.id, step.id)
                    current_group.append(task_id)

            if current_group:
                groups.append(current_group)
                # Mark step IDs (not task IDs) as assigned
                for step in steps:
                    task_id = step_id_to_task_id.get(step.id, step.id)
                    if task_id in current_group:
                        assigned.add(step.id)
            else:
                # Circular dependency - break it
                remaining = [s for s in steps if s.id not in assigned]
                if remaining:
                    step = remaining[0]
                    task_id = step_id_to_task_id.get(step.id, step.id)
                    groups.append([task_id])
                    assigned.add(step.id)
                    logger.warning(
                        f"Detected circular dependency, breaking at step: {step.id}"
                    )

        return groups

    def _collect_all_files(self, parsed_plan: ParsedPlan) -> List[str]:
        """Collect all file targets across steps."""
        files: set = set()
        for step in parsed_plan.steps:
            files.update(step.file_targets)
        return sorted(files)

    def _estimate_speedup(self, parallel_groups: List[List[str]]) -> float:
        """
        Estimate execution speedup from parallelization.

        Returns ratio of sequential steps to parallel phases.
        """
        total_steps = sum(len(g) for g in parallel_groups)
        phases = len(parallel_groups)

        if phases == 0:
            return 1.0

        return total_steps / phases

    def _generate_session_id(self, content: str) -> str:
        """Generate unique session ID based on content and timestamp."""
        timestamp = datetime.now(timezone.utc).isoformat()
        combined = f"{timestamp}:{content[:100]}"
        return hashlib.sha256(combined.encode()).hexdigest()[:12]

    def get_stats(self) -> Dict[str, Any]:
        """Get adapter statistics."""
        return {
            "plans_parsed": self.plans_parsed,
            "plans_converted": self.plans_converted,
            "plans_executed": self.plans_executed,
            "parse_errors": self.parse_errors,
            "success_rate": (
                self.plans_parsed / max(1, self.plans_parsed + self.parse_errors)
            ),
        }
