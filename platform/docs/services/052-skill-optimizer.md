# Service 52/52: SkillOptimizer

## Overview

| Property | Value |
|----------|-------|
| **Layer** | L14 (Skill Library Layer) |
| **Module** | `L14_skill_library.services.skill_optimizer` |
| **Status** | Fully Implemented & Healthy |
| **Dependencies** | SkillStore (L14) |
| **Category** | Skill Library / Optimization |

## Role in Development Environment

The **SkillOptimizer** reduces token consumption while preserving skill effectiveness through various optimization strategies. It provides:
- Token compression without semantic loss
- Priority-based skill loading order
- Context-aware skill selection
- Minimal skill mode for constrained budgets
- Skill deduplication
- Optimization metrics tracking

This is **the token optimization engine** - when context budgets are limited, SkillOptimizer ensures the most relevant skill content fits within constraints.

## Data Model

### OptimizationRequest
- `skills: List[Skill]` - Skills to optimize
- `strategy: OptimizationStrategy` - Strategy to use
- `token_budget: int` - Target token budget
- `context: str` - Task context for relevance
- `preserve_sections: List[str]` - Sections to preserve

### OptimizationResult
- `optimized_skills: List[Skill]` - Optimized skills
- `original_tokens: int` - Tokens before optimization
- `optimized_tokens: int` - Tokens after optimization
- `reduction_percent: float` - Token reduction percentage
- `strategy_used: str` - Strategy that was applied
- `sections_removed: List[str]` - Removed sections
- `loading_order: List[str]` - Recommended load order

### OptimizationStrategy Enum
- `TOKEN_REDUCTION` - Compress to reduce tokens
- `PRIORITY_LOADING` - Order by priority
- `CONTEXT_AWARE` - Optimize based on context
- `MINIMAL` - Extreme reduction for low budgets

## Configuration

| Parameter | Default | Description |
|-----------|---------|-------------|
| `skill_store` | SkillStore() | Skill store for lookups |
| `default_strategy` | CONTEXT_AWARE | Default optimization strategy |
| `min_token_budget` | 500 | Minimum tokens per skill |
| `compression_level` | "medium" | Compression aggressiveness |

## API Methods

| Method | Description |
|--------|-------------|
| `optimize(request)` | Optimize skills per strategy |
| `get_loading_order(skills, context)` | Get priority load order |
| `estimate_total_tokens(skills)` | Estimate total tokens |
| `compress(skill)` | Compress single skill |
| `deduplicate(skills)` | Remove duplicate content |
| `get_minimal(skill)` | Get minimal version |
| `get_stats()` | Get optimization statistics |

## Use Cases in Your Workflow

### 1. Initialize Skill Optimizer
```python
from L14_skill_library.services.skill_optimizer import SkillOptimizer
from L14_skill_library.services.skill_store import SkillStore

# Default initialization
optimizer = SkillOptimizer()

# With custom store
store = SkillStore()
optimizer = SkillOptimizer(
    skill_store=store,
    default_strategy=OptimizationStrategy.CONTEXT_AWARE
)
```

### 2. Optimize Skills with Token Reduction
```python
from L14_skill_library.models import OptimizationRequest, OptimizationStrategy

skills = [skill1, skill2, skill3]

request = OptimizationRequest(
    skills=skills,
    strategy=OptimizationStrategy.TOKEN_REDUCTION,
    token_budget=5000
)

result = optimizer.optimize(request)

print(f"Optimization result:")
print(f"  Original: {result.original_tokens} tokens")
print(f"  Optimized: {result.optimized_tokens} tokens")
print(f"  Reduction: {result.reduction_percent:.1f}%")
print(f"  Sections removed: {result.sections_removed}")
```

### 3. Context-Aware Optimization
```python
# Optimize based on task context
request = OptimizationRequest(
    skills=skills,
    strategy=OptimizationStrategy.CONTEXT_AWARE,
    token_budget=4000,
    context="Review Python code for security vulnerabilities in authentication module"
)

result = optimizer.optimize(request)

print(f"Context-aware optimization:")
print(f"  Most relevant skill: {result.loading_order[0]}")
print(f"  Reduction: {result.reduction_percent:.1f}%")
```

