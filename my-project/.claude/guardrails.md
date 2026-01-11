# Project Guardrails

## HARD BOUNDARIES - DO NOT VIOLATE

### 1. Canvas 2D Electricity Animation is DEPRECATED

**Date Established**: 2026-01-11
**Status**: HARD BOUNDARY

#### Rule
Canvas 2D (`ElectricityAnimation.tsx`) is **deprecated and being replaced** by:
- **ElectricityOrtho** - Orthographic React Three Fiber (R3F)
- React hooks for state management
- React Spring for animations (where applicable)

#### Implications
1. **DO NOT** add new features to `ElectricityAnimation.tsx` (Canvas 2D)
2. **DO NOT** create new Canvas 2D based electricity components
3. **DO NOT** reference Canvas 2D as the primary implementation
4. **ALL** new electricity animation work MUST use `ElectricityOrtho` and the ortho/ directory

#### Correct Technology Stack
```
src/components/electricity/ortho/
├── ElectricityOrtho.tsx     # Main component - USE THIS
├── scene/OrthoScene.tsx     # Scene with orthographic camera
├── bolts/                   # Bolt generation and rendering
└── animation/               # Phase-based animation system
```

#### Migration Status (Updated: 2026-01-11)
| File | Status | Notes |
|------|--------|-------|
| LegacyApp.tsx | MIGRATED | Now uses ElectricityOrtho |
| AlignmentTest.tsx | MIGRATED | Now uses ElectricityOrtho |
| ElectricityOverlayTest.tsx | MIGRATED | Now uses ElectricityOrtho |
| electricity/index.ts | UPDATED | Default export now ElectricityOrtho |
| App.tsx | N/A | Main app integration pending |

#### Archived (Do Not Use)
- `src/components/electricity/ElectricityAnimation.tsx` - Canvas 2D (DEPRECATED)
- `src/components/electricity/ElectricityR3F.tsx` - Perspective R3F (Wrong camera type)

---

## Guidelines (Non-Blocking)

### Electricity Animation Visual Requirements
- 8-10 bolts in radial pattern
- 1-3 branches per bolt
- Animation phases: BUILD (900ms) → PEAK (1300ms) → DECAY (800ms)
- 5-layer glow system with color palette:
  - Core Peak: #FEFDE6 (near white)
  - Core Avg: #FBE9A2 (pale golden)
  - Glow Inner: #DAA041 (bright amber)
  - Glow Outer: #894F18 (deep amber)

### Performance Requirements
- Maintain 60fps during animation
- Use orthographic camera for 1:1 pixel mapping
- Batch geometries where possible
