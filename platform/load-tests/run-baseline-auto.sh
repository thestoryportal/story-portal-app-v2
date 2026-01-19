#!/bin/bash
#
# Automated Baseline Load Testing Script - Minimal Edition
# =========================================================
#
# This script runs baseline load tests automatically without user prompts.
# Suitable for background execution and CI/CD pipelines.
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

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

log "================================================================================"
log "              Baseline Load Testing - Minimal Edition (Automated)              "
log "================================================================================"
log ""
log "Test Suite: Health Endpoint Performance"
log "Target: http://localhost:8009"
log "Timestamp: $TIMESTAMP"
log "Mode: Automated (non-interactive)"
log ""
log "================================================================================"

# Create reports directory
mkdir -p "$REPORTS_DIR"

# Activate virtual environment
log "Activating load testing environment..."
source "$PLATFORM_DIR/.venv-loadtest/bin/activate"

# Verify platform is running
log ""
log "Checking platform health..."
if curl -sf http://localhost:8009/health/live > /dev/null; then
    log "✓ Platform is healthy"
else
    log "✗ Platform is not responding"
    log "Please ensure platform is running: cd platform && docker-compose up -d"
    exit 1
fi

# Test 1: Light Load
log ""
log "================================================================================"
log " Test 1/4: Light Load (10 users, 5 minutes)"
log "================================================================================"
log "Start time: $(date '+%H:%M:%S')"
log "Expected duration: 5 minutes"
log ""

locust -f "$SCRIPT_DIR/locustfile-minimal.py" \
    --host=http://localhost:8009 \
    --users 10 \
    --spawn-rate 2 \
    --run-time 5m \
    --headless \
    --html "$REPORTS_DIR/baseline-light-$TIMESTAMP.html" \
    --csv "$REPORTS_DIR/baseline-light-$TIMESTAMP"

log ""
log "✓ Test 1 Complete"
log "Report: $REPORTS_DIR/baseline-light-$TIMESTAMP.html"

# Test 2: Normal Load
log ""
log "================================================================================"
log " Test 2/4: Normal Load (100 users, 10 minutes)"
log "================================================================================"
log "Start time: $(date '+%H:%M:%S')"
log "Expected duration: 10 minutes"
log ""

locust -f "$SCRIPT_DIR/locustfile-minimal.py" \
    --host=http://localhost:8009 \
    --users 100 \
    --spawn-rate 10 \
    --run-time 10m \
    --headless \
    --html "$REPORTS_DIR/baseline-normal-$TIMESTAMP.html" \
    --csv "$REPORTS_DIR/baseline-normal-$TIMESTAMP"

log ""
log "✓ Test 2 Complete"
log "Report: $REPORTS_DIR/baseline-normal-$TIMESTAMP.html"

# Test 3: Peak Load
log ""
log "================================================================================"
log " Test 3/4: Peak Load (500 users, 15 minutes)"
log "================================================================================"
log "Start time: $(date '+%H:%M:%S')"
log "Expected duration: 15 minutes"
log ""

locust -f "$SCRIPT_DIR/locustfile-minimal.py" \
    --host=http://localhost:8009 \
    --users 500 \
    --spawn-rate 50 \
    --run-time 15m \
    --headless \
    --html "$REPORTS_DIR/baseline-peak-$TIMESTAMP.html" \
    --csv "$REPORTS_DIR/baseline-peak-$TIMESTAMP"

log ""
log "✓ Test 3 Complete"
log "Report: $REPORTS_DIR/baseline-peak-$TIMESTAMP.html"

# Test 4: Endurance
log ""
log "================================================================================"
log " Test 4/4: Endurance Test (200 users, 60 minutes)"
log "================================================================================"
log "Start time: $(date '+%H:%M:%S')"
log "Expected duration: 60 minutes"
log ""

locust -f "$SCRIPT_DIR/locustfile-minimal.py" \
    --host=http://localhost:8009 \
    --users 200 \
    --spawn-rate 20 \
    --run-time 60m \
    --headless \
    --html "$REPORTS_DIR/baseline-endurance-$TIMESTAMP.html" \
    --csv "$REPORTS_DIR/baseline-endurance-$TIMESTAMP"

log ""
log "✓ Test 4 Complete"
log "Report: $REPORTS_DIR/baseline-endurance-$TIMESTAMP.html"

# Summary
log ""
log "================================================================================"
log "                    All Baseline Tests Complete                                "
log "================================================================================"
log ""
log "Completion time: $(date '+%Y-%m-%d %H:%M:%S')"
log "Total duration: ~90 minutes"
log ""
log "Reports saved in: $REPORTS_DIR"
log ""
log "Test Summary:"
log "  1. Light Load (10 users, 5min):       baseline-light-$TIMESTAMP.html"
log "  2. Normal Load (100 users, 10min):    baseline-normal-$TIMESTAMP.html"
log "  3. Peak Load (500 users, 15min):      baseline-peak-$TIMESTAMP.html"
log "  4. Endurance (200 users, 60min):      baseline-endurance-$TIMESTAMP.html"
log ""
log "CSV files also available for detailed analysis"
log ""
log "Next Steps:"
log "  1. Review HTML reports: open $REPORTS_DIR/*.html"
log "  2. Analyze CSV files for performance trends"
log "  3. Run: ./analyze-baseline-results.sh"
log "  4. Document findings in BASELINE-RESULTS.md"
log ""
log "================================================================================"

# Create summary file
cat > "$REPORTS_DIR/test-summary-$TIMESTAMP.txt" << EOF
Baseline Load Test Summary
==========================

Test Run: $TIMESTAMP
Duration: ~90 minutes
Platform: http://localhost:8009

Test Results:
-------------
1. Light Load (10 users, 5min):       baseline-light-$TIMESTAMP.html
2. Normal Load (100 users, 10min):    baseline-normal-$TIMESTAMP.html
3. Peak Load (500 users, 15min):      baseline-peak-$TIMESTAMP.html
4. Endurance (200 users, 60min):      baseline-endurance-$TIMESTAMP.html

Status: ✓ All tests completed successfully

Next: Review reports and document baseline metrics
EOF

log "Summary file created: $REPORTS_DIR/test-summary-$TIMESTAMP.txt"
log "================================================================================"
