# Session: Tool Execution Layer -- Gap Analysis

## Objective
Analyze research findings against Data Layer patterns, Agent Runtime interface, Phase 15/16 integration, and layer definition to identify gaps, validate technology choices, and prepare for specification writing.

## Source Files in Project Knowledge
1. `tool-execution-research-findings.md` (from Session B.1)
2. `agentic-data-layer-master-specification-v4.0-final-ASCII.md` (reference architecture)
3. `agent-runtime-layer-specification-v1.2-final-ASCII.md` (sandbox interface)
4. `phase-15-document-management-specification-v1.0-ASCII.md` (document context)
5. `phase-16-session-orchestration-specification-v1.0-ASCII.md` (state persistence)
6. Layer definition from project instructions

## Checkpoint Protocol

**Exchange limit:** 8 exchanges for this session

**Checkpoint triggers:**
- After each task (9 tasks total)
- When context estimate exceeds 60%

**At each checkpoint:**
1. Save completed tasks to file
2. Report: Task [X] complete, [Y] remaining
3. PAUSE - wait for "Continue"

## Tasks

### Task 1: Classify Research Findings
Review each finding and classify as:
- **APPLICABLE**: Should be specified in this layer
- **OTHER LAYER**: Belongs to a different layer (note which)
- **OUT OF SCOPE**: Not needed for agent workforce
- **DEFER**: Valid but lower priority for v1.0

Output as table:
| Finding | Classification | Target Component | Notes |


---

### Task 2: Data Layer Integration Requirements
Analyze what Tool Execution needs from Data Layer:

| Integration Point | Direction | Data Layer Component | Tool Execution Usage |
|-------------------|-----------|---------------------|----------------------|
| Event Publishing | L03 -> L01 | Event Store | tool.invoked, tool.succeeded, tool.failed events |
| Permission Query | L03 -> L01 | ABAC Engine | Validate agent capabilities for tool access |
| Context Retrieval | L03 <- L01 | Context Injector | Tool-specific credentials and config |
| Audit Logging | L03 -> L01 | Audit Log | Compliance records for tool invocations |
| MCP Integration | L03 <-> L01 | Tool Registry (Phase 13) | MCP tool adapter patterns |

Document each integration pattern (event, API, shared storage).


---

### Task 3: Agent Runtime Integration Requirements
Map the BC-1 nested sandbox interface:

| Interface | L02 Provides | L03 Consumes |
|-----------|--------------|--------------|
| Sandbox Context | Agent DID, resource limits, network policy | Parent sandbox for tool isolation |
| Resource Bounds | CPU/memory/time limits per agent | Inherited limits for tool execution |
| Network Policy | Agent-level allowed connections | Base network restrictions |
| Tool Invocation | L02 calls L03.tool.invoke() | Execute tools on agent behalf |


---

### Task 4: Phase 15 Document Management Integration
Map document context requirements:

| Integration Point | Direction | MCP Tool | L03 Usage |
|-------------------|-----------|----------|-----------|
| Document Query | L03 -> MCP | get_source_of_truth | Retrieve authoritative content during execution |
| Overlap Detection | L03 -> MCP | find_overlaps | Validate tool inputs against corpus |
| Metadata Access | L03 -> MCP | get_document_metadata | Audit trail for document-dependent outputs |

**Document Bridge Design Questions:**
- Caching strategy for repeated queries?
- Error handling for MCP service unavailability?
- Document version pinning during long-running tools?


---

### Task 5: Phase 16 Session Orchestration Integration
Map state persistence requirements:

| Integration Point | Direction | MCP Tool | L03 Usage |
|-------------------|-----------|----------|-----------|
| Checkpoint Creation | L03 -> MCP | save_context_snapshot | Persist tool progress |
| Named Checkpoints | L03 -> MCP | create_checkpoint | Named recovery points |
| State Restoration | L03 <- MCP | restore_from_checkpoint | Resume interrupted execution |
| Session Context | L03 <- MCP | get_session_context | Access session state |

