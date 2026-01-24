# Service 48/52: RoleDispatcher

## Overview

| Property | Value |
|----------|-------|
| **Layer** | L13 (Role Management Layer) |
| **Module** | `L13_role_management.services.role_dispatcher` |
| **Status** | Fully Implemented & Healthy |
| **Dependencies** | RoleRegistry, ClassificationEngine, RoleContextBuilder |
| **Category** | Role Management / Dispatch |

## Role in Development Environment

The **RoleDispatcher** coordinates the complete task-to-role dispatch workflow. It provides:
- Task classification and routing
- Role selection based on capabilities
- Context assembly for execution
- Batch dispatch for multiple tasks
- Dispatch history tracking
- Task reassignment support
- Load balancing hints

This is **the dispatch coordinator** - when tasks need to be assigned to roles, RoleDispatcher orchestrates classification, role selection, and context assembly into a unified workflow.

## Data Model

### DispatchResult
- `task_id: str` - Dispatched task ID
- `role_id: str` - Assigned role ID
- `classification: TaskClassification` - Human/AI/hybrid routing
- `confidence: float` - Classification confidence
- `context: RoleContext` - Assembled context
- `dispatch_time: datetime` - When dispatched
- `metadata: Dict` - Dispatch metadata

### DispatchRequest
- `task: Task` - Task to dispatch
- `preferred_role: str` - Optional preferred role ID
- `exclude_roles: List[str]` - Roles to exclude
- `token_budget: int` - Context token budget
- `priority: str` - Dispatch priority
- `force_classification: TaskClassification` - Force specific routing

### DispatchHistory
- `task_id: str` - Task identifier
- `dispatches: List[DispatchEvent]` - Dispatch events
- `reassignments: int` - Number of reassignments
- `current_role: str` - Currently assigned role

## Configuration

| Parameter | Default | Description |
|-----------|---------|-------------|
| `registry` | RoleRegistry() | Role registry instance |
| `classifier` | ClassificationEngine() | Classification engine |
| `context_builder` | RoleContextBuilder() | Context builder |
| `max_dispatch_attempts` | 3 | Max dispatch retry attempts |
| `default_token_budget` | 8000 | Default context budget |

## API Methods

| Method | Description |
|--------|-------------|
| `dispatch_task(request)` | Dispatch single task to role |
| `batch_dispatch(requests)` | Dispatch multiple tasks |
| `reassign_task(task_id, new_role_id)` | Reassign task to different role |
| `get_dispatch_history(task_id)` | Get task dispatch history |
| `get_available_roles(task)` | Get roles available for task |
| `estimate_dispatch(task)` | Estimate dispatch without executing |
| `cancel_dispatch(task_id)` | Cancel pending dispatch |
| `get_stats()` | Get dispatcher statistics |

## Use Cases in Your Workflow

### 1. Initialize Role Dispatcher
```python
from L13_role_management.services.role_dispatcher import RoleDispatcher
from L13_role_management.services.role_registry import RoleRegistry
from L13_role_management.services.classification_engine import ClassificationEngine
from L13_role_management.services.role_context_builder import RoleContextBuilder

# Default initialization
dispatcher = RoleDispatcher()

# With custom components
dispatcher = RoleDispatcher(
    registry=RoleRegistry(db_url="postgresql://..."),
    classifier=ClassificationEngine(human_threshold=0.7),
    context_builder=RoleContextBuilder(default_token_budget=10000)
)
```

### 2. Dispatch Single Task
```python
from L13_role_management.models import DispatchRequest, Task

task = Task(
    task_id="task-123",
    description="Review pull request for security vulnerabilities",
    required_capabilities=["code_review", "security"],
    priority="high"
)

request = DispatchRequest(
    task=task,
    token_budget=8000
)

result = await dispatcher.dispatch_task(request)

print(f"Task dispatched:")
print(f"  Role: {result.role_id}")
print(f"  Classification: {result.classification.value}")
print(f"  Confidence: {result.confidence:.0%}")
print(f"  Context tokens: {result.context.token_count}")
```

