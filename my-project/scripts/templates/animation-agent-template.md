# Animation Agent Task

You are a highly skilled animation engineer working on the electricity effect for The Story Portal app.

## Project Location
`/Volumes/Extreme SSD/projects/story-portal-app/my-project`

## Your Task

Implement or improve the electricity animation in `src/components/electricity/ElectricityAnimation.tsx`.

## Reference Specification

Read these files for requirements:
- `docs/specs/REFERENCE-BASELINE-SPEC.md` - Canonical visual reference
- `docs/specs/TASK7-DIFFERENTIAL-CRITERIA.md` - Scoring rubric (100 points)

## Required Color Values (DO NOT CHANGE)

```javascript
const COLORS = {
  corePeak: '#FEFDE6',   // Near white, warm
  coreAvg: '#FBE9A2',    // Pale golden
  glowInner: '#DAA041',  // Bright amber
  glowOuter: '#894F18',  // Deep amber
}
```

## Required Phase Timing (DO NOT CHANGE)

- BUILD: 900ms with easeInQuad
- PEAK: 1300ms with subtle 2Hz pulse
- DECAY: 800ms with easeOutQuad
- Total: ~3000ms

## Key Technical Requirements

1. **Glow**: Use blur-based rendering (ctx.shadowBlur or ctx.filter='blur()'), NOT stroke-width approximation
2. **Trails**: Use semi-transparent clear (rgba overlay) instead of full clearRect for motion persistence
3. **Morphing**: Interpolate bolt paths between frames instead of full regeneration
4. **Geometry**: 8-10 primary bolts, 2-5 branches each, 80-138px length, endpoint tapering

## Integration

The component is already integrated in `src/legacy/LegacyApp.tsx` at line ~385.

## Deliverables

1. Update `src/components/electricity/ElectricityAnimation.tsx` with improvements
2. Create `docs/specs/TASK7-ITERATION-[N]-CHANGELOG.md` documenting your changes

## Success Criteria

Target: 95/100 on the differential scoring rubric.

Focus on:
- Glow Characteristics (15 points) - smooth gaussian blur
- Temporal Dynamics (15 points) - morphing, not teleporting
- Special Effects (5 points) - trails, additive blending
- Opacity & Transparency (15 points) - proper falloff curves

Begin implementation now. Read the existing code first, then make targeted improvements.
