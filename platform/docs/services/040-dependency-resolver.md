# Service 40/44: DependencyResolver

## Overview

| Property | Value |
|----------|-------|
| **Layer** | L05 (Planning Layer) |
| **Module** | `L05_planning.services.dependency_resolver` |
| **Status** | Fully Implemented & Healthy |
| **Dependencies** | None (graph algorithms) |
| **Category** | Planning / Dependency Analysis |

## Role in Development Environment

The **DependencyResolver** analyzes task dependency graphs to ensure correct execution ordering. It provides:
- Cycle detection with path reporting
- Topological sorting for execution order
- Ready task identification
- Execution wave computation (parallelization)
- Critical path analysis
- Dependency validation

This is **the dependency analyzer for task graphs** - ensuring tasks execute in the correct order with no circular dependencies.

## Data Model

### DependencyGraph
- `tasks: Dict[str, Task]` - Task ID to Task mapping
- `adjacency_list: Dict[str, List[str]]` - Forward dependencies (task → dependents)
- `reverse_adjacency: Dict[str, List[str]]` - Reverse dependencies (task ← dependencies)

### DependencyType Enum
- `BLOCKING` - Task must complete before dependent starts
- `DATA` - Task provides data to dependent
- `WEAK` - Soft dependency (can proceed if failed)

## Configuration

| Parameter | Default | Description |
|-----------|---------|-------------|
| (none) | - | Pure algorithm implementation |

## API Methods

| Method | Description |
|--------|-------------|
| `resolve(plan)` | Resolve and validate dependencies |
| `detect_cycle(graph)` | Detect cycles in graph |
| `topological_sort(graph)` | Compute execution order |
| `get_ready_tasks(graph, completed, executing)` | Get tasks ready to execute |
| `get_execution_waves(graph)` | Compute parallel execution waves |
| `compute_critical_path(graph)` | Find longest path |
| `get_stats()` | Get resolver statistics |

## Use Cases in Your Workflow

### 1. Initialize Dependency Resolver
```python
from L05_planning.services.dependency_resolver import DependencyResolver

resolver = DependencyResolver()
```

### 2. Resolve Plan Dependencies
```python
from L05_planning.models import ExecutionPlan

# Create plan with tasks and dependencies
plan = ExecutionPlan.create(goal_id="goal-123")
# ... add tasks with dependencies ...

# Resolve dependencies
try:
    graph = resolver.resolve(plan)
    print(f"Resolved {len(plan.tasks)} tasks")
except PlanningError as e:
    print(f"Dependency error: {e.message}")
```

### 3. Detect Cycles
```python
from L05_planning.services.dependency_resolver import DependencyGraph

# Build graph from tasks
graph = DependencyGraph(plan.tasks)

# Check for cycles
cycle = resolver.detect_cycle(graph)

if cycle:
    print(f"Cycle detected: {' → '.join(cycle)}")
else:
    print("No cycles found")
```

### 4. Get Topological Order
```python
# Get execution order
sorted_task_ids = resolver.topological_sort(graph)

print("Execution order:")
for i, task_id in enumerate(sorted_task_ids, 1):
    task = graph.tasks[task_id]
    print(f"  {i}. {task.name}")
```

### 5. Get Ready Tasks
```python
# Track execution state
completed = {"task-1", "task-2"}
executing = {"task-3"}

# Get tasks ready to execute
ready_tasks = resolver.get_ready_tasks(graph, completed, executing)

print(f"{len(ready_tasks)} tasks ready:")
for task in ready_tasks:
    print(f"  - {task.name}")
```

### 6. Compute Execution Waves
```python
# Get parallel execution waves
waves = resolver.get_execution_waves(graph)

print(f"Execution can complete in {len(waves)} waves:")
for i, wave in enumerate(waves, 1):
    task_names = [graph.tasks[tid].name for tid in wave]
    print(f"  Wave {i}: {', '.join(task_names)}")
```

### 7. Compute Critical Path
```python
# Find critical path (longest path)
critical_path, total_duration = resolver.compute_critical_path(graph)

print(f"Critical path ({total_duration}s):")
for task_id in critical_path:
    task = graph.tasks[task_id]
    print(f"  - {task.name} ({task.timeout_seconds}s)")
```

### 8. Query Graph Structure
```python
# Get root tasks (no dependencies)
roots = graph.get_root_tasks()
print(f"Root tasks: {roots}")

# Get leaf tasks (no dependents)
leaves = graph.get_leaf_tasks()
print(f"Leaf tasks: {leaves}")

# Get dependents of a task
dependents = graph.get_dependents("task-1")
print(f"Tasks depending on task-1: {dependents}")

# Get dependencies of a task
dependencies = graph.get_dependencies("task-5")
print(f"task-5 depends on: {dependencies}")
```

