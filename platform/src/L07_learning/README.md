# L07 Learning Layer

**Status:** ✅ Production Ready (Local Development Mode)
**Version:** 1.0.0
**Layer:** L07

## Overview

The Learning Layer (L07) is the continuous improvement engine of the agentic system. It extracts training data from execution traces, manages model fine-tuning pipelines, implements RLHF feedback loops, and enables the system to improve autonomously based on quality signals from L06.

### Key Distinction

- **L06 Evaluation Layer** measures WHAT happened (quality scores)
- **L07 Learning Layer** determines WHY and HOW to make it better

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    L07 Learning Layer                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  [L02/L05 Traces] → [Training Data Extractor]                   │
│         ↓                                                         │
│  [Quality Filter] → [Dataset Curator] → [Versioned Dataset]     │
│         ↓                                                         │
│  [Fine-Tuning Engine] → [Training Job] → [Model Artifact]       │
│         ↓                                                         │
│  [Model Validator] → [Validation Report]                         │
│         ↓                                                         │
│  [Model Registry] → [Stage Transitions] → [L04 Deployment]      │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
```

## Components

### 1. Training Data Extractor
**Path:** `services/training_data_extractor.py`

Extracts structured training examples from:
- L02 execution traces (execution.completed events)
- L05 planning traces (planning.completed events)
- L06 quality scores (evaluation.completed events)

**Features:**
- Async batch processing
- Automatic difficulty estimation
- Domain classification
- Trace validation and error handling

### 2. Example Quality Filter
**Path:** `services/example_quality_filter.py`

Multi-criteria filtering to ensure high-quality training data:
- Quality score threshold (default: 70/100)
- Confidence threshold (default: 0.6/1.0)
- Anomaly detection (Isolation Forest)
- Diversity assessment
- Stratified sampling

### 3. Dataset Curator
**Path:** `services/dataset_curator.py`

Manages versioned datasets with train/val/test splits:
- Semantic versioning (1.0.0, 1.0.1, etc.)
- Stratified splitting (80/10/10)
- Dataset statistics computation
- Incremental updates
- Lineage tracking

### 4. Fine-Tuning Engine
**Path:** `services/fine_tuning_engine.py`

Orchestrates model training:
- **Local Development:** Simulated training (no GPU required)
- **Production:** HuggingFace + PyTorch + LoRA
- Training job lifecycle management
- Metrics collection
- Automatic model artifact creation

### 5. RLHF Engine (Stub)
**Path:** `services/rlhf_engine.py`

Reinforcement Learning from Human Feedback:
- Reward model training interface (stub)
- PPO policy optimization interface (stub)
- Preference pair generation
- Reward signal conversion from L06 scores

**Note:** Full RLHF requires GPU resources, stub for local dev.

### 6. Model Validator
**Path:** `services/model_validator.py`

5-stage pre-deployment validation:
1. **Regression Testing** - Golden test suite
2. **Performance Benchmarking** - Compare to baseline
3. **Safety Analysis** - Security checks
4. **Diversity Testing** - Cross-domain performance
5. **Latency Profiling** - Inference speed

**Recommendations:** DEPLOY | REVIEW | REJECT

### 7. Model Registry
**Path:** `services/model_registry.py`

Model lifecycle management:
- Artifact registration and versioning
- Stage transitions (DEVELOPMENT → STAGING → PRODUCTION)
- Digital signatures and checksums
- Lineage tracking
- Validation gates

### 8. Learning Service (Orchestrator)
**Path:** `services/learning_service.py`

Central coordinator bringing all components together:
- End-to-end pipeline orchestration
- Component initialization and cleanup
- Statistics aggregation
- Async event processing

## Data Models

### Core Models (models/)

| Model | Purpose |
|-------|---------|
| `TrainingExample` | Input-output pairs with quality scores |
| `Dataset` | Versioned collection with train/val/test splits |
| `TrainingJob` | Training execution with lifecycle |
| `ModelArtifact` | Trained model with metadata |
| `RewardSignal` | RLHF reward from quality scores |
| `CurriculumStage` | Curriculum learning progression |
| `BehavioralPattern` | Extracted decision patterns |

### Error Codes

Range: **E7000-E7999**

| Range | Category |
|-------|----------|
| E7000-E7099 | Training data extraction |
| E7100-E7199 | Example filtering |
| E7200-E7299 | Model registry and deployment |
| E7300-E7399 | RLHF and reward modeling |
| E7400-E7499 | Monitoring and reliability |
| E7500-E7599 | Configuration |
| E7600-E7699 | Knowledge distillation |
| E7700-E7799 | Cost and resources |
| E7800-E7899 | Observability |
| E7900-E7999 | System and integration |

## Quick Start

### Basic Usage

```python
import asyncio
from src.L07_learning.services.learning_service import LearningService

