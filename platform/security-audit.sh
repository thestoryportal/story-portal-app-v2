#!/bin/bash
# Security Audit Script

echo "Story Portal V2 - Security Audit"
echo "=================================="
echo ""

# Check exposed ports
echo "1. Exposed Ports:"
docker ps --format "table {{.Names}}\t{{.Ports}}" | grep agentic

# Check for default passwords
echo ""
echo "2. Default Password Check:"
if grep -q "postgres:postgres" .env 2>/dev/null; then
  echo "  ⚠️  WARNING: Default PostgreSQL password detected"
else
  echo "  ✓ PostgreSQL password changed"
fi

# Check SSL configuration
echo ""
echo "3. SSL Configuration:"
if [ -f ssl/certificate.crt ]; then
  echo "  ✓ SSL certificate exists"
  openssl x509 -in ssl/certificate.crt -noout -dates 2>/dev/null || echo "  ⚠️  Invalid certificate"
else
  echo "  ⚠️  No SSL certificate found"
fi

# Check authentication
echo ""
echo "4. Authentication Status:"
if docker logs l01-data-layer 2>&1 | grep -q "authentication middleware enabled"; then
  echo "  ✓ L01 authentication enabled"
else
  echo "  ⚠️  L01 authentication status unknown"
fi

# Check resource limits
echo ""
echo "5. Resource Limits:"
LIMIT_COUNT=$(docker inspect $(docker ps -q --filter "name=agentic") | grep -c "Memory\":" || echo "0")
echo "  $LIMIT_COUNT containers have memory limits configured"

# Check for open CVEs
echo ""
echo "6. Container Vulnerabilities:"
if command -v trivy &> /dev/null; then
  echo "  Running Trivy scan..."
  trivy image --severity CRITICAL --quiet l09-api-gateway:latest | wc -l | \
    xargs -I {} echo "  {} critical vulnerabilities found in l09-api-gateway"
else
  echo "  ⚠️  Trivy not installed (brew install trivy)"
fi

echo ""
echo "Audit complete."
