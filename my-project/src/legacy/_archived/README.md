# Archived Code

**Status:** Pending review
**Archived:** 2025-12-23

---

## Contents

| File | Description | Replaced By |
|------|-------------|-------------|
| `useElectricityEffect.ts` | Raw WebGL multi-pass electricity renderer (540 lines) | `useElectricityEffectThree.ts` |
| `ElectricityCanvas.tsx` | Canvas wrapper for raw WebGL effect | `ElectricityR3F.tsx` |

---

## Why Archived

These files implement the electricity effect using raw WebGL commands (manual shader compilation, framebuffers, render passes). This approach was replaced by React Three Fiber for:

1. **Simpler code** — R3F handles WebGL complexity
2. **Better maintainability** — Declarative React components
3. **Ecosystem benefits** — Access to drei helpers, postprocessing, etc.

---

## Review Notes

**TODO:** Review and decide whether to:
- [ ] Delete permanently (git history preserves code)
- [ ] Keep as reference for complex WebGL patterns
- [ ] Extract any reusable utilities

---

## Technical Details

The raw WebGL implementation featured:
- Multi-pass rendering (bolts → plasma → bloom → composite)
- Custom GLSL shaders for each pass
- Manual framebuffer/texture management
- Per-bolt opacity animation
- 3-second surge cycles with 2Hz center pulse

If restoring, the files depend on:
- `../effects/shaders.ts` (GLSL shader strings)
- `../effects/boltGenerator.ts` (bolt path generation)
- `../effects/noiseUtils.ts` (simplex noise)
- `../constants/config.ts` (ELECTRICITY_CONFIG)
