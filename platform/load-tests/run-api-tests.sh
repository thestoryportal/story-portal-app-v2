#!/bin/bash

# ==============================================================================
# API Load Tests Runner - Week 9 Day 3
# ==============================================================================
#
# Executes load tests against operational API v1 endpoints:
# - /api/v1/agents (CRUD)
# - /api/v1/goals (CRUD)
# - /api/v1/tasks (CRUD)
#
# Tests validate API Gateway fix from Day 2 under realistic load conditions.
#
# ==============================================================================

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
HOST="http://localhost:8009"
REPORTS_DIR="./reports"
TIMESTAMP=$(date +%Y%m%d%H%M%S)
LOCUST="../.venv-loadtest/bin/locust"

echo -e "${BLUE}================================${NC}"
echo -e "${BLUE}API Load Tests - Week 9 Day 3${NC}"
echo -e "${BLUE}================================${NC}"
echo ""
echo -e "Target: ${GREEN}${HOST}${NC}"
echo -e "Timestamp: ${GREEN}${TIMESTAMP}${NC}"
echo -e "Reports Directory: ${GREEN}${REPORTS_DIR}${NC}"
echo ""

# Ensure reports directory exists
mkdir -p "$REPORTS_DIR"

# Verify platform is running
echo -e "${BLUE}[1/5]${NC} Verifying platform availability..."
if ! curl -sf "${HOST}/health/live" > /dev/null; then
    echo -e "${RED}ERROR: Platform not available at ${HOST}${NC}"
    echo "Please start the platform with: docker-compose -f docker-compose.v2.yml up -d"
    exit 1
fi
echo -e "${GREEN}✓ Platform is available${NC}"
echo ""

# Test 1: API Smoke Test (quick validation)
echo -e "${BLUE}[2/5]${NC} Running API Smoke Test (10 users, 1 minute)..."
echo "      Purpose: Quick validation of all API endpoints"
echo "      Users: 10 concurrent"
echo "      Duration: 1 minute"
echo ""

$LOCUST -f locustfile-api.py \
    --host="${HOST}" \
    --users 10 \
    --spawn-rate 5 \
    --run-time 1m \
    --headless \
    --html="${REPORTS_DIR}/api-smoke-${TIMESTAMP}.html" \
    --csv="${REPORTS_DIR}/api-smoke-${TIMESTAMP}" \
    2>&1 | tee "${REPORTS_DIR}/api-smoke-${TIMESTAMP}.log"

echo ""
echo -e "${GREEN}✓ Smoke test complete${NC}"
echo ""
sleep 5

# Test 2: API Normal Load (typical usage)
echo -e "${BLUE}[3/5]${NC} Running API Normal Load Test (50 users, 5 minutes)..."
echo "      Purpose: Simulate typical production load"
echo "      Users: 50 concurrent"
echo "      Duration: 5 minutes"
echo ""

$LOCUST -f locustfile-api.py \
    --host="${HOST}" \
    --users 50 \
    --spawn-rate 10 \
    --run-time 5m \
    --headless \
    --html="${REPORTS_DIR}/api-normal-${TIMESTAMP}.html" \
    --csv="${REPORTS_DIR}/api-normal-${TIMESTAMP}" \
    2>&1 | tee "${REPORTS_DIR}/api-normal-${TIMESTAMP}.log"

echo ""
echo -e "${GREEN}✓ Normal load test complete${NC}"
echo ""
sleep 5

# Test 3: API Peak Load (high traffic)
echo -e "${BLUE}[4/5]${NC} Running API Peak Load Test (200 users, 10 minutes)..."
echo "      Purpose: Test performance under peak traffic"
echo "      Users: 200 concurrent"
echo "      Duration: 10 minutes"
echo ""

$LOCUST -f locustfile-api.py \
    --host="${HOST}" \
    --users 200 \
    --spawn-rate 20 \
    --run-time 10m \
    --headless \
    --html="${REPORTS_DIR}/api-peak-${TIMESTAMP}.html" \
    --csv="${REPORTS_DIR}/api-peak-${TIMESTAMP}" \
    2>&1 | tee "${REPORTS_DIR}/api-peak-${TIMESTAMP}.log"

echo ""
echo -e "${GREEN}✓ Peak load test complete${NC}"
echo ""
sleep 5

# Test 4: API Endurance Test (sustained load)
echo -e "${BLUE}[5/5]${NC} Running API Endurance Test (100 users, 30 minutes)..."
echo "      Purpose: Test stability over extended period"
echo "      Users: 100 concurrent"
echo "      Duration: 30 minutes"
echo ""

$LOCUST -f locustfile-api.py \
    --host="${HOST}" \
    --users 100 \
    --spawn-rate 10 \
    --run-time 30m \
    --headless \
    --html="${REPORTS_DIR}/api-endurance-${TIMESTAMP}.html" \
    --csv="${REPORTS_DIR}/api-endurance-${TIMESTAMP}" \
    2>&1 | tee "${REPORTS_DIR}/api-endurance-${TIMESTAMP}.log"

echo ""
echo -e "${GREEN}✓ Endurance test complete${NC}"
echo ""

# Summary
echo -e "${BLUE}================================${NC}"
echo -e "${BLUE}All API Load Tests Complete${NC}"
echo -e "${BLUE}================================${NC}"
echo ""
echo -e "${GREEN}Test Reports Generated:${NC}"
echo "  1. Smoke Test:     ${REPORTS_DIR}/api-smoke-${TIMESTAMP}.html"
echo "  2. Normal Load:    ${REPORTS_DIR}/api-normal-${TIMESTAMP}.html"
echo "  3. Peak Load:      ${REPORTS_DIR}/api-peak-${TIMESTAMP}.html"
echo "  4. Endurance:      ${REPORTS_DIR}/api-endurance-${TIMESTAMP}.html"
echo ""
echo -e "${YELLOW}Next Steps:${NC}"
echo "  1. Review HTML reports in your browser"
echo "  2. Check logs for any errors: ${REPORTS_DIR}/api-*-${TIMESTAMP}.log"
echo "  3. Document baselines in API-BASELINE-RESULTS.md"
echo ""
echo -e "${GREEN}Total Test Duration: ~47 minutes${NC}"
echo ""