### 4. Get Priority Loading Order
```python
# Get recommended order for loading skills
context = "Implement REST API endpoint for user management"

order = optimizer.get_loading_order(skills, context)

print("Loading order (highest priority first):")
for i, skill_id in enumerate(order, 1):
    skill = next(s for s in skills if s.skill_id == skill_id)
    print(f"  {i}. {skill.name}")
```

### 5. Estimate Token Usage
```python
# Estimate tokens before loading
total = optimizer.estimate_total_tokens(skills)

print(f"Total tokens for {len(skills)} skills: {total}")

if total > budget:
    print(f"Exceeds budget by {total - budget} tokens")
    print("Optimization recommended")
```

### 6. Compress Single Skill
```python
# Compress individual skill
original = skill
compressed = optimizer.compress(skill)

print(f"Skill compression:")
print(f"  Original: {optimizer.estimate_total_tokens([original])} tokens")
print(f"  Compressed: {optimizer.estimate_total_tokens([compressed])} tokens")
```

### 7. Get Minimal Version
```python
# Get extreme minimal version for tight budgets
minimal = optimizer.get_minimal(skill)

print(f"Minimal version:")
print(f"  Sections: role, responsibilities only")
print(f"  Tokens: {optimizer.estimate_total_tokens([minimal])}")
```

### 8. Deduplicate Skills
```python
# Remove duplicate content across skills
skills_with_dupes = [skill1, skill2, skill3]  # Some overlap

deduped = optimizer.deduplicate(skills_with_dupes)

original_tokens = optimizer.estimate_total_tokens(skills_with_dupes)
deduped_tokens = optimizer.estimate_total_tokens(deduped)

print(f"Deduplication:")
print(f"  Original: {original_tokens} tokens")
print(f"  Deduplicated: {deduped_tokens} tokens")
print(f"  Saved: {original_tokens - deduped_tokens} tokens")
```

### 9. Preserve Specific Sections
```python
# Optimize but keep certain sections
request = OptimizationRequest(
    skills=skills,
    strategy=OptimizationStrategy.TOKEN_REDUCTION,
    token_budget=3000,
    preserve_sections=["responsibilities", "constraints"]
)

result = optimizer.optimize(request)

# Examples and procedures may be removed, but responsibilities preserved
print(f"Preserved sections: {request.preserve_sections}")
print(f"Removed sections: {result.sections_removed}")
```

### 10. Get Optimization Statistics
```python
stats = optimizer.get_stats()

print(f"Optimizer Statistics:")
print(f"  Total optimizations: {stats['total_optimizations']}")
print(f"  Total tokens saved: {stats['total_tokens_saved']}")
print(f"  Avg reduction: {stats['avg_reduction_percent']:.1f}%")
print(f"  By strategy:")
for strategy, count in stats['strategy_usage'].items():
    print(f"    {strategy}: {count}")
print(f"  Most compressed skill: {stats['most_compressed']}")
```

## Service Interactions

```
+------------------+
|  SkillOptimizer  | <--- L14 Skill Library Layer
|      (L14)       |
+--------+---------+
         |
   Optimizes:
         |
+--------+--------+--------+
|        |        |        |
v        v        v        v
Token    Priority Context  Minimal
Reduce   Loading  Aware    Mode
```

**Integration Points:**
- **SkillStore (L14)**: Loads skills to optimize
- **RoleContextBuilder (L13)**: Uses optimized skills
- **SkillValidator (L14)**: Validates after optimization

## Optimization Strategies

### Token Reduction Strategy
```
Goal: Minimize tokens while preserving meaning

Steps:
1. Remove optional sections (examples, procedures)
2. Shorten descriptions
3. Compress lists
4. Remove redundant text
5. Use abbreviations where safe

Sections removed (in order):
1. examples (highest savings)
2. procedures
3. tool descriptions
4. constraint details
5. responsibility details (last resort)
```

### Priority Loading Strategy
```
Goal: Order skills by importance for partial loading

Scoring factors:
- Category match to context (0.3 weight)
- Keyword overlap with task (0.3 weight)
- Skill version (newer = higher) (0.2 weight)
- Usage frequency (0.2 weight)

Output: Ordered list from most to least relevant
```

