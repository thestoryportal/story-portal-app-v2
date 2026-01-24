# Service 45/52: RoleRegistry

## Overview

| Property | Value |
|----------|-------|
| **Layer** | L13 (Role Management Layer) |
| **Module** | `L13_role_management.services.role_registry` |
| **Status** | Fully Implemented & Healthy |
| **Dependencies** | PostgreSQL (optional), Redis (optional for events) |
| **Category** | Role Management / Registry |

## Role in Development Environment

The **RoleRegistry** provides centralized role lifecycle management with persistent storage. It provides:
- Role CRUD operations (create, read, update, delete)
- Role search with filtering by name, type, capabilities
- Task dispatch to find suitable roles
- PostgreSQL persistence with in-memory fallback
- Redis event publishing for role changes
- Role activation/deactivation states
- Capability-based role matching

This is **the central registry for all roles** - when agents need to find or manage roles for task execution, RoleRegistry is the authoritative source.

## Data Model

### Role
- `role_id: str` - Unique role identifier (UUID)
- `name: str` - Role name
- `description: str` - Role description
- `role_type: RoleType` - Type (human_primary, ai_primary, hybrid)
- `capabilities: List[str]` - Role capabilities
- `constraints: Dict` - Role constraints
- `skills: List[str]` - Associated skill IDs
- `is_active: bool` - Activation state
- `created_at: datetime` - Creation timestamp
- `updated_at: datetime` - Last update timestamp
- `metadata: Dict` - Additional metadata

### RoleType Enum
- `human_primary` - Role primarily for human execution
- `ai_primary` - Role primarily for AI execution
- `hybrid` - Role for collaborative human/AI execution

### RoleSearchCriteria
- `name_pattern: str` - Name pattern to match
- `role_type: RoleType` - Filter by type
- `capabilities: List[str]` - Required capabilities
- `is_active: bool` - Active state filter
- `limit: int` - Maximum results
- `offset: int` - Pagination offset

## Configuration

| Parameter | Default | Description |
|-----------|---------|-------------|
| `db_url` | None | PostgreSQL connection URL |
| `redis_url` | None | Redis URL for event publishing |
| `use_memory_fallback` | True | Fall back to in-memory if DB unavailable |

## API Methods

| Method | Description |
|--------|-------------|
| `register_role(role)` | Register a new role |
| `get_role(role_id)` | Get role by ID |
| `update_role(role_id, updates)` | Update role attributes |
| `delete_role(role_id)` | Delete a role |
| `search_roles(criteria)` | Search roles with filters |
| `dispatch_for_task(task)` | Find suitable roles for task |
| `activate_role(role_id)` | Activate a role |
| `deactivate_role(role_id)` | Deactivate a role |
| `list_roles(limit, offset)` | List all roles with pagination |
| `get_stats()` | Get registry statistics |

## Use Cases in Your Workflow

### 1. Initialize Role Registry
```python
from L13_role_management.services.role_registry import RoleRegistry

# Default initialization (in-memory)
registry = RoleRegistry()

# With PostgreSQL persistence
registry = RoleRegistry(
    db_url="postgresql://user:pass@localhost/db",
    redis_url="redis://localhost:6379"
)
```

### 2. Register a New Role
```python
from L13_role_management.models import Role, RoleType

# Create role
role = Role(
    name="Senior Developer",
    description="Experienced developer for complex tasks",
    role_type=RoleType.HYBRID,
    capabilities=["code_review", "architecture", "debugging"],
    skills=["skill-python", "skill-typescript"],
    constraints={"max_concurrent_tasks": 3}
)

# Register
registered = await registry.register_role(role)
print(f"Role registered: {registered.role_id}")
```

### 3. Get Role by ID
```python
role = await registry.get_role("role-123")

if role:
    print(f"Role: {role.name}")
    print(f"Type: {role.role_type.value}")
    print(f"Capabilities: {role.capabilities}")
else:
    print("Role not found")
```

### 4. Update Role
```python
updates = {
    "capabilities": ["code_review", "architecture", "debugging", "mentoring"],
    "constraints": {"max_concurrent_tasks": 5}
}

updated = await registry.update_role("role-123", updates)
print(f"Role updated: {updated.updated_at}")
```

