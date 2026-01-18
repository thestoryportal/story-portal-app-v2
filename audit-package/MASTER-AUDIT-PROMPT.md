# MASTER AUDIT PROMPT - Story Portal Platform v2

## AUTONOMOUS EXECUTION DIRECTIVE

You are executing a comprehensive platform audit. Run this AUTONOMOUSLY from start to finish without stopping for confirmation. Save all outputs to files as you go. If a check fails, document it and continue.

**Working Directory:** The directory where this prompt was invoked (should be `story-portal-app-v2/`)
**Output Directory:** `./audit/` (create if not exists)
**Total Agents:** 25
**Estimated Duration:** 4-6 hours

---

## PHASE 0: INITIALIZATION

### Step 0.1: Create Output Directories

```bash
mkdir -p ./audit/{findings,reports,checkpoints,evidence,logs,consolidated}
echo "Audit started at $(date)" > ./audit/logs/audit.log
```

### Step 0.2: Record System State

```bash
echo "=== SYSTEM STATE ===" > ./audit/checkpoints/initial-state.txt
echo "Date: $(date)" >> ./audit/checkpoints/initial-state.txt
echo "Working Directory: $(pwd)" >> ./audit/checkpoints/initial-state.txt
echo "User: $(whoami)" >> ./audit/checkpoints/initial-state.txt
docker ps -a >> ./audit/checkpoints/initial-state.txt 2>&1 || echo "Docker not available"
```

### Step 0.3: Verify Platform Repository

```bash
if [ -d "./platform" ]; then
  echo "Platform directory found" >> ./audit/logs/audit.log
  ls -la ./platform/ > ./audit/checkpoints/platform-structure.txt
else
  echo "ERROR: Platform directory not found" >> ./audit/logs/audit.log
  echo "ERROR: Run this from story-portal-app-v2 root directory"
fi
```

---

## PHASE 1: INFRASTRUCTURE DISCOVERY

Execute these checks and save results. Continue even if individual checks fail.

### AUD-019: Docker/Container Infrastructure

**Execute:**
```bash
echo "=== AUD-019: Docker Infrastructure Audit ===" | tee ./audit/logs/AUD-019.log

# Container Inventory
echo "## Container Inventory" > ./audit/findings/AUD-019-docker.md
docker ps -a --format "table {{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}" >> ./audit/findings/AUD-019-docker.md 2>&1

# Resource Limits
echo "## Resource Limits" >> ./audit/findings/AUD-019-docker.md
docker ps -q | xargs -I {} docker inspect --format='{{.Name}}: Memory={{.HostConfig.Memory}} CPU={{.HostConfig.NanoCpus}}' {} >> ./audit/findings/AUD-019-docker.md 2>&1

# Image Versions
echo "## Image Versions" >> ./audit/findings/AUD-019-docker.md
docker images --format "table {{.Repository}}\t{{.Tag}}\t{{.Size}}" >> ./audit/findings/AUD-019-docker.md 2>&1

# Volume Mounts
echo "## Volumes" >> ./audit/findings/AUD-019-docker.md
docker ps -q | xargs -I {} docker inspect --format='{{.Name}}: {{range .Mounts}}{{.Source}}->{{.Destination}} {{end}}' {} >> ./audit/findings/AUD-019-docker.md 2>&1

# Network Configuration
echo "## Networks" >> ./audit/findings/AUD-019-docker.md
docker network ls >> ./audit/findings/AUD-019-docker.md 2>&1

# Docker Compose Validation
echo "## Compose Validation" >> ./audit/findings/AUD-019-docker.md
docker-compose config --quiet && echo "VALID" >> ./audit/findings/AUD-019-docker.md || echo "INVALID or NOT FOUND" >> ./audit/findings/AUD-019-docker.md
```

**Analyze findings and create report:** `./audit/reports/AUD-019-container-infrastructure.md`

---

### AUD-020: LLM/Model Inventory

**Execute:**
```bash
echo "=== AUD-020: LLM Model Audit ===" | tee ./audit/logs/AUD-020.log

echo "## Model List" > ./audit/findings/AUD-020-llm.md
curl -s http://localhost:11434/api/tags 2>/dev/null | python3 -c "
import json, sys
try:
    data = json.load(sys.stdin)
    for m in data.get('models', []):
        print(f\"- {m['name']}: {m.get('size', 'unknown')} bytes\")
except:
    print('Ollama not available or no models')
" >> ./audit/findings/AUD-020-llm.md

echo "## Model Details" >> ./audit/findings/AUD-020-llm.md
curl -s http://localhost:11434/api/tags 2>/dev/null | python3 -c "
import json, sys
try:
    data = json.load(sys.stdin)
    for m in data.get('models', []):
        print(f\"### {m['name']}\")
        print(f\"Modified: {m.get('modified_at', 'unknown')}\")
        print(f\"Size: {m.get('size', 'unknown')}\")
        print()
except:
    print('Could not retrieve model details')
" >> ./audit/findings/AUD-020-llm.md

# GPU Check
echo "## GPU Status" >> ./audit/findings/AUD-020-llm.md
nvidia-smi --query-gpu=name,memory.used,memory.total --format=csv 2>/dev/null >> ./audit/findings/AUD-020-llm.md || echo "No NVIDIA GPU detected" >> ./audit/findings/AUD-020-llm.md
```

**Analyze findings and create report:** `./audit/reports/AUD-020-llm-inventory.md`

---

### AUD-021: PostgreSQL Deep Configuration

