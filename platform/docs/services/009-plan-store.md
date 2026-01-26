# Service 9/44: PlanStore

## Overview

| Property | Value |
|----------|-------|
| **Layer** | L01 (Data Layer) |
| **Module** | `L01_data_layer.services.plan_store` |
| **Status** | Fully Implemented & Healthy |
| **Dependencies** | PostgreSQL |
| **Category** | Data & Storage |

## Role in Development Environment

The **PlanStore** is the persistence layer for execution plans and their tasks. It bridges the gap between high-level Goals (from GoalStore) and executable work units. It provides:
- Plan persistence with step definitions
- Task CRUD with sequence ordering
- Status lifecycle tracking for both plans and tasks
- Input/output data storage for task execution

This is **the execution backbone** - when the L05 PlanningService generates plans from goals, they're stored here. The TaskOrchestrator then pulls tasks from here to execute.

## Data Model

### Plan Fields
- `id: UUID` - Unique identifier
- `goal_id: UUID` - Associated goal
- `agent_id: UUID` - Agent assigned to execute
- `plan_type: str` - Execution type (default: "sequential")
- `steps: List[Dict]` - Ordered step definitions
- `status: PlanStatus` - Current status
- `current_step: int` - Current execution step index
- `created_at: datetime` - Creation timestamp
- `updated_at: datetime` - Last update timestamp

### PlanStatus Enum
- `DRAFT` - Plan created but not started
- `ACTIVE` - Currently executing
- `COMPLETED` - All steps finished successfully
- `FAILED` - Execution failed
- `CANCELLED` - Explicitly cancelled

### Task Fields
- `id: UUID` - Unique identifier
- `plan_id: UUID` - Parent plan
- `agent_id: UUID` - Agent assigned to task
- `description: str` - Human-readable task description
- `task_type: str` - Optional task type classification
- `input_data: Dict` - Input data for task execution
- `output_data: Dict` - Output data after execution
- `status: TaskStatus` - Current status
- `sequence_order: int` - Execution order within plan
- `created_at: datetime` - Creation timestamp
- `started_at: datetime` - Execution start time
- `completed_at: datetime` - Completion time

### TaskStatus Enum
- `PENDING` - Not yet started
- `RUNNING` - Currently executing
- `COMPLETED` - Successfully finished
- `FAILED` - Execution failed
- `BLOCKED` - Waiting on dependencies
- `SKIPPED` - Intentionally skipped

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/plans/` | Create new plan |
| `GET` | `/plans/{id}` | Get plan by ID |
| `PATCH` | `/plans/{id}` | Update plan |
| `POST` | `/tasks/` | Create new task |
| `GET` | `/tasks/{id}` | Get task by ID |
| `PATCH` | `/tasks/{id}` | Update task |
| `GET` | `/tasks/` | List tasks (filter by plan) |

## Use Cases in Your Workflow

### 1. Create Plan from Goal Decomposition
```bash
curl -X POST http://localhost:8011/plans/ \
  -H "Content-Type: application/json" \
  -d '{
    "goal_id": "660e8400-e29b-41d4-a716-446655440001",
    "agent_id": "550e8400-e29b-41d4-a716-446655440000",
    "plan_type": "sequential",
    "steps": [
      {"step": 1, "action": "analyze_requirements", "description": "Parse and understand requirements"},
      {"step": 2, "action": "design_solution", "description": "Create solution architecture"},
      {"step": 3, "action": "implement", "description": "Write the code"},
      {"step": 4, "action": "test", "description": "Run tests and verify"},
      {"step": 5, "action": "review", "description": "Code review and polish"}
    ]
  }'
```

### 2. Create Tasks for Plan Execution
```bash
# Create first task
curl -X POST http://localhost:8011/tasks/ \
  -H "Content-Type: application/json" \
  -d '{
    "plan_id": "770e8400-e29b-41d4-a716-446655440002",
    "agent_id": "550e8400-e29b-41d4-a716-446655440000",
    "description": "Analyze modal requirements from specification",
    "task_type": "analysis",
    "input_data": {
      "spec_path": "docs/STEAM-MODAL-SPECIFICATION.md",
      "focus_areas": ["animations", "accessibility", "state-management"]
    },
    "sequence_order": 1
  }'

# Create subsequent task
curl -X POST http://localhost:8011/tasks/ \
  -H "Content-Type: application/json" \
  -d '{
    "plan_id": "770e8400-e29b-41d4-a716-446655440002",
    "agent_id": "550e8400-e29b-41d4-a716-446655440000",
    "description": "Implement modal animation system",
    "task_type": "implementation",
    "input_data": {
      "depends_on": "analysis_output",
      "target_files": ["src/components/steam-modal/"]
    },
    "sequence_order": 2
  }'
