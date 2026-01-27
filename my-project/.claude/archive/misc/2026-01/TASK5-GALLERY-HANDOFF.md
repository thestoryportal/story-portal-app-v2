# Task 5: Gallery Implementation - Handoff Document

**Date**: January 8, 2026
**Status**: 60% Complete - Three Critical Bugs Remaining
**Previous Agent**: Implemented accordion structure, fixed layout flow
**Current Task**: Fix three remaining bugs to complete Task 5

---

## Current State

### What's Working ✅
- Accordion structure implemented (expandable tabs)
- Tab height management - tabs shift down when one expands (no squishing)
- Play button visible on collapsed tabs
- Thumbnail photos visible on collapsed tabs
- Modal overlay with blurred background working
- Gallery scrolling for multiple stories
- Dropdown arrow showing expanded/collapsed state
- Delete button visible on right side

### What's Broken ❌
1. **Font License Text Rendering** (CRITICAL)
2. **Expanded Image Cut Off at Bottom** (CRITICAL)
3. **Recording Duration Missing** (CRITICAL)

---

## Bug Details

### Bug 1: Font License Text Instead of Date/Time

**Symptom:**
- Where date/time should display, showing font license agreement text
- Example in screenshot: "JAN [lots of small unreadable license text]"
- Should display: "Jan 8, 2025 • 3:45 PM"

**Location:**
- File: `src/components/recording/StoryAccordion.tsx` (date/time rendering section)
- File: `src/components/recording/recording.module.css` (font declarations)

**Root Cause:**
Date/time rendering code is outputting font object or license metadata instead of formatted date string.

**What's Needed:**
```typescript
// Current (BROKEN): Rendering font object or license text
// Expected (WORKING):
const formattedDate = new Date(story.created_at).toLocaleDateString();
const formattedTime = new Date(story.created_at).toLocaleTimeString();
// Display: "Jan 8, 2025 • 3:45 PM"
```

**Success Criteria:**
Collapsed tab displays readable date/time like "Jan 8, 2025 • 3:45 PM" - NO license text visible

---

### Bug 2: Expanded Image Cut Off at Bottom

**Symptom:**
- When accordion tab opens, photo/thumbnail is cropped at bottom
- Can see top of image but bottom is hidden/cut off
- Should show complete full-size photo

**Location:**
- File: `src/components/recording/StoryAccordion.tsx` (expanded view JSX)
- File: `src/components/recording/recording.module.css` (image container styling)

**Root Cause:**
Likely max-height, overflow: hidden, or flex-basis constraint preventing full image display in expanded state.

**What's Needed:**
- Expanded container must have sufficient height for: image + prompt + audio player
- Remove max-height constraints on image
- Change overflow to visible (not hidden)
- Use flex-grow or auto height for expanded section

**Success Criteria:**
Click to expand → full image visible top to bottom, no cropping, no cutoff

---

### Bug 3: Recording Duration Missing

**Symptom:**
- Duration (like "3:45" or "52 seconds") not displayed anywhere
- Should appear on collapsed tab header

**Location:**
- File: `src/components/recording/StoryAccordion.tsx` (collapsed tab JSX)

**Root Cause:**
Duration field not being rendered in collapsed tab header.

**What's Needed:**
```typescript
// Helper function
function formatDuration(seconds: number): string {
  const mins = Math.floor(seconds / 60);
  const secs = seconds % 60;
  return `${mins}:${String(secs).padStart(2, '0')}`;
}

// Usage in collapsed tab:
// <span>{formatDuration(story.audio_duration_seconds)}</span>
```

Display on collapsed tab: `[Play Button] [Thumbnail] [Prompt] [Date/Time] [Duration] [Delete Button]`

**Success Criteria:**
All collapsed tabs show readable duration like "3:45", "0:30", "2:15"

---

## File Structure

```
src/components/recording/
├── StoryAccordion.tsx          ← MAIN FILE: Has all three bugs
├── GalleryView.tsx             ← Gallery container (mostly working)
├── AudioPlayer.tsx             ← Player component (working)
└── recording.module.css        ← Styling (check font @fontface declarations)

src/legacy/
└── views/
    └── StoriesView.tsx         ← Wrapper that calls GalleryView

LegacyApp.tsx                   ← Main app router (gallery view hooked up)
```

---

## Testing Checklist

**Before Starting:**
1. Run `npm run dev`
2. Build should complete with no errors
3. Navigate to Gallery view ("My Stories" button from wheel)

**Test Bug 1 - Font/Date Fix:**
1. Gallery opens
2. Look at collapsed tabs
3. ✅ Should see: "Jan 8, 2025 • 3:45 PM" (readable date/time)
4. ❌ Should NOT see: Font license text, small unreadable metadata

**Test Bug 2 - Image Cutoff Fix:**
1. Click first accordion tab to expand
2. Photo displays fully visible
3. ✅ Can see entire image top to bottom
4. ❌ No cropping, no hidden content at bottom
5. Prompt text visible above image
6. Audio player visible below image

**Test Bug 3 - Duration Display:**
1. All collapsed tabs show duration
2. ✅ Format: "M:SS" (e.g., "3:45", "0:52", "12:30")
3. ✅ Positioned: [Play] [Thumbnail] [Prompt] [Date] [Duration] [Delete]
4. ❌ Duration not missing or cut off

**Integration Test:**
1. Create 5+ stories via Recording UI
2. Go to Gallery
3. All tabs display correctly: [Play] [Thumbnail] [Prompt] [Date] [Duration] [Delete]
4. Click any tab to expand → full image visible, audio player works
5. Click to collapse → returns to compact view
6. Other tabs shift down/up properly (no height loss)
7. Scroll through gallery if needed (multiple stories)
8. Delete button works with confirmation
9. No console errors

---

## Previous Work Summary

**Session 1 - Recording UI (Task 4):**
- Implemented recording flow: consent → recording → review → photo → saving
- Fixed positioning bugs (modals flash to center issue)
- Fixed button cutoff (Consent/Cancel buttons)
- Audio recording functional end-to-end

**Session 2 - Gallery v1 (Task 5):**
- Implemented full-size card layout (too large, didn't work)

**Session 3 - Gallery v2 (Task 5):**
- Implemented accordion structure (current state)
- Fixed tab height behavior (tabs shift properly)
- Fixed modal overlay/background blur
- Added play button and thumbnails
- **Still needs**: Date formatting fix, image cutoff fix, duration display

---

## Git Information

**Repository:** https://github.com/thestoryportal/story-portal-app-v2.git
**Branch:** main
**Recent commits:**
- Task 4 Recording fixes
- Task 5 Gallery initial implementation
- Task 5 Accordion redesign

---

## Next Steps After This Task

1. **Task 5 Complete** → Gallery fully functional with all bugs fixed
2. **Task 6** → Photo Gallery Enhancements (if needed) or move to Phase 2 Design Polish
3. **Phase 2** → Design and Polish across all components (scheduled after all MVP features complete)

---

## Notes for New Agent

- Previous agent made good progress on structure but missed data rendering bugs
- Font bug specifically suggests date formatting function returning wrong value (font object instead of string)
- Image cutoff is CSS-related, not component structure
- Duration is straightforward - just needs rendering on collapsed tabs
- Test thoroughly in browser before claiming complete
- All three bugs must be fixed for Task 5 to be complete
