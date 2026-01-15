#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLATFORM_DIR="$(dirname "$(dirname "$SCRIPT_DIR")")"

cd "$PLATFORM_DIR"

echo "=========================================="
echo "L01-L06 End-to-End Test Suite"
echo "=========================================="
echo "Started: $(date)"
echo ""

# Check infrastructure
echo "Checking infrastructure..."
docker ps | grep -q agentic-postgres && echo "  ✓ PostgreSQL" || echo "  ✗ PostgreSQL NOT RUNNING"
docker ps | grep -q agentic-redis && echo "  ✓ Redis" || echo "  ✗ Redis NOT RUNNING"
curl -s localhost:11434/api/tags > /dev/null && echo "  ✓ Ollama" || echo "  ✗ Ollama NOT RUNNING"
echo ""

# Run tests by category
echo "Running tests..."
echo ""

echo "--- Layer Initialization Tests ---"
python3 -m pytest tests/e2e/test_layer_initialization.py -v --timeout=30 2>&1 | tee -a tests/e2e/RESULTS.md

echo ""
echo "--- L02 Runtime Tests ---"
python3 -m pytest tests/e2e/test_l02_runtime.py -v --timeout=60 2>&1 | tee -a tests/e2e/RESULTS.md

echo ""
echo "--- L03 Tool Tests ---"
python3 -m pytest tests/e2e/test_l03_tools.py -v --timeout=60 2>&1 | tee -a tests/e2e/RESULTS.md

echo ""
echo "--- L04 Gateway Tests ---"
python3 -m pytest tests/e2e/test_l04_gateway.py -v --timeout=60 2>&1 | tee -a tests/e2e/RESULTS.md

echo ""
echo "--- L05 Planning Tests ---"
python3 -m pytest tests/e2e/test_l05_planning.py -v --timeout=60 2>&1 | tee -a tests/e2e/RESULTS.md

echo ""
echo "--- L06 Evaluation Tests ---"
python3 -m pytest tests/e2e/test_l06_evaluation.py -v --timeout=60 2>&1 | tee -a tests/e2e/RESULTS.md

echo ""
echo "--- Cross-Layer Integration Tests ---"
python3 -m pytest tests/e2e/test_cross_layer_integration.py -v --timeout=120 2>&1 | tee -a tests/e2e/RESULTS.md

echo ""
echo "--- Full Pipeline Tests ---"
python3 -m pytest tests/e2e/test_full_pipeline.py -v --timeout=180 2>&1 | tee -a tests/e2e/RESULTS.md

echo ""
echo "--- Error Handling Tests ---"
python3 -m pytest tests/e2e/test_error_handling.py -v --timeout=60 2>&1 | tee -a tests/e2e/RESULTS.md

echo ""
echo "--- Performance Tests ---"
python3 -m pytest tests/e2e/test_performance.py -v -m "not slow" --timeout=120 2>&1 | tee -a tests/e2e/RESULTS.md

echo ""
echo "=========================================="
echo "Test Suite Complete: $(date)"
echo "=========================================="

# Summary
python3 -m pytest tests/e2e/ --collect-only -q 2>/dev/null | tail -1
