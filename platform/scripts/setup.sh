#!/bin/bash

# Story Portal Platform V2 - Setup Script
# Automated setup and initialization

set -e  # Exit on error

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
COMPOSE_FILE="$PROJECT_ROOT/platform/docker-compose.app.yml"
ENV_FILE="$PROJECT_ROOT/.env"
ENV_EXAMPLE="$PROJECT_ROOT/.env.example"

# Banner
echo ""
echo -e "${CYAN}╔═══════════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║                                                           ║${NC}"
echo -e "${CYAN}║         Story Portal Platform V2 - Setup Script           ║${NC}"
echo -e "${CYAN}║                                                           ║${NC}"
echo -e "${CYAN}╚═══════════════════════════════════════════════════════════╝${NC}"
echo ""

# Check if running as root
if [ "$EUID" -eq 0 ]; then
    echo -e "${YELLOW}⚠ WARNING: Running as root is not recommended${NC}"
    read -p "Continue anyway? (yes/no): " confirm
    if [ "$confirm" != "yes" ]; then
        echo "Setup cancelled."
        exit 0
    fi
fi

# Step 1: Check Prerequisites
echo -e "${BLUE}[Step 1/8] Checking Prerequisites...${NC}"
echo ""

# Check Docker
if command -v docker &> /dev/null; then
    DOCKER_VERSION=$(docker --version | cut -d' ' -f3 | cut -d',' -f1)
    echo -e "${GREEN}✓${NC} Docker found: $DOCKER_VERSION"
else
    echo -e "${RED}✗${NC} Docker not found"
    echo ""
    echo "Please install Docker:"
    echo "  macOS: https://docs.docker.com/desktop/mac/install/"
    echo "  Linux: https://docs.docker.com/engine/install/"
    echo "  Windows: https://docs.docker.com/desktop/windows/install/"
    exit 1
fi

# Check Docker Compose
if command -v docker-compose &> /dev/null; then
    COMPOSE_VERSION=$(docker-compose --version | cut -d' ' -f3 | cut -d',' -f1)
    echo -e "${GREEN}✓${NC} Docker Compose found: $COMPOSE_VERSION"
elif docker compose version &> /dev/null; then
    COMPOSE_VERSION=$(docker compose version | cut -d' ' -f3)
    echo -e "${GREEN}✓${NC} Docker Compose (plugin) found: $COMPOSE_VERSION"
    # Use docker compose instead of docker-compose
    alias docker-compose='docker compose'
else
    echo -e "${RED}✗${NC} Docker Compose not found"
    echo ""
    echo "Please install Docker Compose:"
    echo "  https://docs.docker.com/compose/install/"
    exit 1
fi

# Check Docker daemon
if ! docker info &> /dev/null; then
    echo -e "${RED}✗${NC} Docker daemon not running"
    echo ""
    echo "Please start Docker and try again."
    exit 1
else
    echo -e "${GREEN}✓${NC} Docker daemon is running"
fi

# Check Git (optional)
if command -v git &> /dev/null; then
    GIT_VERSION=$(git --version | cut -d' ' -f3)
    echo -e "${GREEN}✓${NC} Git found: $GIT_VERSION"
else
    echo -e "${YELLOW}⚠${NC} Git not found (optional)"
fi

# Check Python (optional, for development)
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
    echo -e "${GREEN}✓${NC} Python found: $PYTHON_VERSION"
else
    echo -e "${YELLOW}⚠${NC} Python not found (optional)"
fi

# Check available disk space
AVAILABLE_SPACE=$(df -h "$PROJECT_ROOT" | awk 'NR==2 {print $4}')
echo -e "${GREEN}✓${NC} Available disk space: $AVAILABLE_SPACE"

echo ""
echo -e "${GREEN}All prerequisites satisfied!${NC}"
echo ""

# Step 2: Create Directory Structure
echo -e "${BLUE}[Step 2/8] Creating Directory Structure...${NC}"
echo ""

mkdir -p "$PROJECT_ROOT/backups"
echo -e "${GREEN}✓${NC} Created: backups/"

mkdir -p "$PROJECT_ROOT/logs"
echo -e "${GREEN}✓${NC} Created: logs/"

mkdir -p "$PROJECT_ROOT/data/postgres"
echo -e "${GREEN}✓${NC} Created: data/postgres/"

mkdir -p "$PROJECT_ROOT/data/redis"
echo -e "${GREEN}✓${NC} Created: data/redis/"

mkdir -p "$PROJECT_ROOT/tests"
echo -e "${GREEN}✓${NC} Created: tests/"

echo ""
echo -e "${GREEN}Directory structure created!${NC}"
echo ""

# Step 3: Environment Configuration
echo -e "${BLUE}[Step 3/8] Configuring Environment...${NC}"
echo ""

if [ -f "$ENV_FILE" ]; then
    echo -e "${YELLOW}⚠${NC} .env file already exists"
    read -p "Overwrite? (yes/no): " confirm
    if [ "$confirm" != "yes" ]; then
        echo "Keeping existing .env file"
    else
        rm "$ENV_FILE"
        create_env=true
    fi
