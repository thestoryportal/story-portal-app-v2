# L06 Evaluation Layer

## Overview

The Evaluation Layer (L06) provides continuous quality observability, data-driven optimization, compliance validation, and autonomous self-healing for agent-based systems.

## Purpose

L06 measures **how well execution occurred**, not execution itself. It provides:

- Multi-dimensional quality scoring
- Statistical anomaly detection
- Compliance constraint validation
- Real-time alerting and remediation
- SLA monitoring and enforcement

## Architecture

### Event Flow
```
L01 (Event Stream) → CloudEvent Validation → Deduplication
  → Metrics Engine → Quality Scorer → Anomaly Detector
    → Compliance Validator → Alert Manager → [Slack/PagerDuty/Email]
      → Audit Trail → REST APIs → Dashboards
```

### Components

1. **Event Validator**: Validates CloudEvents schema and source whitelist
2. **Deduplication Engine**: Prevents duplicate event processing
3. **Metrics Engine**: Aggregates time-series metrics
4. **Quality Scorer**: Computes multi-dimensional quality scores
5. **Anomaly Detector**: Detects statistical deviations using z-score
6. **Compliance Validator**: Checks constraint violations
7. **Alert Manager**: Routes alerts with exponential backoff retry
8. **Storage Manager**: TSDB writes with tiered storage
9. **Query Engine**: Cached metric queries with pagination
10. **Configuration Manager**: Hot-reload config validation
11. **Audit Logger**: Immutable audit trail
12. **Cache Manager**: Redis-based caching
13. **Evaluation Service**: Main orchestrator

## Quality Dimensions

L06 scores agent execution across 5 dimensions:

1. **Accuracy** (0-100): Goal achievement, correctness
2. **Latency** (0-100): p95 latency vs target
3. **Cost** (0-100): Token/resource cost vs budget
4. **Reliability** (0-100): Success rate, error rate
5. **Compliance** (0-100): Policy adherence

Overall score = weighted sum of dimensions (weights must sum to 1.0)

## Assessment Levels

- **Good**: Score ≥ 80
- **Warning**: Score 60-79
- **Critical**: Score < 60

## Error Codes

L06 uses error codes E6000-E6999:

- **E6001-E6005**: Authentication & Authorization
- **E6101-E6105**: Data Integrity & Validation
- **E6201-E6205**: Configuration & Policy
- **E6301-E6305**: Metric Collection & Storage
- **E6401-E6404**: Quality Scoring
- **E6501-E6504**: Anomaly Detection
- **E6601-E6604**: Compliance & Audit
- **E6703, E6705**: Integration Errors
- **E6801-E6803**: Dashboard & Reporting
- **E6901, E6904-E6905**: Operational Errors

## Integration Points

### Consumed Events (from L01)
- `task.completed`: Task execution finished
- `agent.execution.started`: Agent began task
- `agent.execution.finished`: Agent completed task
- `model.inference.used`: LLM model called
- `error.occurred`: Error reported
- `constraint.checked`: Constraint evaluated

### Exposed APIs
- `GET /api/v1/metrics/query`: Query time-series metrics
- `GET /api/v1/quality-scores`: Get agent quality scores
- `GET /api/v1/anomalies`: List detected anomalies
- `GET /api/v1/compliance/violations`: List violations
- `GET /api/v1/sla/status`: Check SLA compliance
- `GET/PUT/POST /api/v1/config`: Configuration management

## Performance SLOs

- **Metric ingestion**: <1s p99
- **Quality scoring**: <50ms p99
- **Anomaly detection**: <10ms p99
- **API queries**: <100ms p95

## Dependencies

- **Redis**: Hot cache (7 days), deduplication, baselines
- **PostgreSQL**: Warm storage (30 days), audit trail
- **L01 Data Layer**: Event stream, audit log, configuration
- **L02 Agent Runtime**: Runtime metrics source
- **L04 Model Gateway**: LLM inference for scoring
- **L05 Planning**: Plan quality evaluation

## Usage

```python
from src.L06_evaluation.services.evaluation_service import EvaluationService
from src.L06_evaluation.models.cloud_event import CloudEvent

# Initialize service
service = EvaluationService()
await service.initialize()

# Process event
event = CloudEvent(
    id="event-123",
    source="l02.agent-runtime",
    type="task.completed",
    subject="task-456",
    data={"agent_id": "agent-001", "duration_ms": 150, "success": True}
)
await service.process_event(event)

# Query quality scores
scores = await service.get_quality_scores(
    agent_id="agent-001",
    start=datetime.now() - timedelta(hours=1),
    end=datetime.now()
)
```

## Development

### Running Tests
```bash
cd /Volumes/Extreme\ SSD/projects/story-portal-app/platform
python3 -m pytest src/L06_evaluation/tests/ -v
```

### Syntax Validation
```bash
python3 -m py_compile $(find src/L06_evaluation -name "*.py")
```

### Import Check
```bash
python3 -c "from src.L06_evaluation import *; print('OK')"
```

## Specification

Full specification: `/Volumes/Extreme SSD/projects/story-portal-app/platform/specs/evaluation-layer-specification-v1.2-final-ASCII.md`

## Status

Current implementation status tracked in: [PROGRESS.md](./PROGRESS.md)
