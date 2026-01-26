# Service 12/44: TrainingExampleService

## Overview

| Property | Value |
|----------|-------|
| **Layer** | L01 (Data Layer) |
| **Module** | `L01_data_layer.services.training_example_service` |
| **Status** | Fully Implemented & Healthy |
| **Dependencies** | PostgreSQL, Redis |
| **Category** | Data & Storage |

## Role in Development Environment

The **TrainingExampleService** stores training examples extracted from agent executions. It provides:
- Full CRUD operations for training data
- Quality and confidence scoring
- Domain and task type classification
- Source tracking (execution traces, human annotations, synthetic)
- Rich filtering and statistics
- Redis events for training data pipeline

This is **the foundation for RLHF and fine-tuning** - when agents complete tasks successfully, their execution traces become training examples stored here for the L07 Learning Layer.

## Data Model

### TrainingExample Fields
- `id: UUID` - Unique example identifier
- **Identifiers:**
  - `execution_id: str` - Source execution ID
  - `task_id: str` - Source task ID
  - `agent_id: UUID` - Agent that produced this example
- **Source Metadata:**
  - `source_type: ExampleSource` - How the example was created
  - `source_trace_hash: str` - Hash for deduplication
- **Input:**
  - `input_text: str` - Input prompt/query
  - `input_structured: Dict` - Structured input data
- **Output:**
  - `output_text: str` - Expected output text
  - `expected_actions: List[Dict]` - Expected action sequence
  - `final_answer: str` - Final answer from execution
- **Quality Signals:**
  - `quality_score: float` - Score 0-100
  - `confidence: float` - Confidence 0-1
- **Classification:**
  - `labels: List[str]` - Classification labels
  - `domain: str` - Task domain (e.g., "coding", "planning")
  - `task_type: TaskType` - Complexity classification
  - `difficulty: float` - Difficulty 0-1
- **Metadata:**
  - `metadata: Dict` - Additional context
  - `extracted_by: str` - Extraction source
  - `created_at/updated_at: datetime` - Timestamps

### ExampleSource Enum
- `EXECUTION_TRACE` - Extracted from agent execution
- `PLANNING_TRACE` - Extracted from planning process
- `QUALITY_FEEDBACK` - Created from quality feedback
- `SYNTHETIC` - Synthetically generated
- `HUMAN_ANNOTATED` - Human-created examples

### TaskType Enum
- `SINGLE_STEP` - Simple, one-step tasks
- `MULTI_STEP` - Multi-step workflows
- `REASONING` - Reasoning-heavy tasks
- `PLANNING` - Planning/decomposition tasks
- `CODE_GENERATION` - Code writing tasks

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/training-examples/` | Create example |
| `GET` | `/training-examples/{id}` | Get example by ID |
| `PATCH` | `/training-examples/{id}` | Update example |
| `DELETE` | `/training-examples/{id}` | Delete example |
| `GET` | `/training-examples/` | List examples |
| `GET` | `/training-examples/stats` | Get statistics |

## Use Cases in Your Workflow

### 1. Create Training Example from Execution
```bash
curl -X POST http://localhost:8011/training-examples/ \
  -H "Content-Type: application/json" \
  -d '{
    "execution_id": "exec-12345",
    "task_id": "task-67890",
    "agent_id": "550e8400-e29b-41d4-a716-446655440000",
    "source_type": "execution_trace",
    "source_trace_hash": "sha256:abc123...",
    "input_text": "Implement a React component for a modal dialog",
    "input_structured": {
      "task_type": "implementation",
      "language": "typescript",
      "framework": "react"
    },
    "output_text": "I will create a modal component with...",
    "expected_actions": [
      {"tool": "Read", "params": {"file": "Modal.tsx"}},
      {"tool": "Edit", "params": {"file": "Modal.tsx", "changes": "..."}}
    ],
    "final_answer": "Modal component implemented successfully",
    "quality_score": 85.5,
    "confidence": 0.92,
    "labels": ["react", "component", "modal"],
    "domain": "frontend",
    "task_type": "code_generation",
    "difficulty": 0.6
  }'
```

### 2. Create Human-Annotated Example
```bash
curl -X POST http://localhost:8011/training-examples/ \
  -H "Content-Type: application/json" \
  -d '{
    "source_type": "human_annotated",
    "input_text": "How do I fix a memory leak in my React app?",
    "output_text": "Memory leaks in React commonly occur from...",
    "expected_actions": [],
    "final_answer": "Check for missing cleanup in useEffect hooks",
    "quality_score": 95.0,
    "confidence": 1.0,
    "labels": ["debugging", "react", "memory"],
    "domain": "troubleshooting",
    "task_type": "reasoning",
    "difficulty": 0.7,
    "extracted_by": "human-curator"
  }'
