Implement L06 Evaluation Layer: Autonomous end-to-end sprint.

## CRITICAL ENVIRONMENT CONSTRAINTS

READ THESE FIRST - DO NOT VIOLATE:

1. DO NOT create docker-compose files - infrastructure ALREADY RUNNING
2. DO NOT create virtual environments (venv) - use system Python
3. DO NOT run docker-compose up - services ALREADY RUNNING
4. ALWAYS use: pip install <package> --break-system-packages
5. CORRECT directory: /Volumes/Extreme SSD/projects/story-portal-app/platform/src/L06_evaluation/

## Running Infrastructure (DO NOT RECREATE)

| Service | Host | Port | Container/Process |
|---------|------|------|-------------------|
| PostgreSQL | localhost | 5432 | agentic-postgres |
| Redis | localhost | 6379 | agentic-redis |
| Ollama | localhost | 11434 | PM2 managed |

Verify with: docker ps | grep agentic && pm2 status

## Specification

Location: /Volumes/Extreme SSD/projects/story-portal-app/platform/specs/evaluation-layer-specification-v1.2-final-ASCII.md

Read specification Sections 3 (Architecture) and 11 (Implementation Guide) first.

## Layer Purpose

The Evaluation Layer (L06) provides continuous quality observability, data-driven optimization, compliance validation, and autonomous self-healing for agent-based systems. It measures how well execution occurred, not execution itself.

## Completed Layers (Available for Integration)

| Layer | Location | Key Integration |
|-------|----------|-----------------|
| L01 Data Layer | MCP services | Event consumption, audit trail |
| L02 Agent Runtime | platform/src/L02_runtime/ | Runtime metrics source |
| L04 Model Gateway | platform/src/L04_model_gateway/ | LLM inference for scoring |
| L05 Planning | platform/src/L05_planning/ | Plan quality evaluation |

## Output Location

/Volumes/Extreme SSD/projects/story-portal-app/platform/src/L06_evaluation/

## Directory Structure

Create these directories and files:

Root: platform/src/L06_evaluation/
  - __init__.py
  - PROGRESS.md
  - README.md

Subdirectory: platform/src/L06_evaluation/models/
  - __init__.py
  - cloud_event.py (CloudEvent, EventSource, EventType)
  - metric.py (MetricPoint, MetricType, MetricAggregation)
  - quality_score.py (QualityScore, DimensionScore, Assessment)
  - anomaly.py (Anomaly, AnomalySeverity, Baseline)
  - compliance.py (ComplianceResult, Constraint, Violation)
  - alert.py (Alert, AlertChannel, AlertSeverity)
  - sla.py (SLADefinition, SLAStatus, SLAViolation)
  - error_codes.py (E6000-E6999)

Subdirectory: platform/src/L06_evaluation/services/
  - __init__.py
  - event_validator.py (CloudEvent validation, source whitelist)
  - deduplication_engine.py (Idempotency, duplicate detection)
  - metrics_engine.py (Aggregation, time windows, percentiles)
  - quality_scorer.py (Multi-dimensional scoring)
  - anomaly_detector.py (Z-score, baseline training)
  - compliance_validator.py (Constraint checking)
  - alert_manager.py (Routing to Slack/PagerDuty/email)
  - storage_manager.py (TSDB writes, tiered storage)
  - query_engine.py (Metric queries, caching)
  - config_manager.py (Hot-reload, validation)
  - audit_logger.py (Immutable audit trail)
  - cache_manager.py (Redis caching)
  - evaluation_service.py (Main orchestrator)

Subdirectory: platform/src/L06_evaluation/scorers/
  - __init__.py
  - base.py (Scorer protocol)
  - accuracy_scorer.py (Goal achievement, correctness)
  - latency_scorer.py (p50/p95/p99 latency)
  - cost_scorer.py (Token cost, resource cost)
  - reliability_scorer.py (Error rate, success rate)
  - compliance_scorer.py (Policy adherence)

Subdirectory: platform/src/L06_evaluation/tests/
  - __init__.py
  - conftest.py
  - test_models.py
  - test_event_validator.py
  - test_metrics_engine.py
  - test_quality_scorer.py
  - test_anomaly_detector.py
  - test_integration.py

## Implementation Phases

Execute in order per spec Section 11:

### Phase 1: Foundation (Models)

Create data models per spec Section 5.

CloudEvent fields (per CloudEvents spec):
  - id: str (UUID, idempotency key)
  - source: str (event origin URI)
  - type: str (event type identifier)
  - subject: str (subject of event)
  - time: datetime (event timestamp)
  - data: dict (event payload)
  - datacontenttype: str (default application/json)

