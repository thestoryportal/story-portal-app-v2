# Service 3/44: DatasetService

## Overview

| Property | Value |
|----------|-------|
| **Layer** | L01 (Data Layer) |
| **Module** | `L01_data_layer.services.dataset_service` |
| **Status** | Fully Implemented & Healthy |
| **Dependencies** | PostgreSQL, Redis (optional) |
| **Category** | Data & Storage |

## Role in Development Environment

The **DatasetService** manages training datasets for the L07 Learning Layer. It handles:
- Dataset metadata (name, version, description, tags)
- Train/validation/test split management
- Dataset lineage tracking (source datasets, transformations)
- Example-to-dataset linking

This is essential for **fine-tuning workflows** where you need organized training data with proper splits.

## Data Model

### Dataset Fields
- `id: UUID` - Unique identifier
- `name: str` - Dataset name
- `version: str` - Version string (e.g., "1.0.0")
- `description: str` - Human-readable description
- `tags: List[str]` - Searchable tags
- `split_ratios: Dict` - Train/val/test ratios (e.g., {"train": 0.8, "validation": 0.1, "test": 0.1})
- `lineage: Dict` - Provenance tracking (source_datasets, transformations)
- `statistics: Dict` - Dataset statistics (counts, distributions)
- `created_by: str` - Creator identifier
- `created_at: datetime` - Creation timestamp
- `updated_at: datetime` - Last update timestamp

### DatasetSplit Enum
- `TRAIN` - Training split
- `VALIDATION` - Validation split
- `TEST` - Test split

### DatasetExampleLink
Links training examples to datasets with split assignment:
- `dataset_id: UUID`
- `example_id: UUID`
- `split: DatasetSplit`

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/datasets/` | Create new dataset |
| `GET` | `/datasets/{id}` | Get dataset by ID |
| `PATCH` | `/datasets/{id}` | Update dataset metadata |
| `DELETE` | `/datasets/{id}` | Delete dataset |
| `GET` | `/datasets/` | List datasets (with filters) |
| `POST` | `/datasets/{id}/examples` | Add example to dataset |
| `DELETE` | `/datasets/{id}/examples/{example_id}` | Remove example |
| `GET` | `/datasets/{id}/examples` | Get dataset examples |
| `GET` | `/datasets/{id}/splits` | Get split counts |

## Use Cases in Your Workflow

### 1. Create Training Dataset
```bash
curl -X POST http://localhost:8011/datasets/ \
  -H "Content-Type: application/json" \
  -d '{
    "name": "claude-code-examples",
    "version": "1.0.0",
    "description": "Training examples from Claude Code sessions",
    "tags": ["claude-code", "fine-tuning", "code-gen"],
    "split_ratios": {"train": 0.8, "validation": 0.1, "test": 0.1},
    "created_by": "data-pipeline"
  }'
```

### 2. Add Examples to Dataset
```bash
# Add example to training split
curl -X POST http://localhost:8011/datasets/{dataset_id}/examples \
  -H "Content-Type: application/json" \
  -d '{
    "example_id": "550e8400-e29b-41d4-a716-446655440000",
    "split": "train"
  }'
```

### 3. Check Split Distribution
```bash
curl http://localhost:8011/datasets/{dataset_id}/splits
# Response: {"train": 8000, "validation": 1000, "test": 1000}
```

### 4. List Datasets by Tag
```bash
curl "http://localhost:8011/datasets/?tag_filter=fine-tuning"
```

## Service Interactions

```
+------------------+
|  DatasetService  | <--- L01 Data Layer (PostgreSQL)
|     (L01)        |
+--------+---------+
         |
         v
+------------------+     +-------------------+
| TrainingExample  |     |  DatasetCurator   |
|   Service (L01)  |     |      (L07)        |
+------------------+     +-------------------+
         |
         v