else
    create_env=true
fi

if [ "$create_env" = true ]; then
    echo "Creating .env file..."

    # Generate random secrets
    JWT_SECRET=$(openssl rand -base64 32 | tr -d "=+/" | cut -c1-32)
    POSTGRES_PASSWORD=$(openssl rand -base64 16 | tr -d "=+/" | cut -c1-16)
    REDIS_PASSWORD=$(openssl rand -base64 16 | tr -d "=+/" | cut -c1-16)
    API_KEY=$(openssl rand -base64 32 | tr -d "=+/" | cut -c1-32)

    cat > "$ENV_FILE" <<EOF
# Story Portal Platform V2 - Environment Configuration
# Generated on $(date)

# ===================================
# Security Secrets (CHANGE IN PRODUCTION!)
# ===================================
JWT_SECRET=$JWT_SECRET
API_ENCRYPTION_KEY=$API_KEY

# ===================================
# Database Configuration
# ===================================
POSTGRES_USER=postgres
POSTGRES_PASSWORD=$POSTGRES_PASSWORD
POSTGRES_DB=agentic_platform
POSTGRES_HOST=agentic-postgres
POSTGRES_PORT=5432

# PostgreSQL Performance
POSTGRES_SHARED_BUFFERS=512MB
POSTGRES_WORK_MEM=32MB
POSTGRES_MAINTENANCE_WORK_MEM=256MB
POSTGRES_EFFECTIVE_CACHE_SIZE=4GB

# ===================================
# Redis Configuration
# ===================================
REDIS_PASSWORD=$REDIS_PASSWORD
REDIS_HOST=agentic-redis
REDIS_PORT=6379
REDIS_MAX_MEMORY=512mb
REDIS_MAX_MEMORY_POLICY=allkeys-lru

# ===================================
# Application Configuration
# ===================================
ENVIRONMENT=development
LOG_LEVEL=INFO
DEBUG=false

# ===================================
# API Gateway Configuration
# ===================================
API_GATEWAY_HOST=0.0.0.0
API_GATEWAY_PORT=8009
API_RATE_LIMIT=100
API_RATE_LIMIT_PERIOD=60

# ===================================
# Monitoring Configuration
# ===================================
PROMETHEUS_RETENTION=15d
GRAFANA_ADMIN_PASSWORD=admin

# ===================================
# LLM Configuration (Ollama)
# ===================================
OLLAMA_HOST=http://host.docker.internal:11434
OLLAMA_MODEL=llama3.2:latest

# ===================================
# Backup Configuration
# ===================================
BACKUP_RETENTION_DAYS=30
EOF

    chmod 600 "$ENV_FILE"
    echo -e "${GREEN}✓${NC} Created .env file with generated secrets"
    echo -e "${YELLOW}⚠${NC} IMPORTANT: Change secrets before deploying to production!"
else
    echo -e "${GREEN}✓${NC} Using existing .env file"
fi

echo ""
echo -e "${GREEN}Environment configured!${NC}"
echo ""

# Step 4: Docker Network
echo -e "${BLUE}[Step 4/8] Setting Up Docker Network...${NC}"
echo ""

if docker network ls | grep -q "agentic-network"; then
    echo -e "${GREEN}✓${NC} Docker network 'agentic-network' already exists"
else
    docker network create agentic-network
    echo -e "${GREEN}✓${NC} Created Docker network 'agentic-network'"
fi

echo ""
echo -e "${GREEN}Network configured!${NC}"
echo ""

# Step 5: Build Docker Images
echo -e "${BLUE}[Step 5/8] Building Docker Images...${NC}"
echo ""
echo "This may take 10-15 minutes on first run..."
echo ""

cd "$PROJECT_ROOT"

if docker-compose -f "$COMPOSE_FILE" build; then
    echo ""
    echo -e "${GREEN}✓${NC} Docker images built successfully"
else
    echo ""
    echo -e "${RED}✗${NC} Failed to build Docker images"
    echo "Check the error messages above and try again."
    exit 1
fi

echo ""
echo -e "${GREEN}Images built!${NC}"
echo ""

# Step 6: Start Services
echo -e "${BLUE}[Step 6/8] Starting Services...${NC}"
echo ""

if docker-compose -f "$COMPOSE_FILE" up -d; then
    echo ""
    echo -e "${GREEN}✓${NC} Services started successfully"
else
    echo ""
    echo -e "${RED}✗${NC} Failed to start services"
    echo "Check the error messages above and try again."
    exit 1
fi

echo ""
echo -e "${YELLOW}Waiting for services to initialize (30 seconds)...${NC}"
sleep 30

echo ""
echo -e "${GREEN}Services started!${NC}"
echo ""

# Step 7: Health Checks
echo -e "${BLUE}[Step 7/8] Verifying Installation...${NC}"
echo ""

