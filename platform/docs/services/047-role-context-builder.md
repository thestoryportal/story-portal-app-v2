# Service 47/52: RoleContextBuilder

## Overview

| Property | Value |
|----------|-------|
| **Layer** | L13 (Role Management Layer) |
| **Module** | `L13_role_management.services.role_context_builder` |
| **Status** | Fully Implemented & Healthy |
| **Dependencies** | SkillStore (L14) |
| **Category** | Role Management / Context Assembly |

## Role in Development Environment

The **RoleContextBuilder** assembles comprehensive role contexts for task execution with token budget management. It provides:
- System prompt assembly from role definition
- Skill context loading and formatting
- Constraint context building
- Project/task context injection
- Token budget management and estimation
- Context extension and merging
- Minimal context fallback

This is **the context assembler for role execution** - when a role needs to execute a task, RoleContextBuilder assembles all necessary context (skills, constraints, examples) within token limits.

## Data Model

### RoleContext
- `role_id: str` - Role identifier
- `system_prompt: str` - Assembled system prompt
- `skill_context: str` - Loaded skill definitions
- `constraint_context: str` - Role constraints
- `project_context: str` - Project-specific context
- `examples: List[str]` - Few-shot examples
- `token_count: int` - Estimated total tokens
- `metadata: Dict` - Assembly metadata

### ContextSection
- `SYSTEM_PROMPT` - Base role instructions
- `SKILLS` - Skill definitions
- `CONSTRAINTS` - Behavioral constraints
- `PROJECT` - Project-specific info
- `EXAMPLES` - Few-shot examples
- `TASK` - Current task details

### TokenBudget
- `total_budget: int` - Maximum tokens allowed
- `system_prompt_budget: int` - Tokens for system prompt
- `skill_budget: int` - Tokens for skills
- `constraint_budget: int` - Tokens for constraints
- `project_budget: int` - Tokens for project context
- `example_budget: int` - Tokens for examples
- `task_budget: int` - Tokens for task

## Configuration

| Parameter | Default | Description |
|-----------|---------|-------------|
| `default_token_budget` | 8000 | Default token budget |
| `chars_per_token` | 4 | Characters per token estimate |
| `skill_store` | SkillStore() | Skill store for loading |
| `include_examples` | True | Include few-shot examples |

## API Methods

| Method | Description |
|--------|-------------|
| `build_context(role, task, budget)` | Build full role context |
| `build_minimal_context(role)` | Build minimal context |
| `extend_context(context, extension)` | Extend existing context |
| `merge_contexts(contexts)` | Merge multiple contexts |
| `estimate_tokens(text)` | Estimate token count |
| `get_remaining_budget(context, budget)` | Get remaining token budget |
| `get_stats()` | Get builder statistics |

## Use Cases in Your Workflow

### 1. Initialize Context Builder
```python
from L13_role_management.services.role_context_builder import RoleContextBuilder
from L14_skill_library.services.skill_store import SkillStore

# Default initialization
builder = RoleContextBuilder()

# With custom skill store
skill_store = SkillStore()
builder = RoleContextBuilder(
    skill_store=skill_store,
    default_token_budget=12000
)
```

### 2. Build Full Role Context
```python
from L13_role_management.models import Role, TokenBudget

role = Role(
    role_id="role-dev",
    name="Senior Developer",
    description="Experienced developer for code review",
    skills=["skill-python", "skill-review"],
    constraints={"no_production_access": True}
)

task = Task(
    task_id="task-123",
    description="Review authentication module changes"
)

budget = TokenBudget(total_budget=8000)

context = await builder.build_context(role, task, budget)

print(f"Context assembled:")
print(f"  Token count: {context.token_count}")
print(f"  System prompt: {len(context.system_prompt)} chars")
print(f"  Skills loaded: {len(context.skill_context)} chars")
print(f"  Constraints: {len(context.constraint_context)} chars")
```