```

### 3. Update Task Status During Execution
```bash
# Start task execution
curl -X PATCH http://localhost:8011/tasks/880e8400-e29b-41d4-a716-446655440003 \
  -H "Content-Type: application/json" \
  -d '{
    "status": "running",
    "started_at": "2026-01-24T10:00:00Z"
  }'

# Complete task with output
curl -X PATCH http://localhost:8011/tasks/880e8400-e29b-41d4-a716-446655440003 \
  -H "Content-Type: application/json" \
  -d '{
    "status": "completed",
    "completed_at": "2026-01-24T10:30:00Z",
    "output_data": {
      "files_modified": ["SteamModal.tsx", "animations.ts"],
      "tests_added": 5,
      "coverage": 0.85
    }
  }'
```

### 4. Track Plan Progress
```bash
# Get plan with current step
curl http://localhost:8011/plans/770e8400-e29b-41d4-a716-446655440002

# Advance to next step
curl -X PATCH http://localhost:8011/plans/770e8400-e29b-41d4-a716-446655440002 \
  -H "Content-Type: application/json" \
  -d '{"current_step": 2}'

# Mark plan as complete
curl -X PATCH http://localhost:8011/plans/770e8400-e29b-41d4-a716-446655440002 \
  -H "Content-Type: application/json" \
  -d '{"status": "completed"}'
```

### 5. List Tasks for a Plan
```bash
# All tasks for a plan (ordered by sequence)
curl "http://localhost:8011/tasks/?plan_id=770e8400-e29b-41d4-a716-446655440002"

# Recent tasks across all plans
curl "http://localhost:8011/tasks/?limit=20"
```

## Service Interactions

```
+------------------+
|    GoalStore     |
|     (L01)        |
+--------+---------+
         |
         v Goals feed into planning
+------------------+
|  GoalDecomposer  |
|     (L05)        |
+--------+---------+
         |
         v Creates plans/tasks
+------------------+
|    PlanStore     | <--- L01 Data Layer (PostgreSQL)
|     (L01)        |
+--------+---------+
         |
         v Tasks executed by
+------------------+     +-------------------+
| TaskOrchestrator |     |  ExecutionEngine  |
|     (L05)        |     |      (L05)        |
+------------------+     +-------------------+
         |
         v Results stored in
+------------------+     +-------------------+
|  EvaluationStore |     |    EventStore     |
|     (L01)        |     |      (L01)        |
+------------------+     +-------------------+
```

**Integration Points:**
- **GoalStore (L01)**: Plans are created from goals (goal_id reference)
- **GoalDecomposer (L05)**: Generates plans from goals, stores via PlanStore
- **TaskOrchestrator (L05)**: Pulls pending tasks, executes them
- **ExecutionEngine (L05)**: Runs task logic, updates status
- **EvaluationStore (L01)**: Stores task evaluation results
- **EventStore (L01)**: Publishes task lifecycle events

## Plan-to-Task Flow

```
Goal (what to achieve)
   |
   v
Plan (strategy)
   ├── steps: [{step: 1, ...}, {step: 2, ...}]
   └── status: draft -> active -> completed
   |
   v
Tasks (executable units)
   ├── Task 1 (sequence_order: 1)
   │   └── status: pending -> running -> completed
   ├── Task 2 (sequence_order: 2)
   │   └── status: pending (waiting)
   └── Task 3 (sequence_order: 3)
       └── status: pending (waiting)
```

## Execution Examples

```bash
# Create a plan
curl -X POST http://localhost:8011/plans/ \
  -H "Content-Type: application/json" \
  -d '{
    "goal_id": "660e8400-e29b-41d4-a716-446655440001",
    "agent_id": "550e8400-e29b-41d4-a716-446655440000",
    "plan_type": "sequential",
    "steps": [
      {"step": 1, "action": "research"},
      {"step": 2, "action": "implement"},
      {"step": 3, "action": "test"}
    ]
  }'

# Get plan
curl http://localhost:8011/plans/770e8400-e29b-41d4-a716-446655440002

# Update plan status
curl -X PATCH http://localhost:8011/plans/770e8400-e29b-41d4-a716-446655440002 \
  -d '{"status": "active"}'

# Create task
curl -X POST http://localhost:8011/tasks/ \
  -H "Content-Type: application/json" \
  -d '{
    "plan_id": "770e8400-e29b-41d4-a716-446655440002",
    "agent_id": "550e8400-e29b-41d4-a716-446655440000",
    "description": "Research existing implementations",
    "sequence_order": 1
  }'

