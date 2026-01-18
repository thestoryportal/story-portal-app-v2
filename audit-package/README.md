# Story Portal Platform - Complete Audit Package

## What This Does

This package runs a comprehensive audit of the Story Portal App v2 platform. It checks:
- All services (PostgreSQL, Redis, Ollama, application layers)
- Security configurations and vulnerabilities
- Code quality and test coverage
- Database integrity and performance
- API endpoints and integrations
- Docker containers and infrastructure
- And 20+ more audit categories

**Output:** A complete audit report ready to use for V2 specification development.

---

## Before You Start - Requirements

You need these things installed on your computer:

| Requirement | How to Check | How to Install |
|-------------|--------------|----------------|
| Claude Code CLI | Type `claude --version` in terminal | See Step 1 below |
| Git | Type `git --version` in terminal | https://git-scm.com/downloads |
| Docker | Type `docker --version` in terminal | https://docker.com/get-started |

---

## Step-by-Step Instructions

### Step 1: Install Claude Code CLI (if not already installed)

**On Mac:**
```bash
brew install anthropic/tap/claude-code
```

**On Windows (PowerShell as Administrator):**
```powershell
winget install Anthropic.ClaudeCode
```

**On Linux:**
```bash
curl -fsSL https://claude.ai/install.sh | sh
```

**Verify it worked:**
```bash
claude --version
```
You should see a version number like `1.0.0` or similar.

---

### Step 2: Set Up Claude Code (First Time Only)

If this is your first time using Claude Code, you need to log in:

```bash
claude login
```

This opens a web browser. Log in with your Claude account.

---

### Step 3: Download This Audit Package

**Option A: If you received this as a ZIP file:**
1. Unzip the file to a location you can remember
2. Open Terminal (Mac/Linux) or Command Prompt (Windows)
3. Navigate to the unzipped folder:
   ```bash
   cd /path/to/audit-package
   ```

**Option B: Copy from your repository:**
```bash
# Navigate to your story-portal-app-v2 folder
cd /path/to/story-portal-app-v2

# Create the audit-package folder if it doesn't exist
mkdir -p audit-package

# Copy the audit package files there
# (Or extract the ZIP into this location)
```

---

### Step 4: Navigate to Your Platform Directory

The audit runs FROM your platform directory. Open Terminal and type:

```bash
cd /path/to/story-portal-app-v2
```

**Replace `/path/to/` with the actual path to your project.**

**Example paths:**
- Mac: `cd ~/Documents/story-portal-app-v2`
- Windows: `cd C:\Users\YourName\Documents\story-portal-app-v2`
- Linux: `cd /home/yourname/projects/story-portal-app-v2`

**To verify you're in the right place:**
```bash
ls -la
```
You should see folders like `platform/`, `audit-package/`, etc.

---

### Step 5: Make Sure Docker Services Are Running

The audit needs PostgreSQL, Redis, and Ollama running. Check their status:

```bash
docker ps
```

You should see containers like `agentic-postgres` and `agentic-redis`.

**If they're not running, start them:**
```bash
docker-compose up -d
```

Or if you don't have docker-compose:
```bash
docker start agentic-postgres agentic-redis
```

---

### Step 6: Run the Audit (THE MAIN STEP)

This is where the magic happens. Type this ONE command:

```bash
claude --print "$(cat audit-package/MASTER-AUDIT-PROMPT.md)"
```

**What happens next:**
1. Claude reads the audit instructions
2. Claude runs all 25 audit agents automatically
3. Claude saves results to the `audit/` folder
4. Claude creates a final consolidated report

**This takes approximately 4-6 hours to complete.**

You can leave it running and come back later.

---

### Step 7: Find Your Results

When the audit completes, your results are in:

```
story-portal-app-v2/
  audit/
    findings/           <- Individual agent findings (JSON)
    reports/            <- Individual agent reports (Markdown)
    consolidated/       <- MAIN OUTPUT - Use these files
      V2-SPECIFICATION-INPUTS.md     <- Start here!
      EXECUTIVE-SUMMARY.md
      FULL-AUDIT-REPORT.md
      priority-matrix.md
      implementation-roadmap.md
```

**Your main deliverable is:** `audit/consolidated/V2-SPECIFICATION-INPUTS.md`

---

## Troubleshooting

### "claude: command not found"
Claude Code CLI is not installed. Go back to Step 1.

### "Permission denied"
On Mac/Linux, you may need to make scripts executable:
```bash
chmod +x audit-package/scripts/*.sh
```

### "Cannot connect to PostgreSQL"
Make sure Docker is running:
```bash
docker ps
```
If no containers shown:
```bash
docker-compose up -d
```

### "Cannot connect to Ollama"
Start Ollama:
```bash
ollama serve &
```

### Audit stops midway
You can resume! The audit saves checkpoints. Just run Step 6 again.

### "No such file or directory: audit-package/MASTER-AUDIT-PROMPT.md"
You're not in the right directory. Make sure you:
1. Are in the `story-portal-app-v2` folder (not inside `audit-package`)
2. The `audit-package` folder exists and contains `MASTER-AUDIT-PROMPT.md`

---

## Quick Reference Commands

| What You Want | Command |
|---------------|---------|
| Check Claude is installed | `claude --version` |
| Start the audit | `claude --print "$(cat audit-package/MASTER-AUDIT-PROMPT.md)"` |
| Check Docker containers | `docker ps` |
| Start Docker services | `docker-compose up -d` |
| View audit progress | `ls -la audit/findings/` |
| View final report | `cat audit/consolidated/V2-SPECIFICATION-INPUTS.md` |

---

## Files in This Package

```
audit-package/
  README.md                    <- You are here
  MASTER-AUDIT-PROMPT.md       <- The main audit prompt (Step 6)
  agents/                      <- Individual agent definitions
    AUD-001-orchestrator.md
    AUD-002-security.md
    ... (25 agents total)
  scripts/
    setup.sh                   <- Optional: setup script
    health-check.sh            <- Check if services are running
  config/
    audit-config.yaml          <- Audit configuration
  templates/
    finding-template.json      <- Template for findings
    report-template.md         <- Template for reports
  docs/
    agent-catalog.md           <- List of all agents
    output-formats.md          <- Explanation of output files
```

---

## Getting Help

If you encounter issues:

1. Check the Troubleshooting section above
2. Make sure all requirements are installed
3. Verify Docker services are running
4. Try running a simpler command first:
   ```bash
   claude "Hello, can you hear me?"
   ```
   If this works, Claude Code is set up correctly.

---

## Version Information

| Component | Version |
|-----------|---------|
| Audit Package | 1.0.0 |
| Target Platform | Story Portal App v2 (L00-L11) |
| Required Claude Code | 1.0.0+ |
| Last Updated | January 2026 |
