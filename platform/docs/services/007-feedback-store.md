# Service 7/44: FeedbackStore

## Overview

| Property | Value |
|----------|-------|
| **Layer** | L01 (Data Layer) |
| **Module** | `L01_data_layer.services.feedback_store` |
| **Status** | Fully Implemented & Healthy |
| **Dependencies** | PostgreSQL |
| **Category** | Data & Storage |

## Role in Development Environment

The **FeedbackStore** captures human and automated feedback for learning loops. It stores:
- User ratings and corrections
- Automated quality signals
- Processing status for feedback queue

This enables **RLHF-style improvements** by collecting feedback that can be used to curate training data or trigger agent retraining.

## Data Model

### FeedbackEntry Fields
- `id: UUID` - Unique identifier
- `agent_id: UUID` - Agent that received feedback
- `task_id: UUID` - Optional associated task
- `feedback_type: str` - Type (human, automated, correction)
- `rating: int` - 1-5 star rating (optional)
- `content: str` - Feedback text/description
- `metadata: Dict` - Additional context
- `processed: bool` - Whether feedback has been processed
- `created_at: datetime` - Feedback timestamp

### Feedback Types
- `human` - User-provided feedback
- `automated` - System-generated quality signals
- `correction` - Explicit corrections to agent output
- `preference` - A/B preference between outputs

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/feedback/` | Record new feedback |
| `GET` | `/feedback/{id}` | Get feedback by ID |
| `GET` | `/feedback/` | List feedback (filter by agent) |
| `GET` | `/feedback/unprocessed` | Get unprocessed feedback queue |
| `PATCH` | `/feedback/{id}` | Mark as processed |

## Use Cases in Your Workflow

### 1. Record User Feedback on Agent Output
```bash
curl -X POST http://localhost:8011/feedback/ \
  -H "Content-Type: application/json" \
  -d '{
    "agent_id": "550e8400-e29b-41d4-a716-446655440000",
    "task_id": "660e8400-e29b-41d4-a716-446655440001",
    "feedback_type": "human",
    "rating": 4,
    "content": "Good code generation but missed error handling",
    "metadata": {
      "session_id": "sess-123",
      "user_id": "user-456"
    }
  }'
```

### 2. Record Correction
```bash
curl -X POST http://localhost:8011/feedback/ \
  -H "Content-Type: application/json" \
  -d '{
    "agent_id": "550e8400-e29b-41d4-a716-446655440000",
    "feedback_type": "correction",
    "content": "Original output was wrong. Correct answer is: ...",
    "metadata": {
      "original_output": "...",
      "corrected_output": "...",
      "correction_type": "factual_error"
    }
  }'
```

### 3. Process Feedback Queue
```bash
# Get unprocessed feedback
curl http://localhost:8011/feedback/unprocessed?limit=50

# Mark feedback as processed after handling
curl -X PATCH http://localhost:8011/feedback/880e8400-e29b-41d4-a716-446655440003 \
  -H "Content-Type: application/json" \
  -d '{"processed": true}'
```

### 4. List Agent Feedback History
```bash
curl "http://localhost:8011/feedback/?agent_id=550e8400-e29b-41d4-a716-446655440000&limit=20"
```

## Service Interactions

```
+------------------+
|  FeedbackStore   | <--- L01 Data Layer (PostgreSQL)
|     (L01)        |
+--------+---------+
         |
         v
+------------------+     +-------------------+
| LearningService  |     |  DatasetCurator   |
|     (L07)        |     |      (L07)        |
+------------------+     +-------------------+
         |
         v
+------------------+     +-------------------+
|TrainingExample   |     |  FineTuningEngine |
|   Service (L01)  |     |      (L07)        |
+------------------+     +-------------------+
```

**Integration Points:**
- **LearningService (L07)**: Polls unprocessed feedback for training signals
- **DatasetCurator (L07)**: Uses corrections to curate training examples
- **TrainingExampleService (L01)**: Corrections may become new training examples
- **EvaluationStore (L01)**: Feedback informs evaluation metrics

## Processing Workflow

1. **Collect**: Feedback recorded with `processed=false`
2. **Queue**: `get_unprocessed_feedback()` returns pending items
3. **Process**: Learning service analyzes and acts on feedback
4. **Complete**: Mark as `processed=true` via update

```python
# Learning service workflow
unprocessed = await feedback_store.get_unprocessed_feedback(limit=100)
for feedback in unprocessed:
    # Analyze and potentially create training example
    if feedback.feedback_type == "correction":
        await create_training_example(feedback)
    # Mark as processed
    await feedback_store.update_feedback(
        feedback.id,
        FeedbackUpdate(processed=True)
    )