# Get task
curl http://localhost:8011/tasks/880e8400-e29b-41d4-a716-446655440003

# Update task status
curl -X PATCH http://localhost:8011/tasks/880e8400-e29b-41d4-a716-446655440003 \
  -d '{"status": "running"}'

# List tasks by plan
curl "http://localhost:8011/tasks/?plan_id=770e8400-e29b-41d4-a716-446655440002"
```

## Step Structure Examples

### Sequential Plan Steps
```json
{
  "steps": [
    {
      "step": 1,
      "action": "analyze",
      "description": "Analyze requirements",
      "estimated_duration": "5m"
    },
    {
      "step": 2,
      "action": "implement",
      "description": "Write implementation",
      "estimated_duration": "30m"
    },
    {
      "step": 3,
      "action": "test",
      "description": "Run tests",
      "estimated_duration": "10m"
    }
  ]
}
```

### Parallel Plan Steps
```json
{
  "plan_type": "parallel",
  "steps": [
    {
      "step": 1,
      "parallel_group": "A",
      "actions": [
        {"action": "lint", "agent": "linter"},
        {"action": "typecheck", "agent": "typechecker"}
      ]
    },
    {
      "step": 2,
      "depends_on": 1,
      "action": "build"
    }
  ]
}
```

## Implementation Status

| Component | Status |
|-----------|--------|
| Create Plan | Complete |
| Get Plan | Complete |
| Update Plan | Complete |
| Create Task | Complete |
| Get Task | Complete |
| Update Task | Complete |
| List Tasks | Complete |
| Plan-Task Link | Complete |
| Sequence Ordering | Complete |
| PostgreSQL Integration | Complete |

## Remaining Work

| Item | Priority | Description |
|------|----------|-------------|
| List Plans | Medium | Query plans by goal_id or status |
| Delete Plan | Medium | Remove plan and cascade to tasks |
| Delete Task | Medium | Remove individual tasks |
| Task Dependencies | Medium | Block tasks on other tasks |
| Batch Task Create | Low | Create multiple tasks at once |
| Plan Templates | Low | Reusable plan structures |
| Redis Events | Low | Publish on status changes |
| Execution Metrics | Low | Track timing, success rates |

## Strengths

- **Goal-to-Task linkage** - Clear hierarchy from goals to executable work
- **Sequence ordering** - Tasks execute in defined order
- **Input/output data** - Pass data between tasks
- **Timestamp tracking** - Know when tasks started/completed
- **Flexible steps** - Store any step structure as JSON
- **Status lifecycle** - Clear progression tracking

## Weaknesses

- **No list plans** - Cannot query plans by goal or status
- **No task dependencies** - Only sequence order, no DAG support
- **No deletion** - Cannot remove plans or tasks
- **No events** - Status changes not published to Redis
- **No parallel execution** - Sequence order only, no parallel groups
- **No plan templates** - Must create from scratch each time

## Best Practices

### Plan Design
Keep plans focused and manageable:
- 3-7 steps for typical plans
- One agent per plan when possible
- Clear step descriptions

### Task Granularity
Right-size tasks:
- Each task = one coherent unit of work
- Not too large (hard to track)
- Not too small (overhead)

### Status Updates
Track progress accurately:
```python
# Start task
await plan_store.update_task(task_id, TaskUpdate(
    status=TaskStatus.RUNNING,
    started_at=datetime.utcnow()
))

# Complete with output
await plan_store.update_task(task_id, TaskUpdate(
    status=TaskStatus.COMPLETED,
    completed_at=datetime.utcnow(),
    output_data={"result": "success", "files": [...]}
))
```

### Input/Output Data
Structure task data consistently:
```json
{
  "input_data": {
    "source_files": ["a.py", "b.py"],
    "config": {"key": "value"}
  },
  "output_data": {
    "result": "success",
    "artifacts": ["output.json"],
    "metrics": {"lines_changed": 42}
  }
}
```

## Source Files

- Service: `platform/src/L01_data_layer/services/plan_store.py`
- Models: `platform/src/L01_data_layer/models/plan.py`
- Routes: `platform/src/L01_data_layer/routers/plans.py`

## Related Services

- GoalStore (L01) - Goals that plans fulfill
- GoalDecomposer (L05) - Creates plans from goals
- PlanningService (L05) - Planning orchestration
- TaskOrchestrator (L05) - Executes tasks from plans
- EvaluationStore (L01) - Task evaluation results
- EventStore (L01) - Task lifecycle events

---
*Generated: 2026-01-24 | Platform Services Documentation*
