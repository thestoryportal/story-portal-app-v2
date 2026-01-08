# Implementation Decisions — Story Portal MVP

**Date**: January 8, 2026
**Status**: Ready for Implementation
**Blocking Issues**: 5 critical decisions made below

---

## 1. Wheel Physics Formula

**Decision**: Linear velocity damping with empirical tuning
**Implementation**:
```typescript
// Pseudo-code for wheel rotation calculation
const wheelRotationDelta = (touchVelocity: number) => {
  const dampingFactor = 0.5; // Tuned empirically via user testing
  return touchVelocity * dampingFactor;
};
```

**Rationale**:
- Simple, performant, no complex physics simulation needed
- Allows easy tweaking via `dampingFactor` constant
- Velocity measured as pixels/millisecond from touch delta

**Testing Criteria**:
- Fast swipe (velocity ~5px/ms) → ~2.5 turns rotation
- Slow swipe (velocity ~1px/ms) → ~0.5 turns rotation
- Adjustable via single constant without code restructuring

---

## 2. Audio Waveform Visualization

**Decision**: Web Audio API frequency bin extraction
**Implementation**:
```typescript
// Pseudo-code for waveform extraction
const extractWaveform = (audioContext: AudioContext) => {
  const analyser = audioContext.createAnalyser();
  analyser.fftSize = 256; // Balance: detail vs performance
  const dataArray = new Uint8Array(analyser.frequencyBinCount);
  analyser.getByteFrequencyData(dataArray);
  return dataArray; // 128 frequency bins, 0-255 intensity
};
```

**Rationale**:
- No external dependencies (Web Audio API is native to browsers)
- Efficient real-time frequency visualization
- Works with MediaRecorder stream
- Sufficient detail for visual feedback at 256 FFT size

**Testing Criteria**:
- Waveform updates at ≥30fps during recording
- Visual feedback responsive to audio intensity
- No audio processing latency

---

## 3. Content Sourcing Strategy

**Decision**: Hardcoded prompts in MVP; dynamic sourcing deferred to Phase 2
**Implementation**:
```typescript
// Prompts defined in constants/prompts.ts
export const PROMPTS = [
  { id: 'prompt-001', text: 'What is your favorite memory?', category: 'memories' },
  { id: 'prompt-002', text: 'Describe a moment that changed you...', category: 'growth' },
  // ... additional hardcoded prompts
];

// Content pages defined in constants/contentPages.ts
export const CONTENT_PAGES = [
  { id: 'page-001', title: 'About Story Portal', content: '...' },
  { id: 'page-002', title: 'How to Record', content: '...' },
  // ... additional pages
];
```

**Rationale**:
- No backend API needed for MVP validation
- Simple, deterministic, testable
- Easy to transition to dynamic API in Phase 2
- Reduces deployment complexity

**Scope for MVP**:
- ~20 story prompts hardcoded
- ~5 content pages hardcoded
- No API calls for content retrieval

**Phase 2 Extension**:
- Replace constants with API fetch
- Add content management system
- Allow custom prompt generation

---

## 4. TopicPack Visibility in MVP

**Decision**: Component prepared but hidden (not exposed in UI)
**Implementation**:
```typescript
// TopicPack component exists but not imported in main UI
// - TopicPack.tsx fully implemented per COMPONENT_ARCHITECTURE
// - No UI element triggers TopicPack modal
// - Ready for Phase 2 when topic management is added

// In Phase 2, uncomment import and add button:
// <button onClick={() => setView('topic-pack')}>Manage Topics</button>
```

**Rationale**:
- Reduces MVP scope (topic management is complex)
- Component exists and is tested, ready to enable
- Aligns with MVP focus on core recording + gallery workflow
- Zero refactoring needed to enable in Phase 2

**Testing Criteria**:
- TopicPack component renders without errors (even if hidden)
- All TopicPack acceptance criteria pass
- UI flow complete without TopicPack

---

## 5. Reduced-Motion Wheel Snap Behavior

**Decision**: Instant snap (no animation) when `prefers-reduced-motion`
**Implementation**:
```typescript
// In Wheel component
const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

const handleWheelStop = (finalRotation: number) => {
  if (prefersReducedMotion) {
    // Instant snap to nearest prompt (0 animation duration)
    setWheelRotation(snapToNearest(finalRotation));
  } else {
    // Smooth animation to snap point (0.5s easing)
    animateTo(snapToNearest(finalRotation), 500, 'easeOutQuad');
  }
};
```

**Rationale**:
- Respects WCAG A accessibility requirement
- Simplest implementation: conditional duration
- No reduced-motion users experience animation
- Non-reduced-motion users get smooth feedback

**Testing Criteria**:
- Snap completes instantly when flag is true
- Snap animates smoothly when flag is false
- No visual jank or motion sickness risk

---

## Summary & Next Steps

| Decision | Status | Blocker | Next Action |
|----------|--------|---------|-------------|
| Wheel physics | ✅ Approved | No | Implement in Wheel component |
| Audio waveform | ✅ Approved | No | Implement in Recorder component |
| Content sourcing | ✅ Approved | No | Create `constants/prompts.ts` and `constants/contentPages.ts` |
| TopicPack MVP | ✅ Approved | No | Leave component in place, don't expose in UI |
| Reduced-motion snap | ✅ Approved | No | Add matchMedia check in Wheel component |

**Estimated Implementation Time**: 6 hours
**Critical Path**: Wheel mechanics (most complex) → Recording → Storage → Gallery → Content pages

**Ready to Proceed**: ✅ Yes — Agent can now create detailed implementation guides and scaffold project structure.

---

**Previous References**:
- Component Architecture: `COMPONENT_ARCHITECTURE.md`
- Data Model: `DATA_MODEL.md`
- Acceptance Criteria: `ACCEPTANCE_CRITERIA.md`
- Design System: `DESIGN_SYSTEM.md`