### Context-Aware Strategy
```
Goal: Optimize based on specific task context

Steps:
1. Extract keywords from context
2. Score each skill by relevance
3. Fully load highly relevant skills
4. Compress medium-relevance skills
5. Get minimal for low-relevance skills
6. Order by relevance score

Keyword matching:
- Exact word match: 1.0 score
- Stem match: 0.7 score
- Category match: 0.5 score
```

### Minimal Strategy
```
Goal: Extreme reduction for very tight budgets

Output per skill:
- role: Name only
- responsibilities: First 2 only
- No tools, examples, procedures, constraints

Typically achieves 70-80% reduction
```

## Compression Techniques

```
Compression Methods:

1. SECTION REMOVAL
   - Remove entire optional sections
   - Preserve: metadata, role, responsibilities

2. LIST TRUNCATION
   - Keep first N items
   - Add "... and N more" indicator

3. DESCRIPTION SHORTENING
   - Remove adjectives
   - Use active voice
   - Remove redundant phrases

4. DEDUPLICATION
   - Remove repeated content across skills
   - Reference other skills instead

5. ABBREVIATION
   - Common terms → abbreviations
   - "responsibility" → "resp."
   - Only when safe
```

## Error Codes

| Code | Description | Retryable |
|------|-------------|-----------|
| E14201 | Optimization failed | Yes |
| E14202 | Invalid strategy | No |
| E14203 | Budget too low | No |
| E14204 | No skills provided | No |
| E14205 | Compression failed | Yes |

## Execution Examples

```python
# Complete optimization workflow
from L14_skill_library.services.skill_optimizer import SkillOptimizer
from L14_skill_library.services.skill_store import SkillStore
from L14_skill_library.models import (
    Skill,
    OptimizationRequest,
    OptimizationStrategy
)

# Initialize
store = SkillStore()
optimizer = SkillOptimizer(skill_store=store)

# 1. Create test skills
skills = []
for name in ["python-dev", "code-reviewer", "security-expert", "data-analyst"]:
    skill = Skill(
        name=name,
        category="development" if "dev" in name else "other",
        content=f"""
metadata:
  name: {name}
  description: Expert in {name.replace('-', ' ')}
  version: 1.0.0

role: {name.replace('-', ' ').title()}

responsibilities:
  - Responsibility 1 for {name}
  - Responsibility 2 for {name}
  - Responsibility 3 for {name}

tools:
  - tool1
  - tool2
  - tool3

procedures:
  - name: Main procedure
    steps:
      - Step 1
      - Step 2
      - Step 3

examples:
  - input: Example input
    output: Example output
  - input: Another input
    output: Another output

constraints:
  - Constraint 1
  - Constraint 2
"""
    )
    skills.append(skill)
    await store.create(skill)

print(f"Created {len(skills)} test skills")

# 2. Estimate original tokens
original_tokens = optimizer.estimate_total_tokens(skills)
print(f"\nOriginal total tokens: {original_tokens}")

# 3. Token reduction optimization
print("\n--- Token Reduction Strategy ---")
request = OptimizationRequest(
    skills=skills,
    strategy=OptimizationStrategy.TOKEN_REDUCTION,
    token_budget=2000
)
result = optimizer.optimize(request)
print(f"Tokens: {result.original_tokens} → {result.optimized_tokens}")
print(f"Reduction: {result.reduction_percent:.1f}%")
print(f"Removed: {result.sections_removed}")

# 4. Context-aware optimization
print("\n--- Context-Aware Strategy ---")
context = "Review Python authentication code for security vulnerabilities"
request = OptimizationRequest(
    skills=skills,
    strategy=OptimizationStrategy.CONTEXT_AWARE,
    token_budget=2500,
    context=context
)
result = optimizer.optimize(request)
print(f"Context: {context[:40]}...")
print(f"Reduction: {result.reduction_percent:.1f}%")
print(f"Loading order: {[s.name for s in result.optimized_skills][:3]}")

# 5. Priority loading order
print("\n--- Priority Loading ---")
order = optimizer.get_loading_order(skills, context)
print("Recommended order:")
for i, skill_id in enumerate(order[:4], 1):
    skill = next(s for s in skills if s.skill_id == skill_id)
    print(f"  {i}. {skill.name}")

# 6. Minimal mode
print("\n--- Minimal Strategy ---")
request = OptimizationRequest(
    skills=skills,
    strategy=OptimizationStrategy.MINIMAL,
    token_budget=500
)
result = optimizer.optimize(request)
print(f"Extreme reduction: {result.reduction_percent:.1f}%")
print(f"Minimal tokens: {result.optimized_tokens}")

# 7. Single skill compression
print("\n--- Single Skill Compression ---")
original = skills[0]
compressed = optimizer.compress(original)
orig_tokens = optimizer.estimate_total_tokens([original])
comp_tokens = optimizer.estimate_total_tokens([compressed])
print(f"{original.name}: {orig_tokens} → {comp_tokens} tokens")

# 8. Preserve sections
print("\n--- Preserve Sections ---")
request = OptimizationRequest(
    skills=skills,
    strategy=OptimizationStrategy.TOKEN_REDUCTION,
    token_budget=1500,
    preserve_sections=["responsibilities", "constraints"]
)
result = optimizer.optimize(request)
print(f"Preserved: {request.preserve_sections}")
print(f"Removed: {result.sections_removed}")

# 9. Statistics
print("\n--- Optimizer Statistics ---")
stats = optimizer.get_stats()
print(f"Optimizations: {stats['total_optimizations']}")
print(f"Tokens saved: {stats['total_tokens_saved']}")
print(f"Avg reduction: {stats['avg_reduction_percent']:.1f}%")
```