MetricPoint fields:
  - metric_name: str
  - value: float
  - timestamp: datetime
  - labels: dict[str, str]
  - metric_type: MetricType (COUNTER, GAUGE, HISTOGRAM)

QualityScore fields:
  - score_id: str (UUID)
  - agent_id: str
  - tenant_id: str
  - timestamp: datetime
  - overall_score: float (0-100)
  - dimensions: dict[str, DimensionScore]
  - assessment: str (Good/Warning/Critical)
  - data_completeness: float (0-1)
  - cached: bool

DimensionScore fields:
  - dimension: str (accuracy, latency, cost, reliability, compliance)
  - score: float (0-100)
  - weight: float (0-1, all weights sum to 1.0)
  - raw_metrics: dict

Anomaly fields:
  - anomaly_id: str (UUID)
  - metric_name: str
  - severity: AnomalySeverity (INFO, WARNING, CRITICAL)
  - baseline_value: float
  - current_value: float
  - z_score: float
  - detected_at: datetime
  - resolved_at: datetime | None

Error codes E6000-E6999 per spec Section 14.

### Phase 2: Event Validation and Deduplication

Event Validator per spec Section 3.2:
  - Validate CloudEvent schema
  - Source whitelist validation
  - Timestamp bounds checking (not future, not too old)
  - Input sanitization (reject injection patterns)

Deduplication Engine:
  - Track event IDs in Redis (24h TTL)
  - Fallback queue for duplicates
  - Idempotency key handling

Interface:
  async def validate(event: CloudEvent) -> CloudEvent | None:
      # Returns validated event or None if invalid
      
  async def is_duplicate(event_id: str) -> bool:
      # Check Redis for existing event ID

### Phase 3: Metrics Engine

Metrics aggregation per spec Section 3.2:
  - Aggregate metrics into time windows (60s default)
  - Compute avg, sum, min, max, percentiles (p50, p95, p99)
  - Label-based grouping
  - Cardinality limiting (max 100K series per tenant)

Interface:
  async def ingest(metric: MetricPoint) -> None:
      # Store metric in time-series storage
      
  async def query(
      metric_name: str,
      start: datetime,
      end: datetime,
      labels: dict,
      aggregation: str = "avg"
  ) -> list[MetricPoint]:
      # Query metrics with aggregation

Storage: Use Redis sorted sets for hot data, PostgreSQL for persistence.

### Phase 4: Quality Scorer

Multi-dimensional scoring per spec Section 3.2:
  - 5 dimensions: accuracy, latency, cost, reliability, compliance
  - Configurable weights (must sum to 1.0)
  - Score range 0-100
  - Assessment thresholds: Good (>=80), Warning (60-79), Critical (<60)

Formula:
  overall_score = sum(dimension_score * dimension_weight)

Interface:
  async def compute_score(
      agent_id: str,
      tenant_id: str,
      time_window: tuple[datetime, datetime]
  ) -> QualityScore:
      # Compute multi-dimensional quality score

Dimension scorers:
  - AccuracyScorer: Goal achievement rate, correctness
  - LatencyScorer: p95 latency vs target
  - CostScorer: Actual cost vs budget
  - ReliabilityScorer: Success rate, error rate
  - ComplianceScorer: Policy violations

### Phase 5: Anomaly Detector

Statistical anomaly detection per spec Section 3.2:
  - Z-score based detection
  - Baseline training period (1-2 hours)
  - Configurable deviation threshold (default 3.0)
  - Cold-start handling

Interface:
  async def detect(score: QualityScore) -> Anomaly | None:
      # Detect anomaly if z-score exceeds threshold
      
  async def update_baseline(metric_name: str, value: float) -> None:
      # Update running mean and stddev

Baseline storage: Redis with rolling window.

### Phase 6: Compliance Validator

Constraint checking per spec Section 3.2:
  - Deadline violations
  - Budget violations
  - Error rate violations
  - Policy violations

Interface:
  async def validate_compliance(
      execution_id: str,
      constraints: list[Constraint]
  ) -> ComplianceResult:
      # Check all constraints, return violations

### Phase 7: Alert Manager

Alert routing per spec Section 3.2:
  - Slack webhook integration
  - PagerDuty integration (stub)
  - Email integration (stub)
  - Exponential backoff retry (100ms -> 60s)
  - Rate limiting (1 alert/5min per metric per severity)

Interface:
  async def send_alert(alert: Alert) -> bool:
      # Route alert to configured channels

### Phase 8: Storage and Query

Storage Manager:
  - Hot storage: Redis (7 days)
  - Warm storage: PostgreSQL (30 days)
  - Cold storage: Archive (365 days) - stub
  - Fallback queue for write failures

