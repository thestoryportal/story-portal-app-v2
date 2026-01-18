# Load Testing Suite - V2 Platform

## Overview

This directory contains comprehensive load testing infrastructure for the V2 platform using [Locust](https://locust.io/).

**Purpose**: Validate platform performance, identify bottlenecks, and establish baseline metrics before production launch.

## Quick Start

### 1. Install Dependencies

```bash
cd /Volumes/Extreme\ SSD/projects/story-portal-app/platform
pip install -r requirements-loadtest.txt
```

### 2. Start Platform Services

```bash
docker-compose -f docker-compose.app.yml up -d
docker ps | grep -E "agentic-|platform-"
```

### 3. Run Load Tests

#### Web UI Mode
```bash
cd load-tests
locust -f locustfile.py --host=http://localhost:8009
# Open browser to http://localhost:8089
```

#### Headless Mode
```bash
locust -f locustfile.py --host=http://localhost:8009 --users 100 --spawn-rate 10 --run-time 5m --headless --html report.html
```

## Test Scenarios

1. **TestAPIGateway** - Health checks and gateway routing
2. **TestDataLayer** - CRUD operations
3. **TestTaskExecution** - Task workflows
4. **TestModelGateway** - LLM requests
5. **TestToolExecution** - Tool operations
6. **TestFullUserJourney** - End-to-end workflows

## Performance Thresholds

| Metric | Threshold |
|--------|-----------|
| P95 Response Time | ≤ 500ms |
| Error Rate | ≤ 1% |
| Throughput | ≥ 100 req/s |

## Test Examples

### Smoke Test
```bash
locust -f locustfile.py --host=http://localhost:8009 --users 10 --spawn-rate 2 --run-time 30s --headless
```

### Load Test
```bash
locust -f locustfile.py --host=http://localhost:8009 --users 100 --spawn-rate 10 --run-time 5m --headless --html load-test-report.html
```

### Stress Test
```bash
locust -f locustfile.py --host=http://localhost:8009 --users 500 --spawn-rate 50 --run-time 10m --headless --html stress-test-report.html
```

## Results Interpretation

Results show:
- Total requests and success/failure counts
- Error rate percentage
- P95 response time
- Automatic threshold validation

## References

- **Locust Docs**: https://docs.locust.io/
- **Platform Monitoring**: platform/monitoring/README.md
- **Production Deployment**: docs/PRODUCTION-DEPLOYMENT-CHECKLIST.md

**Last Updated**: 2026-01-18