**Execute:**
```bash
echo "=== AUD-021: PostgreSQL Deep Audit ===" | tee ./audit/logs/AUD-021.log

echo "## PostgreSQL Configuration" > ./audit/findings/AUD-021-postgres.md

# Connection Test
echo "### Connection Test" >> ./audit/findings/AUD-021-postgres.md
pg_isready -h localhost -p 5432 >> ./audit/findings/AUD-021-postgres.md 2>&1

# Extensions
echo "### Extensions" >> ./audit/findings/AUD-021-postgres.md
PGPASSWORD=postgres psql -h localhost -U postgres -d agentic -c "SELECT extname, extversion FROM pg_extension;" >> ./audit/findings/AUD-021-postgres.md 2>&1

# Database Size
echo "### Database Size" >> ./audit/findings/AUD-021-postgres.md
PGPASSWORD=postgres psql -h localhost -U postgres -d agentic -c "SELECT pg_size_pretty(pg_database_size('agentic'));" >> ./audit/findings/AUD-021-postgres.md 2>&1

# Table Sizes
echo "### Table Sizes" >> ./audit/findings/AUD-021-postgres.md
PGPASSWORD=postgres psql -h localhost -U postgres -d agentic -c "SELECT schemaname, tablename, pg_size_pretty(pg_total_relation_size(schemaname || '.' || tablename)) as size FROM pg_tables WHERE schemaname='public' ORDER BY pg_total_relation_size(schemaname || '.' || tablename) DESC LIMIT 20;" >> ./audit/findings/AUD-021-postgres.md 2>&1

# Connection Count
echo "### Active Connections" >> ./audit/findings/AUD-021-postgres.md
PGPASSWORD=postgres psql -h localhost -U postgres -c "SELECT count(*) as connections FROM pg_stat_activity;" >> ./audit/findings/AUD-021-postgres.md 2>&1

# Check for pgvector
echo "### pgvector Status" >> ./audit/findings/AUD-021-postgres.md
PGPASSWORD=postgres psql -h localhost -U postgres -d agentic -c "SELECT extversion FROM pg_extension WHERE extname='vector';" >> ./audit/findings/AUD-021-postgres.md 2>&1 || echo "pgvector NOT installed" >> ./audit/findings/AUD-021-postgres.md
```

**Analyze findings and create report:** `./audit/reports/AUD-021-postgresql-deep.md`

---

## PHASE 2: SERVICE DISCOVERY

### AUD-010: Service Health Discovery

**Execute:**
```bash
echo "=== AUD-010: Service Discovery ===" | tee ./audit/logs/AUD-010.log

cat > ./audit/findings/AUD-010-services.md << 'EOF'
# Service Discovery Findings

## Infrastructure Services
EOF

# PostgreSQL
echo "### PostgreSQL (5432)" >> ./audit/findings/AUD-010-services.md
pg_isready -h localhost -p 5432 >> ./audit/findings/AUD-010-services.md 2>&1 && echo "Status: RUNNING" >> ./audit/findings/AUD-010-services.md || echo "Status: NOT AVAILABLE" >> ./audit/findings/AUD-010-services.md

# Redis
echo "### Redis (6379)" >> ./audit/findings/AUD-010-services.md
redis-cli ping >> ./audit/findings/AUD-010-services.md 2>&1 && echo "Status: RUNNING" >> ./audit/findings/AUD-010-services.md || echo "Status: NOT AVAILABLE" >> ./audit/findings/AUD-010-services.md

# Ollama
echo "### Ollama (11434)" >> ./audit/findings/AUD-010-services.md
curl -s http://localhost:11434/api/version >> ./audit/findings/AUD-010-services.md 2>&1 && echo "Status: RUNNING" >> ./audit/findings/AUD-010-services.md || echo "Status: NOT AVAILABLE" >> ./audit/findings/AUD-010-services.md

# Application Layers
echo "## Application Layer Health" >> ./audit/findings/AUD-010-services.md
for port in 8001 8002 8003 8004 8005 8006 8007 8008 8009 8010 8011 8012; do
  echo "### Port $port" >> ./audit/findings/AUD-010-services.md
  response=$(curl -s -w "\nHTTP_CODE:%{http_code}" http://localhost:$port/health 2>/dev/null)
  if [ $? -eq 0 ]; then
    echo "$response" >> ./audit/findings/AUD-010-services.md
  else
    echo "NOT RESPONDING" >> ./audit/findings/AUD-010-services.md
  fi
done

# MCP Services (PM2)
echo "## MCP Services (PM2)" >> ./audit/findings/AUD-010-services.md
pm2 list >> ./audit/findings/AUD-010-services.md 2>&1 || echo "PM2 not available" >> ./audit/findings/AUD-010-services.md
```

**Create structured JSON:**
```bash
cat > ./audit/findings/AUD-010-findings.json << 'EOF'
{
  "agent": "AUD-010",
  "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "category": "service-discovery",
  "services_checked": []
}
EOF
```

**Analyze findings and create report:** `./audit/reports/AUD-010-service-discovery.md`

---

### AUD-011: CLI Tooling Audit

**Execute:**
```bash
echo "=== AUD-011: CLI Tooling Audit ===" | tee ./audit/logs/AUD-011.log

echo "# CLI Tooling Audit" > ./audit/findings/AUD-011-cli.md

# Check each layer for CLI entry points
cd ./platform/src 2>/dev/null || cd ./platform 2>/dev/null || echo "Platform not found"

echo "## Layer CLI Status" >> ../../audit/findings/AUD-011-cli.md 2>/dev/null || echo "## Layer CLI Status" >> ./audit/findings/AUD-011-cli.md

for layer in L01_data_layer L02_runtime L03_tool_execution L04_model_gateway L05_planning L06_evaluation L07_learning L09_api_gateway L10_human_interface L11_integration; do
  echo "### $layer" >> ../../audit/findings/AUD-011-cli.md 2>/dev/null || echo "### $layer" >> ./audit/findings/AUD-011-cli.md
  if [ -d "$layer" ]; then
    # Check for __main__.py
    if [ -f "$layer/__main__.py" ]; then
      echo "- CLI Entry Point: YES (__main__.py)" 
    else
      echo "- CLI Entry Point: NO"
    fi
    # Check for CLI module
    if [ -f "$layer/cli.py" ]; then
      echo "- CLI Module: YES (cli.py)"
    else
      echo "- CLI Module: NO"
    fi
    # Try to get help
    python -m $layer --help 2>&1 | head -5 || echo "- Cannot execute"
  else
    echo "- Directory: NOT FOUND"
  fi >> ../../audit/findings/AUD-011-cli.md 2>/dev/null || >> ./audit/findings/AUD-011-cli.md
done

cd - > /dev/null 2>&1
```

