# Tool Execution Layer - Autonomous Build Orchestrator

You are executing a complete specification build consisting of 11 sequential sessions. Process each session fully before proceeding to the next.

## Working Directory Structure

```
tool-execution-build/
├── START.md                 # This file - read once, then execute
├── prompts/                 # Session prompts to execute in order
│   ├── 01-industry-research.md
│   ├── 02-gap-analysis.md
│   ├── 03-spec-part1.md
│   ├── 04-spec-part2.md
│   ├── 05-spec-part3.md
│   ├── 06-merge.md
│   ├── 07-self-validation.md
│   ├── 08-apply-fixes.md
│   ├── 09-industry-validation.md
│   ├── 10-industry-integration.md
│   └── 11-integration.md
├── inputs/                  # Reference specifications (you must read these)
│   ├── agentic-data-layer-master-specification-v4.0-final-ASCII.md
│   ├── agent-runtime-layer-specification-v1.2-final-ASCII.md
│   ├── model-gateway-layer-specification-v1.2-final-ASCII.md
│   ├── phase-15-document-management-specification-v1.0-ASCII.md
│   ├── phase-16-session-orchestration-specification-v1.0-ASCII.md
│   ├── layer-specification-template.md
│   ├── specification-integration-guide.md
│   ├── ADR-001-mcp-integration-architecture.md
│   └── ADR-002-lightweight-development-stack.md
└── outputs/                 # Write all deliverables here
```

## Execution Instructions

For each session 01 through 11:

1. Read `prompts/NN-*.md`
2. Read any required input files from `inputs/` and `outputs/`
3. Execute the session tasks completely
4. Write the output file to `outputs/`
5. Proceed immediately to the next session

## Session Execution Table

| # | Prompt File | Required Inputs | Output File | Web Search |
|---|-------------|-----------------|-------------|------------|
| 01 | `01-industry-research.md` | inputs/* | `outputs/tool-execution-research-findings.md` | **YES** |
| 02 | `02-gap-analysis.md` | inputs/*, outputs/01 | `outputs/tool-execution-gap-analysis.md` | NO |
| 03 | `03-spec-part1.md` | inputs/*, outputs/01-02 | `outputs/tool-execution-spec-part1.md` | NO |
| 04 | `04-spec-part2.md` | inputs/*, outputs/01-03 | `outputs/tool-execution-spec-part2.md` | NO |
| 05 | `05-spec-part3.md` | inputs/*, outputs/01-04 | `outputs/tool-execution-spec-part3.md` | NO |
| 06 | `06-merge.md` | outputs/03-05 | `outputs/tool-execution-layer-specification-v1.0-ASCII.md` | NO |
| 07 | `07-self-validation.md` | inputs/*, outputs/06 | `outputs/tool-execution-validation-report.md` | NO |
| 08 | `08-apply-fixes.md` | outputs/06-07 | `outputs/tool-execution-layer-specification-v1.1-ASCII.md` | NO |
| 09 | `09-industry-validation.md` | outputs/01,08 | `outputs/tool-execution-industry-validation-report.md` | **YES** |
| 10 | `10-industry-integration.md` | outputs/08-09 | `outputs/tool-execution-layer-specification-v1.2-final-ASCII.md` | NO |
| 11 | `11-integration.md` | outputs/10 | `outputs/full-stack-roadmap-updated.md` | NO |

## Critical Rules

1. **Sequential execution**: Complete session N before starting session N+1
2. **File persistence**: Write each output before proceeding
3. **Web search**: Use web search capabilities for sessions 01 and 09 only
4. **No skipping**: Execute all 11 sessions
5. **Merge protocol (session 06)**: Use `cat` to concatenate files, do NOT rewrite content
6. **Phase 15/16 integration**: Ensure MCP bridge patterns are documented throughout
7. **ADR alignment**: Reflect ADR-001 (MCP stdio) and ADR-002 (PostgreSQL/Redis/Ollama) decisions

## Key Integration Points

This layer has critical integration boundaries:

- **BC-1**: Nested sandbox within Agent Runtime (L02) - tool sandboxes inside agent sandboxes
- **BC-2**: `tool.invoke()` interface consumed by Integration Layer (L11)
- **Phase 15**: Document Bridge for MCP document-consolidator integration
- **Phase 16**: State Bridge for MCP context-orchestrator integration
- **ADR-001**: MCP communication via stdio transport (not HTTP)
- **ADR-002**: PostgreSQL + pgvector for registry, Redis for circuit breaker state

## Begin Execution

Start now with session 01. Read `prompts/01-industry-research.md` and execute it.

After completing all 11 sessions, report:
- Total files created in `outputs/`
- Final deliverable: `tool-execution-layer-specification-v1.2-final-ASCII.md`
- Any issues encountered