Query Engine:
  - Cached query results (60s TTL)
  - Pagination support
  - Label filtering

### Phase 9: Main Service and Observability

Evaluation Service (main orchestrator):
  class EvaluationService:
      def __init__(
          self,
          event_validator: EventValidator,
          dedup_engine: DeduplicationEngine,
          metrics_engine: MetricsEngine,
          quality_scorer: QualityScorer,
          anomaly_detector: AnomalyDetector,
          compliance_validator: ComplianceValidator,
          alert_manager: AlertManager
      ): ...
      
      async def process_event(self, event: CloudEvent) -> None:
          # 1. Validate event
          # 2. Check duplicate
          # 3. Ingest metrics
          # 4. Compute quality score
          # 5. Detect anomalies
          # 6. Check compliance
          # 7. Send alerts if needed
          # 8. Write audit log
      
      async def get_quality_scores(
          self,
          agent_id: str,
          start: datetime,
          end: datetime
      ) -> list[QualityScore]:
          # Query quality scores for agent

Observability:
  - Prometheus metrics (30+ per spec)
  - Structured logging
  - Error codes E6xxx

## Error Code Range

L06 uses E6000-E6999:

| Range | Category |
|-------|----------|
| E6001-E6005 | Authentication & Authorization |
| E6101-E6105 | Data Integrity & Validation |
| E6201-E6205 | Configuration & Policy |
| E6301-E6305 | Metric Collection & Storage |
| E6401-E6404 | Quality Scoring |
| E6501-E6504 | Anomaly Detection |
| E6601-E6604 | Compliance & Audit |
| E6701-E6705 | Integration Errors |
| E6801-E6803 | Dashboard & Reporting |
| E6901-E6905 | Operational Errors |

## Key Constraints (from spec)

- Metric ingestion latency: <1 second (p99)
- Quality score computation: <50ms (p99)
- Anomaly detection: <10ms per point (p99)
- API response time: <100ms (p95) for reads
- Quality weights must sum to 1.0

## Test Configuration

Create tests/conftest.py with:
  - Event loop fixture
  - Cleanup timeout fixture (2 second max)
  - Mock CloudEvent fixture
  - Mock Redis fixture

## Validation After Each Phase

Run after each phase:
  cd /Volumes/Extreme SSD/projects/story-portal-app/platform
  python3 -m py_compile $(find src/L06_evaluation -name "*.py")
  python3 -c "from src.L06_evaluation import *; print('OK')"

## Progress Logging

After each phase append to PROGRESS.md:
  Phase [N] complete: [components] - [timestamp]

## Final Validation

After all phases:
  1. Syntax check all files
  2. Import check main service
  3. Run test suite with 30 second timeout
  4. Test quality score computation

Integration test:
  python3 << 'EOF'
  import asyncio
  import sys
  sys.path.insert(0, '.')
  
  async def test():
      from src.L06_evaluation.services.evaluation_service import EvaluationService
      from src.L06_evaluation.models.cloud_event import CloudEvent
      
      service = EvaluationService()
      await service.initialize()
      
      # Test event processing
      event = CloudEvent(
          id="test-event-1",
          source="l02.agent-runtime",
          type="task.completed",
          subject="task-123",
          data={"agent_id": "agent-1", "duration_ms": 150, "success": True}
      )
      
      await service.process_event(event)
      print("Event processed: OK")
      
      # Test quality score query
      from datetime import datetime, timedelta
      scores = await service.get_quality_scores(
          agent_id="agent-1",
          start=datetime.now() - timedelta(hours=1),
          end=datetime.now()
      )
      print(f"Quality scores: {len(scores)}")
      
      await service.cleanup()
  
  asyncio.run(test())
  EOF

## Completion Criteria

Sprint complete when:
  - All 9 phases implemented
  - All files pass syntax validation
  - All imports resolve
  - Tests exist for each component
  - Tests pass with no hangs
  - Quality scoring works
  - PROGRESS.md shows all phases complete

## Error Handling

If blocked:
  1. Log blocker to PROGRESS.md
  2. Stub the problematic component with TODO
  3. Continue to next phase
  4. Do not stop the sprint

## Final Steps

1. Create completion summary in PROGRESS.md
2. Stage files: git add platform/src/L06_evaluation/
3. Do NOT commit - await human review

## REMINDERS

- NO docker-compose
- NO venv
- Use --break-system-packages for pip
- Infrastructure ALREADY RUNNING
- Quality weights must sum to 1.0
- Follow L02/L03/L04/L05 patterns

## Begin

Read the specification. Execute all phases. Log progress. Complete end-to-end.