## Implementation Status

| Component | Status |
|-----------|--------|
| SkillOptimizer class | Complete |
| optimize() | Complete |
| get_loading_order() | Complete |
| estimate_total_tokens() | Complete |
| compress() | Complete |
| deduplicate() | Complete |
| get_minimal() | Complete |
| TOKEN_REDUCTION strategy | Complete |
| PRIORITY_LOADING strategy | Complete |
| CONTEXT_AWARE strategy | Complete |
| MINIMAL strategy | Complete |
| Statistics | Complete |

## Remaining Work

| Item | Priority | Description |
|------|----------|-------------|
| Semantic compression | High | AI-powered lossless compression |
| Caching | Medium | Cache optimization results |
| Custom strategies | Medium | User-defined strategies |
| Incremental optimization | Low | Optimize on-demand |
| A/B comparison | Low | Compare strategy effectiveness |

## Strengths

- **Multiple strategies** - Different approaches for different needs
- **Context awareness** - Task-relevant optimization
- **Priority ordering** - Load most relevant first
- **Section preservation** - Keep critical content
- **Token estimation** - Plan before optimizing
- **Deduplication** - Remove cross-skill duplicates

## Weaknesses

- **Heuristic-based** - Not semantic understanding
- **English keywords** - Context matching is English
- **No caching** - Recomputes each time
- **Fixed strategies** - Can't create custom strategies
- **Lossy compression** - Some information lost
- **Simple estimation** - Character-based token count

## Best Practices

### Choose Right Strategy
Match strategy to situation:
```python
# Tight budget, specific task
strategy = OptimizationStrategy.CONTEXT_AWARE

# General optimization
strategy = OptimizationStrategy.TOKEN_REDUCTION

# Very tight budget
strategy = OptimizationStrategy.MINIMAL

# When order matters more than size
strategy = OptimizationStrategy.PRIORITY_LOADING
```

### Preserve Critical Sections
Always preserve core sections:
```python
request = OptimizationRequest(
    skills=skills,
    strategy=OptimizationStrategy.TOKEN_REDUCTION,
    preserve_sections=["responsibilities"]  # Always keep
)
```

### Estimate Before Loading
Check budget before loading skills:
```python
estimated = optimizer.estimate_total_tokens(skills)
if estimated > budget:
    # Optimize before loading
    result = optimizer.optimize(request)
    skills = result.optimized_skills
```

## Source Files

- Service: `platform/src/L14_skill_library/services/skill_optimizer.py`
- Models: `platform/src/L14_skill_library/models/`
- Spec: L14 Skill Library Layer specification

## Related Services

- SkillStore (L14) - Provides skills to optimize
- SkillValidator (L14) - Validates optimized skills
- RoleContextBuilder (L13) - Consumes optimized skills
- SkillGenerator (L14) - Creates skills before optimization

---
*Generated: 2026-01-24 | Platform Services Documentation*
