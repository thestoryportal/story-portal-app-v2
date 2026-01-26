# Service 8/44: GoalStore

## Overview

| Property | Value |
|----------|-------|
| **Layer** | L01 (Data Layer) |
| **Module** | `L01_data_layer.services.goal_store` |
| **Status** | Fully Implemented & Healthy |
| **Dependencies** | PostgreSQL |
| **Category** | Data & Storage |

## Role in Development Environment

The **GoalStore** persists high-level objectives that agents work toward. It provides:
- Hierarchical goal structure (parent/child relationships)
- Priority-based ordering (1-10 scale)
- Success criteria definitions
- Status lifecycle tracking

This is the data layer for **L05 Planning** - goals get decomposed into plans and tasks.

## Data Model

### Goal Fields
- `id: UUID` - Unique identifier
- `agent_id: UUID` - Agent responsible for the goal
- `description: str` - Human-readable goal description
- `success_criteria: List[Dict]` - Measurable criteria for completion
- `status: GoalStatus` - Current status
- `priority: int` - Priority level (1-10, higher = more important)
- `parent_goal_id: UUID` - Optional parent for hierarchical goals
- `created_at: datetime` - Creation timestamp
- `updated_at: datetime` - Last update timestamp
- `completed_at: datetime` - Completion timestamp (when status=completed)

### GoalStatus Enum
- `PENDING` - Not yet started
- `ACTIVE` - Currently being worked on
- `COMPLETED` - Successfully achieved
- `FAILED` - Could not be achieved
- `CANCELLED` - Explicitly cancelled

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/goals/` | Create new goal |
| `GET` | `/goals/{id}` | Get goal by ID |
| `PATCH` | `/goals/{id}` | Update goal |
| `GET` | `/goals/` | List goals (filter by agent) |

## Use Cases in Your Workflow

### 1. Define a High-Level Goal
```bash
curl -X POST http://localhost:8011/goals/ \
  -H "Content-Type: application/json" \
  -d '{
    "agent_id": "550e8400-e29b-41d4-a716-446655440000",
    "description": "Implement Steam Modal component with all refinements",
    "success_criteria": [
      {"criterion": "Modal opens/closes correctly", "weight": 0.2},
      {"criterion": "Animations are smooth", "weight": 0.2},
      {"criterion": "Accessibility requirements met", "weight": 0.3},
      {"criterion": "All tests pass", "weight": 0.3}
    ],
    "priority": 8
  }'
```

### 2. Create Sub-Goals (Hierarchical)
```bash
curl -X POST http://localhost:8011/goals/ \
  -H "Content-Type: application/json" \
  -d '{
    "agent_id": "550e8400-e29b-41d4-a716-446655440000",
    "description": "Implement modal animation system",
    "parent_goal_id": "660e8400-e29b-41d4-a716-446655440001",
    "success_criteria": [
      {"criterion": "React Spring integration complete", "weight": 0.5},
      {"criterion": "60fps performance verified", "weight": 0.5}
    ],
    "priority": 7
  }'
```

### 3. Update Goal Status
```bash
# Mark goal as active
curl -X PATCH http://localhost:8011/goals/660e8400-e29b-41d4-a716-446655440001 \
  -H "Content-Type: application/json" \
  -d '{"status": "active"}'

# Mark goal as completed
curl -X PATCH http://localhost:8011/goals/660e8400-e29b-41d4-a716-446655440001 \
  -H "Content-Type: application/json" \
  -d '{"status": "completed", "completed_at": "2026-01-24T12:00:00Z"}'
```

### 4. List Agent Goals
```bash
curl "http://localhost:8011/goals/?agent_id=550e8400-e29b-41d4-a716-446655440000"
```

## Service Interactions

```
+------------------+
|    GoalStore     | <--- L01 Data Layer (PostgreSQL)
|     (L01)        |
+--------+---------+
         |
         v
+------------------+     +-------------------+
| GoalDecomposer   |     |  PlanningService  |
|     (L05)        |     |      (L05)        |
+------------------+     +-------------------+
         |
         v
+------------------+     +-------------------+
|    PlanStore     |     | TaskOrchestrator  |
|     (L01)        |     |      (L05)        |
+------------------+     +-------------------+
```

**Integration Points:**
- **GoalDecomposer (L05)**: Breaks goals into executable plans
- **PlanningService (L05)**: Orchestrates goal-to-plan workflow
- **PlanStore (L01)**: Stores generated plans
- **TaskOrchestrator (L05)**: Executes tasks derived from goals

## Goal Decomposition Flow

```
Goal (high-level objective)
   |
   v
