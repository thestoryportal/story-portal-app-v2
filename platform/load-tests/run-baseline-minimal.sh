#!/bin/bash
#
# Baseline Load Testing Script - Minimal Edition
# ===============================================
#
# This script runs baseline load tests on health endpoints only.
# The full API endpoints are not yet implemented, so this provides
# a baseline for gateway health and routing performance.
#
# Test Scenarios:
#   1. Light Load    - 10 users,  5 minutes  - Validates basic functionality
#   2. Normal Load   - 100 users, 10 minutes - Simulates typical usage
#   3. Peak Load     - 500 users, 15 minutes - Tests maximum capacity
#   4. Endurance     - 200 users, 60 minutes - Tests stability over time
#
# Total Duration: ~90 minutes

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLATFORM_DIR="$(dirname "$SCRIPT_DIR")"
REPORTS_DIR="$SCRIPT_DIR/reports"
TIMESTAMP=$(date +%Y%m%d-%H%M%S)

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "================================================================================"
echo "                    Baseline Load Testing - Minimal Edition                    "
echo "================================================================================"
echo ""
echo "Test Suite: Health Endpoint Performance"
echo "Target: http://localhost:8009"
echo "Timestamp: $TIMESTAMP"
echo ""
echo "Note: This is a minimal baseline test as API endpoints are not yet implemented."
echo "      Testing gateway health and routing performance only."
echo ""
echo "================================================================================"

# Create reports directory
mkdir -p "$REPORTS_DIR"

# Activate virtual environment
echo "Activating load testing environment..."
source "$PLATFORM_DIR/.venv-loadtest/bin/activate"

# Verify platform is running
echo ""
echo "Checking platform health..."
if curl -sf http://localhost:8009/health/live > /dev/null; then
    echo -e "${GREEN}✓${NC} Platform is healthy"
else
    echo -e "${RED}✗${NC} Platform is not responding"
    echo "Please ensure platform is running: cd platform && docker-compose up -d"
    exit 1
fi

echo ""
echo "================================================================================"
echo " Test 1/4: Light Load (10 users, 5 minutes)"
echo "================================================================================"
echo "Purpose: Validate basic functionality and establish minimum baseline"
echo "Expected: P95 < 500ms, Error rate < 1%"
echo ""

locust -f "$SCRIPT_DIR/locustfile-minimal.py" \
    --host=http://localhost:8009 \
    --users 10 \
    --spawn-rate 2 \
    --run-time 5m \
    --headless \
    --html "$REPORTS_DIR/baseline-light-$TIMESTAMP.html" \
    --csv "$REPORTS_DIR/baseline-light-$TIMESTAMP"

echo ""
echo -e "${GREEN}Test 1 Complete${NC}"
echo "Report saved to: $REPORTS_DIR/baseline-light-$TIMESTAMP.html"
echo ""
read -p "Press Enter to continue to Test 2 (Normal Load)..."

echo ""
echo "================================================================================"
echo " Test 2/4: Normal Load (100 users, 10 minutes)"
echo "================================================================================"
echo "Purpose: Simulate typical production usage patterns"
echo "Expected: P95 < 500ms, Error rate < 1%"
echo ""

locust -f "$SCRIPT_DIR/locustfile-minimal.py" \
    --host=http://localhost:8009 \
    --users 100 \
    --spawn-rate 10 \
    --run-time 10m \
    --headless \
    --html "$REPORTS_DIR/baseline-normal-$TIMESTAMP.html" \
    --csv "$REPORTS_DIR/baseline-normal-$TIMESTAMP"

echo ""
echo -e "${GREEN}Test 2 Complete${NC}"
echo "Report saved to: $REPORTS_DIR/baseline-normal-$TIMESTAMP.html"
echo ""
read -p "Press Enter to continue to Test 3 (Peak Load)..."

echo ""
echo "================================================================================"
echo " Test 3/4: Peak Load (500 users, 15 minutes)"
echo "================================================================================"
echo "Purpose: Test maximum capacity and identify breaking points"
echo "Expected: P95 < 500ms, Error rate < 1%"
echo ""

locust -f "$SCRIPT_DIR/locustfile-minimal.py" \
    --host=http://localhost:8009 \
    --users 500 \
    --spawn-rate 50 \
    --run-time 15m \
    --headless \
    --html "$REPORTS_DIR/baseline-peak-$TIMESTAMP.html" \
    --csv "$REPORTS_DIR/baseline-peak-$TIMESTAMP"

echo ""
echo -e "${GREEN}Test 3 Complete${NC}"
echo "Report saved to: $REPORTS_DIR/baseline-peak-$TIMESTAMP.html"
echo ""
read -p "Press Enter to continue to Test 4 (Endurance)..."

echo ""
echo "================================================================================"
echo " Test 4/4: Endurance Test (200 users, 60 minutes)"
echo "================================================================================"
echo "Purpose: Test system stability and identify memory leaks over time"
echo "Expected: P95 < 500ms, Error rate < 1%, No degradation over time"
echo ""

locust -f "$SCRIPT_DIR/locustfile-minimal.py" \
    --host=http://localhost:8009 \
    --users 200 \
    --spawn-rate 20 \
    --run-time 60m \
    --headless \
    --html "$REPORTS_DIR/baseline-endurance-$TIMESTAMP.html" \
    --csv "$REPORTS_DIR/baseline-endurance-$TIMESTAMP"

echo ""
echo -e "${GREEN}Test 4 Complete${NC}"
echo "Report saved to: $REPORTS_DIR/baseline-endurance-$TIMESTAMP.html"

echo ""
echo "================================================================================"
echo "                         All Baseline Tests Complete                           "
echo "================================================================================"
echo ""
echo "Reports saved in: $REPORTS_DIR"
echo ""
echo "Test Summary:"
echo "  1. Light Load (10 users, 5min):       baseline-light-$TIMESTAMP.html"
echo "  2. Normal Load (100 users, 10min):    baseline-normal-$TIMESTAMP.html"
echo "  3. Peak Load (500 users, 15min):      baseline-peak-$TIMESTAMP.html"
echo "  4. Endurance (200 users, 60min):      baseline-endurance-$TIMESTAMP.html"
echo ""
echo "Next Steps:"
echo "  1. Review HTML reports for detailed metrics"
echo "  2. Analyze CSV files for performance trends"
echo "  3. Document baseline metrics in BASELINE-RESULTS.md"
echo "  4. Configure Prometheus alerts based on P95 + 20% threshold"
echo ""
echo "================================================================================"
