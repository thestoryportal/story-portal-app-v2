# Service 46/52: ClassificationEngine

## Overview

| Property | Value |
|----------|-------|
| **Layer** | L13 (Role Management Layer) |
| **Module** | `L13_role_management.services.classification_engine` |
| **Status** | Fully Implemented & Healthy |
| **Dependencies** | None (pure algorithm) |
| **Category** | Role Management / Classification |

## Role in Development Environment

The **ClassificationEngine** determines whether tasks should be routed to human, AI, or hybrid execution based on task characteristics. It provides:
- Keyword-based task analysis
- Weighted multi-factor scoring
- Human/AI/hybrid classification
- Confidence scoring for routing decisions
- Custom rule support
- Classification explanation

This is **the routing decision maker** - when a task comes in, ClassificationEngine analyzes it and determines the optimal execution path (human, AI, or collaborative).

## Data Model

### ClassificationResult
- `classification: TaskClassification` - Routing decision
- `confidence: float` - Confidence score (0.0-1.0)
- `scores: Dict[str, float]` - Individual factor scores
- `explanation: str` - Human-readable explanation
- `factors: List[str]` - Contributing factors

### TaskClassification Enum
- `human_primary` - Route to human execution
- `ai_primary` - Route to AI execution
- `hybrid` - Collaborative human/AI execution

### ClassificationFactors
- `keyword_score: float` - Based on keyword analysis (weight: 0.30)
- `complexity_score: float` - Task complexity (weight: 0.25)
- `urgency_score: float` - Time sensitivity (weight: 0.15)
- `skill_score: float` - Required skills match (weight: 0.15)
- `custom_score: float` - Custom rules (weight: 0.15)

## Configuration

| Parameter | Default | Description |
|-----------|---------|-------------|
| `human_threshold` | 0.6 | Score threshold for human routing |
| `ai_threshold` | 0.6 | Score threshold for AI routing |
| `custom_rules` | [] | Custom classification rules |

## Keyword Sets

### Human Keywords
Decision-requiring, sensitive, or strategic tasks:
```python
HUMAN_KEYWORDS = {
    "decision", "approve", "reject", "sensitive", "confidential",
    "strategic", "negotiate", "relationship", "ethical", "judgment",
    "creative", "innovative", "empathy", "conflict", "policy",
    "exception", "override", "executive", "stakeholder", "customer"
}
```

### AI Keywords
Automatable, analytical, or repetitive tasks:
```python
AI_KEYWORDS = {
    "analyze", "generate", "calculate", "automate", "process",
    "transform", "validate", "format", "convert", "extract",
    "summarize", "classify", "categorize", "sort", "filter",
    "aggregate", "compile", "template", "standard", "routine"
}
```

## API Methods

| Method | Description |
|--------|-------------|
| `classify_task(task)` | Classify task for routing |
| `add_custom_rule(rule)` | Add custom classification rule |
| `remove_custom_rule(rule_id)` | Remove custom rule |
| `get_classification_factors(task)` | Get detailed factor breakdown |
| `explain_classification(result)` | Get human-readable explanation |
| `get_stats()` | Get classification statistics |

## Use Cases in Your Workflow

### 1. Initialize Classification Engine
```python
from L13_role_management.services.classification_engine import ClassificationEngine

# Default initialization
engine = ClassificationEngine()

# With custom thresholds
engine = ClassificationEngine(
    human_threshold=0.7,
    ai_threshold=0.65
)
```

### 2. Classify a Task
```python
from L13_role_management.models import Task

task = Task(
    task_id="task-123",
    description="Analyze sales data and generate monthly report",
    required_capabilities=["data_analysis", "report_generation"],
    priority="medium"
)

result = await engine.classify_task(task)

print(f"Classification: {result.classification.value}")
print(f"Confidence: {result.confidence:.2f}")
print(f"Explanation: {result.explanation}")
```

### 3. Get Detailed Factor Breakdown
```python
factors = await engine.get_classification_factors(task)

print("Classification factors:")
print(f"  Keyword score: {factors['keyword_score']:.2f}")
print(f"  Complexity score: {factors['complexity_score']:.2f}")
print(f"  Urgency score: {factors['urgency_score']:.2f}")
print(f"  Skill score: {factors['skill_score']:.2f}")
print(f"  Custom score: {factors['custom_score']:.2f}")
print(f"  Weighted total: {factors['weighted_total']:.2f}")
```

### 4. Add Custom Classification Rule
```python
from L13_role_management.models import ClassificationRule

# Rule: Always route security tasks to human
security_rule = ClassificationRule(
    rule_id="security-human",
    name="Security tasks to human",
    condition=lambda task: "security" in task.description.lower(),
    classification=TaskClassification.HUMAN_PRIMARY,
    priority=10  # Higher priority rules apply first
)

engine.add_custom_rule(security_rule)
```

### 5. Classify Sensitive Task
```python
sensitive_task = Task(
    task_id="task-456",
    description="Approve budget exception for client contract negotiation",
    required_capabilities=["decision_making", "negotiation"],
    priority="high",
    metadata={"sensitive": True}
)

result = await engine.classify_task(sensitive_task)

# Should route to human due to keywords: approve, exception, negotiation
print(f"Classification: {result.classification.value}")  # human_primary
print(f"Contributing factors: {result.factors}")
```