GoalDecomposer (L05)
   |
   v
Plan (strategy with steps)
   |
   v
Tasks (executable work units)
   |
   v
Agent execution
```

## Success Criteria Structure

Define measurable criteria with optional weights:
```json
{
  "success_criteria": [
    {
      "criterion": "All unit tests pass",
      "weight": 0.3,
      "type": "automated",
      "measurement": "test_coverage >= 80%"
    },
    {
      "criterion": "Code review approved",
      "weight": 0.3,
      "type": "human",
      "required_approvers": 1
    },
    {
      "criterion": "Performance benchmarks met",
      "weight": 0.4,
      "type": "automated",
      "measurement": "latency_p95 < 100ms"
    }
  ]
}
```

## Execution Examples

```bash
# Create a goal
curl -X POST http://localhost:8011/goals/ \
  -H "Content-Type: application/json" \
  -d '{
    "agent_id": "550e8400-e29b-41d4-a716-446655440000",
    "description": "Optimize database query performance",
    "success_criteria": [
      {"criterion": "Reduce p95 latency by 50%", "type": "automated"}
    ],
    "priority": 9
  }'

# Get goal details
curl http://localhost:8011/goals/660e8400-e29b-41d4-a716-446655440001

# Update priority
curl -X PATCH http://localhost:8011/goals/660e8400-e29b-41d4-a716-446655440001 \
  -H "Content-Type: application/json" \
  -d '{"priority": 10}'

# Update status to failed
curl -X PATCH http://localhost:8011/goals/660e8400-e29b-41d4-a716-446655440001 \
  -H "Content-Type: application/json" \
  -d '{"status": "failed"}'

# List all goals
curl http://localhost:8011/goals/

# Filter by agent
curl "http://localhost:8011/goals/?agent_id=550e8400-e29b-41d4-a716-446655440000&limit=20"
```

## Implementation Status

| Component | Status |
|-----------|--------|
| Create Goal | Complete |
| Get Goal | Complete |
| Update Goal | Complete |
| List Goals | Complete |
| Agent Filter | Complete |
| JSON Criteria | Complete |
| Status Lifecycle | Complete |
| Hierarchical (parent_id) | Complete |

## Remaining Work

| Item | Priority | Description |
|------|----------|-------------|
| Status Filter | Medium | Filter by status (active, completed, etc.) |
| Get Sub-Goals | Medium | Query child goals by parent_id |
| Delete Goal | Low | Remove goals (cascade to sub-goals?) |
| Progress Tracking | Low | Calculate completion % from sub-goals |
| Redis Events | Low | Publish on goal status changes |
| Priority Reordering | Low | Bulk update priorities |

## Strengths

- **Hierarchical structure** - Parent/child relationships for complex objectives
- **Priority system** - 1-10 scale for ordering importance
- **Flexible criteria** - JSON structure for any success definition
- **Status lifecycle** - Clear progression tracking
- **Completion timestamp** - Know exactly when goals finished

## Weaknesses

- **No status filtering** - Cannot list only active goals
- **No sub-goal queries** - Must filter client-side for children
- **No progress calculation** - Manual tracking required
- **No events** - Status changes not published to Redis
- **No cascading updates** - Parent status doesn't auto-update

## Best Practices

### Goal Descriptions
Be specific and actionable:
- "Implement user authentication with OAuth2" (specific)
- "Make the app better" (too vague)

### Priority Guidelines
- **9-10**: Critical, blocking other work
- **7-8**: High priority, do soon
- **5-6**: Normal priority
- **3-4**: Low priority, nice to have
- **1-2**: Backlog, someday maybe

### Success Criteria
Include measurable outcomes:
```json
[
  {"criterion": "API latency < 100ms", "type": "automated"},
  {"criterion": "Zero critical bugs", "type": "automated"},
  {"criterion": "User acceptance complete", "type": "human"}
]
```

## Source Files

- Service: `platform/src/L01_data_layer/services/goal_store.py`
- Models: `platform/src/L01_data_layer/models/goal.py`
- Routes: `platform/src/L01_data_layer/routers/goals.py`

## Related Services

- PlanStore (L01) - Stores execution plans derived from goals
- GoalDecomposer (L05) - Breaks goals into plans
- PlanningService (L05) - Goal planning orchestration
- TaskOrchestrator (L05) - Task execution from plans
- AgentRegistry (L01) - Agent metadata

---
*Generated: 2026-01-24 | Platform Services Documentation*
