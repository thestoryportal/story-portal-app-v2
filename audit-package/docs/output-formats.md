# Audit Output Formats

## Directory Structure

After a complete audit, the output directory contains:

```
audit/
├── findings/                    # Raw findings from each agent
│   ├── AUD-002-security.md
│   ├── AUD-003-qa.md
│   ├── AUD-004-database.md
│   ├── AUD-005-integration.md
│   ├── AUD-006-performance.md
│   ├── AUD-007-quality.md
│   ├── AUD-008-uiux.md
│   ├── AUD-009-devex.md
│   ├── AUD-010-services.md
│   ├── AUD-011-cli.md
│   ├── AUD-012-mcp.md
│   ├── AUD-013-config.md
│   ├── AUD-014-tokens.md
│   ├── AUD-015-redis.md
│   ├── AUD-016-api.md
│   ├── AUD-017-events.md
│   ├── AUD-018-errors.md
│   ├── AUD-019-docker.md
│   ├── AUD-020-llm.md
│   ├── AUD-021-postgres.md
│   ├── AUD-022-observability.md
│   ├── AUD-023-network.md
│   ├── AUD-024-backup.md
│   └── AUD-025-external.md
│
├── reports/                     # Analyzed reports with recommendations
│   ├── AUD-002-security.md
│   ├── AUD-003-qa-coverage.md
│   └── ... (one per agent)
│
├── logs/                        # Execution logs
│   ├── audit.log               # Main audit log
│   ├── AUD-002.log             # Per-agent logs
│   └── consolidation.log
│
├── checkpoints/                 # Checkpoint data
│   ├── initial-state.txt
│   └── platform-structure.txt
│
├── evidence/                    # Supporting evidence files
│   └── (command outputs, screenshots)
│
└── consolidated/                # MAIN OUTPUT
    ├── V2-SPECIFICATION-INPUTS.md    # ← START HERE
    ├── EXECUTIVE-SUMMARY.md
    ├── FULL-AUDIT-REPORT.md
    ├── priority-matrix.md
    └── implementation-roadmap.md
```

---

## Key Deliverables

### 1. V2-SPECIFICATION-INPUTS.md

**Purpose:** Primary input document for V2 specification development.

**Structure:**
- Infrastructure requirements
- Security requirements
- Data layer requirements
- API & integration requirements
- Quality & testing requirements
- UX & DevEx requirements
- Service discovery findings
- External dependencies
- Priority matrix
- Implementation roadmap

**Use this to:** Start writing V2 layer specifications.

---

### 2. EXECUTIVE-SUMMARY.md

**Purpose:** Quick overview for stakeholders.

**Contains:**
- Finding counts by severity
- Service health status
- Top 10 priority issues
- Key metrics

**Use this to:** Brief leadership or make go/no-go decisions.

---

### 3. FULL-AUDIT-REPORT.md

**Purpose:** Complete detailed audit record.

**Contains:**
- All findings with full details
- Evidence references
- Complete recommendations

**Use this to:** Deep-dive into specific issues.

---

### 4. priority-matrix.md

**Purpose:** Prioritized action list.

**Contains:**
- All findings sorted by P1 → P4
- Effort estimates
- Dependencies

**Use this to:** Plan sprint work.

---

### 5. implementation-roadmap.md

**Purpose:** Phased implementation plan.

**Contains:**
- Week-by-week breakdown
- Resource requirements
- Risk mitigation

**Use this to:** Create project timeline.

---

## Finding Format

Each finding follows this structure:

```markdown
### [ID]: [Title]

**Severity:** Critical | High | Medium | Low
**Category:** Security | Performance | Reliability | Quality
**Component:** [Affected layer/component]

**Description:**
[What was found]

**Evidence:**
[Command output or observation]

**Impact:**
[What happens if not fixed]

**Recommendation:**
[How to fix]

**Effort:** S | M | L | XL
```

---

## Severity Definitions

| Severity | Criteria | Examples |
|----------|----------|----------|
| Critical | Security vulnerability, production blocker | SQL injection, exposed secrets |
| High | Reliability risk, significant gap | No backup strategy, missing auth |
| Medium | Best practice violation | No type hints, missing tests |
| Low | Enhancement opportunity | Documentation gaps |

---

## Priority Mapping

| Priority | Severity + Category | Response |
|----------|---------------------|----------|
| P1 | Critical + Security | Immediate |
| P2 | High + Reliability | Week 1 |
| P3 | Medium + Functionality | Week 2-4 |
| P4 | Low + Enhancement | Backlog |

---

## Using the Output

### For V2 Specification Development

1. Open `./audit/consolidated/V2-SPECIFICATION-INPUTS.md`
2. Review each requirements section
3. Cross-reference with existing layer specifications
4. Identify gaps between current state and desired V2 state
5. Create specification updates for each layer

### For Sprint Planning

1. Open `./audit/consolidated/priority-matrix.md`
2. Filter by priority (P1 first)
3. Assign to sprints based on effort
4. Track using `status` field

### For Stakeholder Reporting

1. Open `./audit/consolidated/EXECUTIVE-SUMMARY.md`
2. Present severity distribution
3. Highlight top 10 issues
4. Share implementation roadmap
