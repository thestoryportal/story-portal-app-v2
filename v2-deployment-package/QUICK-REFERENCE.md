# V2 Deployment - Quick Reference

## ONE COMMAND TO DEPLOY

```bash
./v2-deployment-package/run-deploy.sh
```

---

## PREREQUISITES

| Requirement | Check Command | Install |
|-------------|---------------|---------|
| Claude Code | `claude --version` | `brew install anthropic/tap/claude-code` |
| Docker | `docker --version` | https://docker.com |
| Ollama | `ollama --version` | https://ollama.ai |

---

## AFTER DEPLOYMENT

| Action | Command/URL |
|--------|-------------|
| Check status | `./platform-cli/portal status` |
| Dashboard | http://localhost:8010 |
| Grafana | http://localhost:3000 (admin/admin) |
| List agents | `./platform-cli/portal agents` |
| List models | `./platform-cli/portal models` |
| View logs | `docker-compose -f docker-compose.v2.yml logs` |
| Stop all | `docker-compose -f docker-compose.v2.yml down` |
| Start all | `docker-compose -f docker-compose.v2.yml up -d` |
| Backup | `./scripts/backup/backup-all.sh` |

---

## SERVICE PORTS

| Service | Port |
|---------|------|
| L01 Data Layer | 8001 |
| L02 Runtime | 8002 |
| L03 Tool Execution | 8003 |
| L04 Model Gateway | 8004 |
| L05 Planning | 8005 |
| L06 Evaluation | 8006 |
| L07 Learning | 8007 |
| L09 API Gateway | 8009 |
| L10 Human Interface | 8010 |
| L11 Integration | 8011 |
| Prometheus | 9090 |
| Grafana | 3000 |
| PostgreSQL | 5432 |
| Redis | 6379 |
| Ollama | 11434 |

---

## TROUBLESHOOTING

| Problem | Solution |
|---------|----------|
| Permission denied | `chmod +x ./v2-deployment-package/run-deploy.sh` |
| Docker not running | Start Docker Desktop |
| Ollama not running | Run `ollama serve` in separate terminal |
| Port in use | Stop conflicting service |
| Check logs | `cat ./v2-deployment/logs/deployment.log` |
