# L09 API Gateway Layer

**Version:** 1.2.0
**Error Code Range:** E9000-E9999
**Status:** Production Ready

## Overview

The API Gateway Layer (L09) serves as the primary entry point for all external API requests. It provides comprehensive authentication, authorization, rate limiting, and request routing to backend services.

## Core Features

### 1. Authentication
- **API Key Authentication**: bcrypt-hashed keys with 90-day rotation
- **OAuth 2.0 with JWT**: RS256 signature verification
- **Mutual TLS (mTLS)**: Certificate-based authentication

### 2. Authorization
- **RBAC**: Role-based access control (ADMIN, DEVELOPER, GUEST)
- **OAuth Scopes**: Fine-grained permission scopes
- **ABAC**: Attribute-based policies via L08 Supervision

### 3. Rate Limiting
- **Distributed Token Bucket**: Redis-backed rate limiting
- **Three Tiers**: STANDARD (100 rps), PREMIUM (1000 rps), ENTERPRISE (10K rps)
- **Cost-Aware**: Heavy operations consume more tokens

### 4. Idempotency
- **24-Hour Deduplication**: UUID v4 idempotency keys
- **Automatic Replay**: Returns cached responses for duplicates

### 5. Circuit Breaker
- **4-State Machine**: CLOSED → OPEN → HALF_OPEN → RECOVERING
- **Automatic Recovery**: Gradual traffic ramp-up over 5 minutes

### 6. Async Operations
- **202 Accepted**: Long-running operations
- **Webhook Delivery**: HMAC-SHA256 signed webhooks with retry
- **SSRF Prevention**: URL validation and private IP blocking

## Architecture

```
External Request
    ↓
┌─────────────────────────────┐
│ 1. Authentication Handler   │
├─────────────────────────────┤
│ 2. Authorization Engine     │
├─────────────────────────────┤
│ 3. Request Validator        │
├─────────────────────────────┤
│ 4. Idempotency Handler      │
├─────────────────────────────┤
│ 5. Rate Limiter             │
├─────────────────────────────┤
│ 6. Request Router           │
├─────────────────────────────┤
│ 7. Backend Executor         │
├─────────────────────────────┤
│ 8. Response Formatter       │
├─────────────────────────────┤
│ 9. Event Publisher          │
└─────────────────────────────┘
    ↓
Response to Client
```

## Installation

```bash
# Install dependencies
pip3 install -r requirements.txt --break-system-packages

# Or using pip
pip install -r requirements.txt
```

## Configuration

Create `.env` file in the gateway directory:

```env
# Server
GATEWAY_HOST=0.0.0.0
GATEWAY_PORT=8000

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0

# PostgreSQL (L01)
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=l01_data_layer
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres

# Environment
ENVIRONMENT=development
DEBUG=false
LOG_LEVEL=INFO
```

## Running the Gateway

### Development Mode

```bash
# Run with auto-reload
python -m src.L09_api_gateway.app

# Or with uvicorn directly
uvicorn src.L09_api_gateway.app:app --reload --port 8000
```

### Production Mode

```bash
# Run with multiple workers
uvicorn src.L09_api_gateway.app:app \
  --host 0.0.0.0 \
  --port 8000 \
  --workers 4
```

## Health Endpoints

### Liveness Probe
```bash
curl http://localhost:8000/health/live
```

### Readiness Probe
```bash
curl http://localhost:8000/health/ready
```

### Startup Probe
```bash
curl http://localhost:8000/health/startup
```

### Detailed Health
```bash
curl http://localhost:8000/health/detailed
```

## API Usage

### Making a Request

```bash
# With API Key
curl -X POST http://localhost:8000/api/test \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello"}'

# With Idempotency Key
curl -X POST http://localhost:8000/api/test \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Idempotency-Key: 550e8400-e29b-41d4-a716-446655440000" \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello"}'
```

### Response Headers

All responses include:
- `X-Request-ID`: Unique request identifier
- `X-Trace-ID`: W3C Trace Context trace ID
- `X-Span-ID`: W3C Trace Context span ID
- `X-RateLimit-Limit`: Rate limit
- `X-RateLimit-Remaining`: Remaining tokens
- `X-RateLimit-Reset`: Reset timestamp

## Error Codes

| Range | Category | Examples |
|-------|----------|----------|
| E9001-E9099 | Routing | E9001: Route not found |
| E9101-E9199 | Authentication | E9101: Invalid API key, E9102: Token expired |
| E9201-E9299 | Authorization | E9205: Cross-tenant access, E9207: Insufficient scopes |
| E9301-E9399 | Validation | E9301: Invalid format, E9304: Body too large |
| E9401-E9499 | Rate Limiting | E9401: Rate limit exceeded, E9402: Daily quota exceeded |
| E9601-E9699 | Async Operations | E9602: Operation not found, E9603: Operation expired |
| E9701-E9799 | Webhooks | E9701: Invalid webhook URL, E9704: SSRF violation |
| E9801-E9899 | Circuit Breaker | E9801: Circuit breaker open, E9803: All replicas down |
| E9901-E9999 | Server Errors | E9901: Internal error, E9904: Bad gateway |

## Rate Limit Tiers

| Tier | RPS Limit | Burst Capacity | Daily Quota |
|------|-----------|----------------|-------------|
| STANDARD | 100 | 1,000 | 100,000 |
| PREMIUM | 1,000 | 10,000 | 1,000,000 |
| ENTERPRISE | 10,000 | 100,000 | 100,000,000 |

## Testing

```bash
# Run tests
pytest src/L09_api_gateway/tests/ -v

# Run with coverage
pytest src/L09_api_gateway/tests/ --cov=src.L09_api_gateway
```

## Dependencies

- **L01 Data Layer**: Consumer registry, configuration, event store
- **L08 Supervision**: ABAC policy evaluation
- **L02 Agent Runtime**: Async operation execution
- **Redis**: Distributed rate limiting, idempotency cache
- **PostgreSQL**: Persistent storage

## Security Features

1. **Multi-Tenant Isolation**: Enforced at every stage
2. **SSRF Prevention**: Webhook URL validation
3. **Input Validation**: Character encoding, null byte detection
4. **Authentication Required**: All routes require auth by default
5. **Audit Logging**: Immutable, time-locked audit trails

## Performance

- **Horizontal Scaling**: Stateless gateway design
- **Connection Pooling**: Reusable HTTP connections
- **Circuit Breaking**: Prevents cascading failures
- **Caching**: Consumer profiles, configuration

## Monitoring

- **Prometheus Metrics**: Request duration, error rates, rate limit violations
- **Structured Logging**: JSON logs with trace context
- **Health Checks**: Kubernetes-compatible probes

## License

Copyright © 2026 Story Portal Platform