async def main():
    # Initialize service
    service = LearningService(storage_path="/tmp/l07")
    await service.initialize()

    # Process events from L01
    events = [...]  # CloudEvents from execution stream
    examples = await service.process_events_batch(events)

    # Filter examples
    filtered = await service.filter_examples(examples)

    # Create dataset
    dataset = await service.create_training_dataset(
        name="my-dataset",
        examples=filtered
    )

    # Train model (simulated)
    job = await service.train_model(
        dataset_id=dataset.dataset_id,
        base_model_id="gpt-4-turbo-2024-04"
    )

    # Wait for completion
    while not job.is_terminal():
        await asyncio.sleep(1)
        job = await service.fine_tuning_engine.get_job_status(job.job_id)

    # Validate model
    if job.output_model_id:
        result = await service.validate_model(job.output_model_id)
        print(f"Validation: {result.recommendation}")

    await service.cleanup()

asyncio.run(main())
```

### End-to-End Pipeline

```python
async def run_pipeline():
    service = LearningService()
    await service.initialize()

    # Run complete pipeline
    result = await service.end_to_end_pipeline(
        events=events,
        dataset_name="auto-dataset",
        base_model_id="gpt-4-turbo-2024-04"
    )

    print(f"Status: {result['status']}")
    print(f"Model ID: {result['model_id']}")
    print(f"Validation: {result['validation_recommendation']}")

    await service.cleanup()
```

## Configuration

### Training Configuration

```python
from src.L07_learning.models.training_job import JobConfig, LoRAConfig

config = JobConfig(
    learning_rate=2e-5,
    batch_size=16,
    num_epochs=3,
    lora_config=LoRAConfig(
        rank=16,
        alpha=32,
        dropout=0.05
    )
)
```

### Filter Configuration

```python
from src.L07_learning.services.example_quality_filter import FilterConfig

filter_config = FilterConfig(
    quality_threshold=70.0,
    confidence_threshold=0.6,
    max_outlier_probability=0.15
)
```

## Integration

### L01 Data Layer
- Consumes CloudEvents from event stream
- Stores training examples and datasets
- Persists model artifacts

### L02 Agent Runtime
- Receives execution.completed events
- Extracts agent decision traces
- Quality annotations from L06

### L04 Model Gateway
- Deploys fine-tuned models
- Registers with model gateway
- A/B testing support

### L05 Planning Layer
- Receives planning.completed events
- Extracts planning strategies
- Optimizes planning decisions

### L06 Evaluation Layer
- **Primary dependency**
- Quality scores (0-100)
- Confidence levels (0-1)
- Converts to reward signals

## Local Development

### Simulation Mode

Training is **simulated** for local development:
- ✅ No GPU required
- ✅ Fast execution (seconds not hours)
- ✅ Realistic metrics and loss curves
- ✅ Complete pipeline testing

### Dependencies

```bash
pip3 install numpy --break-system-packages
```

Optional (for anomaly detection):
```bash
pip3 install scikit-learn --break-system-packages
```

### Running Tests

```bash
cd /Volumes/Extreme\ SSD/projects/story-portal-app/platform
pytest src/L07_learning/tests/test_integration.py -v
```

## Production Deployment

### Real Training

Replace simulation with actual training:

```python
engine = FineTuningEngine(
    model_registry=registry,
    dataset_curator=curator,
    simulate_training=False  # Enable real training
)
```

Requires:
- GPU resources (CUDA)
- HuggingFace transformers
- PyTorch
- PEFT (for LoRA)

### RLHF

Enable full RLHF pipeline:

```python
service = LearningService(enable_rlhf=True)
```

Requires:
- Significant GPU resources
- Reward model training infrastructure
- PPO implementation
- Rollout generation

## Statistics and Observability

### Get Statistics

```python
stats = service.get_statistics()