```

## Execution Examples

```bash
# Record human feedback with rating
curl -X POST http://localhost:8011/feedback/ \
  -H "Content-Type: application/json" \
  -d '{
    "agent_id": "550e8400-e29b-41d4-a716-446655440000",
    "feedback_type": "human",
    "rating": 5,
    "content": "Excellent response, exactly what I needed"
  }'

# Record automated quality signal
curl -X POST http://localhost:8011/feedback/ \
  -H "Content-Type: application/json" \
  -d '{
    "agent_id": "550e8400-e29b-41d4-a716-446655440000",
    "task_id": "770e8400-e29b-41d4-a716-446655440002",
    "feedback_type": "automated",
    "content": "Code passed all tests",
    "metadata": {
      "tests_passed": 15,
      "tests_failed": 0,
      "coverage": 0.87
    }
  }'

# Get specific feedback
curl http://localhost:8011/feedback/880e8400-e29b-41d4-a716-446655440003

# List recent feedback
curl http://localhost:8011/feedback/

# Filter by agent
curl "http://localhost:8011/feedback/?agent_id=550e8400-e29b-41d4-a716-446655440000"

# Get unprocessed queue
curl http://localhost:8011/feedback/unprocessed

# Mark as processed
curl -X PATCH http://localhost:8011/feedback/880e8400-e29b-41d4-a716-446655440003 \
  -d '{"processed": true}'
```

## Metadata Examples

### Human Feedback Metadata
```json
{
  "session_id": "sess-123",
  "user_id": "user-456",
  "response_time_ms": 1500,
  "was_helpful": true
}
```

### Correction Metadata
```json
{
  "original_output": "The function returns None",
  "corrected_output": "The function returns an empty list",
  "error_category": "factual_error",
  "severity": "high"
}
```

### Automated Signal Metadata
```json
{
  "source": "test_runner",
  "tests_passed": 15,
  "tests_failed": 0,
  "lint_errors": 2,
  "coverage_percent": 87
}
```

## Implementation Status

| Component | Status |
|-----------|--------|
| Record Feedback | Complete |
| Get Feedback | Complete |
| List Feedback | Complete |
| Agent Filter | Complete |
| Unprocessed Queue | Complete |
| Mark Processed | Complete |
| PostgreSQL Integration | Complete |

## Remaining Work

| Item | Priority | Description |
|------|----------|-------------|
| Type Filter | Medium | Filter by feedback_type |
| Rating Aggregation | Medium | Average rating per agent |
| Time-Range Query | Low | Filter by date range |
| Bulk Processing | Low | Mark multiple as processed at once |
| Redis Events | Low | Publish on new feedback |
| Delete Feedback | Low | Remove old processed entries |

## Strengths

- **Simple queue pattern** - processed flag enables easy workflow
- **Flexible types** - Human, automated, corrections all fit
- **Rating support** - 1-5 scale for quick quality signals
- **Agent association** - Track feedback per agent

## Weaknesses

- **No type filtering** - Cannot query by feedback_type
- **No rating aggregation** - Must calculate averages manually
- **No events** - New feedback not published to Redis
- **Limited update** - Can only toggle processed flag
- **No bulk operations** - Process one at a time

## Best Practices

### Feedback Types
Use consistent type names:
- `human` - Direct user feedback
- `automated` - System-generated signals
- `correction` - Explicit error corrections
- `preference` - A/B comparisons

### Content Quality
Include actionable information:
- Specific what was good/bad
- Exact corrections for errors
- Context for understanding

### Processing Discipline
Keep the queue clean:
- Process feedback regularly
- Mark processed promptly
- Handle all feedback types

## Source Files

- Service: `platform/src/L01_data_layer/services/feedback_store.py`
- Models: `platform/src/L01_data_layer/models/feedback.py`
- Routes: (likely in `routers/feedback.py`)

## Related Services

- EvaluationStore (L01) - Formal evaluations (vs. informal feedback)
- LearningService (L07) - Consumes feedback for training
- DatasetCurator (L07) - Uses corrections for curation
- TrainingExampleService (L01) - May create examples from corrections

---
*Generated: 2026-01-24 | Platform Services Documentation*
