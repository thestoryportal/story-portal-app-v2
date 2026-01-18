# Story Portal Platform V2 - One-Command Deployment

## What This Does

This package deploys the complete Story Portal Platform V2 to your local development environment:

- Starts all infrastructure (PostgreSQL, Redis, Ollama)
- Deploys all 10 application layers (L01-L11)
- Creates CLI tools for platform management
- Deploys a 5-agent development swarm
- Sets up monitoring (Prometheus + Grafana)
- Configures automated backups

**Estimated time:** 45-90 minutes (runs autonomously)

---

## Before You Start

You need these installed:

| Requirement | How to Check | How to Install |
|-------------|--------------|----------------|
| Claude Code CLI | `claude --version` | See Step 1 below |
| Docker | `docker --version` | https://docker.com/get-started |
| Ollama | `ollama --version` | https://ollama.ai/download |

---

## Step-by-Step Instructions

### Step 1: Install Claude Code CLI (if needed)

**Mac:**
```bash
brew install anthropic/tap/claude-code
```

**Windows (PowerShell as Admin):**
```powershell
winget install Anthropic.ClaudeCode
```

**Linux:**
```bash
curl -fsSL https://claude.ai/install.sh | sh
```

### Step 2: Start Docker

Make sure Docker Desktop is running (you should see the whale icon in your menu bar/system tray).

### Step 3: Start Ollama

Open a terminal and run:
```bash
ollama serve
```

Leave this terminal open. Ollama needs to keep running.

### Step 4: Navigate to Your Project

Open a NEW terminal window and type:
```bash
cd /path/to/story-portal-app-v2
```

**Replace `/path/to/` with your actual project location.**

Examples:
- Mac: `cd ~/Documents/story-portal-app-v2`
- Windows: `cd C:\Users\YourName\Documents\story-portal-app-v2`

### Step 5: Run the Deployment (ONE COMMAND)

```bash
./v2-deployment-package/run-deploy.sh
```

**That's it!** The deployment runs automatically. Come back in 45-90 minutes.

---

## What Happens During Deployment

The script automatically:

1. ✓ Verifies PostgreSQL, Redis, Ollama are running
2. ✓ Runs database migrations
3. ✓ Creates Docker configuration for all services
4. ✓ Starts all 10 application layers
5. ✓ Creates the `portal` CLI tool
6. ✓ Deploys 5 development agents
7. ✓ Sets up Prometheus + Grafana monitoring
8. ✓ Creates backup scripts
9. ✓ Generates deployment report

---

## After Deployment Completes

### Check Status
```bash
./platform-cli/portal status
```

### View Dashboard
Open your browser to: http://localhost:8010

### View Monitoring
- Grafana: http://localhost:3000 (username: admin, password: admin)
- Prometheus: http://localhost:9090

### List Deployed Agents
```bash
./platform-cli/portal agents
```

### List Available LLM Models
```bash
./platform-cli/portal models
```

---

## Quick Reference

| What You Want | Command |
|---------------|---------|
| Check all services | `./platform-cli/portal status` |
| View dashboard | Open http://localhost:8010 |
| List agents | `./platform-cli/portal agents` |
| List models | `./platform-cli/portal models` |
| View logs | `docker-compose -f docker-compose.v2.yml logs` |
| Stop everything | `docker-compose -f docker-compose.v2.yml down` |
| Start everything | `docker-compose -f docker-compose.v2.yml up -d` |
| Run backup | `./scripts/backup/backup-all.sh` |

---

## Troubleshooting

### "Permission denied" when running script
```bash
chmod +x ./v2-deployment-package/run-deploy.sh
```

### "Docker not running"
Start Docker Desktop from your Applications folder.

### "Ollama not running"
Open a terminal and run: `ollama serve`

### Services won't start
Check Docker is running:
```bash
docker ps
```

### Port already in use
Stop the conflicting service or change the port in `docker-compose.v2.yml`.

### Deployment fails partway
Check the logs:
```bash
cat ./v2-deployment/logs/deployment.log
```

Then restart:
```bash
./v2-deployment-package/run-deploy.sh
```

---

## Files Created

After deployment, you'll have:

```
story-portal-app-v2/
├── docker-compose.v2.yml      <- Service orchestration
├── platform/
│   └── .env                   <- Environment config
├── platform-cli/
│   └── portal                 <- CLI tool
├── scripts/
│   └── backup/                <- Backup scripts
└── v2-deployment/
    ├── logs/                  <- Deployment logs
    ├── reports/               <- Status reports
    └── configs/               <- Generated configs
```

---

## Getting Help

1. Check `./v2-deployment/logs/deployment.log` for errors
2. Run `./platform-cli/portal status` to see service health
3. Check Docker logs: `docker-compose -f docker-compose.v2.yml logs`

---

**Version:** 1.0.0
**Platform:** Story Portal V2 (L00-L11 Architecture)
**Last Updated:** January 2026
