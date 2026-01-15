"""
L05 Planning Layer - Dependency Resolver Service.

Analyzes task dependency graphs to:
- Detect cycles (circular dependencies)
- Compute topological ordering
- Identify ready tasks (dependencies satisfied)
- Compute critical path
"""

import logging
from typing import List, Optional, Dict, Set, Tuple
from collections import defaultdict, deque

from ..models import Task, ExecutionPlan, PlanningError, ErrorCode, DependencyType

logger = logging.getLogger(__name__)


class DependencyGraph:
    """
    Represents a task dependency graph.

    Provides methods for graph analysis and traversal.
    """

    def __init__(self, tasks: List[Task]):
        """
        Initialize dependency graph from tasks.

        Args:
            tasks: List of tasks to build graph from
        """
        self.tasks = {task.task_id: task for task in tasks}
        self.adjacency_list: Dict[str, List[str]] = defaultdict(list)
        self.reverse_adjacency: Dict[str, List[str]] = defaultdict(list)

        # Build adjacency lists
        for task in tasks:
            for dep in task.dependencies:
                # Forward: dep.task_id -> task.task_id
                self.adjacency_list[dep.task_id].append(task.task_id)
                # Reverse: task.task_id <- dep.task_id
                self.reverse_adjacency[task.task_id].append(dep.task_id)

    def get_dependents(self, task_id: str) -> List[str]:
        """Get tasks that depend on this task."""
        return self.adjacency_list.get(task_id, [])

    def get_dependencies(self, task_id: str) -> List[str]:
        """Get tasks that this task depends on."""
        return self.reverse_adjacency.get(task_id, [])

    def get_root_tasks(self) -> List[str]:
        """Get tasks with no dependencies (root nodes)."""
        return [
            task_id
            for task_id in self.tasks.keys()
            if not self.reverse_adjacency.get(task_id)
        ]

    def get_leaf_tasks(self) -> List[str]:
        """Get tasks with no dependents (leaf nodes)."""
        return [
            task_id
            for task_id in self.tasks.keys()
            if not self.adjacency_list.get(task_id)
        ]