HEALTHY=0
UNHEALTHY=0

# Check key services
SERVICES=(
    "8009:L09 API Gateway"
    "8010:L10 Human Interface"
    "8001:L01 Data Layer"
)

for service in "${SERVICES[@]}"; do
    PORT=$(echo "$service" | cut -d: -f1)
    NAME=$(echo "$service" | cut -d: -f2)

    if curl -sf "http://localhost:$PORT/health" > /dev/null 2>&1; then
        echo -e "${GREEN}✓${NC} $NAME (port $PORT): Healthy"
        ((HEALTHY++))
    else
        echo -e "${RED}✗${NC} $NAME (port $PORT): Not responding"
        ((UNHEALTHY++))
    fi
done

# Check PostgreSQL
if docker exec agentic-postgres psql -U postgres -c "SELECT 1" > /dev/null 2>&1; then
    echo -e "${GREEN}✓${NC} PostgreSQL: Connected"
    ((HEALTHY++))
else
    echo -e "${RED}✗${NC} PostgreSQL: Not responding"
    ((UNHEALTHY++))
fi

# Check Redis
if docker exec agentic-redis redis-cli ping > /dev/null 2>&1; then
    echo -e "${GREEN}✓${NC} Redis: Connected"
    ((HEALTHY++))
else
    echo -e "${RED}✗${NC} Redis: Not responding"
    ((UNHEALTHY++))
fi

echo ""
if [ $UNHEALTHY -eq 0 ]; then
    echo -e "${GREEN}✓ All services healthy! ($HEALTHY/$((HEALTHY+UNHEALTHY)))${NC}"
else
    echo -e "${YELLOW}⚠ Some services unhealthy ($HEALTHY/$((HEALTHY+UNHEALTHY)))${NC}"
    echo "Check logs with: docker-compose -f $COMPOSE_FILE logs"
fi

echo ""

# Step 8: Display Summary
echo -e "${BLUE}[Step 8/8] Setup Complete!${NC}"
echo ""

echo -e "${GREEN}╔═══════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║                                                           ║${NC}"
echo -e "${GREEN}║           Story Portal Platform V2 is Ready!              ║${NC}"
echo -e "${GREEN}║                                                           ║${NC}"
echo -e "${GREEN}╚═══════════════════════════════════════════════════════════╝${NC}"
echo ""

echo -e "${CYAN}Access Points:${NC}"
echo -e "  ${BLUE}API Gateway:${NC}        http://localhost:8009"
echo -e "  ${BLUE}API Documentation:${NC}  http://localhost:8009/docs"
echo -e "  ${BLUE}Platform UI:${NC}        http://localhost:8010"
echo -e "  ${BLUE}Prometheus:${NC}         http://localhost:9090"
echo -e "  ${BLUE}Grafana:${NC}            http://localhost:3000 (admin/admin)"
echo ""

echo -e "${CYAN}Useful Commands:${NC}"
echo -e "  ${YELLOW}make help${NC}           - Show all available commands"
echo -e "  ${YELLOW}make status${NC}         - View platform status"
echo -e "  ${YELLOW}make health${NC}         - Check service health"
echo -e "  ${YELLOW}make logs${NC}           - View service logs"
echo -e "  ${YELLOW}make backup${NC}         - Create backup"
echo -e "  ${YELLOW}make down${NC}           - Stop all services"
echo -e "  ${YELLOW}make up${NC}             - Start all services"
echo ""

echo -e "${CYAN}Documentation:${NC}"
echo -e "  ${BLUE}Architecture:${NC}    docs/ARCHITECTURE.md"
echo -e "  ${BLUE}Development:${NC}     docs/DEVELOPMENT.md"
echo -e "  ${BLUE}Security:${NC}        SECURITY.md"
echo -e "  ${BLUE}Monitoring:${NC}      docs/MONITORING.md"
echo -e "  ${BLUE}Scripts:${NC}         platform/scripts/README.md"
echo ""

echo -e "${CYAN}Next Steps:${NC}"
echo "  1. Review the generated .env file"
echo "  2. Visit http://localhost:8009/docs to explore the API"
echo "  3. Set up Grafana dashboards (see docs/MONITORING.md)"
echo "  4. Configure backup schedule (see platform/scripts/README.md)"
echo "  5. Read SECURITY.md for production deployment guidelines"
echo ""

if [ $UNHEALTHY -gt 0 ]; then
    echo -e "${YELLOW}⚠ Note: Some services are unhealthy. Check logs for details:${NC}"
    echo "  docker-compose -f $COMPOSE_FILE logs"
    echo ""
fi

echo -e "${GREEN}Setup complete! Happy coding! 🚀${NC}"
echo ""

# Optional: Open browser
if command -v open &> /dev/null; then
    read -p "Open API documentation in browser? (yes/no): " open_browser
    if [ "$open_browser" = "yes" ]; then
        sleep 2
        open "http://localhost:8009/docs"
    fi
fi
