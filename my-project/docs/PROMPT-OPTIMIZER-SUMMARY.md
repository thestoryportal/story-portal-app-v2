# Prompt Optimizer Implementation Summary

The prompt optimizer is a sophisticated, production-grade system located primarily in `packages/prompt-optimizer/`.

## Architecture

### Package Structure

```
packages/prompt-optimizer/
├── src/
│   ├── core/         - Main optimizer, pipeline, session
│   ├── layers/       - Modular processing (classifier, verifier, optimization passes)
│   ├── api/          - Anthropic & Ollama clients
│   ├── context/      - Session, project, user, terminal context
│   ├── learning/     - Preference engine & pattern tracking
│   ├── storage/      - Cache, profile, metrics persistence
│   ├── recovery/     - Undo/rollback functionality
│   ├── cli/          - Command-line interface
│   └── constants/    - Defaults, prompts, thresholds
```

### Integration Files

- `.claude/commands/prompt.md` - CLI command definition
- `.claude/hooks/prompt-optimizer-hook.cjs` - UserPromptSubmit hook (~428 lines)

---

## Core Features

### 1. 4-Way Classification System

| Category | Confidence | Action |
|----------|------------|--------|
| PASS_THROUGH | >0.85 | Well-formed, send as-is |
| DEBUG | >0.80 | Error/troubleshooting detected |
| OPTIMIZE | >0.75 | Needs improvement |
| CLARIFY | >0.60 | Intent unclear |

**Domain Detection:** CODE, WRITING, ANALYSIS, CREATIVE, RESEARCH

### 2. Workflow Modes (6 Types)

| Mode | Prefix | Purpose | Max Expansion |
|------|--------|---------|---------------|
| SPECIFICATION | `!spec` | New features/projects | 3.0x |
| FEEDBACK | `!feedback` | Iteration on existing work | 1.5x |
| BUG_REPORT | `!bug` | Structured issues | 2.0x |
| QUICK_TASK | `!quick` | Simple actions | 1.2x |
| ARCHITECTURE | `!arch` | Design decisions | 2.5x |
| EXPLORATION | `!explore` | Research topics | 1.5x |

### 3. 3-Pass Optimization Pipeline

- **Pass 1**: Fast clarity improvements, element preservation
- **Pass 2**: Critique & domain-specific refinement
- **Pass 3**: Final polish & format optimization

**Processing Flow:**
```
Input → Workflow Detection → Context Assembly
    → Classification → Routing Decision
    → Optimization (1-3 passes) → Intent Verification
    → Review Gate → Output
```

### 4. Intent Verification

- Local checks (element preservation, length delta)
- API semantic similarity (>0.90 high, >0.80 medium)
- Blended scoring: 40% local + 60% API

---

## API Support

- **Anthropic** (primary): Haiku for classification/simple tasks, Sonnet for complex optimization
- **Ollama** (local): For offline/privacy
- **Mock mode**: For testing

Auto-escalation triggers: >200 tokens or <0.80 confidence → upgrades to Sonnet

---

## Configuration

### Key Defaults

| Setting | Value |
|---------|-------|
| Optimization level | 2 (1-3 scale) |
| Confirmation threshold | 0.75 |
| Max passes | 3 |
| Max latency | 1500ms |
| Context tokens | 4000 max |
| Session history | 5 turns |

### Pattern Rules

**Never-Optimize Patterns:** Shell commands (`^/`, `^cd `, `^git `, `^npm `)

**Always-Confirm Patterns:** Destructive ops (`delete`, `remove`, `drop`, `destroy`)

### Confidence Thresholds

| Threshold | Value |
|-----------|-------|
| PASS_THROUGH | 0.85 |
| DEBUG | 0.80 |
| OPTIMIZE | 0.75 |
| CLARIFY | 0.60 |
| Verification HIGH | 0.90 |
| Verification MEDIUM | 0.80 |
| Verification LOW | 0.60 |

### Latency Budgets

| Stage | Budget |
|-------|--------|
| Context assembly | 50ms |
| Classification | 100ms |
| Optimization per pass | 200ms |
| Intent verification | 100ms |
| Review gate | 50ms |
| Total 1-pass | 500ms |
| Total 3-pass | 900ms |

---

## CLI Usage