### 3. Dispatch with Preferred Role
```python
# Request specific role if available
request = DispatchRequest(
    task=task,
    preferred_role="role-senior-dev",
    token_budget=10000
)

result = await dispatcher.dispatch_task(request)

if result.role_id == "role-senior-dev":
    print("Dispatched to preferred role")
else:
    print(f"Preferred unavailable, dispatched to: {result.role_id}")
```

### 4. Dispatch with Excluded Roles
```python
# Exclude roles that previously failed
request = DispatchRequest(
    task=task,
    exclude_roles=["role-123", "role-456"],  # Previously failed
    token_budget=8000
)

result = await dispatcher.dispatch_task(request)
print(f"Dispatched to: {result.role_id} (excluded others)")
```

### 5. Force Classification
```python
from L13_role_management.models import TaskClassification

# Force human routing regardless of classification
request = DispatchRequest(
    task=task,
    force_classification=TaskClassification.HUMAN_PRIMARY,
    token_budget=8000
)

result = await dispatcher.dispatch_task(request)
print(f"Forced to human role: {result.role_id}")
```

### 6. Batch Dispatch
```python
tasks = [
    Task(task_id="t1", description="Analyze data...", required_capabilities=["analysis"]),
    Task(task_id="t2", description="Approve budget...", required_capabilities=["approval"]),
    Task(task_id="t3", description="Generate report...", required_capabilities=["reporting"]),
]

requests = [DispatchRequest(task=t, token_budget=6000) for t in tasks]

results = await dispatcher.batch_dispatch(requests)

print(f"Batch dispatch results:")
for result in results:
    print(f"  {result.task_id} → {result.role_id} ({result.classification.value})")
```

### 7. Reassign Task
```python
# Task needs to be reassigned (e.g., role became unavailable)
new_result = await dispatcher.reassign_task(
    task_id="task-123",
    new_role_id="role-backup-dev"
)

print(f"Task reassigned to: {new_result.role_id}")

# Check reassignment history
history = await dispatcher.get_dispatch_history("task-123")
print(f"Reassignments: {history.reassignments}")
```

### 8. Get Available Roles for Task
```python
# Preview which roles could handle the task
available = await dispatcher.get_available_roles(task)

print(f"Available roles ({len(available)}):")
for role, score in available:
    print(f"  {role.name}: {score:.2f} match score")
```

### 9. Estimate Dispatch (Dry Run)
```python
# Preview dispatch without executing
estimate = await dispatcher.estimate_dispatch(task)

print(f"Dispatch estimate:")
print(f"  Best role: {estimate['recommended_role']}")
print(f"  Classification: {estimate['classification']}")
print(f"  Confidence: {estimate['confidence']:.0%}")
print(f"  Estimated tokens: {estimate['token_estimate']}")
print(f"  Alternative roles: {estimate['alternatives']}")
```

### 10. Get Dispatcher Statistics
```python
stats = dispatcher.get_stats()

print(f"Dispatcher Statistics:")
print(f"  Total dispatches: {stats['total_dispatches']}")
print(f"  Successful: {stats['successful_dispatches']}")
print(f"  Failed: {stats['failed_dispatches']}")
print(f"  Reassignments: {stats['reassignments']}")
print(f"  By classification:")
print(f"    Human: {stats['human_dispatches']}")
print(f"    AI: {stats['ai_dispatches']}")
print(f"    Hybrid: {stats['hybrid_dispatches']}")
print(f"  Avg dispatch time: {stats['avg_dispatch_time_ms']:.0f}ms")
```

## Service Interactions

```
+------------------+
|  RoleDispatcher  | <--- L13 Role Management Layer
|      (L13)       |
+--------+---------+
         |
   Coordinates:
         |
+--------+--------+--------+
|        |        |        |
v        v        v        v
Role     Class-   Context  History
Registry ifier    Builder  Tracker
(L13)    (L13)    (L13)    (L13)
```

**Integration Points:**
- **RoleRegistry (L13)**: Role lookup and search
- **ClassificationEngine (L13)**: Task classification
- **RoleContextBuilder (L13)**: Context assembly
- **TaskOrchestrator (L05)**: Receives dispatch results

## Dispatch Workflow

