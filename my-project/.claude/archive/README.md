# Archive - Historical Documentation

This directory contains archived documentation that has been superseded by consolidated context files.

## Structure

```
archive/
├── l05-planning/2026-01/     # L05 Planning Pipeline docs
├── phase4-integration/2026-01/ # Phase 4 integration docs
├── e2e-testing/2026-01/      # End-to-end testing docs
├── steam-modal/2026-01/      # Steam Modal implementation docs
├── layer-implementations/2026-01/ # Layer implementation prompts
└── misc/2026-01/             # Miscellaneous docs
```

## Superseded By

| Archive Category | Superseded By |
|------------------|---------------|
| l05-planning/ | `.claude/contexts/L05-PLANNING-PIPELINE-REFERENCE.md` (authoritative) |
| l05-planning/ | `.claude/contexts/l05/l05-known-fixes.yaml` (structured fixes) |
| l05-planning/ | `.claude/contexts/l05/l05-cross-layer.yaml` (boundary info) |

## L05 Planning Archive Contents

| File | Description | Key Extractions |
|------|-------------|-----------------|
| L05-PLANNING-PIPELINE-IMPLEMENTATION-PLAN.md | Original implementation guide | Fixes extracted to l05-known-fixes.yaml |
| L05_PLANNING_PIPELINE_DEBUG_REPORT.md | Debug analysis | Error patterns extracted |
| planning-layer-implementation-prompt.md | Initial prompt | Architecture → reference doc |

## Usage

These files are kept for historical reference only. Do NOT inject these into context.
Use the consolidated YAML files in `.claude/contexts/l05/` for context injection.