### 3. Build Minimal Context
```python
# For quick tasks or low token budgets
minimal = await builder.build_minimal_context(role)

print(f"Minimal context: {minimal.token_count} tokens")
# Only includes system prompt, no skills or examples
```

### 4. Custom Token Budget Allocation
```python
# Prioritize skill context
budget = TokenBudget(
    total_budget=10000,
    system_prompt_budget=1000,
    skill_budget=5000,      # Large skill budget
    constraint_budget=500,
    project_budget=1000,
    example_budget=1000,
    task_budget=500
)

context = await builder.build_context(role, task, budget)
```

### 5. Extend Existing Context
```python
# Add project-specific context
project_info = """
Project: Authentication Service Refactor
Goals: Improve security, add MFA support
Tech Stack: Python, FastAPI, PostgreSQL
"""

extended = await builder.extend_context(
    context,
    extension={
        "project_context": project_info,
        "examples": [
            "Example: When reviewing auth code, check for SQL injection...",
            "Example: MFA implementation should use TOTP standard..."
        ]
    }
)

print(f"Extended context: {extended.token_count} tokens")
```

### 6. Merge Multiple Contexts
```python
# Combine contexts from multiple roles
dev_context = await builder.build_context(dev_role, task, budget)
security_context = await builder.build_context(security_role, task, budget)

merged = await builder.merge_contexts([dev_context, security_context])

print(f"Merged context includes:")
print(f"  Skills from both roles")
print(f"  Combined constraints")
print(f"  Total tokens: {merged.token_count}")
```

### 7. Estimate Token Count
```python
text = "This is some text to estimate tokens for."
tokens = builder.estimate_tokens(text)
print(f"Estimated tokens: {tokens}")  # ~10 tokens

# Check if content fits budget
skill_content = load_skill_content("skill-python")
skill_tokens = builder.estimate_tokens(skill_content)

if skill_tokens > budget.skill_budget:
    print(f"Skill too large: {skill_tokens} > {budget.skill_budget}")
```

### 8. Get Remaining Budget
```python
context = await builder.build_context(role, task, budget)
remaining = builder.get_remaining_budget(context, budget)

print(f"Token budget remaining:")
print(f"  Total: {remaining['total']} tokens")
print(f"  Can add: {remaining['available_sections']}")

# Use remaining budget for additional context
if remaining['total'] > 500:
    context = await builder.extend_context(
        context,
        extension={"additional_info": extra_context}
    )
```

### 9. Context with Skill Loading
```python
# Role with multiple skills
role = Role(
    role_id="role-fullstack",
    name="Full Stack Developer",
    skills=["skill-react", "skill-python", "skill-postgres", "skill-docker"],
    constraints={"environment": "development"}
)

# Builder loads skills from SkillStore
context = await builder.build_context(role, task, budget)

print(f"Loaded {len(role.skills)} skills")
print(f"Skill context: {context.skill_context[:200]}...")
```

### 10. Get Builder Statistics
```python
stats = builder.get_stats()

print(f"Context Builder Statistics:")
print(f"  Contexts built: {stats['contexts_built']}")
print(f"  Average tokens: {stats['avg_token_count']}")
print(f"  Budget overflows: {stats['budget_overflows']}")
print(f"  Minimal contexts: {stats['minimal_contexts']}")
print(f"  Skills loaded: {stats['skills_loaded']}")
print(f"  Cache hits: {stats['skill_cache_hits']}")
```

## Service Interactions

```
+---------------------+
| RoleContextBuilder  | <--- L13 Role Management Layer
|        (L13)        |
+----------+----------+
           |
     Assembles:
           |
+----------+----------+----------+
|          |          |          |
v          v          v          v
System     Skill      Constraint Token
Prompt     Context    Context    Budget
           ↓
      SkillStore
         (L14)
```

**Integration Points:**
- **SkillStore (L14)**: Loads skill definitions
- **RoleDispatcher (L13)**: Requests contexts for dispatch
- **RoleRegistry (L13)**: Provides role definitions
- **ModelGateway (L04)**: Receives assembled context

## Context Assembly Pipeline