```
Dispatch Flow:

1. RECEIVE DISPATCH REQUEST
   ├─ Validate task
   ├─ Check token budget
   └─ Parse preferences

2. CLASSIFY TASK
   ├─ Call ClassificationEngine.classify_task()
   ├─ Get classification: human/ai/hybrid
   └─ Get confidence score

3. CHECK FORCE CLASSIFICATION
   └─ If force_classification set, override step 2

4. SEARCH AVAILABLE ROLES
   ├─ Query RoleRegistry
   ├─ Filter by classification type
   ├─ Filter by required capabilities
   ├─ Exclude specified roles
   └─ Sort by capability match score

5. SELECT ROLE
   ├─ If preferred_role available, select it
   ├─ Else select highest scoring role
   └─ If no roles available, fail

6. BUILD CONTEXT
   ├─ Call RoleContextBuilder.build_context()
   ├─ Apply token budget
   └─ Include task-specific context

7. CREATE DISPATCH RESULT
   ├─ Assign task to role
   ├─ Record in history
   └─ Publish dispatch event

8. RETURN RESULT
   └─ DispatchResult with all details
```

## Error Codes

| Code | Description | Retryable |
|------|-------------|-----------|
| E13301 | No suitable role found | Yes |
| E13302 | Classification failed | Yes |
| E13303 | Context build failed | Yes |
| E13304 | Dispatch timeout | Yes |
| E13305 | Role unavailable | Yes |
| E13306 | Task already dispatched | No |
| E13307 | Invalid dispatch request | No |

## Execution Examples

```python
# Complete dispatch workflow
from L13_role_management.services.role_dispatcher import RoleDispatcher
from L13_role_management.services.role_registry import RoleRegistry
from L13_role_management.services.classification_engine import ClassificationEngine
from L13_role_management.models import (
    Role, RoleType, Task, DispatchRequest, TaskClassification
)

# Initialize components
registry = RoleRegistry()
classifier = ClassificationEngine()
dispatcher = RoleDispatcher(
    registry=registry,
    classifier=classifier
)

# 1. Register roles
await registry.register_role(Role(
    name="AI Code Reviewer",
    role_type=RoleType.AI_PRIMARY,
    capabilities=["code_review", "security_analysis", "performance_review"],
    skills=["skill-python", "skill-security"]
))

await registry.register_role(Role(
    name="Senior Architect",
    role_type=RoleType.HUMAN_PRIMARY,
    capabilities=["architecture_review", "decision_making", "mentoring"],
    skills=["skill-architecture"]
))

await registry.register_role(Role(
    name="DevOps Engineer",
    role_type=RoleType.HYBRID,
    capabilities=["deployment", "monitoring", "automation"],
    skills=["skill-kubernetes", "skill-aws"]
))

print("Registered 3 roles")

# 2. Create diverse tasks
tasks = [
    Task(
        task_id="task-001",
        description="Review Python code changes for security vulnerabilities",
        required_capabilities=["code_review", "security_analysis"],
        priority="high"
    ),
    Task(
        task_id="task-002",
        description="Approve architectural decision for microservices migration",
        required_capabilities=["architecture_review", "decision_making"],
        priority="critical"
    ),
    Task(
        task_id="task-003",
        description="Deploy and monitor new service to production",
        required_capabilities=["deployment", "monitoring"],
        priority="medium"
    ),
]

# 3. Dispatch each task
print("\nDispatching tasks:")
print("-" * 60)

for task in tasks:
    # Estimate first
    estimate = await dispatcher.estimate_dispatch(task)
    print(f"\nTask: {task.task_id}")
    print(f"  Description: {task.description[:40]}...")
    print(f"  Estimate: {estimate['classification']} → {estimate['recommended_role']}")

    # Dispatch
    request = DispatchRequest(
        task=task,
        token_budget=8000
    )
    result = await dispatcher.dispatch_task(request)

    print(f"  Dispatched: {result.classification.value} → {result.role_id}")
    print(f"  Confidence: {result.confidence:.0%}")
    print(f"  Context tokens: {result.context.token_count}")

# 4. Simulate reassignment
print("\n\nSimulating reassignment:")
print("-" * 40)

old_result = await dispatcher.get_dispatch_history("task-001")
print(f"Task task-001 currently assigned to: {old_result.current_role}")

new_result = await dispatcher.reassign_task(
    task_id="task-001",
    new_role_id="role-senior-dev"  # Different role
)
print(f"Reassigned to: {new_result.role_id}")

history = await dispatcher.get_dispatch_history("task-001")
print(f"Total reassignments: {history.reassignments}")

# 5. Batch dispatch
print("\n\nBatch dispatch:")
print("-" * 40)

batch_tasks = [
    Task(task_id=f"batch-{i}", description=f"Analyze dataset {i}",
         required_capabilities=["analysis"], priority="low")
    for i in range(5)
]

batch_requests = [DispatchRequest(task=t, token_budget=4000) for t in batch_tasks]
batch_results = await dispatcher.batch_dispatch(batch_requests)

print(f"Batch dispatched {len(batch_results)} tasks")
for result in batch_results:
    print(f"  {result.task_id} → {result.classification.value}")

# 6. Statistics
print("\n\nDispatcher Statistics:")
print("-" * 40)
stats = dispatcher.get_stats()
for key, value in stats.items():
    print(f"  {key}: {value}")
```

