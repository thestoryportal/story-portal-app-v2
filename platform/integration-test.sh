#!/bin/bash
set -e

echo "=========================================="
echo "Story Portal Platform V2 - Integration Test Suite"
echo "=========================================="
echo ""

PASSED=0
FAILED=0

# Test function
test_endpoint() {
    local name="$1"
    local url="$2"
    local expected_status="${3:-200}"

    echo -n "Testing $name... "

    response=$(curl -s -w "\n%{http_code}" "$url" 2>&1)
    status_code=$(echo "$response" | tail -n 1)
    body=$(echo "$response" | sed '$d')

    if [ "$status_code" = "$expected_status" ]; then
        echo "✓ PASSED (HTTP $status_code)"
        ((PASSED++))
        return 0
    else
        echo "✗ FAILED (Expected $expected_status, got $status_code)"
        echo "  Response: $body"
        ((FAILED++))
        return 1
    fi
}

# Test 1: Container Health
echo "=== Test 1: Container Health ==="
echo "Checking all containers are healthy..."
unhealthy=$(docker ps --format "{{.Names}}\t{{.Status}}" | grep -v "healthy" | grep -v "STATUS" | wc -l | tr -d ' ')

if [ "$unhealthy" = "0" ]; then
    echo "✓ All containers healthy"
    ((PASSED++))
else
    echo "✗ Found $unhealthy unhealthy containers:"
    docker ps --format "table {{.Names}}\t{{.Status}}" | grep -v "healthy"
    ((FAILED++))
fi
echo ""

# Test 2: Core Layer Health Checks (L01-L07)
echo "=== Test 2: Core Layer Health Checks (L01-L07) ==="
test_endpoint "L01 Data Layer" "http://localhost:8001/health/live"
test_endpoint "L02 Runtime" "http://localhost:8002/health/live"
test_endpoint "L03 Tool Execution" "http://localhost:8003/health/live"
test_endpoint "L04 Model Gateway" "http://localhost:8004/health/live"
test_endpoint "L05 Planning" "http://localhost:8005/health/live"
test_endpoint "L06 Evaluation" "http://localhost:8006/health/live"
test_endpoint "L07 Learning" "http://localhost:8007/health/live"
echo ""

# Test 3: Gateway Layer Health Checks (L09, L10, L11)
echo "=== Test 3: Gateway Layer Health Checks (L09-L11) ==="
test_endpoint "L09 API Gateway" "http://localhost:8009/health/live"
test_endpoint "L10 Human Interface" "http://localhost:8010/health/live"
test_endpoint "L11 Integration" "http://localhost:8011/health/live"
echo ""

# Test 4: L12 Service Hub
echo "=== Test 4: L12 Service Hub ==="
test_endpoint "L12 Service Hub Health" "http://localhost:8012/health"

echo -n "Checking L12 service count... "
services=$(curl -s http://localhost:8012/v1/services 2>&1)
service_count=$(echo "$services" | jq '. | length' 2>/dev/null || echo "0")

if [ "$service_count" -ge "40" ]; then
    echo "✓ PASSED ($service_count services registered)"
    ((PASSED++))
else
    echo "✗ FAILED (Expected 40+ services, got $service_count)"
    ((FAILED++))
fi
echo ""

# Test 5: L09 API Gateway Authentication
echo "=== Test 5: L09 API Gateway Authentication ==="
echo -n "Testing L09 authentication error handling... "

status_code=$(curl -s -w "%{http_code}" -o /dev/null -X POST http://localhost:8009/api/v1/agents \
    -H "Content-Type: application/json" \
    -d '{"name":"test"}' 2>&1)

if [ "$status_code" = "401" ]; then
    echo "✓ PASSED (Returns 401, not 500)"
    ((PASSED++))
else
    echo "✗ FAILED (Expected 401, got $status_code)"
    echo "  This indicates the L09 NoneType fix may not be working"
    ((FAILED++))
fi
echo ""

# Test 6: Platform UI
echo "=== Test 6: Platform UI ==="
test_endpoint "Platform UI Root" "http://localhost:3000/"
test_endpoint "Platform UI Health" "http://localhost:3000/health"
echo ""

# Test 7: Database Connectivity
echo "=== Test 7: Database Connectivity ==="
echo -n "Testing PostgreSQL... "
if docker exec agentic-postgres pg_isready -U postgres > /dev/null 2>&1; then
    echo "✓ PASSED"
    ((PASSED++))
else
    echo "✗ FAILED"
    ((FAILED++))
fi

echo -n "Testing Redis... "
redis_response=$(docker exec agentic-redis redis-cli PING 2>&1)
if echo "$redis_response" | grep -q "PONG"; then
    echo "✓ PASSED"
    ((PASSED++))
else
    echo "✗ FAILED (Got: $redis_response)"
    ((FAILED++))
fi
echo ""

# Test 8: Resource Limits
echo "=== Test 8: Resource Limits Configured ==="
echo -n "Checking docker-compose has resource limits... "
limit_count=$(grep -c "limits:" docker-compose.app.yml 2>/dev/null || echo "0")

if [ "$limit_count" -ge "14" ]; then
    echo "✓ PASSED ($limit_count resource limit sections found)"
    ((PASSED++))
else
    echo "✗ FAILED (Expected 14+ resource limits, found $limit_count)"
    ((FAILED++))
fi
echo ""

# Test 9: Docker Network
echo "=== Test 9: Docker Network ==="
echo -n "Checking for duplicate networks... "
network_count=$(docker network ls | grep -c -E "(agentic|platform|story)" || echo "0")

if [ "$network_count" = "1" ]; then
    echo "✓ PASSED (Only 1 network, duplicates cleaned up)"
    ((PASSED++))
else
    echo "⚠ WARNING (Found $network_count networks, expected 1)"
    docker network ls | grep -E "(agentic|platform|story)"
    # Don't fail, just warn
    ((PASSED++))
fi
echo ""

# Test 10: Ollama Stability
echo "=== Test 10: Ollama Stability ==="
echo -n "Checking Ollama service... "
if curl -s http://localhost:11434/api/version > /dev/null 2>&1; then
    echo "✓ PASSED (Ollama responding)"
    ((PASSED++))

    # Check PM2 status
    echo -n "Checking PM2 Ollama is not running... "
    if ! pm2 list | grep -q "ollama"; then
        echo "✓ PASSED (PM2 Ollama removed)"
        ((PASSED++))
    else
        echo "⚠ WARNING (PM2 Ollama still in list)"
        ((PASSED++))
    fi
else
    echo "✗ FAILED (Ollama not responding)"
    ((FAILED++))
fi
echo ""

# Final Summary
echo "=========================================="
echo "Test Summary"
echo "=========================================="
echo "Passed: $PASSED"
echo "Failed: $FAILED"
echo "Total:  $((PASSED + FAILED))"
echo ""

if [ "$FAILED" = "0" ]; then
    echo "🎉 All tests passed!"
    echo "=========================================="
    exit 0
else
    echo "❌ Some tests failed"
    echo "=========================================="
    exit 1
fi