**Analyze findings and create report:** `./audit/reports/AUD-011-cli-tooling.md`

---

### AUD-012: MCP Service Audit

**Execute:**
```bash
echo "=== AUD-012: MCP Service Audit ===" | tee ./audit/logs/AUD-012.log

echo "# MCP Service Audit" > ./audit/findings/AUD-012-mcp.md

# PM2 Status
echo "## PM2 Process Status" >> ./audit/findings/AUD-012-mcp.md
pm2 jlist 2>/dev/null | python3 -c "
import json, sys
try:
    data = json.load(sys.stdin)
    for p in data:
        print(f\"- {p['name']}: {p['pm2_env']['status']} (pid: {p.get('pid', 'N/A')})\")
except:
    print('PM2 not available')
" >> ./audit/findings/AUD-012-mcp.md

# MCP Config Files
echo "## MCP Configuration Files" >> ./audit/findings/AUD-012-mcp.md
find . -name "*.mcp.json" -o -name "mcp*.json" 2>/dev/null | head -20 >> ./audit/findings/AUD-012-mcp.md
find . -name "mcp-config*" 2>/dev/null | head -20 >> ./audit/findings/AUD-012-mcp.md

# Tool Definitions
echo "## Tool Definitions Found" >> ./audit/findings/AUD-012-mcp.md
grep -r "\"tools\"" --include="*.json" ./platform 2>/dev/null | head -20 >> ./audit/findings/AUD-012-mcp.md
```

**Analyze findings and create report:** `./audit/reports/AUD-012-mcp-services.md`

---

### AUD-013: Configuration Audit

**Execute:**
```bash
echo "=== AUD-013: Configuration Audit ===" | tee ./audit/logs/AUD-013.log

echo "# Configuration Audit" > ./audit/findings/AUD-013-config.md

# Environment Files
echo "## Environment Files" >> ./audit/findings/AUD-013-config.md
find . -name ".env*" -type f 2>/dev/null | head -20 >> ./audit/findings/AUD-013-config.md

# Count env vars (without exposing values)
echo "## Environment Variables (count per file)" >> ./audit/findings/AUD-013-config.md
for f in $(find . -name ".env*" -type f 2>/dev/null | head -10); do
  count=$(grep -c "=" "$f" 2>/dev/null || echo 0)
  echo "- $f: $count variables" >> ./audit/findings/AUD-013-config.md
done

# Config YAML/JSON files
echo "## Configuration Files" >> ./audit/findings/AUD-013-config.md
find ./platform -name "config*.yaml" -o -name "config*.json" -o -name "settings*.yaml" 2>/dev/null | head -20 >> ./audit/findings/AUD-013-config.md

# Check for sensitive patterns (without exposing)
echo "## Sensitive Pattern Detection" >> ./audit/findings/AUD-013-config.md
grep -r "API_KEY\|SECRET\|PASSWORD\|TOKEN" --include=".env*" . 2>/dev/null | wc -l | xargs -I {} echo "Found {} lines with sensitive patterns" >> ./audit/findings/AUD-013-config.md
```

**Analyze findings and create report:** `./audit/reports/AUD-013-configuration.md`

---

## PHASE 3: SECURITY & COMPLIANCE

### AUD-002: Security Audit

**Execute:**
```bash
echo "=== AUD-002: Security Audit ===" | tee ./audit/logs/AUD-002.log

echo "# Security Audit" > ./audit/findings/AUD-002-security.md

# Authentication Patterns
echo "## Authentication Patterns" >> ./audit/findings/AUD-002-security.md
grep -r "jwt\|oauth\|bearer\|api.key\|authenticate" --include="*.py" ./platform 2>/dev/null | wc -l | xargs -I {} echo "Found {} auth-related code lines" >> ./audit/findings/AUD-002-security.md

# Authorization Patterns
echo "## Authorization Patterns" >> ./audit/findings/AUD-002-security.md
grep -r "permission\|authorize\|rbac\|abac\|policy" --include="*.py" ./platform 2>/dev/null | wc -l | xargs -I {} echo "Found {} authz-related code lines" >> ./audit/findings/AUD-002-security.md

# Input Validation
echo "## Input Validation" >> ./audit/findings/AUD-002-security.md
grep -r "pydantic\|validator\|validate\|sanitize" --include="*.py" ./platform 2>/dev/null | wc -l | xargs -I {} echo "Found {} validation-related code lines" >> ./audit/findings/AUD-002-security.md

# Hardcoded Secrets (pattern only, not values)
echo "## Potential Hardcoded Secrets" >> ./audit/findings/AUD-002-security.md
grep -rn "password\s*=\s*['\"]" --include="*.py" ./platform 2>/dev/null | wc -l | xargs -I {} echo "Found {} potential hardcoded passwords" >> ./audit/findings/AUD-002-security.md

# SQL Injection Patterns
echo "## SQL Patterns" >> ./audit/findings/AUD-002-security.md
grep -rn "execute\|raw_sql\|text(" --include="*.py" ./platform 2>/dev/null | wc -l | xargs -I {} echo "Found {} raw SQL patterns (review needed)" >> ./audit/findings/AUD-002-security.md

# CORS Configuration
echo "## CORS Configuration" >> ./audit/findings/AUD-002-security.md
grep -rn "CORSMiddleware\|allow_origins" --include="*.py" ./platform 2>/dev/null >> ./audit/findings/AUD-002-security.md
```

**Analyze findings and create report:** `./audit/reports/AUD-002-security.md`

---

### AUD-014: Token Management Audit