```

### 3. Update Quality Score After Evaluation
```bash
curl -X PATCH http://localhost:8011/training-examples/660e8400-e29b-41d4-a716-446655440001 \
  -H "Content-Type: application/json" \
  -d '{
    "quality_score": 92.0,
    "confidence": 0.95,
    "labels": ["verified", "high-quality"]
  }'
```

### 4. Query High-Quality Examples
```bash
# Get high-quality examples (score >= 80)
curl "http://localhost:8011/training-examples/?min_quality=80&limit=50"

# Filter by domain
curl "http://localhost:8011/training-examples/?domain=frontend&min_quality=70"

# Filter by source type
curl "http://localhost:8011/training-examples/?source_type=human_annotated"

# Filter by agent
curl "http://localhost:8011/training-examples/?agent_id=550e8400-e29b-41d4-a716-446655440000"
```

### 5. Get Training Statistics
```bash
curl http://localhost:8011/training-examples/stats
# Response:
# {
#   "total_examples": 1500,
#   "avg_quality_score": 78.5,
#   "avg_confidence": 0.85,
#   "avg_difficulty": 0.55,
#   "unique_domains": 12,
#   "unique_agents": 5,
#   "domain_distribution": {
#     "frontend": 450,
#     "backend": 380,
#     "devops": 220,
#     ...
#   }
# }
```

### 6. Delete Low-Quality Example
```bash
curl -X DELETE http://localhost:8011/training-examples/660e8400-e29b-41d4-a716-446655440001
```

## Service Interactions

```
+------------------+
| TrainingExample  | <--- L01 Data Layer (PostgreSQL)
|   Service (L01)  | ---> Redis (pub/sub events)
+--------+---------+
         |
   Stores examples extracted by:
         |
+------------------+     +-------------------+
|TrainingDataExtrac|     |  EvaluationStore  |
|     tor (L07)    |     |      (L01)        |
+------------------+     +-------------------+
         |
   Provides data for:
         |
+------------------+     +-------------------+     +------------------+
| DatasetCurator   |     |  FineTuningEngine |     |  SyntheticData   |
|     (L07)        |     |      (L07)        |     |  Generator (L07) |
+------------------+     +-------------------+     +------------------+
```

**Integration Points:**
- **TrainingDataExtractor (L07)**: Extracts examples from execution traces
- **EvaluationStore (L01)**: Quality scores from evaluations
- **DatasetCurator (L07)**: Curates training datasets from examples
- **FineTuningEngine (L07)**: Uses examples for model training
- **DatasetService (L01)**: Examples assigned to datasets
- **FeedbackStore (L01)**: Corrections become training examples

## Redis Events

TrainingExampleService publishes events on example lifecycle:

```python
# Example created
{
    "event_type": "training_example.created",
    "aggregate_type": "training_example",
    "aggregate_id": "example-uuid",
    "payload": {
        "execution_id": "exec-123",
        "agent_id": "agent-uuid",
        "source_type": "execution_trace",
        "quality_score": 85.5,
        "domain": "frontend"
    }
}

# Example updated
{
    "event_type": "training_example.updated",
    "aggregate_type": "training_example",
    "aggregate_id": "example-uuid",
    "payload": {"updated_fields": ["quality_score", "labels"]}
}

# Example deleted
{
    "event_type": "training_example.deleted",
    "aggregate_type": "training_example",
    "aggregate_id": "example-uuid",
    "payload": {}
}
```

## Execution Examples

```bash
# Create example
curl -X POST http://localhost:8011/training-examples/ \
  -H "Content-Type: application/json" \
  -d '{
    "input_text": "Write a function to sort an array",
    "output_text": "function sortArray(arr) { return arr.sort((a, b) => a - b); }",
    "domain": "coding",
    "task_type": "code_generation",
    "quality_score": 90.0
  }'

# Get example
curl http://localhost:8011/training-examples/660e8400-e29b-41d4-a716-446655440001

# Update example
curl -X PATCH http://localhost:8011/training-examples/660e8400-e29b-41d4-a716-446655440001 \
  -d '{"quality_score": 95.0, "labels": ["verified"]}'

# List examples with filters
curl "http://localhost:8011/training-examples/?domain=coding&min_quality=80&limit=20"

# Get statistics
curl http://localhost:8011/training-examples/stats