**State Bridge Design Questions:**
- Checkpoint granularity (per-phase vs continuous)?
- State serialization format?
- Cleanup policy for completed tool checkpoints?


---

### Task 6: Dependent Layer Requirements
Map what L11 (Integration) will need from Tool Execution:

| Consuming Layer | Required Interface | Data Exchanged |
|-----------------|-------------------|----------------|
| L11 Integration | `tool.invoke()` | ToolInvokeRequest -> ToolInvokeResponse |

Document the BC-2 interface contract completely including new Phase 15/16 fields.


---

### Task 7: Component Coverage Analysis
For each Tool Execution component, assess research coverage:

| Component | Research Coverage | Gaps Identified |
|-----------|------------------|-----------------|
| Tool Registry | [Coverage assessment] | [Gaps] |
| Tool Executor | [Coverage assessment] | [Gaps] |
| Permission Checker | [Coverage assessment] | [Gaps] |
| External Adapter Manager | [Coverage assessment] | [Gaps] |
| Circuit Breaker Controller | [Coverage assessment] | [Gaps] |
| Result Validator | [Coverage assessment] | [Gaps] |
| Document Bridge (Phase 15) | [Coverage assessment] | [Gaps] |
| State Bridge (Phase 16) | [Coverage assessment] | [Gaps] |


---

### Task 8: Open Question Resolution
Evaluate whether research addresses the open questions:

| Question | Research Answer | Confidence | Section Target |
|----------|-----------------|------------|----------------|
| Q1: Tool versioning (independent vs agent-tied)? | [Answer] | [High/Medium/Low] | Section 3 |
| Q2: Long-running operations (>30s)? | [Answer] | [High/Medium/Low] | Section 7 |
| Q3: Credential rotation during invocations? | [Answer] | [High/Medium/Low] | Section 8 |
| Q4: MCP tool adapter pattern? | [Answer] | [High/Medium/Low] | Section 6 |
| Q5: Phase 15 document context caching? | [Answer] | [High/Medium/Low] | Section 6 |
| Q6: Phase 16 checkpoint granularity? | [Answer] | [High/Medium/Low] | Section 7 |
| Q7: Redis vs PostgreSQL for circuit breaker? | [Answer] | [High/Medium/Low] | Section 3 |


---

### Task 9: Gap Summary and Prioritization
Compile all gaps with severity ratings:

**IMPORTANT:** All gaps will be integrated into the specification. Prioritization is for ordering within sections, NOT for deciding what to include or exclude.

| Gap ID | Description | Priority | Target Section |
|--------|-------------|----------|----------------|
| G-001 | [Description] | Critical/High/Medium/Low | [Section] |

## Specification Preparation
Document decisions for specification writing:

**Technology Decisions:**
| Decision | Choice | Rationale |
|----------|--------|-----------|
| Tool Registry Storage | PostgreSQL + pgvector | Per ADR-002, vector search for capability matching |
| Circuit Breaker State | Redis | Per ADR-002, distributed state with TTL |
| MCP Transport | stdio | Per ADR-001, JSON-RPC over stdio |

**Patterns to Specify:**
| Pattern | Source | Application |
|---------|--------|-------------|

**Standards to Reference:**
| Standard | Sections | How Used |
|----------|----------|----------|

## Deliverable
Output as: `tool-execution-gap-analysis.md`

## KB Management

### Add to This Project KB
| File | Purpose |
|------|---------|
| `tool-execution-gap-analysis.md` | Gap tracking for specification |

### Verification
- [ ] All research findings classified
- [ ] Data Layer integration points mapped
- [ ] Agent Runtime interface documented (BC-1)
- [ ] Phase 15 Document Bridge integration mapped
- [ ] Phase 16 State Bridge integration mapped
- [ ] Integration Layer interface documented (BC-2)
- [ ] All gaps have target sections assigned
- [ ] File added to KB before C.1