**Execute:**
```bash
echo "=== AUD-014: Token Management Audit ===" | tee ./audit/logs/AUD-014.log

echo "# Token Management Audit" > ./audit/findings/AUD-014-tokens.md

# JWT Configuration
echo "## JWT Patterns" >> ./audit/findings/AUD-014-tokens.md
grep -rn "jwt\|JWT\|JsonWebToken" --include="*.py" ./platform 2>/dev/null | head -30 >> ./audit/findings/AUD-014-tokens.md

# API Key Patterns
echo "## API Key Patterns" >> ./audit/findings/AUD-014-tokens.md
grep -rn "api.key\|apikey\|x-api-key" --include="*.py" ./platform 2>/dev/null | head -30 >> ./audit/findings/AUD-014-tokens.md

# Session Management
echo "## Session Patterns" >> ./audit/findings/AUD-014-tokens.md
grep -rn "session\|Session" --include="*.py" ./platform 2>/dev/null | head -30 >> ./audit/findings/AUD-014-tokens.md

# LLM Token Tracking
echo "## LLM Token Tracking" >> ./audit/findings/AUD-014-tokens.md
grep -rn "token_count\|usage\|prompt_tokens\|completion_tokens" --include="*.py" ./platform 2>/dev/null | head -30 >> ./audit/findings/AUD-014-tokens.md
```

**Analyze findings and create report:** `./audit/reports/AUD-014-token-management.md`

---

### AUD-023: Network/TLS Audit

**Execute:**
```bash
echo "=== AUD-023: Network/TLS Audit ===" | tee ./audit/logs/AUD-023.log

echo "# Network/TLS Audit" > ./audit/findings/AUD-023-network.md

# TLS Certificates
echo "## TLS Certificates" >> ./audit/findings/AUD-023-network.md
find . -name "*.pem" -o -name "*.crt" -o -name "*.key" 2>/dev/null | head -20 >> ./audit/findings/AUD-023-network.md
if [ $(find . -name "*.crt" 2>/dev/null | wc -l) -eq 0 ]; then
  echo "No TLS certificates found" >> ./audit/findings/AUD-023-network.md
fi

# Internal HTTPS
echo "## Internal HTTPS Usage" >> ./audit/findings/AUD-023-network.md
grep -rn "https://localhost\|https://127.0.0.1" --include="*.py" ./platform 2>/dev/null | wc -l | xargs -I {} echo "Found {} internal HTTPS references" >> ./audit/findings/AUD-023-network.md

# Exposed Ports
echo "## Exposed Docker Ports" >> ./audit/findings/AUD-023-network.md
docker ps --format "{{.Names}}: {{.Ports}}" 2>/dev/null >> ./audit/findings/AUD-023-network.md
```

**Analyze findings and create report:** `./audit/reports/AUD-023-network-tls.md`

---

### AUD-024: Backup/Recovery Audit

**Execute:**
```bash
echo "=== AUD-024: Backup/Recovery Audit ===" | tee ./audit/logs/AUD-024.log

echo "# Backup/Recovery Audit" > ./audit/findings/AUD-024-backup.md

# Backup Scripts
echo "## Backup Scripts" >> ./audit/findings/AUD-024-backup.md
find . -name "*backup*" -type f 2>/dev/null | head -20 >> ./audit/findings/AUD-024-backup.md
find . -name "*dump*" -type f 2>/dev/null | head -20 >> ./audit/findings/AUD-024-backup.md

# Redis Persistence
echo "## Redis Persistence" >> ./audit/findings/AUD-024-backup.md
redis-cli CONFIG GET save 2>/dev/null >> ./audit/findings/AUD-024-backup.md || echo "Redis not available" >> ./audit/findings/AUD-024-backup.md
redis-cli LASTSAVE 2>/dev/null >> ./audit/findings/AUD-024-backup.md

# PostgreSQL Backup Test
echo "## PostgreSQL Backup Capability" >> ./audit/findings/AUD-024-backup.md
which pg_dump >> ./audit/findings/AUD-024-backup.md 2>&1 && echo "pg_dump: AVAILABLE" >> ./audit/findings/AUD-024-backup.md || echo "pg_dump: NOT FOUND" >> ./audit/findings/AUD-024-backup.md
```

**Analyze findings and create report:** `./audit/reports/AUD-024-backup-recovery.md`

---

## PHASE 4: DATA & STATE

### AUD-004: Database Schema Audit

**Execute:**
```bash
echo "=== AUD-004: Database Schema Audit ===" | tee ./audit/logs/AUD-004.log

echo "# Database Schema Audit" > ./audit/findings/AUD-004-database.md

# List Tables
echo "## Tables" >> ./audit/findings/AUD-004-database.md
PGPASSWORD=postgres psql -h localhost -U postgres -d agentic -c "\dt" >> ./audit/findings/AUD-004-database.md 2>&1

# List Indexes
echo "## Indexes" >> ./audit/findings/AUD-004-database.md
PGPASSWORD=postgres psql -h localhost -U postgres -d agentic -c "\di" >> ./audit/findings/AUD-004-database.md 2>&1

# Foreign Keys
echo "## Foreign Key Constraints" >> ./audit/findings/AUD-004-database.md
PGPASSWORD=postgres psql -h localhost -U postgres -d agentic -c "SELECT conname, conrelid::regclass, confrelid::regclass FROM pg_constraint WHERE contype = 'f';" >> ./audit/findings/AUD-004-database.md 2>&1

# Check Constraints
echo "## Check Constraints" >> ./audit/findings/AUD-004-database.md
PGPASSWORD=postgres psql -h localhost -U postgres -d agentic -c "SELECT conname, conrelid::regclass FROM pg_constraint WHERE contype = 'c';" >> ./audit/findings/AUD-004-database.md 2>&1

# Schema Definition Files
echo "## Schema Files in Codebase" >> ./audit/findings/AUD-004-database.md
find ./platform -name "*schema*" -o -name "*migration*" -o -name "models.py" 2>/dev/null | head -30 >> ./audit/findings/AUD-004-database.md
```