+------------------+     +-------------------+
| FineTuningEngine |     |  LearningService  |
|     (L07)        |     |      (L07)        |
+------------------+     +-------------------+
```

**Integration Points:**
- **TrainingExampleService (L01)**: Stores individual examples that get linked to datasets
- **DatasetCurator (L07)**: Quality filtering and curation of datasets
- **FineTuningEngine (L07)**: Consumes datasets for model training
- **LearningService (L07)**: Orchestrates learning workflows using datasets

## Event Publishing

Redis events for dataset lifecycle:
- `dataset.created` - New dataset created
- `dataset.updated` - Dataset metadata updated
- `dataset.deleted` - Dataset removed
- `dataset.example_added` - Example linked to dataset
- `dataset.example_removed` - Example unlinked

## Lineage Tracking

Track dataset provenance:
```json
{
  "source_datasets": ["uuid1", "uuid2"],
  "extraction_jobs": ["job-123", "job-456"],
  "filter_configs": {
    "min_quality_score": 0.8,
    "language": "en"
  },
  "transformations": [
    {"type": "tokenize", "model": "cl100k_base"},
    {"type": "deduplicate", "threshold": 0.95}
  ]
}
```

## Execution Examples

```bash
# Create a dataset
curl -X POST http://localhost:8011/datasets/ \
  -H "Content-Type: application/json" \
  -d '{
    "name": "code-review-examples",
    "version": "2.0.0",
    "description": "High-quality code review training data",
    "tags": ["code-review", "quality-high"],
    "split_ratios": {"train": 0.85, "validation": 0.10, "test": 0.05},
    "statistics": {"total_examples": 0, "avg_length": 0},
    "created_by": "curator-bot"
  }'

# Get dataset details
curl http://localhost:8011/datasets/550e8400-e29b-41d4-a716-446655440000

# Update dataset description
curl -X PATCH http://localhost:8011/datasets/550e8400-e29b-41d4-a716-446655440000 \
  -H "Content-Type: application/json" \
  -d '{"description": "Updated description", "tags": ["new-tag"]}'

# List all datasets
curl http://localhost:8011/datasets/

# Filter by name
curl "http://localhost:8011/datasets/?name_filter=code"

# Get examples in training split
curl "http://localhost:8011/datasets/{id}/examples?split=train"

# Get service statistics
curl http://localhost:8011/datasets/stats
```

## Implementation Status

| Component | Status |
|-----------|--------|
| Dataset CRUD | Complete |
| Example Linking | Complete |
| Split Management | Complete |
| Tag Filtering | Complete |
| Name Filtering | Complete |
| Lineage Tracking | Complete |
| Statistics | Complete |
| Redis Events | Complete |

## Remaining Work

| Item | Priority | Description |
|------|----------|-------------|
| Bulk Example Import | Medium | Add many examples at once |
| Auto-Split Assignment | Medium | Automatically assign splits based on ratios |
| Version Comparison | Low | Compare different dataset versions |
| Export to JSONL | Low | Export dataset to training file format |
| Validation Rules | Low | Ensure split ratios sum to 1.0 |

## Strengths

- **Versioned datasets** - Track dataset evolution over time
- **Flexible splits** - Custom train/val/test ratios
- **Full lineage** - Know where data came from
- **Tag-based discovery** - Find datasets by purpose
- **Event-driven** - Services react to dataset changes

## Weaknesses

- **No actual data storage** - Only metadata; examples stored separately
- **No file export** - Can't generate training files directly
- **Manual split assignment** - Must assign each example's split manually
- **No validation** - Split ratios not enforced
- **No deduplication** - Same example can be in multiple datasets

## Best Practices

### Dataset Naming
Use semantic versioning and clear names:
- `claude-code-v1.0.0`
- `code-review-v2.1.0`
- `qa-pairs-english-v1.0.0`

### Tag Conventions
Consistent tagging for discovery:
- Task type: `code-gen`, `code-review`, `qa`
- Quality: `quality-high`, `quality-curated`
- Language: `lang-en`, `lang-python`
- Source: `source-github`, `source-internal`

### Split Ratios
Common patterns:
- Standard: `{"train": 0.8, "validation": 0.1, "test": 0.1}`
- Large dataset: `{"train": 0.9, "validation": 0.05, "test": 0.05}`
- Small dataset: `{"train": 0.7, "validation": 0.15, "test": 0.15}`

## Source Files

- Service: `platform/src/L01_data_layer/services/dataset_service.py`
- Models: `platform/src/L01_data_layer/models/dataset.py`
- Routes: (likely in `routers/datasets.py`)

## Related Services

- TrainingExampleService (L01) - Individual training examples
- DatasetCurator (L07) - Quality filtering
- FineTuningEngine (L07) - Model training
- LearningService (L07) - Learning orchestration
- EvaluationStore (L01) - Evaluation results

---
*Generated: 2026-01-24 | Platform Services Documentation*
