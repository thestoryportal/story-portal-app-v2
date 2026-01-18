# Quick Start Guide

## 5-Minute Setup

### 1. Install Claude Code CLI

**Mac:**
```bash
brew install anthropic/tap/claude-code
```

**Windows:**
```powershell
winget install Anthropic.ClaudeCode
```

**Linux:**
```bash
curl -fsSL https://claude.ai/install.sh | sh
```

### 2. Login (first time only)

```bash
claude login
```

### 3. Navigate to your project

```bash
cd /path/to/story-portal-app-v2
```

### 4. Run the audit

```bash
claude --print "$(cat audit-package/MASTER-AUDIT-PROMPT.md)"
```

### 5. Find results

```
audit/consolidated/V2-SPECIFICATION-INPUTS.md  ← Main output
```

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| "claude: command not found" | Install Claude Code CLI (step 1) |
| "file not found" | Navigate to story-portal-app-v2 root (step 3) |
| "cannot connect to postgres" | Run `docker start agentic-postgres` |
| "cannot connect to redis" | Run `docker start agentic-redis` |

---

## Pre-Flight Check

```bash
# Verify everything is ready
./audit-package/scripts/setup.sh
```

---

## Duration

Full audit: **4-6 hours** (runs autonomously)

You can leave it running and check back later.
