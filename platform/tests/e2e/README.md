# L01-L06 End-to-End Test Suite

Comprehensive E2E test suite for the agentic platform layers L02-L06.

## Overview

This test suite validates:
- Individual layer initialization and functionality
- Cross-layer integration
- Full pipeline flows
- Error handling
- Performance characteristics

## Requirements

### Infrastructure
All services must be running (DO NOT start them):
- PostgreSQL (localhost:5432)
- Redis (localhost:6379)
- Ollama (localhost:11434)
- MCP context-orchestrator (PM2)
- MCP document-consolidator (PM2)

### Python Dependencies
```bash
pip install pytest pytest-asyncio pytest-timeout redis psycopg2-binary httpx --break-system-packages
```

## Test Structure

```
tests/e2e/
├── __init__.py
├── conftest.py                      # Pytest configuration and fixtures
├── pytest.ini                       # Pytest settings
├── run_tests.sh                     # Test runner script
├── README.md                        # This file
├── test_layer_initialization.py     # Layer initialization tests
├── test_l02_runtime.py             # L02 Agent Runtime tests
├── test_l03_tools.py               # L03 Tool Execution tests
├── test_l04_gateway.py             # L04 Model Gateway tests
├── test_l05_planning.py            # L05 Planning tests
├── test_l06_evaluation.py          # L06 Evaluation tests
├── test_cross_layer_integration.py # Cross-layer integration tests
├── test_full_pipeline.py           # Full pipeline tests
├── test_error_handling.py          # Error handling tests
├── test_performance.py             # Performance tests
└── utils/
    ├── __init__.py
    ├── fixtures.py                 # Reusable test fixtures
    ├── helpers.py                  # Test helper functions
    └── assertions.py               # Custom assertions
```

## Running Tests

### All Tests
```bash
cd /Volumes/Extreme\ SSD/projects/story-portal-app/platform
chmod +x tests/e2e/run_tests.sh
./tests/e2e/run_tests.sh
```

### Individual Test Files
```bash
pytest tests/e2e/test_layer_initialization.py -v
pytest tests/e2e/test_l05_planning.py -v
```

### By Marker
```bash
# Integration tests only
pytest tests/e2e/ -m integration -v

# Exclude slow tests
pytest tests/e2e/ -m "not slow" -v

# E2E tests only
pytest tests/e2e/ -m e2e -v
```

### Specific Tests
```bash
pytest tests/e2e/test_l04_gateway.py::TestL04ModelGateway::test_simple_completion -v
```

## Test Markers

- `@pytest.mark.slow` - Tests that take longer than 30s
- `@pytest.mark.integration` - Tests requiring external services (Ollama, MCP)
- `@pytest.mark.e2e` - Full end-to-end pipeline tests

## Layer Coverage

### L02 Agent Runtime
- Agent executor initialization
- Session bridge MCP integration
- Document bridge MCP integration
- Context management

### L03 Tool Execution
- Tool registry operations
- Tool executor functionality
- Tool listing and retrieval

### L04 Model Gateway
- Model registry operations
- LLM router functionality
- Ollama provider integration
- Semantic cache operations
- Rate limiting

### L05 Planning
- Planning service initialization
- Goal decomposition
- Dependency resolution
- Topological sorting
- Plan validation

### L06 Evaluation
- Evaluation service initialization
- CloudEvent processing
- Quality scoring (5 dimensions)
- Metrics ingestion and querying
- Anomaly detection

### Cross-Layer Integration
- L04 ↔ L05: Planning uses Model Gateway for LLM-based decomposition
- L02 ↔ L03: Agent Runtime uses Tool Execution
- L05 ↔ L06: Evaluation evaluates plans
- L02 ↔ MCP: Bridges communicate with MCP services

### Full Pipeline
- Goal → Plan → Execute → Evaluate
- Multi-task plan execution
- Concurrent layer operations

## Troubleshooting

### Tests hang
- Check pytest timeout settings in pytest.ini
- Verify infrastructure is running: `docker ps && pm2 status`

### Import errors
- Verify PYTHONPATH includes platform root
- Check conftest.py path configuration

### Connection errors
- Verify services are running on correct ports
- Check docker-compose.yml for service configuration

### Ollama errors
- Ensure Ollama is running: `curl localhost:11434/api/tags`
- Verify models are available: `ollama list`

## Progress Log

### 2026-01-15: Initial Implementation Complete
- Phase 1 complete: Test infrastructure (conftest.py, pytest.ini, run_tests.sh, README.md) - 01:45
- Phase 2 complete: Layer initialization tests (11 tests) - 01:45
- Phase 3 complete: Individual layer tests (43 tests across 5 files) - 01:46
- Phase 4 complete: Cross-layer integration tests (4 tests) - 01:47
- Phase 5 complete: Full pipeline tests (3 tests) - 01:47
- Phase 6 complete: Error handling tests (5 tests) - 01:47
- Phase 7 complete: Performance tests (5 tests) - 01:47
- Phase 8 complete: Utilities (fixtures, helpers, assertions) - 01:48
- Dependencies installed: pytest, pytest-asyncio, pytest-timeout, redis, psycopg2-binary, httpx - 01:48
- Test suite executed: 71 tests total, API mismatches identified - 01:52
- **Total: 19 files, 1,311 lines of test code**

### Test Results Summary
- Layer initialization: 11/11 passing (100%)
- Individual layers: Mixed results - API mismatches detected
- Integration tests: Running
- Known issues documented in IMPLEMENTATION_SUMMARY.md