**Analyze findings and create report:** `./audit/reports/AUD-004-database-schema.md`

---

### AUD-015: Redis State Audit

**Execute:**
```bash
echo "=== AUD-015: Redis State Audit ===" | tee ./audit/logs/AUD-015.log

echo "# Redis State Audit" > ./audit/findings/AUD-015-redis.md

# Redis Info
echo "## Redis Info" >> ./audit/findings/AUD-015-redis.md
redis-cli INFO server 2>/dev/null | head -20 >> ./audit/findings/AUD-015-redis.md

# Key Patterns
echo "## Key Patterns" >> ./audit/findings/AUD-015-redis.md
redis-cli KEYS "*" 2>/dev/null | head -50 >> ./audit/findings/AUD-015-redis.md

# Key Count by Pattern
echo "## Key Statistics" >> ./audit/findings/AUD-015-redis.md
redis-cli DBSIZE 2>/dev/null >> ./audit/findings/AUD-015-redis.md

# Memory Usage
echo "## Memory Usage" >> ./audit/findings/AUD-015-redis.md
redis-cli INFO memory 2>/dev/null | grep -E "used_memory|maxmemory" >> ./audit/findings/AUD-015-redis.md

# Pub/Sub Channels
echo "## Pub/Sub Channels" >> ./audit/findings/AUD-015-redis.md
redis-cli PUBSUB CHANNELS "*" 2>/dev/null >> ./audit/findings/AUD-015-redis.md
```

**Analyze findings and create report:** `./audit/reports/AUD-015-redis-state.md`

---

### AUD-017: Event Flow Audit

**Execute:**
```bash
echo "=== AUD-017: Event Flow Audit ===" | tee ./audit/logs/AUD-017.log

echo "# Event Flow Audit" > ./audit/findings/AUD-017-events.md

# Event Sourcing Patterns
echo "## Event Sourcing Code" >> ./audit/findings/AUD-017-events.md
grep -rn "event_store\|EventStore\|append_event\|get_events" --include="*.py" ./platform 2>/dev/null | head -30 >> ./audit/findings/AUD-017-events.md

# Event Types
echo "## Event Type Definitions" >> ./audit/findings/AUD-017-events.md
grep -rn "class.*Event\|EventType\|event_type" --include="*.py" ./platform 2>/dev/null | head -30 >> ./audit/findings/AUD-017-events.md

# CQRS Patterns
echo "## CQRS Patterns" >> ./audit/findings/AUD-017-events.md
grep -rn "Command\|Query\|CommandHandler\|QueryHandler" --include="*.py" ./platform 2>/dev/null | head -30 >> ./audit/findings/AUD-017-events.md

# Event Table
echo "## Event Table Contents (sample)" >> ./audit/findings/AUD-017-events.md
PGPASSWORD=postgres psql -h localhost -U postgres -d agentic -c "SELECT * FROM events LIMIT 5;" >> ./audit/findings/AUD-017-events.md 2>&1 || echo "No events table" >> ./audit/findings/AUD-017-events.md
```

**Analyze findings and create report:** `./audit/reports/AUD-017-event-flow.md`

---

## PHASE 5: INTEGRATION & API

### AUD-016: API Endpoint Audit

**Execute:**
```bash
echo "=== AUD-016: API Endpoint Audit ===" | tee ./audit/logs/AUD-016.log

echo "# API Endpoint Audit" > ./audit/findings/AUD-016-api.md

# FastAPI Routes
echo "## FastAPI Route Definitions" >> ./audit/findings/AUD-016-api.md
grep -rn "@app\.\|@router\." --include="*.py" ./platform 2>/dev/null | head -100 >> ./audit/findings/AUD-016-api.md

# Route Count by Method
echo "## Route Counts" >> ./audit/findings/AUD-016-api.md
echo "GET routes: $(grep -rn "@.*\.get(" --include="*.py" ./platform 2>/dev/null | wc -l)" >> ./audit/findings/AUD-016-api.md
echo "POST routes: $(grep -rn "@.*\.post(" --include="*.py" ./platform 2>/dev/null | wc -l)" >> ./audit/findings/AUD-016-api.md
echo "PUT routes: $(grep -rn "@.*\.put(" --include="*.py" ./platform 2>/dev/null | wc -l)" >> ./audit/findings/AUD-016-api.md
echo "DELETE routes: $(grep -rn "@.*\.delete(" --include="*.py" ./platform 2>/dev/null | wc -l)" >> ./audit/findings/AUD-016-api.md

# OpenAPI Specs
echo "## OpenAPI Specifications" >> ./audit/findings/AUD-016-api.md
find ./platform -name "openapi*.json" -o -name "openapi*.yaml" -o -name "swagger*" 2>/dev/null >> ./audit/findings/AUD-016-api.md

# Health Endpoints
echo "## Health Endpoints" >> ./audit/findings/AUD-016-api.md
grep -rn "/health\|/ready\|/live" --include="*.py" ./platform 2>/dev/null >> ./audit/findings/AUD-016-api.md
```

**Analyze findings and create report:** `./audit/reports/AUD-016-api-endpoints.md`

---

### AUD-005: Integration Test Audit

**Execute:**
```bash
echo "=== AUD-005: Integration Test Audit ===" | tee ./audit/logs/AUD-005.log

echo "# Integration Audit" > ./audit/findings/AUD-005-integration.md

# Cross-Layer Imports
echo "## Cross-Layer Imports" >> ./audit/findings/AUD-005-integration.md
for layer in L01 L02 L03 L04 L05 L06 L07 L09 L10 L11; do
  echo "### $layer imports:" >> ./audit/findings/AUD-005-integration.md
  grep -rn "from.*$layer\|import.*$layer" --include="*.py" ./platform 2>/dev/null | grep -v "^./platform/src/$layer" | head -10 >> ./audit/findings/AUD-005-integration.md
done

# HTTP Client Usage
echo "## HTTP Client Patterns" >> ./audit/findings/AUD-005-integration.md
grep -rn "httpx\|requests\|aiohttp\|AsyncClient" --include="*.py" ./platform 2>/dev/null | wc -l | xargs -I {} echo "Found {} HTTP client usages" >> ./audit/findings/AUD-005-integration.md

# gRPC Usage
echo "## gRPC Patterns" >> ./audit/findings/AUD-005-integration.md
grep -rn "grpc\|protobuf" --include="*.py" ./platform 2>/dev/null | wc -l | xargs -I {} echo "Found {} gRPC references" >> ./audit/findings/AUD-005-integration.md
```