```bash
prompt-optimize "your prompt"
  --level 1|2|3      # Optimization depth
  --workflow spec    # Force workflow mode
  --undo             # Revert last optimization
  --json             # Machine-readable output
  --local            # Use Ollama
  --feedback good|bad
```

### Available Commands

| Command | Description |
|---------|-------------|
| `[prompt]` | Input prompt (positional) |
| `--no-optimize` / `--optimize` | Skip/force optimization |
| `--level 1\|2\|3` | Optimization depth |
| `--confirm` / `--auto` | Confirmation handling |
| `--undo` | Revert last optimization |
| `--reoptimize` | Re-optimize with hint |
| `--json` | Machine-readable output |
| `--explain` | Show detailed explanation |
| `--workflow [mode]` | Override workflow |
| `--mock` / `--local` | API mode override |
| `--stats` | Show statistics |
| `--feedback good\|bad` | User feedback |

---

## Learning & Personalization

- Stores user feedback (good/bad ratings)
- Tracks pattern acceptance rates
- Learns domain preferences
- Maintains profiles at `~/.claude/optimizer-*.json`

### Storage Files

| File | Purpose |
|------|---------|
| `~/.claude/optimizer-profile.json` | User profile & preferences |
| `~/.claude/optimizer-metrics.json` | Usage metrics |
| `~/.claude/optimizer-history.json` | Optimization history |

---

## Hook Integration

The hook intercepts all `UserPromptSubmit` events in Claude Code, detecting workflow prefixes and routing prompts through the optimization pipeline before submission.

### Features

- Auto-enabled via `.optimizer-auto-enabled` flag file
- 15s API timeout, 120s local timeout
- Confidence ≥0.85 auto-sends; below requires confirmation

### Modes

| Mode | Trigger | Description |
|------|---------|-------------|
| API mode | Default | Uses Anthropic API |
| Local mode | `PROMPT_OPTIMIZER_MODE=local` | Uses Ollama |
| Mock mode | `PROMPT_OPTIMIZER_MODE=mock` | Testing |

---

## Programmatic API

```typescript
import { createOptimizer } from '@story-portal/prompt-optimizer';

const optimizer = createOptimizer({
  useMock: false,
  useLocal: false,
  localConfig: { model: 'neural-chat' }
});

const result = await optimizer.optimize('your prompt', {
  level: 2,
  force: false,
  skip: false,
  workflowMode: 'SPECIFICATION',
  context: {
    language: 'TypeScript',
    framework: 'React',
    expertise: 'senior'
  }
});
```

### Result Object

```typescript
{
  optimized: string,
  wasOptimized: boolean,
  category: 'PASS_THROUGH' | 'DEBUG' | 'OPTIMIZE' | 'CLARIFY',
  domain: 'CODE' | 'WRITING' | 'ANALYSIS' | 'CREATIVE' | 'RESEARCH',
  workflowMode: string,
  confidence: number,
  latencyMs: number
}
```

---

## Key Files Reference

| Path | Purpose | Lines |
|------|---------|-------|
| `core/optimizer.ts` | Main PromptOptimizer class | ~229 |
| `core/pipeline.ts` | Orchestrates pipeline flow | ~365 |
| `layers/classifier.ts` | 4-way classification | ~200+ |
| `layers/workflow/configs.ts` | Workflow mode definitions | ~227 |
| `layers/workflow/detector.ts` | Workflow detection | ~80+ |
| `layers/workflow/transformer.ts` | Structural transforms | ~80+ |
| `layers/optimization/pass-one.ts` | Initial optimization | ~100+ |
| `layers/intent-verifier.ts` | Semantic verification | ~60+ |
| `constants/defaults.ts` | Default config | ~177 |
| `constants/thresholds.ts` | Confidence thresholds | ~125 |
| `api/anthropic-client.ts` | API integration | ~80+ |
| `cli/index.ts` | CLI entry point | ~110 |
| `cli/args.ts` | Argument parsing | ~100+ |
| `.claude/hooks/prompt-optimizer-hook.cjs` | Claude CLI hook | ~428 |
| `.claude/commands/prompt.md` | Command spec | ~196 |

---

## Recovery Features

- **Undo**: Reverts last optimization within 30 seconds
- **Re-optimize**: Re-runs with hints
- **Pattern detection**: Flags repeated rejections (>5)
- **Rate limiting**: Limits `--no-optimize` (>3 times triggers flag)
