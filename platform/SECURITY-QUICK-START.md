# Security Scanning - Quick Start Guide

## Installation (One-Time Setup)

```bash
cd /Volumes/Extreme\ SSD/projects/story-portal-app/platform
pip install -r requirements-security.txt
```

## Quick Scan Commands

### Complete Security Scan (Recommended)
```bash
sp-cli security scan
```
Runs all scans and generates reports in Markdown, JSON, and HTML formats.

### Dependency Vulnerabilities Only
```bash
sp-cli security deps
```
Scans Python (pip-audit) and NPM (npm audit) dependencies.

### Static Code Analysis Only
```bash
sp-cli security bandit
```
Analyzes Python code for security issues using Bandit.

### Secret Detection Only
```bash
sp-cli security secrets
```
Scans codebase for accidentally committed secrets.

## Output Locations

All scan results are saved to:
```
platform/security-reports/
├── security-scan-YYYYMMDD-HHMMSS.md      # Markdown report
├── security-scan-YYYYMMDD-HHMMSS.json    # JSON report
└── security-scan-YYYYMMDD-HHMMSS.html    # HTML report
```

## Interpreting Results

### Severity Levels
- **CRITICAL**: Fix immediately before deployment
- **HIGH**: Fix within 7 days
- **MEDIUM**: Fix within 30 days
- **LOW**: Document and monitor

### Success Criteria
✅ Zero CRITICAL vulnerabilities
✅ Zero exposed secrets
✅ All HIGH issues have mitigation plan
✅ All findings documented

## Quick Remediation

### Update Vulnerable Dependency
```bash
# Check current version
pip show <package-name>

# Update to fixed version
pip install <package-name>==<fixed-version>

# Update requirements.txt
pip freeze | grep <package-name> >> requirements.txt
```

### Fix Bandit Finding
Review the code location in the report, then:
1. Apply recommended fix from Bandit documentation
2. Re-run scan to verify fix
3. Commit changes

### Remove Exposed Secret
1. Immediately rotate the exposed credential
2. Remove from version control history (if needed)
3. Add to .gitignore or use environment variables
4. Update documentation

## Automated Scanning

### Daily Scans (CI/CD)
Security scans run automatically:
- On every push to main branch
- On every pull request
- Daily at 2 AM UTC

### Manual Scans
Run before:
- Deploying to production
- Major version releases
- After adding new dependencies
- After security incidents

## Need Help?

- **Documentation**: `platform/SECURITY-SCAN-REPORT.md`
- **Scanner Code**: `platform/src/shared/security_scanner.py`
- **CLI Tool**: `platform/cli/sp-cli`

---

**Quick Reference Card**
```
┌─────────────────────────────────────────────────┐
│  Security Scanning Quick Reference              │
├─────────────────────────────────────────────────┤
│  Complete Scan:    sp-cli security scan         │
│  Dependencies:     sp-cli security deps         │
│  Code Analysis:    sp-cli security bandit       │
│  Secret Detection: sp-cli security secrets      │
│                                                  │
│  Reports Location: platform/security-reports/   │
│                                                  │
│  Zero CRITICAL before deployment ✅             │
└─────────────────────────────────────────────────┘
```

**Last Updated**: 2026-01-18