### 5. Search Roles
```python
from L13_role_management.models import RoleSearchCriteria

# Search by capabilities
criteria = RoleSearchCriteria(
    capabilities=["code_review"],
    role_type=RoleType.AI_PRIMARY,
    is_active=True,
    limit=10
)

roles = await registry.search_roles(criteria)
print(f"Found {len(roles)} matching roles")
for role in roles:
    print(f"  - {role.name}: {role.capabilities}")
```

### 6. Dispatch Task to Role
```python
from L13_role_management.models import Task

task = Task(
    task_id="task-456",
    description="Review pull request for security issues",
    required_capabilities=["code_review", "security"],
    priority="high"
)

# Find suitable roles
suitable_roles = await registry.dispatch_for_task(task)

if suitable_roles:
    print(f"Dispatching to: {suitable_roles[0].name}")
else:
    print("No suitable roles found")
```

### 7. Activate/Deactivate Roles
```python
# Deactivate role (e.g., for maintenance)
await registry.deactivate_role("role-123")
print("Role deactivated")

# Reactivate role
await registry.activate_role("role-123")
print("Role activated")
```

### 8. List All Roles
```python
# Paginated listing
roles = await registry.list_roles(limit=20, offset=0)

print(f"Roles (page 1):")
for role in roles:
    status = "active" if role.is_active else "inactive"
    print(f"  [{status}] {role.name} ({role.role_type.value})")
```

### 9. Delete Role
```python
deleted = await registry.delete_role("role-123")

if deleted:
    print("Role deleted successfully")
else:
    print("Role not found")
```

### 10. Get Registry Statistics
```python
stats = registry.get_stats()

print(f"Total roles: {stats['total_roles']}")
print(f"Active roles: {stats['active_roles']}")
print(f"By type:")
print(f"  Human: {stats['human_primary']}")
print(f"  AI: {stats['ai_primary']}")
print(f"  Hybrid: {stats['hybrid']}")
print(f"Registrations: {stats['registrations']}")
print(f"Lookups: {stats['lookups']}")
```

## Service Interactions

```
+------------------+
|   RoleRegistry   | <--- L13 Role Management Layer
|      (L13)       |
+--------+---------+
         |
   Provides:
         |
+--------+--------+--------+
|        |        |        |
v        v        v        v
Role     Role     Task     Event
CRUD     Search   Dispatch Publish
```

**Integration Points:**
- **RoleDispatcher (L13)**: Uses registry to find roles
- **ClassificationEngine (L13)**: Queries role capabilities
- **PostgreSQL (External)**: Persistent role storage
- **Redis (External)**: Event publishing (role.registered, role.updated, role.deleted)

## Event Publishing

```
Role Events (via Redis):

role.registered
├─ role_id
├─ name
├─ role_type
└─ timestamp

role.updated
├─ role_id
├─ updated_fields
└─ timestamp

role.deleted
├─ role_id
└─ timestamp

role.activated / role.deactivated
├─ role_id
└─ timestamp
```

## Error Codes

| Code | Description | Retryable |
|------|-------------|-----------|
| E13001 | Role not found | No |
| E13002 | Role already exists | No |
| E13003 | Invalid role data | No |
| E13004 | Database error | Yes |
| E13005 | Dispatch failed | Yes |

## Execution Examples