**Analyze findings and create report:** `./audit/reports/AUD-005-integration.md`

---

### AUD-018: Error Handling Audit

**Execute:**
```bash
echo "=== AUD-018: Error Handling Audit ===" | tee ./audit/logs/AUD-018.log

echo "# Error Handling Audit" > ./audit/findings/AUD-018-errors.md

# Exception Classes
echo "## Custom Exception Classes" >> ./audit/findings/AUD-018-errors.md
grep -rn "class.*Exception\|class.*Error" --include="*.py" ./platform 2>/dev/null | head -50 >> ./audit/findings/AUD-018-errors.md

# Try/Except Patterns
echo "## Exception Handling Patterns" >> ./audit/findings/AUD-018-errors.md
grep -rn "except\s" --include="*.py" ./platform 2>/dev/null | wc -l | xargs -I {} echo "Found {} except clauses" >> ./audit/findings/AUD-018-errors.md

# Bare Except
echo "## Bare Except (anti-pattern)" >> ./audit/findings/AUD-018-errors.md
grep -rn "except:" --include="*.py" ./platform 2>/dev/null | head -20 >> ./audit/findings/AUD-018-errors.md

# Error Codes
echo "## Error Code Definitions" >> ./audit/findings/AUD-018-errors.md
grep -rn "E[0-9]\{4\}\|error_code\|ErrorCode" --include="*.py" ./platform 2>/dev/null | head -50 >> ./audit/findings/AUD-018-errors.md

# HTTP Error Responses
echo "## HTTP Error Responses" >> ./audit/findings/AUD-018-errors.md
grep -rn "HTTPException\|status_code=" --include="*.py" ./platform 2>/dev/null | head -30 >> ./audit/findings/AUD-018-errors.md
```

**Analyze findings and create report:** `./audit/reports/AUD-018-error-handling.md`

---

### AUD-022: Observability Audit

**Execute:**
```bash
echo "=== AUD-022: Observability Audit ===" | tee ./audit/logs/AUD-022.log

echo "# Observability Audit" > ./audit/findings/AUD-022-observability.md

# Prometheus Metrics
echo "## Prometheus Metrics" >> ./audit/findings/AUD-022-observability.md
grep -rn "prometheus\|Counter\|Gauge\|Histogram\|metrics" --include="*.py" ./platform 2>/dev/null | head -30 >> ./audit/findings/AUD-022-observability.md

# Logging Configuration
echo "## Logging Configuration" >> ./audit/findings/AUD-022-observability.md
grep -rn "logging\|structlog\|loguru" --include="*.py" ./platform 2>/dev/null | head -30 >> ./audit/findings/AUD-022-observability.md

# OpenTelemetry
echo "## OpenTelemetry" >> ./audit/findings/AUD-022-observability.md
grep -rn "opentelemetry\|otel\|tracer\|span" --include="*.py" ./platform 2>/dev/null | head -30 >> ./audit/findings/AUD-022-observability.md

# Monitoring Services
echo "## Monitoring Service Status" >> ./audit/findings/AUD-022-observability.md
curl -s http://localhost:9090/-/healthy >> ./audit/findings/AUD-022-observability.md 2>&1 && echo "Prometheus: RUNNING" >> ./audit/findings/AUD-022-observability.md || echo "Prometheus: NOT RUNNING" >> ./audit/findings/AUD-022-observability.md
curl -s http://localhost:3000/api/health >> ./audit/findings/AUD-022-observability.md 2>&1 && echo "Grafana: RUNNING" >> ./audit/findings/AUD-022-observability.md || echo "Grafana: NOT RUNNING" >> ./audit/findings/AUD-022-observability.md
```

**Analyze findings and create report:** `./audit/reports/AUD-022-observability.md`

---

### AUD-025: External Dependencies Audit

**Execute:**
```bash
echo "=== AUD-025: External Dependencies Audit ===" | tee ./audit/logs/AUD-025.log

echo "# External Dependencies Audit" > ./audit/findings/AUD-025-external.md

# Python Dependencies
echo "## Python Dependencies" >> ./audit/findings/AUD-025-external.md
cat ./platform/requirements*.txt 2>/dev/null | grep -v "^#" | head -50 >> ./audit/findings/AUD-025-external.md

# External API References
echo "## External API References" >> ./audit/findings/AUD-025-external.md
grep -rn "https://\|http://" --include="*.py" ./platform 2>/dev/null | grep -v "localhost\|127.0.0.1\|0.0.0.0" | head -30 >> ./audit/findings/AUD-025-external.md

# CI/CD Configuration
echo "## CI/CD Files" >> ./audit/findings/AUD-025-external.md
ls -la .github/workflows/ 2>/dev/null >> ./audit/findings/AUD-025-external.md || echo "No GitHub Actions found" >> ./audit/findings/AUD-025-external.md

# Package Lock Files
echo "## Lock Files" >> ./audit/findings/AUD-025-external.md
find . -name "*.lock" -o -name "package-lock.json" -o -name "poetry.lock" 2>/dev/null | head -10 >> ./audit/findings/AUD-025-external.md
```

**Analyze findings and create report:** `./audit/reports/AUD-025-external-dependencies.md`

---

## PHASE 6: QUALITY & EXPERIENCE

### AUD-003: QA/Test Coverage Audit