class DependencyResolver:
    """
    Resolves task dependencies and validates dependency graphs.

    Key capabilities:
    - Cycle detection with path reporting
    - Topological sort for execution ordering
    - Ready task identification
    - Critical path computation
    """

    def __init__(self):
        """Initialize dependency resolver."""
        self.cycles_detected = 0
        self.graphs_resolved = 0
        logger.info("DependencyResolver initialized")

    def resolve(self, plan: ExecutionPlan) -> DependencyGraph:
        """
        Resolve dependencies for execution plan.

        Args:
            plan: Execution plan with tasks

        Returns:
            DependencyGraph with validated dependencies

        Raises:
            PlanningError: If cycles detected or graph invalid
        """
        self.graphs_resolved += 1

        # Build dependency graph
        graph = DependencyGraph(plan.tasks)

        # Validate: check for cycles
        cycle = self.detect_cycle(graph)
        if cycle:
            self.cycles_detected += 1
            logger.error(f"Cycle detected in plan {plan.plan_id}: {' -> '.join(cycle)}")
            raise PlanningError.from_code(
                ErrorCode.E5301,
                details={
                    "plan_id": plan.plan_id,
                    "cycle": cycle,
                },
                recovery_suggestion="Remove circular dependencies between tasks",
            )

        # Validate: all dependencies exist
        self._validate_dependencies_exist(graph)

        logger.info(f"Resolved dependencies for plan {plan.plan_id} ({len(plan.tasks)} tasks)")
        return graph

    def detect_cycle(self, graph: DependencyGraph) -> Optional[List[str]]:
        """
        Detect cycles in dependency graph using DFS.

        Args:
            graph: Dependency graph to check

        Returns:
            List of task IDs forming cycle, or None if no cycle
        """
        visited: Set[str] = set()
        rec_stack: Set[str] = set()  # Recursion stack for cycle detection
        parent: Dict[str, str] = {}  # Parent pointers for cycle reconstruction

        def dfs(node: str) -> Optional[List[str]]:
            """DFS to detect cycle."""
            visited.add(node)
            rec_stack.add(node)

            # Visit all dependents
            for neighbor in graph.get_dependents(node):
                if neighbor not in visited:
                    parent[neighbor] = node
                    cycle = dfs(neighbor)
                    if cycle:
                        return cycle
                elif neighbor in rec_stack:
                    # Cycle detected! Reconstruct path
                    cycle = [neighbor]
                    current = node
                    while current != neighbor:
                        cycle.append(current)
                        current = parent.get(current)
                        if current is None:
                            break
                    cycle.append(neighbor)
                    return list(reversed(cycle))

            rec_stack.remove(node)
            return None

        # Check all components (handle disconnected graphs)
        for task_id in graph.tasks.keys():
            if task_id not in visited:
                cycle = dfs(task_id)
                if cycle:
                    return cycle

        return None

    def topological_sort(self, graph: DependencyGraph) -> List[str]:
        """
        Compute topological sort of dependency graph using Kahn's algorithm.

        Args:
            graph: Dependency graph

        Returns:
            List of task IDs in topologically sorted order

        Raises:
            PlanningError: If graph contains cycles
        """
        # Compute in-degrees
        in_degree: Dict[str, int] = defaultdict(int)
        for task_id in graph.tasks.keys():
            in_degree[task_id] = len(graph.get_dependencies(task_id))

        # Queue of tasks with in-degree 0
        queue: deque = deque([task_id for task_id in graph.tasks.keys() if in_degree[task_id] == 0])
        sorted_tasks: List[str] = []

        while queue:
            # Remove task with no dependencies
            task_id = queue.popleft()
            sorted_tasks.append(task_id)

            # Decrease in-degree of dependents
            for dependent in graph.get_dependents(task_id):
                in_degree[dependent] -= 1
                if in_degree[dependent] == 0:
                    queue.append(dependent)

        # If not all tasks processed, there's a cycle
        if len(sorted_tasks) != len(graph.tasks):
            raise PlanningError.from_code(
                ErrorCode.E5305,
                details={"processed": len(sorted_tasks), "total": len(graph.tasks)},
            )

        return sorted_tasks

    def get_ready_tasks(
        self,
        graph: DependencyGraph,
        completed: Set[str],
        executing: Optional[Set[str]] = None,
    ) -> List[Task]:
        """
        Get tasks that are ready to execute.

        A task is ready if:
        1. All its dependencies are completed
        2. It's not already executing
        3. Its status is PENDING

        Args:
            graph: Dependency graph
            completed: Set of completed task IDs
            executing: Optional set of currently executing task IDs

        Returns:
            List of Task objects ready to execute
        """
        executing = executing or set()
        ready_tasks: List[Task] = []

        for task_id, task in graph.tasks.items():
            # Skip if already executing or completed
            if task_id in executing or task_id in completed:
                continue

            # Check if all dependencies are satisfied
            dependencies = graph.get_dependencies(task_id)
            if all(dep_id in completed for dep_id in dependencies):
                # Check task can execute based on status
                if task.can_execute(completed):
                    ready_tasks.append(task)

        return ready_tasks

    def get_execution_waves(self, graph: DependencyGraph) -> List[List[str]]:
        """
        Compute execution waves (tasks that can run in parallel).

        Each wave contains tasks with no dependencies on each other.

        Args:
            graph: Dependency graph

        Returns:
            List of waves, where each wave is a list of task IDs
        """
        # Compute in-degrees
        in_degree: Dict[str, int] = defaultdict(int)
        for task_id in graph.tasks.keys():
            in_degree[task_id] = len(graph.get_dependencies(task_id))

        waves: List[List[str]] = []
        remaining = set(graph.tasks.keys())

        while remaining:
            # Current wave: tasks with in-degree 0
            wave = [task_id for task_id in remaining if in_degree[task_id] == 0]

            if not wave:
                # No progress possible (shouldn't happen if no cycles)
                break

            waves.append(wave)

            # Remove wave tasks and update in-degrees
            for task_id in wave:
                remaining.remove(task_id)
                for dependent in graph.get_dependents(task_id):
                    in_degree[dependent] -= 1

        return waves

    def compute_critical_path(self, graph: DependencyGraph) -> Tuple[List[str], int]:
        """
        Compute critical path through dependency graph.

        The critical path is the longest path from root to leaf.

        Args:
            graph: Dependency graph

        Returns:
            Tuple of (critical_path task IDs, total duration in seconds)
        """
        # Compute longest path to each node
        longest_path: Dict[str, int] = defaultdict(int)
        predecessor: Dict[str, Optional[str]] = {task_id: None for task_id in graph.tasks.keys()}

        # Process tasks in topological order
        try:
            sorted_tasks = self.topological_sort(graph)
        except PlanningError:
            logger.warning("Cannot compute critical path: graph has cycles")
            return [], 0

        for task_id in sorted_tasks:
            task = graph.tasks[task_id]
            task_duration = task.timeout_seconds

            # Compute longest path through this task
            for dep_id in graph.get_dependencies(task_id):
                path_length = longest_path[dep_id] + task_duration
                if path_length > longest_path[task_id]:
                    longest_path[task_id] = path_length
                    predecessor[task_id] = dep_id

        # Find task with longest path (critical path end)
        if not longest_path:
            return [], 0

        critical_end = max(longest_path.keys(), key=lambda k: longest_path[k])
        critical_duration = longest_path[critical_end]

        # Reconstruct critical path
        path = []
        current = critical_end
        while current is not None:
            path.append(current)
            current = predecessor[current]

        path.reverse()

        logger.info(f"Critical path: {len(path)} tasks, {critical_duration}s total duration")
        return path, critical_duration

    def _validate_dependencies_exist(self, graph: DependencyGraph) -> None:
        """
        Validate that all dependencies reference existing tasks.

        Args:
            graph: Dependency graph

        Raises:
            PlanningError: If dependency references non-existent task
        """
        for task_id, task in graph.tasks.items():
            for dep in task.dependencies:
                if dep.task_id not in graph.tasks:
                    raise PlanningError.from_code(
                        ErrorCode.E5302,
                        details={
                            "task_id": task_id,
                            "missing_dependency": dep.task_id,
                        },
                        recovery_suggestion="Ensure all task dependencies reference existing tasks",
                    )

    def get_stats(self) -> dict:
        """Get resolver statistics."""
        return {
            "graphs_resolved": self.graphs_resolved,
            "cycles_detected": self.cycles_detected,
            "cycle_detection_rate": self.cycles_detected / max(1, self.graphs_resolved),
        }
