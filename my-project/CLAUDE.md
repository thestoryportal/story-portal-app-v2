# Frontend Application

## Stack
- React 19
- TypeScript 5.9
- Vite 7
- Three.js (3D rendering)
- React Spring (animation timing)
- localForage (IndexedDB wrapper)

---

## CRITICAL RULES

### Canvas 2D is DEPRECATED
- **DO NOT** use Canvas 2D API for rendering
- **USE** `ElectricityOrtho` component only
- Location: `src/components/electricity/ortho/`
- Legacy code archived in `src/legacy/_archived/` - DO NOT USE

### Animation Timing
- All animation timing via **React Spring**
- Do not use CSS animations for complex sequences
- Do not use requestAnimationFrame directly

### Props Over Context (MVP)
- **NO** Context API (deferred to Phase 2)
- **NO** Redux or state management libraries
- Pass state down via props, callbacks up
- Accept prop drilling—it's fine for MVP scope

---

## Design Philosophy

**Steampunk: mechanical, warm, tactile, intentional**

Every design decision reinforces the metaphor of an analog time machine.

| Embrace | Avoid |
|---------|-------|
| Brass, amber, aged bronze | Cold blues, grays, whites |
| Natural wood, patina, texture | Flat design, sterile minimal |
| Mechanical gears, hand-forged | Algorithmic, frictionless |
| Substantial animations | Instant, slick transitions |

**Mood**: Colors evoke candlelight and fire, NOT sterile fluorescence.

### Core Color Tokens
| Token | Hex | Usage |
|-------|-----|-------|
| `--color-brass-light` | `#f5deb3` | Body text, headings |
| `--color-bronze-standard` | `#8b6f47` | Borders, outlines |
| `--color-flame-core` | `#ffb836` | Interactive accents |
| `--bg-primary` | `#0a0705` | Main background |

Full color system: `src/tokens/colors.css`

---

## Architecture Constraints (MVP)

### Container/Presentational Pattern
- **Container** ("Smart"): Manage state, use hooks, handle logic
- **Presentational** ("Dumb"): Receive props, render UI, fire callbacks
- Keep animation logic inside containers, not abstracted

### Styling Rules
- **CSS Modules** for complex features (views, feature components)
- **Inline styles** for simple variants (conditional opacity, etc.)
- **NO** styled-components or CSS-in-JS
- Always use semantic color tokens (`var(--color-brass-light)`)

### Data Storage
- **IndexedDB** via `localForage` for all local storage
- Stores: `stories`, `prompts`, `topic_packs`, `settings`
- Audio files stored as Blobs
- Minimum 5MB storage required

---

## Steam Modal
**Authority Source**: `docs/STEAM-MODAL-SPECIFICATION.md` (Authority 10)

Key specifications:
- Steam color: `#C5B389` (most dense)
- Text color: `#433722` (regular case, NOT uppercase)
- Animation: 5-phase sequence (0-5500ms+)
- Content reveal: Clearing mechanism (NOT fade-in)
- Zero brass dividers or outlines

---

## Key Specifications

Consult these for detailed requirements:

| Spec | Size | When to Consult |
|------|------|-----------------|
| `docs/specs/DESIGN_SYSTEM.md` | 29KB | Colors, typography, animations, accessibility |
| `docs/specs/COMPONENT_ARCHITECTURE.md` | 33KB | Component patterns, data flow, folder structure |
| `docs/specs/APP_SPECIFICATION.md` | 13KB | Product scope, personas, UX rules, mission |
| `docs/specs/ACCEPTANCE_CRITERIA.md` | 36KB | 225 validation criteria (MUST/SHOULD/NICE) |
| `docs/specs/USER_FLOWS.md` | 30KB | User journeys, state diagrams, pass rule |
| `docs/specs/DATA_MODEL.md` | 24KB | TypeScript interfaces, IndexedDB schema |
| `docs/specs/IMPLEMENTATION_DECISIONS.md` | 5.7KB | 5 key technical decisions with rationale |
| `docs/IMPLEMENTATION_GUIDES.md` | 30KB | Wheel physics, audio waveform, content strategy |

Quick reference: `docs/specs/PRODUCT_CONTEXT.md`

---

## Key TypeScript Interfaces

