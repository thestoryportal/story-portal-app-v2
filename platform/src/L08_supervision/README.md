# L08 Supervision Layer

Policy evaluation, constraint enforcement, anomaly detection, and escalation management for the agentic platform.

## Overview

The L08 Supervision Layer provides comprehensive oversight capabilities for autonomous agents:

- **Policy Engine**: Evaluate agent requests against configurable policies with deny-wins conflict resolution
- **Constraint Enforcer**: Rate limiting, quotas, and temporal constraints using Redis
- **Anomaly Detector**: Statistical anomaly detection using Z-score and IQR ensemble methods
- **Escalation Orchestrator**: Human-in-the-loop approval workflows with timeout handling
- **Audit Manager**: Cryptographically signed, immutable audit trail
- **Compliance Monitor**: Aggregated compliance scoring and risk level assessment

## Quick Start

### Running the Service

```bash
# Start with uvicorn
uvicorn src.L08_supervision.main:app --port 8008

# Or with docker-compose
docker-compose -f docker-compose.app.yml up l08-supervision
```

### Health Check

```bash
curl http://localhost:8008/health
curl http://localhost:8008/health/live
curl http://localhost:8008/health/ready
```

### Basic Policy Evaluation

```bash
# Create a policy
curl -X POST http://localhost:8008/api/v1/policies \
  -H "Content-Type: application/json" \
  -d '{
    "name": "data_access_policy",
    "rules": [
      {
        "rule_name": "allow_read",
        "condition": "operation == '\''read'\''",
        "action": "ALLOW",
        "priority": 10
      },
      {
        "rule_name": "deny_sensitive_delete",
        "condition": "operation == '\''delete'\'' and resource.sensitive == True",
        "action": "DENY",
        "priority": 100
      }
    ],
    "enabled": true
  }'

# Evaluate a request
curl -X POST http://localhost:8008/api/v1/evaluate \
  -H "Content-Type: application/json" \
  -d '{
    "agent_id": "agent_001",
    "operation": "read",
    "resource": {"type": "dataset", "id": "ds_123"}
  }'
```

## API Reference

### Policy Management

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/policies` | POST | Create a policy |
| `/api/v1/policies` | GET | List policies |
| `/api/v1/policies/{id}` | GET | Get policy by ID |
| `/api/v1/policies/{id}` | PUT | Update policy |
| `/api/v1/policies/{id}` | DELETE | Deprecate policy |
| `/api/v1/policies/{id}/deploy` | POST | Deploy to active set |
| `/api/v1/policies/validate` | POST | Validate policy definition |

### Evaluation

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/evaluate` | POST | Evaluate agent request |
| `/api/v1/constraints/check` | POST | Check rate limit/quota |
| `/api/v1/metrics/report` | POST | Report metric observation |
| `/api/v1/compliance/{agent_id}` | GET | Get compliance status |

### Escalations

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/escalations` | POST | Create escalation |
| `/api/v1/escalations` | GET | List escalations |
| `/api/v1/escalations/{id}` | GET | Get escalation |
| `/api/v1/escalations/{id}/approve` | POST | Approve escalation |
| `/api/v1/escalations/{id}/reject` | POST | Reject escalation |

### Audit

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/audit/search` | GET | Search audit log |
| `/api/v1/audit/{id}` | GET | Get audit entry |
| `/api/v1/audit/verify` | POST | Verify chain integrity |
| `/api/v1/audit/stats` | GET | Get audit statistics |

## Configuration

Configuration via environment variables:

```bash
# Core settings
L08_DEV_MODE=true                    # Enable development mode
L08_PORT=8008                        # Service port

# Integration URLs
L01_BASE_URL=http://localhost:8001   # Data layer
L10_BASE_URL=http://localhost:8010   # Human interface
VAULT_URL=http://localhost:8200      # HashiCorp Vault
REDIS_URL=redis://localhost:6379     # Redis for rate limiting

# Policy settings
POLICY_CACHE_TTL_SECONDS=300
POLICY_CACHE_MAX_SIZE=1000

# Escalation settings
ESCALATION_TIMEOUT_SECONDS=300       # 5 minutes
MAX_ESCALATION_LEVEL=3

# Anomaly detection
ANOMALY_Z_SCORE_THRESHOLD=3.0
ANOMALY_IQR_MULTIPLIER=1.5
MIN_BASELINE_SAMPLES=30

# Security
REQUIRE_MFA_FOR_ADMIN=true
ALLOW_ON_CONSENSUS_FAIL=false
```

