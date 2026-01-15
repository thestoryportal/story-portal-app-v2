# Session: Tool Execution Layer -- Specification Part 1

## Objective
Write specification Sections 1-5: Executive Summary, Scope, Architecture, Interfaces, Data Model.

Integrate ALL gap analysis findings targeted at these sections.

## Source Files in Project Knowledge
1. `tool-execution-research-findings.md`
2. `tool-execution-gap-analysis.md`
3. `agentic-data-layer-master-specification-v4.0-final-ASCII.md`
4. `agent-runtime-layer-specification-v1.2-final-ASCII.md`
5. `phase-15-document-management-specification-v1.0-ASCII.md`
6. `phase-16-session-orchestration-specification-v1.0-ASCII.md`
7. `layer-specification-template.md`

## Checkpoint Protocol

**Exchange limit:** 8 exchanges for this session

**Checkpoint triggers:**
- After each section (5 sections total)
- When context estimate exceeds 60%

**At each checkpoint:**
1. Save completed sections to file
2. Report: Section [X] complete, [Y] remaining
3. PAUSE - wait for "Continue"

## Gap Integration Requirement

**ALL findings from gap analysis MUST be addressed in this specification.**

Before starting each section, check gap analysis for findings targeted at that section.

Create a tracking table at the end of this output:
| Gap ID | Description | Priority | Section | How Addressed |

## Sections to Write

### Section 1: Executive Summary
- 1.1 Purpose (2-3 paragraphs)
- 1.2 Key Capabilities (table including Document Bridge, State Bridge)
- 1.3 Position in Stack (ASCII diagram showing L03 with Phase 15/16 integration)
- 1.4 Design Principles (5-7 principles including nested sandbox, fail-safe circuit breaking, checkpoint recovery)


---

### Section 2: Scope Definition
- 2.1 In Scope (detailed table with descriptions for all 8 capabilities including MCP bridges)
- 2.2 Out of Scope (with owning layer for each of 6 excluded items)
- 2.3 Boundary Decisions (BC-1 nested sandbox, BC-2 tool.invoke interface, ADR-001/002 infrastructure)


---

### Section 3: Architecture
- 3.1 Component Diagram (ASCII showing all 8 components including Document/State bridges)
- 3.2 Component Inventory (table with purpose, technology per ADR-002, dependencies)
- 3.3 Component Specifications (for each component):
  - Tool Registry (PostgreSQL + pgvector)
  - Tool Executor (nested sandbox)
  - Permission Checker (OPA integration)
  - External Adapter Manager
  - Circuit Breaker Controller (Redis)
  - Result Validator
  - Document Bridge (Phase 15 MCP)
  - State Bridge (Phase 16 MCP)

For each component include:
- Purpose
- Technology choice with rationale (reference ADR-001/002 where applicable)
- Configuration schema
- Dependencies
- Error codes (E3000-E3999 range)


---

### Section 4: Interfaces
- 4.1 Provided Interfaces
  - `tool.invoke()` (BC-2) - Python Protocol definition with Phase 15/16 fields
  - Tool Registry query interface
  - Circuit breaker status interface
- 4.2 Required Interfaces
  - Agent Sandbox Context (from L02, BC-1)
  - ABAC Policy Engine (from L01)
  - Event Store (from L01)
  - Document Bridge (from Phase 15 MCP)
  - State Bridge (from Phase 16 MCP)
- 4.3 Events Published
  - tool.invoked schema
  - tool.succeeded schema
  - tool.failed schema
  - tool.timeout schema
  - tool.checkpoint.created schema
  - circuit.opened schema
  - circuit.closed schema
- 4.4 Events Consumed (if any)


---

### Section 5: Data Model
- 5.1 Owned Entities
  - ToolDefinition (manifest schema with vector embedding)
  - ToolVersion
  - ToolInvocation (execution record)
  - ToolCheckpoint (Phase 16 state)
  - CircuitState (Redis schema)
  - ExternalServiceCredential
- 5.2 Configuration Schemas (JSON Schema 2020-12)
  - Tool manifest schema
  - Circuit breaker configuration
  - Rate limit configuration
  - MCP bridge configuration
- 5.3 Data Flows (ASCII diagrams)
  - Tool invocation flow with Phase 15 document context
  - Long-running tool flow with Phase 16 checkpoints
  - Circuit breaker state flow

## Gap Tracking Table
Complete this table showing gaps addressed in this part:
| Gap ID | Description | Priority | Section | How Addressed |

## ASCII Requirement
All diagrams must use: + - | = > < ^ v
No Unicode box characters.

## Output
Save as: `tool-execution-spec-part1.md`

## KB Management

### Add to This Project KB
| File | Purpose |
|------|---------|
| `tool-execution-spec-part1.md` | Sections 1-5 for merge |

### Verification
- [ ] All 5 sections complete
- [ ] Phase 15/16 integration documented
- [ ] ADR-001/002 decisions reflected
- [ ] Gap tracking table included
- [ ] ASCII diagrams render correctly
- [ ] File added to KB before C.2
