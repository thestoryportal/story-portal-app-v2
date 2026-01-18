#!/bin/bash
# Run Baseline Load Tests
# =======================
# This script executes the complete baseline test suite for the V2 platform

set -e

# Configuration
PLATFORM_ROOT="/Volumes/Extreme SSD/projects/story-portal-app"
LOADTEST_DIR="$PLATFORM_ROOT/platform/load-tests"
RESULTS_DIR="$LOADTEST_DIR/results"
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
REPORT_DIR="$RESULTS_DIR/baseline-$TIMESTAMP"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Create results directory
mkdir -p "$REPORT_DIR"

echo "================================================"
echo "  V2 Platform - Baseline Load Testing Suite"
echo "================================================"
echo ""
echo "Report Directory: $REPORT_DIR"
echo "Timestamp: $TIMESTAMP"
echo ""

# Function to run a single test
run_test() {
    local test_name=$1
    local users=$2
    local spawn_rate=$3
    local duration=$4
    local description=$5

    echo "================================================"
    echo "Running: $test_name"
    echo "Description: $description"
    echo "Parameters: $users users, spawn rate $spawn_rate, duration $duration"
    echo "================================================"
    echo ""

    local test_slug=$(echo "$test_name" | tr '[:upper:]' '[:lower:]' | tr ' ' '-')
    local output_prefix="$REPORT_DIR/$test_slug"

    cd "$LOADTEST_DIR"
    
    if locust -f locustfile.py \
        --host=http://localhost:8009 \
        --users "$users" \
        --spawn-rate "$spawn_rate" \
        --run-time "$duration" \
        --headless \
        --html "$output_prefix.html" \
        --csv "$output_prefix" \
        --only-summary; then
        echo -e "${GREEN}✅ PASSED: $test_name${NC}"
        echo ""
        return 0
    else
        echo -e "${RED}❌ FAILED: $test_name${NC}"
        echo ""
        return 1
    fi
}

# Check platform health before starting
echo "Checking platform health..."
if ! curl -sf http://localhost:8009/health/ready > /dev/null; then
    echo -e "${RED}❌ ERROR: Platform is not ready${NC}"
    echo "Please start platform services:"
    echo "  cd '$PLATFORM_ROOT'"
    echo "  docker-compose -f docker-compose.app.yml up -d"
    exit 1
fi
echo -e "${GREEN}✅ Platform is ready${NC}"
echo ""

# Test execution tracking
tests_passed=0
tests_failed=0
total_tests=4

# Test 1: Light Load Baseline
if run_test \
    "Light Load Baseline" \
    10 \
    2 \
    "5m" \
    "Establish minimum performance baseline"; then
    ((tests_passed++))
else
    ((tests_failed++))
fi

# Test 2: Normal Load Baseline
if run_test \
    "Normal Load Baseline" \
    100 \
    10 \
    "10m" \
    "Validate target production load"; then
    ((tests_passed++))
else
    ((tests_failed++))
fi

# Test 3: Peak Load Baseline
if run_test \
    "Peak Load Baseline" \
    500 \
    50 \
    "15m" \
    "Validate peak hour capacity"; then
    ((tests_passed++))
else
    ((tests_failed++))
fi

# Test 4: Endurance Baseline
if run_test \
    "Endurance Baseline" \
    200 \
    20 \
    "60m" \
    "Validate stability over time"; then
    ((tests_passed++))
else
    ((tests_failed++))
fi

# Summary
echo "================================================"
echo "  BASELINE TEST SUITE - SUMMARY"
echo "================================================"
echo ""
echo "Total Tests: $total_tests"
echo -e "Passed: ${GREEN}$tests_passed${NC}"
echo -e "Failed: ${RED}$tests_failed${NC}"
echo ""
echo "Results Directory: $REPORT_DIR"
echo ""

# Create summary report
cat > "$REPORT_DIR/SUMMARY.md" << SUMMARY_EOF
# Baseline Load Testing Summary

**Date**: $(date)
**Platform Version**: v2.0.0
**Results Directory**: $REPORT_DIR

## Test Results

| Test Name | Status | Users | Duration | Report |
|-----------|--------|-------|----------|--------|
| Light Load Baseline | $([ $tests_passed -ge 1 ] && echo "✅ PASSED" || echo "❌ FAILED") | 10 | 5m | [HTML](light-load-baseline.html) |
| Normal Load Baseline | $([ $tests_passed -ge 2 ] && echo "✅ PASSED" || echo "❌ FAILED") | 100 | 10m | [HTML](normal-load-baseline.html) |
| Peak Load Baseline | $([ $tests_passed -ge 3 ] && echo "✅ PASSED" || echo "❌ FAILED") | 500 | 15m | [HTML](peak-load-baseline.html) |
| Endurance Baseline | $([ $tests_passed -ge 4 ] && echo "✅ PASSED" || echo "❌ FAILED") | 200 | 60m | [HTML](endurance-baseline.html) |

## Overall Result

- **Tests Passed**: $tests_passed / $total_tests
- **Success Rate**: $(echo "scale=1; $tests_passed * 100 / $total_tests" | bc)%

## Next Steps

$(if [ $tests_passed -eq $total_tests ]; then
    echo "✅ All baseline tests passed. Platform is ready for production launch."
    echo ""
    echo "Recommended actions:"
    echo "1. Review individual test reports for performance insights"
    echo "2. Document baseline metrics for future comparison"
    echo "3. Configure production monitoring alerts"
    echo "4. Schedule regular load testing in CI/CD pipeline"
else
    echo "⚠️ Some baseline tests failed. Investigation required."
    echo ""
    echo "Recommended actions:"
    echo "1. Review failed test reports and logs"
    echo "2. Identify performance bottlenecks"
    echo "3. Optimize infrastructure or code"
    echo "4. Re-run baseline tests after fixes"
fi)

## Reference

- **Load Testing Documentation**: platform/load-tests/README.md
- **Monitoring Setup**: platform/monitoring/README.md
- **Production Deployment**: docs/PRODUCTION-DEPLOYMENT-CHECKLIST.md
SUMMARY_EOF

cat "$REPORT_DIR/SUMMARY.md"

# Exit with appropriate code
if [ $tests_failed -eq 0 ]; then
    echo -e "${GREEN}🎉 All baseline tests passed!${NC}"
    exit 0
else
    echo -e "${YELLOW}⚠️  Some tests failed. See summary above.${NC}"
    exit 1
fi