### 6. Classify Automatable Task
```python
auto_task = Task(
    task_id="task-789",
    description="Extract data from CSV, validate format, and generate summary report",
    required_capabilities=["data_processing", "validation"],
    priority="low"
)

result = await engine.classify_task(auto_task)

# Should route to AI due to keywords: extract, validate, generate, format
print(f"Classification: {result.classification.value}")  # ai_primary
```

### 7. Handle Hybrid Classification
```python
hybrid_task = Task(
    task_id="task-101",
    description="Analyze customer feedback and prepare strategic recommendations",
    required_capabilities=["analysis", "strategy"],
    priority="medium"
)

result = await engine.classify_task(hybrid_task)

if result.classification == TaskClassification.HYBRID:
    print("Task requires human-AI collaboration")
    print(f"AI portion: data analysis")
    print(f"Human portion: strategic decisions")
```

### 8. Explain Classification Decision
```python
result = await engine.classify_task(task)
explanation = engine.explain_classification(result)

print("Classification Explanation:")
print(explanation)
# Output:
# Task classified as AI_PRIMARY with 78% confidence.
# Key factors:
# - Contains AI keywords: analyze, generate, validate
# - Low complexity score (0.3)
# - No urgency indicators
# - Skills match AI capabilities
```

### 9. Batch Classification
```python
tasks = [task1, task2, task3, task4, task5]

results = []
for task in tasks:
    result = await engine.classify_task(task)
    results.append({
        "task_id": task.task_id,
        "classification": result.classification.value,
        "confidence": result.confidence
    })

# Group by classification
human_tasks = [r for r in results if r["classification"] == "human_primary"]
ai_tasks = [r for r in results if r["classification"] == "ai_primary"]
hybrid_tasks = [r for r in results if r["classification"] == "hybrid"]

print(f"Human: {len(human_tasks)}, AI: {len(ai_tasks)}, Hybrid: {len(hybrid_tasks)}")
```

### 10. Get Classification Statistics
```python
stats = engine.get_stats()

print(f"Total classifications: {stats['total_classifications']}")
print(f"Human routed: {stats['human_classifications']} ({stats['human_rate']:.1%})")
print(f"AI routed: {stats['ai_classifications']} ({stats['ai_rate']:.1%})")
print(f"Hybrid: {stats['hybrid_classifications']} ({stats['hybrid_rate']:.1%})")
print(f"Average confidence: {stats['avg_confidence']:.2f}")
print(f"Custom rules applied: {stats['custom_rule_applications']}")
```

## Service Interactions

```
+----------------------+
| ClassificationEngine | <--- L13 Role Management Layer
|        (L13)         |
+-----------+----------+
            |
      Analyzes:
            |
+-----------+-----------+
|           |           |
v           v           v
Keywords    Complexity  Custom
Analysis    Scoring     Rules
```

**Integration Points:**
- **RoleDispatcher (L13)**: Uses classification for routing
- **RoleRegistry (L13)**: Queries role types for matching
- **TaskOrchestrator (L05)**: Receives routing decisions

## Classification Algorithm

```
Classification Flow:

1. KEYWORD ANALYSIS (weight: 0.30)
   ├─ Count human keywords in description
   ├─ Count AI keywords in description
   └─ Compute keyword score: (human - ai) / total

2. COMPLEXITY SCORING (weight: 0.25)
   ├─ Analyze task description length
   ├─ Count required capabilities
   ├─ Check for subtasks
   └─ Score: higher complexity → human

3. URGENCY SCORING (weight: 0.15)
   ├─ Check priority field
   ├─ Look for urgency keywords
   └─ Score: high urgency → AI (faster)

4. SKILL MATCHING (weight: 0.15)
   ├─ Match capabilities to role types
   └─ Score based on best match

5. CUSTOM RULES (weight: 0.15)
   ├─ Apply priority-ordered rules
   └─ First matching rule wins

6. COMPUTE FINAL SCORE
   └─ Weighted sum of all factors

7. DETERMINE CLASSIFICATION
   ├─ If score >= human_threshold → HUMAN_PRIMARY
   ├─ If score <= -ai_threshold → AI_PRIMARY
   └─ Else → HYBRID
```

## Error Codes

| Code | Description | Retryable |
|------|-------------|-----------|
| E13101 | Invalid task | No |
| E13102 | Classification failed | Yes |
| E13103 | Custom rule error | No |

## Execution Examples