```
Context Assembly Flow:

1. VALIDATE INPUTS
   ├─ Check role exists
   ├─ Validate token budget
   └─ Parse task requirements

2. BUILD SYSTEM PROMPT
   ├─ Role name and description
   ├─ Role type instructions
   └─ Base behavioral guidelines

3. LOAD SKILL CONTEXT
   ├─ Query SkillStore for role.skills
   ├─ Filter by budget constraint
   ├─ Prioritize by relevance to task
   └─ Format as skill definitions

4. BUILD CONSTRAINT CONTEXT
   ├─ Role constraints
   ├─ Environment constraints
   └─ Task-specific constraints

5. ADD PROJECT CONTEXT
   ├─ Project metadata
   ├─ Team conventions
   └─ Technical stack info

6. SELECT EXAMPLES
   ├─ Choose relevant few-shot examples
   ├─ Fit within example budget
   └─ Prioritize by similarity

7. ADD TASK CONTEXT
   ├─ Task description
   ├─ Required capabilities
   └─ Expected outputs

8. ESTIMATE TOKENS
   └─ Sum all sections: total_tokens

9. VALIDATE BUDGET
   ├─ If over budget: truncate or remove sections
   └─ Return assembled context
```

## Token Budget Allocation

```
Default Budget Distribution (8000 tokens):

+---------------------------+-------+--------+
| Section                   | Tokens| %      |
+---------------------------+-------+--------+
| System Prompt             | 1500  | 18.75% |
| Skill Context             | 3000  | 37.50% |
| Constraint Context        | 500   | 6.25%  |
| Project Context           | 1000  | 12.50% |
| Examples                  | 1000  | 12.50% |
| Task Context              | 1000  | 12.50% |
+---------------------------+-------+--------+
| Total                     | 8000  | 100%   |
+---------------------------+-------+--------+
```

## Error Codes

| Code | Description | Retryable |
|------|-------------|-----------|
| E13201 | Role not found | No |
| E13202 | Skill loading failed | Yes |
| E13203 | Budget exceeded | No |
| E13204 | Context merge conflict | No |

## Execution Examples

```python
# Complete context building workflow
from L13_role_management.services.role_context_builder import RoleContextBuilder
from L13_role_management.models import Role, RoleType, TokenBudget
from L14_skill_library.services.skill_store import SkillStore

# Initialize
skill_store = SkillStore()
builder = RoleContextBuilder(
    skill_store=skill_store,
    default_token_budget=10000
)

# 1. Create role with skills
role = Role(
    role_id="role-security-reviewer",
    name="Security Code Reviewer",
    description="Reviews code for security vulnerabilities and best practices",
    role_type=RoleType.AI_PRIMARY,
    skills=["skill-security", "skill-python", "skill-owasp"],
    constraints={
        "no_production_access": True,
        "require_audit_log": True,
        "max_file_size_mb": 10
    }
)

# 2. Create task
task = Task(
    task_id="task-sec-001",
    description="Review authentication module for SQL injection and XSS vulnerabilities",
    required_capabilities=["security_review", "code_analysis"],
    context={
        "repository": "auth-service",
        "branch": "feature/oauth2",
        "files": ["auth/login.py", "auth/session.py"]
    }
)

# 3. Build with custom budget
budget = TokenBudget(
    total_budget=12000,
    system_prompt_budget=1500,
    skill_budget=5000,      # More for security skills
    constraint_budget=1000,  # More for security constraints
    project_budget=1500,
    example_budget=1500,
    task_budget=500
)

print("Building role context...")
context = await builder.build_context(role, task, budget)

# 4. Inspect assembled context
print(f"\nContext assembled:")
print(f"  Total tokens: {context.token_count}")
print(f"\nSystem prompt ({builder.estimate_tokens(context.system_prompt)} tokens):")
print(f"  {context.system_prompt[:200]}...")

print(f"\nSkill context ({builder.estimate_tokens(context.skill_context)} tokens):")
print(f"  {context.skill_context[:200]}...")

print(f"\nConstraints ({builder.estimate_tokens(context.constraint_context)} tokens):")
print(f"  {context.constraint_context}")

# 5. Check remaining budget
remaining = builder.get_remaining_budget(context, budget)
print(f"\nRemaining budget: {remaining['total']} tokens")

# 6. Extend with project-specific info
project_context = """
## Auth Service Security Guidelines

1. All user inputs must be sanitized
2. Use parameterized queries only
3. Session tokens must be httpOnly and secure
4. Rate limiting required on all endpoints
5. Audit logging for all auth events
"""

extended = await builder.extend_context(
    context,
    extension={"project_context": project_context}
)
print(f"\nExtended context: {extended.token_count} tokens")

# 7. Build minimal for comparison
minimal = await builder.build_minimal_context(role)
print(f"\nMinimal context: {minimal.token_count} tokens")
print(f"Reduction: {context.token_count - minimal.token_count} tokens saved")

# 8. Statistics
print("\n\nBuilder Statistics:")
stats = builder.get_stats()
for key, value in stats.items():
    print(f"  {key}: {value}")
```