**Execute:**
```bash
echo "=== AUD-003: QA/Test Coverage Audit ===" | tee ./audit/logs/AUD-003.log

echo "# QA/Test Coverage Audit" > ./audit/findings/AUD-003-qa.md

# Test Files
echo "## Test Files" >> ./audit/findings/AUD-003-qa.md
find ./platform -name "test_*.py" -o -name "*_test.py" 2>/dev/null | head -50 >> ./audit/findings/AUD-003-qa.md

# Test Count
echo "## Test Function Count" >> ./audit/findings/AUD-003-qa.md
grep -rn "def test_\|async def test_" --include="*.py" ./platform 2>/dev/null | wc -l | xargs -I {} echo "Found {} test functions" >> ./audit/findings/AUD-003-qa.md

# pytest Configuration
echo "## pytest Configuration" >> ./audit/findings/AUD-003-qa.md
cat ./platform/pytest.ini 2>/dev/null >> ./audit/findings/AUD-003-qa.md || cat ./platform/pyproject.toml 2>/dev/null | grep -A20 "\[tool.pytest" >> ./audit/findings/AUD-003-qa.md || echo "No pytest config found" >> ./audit/findings/AUD-003-qa.md

# Coverage Configuration
echo "## Coverage Configuration" >> ./audit/findings/AUD-003-qa.md
cat ./platform/.coveragerc 2>/dev/null >> ./audit/findings/AUD-003-qa.md || echo "No coverage config found" >> ./audit/findings/AUD-003-qa.md
```

**Analyze findings and create report:** `./audit/reports/AUD-003-qa-coverage.md`

---

### AUD-007: Code Quality Audit

**Execute:**
```bash
echo "=== AUD-007: Code Quality Audit ===" | tee ./audit/logs/AUD-007.log

echo "# Code Quality Audit" > ./audit/findings/AUD-007-quality.md

# Type Hints
echo "## Type Hint Coverage" >> ./audit/findings/AUD-007-quality.md
grep -rn "def.*->.*:" --include="*.py" ./platform 2>/dev/null | wc -l | xargs -I {} echo "Functions with return type hints: {}" >> ./audit/findings/AUD-007-quality.md
grep -rn "def.*:$" --include="*.py" ./platform 2>/dev/null | wc -l | xargs -I {} echo "Functions without return type hints: {}" >> ./audit/findings/AUD-007-quality.md

# Docstrings
echo "## Docstring Coverage" >> ./audit/findings/AUD-007-quality.md
grep -rn '"""' --include="*.py" ./platform 2>/dev/null | wc -l | xargs -I {} echo "Docstring markers found: {}" >> ./audit/findings/AUD-007-quality.md

# TODO/FIXME
echo "## TODO/FIXME Comments" >> ./audit/findings/AUD-007-quality.md
grep -rn "TODO\|FIXME\|XXX\|HACK" --include="*.py" ./platform 2>/dev/null | head -30 >> ./audit/findings/AUD-007-quality.md

# Code Complexity (file sizes)
echo "## Large Files (>500 lines)" >> ./audit/findings/AUD-007-quality.md
find ./platform -name "*.py" -exec wc -l {} \; 2>/dev/null | awk '$1 > 500 {print}' | sort -rn | head -20 >> ./audit/findings/AUD-007-quality.md
```

**Analyze findings and create report:** `./audit/reports/AUD-007-code-quality.md`

---

### AUD-006: Performance Audit

**Execute:**
```bash
echo "=== AUD-006: Performance Audit ===" | tee ./audit/logs/AUD-006.log

echo "# Performance Audit" > ./audit/findings/AUD-006-performance.md

# Async Patterns
echo "## Async Pattern Usage" >> ./audit/findings/AUD-006-performance.md
grep -rn "async def\|await " --include="*.py" ./platform 2>/dev/null | wc -l | xargs -I {} echo "Async patterns found: {}" >> ./audit/findings/AUD-006-performance.md

# Connection Pooling
echo "## Connection Pool Configuration" >> ./audit/findings/AUD-006-performance.md
grep -rn "pool_size\|max_connections\|pool" --include="*.py" ./platform 2>/dev/null | head -20 >> ./audit/findings/AUD-006-performance.md

# Caching
echo "## Caching Patterns" >> ./audit/findings/AUD-006-performance.md
grep -rn "cache\|@cached\|lru_cache\|ttl" --include="*.py" ./platform 2>/dev/null | head -20 >> ./audit/findings/AUD-006-performance.md

# N+1 Query Risk
echo "## Potential N+1 Query Patterns" >> ./audit/findings/AUD-006-performance.md
grep -rn "for.*in.*:.*\.query\|for.*in.*select" --include="*.py" ./platform 2>/dev/null | head -20 >> ./audit/findings/AUD-006-performance.md
```

**Analyze findings and create report:** `./audit/reports/AUD-006-performance.md`

---

### AUD-008: UI/UX Audit

**Execute:**
```bash
echo "=== AUD-008: UI/UX Audit ===" | tee ./audit/logs/AUD-008.log

echo "# UI/UX Audit" > ./audit/findings/AUD-008-uiux.md

# Frontend Files
echo "## Frontend Files" >> ./audit/findings/AUD-008-uiux.md
find ./platform -name "*.html" -o -name "*.jsx" -o -name "*.tsx" -o -name "*.vue" 2>/dev/null | head -30 >> ./audit/findings/AUD-008-uiux.md

# Static Assets
echo "## Static Assets" >> ./audit/findings/AUD-008-uiux.md
find ./platform -type d -name "static" -o -name "public" -o -name "assets" 2>/dev/null >> ./audit/findings/AUD-008-uiux.md

# L10 Human Interface
echo "## L10 Human Interface Layer" >> ./audit/findings/AUD-008-uiux.md
ls -la ./platform/src/L10_human_interface/ 2>/dev/null >> ./audit/findings/AUD-008-uiux.md || echo "L10 not found" >> ./audit/findings/AUD-008-uiux.md

# Accessibility Patterns
echo "## Accessibility Patterns" >> ./audit/findings/AUD-008-uiux.md
grep -rn "aria-\|role=\|alt=" --include="*.html" --include="*.jsx" --include="*.tsx" ./platform 2>/dev/null | wc -l | xargs -I {} echo "ARIA/accessibility attributes: {}" >> ./audit/findings/AUD-008-uiux.md
```

