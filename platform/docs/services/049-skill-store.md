# Service 49/52: SkillStore

## Overview

| Property | Value |
|----------|-------|
| **Layer** | L14 (Skill Library Layer) |
| **Module** | `L14_skill_library.services.skill_store` |
| **Status** | Fully Implemented & Healthy |
| **Dependencies** | None (in-memory storage) |
| **Category** | Skill Library / Storage |

## Role in Development Environment

The **SkillStore** provides CRUD operations for skill definitions with multi-index lookups. It provides:
- Skill create, read, update, delete operations
- Multi-index lookups (by name, agent, category)
- Agent skill assignment
- Skill activation and deprecation
- Version tracking
- Skill listing and filtering

This is **the central repository for skill definitions** - when roles need skill definitions or agents need to manage their skills, SkillStore is the authoritative source.

## Data Model

### Skill
- `skill_id: str` - Unique skill identifier (UUID)
- `name: str` - Skill name (unique)
- `description: str` - Skill description
- `category: str` - Skill category (e.g., "development", "analysis")
- `version: str` - Semantic version
- `content: str` - YAML skill definition
- `metadata: Dict` - Additional metadata
- `agent_ids: List[str]` - Assigned agent IDs
- `status: SkillStatus` - Skill status
- `created_at: datetime` - Creation timestamp
- `updated_at: datetime` - Last update timestamp

### SkillStatus Enum
- `active` - Skill is available for use
- `deprecated` - Skill is marked for removal
- `draft` - Skill is in development

### SkillIndex
- `_name_index: Dict[str, str]` - Name to skill ID
- `_agent_index: Dict[str, List[str]]` - Agent ID to skill IDs
- `_category_index: Dict[str, List[str]]` - Category to skill IDs

## Configuration

| Parameter | Default | Description |
|-----------|---------|-------------|
| `storage_path` | None | Optional file-based persistence |
| `enable_versioning` | True | Track skill versions |

## API Methods

| Method | Description |
|--------|-------------|
| `create(skill)` | Create new skill |
| `get(skill_id)` | Get skill by ID |
| `get_by_name(name)` | Get skill by name |
| `list(filters)` | List skills with filters |
| `update(skill_id, updates)` | Update skill |
| `delete(skill_id)` | Delete skill |
| `assign_to_agent(skill_id, agent_id)` | Assign skill to agent |
| `unassign_from_agent(skill_id, agent_id)` | Remove agent assignment |
| `get_by_agent(agent_id)` | Get skills for agent |
| `get_by_category(category)` | Get skills in category |
| `activate(skill_id)` | Activate skill |
| `deprecate(skill_id)` | Mark skill as deprecated |
| `get_stats()` | Get store statistics |

## Use Cases in Your Workflow

### 1. Initialize Skill Store
```python
from L14_skill_library.services.skill_store import SkillStore

# Default initialization (in-memory)
store = SkillStore()

# With file persistence
store = SkillStore(storage_path="/path/to/skills.json")
```

### 2. Create a Skill
```python
from L14_skill_library.models import Skill

skill = Skill(
    name="python-developer",
    description="Python development expertise",
    category="development",
    version="1.0.0",
    content="""
role: Python Developer
responsibilities:
  - Write clean, maintainable Python code
  - Follow PEP 8 style guidelines
  - Implement unit tests
tools:
  - pytest
  - black
  - mypy
"""
)

created = await store.create(skill)
print(f"Skill created: {created.skill_id}")
```

### 3. Get Skill by ID or Name
```python
# By ID
skill = await store.get("skill-123")

# By name
skill = await store.get_by_name("python-developer")

if skill:
    print(f"Skill: {skill.name}")
    print(f"Category: {skill.category}")
    print(f"Version: {skill.version}")
    print(f"Status: {skill.status.value}")
```

### 4. List Skills with Filters
```python
# List all active skills
skills = await store.list(status="active")

# List by category
dev_skills = await store.list(category="development")

# List with pagination
page = await store.list(limit=10, offset=20)

print(f"Found {len(skills)} skills")
for skill in skills:
    print(f"  - {skill.name} ({skill.category})")
```

### 5. Update Skill
```python
updates = {
    "description": "Advanced Python development expertise",
    "version": "1.1.0",
    "content": updated_yaml_content
}

updated = await store.update("skill-123", updates)
print(f"Skill updated: v{updated.version}")
```