```python
# Complete classification workflow
from L13_role_management.services.classification_engine import ClassificationEngine
from L13_role_management.models import Task, ClassificationRule, TaskClassification

# Initialize
engine = ClassificationEngine(
    human_threshold=0.6,
    ai_threshold=0.6
)

# 1. Add custom rules
# High-priority security rule
engine.add_custom_rule(ClassificationRule(
    rule_id="security-audit",
    name="Security audits to human",
    condition=lambda t: "audit" in t.description.lower() and "security" in t.description.lower(),
    classification=TaskClassification.HUMAN_PRIMARY,
    priority=100
))

# Performance tasks to AI
engine.add_custom_rule(ClassificationRule(
    rule_id="performance-ai",
    name="Performance analysis to AI",
    condition=lambda t: "performance" in t.description.lower() and "analyze" in t.description.lower(),
    classification=TaskClassification.AI_PRIMARY,
    priority=50
))

# 2. Test various task types
test_tasks = [
    Task(
        task_id="t1",
        description="Approve quarterly budget allocation for marketing department",
        required_capabilities=["approval", "budgeting"],
        priority="high"
    ),
    Task(
        task_id="t2",
        description="Extract customer data from database and generate CSV report",
        required_capabilities=["data_extraction", "reporting"],
        priority="low"
    ),
    Task(
        task_id="t3",
        description="Analyze competitor strategy and prepare strategic recommendations",
        required_capabilities=["analysis", "strategy"],
        priority="medium"
    ),
    Task(
        task_id="t4",
        description="Conduct security audit of authentication system",
        required_capabilities=["security", "auditing"],
        priority="high"
    ),
]

print("Classification Results:")
print("-" * 60)

for task in test_tasks:
    result = await engine.classify_task(task)

    print(f"\nTask: {task.task_id}")
    print(f"Description: {task.description[:50]}...")
    print(f"Classification: {result.classification.value}")
    print(f"Confidence: {result.confidence:.0%}")
    print(f"Key factors: {', '.join(result.factors[:3])}")

# 3. Detailed factor analysis
print("\n\nDetailed Factor Analysis for t3:")
print("-" * 40)
factors = await engine.get_classification_factors(test_tasks[2])
for factor, score in factors.items():
    if factor != "weighted_total":
        print(f"  {factor}: {score:.2f}")
print(f"  Final score: {factors['weighted_total']:.2f}")

# 4. Statistics
print("\n\nClassification Statistics:")
print("-" * 40)
stats = engine.get_stats()
print(f"Total: {stats['total_classifications']}")
print(f"Human: {stats['human_classifications']}")
print(f"AI: {stats['ai_classifications']}")
print(f"Hybrid: {stats['hybrid_classifications']}")
```

## Implementation Status

| Component | Status |
|-----------|--------|
| ClassificationEngine class | Complete |
| classify_task() | Complete |
| Keyword analysis | Complete |
| Complexity scoring | Complete |
| Urgency scoring | Complete |
| Skill matching | Complete |
| Custom rules | Complete |
| Factor breakdown | Complete |
| Explanation generation | Complete |
| Statistics | Complete |

## Remaining Work

| Item | Priority | Description |
|------|----------|-------------|
| ML-based classification | High | Train model on historical data |
| Confidence calibration | Medium | Tune confidence scores |
| Rule DSL | Medium | Domain-specific language for rules |
| A/B testing | Low | Compare classification strategies |
| Feedback loop | Low | Learn from routing outcomes |

## Strengths

- **Multi-factor analysis** - Considers multiple signals
- **Weighted scoring** - Tunable factor weights
- **Custom rules** - Extensible with business rules
- **Explainable** - Clear factor breakdown
- **Pure algorithm** - No external dependencies
- **Fast execution** - In-memory computation

## Weaknesses

- **Keyword-based** - Limited semantic understanding
- **Fixed weights** - No adaptive weighting
- **No learning** - Doesn't improve from feedback
- **English-only** - Keyword sets are English
- **Binary keywords** - No partial matches
- **Threshold sensitivity** - Results depend on thresholds

## Best Practices

### Threshold Tuning
Choose thresholds based on organization needs:
```python
# Conservative: Route uncertain to human
engine = ClassificationEngine(
    human_threshold=0.5,  # Lower = more human routing
    ai_threshold=0.7      # Higher = less AI routing
)

# Aggressive: Maximize AI usage
engine = ClassificationEngine(
    human_threshold=0.8,  # Higher = less human routing
    ai_threshold=0.4      # Lower = more AI routing
)
```

### Custom Rule Design
Design specific, high-priority rules:
```python
# Good: Specific condition
ClassificationRule(
    condition=lambda t: t.metadata.get("compliance_required") == True,
    classification=TaskClassification.HUMAN_PRIMARY,
    priority=100  # High priority
)

# Avoid: Overly broad rules
ClassificationRule(
    condition=lambda t: True,  # Matches everything
    classification=TaskClassification.HUMAN_PRIMARY
)
```

### Confidence Handling
Act on confidence levels:
```python
result = await engine.classify_task(task)

if result.confidence < 0.6:
    # Low confidence - consider hybrid or human review
    print("Classification uncertain, defaulting to human review")
    result.classification = TaskClassification.HUMAN_PRIMARY
```

## Source Files

- Service: `platform/src/L13_role_management/services/classification_engine.py`
- Models: `platform/src/L13_role_management/models/`
- Spec: L13 Role Management Layer specification

## Related Services

- RoleDispatcher (L13) - Uses classification for routing
- RoleRegistry (L13) - Provides role type information
- TaskOrchestrator (L05) - Receives routed tasks

---
*Generated: 2026-01-24 | Platform Services Documentation*