# Delete example
curl -X DELETE http://localhost:8011/training-examples/660e8400-e29b-41d4-a716-446655440001
```

## Example Structure Examples

### Code Generation Example
```json
{
  "input_text": "Create a TypeScript function to validate email addresses",
  "input_structured": {
    "language": "typescript",
    "constraints": ["must return boolean", "handle edge cases"]
  },
  "output_text": "function validateEmail(email: string): boolean {...}",
  "expected_actions": [
    {"tool": "Write", "params": {"file": "validators.ts"}}
  ],
  "final_answer": "Email validation function created",
  "domain": "backend",
  "task_type": "code_generation",
  "labels": ["typescript", "validation", "email"],
  "difficulty": 0.4
}
```

### Reasoning Example
```json
{
  "input_text": "Why is my React component re-rendering too often?",
  "input_structured": {
    "context": "Component uses multiple useState hooks"
  },
  "output_text": "Let me analyze the potential causes...",
  "expected_actions": [
    {"tool": "Read", "params": {"file": "Component.tsx"}},
    {"tool": "Grep", "params": {"pattern": "useState|useEffect"}}
  ],
  "final_answer": "The component lacks useMemo for expensive computations",
  "domain": "debugging",
  "task_type": "reasoning",
  "labels": ["react", "performance", "debugging"],
  "difficulty": 0.7
}
```

### Planning Example
```json
{
  "input_text": "Plan the implementation of a user authentication system",
  "input_structured": {
    "requirements": ["OAuth", "JWT", "password reset"]
  },
  "output_text": "I will break this down into steps...",
  "expected_actions": [
    {"action": "create_plan", "steps": 5},
    {"action": "create_tasks", "count": 8}
  ],
  "final_answer": "Authentication system plan created with 8 tasks",
  "domain": "planning",
  "task_type": "planning",
  "labels": ["auth", "security", "architecture"],
  "difficulty": 0.8
}
```

## Implementation Status

| Component | Status |
|-----------|--------|
| Create Example | Complete |
| Get Example | Complete |
| Update Example | Complete |
| Delete Example | Complete |
| List Examples | Complete |
| Multi-Filter Query | Complete |
| Statistics | Complete |
| Redis Events | Complete |

## Remaining Work

| Item | Priority | Description |
|------|----------|-------------|
| Bulk Import | Medium | Import multiple examples at once |
| Duplicate Detection | Medium | Hash-based dedup on create |
| Export to Dataset | Medium | Export filtered examples to dataset |
| Full-Text Search | Low | Search input/output text |
| Time-Range Filter | Low | Filter by date range |
| Label Aggregation | Low | List all unique labels |

## Strengths

- **Full CRUD** - Complete create/read/update/delete operations
- **Rich filtering** - Agent, domain, quality, source filters
- **Statistics API** - Aggregate stats for training data
- **Quality tracking** - Score and confidence for each example
- **Dedup support** - source_trace_hash for duplicate detection
- **Redis events** - Real-time notifications for data pipeline

## Weaknesses

- **No bulk import** - Must create one at a time
- **No dedup enforcement** - Hash stored but not checked
- **No full-text search** - Cannot search content
- **No export** - Must manually copy to datasets
- **Labels not indexed** - Label queries not optimized

## Best Practices

### Quality Scoring
Use consistent quality scales:
- **90-100**: Excellent, verified examples
- **70-89**: Good, usable examples
- **50-69**: Acceptable, may need review
- **<50**: Low quality, consider deletion

### Source Tracking
Always set source_type correctly:
```python
example = TrainingExampleCreate(
    source_type=ExampleSource.EXECUTION_TRACE,
    source_trace_hash=hash_trace(execution_trace),
    extracted_by="L07 TrainingDataExtractor"
)
```

### Domain Conventions
Use consistent domain names:
- `frontend` - UI/React/CSS work
- `backend` - API/server work
- `devops` - Infrastructure/deployment
- `planning` - Task decomposition
- `debugging` - Problem investigation
- `documentation` - Docs/comments

## Source Files

- Service: `platform/src/L01_data_layer/services/training_example_service.py`
- Models: `platform/src/L01_data_layer/models/training_example.py`
- Routes: (likely in `routers/training_examples.py`)

## Related Services

- DatasetService (L01) - Training datasets
- EvaluationStore (L01) - Quality evaluations
- FeedbackStore (L01) - Corrections/feedback
- TrainingDataExtractor (L07) - Extracts examples
- DatasetCurator (L07) - Curates training sets
- FineTuningEngine (L07) - Uses examples for training

---
*Generated: 2026-01-24 | Platform Services Documentation*