### 6. Assign Skill to Agent
```python
# Assign skill to an agent
await store.assign_to_agent("skill-123", "agent-456")

# Check assignment
skill = await store.get("skill-123")
print(f"Assigned to: {skill.agent_ids}")

# Unassign
await store.unassign_from_agent("skill-123", "agent-456")
```

### 7. Get Skills by Agent
```python
# Get all skills for an agent
agent_skills = await store.get_by_agent("agent-456")

print(f"Agent has {len(agent_skills)} skills:")
for skill in agent_skills:
    print(f"  - {skill.name}")
```

### 8. Get Skills by Category
```python
# Get all development skills
dev_skills = await store.get_by_category("development")

# Get all analysis skills
analysis_skills = await store.get_by_category("analysis")

print(f"Development: {len(dev_skills)}")
print(f"Analysis: {len(analysis_skills)}")
```

### 9. Activate/Deprecate Skills
```python
# Deprecate old skill
await store.deprecate("skill-old-123")
deprecated = await store.get("skill-old-123")
print(f"Status: {deprecated.status.value}")  # deprecated

# Activate skill
await store.activate("skill-new-456")
```

### 10. Get Store Statistics
```python
stats = store.get_stats()

print(f"Skill Store Statistics:")
print(f"  Total skills: {stats['total_skills']}")
print(f"  Active: {stats['active_skills']}")
print(f"  Deprecated: {stats['deprecated_skills']}")
print(f"  Draft: {stats['draft_skills']}")
print(f"  Categories: {stats['categories']}")
print(f"  Assigned agents: {stats['agents_with_skills']}")
```

## Service Interactions

```
+------------------+
|    SkillStore    | <--- L14 Skill Library Layer
|      (L14)       |
+--------+---------+
         |
   Provides:
         |
+--------+--------+--------+
|        |        |        |
v        v        v        v
CRUD     Index    Agent    Lifecycle
Ops      Lookups  Assign   Management
```

**Integration Points:**
- **RoleContextBuilder (L13)**: Loads skills for context
- **SkillValidator (L14)**: Validates before storing
- **SkillGenerator (L14)**: Creates skills for store
- **SkillOptimizer (L14)**: Optimizes skill content

## Index Architecture

```
Skill Indexing:

Primary Storage:
+-------------------+
|   _skills: Dict   |
|  skill_id → Skill |
+-------------------+

Secondary Indexes:
+-------------------+     +-------------------+     +-------------------+
|   _name_index     |     |   _agent_index    |     |  _category_index  |
|  name → skill_id  |     | agent_id → [ids]  |     | category → [ids]  |
+-------------------+     +-------------------+     +-------------------+

Index Maintenance:
- CREATE: Add to all indexes
- UPDATE: Update affected indexes
- DELETE: Remove from all indexes
- ASSIGN: Update agent index
```

## Error Codes

| Code | Description | Retryable |
|------|-------------|-----------|
| E14001 | Skill not found | No |
| E14002 | Skill already exists | No |
| E14003 | Invalid skill data | No |
| E14004 | Agent assignment failed | Yes |
| E14005 | Storage error | Yes |

## Execution Examples