### 9. Get Resolver Statistics
```python
stats = resolver.get_stats()

print(f"Graphs resolved: {stats['graphs_resolved']}")
print(f"Cycles detected: {stats['cycles_detected']}")
print(f"Cycle rate: {stats['cycle_detection_rate']:.1%}")
```

### 10. Integration with TaskOrchestrator
```python
from L05_planning.services.task_orchestrator import TaskOrchestrator

# Create orchestrator with resolver
resolver = DependencyResolver()
orchestrator = TaskOrchestrator(
    dependency_resolver=resolver
)

# Orchestrator uses resolver for execution ordering
result = await orchestrator.execute_plan(plan)
```

## Service Interactions

```
+--------------------+
| DependencyResolver | <--- L05 Planning Layer
|       (L05)        |
+---------+----------+
          |
    Provides:
          |
+---------+----------+----------+
|         |          |          |
v         v          v          v
Cycle     Topo       Ready      Critical
Detect    Sort       Tasks      Path
```

**Integration Points:**
- **PlanningService (L05)**: Uses for plan validation
- **PlanValidator (L05)**: Validates dependencies
- **TaskOrchestrator (L05)**: Gets execution order
- **ExecutionPlan (L05)**: Analyzes task dependencies

## Algorithms

### Cycle Detection (DFS)
```
1. Start DFS from each unvisited node
2. Track nodes in current recursion stack
3. If neighbor in recursion stack → cycle found
4. Reconstruct cycle path using parent pointers
```

### Topological Sort (Kahn's Algorithm)
```
1. Compute in-degree for all nodes
2. Queue nodes with in-degree 0
3. While queue not empty:
   - Dequeue node, add to result
   - Decrease in-degree of dependents
   - Queue any with in-degree now 0
4. If result incomplete → cycle exists
```

### Execution Waves
```
1. Initialize in-degrees
2. While nodes remain:
   - Wave = nodes with in-degree 0
   - Remove wave nodes
   - Decrease dependent in-degrees
   - Add wave to result
```

### Critical Path
```
1. Topological sort
2. For each node (in order):
   - longest_path[node] = max(longest_path[deps]) + duration
3. Find node with maximum longest_path
4. Reconstruct path using predecessors
```

## Error Codes

| Code | Description | Retryable |
|------|-------------|-----------|
| E5301 | Circular dependency detected | No |
| E5302 | Missing dependency reference | No |
| E5305 | Topological sort failed | No |

## Execution Examples

```python
# Complete dependency resolution workflow
from L05_planning.services.dependency_resolver import (
    DependencyResolver,
    DependencyGraph,
)
from L05_planning.models import (
    ExecutionPlan,
    Task,
    TaskDependency,
    DependencyType,
    PlanningError,
)

# Initialize
resolver = DependencyResolver()

# 1. Create plan with task dependencies
plan = ExecutionPlan.create(goal_id="goal-build-app")

# Task A: No dependencies (root)
task_a = Task.create(
    plan_id=plan.plan_id,
    name="Setup environment",
    description="Initialize project",
    timeout_seconds=60,
)
plan.add_task(task_a)

# Task B: Depends on A
task_b = Task.create(
    plan_id=plan.plan_id,
    name="Install dependencies",
    description="Install npm packages",
    timeout_seconds=120,
)
task_b.dependencies.append(
    TaskDependency(task_id=task_a.task_id, dependency_type=DependencyType.BLOCKING)
)
plan.add_task(task_b)

# Task C: Depends on A (parallel with B)
task_c = Task.create(
    plan_id=plan.plan_id,
    name="Configure database",
    description="Setup database connection",
    timeout_seconds=90,
)
task_c.dependencies.append(
    TaskDependency(task_id=task_a.task_id, dependency_type=DependencyType.BLOCKING)
)
plan.add_task(task_c)

# Task D: Depends on B and C
task_d = Task.create(
    plan_id=plan.plan_id,
    name="Run tests",
    description="Execute test suite",
    timeout_seconds=180,
)
task_d.dependencies.extend([
    TaskDependency(task_id=task_b.task_id, dependency_type=DependencyType.BLOCKING),
    TaskDependency(task_id=task_c.task_id, dependency_type=DependencyType.BLOCKING),
])
plan.add_task(task_d)

print(f"Created plan with {len(plan.tasks)} tasks")

# 2. Resolve dependencies
try:
    graph = resolver.resolve(plan)
    print("\nDependencies resolved successfully")
except PlanningError as e:
    print(f"Error: {e.message}")
    exit()

# 3. Check for cycles (should be none)
cycle = resolver.detect_cycle(graph)
print(f"Cycles: {cycle or 'None'}")

# 4. Get topological order
sorted_ids = resolver.topological_sort(graph)
print("\nExecution order:")
for i, task_id in enumerate(sorted_ids, 1):
    task = graph.tasks[task_id]
    print(f"  {i}. {task.name}")

# 5. Compute execution waves
waves = resolver.get_execution_waves(graph)
print(f"\nExecution waves ({len(waves)} total):")
for i, wave in enumerate(waves, 1):
    names = [graph.tasks[tid].name for tid in wave]
    print(f"  Wave {i}: {', '.join(names)}")

# 6. Compute critical path
path, duration = resolver.compute_critical_path(graph)
print(f"\nCritical path ({duration}s total):")
for task_id in path:
    task = graph.tasks[task_id]
    print(f"  - {task.name} ({task.timeout_seconds}s)")

# 7. Simulate execution
print("\nSimulating execution:")
completed = set()
executing = set()

while len(completed) < len(plan.tasks):
    ready = resolver.get_ready_tasks(graph, completed, executing)

    if not ready and not executing:
        print("  Deadlock detected!")
        break

    # Start executing ready tasks
    for task in ready:
        if task.task_id not in executing:
            executing.add(task.task_id)
            print(f"  Started: {task.name}")

    # Simulate completion of first executing task
    if executing:
        done_id = next(iter(executing))
        executing.remove(done_id)
        completed.add(done_id)
        print(f"  Completed: {graph.tasks[done_id].name}")

print(f"\nAll {len(completed)} tasks completed")

# 8. Statistics
stats = resolver.get_stats()
print(f"\nResolver stats: {stats}")
```

