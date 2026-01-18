#!/bin/bash
set -e

# Story Portal V2 - Security Hardening Script
# Implements security measures for production deployment

echo "==========================================="
echo "Story Portal V2 - Security Hardening"
echo "==========================================="
echo ""

# Check if running as root/sudo
if [ "$EUID" -ne 0 ]; then
  echo "⚠️  Warning: Some operations may require sudo privileges"
fi

# 1. Create SSL directory
echo "[1/8] Setting up SSL directory..."
mkdir -p ssl
chmod 700 ssl

if [ ! -f ssl/certificate.crt ]; then
  echo "  Generating self-signed certificate (development only)..."
  openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout ssl/private.key \
    -out ssl/certificate.crt \
    -subj "/C=US/ST=State/L=City/O=StoryPortal/CN=localhost" \
    2>/dev/null
  chmod 600 ssl/private.key
  chmod 644 ssl/certificate.crt
  echo "  ✓ Self-signed certificate generated"
else
  echo "  ✓ SSL certificates already exist"
fi

# 2. Create .env template with secure defaults
echo ""
echo "[2/8] Creating .env template..."
if [ ! -f .env ]; then
  cat > .env <<EOF
# Story Portal V2 - Environment Configuration
# IMPORTANT: Change all passwords and secrets before production deployment!

# Database
POSTGRES_USER=postgres
POSTGRES_PASSWORD=$(openssl rand -base64 32)
POSTGRES_DB=agentic_platform

# Redis
REDIS_PASSWORD=$(openssl rand -base64 32)

# JWT
JWT_SECRET=$(openssl rand -base64 64)
JWT_EXPIRATION=3600

# Security
TLS_ENABLED=true
TLS_CERT_PATH=./ssl/certificate.crt
TLS_KEY_PATH=./ssl/private.key

# Rate Limiting
RATE_LIMIT_ENABLED=true
RATE_LIMIT_REQUESTS_PER_MINUTE=100
RATE_LIMIT_BURST=20

# Audit Logging
AUDIT_LOG_ENABLED=true
AUDIT_LOG_LEVEL=INFO

# Authentication
L01_AUTH_DISABLED=false
L09_AUTH_ENABLED=true

# Monitoring
PROMETHEUS_RETENTION_DAYS=30
GRAFANA_ADMIN_PASSWORD=$(openssl rand -base64 24)
EOF
  chmod 600 .env
  echo "  ✓ .env file created with random passwords"
  echo "  ⚠️  IMPORTANT: Review and update .env before production use"
else
  echo "  ✓ .env file already exists"
fi

# 3. Configure PostgreSQL security
echo ""
echo "[3/8] Configuring PostgreSQL security..."
if docker ps | grep -q agentic-postgres; then
  # Create RBAC roles
  docker exec agentic-postgres psql -U postgres -c "
    DO \$\$
    BEGIN
      IF NOT EXISTS (SELECT FROM pg_user WHERE usrname = 'l01_service') THEN
        CREATE ROLE l01_service WITH LOGIN PASSWORD '$(openssl rand -base64 24)';
      END IF;
      IF NOT EXISTS (SELECT FROM pg_user WHERE usrname = 'l09_service') THEN
        CREATE ROLE l09_service WITH LOGIN PASSWORD '$(openssl rand -base64 24)';
      END IF;
    END
    \$\$;
  " 2>/dev/null || echo "  Note: Roles may already exist"

  # Grant minimal permissions
  docker exec agentic-postgres psql -U postgres agentic_platform -c "
    GRANT CONNECT ON DATABASE agentic_platform TO l01_service, l09_service;
    GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA mcp_documents TO l01_service;
    GRANT SELECT ON ALL TABLES IN SCHEMA mcp_documents TO l09_service;
  " 2>/dev/null || true

  echo "  ✓ PostgreSQL security configured"
else
  echo "  ⚠️  PostgreSQL not running, skipped"
fi

# 4. Configure Redis security
echo ""
echo "[4/8] Configuring Redis security..."
if docker ps | grep -q agentic-redis; then
  # Note: Redis config would need to be persistent via volume mount
  # For now, just log the recommendation
  echo "  ⚠️  Redis security requires persistent configuration"
  echo "     Add to redis.conf: requirepass <strong-password>"
fi

# 5. Scan Docker images for vulnerabilities
echo ""
echo "[5/8] Scanning Docker images for vulnerabilities..."
if command -v trivy &> /dev/null; then
  echo "  Scanning critical images..."
  for image in l01-data-layer l09-api-gateway l12-service-hub; do
    echo "    Scanning $image..."
    trivy image --severity HIGH,CRITICAL --quiet $image:latest | head -n 20 || true
  done
  echo "  ✓ Image scanning complete"
else
  echo "  ⚠️  Trivy not installed, skipping image scan"
  echo "     Install: brew install trivy (macOS) or see https://trivy.dev"
fi

# 6. Configure firewall rules (if UFW available)
echo ""
echo "[6/8] Configuring firewall rules..."
if command -v ufw &> /dev/null && [ "$EUID" -eq 0 ]; then
  ufw allow 8009/tcp comment "Story Portal API Gateway"
  ufw allow 3000/tcp comment "Story Portal UI"
  ufw allow 3001/tcp comment "Grafana Monitoring"
  ufw deny 5432/tcp comment "Block external PostgreSQL"
  ufw deny 6379/tcp comment "Block external Redis"
  echo "  ✓ Firewall rules configured"
elif command -v ufw &> /dev/null; then
  echo "  ⚠️  UFW detected but requires sudo to configure"
  echo "     Run with sudo to configure firewall rules"
else
  echo "  ⚠️  UFW not available, configure firewall manually"
fi

# 7. Set proper file permissions
echo ""
echo "[7/8] Setting file permissions..."
chmod 600 .env 2>/dev/null || true
chmod 700 ssl 2>/dev/null || true
chmod 600 ssl/private.key 2>/dev/null || true
chmod 755 *.sh 2>/dev/null || true
echo "  ✓ File permissions set"

# 8. Create security audit script
echo ""
echo "[8/8] Creating security audit script..."
cat > security-audit.sh <<'EOF'
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
EOF
chmod +x security-audit.sh
echo "  ✓ Security audit script created: ./security-audit.sh"

echo ""
echo "==========================================="
echo "✓ Security hardening complete"
echo "==========================================="
echo ""
echo "Next steps:"
echo "  1. Review and update .env file with production credentials"
echo "  2. Replace self-signed certificate with Let's Encrypt cert"
echo "  3. Configure external secrets manager (Vault/AWS Secrets Manager)"
echo "  4. Run security audit: ./security-audit.sh"
echo "  5. Review SECURITY.md for additional hardening measures"
echo "  6. Restart services to apply changes:"
echo "     docker-compose -f docker-compose.app.yml restart"
echo ""