```python
# Complete skill store workflow
from L14_skill_library.services.skill_store import SkillStore
from L14_skill_library.models import Skill, SkillStatus

# Initialize
store = SkillStore()

# 1. Create multiple skills
skills_to_create = [
    Skill(
        name="python-developer",
        description="Python development expertise",
        category="development",
        version="1.0.0",
        content="""
role: Python Developer
responsibilities:
  - Write Python code
  - Create unit tests
tools:
  - pytest
  - black
"""
    ),
    Skill(
        name="code-reviewer",
        description="Code review expertise",
        category="review",
        version="1.0.0",
        content="""
role: Code Reviewer
responsibilities:
  - Review code changes
  - Identify issues
tools:
  - github
  - reviewbot
"""
    ),
    Skill(
        name="data-analyst",
        description="Data analysis expertise",
        category="analysis",
        version="1.0.0",
        content="""
role: Data Analyst
responsibilities:
  - Analyze datasets
  - Generate insights
tools:
  - pandas
  - matplotlib
"""
    ),
]

print("Creating skills...")
created_ids = []
for skill in skills_to_create:
    created = await store.create(skill)
    created_ids.append(created.skill_id)
    print(f"  Created: {skill.name} ({created.skill_id})")

# 2. List by category
print("\nSkills by category:")
for category in ["development", "review", "analysis"]:
    skills = await store.get_by_category(category)
    print(f"  {category}: {[s.name for s in skills]}")

# 3. Assign to agents
print("\nAssigning skills to agents...")
await store.assign_to_agent(created_ids[0], "agent-dev-1")
await store.assign_to_agent(created_ids[0], "agent-dev-2")
await store.assign_to_agent(created_ids[1], "agent-reviewer-1")
await store.assign_to_agent(created_ids[2], "agent-analyst-1")

# 4. Get skills by agent
print("\nSkills by agent:")
for agent_id in ["agent-dev-1", "agent-reviewer-1"]:
    skills = await store.get_by_agent(agent_id)
    print(f"  {agent_id}: {[s.name for s in skills]}")

# 5. Update a skill
print("\nUpdating python-developer...")
updated = await store.update(
    created_ids[0],
    {
        "version": "1.1.0",
        "description": "Advanced Python development expertise"
    }
)
print(f"  New version: {updated.version}")

# 6. Deprecate old skill
print("\nDeprecating old skill...")
await store.deprecate(created_ids[2])
deprecated = await store.get(created_ids[2])
print(f"  {deprecated.name} status: {deprecated.status.value}")

# 7. List active only
print("\nActive skills:")
active = await store.list(status="active")
for skill in active:
    print(f"  - {skill.name}")

# 8. Statistics
print("\nStore Statistics:")
stats = store.get_stats()
for key, value in stats.items():
    print(f"  {key}: {value}")
```

## Implementation Status

| Component | Status |
|-----------|--------|
| SkillStore class | Complete |
| create() | Complete |
| get() / get_by_name() | Complete |
| list() | Complete |
| update() | Complete |
| delete() | Complete |
| assign_to_agent() | Complete |
| unassign_from_agent() | Complete |
| get_by_agent() | Complete |
| get_by_category() | Complete |
| activate() / deprecate() | Complete |
| Index maintenance | Complete |
| Statistics | Complete |

## Remaining Work

| Item | Priority | Description |
|------|----------|-------------|
| Database persistence | High | PostgreSQL storage |
| Skill versioning history | Medium | Track all versions |
| Full-text search | Medium | Search skill content |
| Skill dependencies | Low | Skills depending on other skills |
| Import/export | Low | Bulk skill operations |

## Strengths

- **Fast lookups** - Multi-index architecture
- **Flexible queries** - By ID, name, agent, category
- **Agent tracking** - Skill-agent assignments
- **Lifecycle management** - Active/deprecated states
- **Simple API** - Clean CRUD operations
- **No dependencies** - Self-contained

## Weaknesses

- **In-memory only** - No persistent storage by default
- **No version history** - Only tracks current version
- **Simple text search** - No full-text search
- **No dependencies** - Skills can't depend on other skills
- **Single node** - No replication
- **Memory limits** - Constrained by available memory

## Best Practices

### Skill Naming
Use consistent naming conventions:
```python
# Good: Lowercase, hyphenated
Skill(name="python-developer")
Skill(name="code-reviewer")
Skill(name="data-analyst")

# Avoid: Inconsistent naming
Skill(name="PythonDeveloper")
Skill(name="Code_Reviewer")
Skill(name="dataanalyst")
```

### Category Organization
Organize skills into clear categories:
```python
# Good: Clear categories
categories = ["development", "review", "analysis", "testing", "deployment"]

# Avoid: Too granular
categories = ["python-dev", "js-dev", "ts-dev"]  # Use "development"
```

### Version Management
Use semantic versioning:
```python
# Major.Minor.Patch
skill.version = "1.0.0"  # Initial release
skill.version = "1.1.0"  # New feature
skill.version = "1.1.1"  # Bug fix
skill.version = "2.0.0"  # Breaking change
```

## Source Files

- Service: `platform/src/L14_skill_library/services/skill_store.py`
- Models: `platform/src/L14_skill_library/models/`
- Spec: L14 Skill Library Layer specification

## Related Services

- SkillValidator (L14) - Validates skill content
- SkillGenerator (L14) - Generates new skills
- SkillOptimizer (L14) - Optimizes skill content
- RoleContextBuilder (L13) - Loads skills for context

---
*Generated: 2026-01-24 | Platform Services Documentation*
