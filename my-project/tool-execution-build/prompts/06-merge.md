# Session: Tool Execution Layer -- Merge Specification

## Objective
Combine specification parts using CONCATENATION-FIRST protocol. Do NOT read and rewrite content.

## Source Files
1. `tool-execution-spec-part1.md`
2. `tool-execution-spec-part2.md`
3. `tool-execution-spec-part3.md`

## Checkpoint Protocol

**Exchange limit:** 6 exchanges for this session

**Checkpoint triggers:**
- After pre-merge metrics recorded
- After Stage 1 (concatenation)
- After Stages 2-3 (structure and cleanup)
- After post-merge validation

**At each checkpoint:**
1. Report current state
2. PAUSE - wait for "Continue"

## Why Concatenation-First?

| Merge Approach | Content Loss Risk | Outcome |
|----------------|------------------|---------|
| LLM "intelligent" merge | 35-60% | **UNACCEPTABLE** |
| Concatenation-first | 0% | Required approach |

## Pre-Merge: Record Source Metrics

Count lines in each source file BEFORE any merge operations:

| File | Lines |
|------|-------|
| Part 1 | [count] |
| Part 2 | [count] |
| Part 3 | [count] |
| **EXPECTED MINIMUM** | **[sum]** |


---

## Merge Execution

### Stage 1: Direct File Concatenation

Execute raw file concatenation using bash:

cat tool-execution-spec-part1.md \
    tool-execution-spec-part2.md \
    tool-execution-spec-part3.md > tool-execution-merged-raw.md

Verify immediately:
wc -l tool-execution-merged-raw.md
# MUST be >= EXPECTED MINIMUM


---

### Stage 2: Additive-Only Edits

PREPEND to merged-raw.md (do not modify existing content):
1. Document header with version 1.0.0
2. Unified Table of Contents (generated from actual section headers)

APPEND to merged-raw.md (do not modify existing content):
3. Version history entry

### Stage 3: Duplicate Header Removal (ONLY)

Remove ONLY these duplicates from the merged file:
- Duplicate document headers from Parts 2 and 3
- Duplicate metadata tables from Parts 2 and 3

**DO NOT REMOVE:**
- Any section content
- Any code blocks
- Any diagrams
- Any tables within sections


---

## Post-Merge Validation

### Verification Checklist
| Check | Expected | Actual | Status |
|-------|----------|--------|--------|
| Total lines | >= [EXPECTED MINIMUM] | [count] | [PASS/FAIL] |
| Section count | 15 | [count] | [PASS/FAIL] |
| Code blocks | >= [sum from parts] | [count] | [PASS/FAIL] |
| ASCII diagrams | >= [sum from parts] | [count] | [PASS/FAIL] |
| Phase 15 references | >= 5 | [count] | [PASS/FAIL] |
| Phase 16 references | >= 5 | [count] | [PASS/FAIL] |
| ADR references | >= 4 | [count] | [PASS/FAIL] |

### Failure Conditions
If ANY of these occur, the merge has **FAILED**:
1. output_lines < sum(source_lines) -- Content was lost
2. Section count < 15 -- Sections were dropped
3. Fewer code blocks than sources -- Code was lost
4. Fewer diagrams than sources -- Diagrams were lost

### Failure Response
1. STOP immediately
2. Discard merged output
3. Report which validation failed
4. Restart from Stage 1 with fresh concatenation

## Output
Save as: `tool-execution-layer-specification-v1.0-ASCII.md`

Report final metrics:
- Source content: [X] lines total
- Final document: [Y] lines
- Added content: [Y-X] lines (should be +100 to +200)
- Content preserved: 100%

## KB Management

### Add to This Project KB
| File | Purpose |
|------|---------|
| `tool-execution-layer-specification-v1.0-ASCII.md` | Merged spec for validation |

### Remove from This Project KB
| File | Reason |
|------|--------|
| `tool-execution-spec-part1.md` | Merged into v1.0 |
| `tool-execution-spec-part2.md` | Merged into v1.0 |
| `tool-execution-spec-part3.md` | Merged into v1.0 |

### Verification
- [ ] Line count >= sum of parts
- [ ] All 15 sections present
- [ ] ASCII encoding verified
- [ ] Phase 15/16 integration preserved
- [ ] Part files removed from KB