## Implementation Status

| Component | Status |
|-----------|--------|
| RoleContextBuilder class | Complete |
| build_context() | Complete |
| build_minimal_context() | Complete |
| extend_context() | Complete |
| merge_contexts() | Complete |
| Token estimation | Complete |
| Budget management | Complete |
| Skill loading | Complete |
| Constraint formatting | Complete |
| Statistics | Complete |

## Remaining Work

| Item | Priority | Description |
|------|----------|-------------|
| Semantic compression | High | Compress context without losing meaning |
| Dynamic budget allocation | Medium | Allocate based on task needs |
| Context caching | Medium | Cache assembled contexts |
| Streaming context | Low | Stream context assembly |
| Multi-language support | Low | Non-English skill content |

## Strengths

- **Token-aware** - Budget-constrained assembly
- **Modular sections** - Clear separation of context parts
- **Skill integration** - Loads from SkillStore
- **Extensible** - Easy to extend contexts
- **Mergeable** - Combine multiple role contexts
- **Minimal fallback** - Graceful degradation

## Weaknesses

- **Simple estimation** - Character-based token counting
- **No compression** - Doesn't optimize content
- **Static allocation** - Fixed budget percentages
- **No caching** - Rebuilds context each time
- **Skill dependency** - Requires SkillStore
- **English-centric** - Character estimation assumes English

## Best Practices

### Budget Allocation
Allocate based on task complexity:
```python
# For complex tasks: more skill context
complex_budget = TokenBudget(
    total_budget=15000,
    skill_budget=8000,  # 53% for skills
    example_budget=3000  # 20% for examples
)

# For simple tasks: minimal context
simple_budget = TokenBudget(
    total_budget=4000,
    skill_budget=1500,
    example_budget=500
)
```

### Skill Prioritization
Order skills by relevance:
```python
# Put most relevant skills first in role definition
role.skills = [
    "skill-security",     # Most relevant for security review
    "skill-python",       # Language-specific
    "skill-owasp",        # Reference material
    "skill-general-dev"   # Least specific
]
# Builder truncates from end if budget exceeded
```

### Context Extension
Extend rather than rebuild:
```python
# Good: Extend existing context
context = await builder.build_context(role, task, budget)
context = await builder.extend_context(context, {"extra": info})

# Avoid: Rebuilding from scratch
context1 = await builder.build_context(role, task, budget)
context2 = await builder.build_context(role, task, budget)  # Duplicate work
```

## Source Files

- Service: `platform/src/L13_role_management/services/role_context_builder.py`
- Models: `platform/src/L13_role_management/models/`
- Spec: L13 Role Management Layer specification

## Related Services

- SkillStore (L14) - Provides skill definitions
- RoleDispatcher (L13) - Requests contexts
- RoleRegistry (L13) - Provides role definitions
- ModelGateway (L04) - Consumes assembled context

---
*Generated: 2026-01-24 | Platform Services Documentation*