## Implementation Status

| Component | Status |
|-----------|--------|
| DependencyGraph class | Complete |
| DependencyResolver class | Complete |
| resolve() | Complete |
| detect_cycle() | Complete |
| topological_sort() | Complete |
| get_ready_tasks() | Complete |
| get_execution_waves() | Complete |
| compute_critical_path() | Complete |
| Dependency validation | Complete |
| Statistics | Complete |

## Remaining Work

| Item | Priority | Description |
|------|----------|-------------|
| Optional dependencies | Medium | Handle weak/optional deps |
| Dynamic dependencies | Low | Support runtime dep changes |
| Dependency visualization | Low | Generate graph diagrams |
| Performance optimization | Low | Optimize for large graphs |

## Strengths

- **Complete graph analysis** - Cycles, paths, waves
- **Parallel execution support** - Identifies parallelizable tasks
- **Critical path analysis** - Estimates minimum execution time
- **Clean algorithms** - Standard graph algorithms
- **No external dependencies** - Pure Python implementation
- **Detailed error reporting** - Cycle path reconstruction

## Weaknesses

- **Static analysis only** - No runtime dependency changes
- **No optional dependencies** - All deps are required
- **Memory for large graphs** - Full adjacency storage
- **No visualization** - Text output only
- **Simple duration model** - Uses timeout as duration

## Best Practices

### Dependency Design
Create clear dependency chains:
```python
# Good: Clear, minimal dependencies
task_b.dependencies = [TaskDependency(task_id=task_a.task_id)]
task_c.dependencies = [TaskDependency(task_id=task_b.task_id)]

# Avoid: Redundant transitive dependencies
# If B depends on A and C depends on B, C doesn't need to depend on A
```

### Parallelization
Design for parallelism:
```python
# Good: Independent tasks can run in parallel
task_b.dependencies = [TaskDependency(task_id=task_a.task_id)]
task_c.dependencies = [TaskDependency(task_id=task_a.task_id)]
# B and C can execute in parallel after A

# Bad: Unnecessary serialization
task_c.dependencies = [TaskDependency(task_id=task_b.task_id)]
# C must wait for B even if not needed
```

### Cycle Prevention
Validate dependencies early:
```python
try:
    graph = resolver.resolve(plan)
except PlanningError as e:
    if e.code == ErrorCode.E5301:
        print(f"Cycle detected: {e.details['cycle']}")
        # Fix the dependency causing the cycle
```

## Source Files

- Service: `platform/src/L05_planning/services/dependency_resolver.py`
- Models: `platform/src/L05_planning/models/`
- Spec: L05 Planning Layer specification

## Related Services

- PlanningService (L05) - Uses for plan creation
- PlanValidator (L05) - Validates dependencies
- TaskOrchestrator (L05) - Uses for execution ordering
- ExecutionPlan (L05) - Contains task dependencies

---
*Generated: 2026-01-24 | Platform Services Documentation*