```python
# Complete role management workflow
from L13_role_management.services.role_registry import RoleRegistry
from L13_role_management.models import Role, RoleType, RoleSearchCriteria

# Initialize
registry = RoleRegistry(
    db_url="postgresql://localhost/platform",
    redis_url="redis://localhost:6379"
)

# 1. Register multiple roles
roles_to_create = [
    Role(
        name="Code Reviewer",
        description="Reviews code for quality and security",
        role_type=RoleType.AI_PRIMARY,
        capabilities=["code_review", "security_analysis"],
        skills=["skill-review"],
    ),
    Role(
        name="Project Manager",
        description="Manages project planning and coordination",
        role_type=RoleType.HUMAN_PRIMARY,
        capabilities=["planning", "coordination", "decision_making"],
        skills=["skill-management"],
    ),
    Role(
        name="Full Stack Developer",
        description="Develops frontend and backend features",
        role_type=RoleType.HYBRID,
        capabilities=["frontend", "backend", "database"],
        skills=["skill-react", "skill-python"],
    ),
]

print("Registering roles...")
for role in roles_to_create:
    registered = await registry.register_role(role)
    print(f"  Registered: {registered.name} ({registered.role_id})")

# 2. Search for AI roles with code review capability
print("\nSearching for AI code reviewers...")
criteria = RoleSearchCriteria(
    role_type=RoleType.AI_PRIMARY,
    capabilities=["code_review"],
    is_active=True
)
results = await registry.search_roles(criteria)
print(f"Found {len(results)} roles")

# 3. Update role capabilities
if results:
    role = results[0]
    print(f"\nUpdating {role.name}...")
    updated = await registry.update_role(
        role.role_id,
        {"capabilities": role.capabilities + ["performance_analysis"]}
    )
    print(f"  New capabilities: {updated.capabilities}")

# 4. Dispatch a task
print("\nDispatching task...")
task = Task(
    task_id="task-001",
    description="Review authentication module changes",
    required_capabilities=["code_review", "security_analysis"],
    priority="high"
)
suitable = await registry.dispatch_for_task(task)
print(f"Suitable roles: {[r.name for r in suitable]}")

# 5. Get statistics
print("\nRegistry statistics:")
stats = registry.get_stats()
for key, value in stats.items():
    print(f"  {key}: {value}")
```

## Implementation Status

| Component | Status |
|-----------|--------|
| RoleRegistry class | Complete |
| register_role() | Complete |
| get_role() | Complete |
| update_role() | Complete |
| delete_role() | Complete |
| search_roles() | Complete |
| dispatch_for_task() | Complete |
| PostgreSQL persistence | Complete |
| In-memory fallback | Complete |
| Redis event publishing | Complete |
| Statistics | Complete |

## Remaining Work

| Item | Priority | Description |
|------|----------|-------------|
| Role versioning | Medium | Track role history |
| Bulk operations | Medium | Batch register/update |
| Role inheritance | Low | Roles extending other roles |
| Role templates | Low | Predefined role templates |
| GraphQL API | Low | GraphQL query support |

## Strengths

- **Dual storage** - PostgreSQL with in-memory fallback
- **Event-driven** - Redis publishing for real-time updates
- **Flexible search** - Multi-criteria filtering
- **Task dispatch** - Capability-based role matching
- **Activation control** - Enable/disable roles dynamically
- **Statistics** - Built-in usage tracking

## Weaknesses

- **No versioning** - Can't track role history
- **Single database** - No replication support
- **Basic dispatch** - Simple capability matching
- **No inheritance** - Roles can't extend others
- **In-memory limits** - Memory storage for fallback

## Best Practices

### Role Design
Create specific, well-defined roles:
```python
# Good: Specific capabilities
Role(
    name="Security Reviewer",
    capabilities=["security_analysis", "vulnerability_assessment"],
    role_type=RoleType.AI_PRIMARY
)

# Avoid: Overly broad roles
Role(
    name="Everything Role",
    capabilities=["*"],  # Too broad
)
```

### Capability Naming
Use consistent capability naming:
```python
# Good: Verb_noun pattern
capabilities = ["code_review", "security_analysis", "test_execution"]

# Avoid: Inconsistent naming
capabilities = ["review", "SecurityCheck", "run-tests"]
```

### Event Handling
Subscribe to role events:
```python
# In Redis subscriber
async def handle_role_event(event):
    if event.type == "role.registered":
        print(f"New role: {event.data['name']}")
    elif event.type == "role.deleted":
        # Clean up references
        await cleanup_role_references(event.data['role_id'])
```

## Source Files

- Service: `platform/src/L13_role_management/services/role_registry.py`
- Models: `platform/src/L13_role_management/models/`
- Spec: L13 Role Management Layer specification

## Related Services

- RoleDispatcher (L13) - Uses registry for dispatch
- ClassificationEngine (L13) - Queries role types
- RoleContextBuilder (L13) - Builds contexts for roles
- SkillStore (L14) - Links skills to roles

---
*Generated: 2026-01-24 | Platform Services Documentation*
