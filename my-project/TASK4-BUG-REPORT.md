# Task 4: Recording UI - Known Bugs (Not Fixed)

**Date**: January 8, 2026
**Status**: Task 4 components built, but critical bugs remain unfixed
**Previous Attempt**: Agent claimed bugs were fixed, but testing confirmed they are NOT fixed

---

## Bug #1: Stop Button Behavior (First Recording)

### Symptom
1. User spins wheel and clicks Record button
2. Goes through consent flow (enters email)
3. Clicks "I Consent & Record"
4. Sees "Start Recording" button and prompt reminder
5. Clicks "Start Recording" and records audio for 3-5 seconds
6. **Clicks "Stop" button**
7. **Current behavior**: UI returns to "Start Recording" button (as if recording wasn't saved)
8. **Expected behavior**: ReviewScreen should appear with audio playback controls

### Details
- **Bug only occurs on FIRST recording attempt** (short duration)
- If user records for 10+ seconds, Stop button works correctly
- This suggests timing/async issue in phase transitions or audioBlob capture
- No visible console errors, but issue is consistent

### Files to Investigate
- `src/components/views/RecordingView.tsx` - Line ~50-70, `handleStopRecording()` function
- `src/hooks/useRecording.ts` - `stopRecording()` function
- Check: Is `audioBlob` being captured correctly?
- Check: Is `phase` state transitioning from 'recording' to 'review'?

### How to Reproduce
1. `localhost:5173` → Spin wheel
2. Click Record button
3. Enter email, click consent
4. Click "Start Recording"
5. Record for 3-5 seconds (short duration)
6. Click "Stop"
7. ❌ Currently shows "Start Recording" button again
8. ✅ Should show ReviewScreen with play/pause controls

### Root Cause Hypothesis
- Possible race condition: audioBlob not ready when Stop is clicked
- Possible phase transition failing for short recordings
- Possible timing issue between `stopRecording()` completing and state update

---

## Bug #2: Skip Photo Button Navigation

### Symptom
1. User completes full flow: consent → record → review → keep → photo prompt
2. PhotoPrompt shows with "Add Photo / Skip / Cancel" buttons
3. **Clicks "Skip" button**
4. **Current behavior**: UI returns to wheel view WITHOUT saving the recording
5. **Expected behavior**: Recording should be saved (with null photo) and user returns to wheel

### Details
- Recording is lost when Skip is clicked
- No error messages or failures visible
- Story should still be saved to IndexedDB even without photo
- User should be able to see saved recording in Gallery (Task 5)

### Files to Investigate
- `src/components/views/RecordingView.tsx` - Line ~130-140, `handlePhotoSkip()` function
- Check: Does `handlePhotoSkip()` call `saveStory(null)`?
- Check: Does `saveStory()` properly invoke `onSaveStory()` callback?
- Check: Is `onSaveStory` callback properly wired in LegacyApp.tsx?

### How to Reproduce
1. `localhost:5173` → Spin wheel
2. Click Record button → complete consent → record → review → keep
3. Reach PhotoPrompt screen
4. Click "Skip" button
5. ❌ Currently returns to wheel without saving
6. ✅ Should save recording and return to wheel

### Root Cause Hypothesis
- `handlePhotoSkip()` may not be calling `saveStory(null)`
- `onSaveStory` callback may not be connected properly
- Story record may not be created/saved when photo is null

---

## Bug #3: CSS Styling Not Applied

### Symptom
Recording UI appears completely unstyled:
- **Buttons**: White background with black text (no styling)
- **Background**: Transparent/plain (no dark overlay, no design)
- **Layout**: RecordingUI positioned far left of viewport (not centered)
- **Spacing**: No padding, margins, or proper spacing
- **Typography**: No styling applied
- **Overall**: Looks like a debug shell, not a polished interface

### Details
- CSS file exists: `src/components/recording/recording.module.css` (785 lines)
- CSS is imported: `import styles from './recording.module.css'`
- Classes are applied: `<div className={styles.recordingView}>`
- **BUT**: Styling is not visible in browser
- No console errors about missing imports

### Root Cause: Path Alias Issue

**The Problem**:
```css
/* In recording.module.css, line 7: */
@import '@/tokens/design-tokens.css';
```

The `@/` path alias works in **JavaScript/TypeScript files** but **NOT in CSS import statements**. This causes:
1. CSS import fails silently
2. All CSS custom properties (`var(--sp-color-bg-container)`, etc.) are undefined
3. All styling that depends on these variables fails
4. Browser applies default styles (white/transparent/no decoration)

### Files to Fix
- `src/components/recording/recording.module.css` (top of file, line ~7)
- Change: `@import '@/tokens/design-tokens.css';`
- To: A **relative path** that actually works in CSS context

**How to Find the Right Path**:
1. Check how other `.css` or `.module.css` files in the project import design tokens
2. Look at: `src/legacy/styles/` folder for examples
3. Common pattern: `@import '../tokens/design-tokens.css';` or similar relative path

### Expected Styling (Once Fixed)
- Dark background with backdrop blur
- Brass/bronze borders (2px solid #8b6f47)
- Dark containers (rgba(0, 0, 0, 0.8))
- Flame-colored accent elements
- Properly centered modal-like interface
- Styled buttons matching app design
- Waveform visualization centered
- Proper spacing and typography

### How to Verify Fix
1. Fix the import path
2. Build: `npm run build`
3. Refresh browser: `localhost:5173`
4. Click Record button
5. ✅ Should see dark background, brass borders, styled buttons
6. ❌ If still plain white/transparent, import is still broken

---

## Complete Test Flow (Should Work After Fixes)

```
1. Spin wheel → lands on prompt ✅
2. Click Record button ✅
3. Enter email → click consent ✅
4. Click "Start Recording" ✅
5. Record audio for 3-5 seconds
6. Click "Stop" → ReviewScreen shows ← BUG #1 (currently broken)
7. Click "Keep Recording" ✅
8. PhotoPrompt shows ✅
9. Click "Skip" → Recording saves, returns to wheel ← BUG #2 (currently broken)
10. UI is styled with dark background, brass borders, centered layout ← BUG #3 (currently broken)
```

---

## Building Context for Next Agent

### What's Already Built (Working)
- ✅ RecordingView component (phase state machine)
- ✅ RecordingUI (waveform visualization)
- ✅ ReviewScreen (audio playback)
- ✅ ConsentFlow (email + consent)
- ✅ PhotoPrompt (file picker)
- ✅ useRecording hook (Web Audio API)
- ✅ CSS file (785 lines of proper styling)
- ✅ All components compile without TypeScript errors

### What's NOT Working
- ❌ Stop button phase transition (Bug #1)
- ❌ Skip photo save flow (Bug #2)
- ❌ CSS import path (Bug #3)

### All Components Are Properly Structured
- No major refactoring needed
- No missing dependencies
- Just need: phase logic fixes, callback wiring check, CSS import fix

---

## Files to Review/Modify

| File | Purpose | Status |
|------|---------|--------|
| `src/components/views/RecordingView.tsx` | Recording flow orchestration | Needs debugging (Bugs #1, #2) |
| `src/components/recording/recording.module.css` | Styling (CSS import broken) | Needs path fix (Bug #3) |
| `src/components/recording/RecordingUI.tsx` | Waveform UI | ✅ Working |
| `src/components/recording/ReviewScreen.tsx` | Playback screen | ✅ Working |
| `src/components/recording/PhotoPrompt.tsx` | Photo upload | ✅ Working |
| `src/hooks/useRecording.ts` | Web Audio API | ✅ Working |
| `src/tokens/design-tokens.css` | Design variables | ✅ Working |

---

## Next Steps

1. **Agent Task**: Fix all three bugs
2. **Testing Required**: Actual browser testing, not just code review
3. **Verification**: Complete test flow must work end-to-end
4. **Success**: User can record → stop → review → skip photo → save

---

## Technical Notes

- Recording works (audio is captured)
- Components render (no missing imports)
- The issue is in phase transitions, callbacks, and CSS path resolution
- All infrastructure is in place; just needs debugging and path fix
- No architectural changes needed
