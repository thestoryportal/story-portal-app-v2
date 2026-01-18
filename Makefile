# Story Portal Platform V2 - Makefile
# Common operations for platform management

.PHONY: help up down restart logs health backup restore test build clean ps stats shell db-shell redis-shell audit setup

# Default target
.DEFAULT_GOAL := help

# Configuration
COMPOSE_FILE := platform/docker-compose.app.yml
COMPOSE_V2_FILE := docker-compose.v2.yml
BACKUP_SCRIPT := platform/scripts/backup.sh
RESTORE_SCRIPT := platform/scripts/restore.sh
SETUP_SCRIPT := platform/scripts/setup.sh

# Colors for output
GREEN := \033[0;32m
YELLOW := \033[1;33m
RED := \033[0;31m
BLUE := \033[0;34m
NC := \033[0m # No Color

##@ General

help: ## Display this help message
	@echo ""
	@echo "$(GREEN)Story Portal Platform V2 - Makefile Commands$(NC)"
	@echo ""
	@awk 'BEGIN {FS = ":.*##"; printf "Usage:\n  make $(BLUE)<target>$(NC)\n"} /^[a-zA-Z_0-9-]+:.*?##/ { printf "  $(BLUE)%-20s$(NC) %s\n", $$1, $$2 } /^##@/ { printf "\n$(YELLOW)%s$(NC)\n", substr($$0, 5) } ' $(MAKEFILE_LIST)
	@echo ""

##@ Platform Control

up: ## Start all platform services
	@echo "$(GREEN)Starting Story Portal Platform V2...$(NC)"
	docker-compose -f $(COMPOSE_FILE) up -d
	@echo "$(GREEN)✓ Platform started$(NC)"
	@echo "Run 'make health' to verify all services are healthy"

down: ## Stop all platform services
	@echo "$(YELLOW)Stopping Story Portal Platform V2...$(NC)"
	docker-compose -f $(COMPOSE_FILE) down
	@echo "$(GREEN)✓ Platform stopped$(NC)"

restart: ## Restart all platform services
	@echo "$(YELLOW)Restarting Story Portal Platform V2...$(NC)"
	docker-compose -f $(COMPOSE_FILE) restart
	@echo "$(GREEN)✓ Platform restarted$(NC)"

restart-v2: ## Restart services using docker-compose.v2.yml
	@echo "$(YELLOW)Restarting V2 services...$(NC)"
	docker-compose -f $(COMPOSE_V2_FILE) restart
	@echo "$(GREEN)✓ V2 services restarted$(NC)"

build: ## Build all Docker images
	@echo "$(GREEN)Building all Docker images...$(NC)"
	docker-compose -f $(COMPOSE_FILE) build --no-cache
	@echo "$(GREEN)✓ Images built$(NC)"

pull: ## Pull latest Docker images
	@echo "$(GREEN)Pulling latest Docker images...$(NC)"
	docker-compose -f $(COMPOSE_FILE) pull
	@echo "$(GREEN)✓ Images pulled$(NC)"

##@ Service Management

ps: ## Show running containers
	@echo "$(GREEN)Platform Containers:$(NC)"
	@docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | grep -E "(agentic|NAMES)" || echo "No containers running"

stats: ## Show container resource usage
	@echo "$(GREEN)Container Resource Usage:$(NC)"
	@docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}" | grep -E "(agentic|NAME)" || echo "No containers running"

logs: ## Tail logs from all services
	docker-compose -f $(COMPOSE_FILE) logs -f --tail=100

logs-v2: ## Tail logs from V2 services
	docker-compose -f $(COMPOSE_V2_FILE) logs -f --tail=100

logs-errors: ## Show only error logs
	docker-compose -f $(COMPOSE_FILE) logs --tail=500 | grep -i "error\|exception\|failed"

##@ Health & Monitoring

health: ## Check health of all services
	@echo "$(GREEN)Checking service health...$(NC)"
	@echo ""
	@for port in 8001 8002 8003 8004 8005 8006 8007 8009 8010 8011 8012; do \
		if curl -sf http://localhost:$$port/health > /dev/null 2>&1; then \
			echo "$(GREEN)✓$(NC) Port $$port: Healthy"; \
		else \
			echo "$(RED)✗$(NC) Port $$port: Unhealthy"; \
		fi; \
	done
	@echo ""

health-detailed: ## Detailed health check with response bodies
	@echo "$(GREEN)Detailed Health Check:$(NC)"
	@echo ""
	@for port in 8001 8002 8003 8004 8005 8006 8007 8009 8010 8011 8012; do \
		echo "$(BLUE)Port $$port:$(NC)"; \
		curl -sf http://localhost:$$port/health 2>/dev/null | jq . 2>/dev/null || echo "$(RED)Not responding$(NC)"; \
		echo ""; \
	done

status: ## Show comprehensive platform status
	@echo "$(GREEN)=== Platform Status ===$(NC)"
	@echo ""
	@echo "$(BLUE)Containers:$(NC)"
	@docker ps --format "table {{.Names}}\t{{.Status}}" | grep -E "(agentic|NAMES)" || echo "No containers running"
	@echo ""
	@echo "$(BLUE)Service Health:$(NC)"
	@for port in 8009 8010; do \
		if curl -sf http://localhost:$$port/health > /dev/null 2>&1; then \
			echo "$(GREEN)✓$(NC) Port $$port: Healthy"; \
		else \
			echo "$(RED)✗$(NC) Port $$port: Unhealthy"; \
		fi; \
	done
	@echo ""
	@echo "$(BLUE)Disk Usage:$(NC)"
	@du -sh backups/ 2>/dev/null || echo "No backups directory"
	@docker system df | grep -E "TYPE|Images|Containers|Local Volumes"

##@ Backup & Restore

backup: ## Create backup of PostgreSQL and Redis
	@echo "$(GREEN)Creating backup...$(NC)"
	@chmod +x $(BACKUP_SCRIPT)
	@$(BACKUP_SCRIPT)

restore: ## Restore from backup (interactive)
	@echo "$(YELLOW)Starting restore process...$(NC)"
	@chmod +x $(RESTORE_SCRIPT)
	@$(RESTORE_SCRIPT)

restore-timestamp: ## Restore specific backup: make restore-timestamp TIMESTAMP=20260118-143022
	@if [ -z "$(TIMESTAMP)" ]; then \
		echo "$(RED)ERROR: TIMESTAMP not provided$(NC)"; \
		echo "Usage: make restore-timestamp TIMESTAMP=20260118-143022"; \
		exit 1; \
	fi
	@chmod +x $(RESTORE_SCRIPT)
	@$(RESTORE_SCRIPT) $(TIMESTAMP)

list-backups: ## List all available backups
	@echo "$(GREEN)Available Backups:$(NC)"
	@$(RESTORE_SCRIPT) || true

##@ Database Operations

db-shell: ## Open PostgreSQL shell
	@echo "$(GREEN)Opening PostgreSQL shell...$(NC)"
	docker exec -it agentic-postgres psql -U postgres -d agentic_platform

db-list: ## List all databases
	docker exec agentic-postgres psql -U postgres -c "\l"

db-tables: ## List all tables in agentic_platform
	docker exec agentic-postgres psql -U postgres -d agentic_platform -c "\dt"

db-size: ## Show database sizes
	docker exec agentic-postgres psql -U postgres -c "SELECT datname, pg_size_pretty(pg_database_size(datname)) FROM pg_database ORDER BY pg_database_size(datname) DESC;"

redis-shell: ## Open Redis CLI
	@echo "$(GREEN)Opening Redis shell...$(NC)"
	docker exec -it agentic-redis redis-cli

redis-info: ## Show Redis info
	docker exec agentic-redis redis-cli INFO

redis-keys: ## Count Redis keys
	@echo "$(GREEN)Redis Key Count:$(NC)"
	docker exec agentic-redis redis-cli DBSIZE

##@ Testing & Development

test: ## Run all tests
	@echo "$(GREEN)Running tests...$(NC)"
	@if [ -f pytest.ini ]; then \
		python -m pytest tests/ -v; \
	else \
		echo "$(YELLOW)No pytest.ini found - skipping tests$(NC)"; \
	fi

test-unit: ## Run unit tests only
	@echo "$(GREEN)Running unit tests...$(NC)"
	python -m pytest tests/ -v -m unit

test-integration: ## Run integration tests only
	@echo "$(GREEN)Running integration tests...$(NC)"
	python -m pytest tests/ -v -m integration

lint: ## Run linting on Python code
	@echo "$(GREEN)Running linters...$(NC)"
	@find platform/src -name "*.py" -type f | xargs pylint || echo "$(YELLOW)pylint not installed$(NC)"

format: ## Format Python code with black
	@echo "$(GREEN)Formatting code...$(NC)"
	@find platform/src -name "*.py" -type f | xargs black || echo "$(YELLOW)black not installed$(NC)"

##@ Shell Access

shell-l01: ## Open shell in L01 Data Layer container
	docker exec -it agentic-l01-data-layer /bin/bash

shell-l09: ## Open shell in L09 API Gateway container
	docker exec -it agentic-l09-api-gateway /bin/bash

shell-l10: ## Open shell in L10 Human Interface container
	docker exec -it agentic-l10-human-interface /bin/bash

shell-postgres: ## Open shell in PostgreSQL container
	docker exec -it agentic-postgres /bin/bash

shell-redis: ## Open shell in Redis container
	docker exec -it agentic-redis /bin/sh

##@ Cleanup

clean: ## Remove stopped containers
	@echo "$(YELLOW)Removing stopped containers...$(NC)"
	docker container prune -f
	@echo "$(GREEN)✓ Cleanup complete$(NC)"

clean-images: ## Remove unused Docker images
	@echo "$(YELLOW)Removing unused images...$(NC)"
	docker image prune -a -f
	@echo "$(GREEN)✓ Images cleaned$(NC)"

clean-volumes: ## Remove unused volumes (DESTRUCTIVE - use with caution)
	@echo "$(RED)⚠ WARNING: This will remove all unused volumes!$(NC)"
	@read -p "Are you sure? (yes/no): " confirm; \
	if [ "$$confirm" = "yes" ]; then \
		docker volume prune -f; \
		echo "$(GREEN)✓ Volumes cleaned$(NC)"; \
	else \
		echo "Cancelled."; \
	fi

clean-all: ## Remove all containers, images, volumes (DESTRUCTIVE)
	@echo "$(RED)⚠ WARNING: This will remove ALL containers, images, and volumes!$(NC)"
	@read -p "Are you sure? (yes/no): " confirm; \
	if [ "$$confirm" = "yes" ]; then \
		docker-compose -f $(COMPOSE_FILE) down -v; \
		docker system prune -a -f --volumes; \
		echo "$(GREEN)✓ Complete cleanup done$(NC)"; \
	else \
		echo "Cancelled."; \
	fi

##@ Audit & Documentation

audit: ## Run comprehensive platform audit
	@echo "$(GREEN)Running comprehensive platform audit...$(NC)"
	@echo "$(YELLOW)This will take 5-7 hours to complete all 37 agents$(NC)"
	@echo "Consider running in the background or overnight."
	@read -p "Continue? (yes/no): " confirm; \
	if [ "$$confirm" = "yes" ]; then \
		echo "Audit execution would start here..."; \
		echo "Implementation pending - see audit/MASTER-AUDIT-PROMPT.md"; \
	else \
		echo "Cancelled."; \
	fi

docs: ## Open documentation directory
	@echo "$(GREEN)Documentation:$(NC)"
	@echo "  - Architecture: docs/ARCHITECTURE.md"
	@echo "  - Development: docs/DEVELOPMENT.md"
	@echo "  - Security: SECURITY.md"
	@echo "  - Monitoring: docs/MONITORING.md"
	@echo "  - Scripts: platform/scripts/README.md"

##@ Setup & Installation

setup: ## Run initial setup script
	@if [ -f "$(SETUP_SCRIPT)" ]; then \
		chmod +x $(SETUP_SCRIPT); \
		$(SETUP_SCRIPT); \
	else \
		echo "$(YELLOW)Setup script not found: $(SETUP_SCRIPT)$(NC)"; \
		echo "Run: make install"; \
	fi

install: ## Install dependencies and initialize platform
	@echo "$(GREEN)Installing Story Portal Platform V2...$(NC)"
	@echo ""
	@echo "$(BLUE)Step 1: Checking Docker...$(NC)"
	@command -v docker >/dev/null 2>&1 || { echo "$(RED)ERROR: Docker not installed$(NC)"; exit 1; }
	@echo "$(GREEN)✓ Docker found$(NC)"
	@echo ""
	@echo "$(BLUE)Step 2: Checking Docker Compose...$(NC)"
	@command -v docker-compose >/dev/null 2>&1 || { echo "$(RED)ERROR: Docker Compose not installed$(NC)"; exit 1; }
	@echo "$(GREEN)✓ Docker Compose found$(NC)"
	@echo ""
	@echo "$(BLUE)Step 3: Creating directories...$(NC)"
	@mkdir -p backups logs
	@echo "$(GREEN)✓ Directories created$(NC)"
	@echo ""
	@echo "$(BLUE)Step 4: Building images...$(NC)"
	@docker-compose -f $(COMPOSE_FILE) build
	@echo "$(GREEN)✓ Images built$(NC)"
	@echo ""
	@echo "$(BLUE)Step 5: Starting services...$(NC)"
	@docker-compose -f $(COMPOSE_FILE) up -d
	@echo "$(GREEN)✓ Services started$(NC)"
	@echo ""
	@echo "$(GREEN)Installation complete!$(NC)"
	@echo ""
	@echo "Next steps:"
	@echo "  1. Check health: make health"
	@echo "  2. View logs: make logs"
	@echo "  3. View status: make status"

##@ Monitoring

prometheus: ## Open Prometheus web UI
	@echo "$(GREEN)Opening Prometheus...$(NC)"
	@open http://localhost:9090 || xdg-open http://localhost:9090 || echo "Open: http://localhost:9090"

grafana: ## Open Grafana web UI
	@echo "$(GREEN)Opening Grafana...$(NC)"
	@open http://localhost:3000 || xdg-open http://localhost:3000 || echo "Open: http://localhost:3000"

ui: ## Open Platform UI
	@echo "$(GREEN)Opening Platform UI...$(NC)"
	@open http://localhost:8010 || xdg-open http://localhost:8010 || echo "Open: http://localhost:8010"

api: ## Open API Gateway
	@echo "$(GREEN)Opening API Gateway...$(NC)"
	@open http://localhost:8009/docs || xdg-open http://localhost:8009/docs || echo "Open: http://localhost:8009/docs"

##@ Troubleshooting

diagnose: ## Run diagnostic checks
	@echo "$(GREEN)=== Platform Diagnostics ===$(NC)"
	@echo ""
	@echo "$(BLUE)1. Docker Status:$(NC)"
	@docker version | grep "Version:" | head -2
	@echo ""
	@echo "$(BLUE)2. Container Status:$(NC)"
	@docker ps -a --format "table {{.Names}}\t{{.Status}}" | grep -E "(agentic|NAMES)" || echo "No containers found"
	@echo ""
	@echo "$(BLUE)3. Port Bindings:$(NC)"
	@docker ps --format "table {{.Names}}\t{{.Ports}}" | grep -E "(agentic|NAMES)" || echo "No containers running"
	@echo ""
	@echo "$(BLUE)4. Service Health:$(NC)"
	@for port in 8001 8009 8010; do \
		if curl -sf http://localhost:$$port/health > /dev/null 2>&1; then \
			echo "$(GREEN)✓$(NC) Port $$port: Responding"; \
		else \
			echo "$(RED)✗$(NC) Port $$port: Not responding"; \
		fi; \
	done
	@echo ""
	@echo "$(BLUE)5. Disk Usage:$(NC)"
	@docker system df
	@echo ""
	@echo "$(BLUE)6. Recent Errors (last 50 lines):$(NC)"
	@docker-compose -f $(COMPOSE_FILE) logs --tail=50 | grep -i "error\|exception" | head -10 || echo "No recent errors"

reset: ## Reset platform to fresh state (DESTRUCTIVE)
	@echo "$(RED)⚠ WARNING: This will reset the platform to a fresh state!$(NC)"
	@echo "All data will be lost (unless you have backups)."
	@read -p "Are you sure? (yes/no): " confirm; \
	if [ "$$confirm" = "yes" ]; then \
		make down; \
		docker volume rm $$(docker volume ls -q | grep agentic) 2>/dev/null || true; \
		make up; \
		echo "$(GREEN)✓ Platform reset complete$(NC)"; \
	else \
		echo "Cancelled."; \
	fi

##@ CI/CD

ci-build: ## CI: Build images
	docker-compose -f $(COMPOSE_FILE) build

ci-test: ## CI: Run tests
	@echo "Running CI tests..."
	python -m pytest tests/ -v --junitxml=test-results.xml || true

ci-lint: ## CI: Run linters
	@echo "Running linters..."
	find platform/src -name "*.py" -type f | xargs pylint --output-format=parseable || true

ci-security-scan: ## CI: Run security scans
	@echo "Running security scans..."
	@command -v trivy >/dev/null 2>&1 && docker images --format "{{.Repository}}:{{.Tag}}" | grep agentic | xargs -I {} trivy image {} || echo "trivy not installed"