**Analyze findings and create report:** `./audit/reports/AUD-008-uiux.md`

---

### AUD-009: Developer Experience Audit

**Execute:**
```bash
echo "=== AUD-009: Developer Experience Audit ===" | tee ./audit/logs/AUD-009.log

echo "# Developer Experience Audit" > ./audit/findings/AUD-009-devex.md

# README Files
echo "## README Files" >> ./audit/findings/AUD-009-devex.md
find ./platform -name "README*" -type f 2>/dev/null >> ./audit/findings/AUD-009-devex.md

# Documentation
echo "## Documentation Files" >> ./audit/findings/AUD-009-devex.md
find ./platform -name "*.md" -type f 2>/dev/null | wc -l | xargs -I {} echo "Markdown files: {}" >> ./audit/findings/AUD-009-devex.md

# Examples
echo "## Example Files" >> ./audit/findings/AUD-009-devex.md
find ./platform -name "*example*" -o -name "*sample*" 2>/dev/null | head -20 >> ./audit/findings/AUD-009-devex.md

# Setup Scripts
echo "## Setup Scripts" >> ./audit/findings/AUD-009-devex.md
find ./platform -name "setup*" -o -name "install*" -o -name "bootstrap*" 2>/dev/null | head -10 >> ./audit/findings/AUD-009-devex.md

# Makefile
echo "## Makefile" >> ./audit/findings/AUD-009-devex.md
cat ./platform/Makefile 2>/dev/null | head -30 >> ./audit/findings/AUD-009-devex.md || echo "No Makefile found" >> ./audit/findings/AUD-009-devex.md
```

**Analyze findings and create report:** `./audit/reports/AUD-009-devex.md`

---

## PHASE 7: CONSOLIDATION

After completing all agent executions, consolidate findings.

### AUD-001: Orchestrator - Final Consolidation

**Execute consolidation:**

```bash
echo "=== CONSOLIDATION PHASE ===" | tee ./audit/logs/consolidation.log

# Create consolidated directory
mkdir -p ./audit/consolidated

# Generate timestamp
TIMESTAMP=$(date -u +%Y-%m-%dT%H:%M:%SZ)

echo "Consolidation started at $TIMESTAMP" >> ./audit/logs/consolidation.log
```

**Create Executive Summary:**

Read ALL files in `./audit/findings/` and `./audit/reports/` and create:

1. **`./audit/consolidated/EXECUTIVE-SUMMARY.md`**
   - Total findings count by severity (Critical, High, Medium, Low)
   - Service health summary
   - Top 10 priority issues
   - Key metrics dashboard

2. **`./audit/consolidated/V2-SPECIFICATION-INPUTS.md`** (MAIN DELIVERABLE)
   Structure:
   ```markdown
   # V2 Specification Inputs
   
   ## 1. Infrastructure Requirements
   [From AUD-019, AUD-020, AUD-021, AUD-022]
   
   ## 2. Security Requirements
   [From AUD-002, AUD-014, AUD-023, AUD-024]
   
   ## 3. Data Layer Requirements
   [From AUD-004, AUD-015, AUD-017]
   
   ## 4. API & Integration Requirements
   [From AUD-005, AUD-016, AUD-018]
   
   ## 5. Quality & Testing Requirements
   [From AUD-003, AUD-006, AUD-007]
   
   ## 6. UX & DevEx Requirements
   [From AUD-008, AUD-009]
   
   ## 7. Service Discovery Findings
   [From AUD-010, AUD-011, AUD-012, AUD-013]
   
   ## 8. External Dependencies
   [From AUD-025]
   
   ## 9. Priority Matrix
   
   | Priority | Category | Finding | Recommended Action |
   |----------|----------|---------|-------------------|
   | P1 | ... | ... | ... |
   
   ## 10. Implementation Roadmap
   
   ### Phase 1: Critical Fixes (Week 1-2)
   ### Phase 2: High Priority (Week 3-4)
   ### Phase 3: Medium Priority (Week 5-8)
   ### Phase 4: Low Priority/Enhancements (Week 9+)
   ```

3. **`./audit/consolidated/FULL-AUDIT-REPORT.md`**
   - Complete findings from all agents
   - Detailed analysis
   - Evidence references

4. **`./audit/consolidated/priority-matrix.md`**
   - All findings sorted by priority
   - Effort estimates
   - Dependencies

5. **`./audit/consolidated/implementation-roadmap.md`**
   - Phased implementation plan
   - Resource requirements
   - Risk mitigation

---

## COMPLETION

When all phases complete:

```bash
echo "=== AUDIT COMPLETE ===" | tee -a ./audit/logs/audit.log
echo "Completed at $(date)" >> ./audit/logs/audit.log

# Summary
echo ""
echo "=============================================="
echo "  AUDIT COMPLETE"
echo "=============================================="
echo ""
echo "Results saved to: ./audit/"
echo ""
echo "Key deliverables:"
echo "  - ./audit/consolidated/V2-SPECIFICATION-INPUTS.md"
echo "  - ./audit/consolidated/EXECUTIVE-SUMMARY.md"
echo "  - ./audit/consolidated/FULL-AUDIT-REPORT.md"
echo ""
echo "Individual findings: ./audit/findings/"
echo "Individual reports: ./audit/reports/"
echo "Logs: ./audit/logs/"
echo ""
```

**Present the consolidated files to the user for download.**

---

## ERROR RECOVERY

If any phase fails:
1. Log the error
2. Save partial results
3. Continue with next agent
4. Report failures in final summary

Never stop completely - always produce partial results.
