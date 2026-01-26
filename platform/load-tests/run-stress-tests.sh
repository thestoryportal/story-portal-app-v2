#!/bin/bash

# ==============================================================================
# API Stress Tests Runner - Week 9 Day 4
# ==============================================================================
#
# Executes stress tests to find platform breaking points:
# - Spike Test (500 users, 5 minutes) - sudden traffic spike
# - Progressive Stress Test (200→800 users) - find capacity ceiling
#
# Tests push beyond Day 3 peak load (200 users) to identify limits.
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
echo -e "${BLUE}API Stress Tests - Week 9 Day 4${NC}"
echo -e "${BLUE}================================${NC}"
echo ""
echo -e "Target: ${GREEN}${HOST}${NC}"
echo -e "Timestamp: ${GREEN}${TIMESTAMP}${NC}"
echo -e "Reports Directory: ${GREEN}${REPORTS_DIR}${NC}"
echo ""
echo -e "${YELLOW}⚠️  WARNING: These tests may cause temporary service degradation${NC}"
echo ""

# Ensure reports directory exists
mkdir -p "$REPORTS_DIR"

# Verify platform is running
echo -e "${BLUE}[1/4]${NC} Verifying platform availability..."
if ! curl -sf "${HOST}/health/live" > /dev/null; then
    echo -e "${RED}ERROR: Platform not available at ${HOST}${NC}"
    echo "Please start the platform with: docker-compose -f docker-compose.v2.yml up -d"
    exit 1
fi
echo -e "${GREEN}✓ Platform is available${NC}"
echo ""

# Test 1: Spike Test (500 users, 5 minutes)
echo -e "${BLUE}[2/4]${NC} Running Spike Test (500 users, 5 minutes)..."
echo "      Purpose: Simulate sudden traffic spike (2.5x peak)"
echo "      Users: 500 concurrent"
echo "      Spawn Rate: 50 users/sec"
echo "      Duration: 5 minutes"
echo ""

$LOCUST -f locustfile-api.py \
    --host="${HOST}" \
    --users 500 \
    --spawn-rate 50 \
    --run-time 5m \
    --headless \
    --html="${REPORTS_DIR}/api-spike-${TIMESTAMP}.html" \
    --csv="${REPORTS_DIR}/api-spike-${TIMESTAMP}" \
    2>&1 | tee "${REPORTS_DIR}/api-spike-${TIMESTAMP}.log"

echo ""
echo -e "${GREEN}✓ Spike test complete${NC}"
echo ""
sleep 10

# Test 2: Progressive Stress Test - 300 users
echo -e "${BLUE}[3/4]${NC} Running Progressive Stress Test - Phase 1 (300 users, 5 minutes)..."
echo "      Purpose: Test 1.5x peak load"
echo "      Users: 300 concurrent"
echo "      Duration: 5 minutes"
echo ""

$LOCUST -f locustfile-api.py \
    --host="${HOST}" \
    --users 300 \
    --spawn-rate 30 \
    --run-time 5m \
    --headless \
    --html="${REPORTS_DIR}/api-stress-300-${TIMESTAMP}.html" \
    --csv="${REPORTS_DIR}/api-stress-300-${TIMESTAMP}" \
    2>&1 | tee "${REPORTS_DIR}/api-stress-300-${TIMESTAMP}.log"

echo ""
echo -e "${GREEN}✓ Progressive stress test phase 1 complete${NC}"
echo ""
sleep 10

# Test 3: Progressive Stress Test - 400 users
echo -e "${BLUE}[4/4]${NC} Running Progressive Stress Test - Phase 2 (400 users, 5 minutes)..."
echo "      Purpose: Test 2x peak load"
echo "      Users: 400 concurrent"
echo "      Duration: 5 minutes"
echo ""

$LOCUST -f locustfile-api.py \
    --host="${HOST}" \
    --users 400 \
    --spawn-rate 40 \
    --run-time 5m \
    --headless \
    --html="${REPORTS_DIR}/api-stress-400-${TIMESTAMP}.html" \
    --csv="${REPORTS_DIR}/api-stress-400-${TIMESTAMP}" \
    2>&1 | tee "${REPORTS_DIR}/api-stress-400-${TIMESTAMP}.log"

echo ""
echo -e "${GREEN}✓ Progressive stress test phase 2 complete${NC}"
echo ""

# Summary
echo -e "${BLUE}================================${NC}"
echo -e "${BLUE}All Stress Tests Complete${NC}"
echo -e "${BLUE}================================${NC}"
echo ""
echo -e "${GREEN}Test Reports Generated:${NC}"
echo "  1. Spike Test (500 users):    ${REPORTS_DIR}/api-spike-${TIMESTAMP}.html"
echo "  2. Stress Test (300 users):   ${REPORTS_DIR}/api-stress-300-${TIMESTAMP}.html"
echo "  3. Stress Test (400 users):   ${REPORTS_DIR}/api-stress-400-${TIMESTAMP}.html"
echo ""
echo -e "${YELLOW}Next Steps:${NC}"
echo "  1. Review HTML reports for error rates and response times"
echo "  2. Check logs: ${REPORTS_DIR}/api-*-${TIMESTAMP}.log"
echo "  3. Identify breaking point (if any)"
echo "  4. Document capacity limits in stress test report"
echo ""
echo -e "${GREEN}Total Test Duration: ~15 minutes${NC}"
echo ""
