# Required Input Files

Copy these files from your `story-portal-app/platform/` directory (and related locations) into this `inputs/` folder before starting the build.

## Required Files

| File | Source Location | Purpose |
|------|-----------------|---------|
| `agentic-data-layer-master-specification-v4.0-final-ASCII.md` | Data Layer project KB | Pattern reference, event schemas, ABAC integration |
| `agent-runtime-layer-specification-v1.2-final-ASCII.md` | Agent Runtime project KB | Sandbox interface, BC-1 boundary |
| `model-gateway-layer-specification-v1.2-final-ASCII.md` | Model Gateway project KB | Function calling support patterns |
| `phase-15-document-management-specification-v1.0-ASCII.md` | Data Layer project KB | Document context for tool execution |
| `phase-16-session-orchestration-specification-v1.0-ASCII.md` | Data Layer project KB | Tool state persistence and checkpointing |
| `layer-specification-template.md` | Process Support project KB | 15-section structure template |
| `specification-integration-guide.md` | Process Support project KB | Writing standards and conventions |
| `ADR-001-mcp-integration-architecture.md` | Full Stack project KB | MCP stdio transport patterns |
| `ADR-002-lightweight-development-stack.md` | Full Stack project KB | PostgreSQL/Redis/Ollama stack decisions |

## Verification

Before starting, verify all 9 files are present:

```bash
ls -la inputs/
# Should show 9 .md files plus this README
```

## Notes

- These files are READ-ONLY references during the build
- The build will fail if required files are missing
- File names must match exactly (case-sensitive)