From `DATA_MODEL.md`:

```typescript
interface StoryRecord {
  id: string;
  prompt_id: string;
  audio_blob: Blob;
  duration_seconds: number;
  created_at: string;
  consent_data: ConsentData;
}

interface Prompt {
  id: string;
  text: string;
  category: string;
  declaration_risk: 'low' | 'medium' | 'high';
  facilitation_hint?: string;
}

interface ConsentData {
  recording_consented: boolean;
  storage_consented: boolean;
  consented_at: string;
}
```

---

## Session Infrastructure

### Auto-Injected Context
Hooks in `.claude/settings.json` auto-inject context on:
- `startup` - Session start (loads hot context, available tasks)
- `clear` - After /clear command
- `compact` - After context compaction (recovery hint)

### Hook Behavior
| Hook | Trigger | Purpose |
|------|---------|---------|
| `session-start-hook.cjs` | startup/clear | Load hot context, list available tasks |
| `post-compact-hook.cjs` | compact | Inject recovery hint |
| `pre-compact-hook.cjs` | auto/manual | Save session state before compaction |
| `task-detector-hook.cjs` | UserPromptSubmit | Detect task keywords, inject context |
| `context-loader-hook.cjs` | UserPromptSubmit | Load task or global context |
| `context-saver-hook.cjs` | Pre/PostToolUse | Track session activity |
| `plan-mode-l05-hook.cjs` | ExitPlanMode | Execute L05 planning |

### MCP Servers (configured in `.mcp.json`)
| Server | Purpose |
|--------|---------|
| `document-consolidator` | Document management, overlap detection, source of truth |
| `context-orchestrator` | Task context, checkpoints, recovery, role switching |
| `platform-services` | Service invocation, workflow execution |

### Context Files
- `.claude/contexts/_hot_context.json` - Current session state (synced from PostgreSQL/Redis)
- `.claude/contexts/_registry.json` - Document index, available tasks
- `.claude/contexts/task-agents/*.json` - Task-specific contexts
- `.claude/contexts/.session-state.json` - Session tracking for recovery

---

## Core UX Rules (from APP_SPECIFICATION)

1. **One pass allowed** — Can skip first prompt, must accept second
2. **No prompt shopping** — Can't browse prompts before spinning
3. **Audio only** — No typed stories
4. **5-minute max** — Recording duration limit
5. **Facilitation hints** — Show for declaration-risk prompts

---

## Test Modes
Access via URL parameters:
```
?test=modal       # Steam modal test
?test=comparison  # A/B comparison
?test=v37         # Version 37 test
```

---

## Project Structure
```
my-project/
├── src/
│   ├── components/
│   │   ├── electricity/ortho/  # ElectricityOrtho renderer (Three.js)
│   │   ├── views/              # Page-level containers
│   │   ├── gallery/            # Story gallery components
│   │   ├── modal/              # Modal content window
│   │   └── form/               # Form components (see USAGE.md)
│   ├── hooks/                  # Custom React hooks
│   ├── tokens/                 # Design system (colors.css, design-tokens.css)
│   ├── types/                  # TypeScript interfaces
│   ├── utils/                  # Pure utility functions
│   ├── legacy/_archived/       # DEPRECATED - raw WebGL code, DO NOT USE
│   └── constants/              # Hardcoded prompts, content pages (MVP)
├── docs/
│   ├── specs/                  # Formal specifications (Authority 8-9)
│   ├── archive/                # Superseded documents
│   └── STEAM-MODAL-SPECIFICATION.md  # Authority 10
└── .claude/
    ├── settings.json           # Hooks configuration
    ├── settings.local.json     # Local permissions + hooks
    ├── hooks/                  # Hook scripts (.cjs)
    └── contexts/               # Session contexts
```

---

## Development
```bash
npm run dev       # Start dev server (Vite)
npm run build     # Production build
npm run test      # Run tests
```

---

## What's in MVP vs Phase 2

**MVP (Now):**
- 3D wheel, audio recording, local storage
- Consent flow, content screens, PWA
- Props-based state, hardcoded content

**NOT in MVP (Phase 2+):**
- User accounts, cloud sync
- Context API, Redux
- Video recording, social features
- Custom prompts, topic management UI