## Policy Expression Syntax

Policies use a safe Python-like expression syntax:

```python
# Simple comparison
operation == 'read'

# Nested attribute access
resource.type == 'dataset'
agent.team == 'datascience'

# Boolean operators
operation == 'delete' and resource.sensitive == True
agent.role == 'admin' or agent.role == 'superuser'

# Membership testing
operation in allowed_operations
agent.team in ['engineering', 'datascience']

# Comparison operators
request.amount < 1000
agent.trust_score >= 0.8
```

## Error Codes

| Code | Description |
|------|-------------|
| E8001 | Policy not found |
| E8002 | Policy invalid |
| E8100 | Policy condition parse error |
| E8101 | Policy evaluation error |
| E8200 | Rate limit exceeded |
| E8201 | Quota exceeded |
| E8300 | Escalation not found |
| E8301 | Escalation already resolved |
| E8400 | Anomaly detection failed |
| E8401 | Insufficient baseline data |
| E8500 | Audit write failed |
| E8501 | Audit signature invalid |
| E8600 | Access denied |
| E8700 | L01 bridge connection failed |
| E8800 | Configuration error |
| E8900 | Internal error |

## Architecture

```
L08_supervision/
├── main.py                    # FastAPI application
├── models/
│   ├── domain.py              # Domain models
│   ├── dtos.py                # HTTP DTOs
│   ├── config.py              # Configuration
│   └── error_codes.py         # Error definitions
├── services/
│   ├── policy_engine.py       # Policy evaluation
│   ├── constraint_enforcer.py # Rate limiting
│   ├── anomaly_detector.py    # Statistical detection
│   ├── escalation_orchestrator.py # Workflow management
│   ├── audit_manager.py       # Audit trail
│   ├── access_control.py      # ABAC
│   ├── compliance_monitor.py  # Compliance scoring
│   └── supervision_service.py # Unified service
├── integration/
│   ├── l01_bridge.py          # Data layer integration
│   ├── l10_bridge.py          # Human interface integration
│   ├── vault_client.py        # Cryptographic signing
│   └── redis_client.py        # Rate limiting backend
├── routes/
│   ├── policies.py            # Policy CRUD
│   ├── evaluations.py         # Evaluation endpoints
│   ├── escalations.py         # Escalation workflows
│   ├── audit.py               # Audit trail
│   └── health.py              # Health checks
└── tests/
    ├── conftest.py            # Fixtures
    ├── test_policy_engine.py
    ├── test_constraint_enforcer.py
    ├── test_anomaly_detector.py
    ├── test_escalation.py
    ├── test_audit.py
    └── test_routes.py
```

## Testing

```bash
# Run all L08 tests
pytest src/L08_supervision/tests/ -v

# Run specific test file
pytest src/L08_supervision/tests/test_policy_engine.py -v

# Run with coverage
pytest src/L08_supervision/tests/ --cov=src/L08_supervision --cov-report=html

# Run only unit tests
pytest src/L08_supervision/tests/ -m unit -v

# Run performance tests
pytest src/L08_supervision/tests/ -m performance -v
```

## Performance

- Policy evaluation: <100ms p99 latency
- Rate limit checks: <10ms p99 latency
- Anomaly detection: <50ms p99 latency
- Audit write: <20ms p99 latency

## Integration

### With L01 Data Layer
- Policy definitions stored in PostgreSQL
- Audit entries persisted to event store
- Agent context loaded for evaluation

### With L10 Human Interface
- Escalation notifications via webhooks
- MFA verification for sensitive approvals
- Dashboard updates via WebSocket

### With Vault
- ECDSA-P256 signing for audit entries
- HMAC-SHA256 fallback for development
- Key rotation support

## Development Mode

In development mode (`L08_DEV_MODE=true`):
- Vault signing uses HMAC fallback
- Redis uses in-memory fallback
- L01/L10 bridges use local storage
- MFA verification is skipped