## Implementation Status

| Component | Status |
|-----------|--------|
| RoleDispatcher class | Complete |
| dispatch_task() | Complete |
| batch_dispatch() | Complete |
| reassign_task() | Complete |
| get_dispatch_history() | Complete |
| get_available_roles() | Complete |
| estimate_dispatch() | Complete |
| cancel_dispatch() | Complete |
| History tracking | Complete |
| Statistics | Complete |

## Remaining Work

| Item | Priority | Description |
|------|----------|-------------|
| Load balancing | High | Balance dispatch across roles |
| Priority queuing | Medium | Queue-based priority dispatch |
| Dispatch scheduling | Medium | Time-based dispatch |
| Role affinity | Low | Remember successful role assignments |
| Dispatch webhooks | Low | External dispatch notifications |

## Strengths

- **Unified workflow** - Single entry point for dispatch
- **Component coordination** - Orchestrates registry, classifier, builder
- **Flexible routing** - Supports force, prefer, exclude options
- **Batch support** - Efficient multi-task dispatch
- **History tracking** - Full dispatch audit trail
- **Dry run** - Estimate without executing

## Weaknesses

- **No load balancing** - Doesn't balance role workload
- **Simple selection** - First match, not optimal
- **No priority queue** - FIFO processing
- **Synchronous** - Blocking dispatch calls
- **No scheduling** - Immediate dispatch only
- **Memory history** - History not persisted

## Best Practices

### Dispatch Strategy
Choose dispatch parameters wisely:
```python
# For critical tasks: prefer experienced role
request = DispatchRequest(
    task=critical_task,
    preferred_role="role-senior-dev",
    force_classification=TaskClassification.HUMAN_PRIMARY,
    token_budget=12000  # More context
)

# For routine tasks: let classifier decide
request = DispatchRequest(
    task=routine_task,
    token_budget=6000  # Less context needed
)
```

### Retry with Exclusions
Handle failures by excluding failed roles:
```python
failed_roles = []
max_attempts = 3

for attempt in range(max_attempts):
    try:
        request = DispatchRequest(
            task=task,
            exclude_roles=failed_roles
        )
        result = await dispatcher.dispatch_task(request)
        break
    except DispatchError as e:
        failed_roles.append(e.role_id)
        print(f"Attempt {attempt+1} failed, excluding {e.role_id}")
```

### Use Estimates for Preview
Preview before dispatching:
```python
# Good: Estimate first, then dispatch
estimate = await dispatcher.estimate_dispatch(task)
if estimate['confidence'] > 0.7:
    result = await dispatcher.dispatch_task(request)
else:
    # Low confidence - get user input
    print(f"Uncertain routing, recommend: {estimate['recommended_role']}")
```

## Source Files

- Service: `platform/src/L13_role_management/services/role_dispatcher.py`
- Models: `platform/src/L13_role_management/models/`
- Spec: L13 Role Management Layer specification

## Related Services

- RoleRegistry (L13) - Role lookup
- ClassificationEngine (L13) - Task classification
- RoleContextBuilder (L13) - Context assembly
- TaskOrchestrator (L05) - Receives dispatch results

---
*Generated: 2026-01-24 | Platform Services Documentation*