print(f"Extracted: {stats['extractor']['total_extracted']}")
print(f"Filtered: {stats['filter']['accepted_count']}")
print(f"Datasets: {stats['curator']['total_datasets']}")
print(f"Models: {stats['registry']['total_models']}")
print(f"Training Jobs: {stats['fine_tuning']['total_jobs']}")
```

### Logging

All services use Python logging:

```python
import logging
logging.basicConfig(level=logging.INFO)
```

## Model Lifecycle

### Stage Transitions

```
DEVELOPMENT → STAGING → PRODUCTION
     ↓            ↓           ↓
 ARCHIVED    QUARANTINED  ARCHIVED
```

### Deployment Flow

1. Training completes → DEVELOPMENT
2. Validation passes → STAGING
3. Manual approval + signing → PRODUCTION
4. Issues detected → QUARANTINED
5. Superseded → ARCHIVED

## Best Practices

### Training Data Quality

- Minimum quality score: 70/100
- Minimum confidence: 0.6
- Filter outliers with Isolation Forest
- Maintain domain diversity

### Dataset Management

- Version all datasets
- Track lineage
- Stratified splits
- Regular statistics computation

### Model Validation

- Always validate before production
- Compare against baseline
- Run safety checks
- Monitor latency

### Production Readiness

1. Sign all production models
2. Validate stage transitions
3. Track model lineage
4. Monitor performance metrics

## Troubleshooting

### Import Errors

```bash
# Install numpy
pip3 install numpy --break-system-packages
```

### Training Failures

Check job status:
```python
job = await service.fine_tuning_engine.get_job_status(job_id)
print(f"Status: {job.status}, Error: {job.error_message}")
```

### Validation Failures

Review validation stages:
```python
result = await service.validate_model(model_id)
for stage_name, stage_result in result.stages.items():
    print(f"{stage_name}: {'PASS' if stage_result.passed else 'FAIL'}")
    if stage_result.errors:
        print(f"  Errors: {stage_result.errors}")
```

## Future Enhancements

### Planned Features

- [ ] Real GPU training with HuggingFace
- [ ] Full RLHF with PPO
- [ ] Knowledge distillation
- [ ] Curriculum learning progression
- [ ] Pattern extraction and replay
- [ ] Multi-domain specialization
- [ ] Active learning selector
- [ ] Cost-benefit analysis
- [ ] Prometheus metrics export

## References

- [Specification](../../specs/learning-layer-specification-v1.2-final-ASCII.md)
- [L01 Data Layer](../L01_data/)
- [L02 Agent Runtime](../L02_runtime/)
- [L04 Model Gateway](../L04_model_gateway/)
- [L06 Evaluation](../L06_evaluation/)

## Support

For issues or questions:
- Check [PROGRESS.md](./PROGRESS.md) for implementation details
- Review error codes in `models/error_codes.py`
- Enable debug logging: `logging.basicConfig(level=logging.DEBUG)`

---

**Autonomous Implementation:** Claude Sonnet 4.5
**Date:** 2026-01-15
**Status:** Production Ready (Local Development Mode)
