# Story Portal — Component Architecture

**Version**: 1.0
**Date Created**: January 8, 2025
**Status**: Approved for MVP Implementation
**Related Specs**:
- [DESIGN_SYSTEM.md](./DESIGN_SYSTEM.md) (visual patterns, CSS Modules)
- [USER_FLOWS.md](./USER_FLOWS.md) (flows components implement)
- [DATA_MODEL.md](./DATA_MODEL.md) (data structures components consume)

---

## Table of Contents

1. [Overview](#overview)
2. [Architecture Principles](#architecture-principles)
3. [Folder Structure](#folder-structure)
4. [Component Inventory](#component-inventory)
5. [Component Hierarchy Diagram](#component-hierarchy-diagram)
6. [Data Flow Pattern](#data-flow-pattern)
7. [Core Containers (Smart Components)](#core-containers-smart-components)
8. [Feature Components (Dumb Components)](#feature-components-dumb-components)
9. [Shared Components (Existing)](#shared-components-existing)
10. [Hooks & Utilities](#hooks--utilities)
11. [Styling Approach](#styling-approach)
12. [Error Handling Strategy](#error-handling-strategy)
13. [Integration Checklist](#integration-checklist)

---

## Overview

The Story Portal uses a **container/presentational component pattern** with minimal state management:

- **Container Components** ("Smart"): Manage state, handle logic, use hooks
- **Presentational Components** ("Dumb"): Receive props, render UI, fire callbacks
- **Custom Hooks**: Encapsulate side effects (audio recording, storage, wheel physics)
- **CSS Modules**: Feature-level styling, following existing patterns

**MVP Philosophy**: Props + hooks only. No Context API, no Redux. Keep it simple and colocated.

---

## Architecture Principles

### 1. Props Over Context (MVP Constraint)

**Decision**: Defer Context API. Props + hooks work fine for MVP scope.

- Pass state down via props
- Use custom hooks for shared logic (not Context)
- Accept prop drilling—it's fine for a small app
- Phase 2: Add Context only if nesting becomes unwieldy

**Example**:
```tsx
<App>
  <WheelContainer prompt={selectedPrompt} onSelectPrompt={...} />
  <RecordingContainer prompt={selectedPrompt} onSave={...} />
</App>
```

### 2. Animation Logic Stays Colocated

**Decision**: Keep animation logic inside containers, not separate components.

- WheelContainer handles spin animation internally
- RecordingContainer manages waveform animation
- Don't over-abstract to `<AnimatedWheel>` yet
- If animation logic explodes, refactor then

### 3. CSS Modules for Complex, Inline for Simple

**Decision**: Use CSS Modules for feature-level styles, inline styles for variants.

**CSS Modules** (complex features):
```css
/* WheelView.module.css */
.container { /* wheel-specific layout */ }
.spinning { /* animation state */ }
```

**Inline Styles** (simple variants):
```tsx
<button style={{ opacity: disabled ? 0.6 : 1 }} />
```

**Avoid**: CSS-in-JS libraries (styled-components, emotion). Not in tech stack.

### 4. Basic Error Recovery (Not Enterprise Patterns)

**Decision**: Show fallbacks, don't crash. Formal Error Boundary is Phase 2.

**Pattern**:
```tsx
if (recordingError) {
  return <div>Recording failed. Try again.</div>
}
```

**NOT** yet: Error Boundary component, error logger, error tracking.

### 5. Practical Data Flow

**Decision**: State lives at app level, passed down via props. Side effects in hooks.

- `LegacyApp.tsx` = source of truth for current prompt, stories, etc.
- Props flow down
- Callbacks flow up
- Hooks handle side effects (MediaRecorder, IndexedDB)

---

## Folder Structure

```
src/
├── components/
│   ├── layouts/                  # Page layout shells
│   │   ├── AppLayout.tsx         # Root layout + nav + menu (NEW)
│   │   └── index.ts
│   │
│   ├── views/                    # Page-level containers (mirrors USER_FLOWS)
│   │   ├── WheelView.tsx         # Spin wheel + prompt (NEW)
│   │   ├── WheelView.module.css  # Wheel styles (NEW)
│   │   ├── RecordingView.tsx     # Record + consent flow (NEW)
│   │   ├── RecordingView.module.css
│   │   ├── GalleryView.tsx       # My Stories gallery (NEW)
│   │   ├── GalleryView.module.css
│   │   ├── ContentView.tsx       # How to Play, About, etc. (NEW)
│   │   ├── ContentView.module.css
│   │   ├── OnboardingView.tsx    # Splash + intro (NEW)
│   │   └── index.ts
│   │
│   ├── wheel/                    # Wheel sub-components
│   │   ├── WheelCanvas.tsx       # 3D wheel rendering (NEW)
│   │   ├── WheelCanvas.module.css
│   │   ├── PromptPanel.tsx       # Single wheel panel (NEW)
│   │   ├── PromptDisplay.tsx     # Selected prompt + flame (NEW)
│   │   ├── ContemplationHints.tsx # Cycling facilitation hints (NEW)
│   │   ├── TopicPickerModal.tsx  # Topic pack selector (NEW)
│   │   └── index.ts
│   │
│   ├── recording/                # Recording sub-components
│   │   ├── RecordingUI.tsx       # Waveform + timer + controls (NEW)
│   │   ├── RecordingUI.module.css
│   │   ├── ReviewScreen.tsx      # Playback after recording (NEW)
│   │   ├── ConsentFlow.tsx       # Consent modal (NEW)
│   │   ├── PhotoPrompt.tsx       # Add photo UI (NEW)
│   │   └── index.ts
│   │
│   ├── gallery/                  # Gallery sub-components
│   │   ├── StoryCard.tsx         # Gallery item preview (NEW)
│   │   ├── StoryDetail.tsx       # Full story view + playback (NEW)
│   │   ├── AudioPlayer.tsx       # Playback controls (NEW)
│   │   ├── DeleteConfirmModal.tsx # Delete confirmation (NEW)
│   │   └── index.ts
│   │
│   ├── navigation/               # Nav components
│   │   ├── Navigation.tsx        # Top nav buttons (NEW)
│   │   ├── HamburgerMenu.tsx     # Menu toggle + panel (NEW)
│   │   ├── MenuPanel.tsx         # Menu items (NEW)
│   │   └── index.ts
│   │
│   ├── form/                     # Reusable form components (EXISTING)
│   │   ├── FormButton.tsx        # Steampunk button ✅
│   │   ├── FormInput.tsx         # Text input ✅
│   │   ├── FormField.tsx         # Label + input ✅
│   │   ├── BookingForm.tsx       # Booking form ✅
│   │   ├── BookingModal.tsx      # Modal wrapper ✅
│   │   └── index.ts
│   │
│   ├── modal/                    # Modal system (EXISTING)
│   │   ├── ModalContentWindow.tsx # Universal modal ✅
│   │   └── index.ts
│   │
│   ├── common/                   # Shared presentational
│   │   ├── Button.tsx            # Button wrapper (NEW)
│   │   ├── Icon.tsx              # Icon wrapper (NEW)
│   │   ├── Divider.tsx           # Visual separator (NEW)
│   │   ├── Toast.tsx             # Notifications (NEW)
│   │   └── index.ts
│   │
│   └── App.tsx                   # Root component
│
├── hooks/                        # Custom React hooks
│   ├── useWheel.ts              # Wheel physics + selection (NEW)
│   ├── useRecording.ts          # Audio recording lifecycle (NEW)
│   ├── useLocalStorage.ts       # IndexedDB wrapper (NEW)
│   ├── useOnboarding.ts         # First-time tracking (NEW)
│   ├── useMediaQuery.ts         # Responsive breakpoint (NEW)
│   └── index.ts
│
├── types/                        # TypeScript interfaces
│   ├── index.ts
│   ├── story.ts                 # Story, Prompt, StoryRecord (NEW)
│   ├── wheel.ts                 # Wheel state types (NEW)
│   ├── recording.ts             # Recording state types (NEW)
│   └── ui.ts                    # UI state types (NEW)
│
├── utils/                        # Pure utility functions
│   ├── storage.ts               # IndexedDB operations (NEW)
│   ├── prompt.ts                # Prompt selection logic (NEW)
│   ├── validation.ts            # Form validation (NEW)
│   ├── formatting.ts            # Time/duration formatting (NEW)
│   └── index.ts
│
├── constants/                   # App constants
│   ├── prompts.ts              # Prompt database ✅
│   ├── config.ts               # Configuration ✅
│   └── index.ts
│
├── tokens/                      # Design system
│   ├── design-tokens.css        # CSS variables ✅
│   └── colors.css               # Semantic colors ✅
│
└── index.css                    # Global imports ✅
```

---

## Component Inventory

### Existing Components (✅ Reuse)

| Component | Location | Purpose | Status |
|---|---|---|---|
| `FormButton` | `src/components/form/` | Steampunk styled button | ✅ Use as-is |
| `FormInput` | `src/components/form/` | Text input field | ✅ Use as-is |
| `FormField` | `src/components/form/` | Label + input wrapper | ✅ Use as-is |
| `BookingForm` | `src/components/form/` | Booking inquiry form | ✅ Use as-is |
| `BookingModal` | `src/components/form/` | Booking modal wrapper | ✅ Use as-is |
| `ModalContentWindow` | `src/components/modal/` | Universal modal frame | ✅ Use as-is |

### New Components (❌ Build for MVP)

**Total NEW: 28 components**

#### Layout Components (1)
- `AppLayout` — Root page layout with nav + hamburger

#### View/Container Components (5)
- `WheelView` — Spin wheel + prompt display
- `RecordingView` — Recording interface
- `GalleryView` — My Stories gallery
- `ContentView` — How to Play, About, Privacy, Booking pages
- `OnboardingView` — Splash screen + wheel intro

#### Wheel Components (5)
- `WheelCanvas` — 3D wheel rendering
- `PromptPanel` — Single wheel panel
- `PromptDisplay` — Selected prompt + flame animation
- `ContemplationHints` — Cycling facilitation cues
- `TopicPickerModal` — Topic pack selector

#### Recording Components (4)
- `RecordingUI` — Waveform, timer, controls
- `ReviewScreen` — Playback after recording
- `ConsentFlow` — Consent script + email
- `PhotoPrompt` — Add photo UI

#### Gallery Components (4)
- `StoryCard` — Gallery preview
- `StoryDetail` — Full story view
- `AudioPlayer` — Playback controls
- `DeleteConfirmModal` — Delete confirmation

#### Navigation Components (3)
- `Navigation` — Top nav buttons
- `HamburgerMenu` — Menu toggle + panel
- `MenuPanel` — Menu items list

#### Common Components (5)
- `Button` — Button wrapper
- `Icon` — Icon wrapper
- `Divider` — Visual separator
- `Toast` — Toast notifications
- `Loading` — Loading indicator

---

## Component Hierarchy Diagram

### ASCII Tree View

```
App (root)
├── AppLayout
│   ├── Navigation
│   │   └── Button (My Stories, How to Play)
│   ├── HamburgerMenu
│   │   └── MenuPanel
│   │       ├── Button (Our Story)
│   │       ├── Button (Our Work)
│   │       ├── Button (Privacy)
│   │       └── Button (Booking)
│   │
│   └── [Dynamic View Below]
│
├── WheelView (when active)
│   ├── WheelCanvas
│   │   └── PromptPanel (×20)
│   ├── PromptDisplay
│   ├── ContemplationHints (if accepted)
│   ├── Button (Record / New Topics)
│   └── [Modals]
│       └── TopicPickerModal
│
├── RecordingView (when active)
│   ├── ConsentFlow (if recording others)
│   │   ├── FormField (email)
│   │   └── FormButton
│   ├── RecordingUI
│   │   ├── Icon (waveform)
│   │   ├── Timer
│   │   └── RecordingControls (Pause, Stop)
│   ├── ReviewScreen
│   │   ├── AudioPlayer
│   │   ├── Button (Keep)
│   │   └── Button (Re-record)
│   ├── PhotoPrompt
│   │   └── Button (Add Photo / Skip)
│   └── Button (Save)
│
├── GalleryView (when active)
│   ├── [Empty State OR List]
│   ├── StoryCard (×N)
│   └── StoryDetail (if selected)
│       ├── AudioPlayer
│       ├── Button (Delete)
│       └── DeleteConfirmModal
│
├── ContentView (when active)
│   ├── HowToPlayPage
│   ├── OurStoryPage
│   ├── OurWorkPage
│   ├── PrivacyPolicyPage
│   └── BookingPage
│
└── OnboardingView (first-time only)
    ├── SplashScreen
    └── WheelIntro

[Modals - Layer Above All]
├── TopicPickerModal (from WheelView)
├── DeleteConfirmModal (from StoryDetail)
├── PermissionErrorModal (mic, camera denied)
└── Toast (notifications)
```

---

## Data Flow Pattern

### State Management: Props Down, Callbacks Up

```
App
├── state: { selectedPrompt, stories, currentView, isFirstTime, ... }
├──
├── WheelView (receives: selectedPrompt, onSelectPrompt, onRecord)
│   ├── WheelCanvas (receives: selectedPrompt)
│   │   └── PromptPanel (receives: text, isSelected)
│   ├── PromptDisplay (receives: selectedPrompt)
│   └── Button Record (fires: onRecord callback)
│
├── RecordingView (receives: selectedPrompt, onSave, onCancel)
│   ├── RecordingUI (receives: isRecording, duration)
│   ├── ReviewScreen (receives: audioBlob, duration)
│   └── Button Save (fires: onSave callback → App saves to storage)
│
└── GalleryView (receives: stories)
    ├── StoryCard (receives: story object)
    └── StoryDetail (receives: selectedStory, onDelete)
        └── Button Delete (fires: onDelete callback)
```

### Data Flow Example: Wheel → Recording → Storage

```
1. User spins wheel in WheelView
   └─ WheelView fires onPromptSelected("When I fell in love")
   └─ App updates state.selectedPrompt

2. User taps Record button
   └─ App switches to RecordingView
   └─ RecordingView receives prompt via props

3. User grants microphone, records, stops
   └─ RecordingView creates audioBlob
   └─ User taps "Keep" → ReviewScreen fires onSave(StoryRecord)

4. App receives story object
   └─ App calls useLocalStorage.save(story)
   └─ Hook saves to IndexedDB
   └─ App switches to GalleryView
   └─ GalleryView fetches fresh stories and displays

5. User views story in GalleryView
   └─ StoryDetail receives story object
   └─ AudioPlayer plays audioBlob
```

---

## Core Containers (Smart Components)

Smart components manage state and side effects. They use hooks and pass data down via props.

### 1. App (Root)

**File**: `src/components/App.tsx`

**Responsibility**:
- Central state manager for MVP
- Route between views
- Load prompts on mount

**Props**: None (root component)

**State**:
```typescript
{
  selectedPrompt: string | null,          // Current wheel selection
  stories: StoryRecord[],                 // Saved stories from storage
  currentView: 'wheel' | 'recording' | 'gallery' | 'content' | 'onboarding',
  currentContentPage: string | null,      // Which content page to show
  isFirstTime: boolean,                   // Onboarding flag
  recordingOther: boolean,                // Recording self or someone else?
}
```

**Hooks Used**:
- `useOnboarding()` — Track first-time user
- `useLocalStorage('stories')` — Fetch stories on mount

**Key Methods**:
```typescript
handlePromptSelected(prompt: string) {
  setSelectedPrompt(prompt)
}

handleStartRecording() {
  setCurrentView('recording')
}

handleSaveStory(story: StoryRecord) {
  saveToStorage(story)
  setCurrentView('gallery')
  fetchStoriesFromStorage()
}

handleNavigate(view: string, page?: string) {
  setCurrentView(view)
  if (page) setCurrentContentPage(page)
}
```

**Data Dependencies**:
- `Prompt[]` from constants/prompts.ts
- `StoryRecord[]` from IndexedDB (via useLocalStorage)

**Styling**: None (layout managed by AppLayout)

**Status**: ✅ Refactor existing LegacyApp.tsx or use as template

---

### 2. WheelView

**File**: `src/components/views/WheelView.tsx`

**Responsibility**:
- Manage wheel spin state (rotation, velocity)
- Handle prompt selection
- Enforce pass rule (first spin can pass, second cannot)
- Render wheel + prompt display

**Props**:
```typescript
{
  prompt: string | null,                  // Currently selected prompt
  onPromptSelected: (prompt: string) => void,
  onStartRecording: () => void,
  onViewChange: (view: string) => void,
}
```

**State**:
```typescript
{
  rotation: number,                       // CSS rotation value (degrees)
  isSpinning: boolean,
  spinCount: number,                      // 0 = no spins, 1 = can pass, 2+ = must accept
  showHints: boolean,                     // Show facilitation hints?
}
```

**Hooks Used**:
- `useWheel(prompts)` — Wheel physics + landing calculation
- `useMediaQuery('(prefers-reduced-motion: reduce)')` — Animation preference

**Key Methods**:
```typescript
handleSpin(delta: number) {
  // Pass to useWheel hook, which handles physics
  // Hook returns final rotation + landed prompt
  // Fire onPromptSelected with landed prompt
}

handlePass() {
  if (spinCount === 0) {
    handleSpin() // Spin again
    spinCount++
  }
  // Can't pass on second spin
}

handleRecord() {
  onStartRecording() // Switch to RecordingView
}
```

**Styling**: `WheelView.module.css`
- `.wheelContainer` — Layout
- `.wheelCanvas` — 3D perspective
- `.promptDisplay` — Selected prompt area
- `.hints` — Facilitation hints area
- `.buttons` — Record + Topic buttons

**Data Dependencies**:
- `Prompt[]` (all available prompts)
- Current selected prompt

**Status**: ❌ NEW — Refactor existing wheel code from legacy/

---

### 3. RecordingView

**File**: `src/components/views/RecordingView.tsx`

**Responsibility**:
- Manage recording lifecycle (requesting permission, recording, stopping, review, save)
- Handle consent flow for recording others
- Save story to storage
- Handle errors (mic denied, storage full)

**Props**:
```typescript
{
  prompt: string,                         // The prompt being answered
  onSaveStory: (story: StoryRecord) => void,
  onCancel: () => void,                   // Back to wheel
  recordingOther?: boolean,               // Recording someone else?
}
```

**State**:
```typescript
{
  stage: 'consent' | 'recording' | 'review' | 'saving',
  isRecording: boolean,
  isPaused: boolean,
  audioBlob: Blob | null,
  duration: number,                       // Seconds
  waveformData: number[],                 // For visualization
  consentStatus: 'pending' | 'confirmed',
  storytellerEmail: string | null,
  storytellerName: string | null,
  error: string | null,                   // Error message for user
}
```

**Hooks Used**:
- `useRecording()` — Audio capture + permission handling
- `useLocalStorage('stories')` — Save to IndexedDB
- `useMediaQuery('(prefers-reduced-motion: reduce)')` — Reduced motion check

**Key Methods**:
```typescript
async handleStartRecording() {
  try {
    await requestMicPermission()
    startAudioCapture()
    setIsRecording(true)
  } catch (err) {
    if (err.name === 'NotAllowedError') {
      setError('Microphone access denied. Please check browser settings.')
    }
  }
}

handleStop() {
  stopAudioCapture()
  setIsRecording(false)
  setStage('review')
}

async handleSave() {
  setStage('saving')
  const story = {
    id: uuid(),
    audioBlob,
    prompt,
    timestamp: new Date().toISOString(),
    duration,
    consent: { type: recordingOther ? 'other' : 'self', ... },
    storytellerEmail,
  }
  await saveStory(story)  // via useLocalStorage
  onSaveStory(story)
}
```

**Styling**: `RecordingView.module.css`
- `.recordingContainer` — Layout
- `.waveform` — Waveform display
- `.timer` — Duration timer
- `.controls` — Play/pause/stop buttons
- `.review` — Playback controls
- `.consent` — Consent modal styling

**Data Dependencies**:
- Current prompt (received via props)
- StoryRecord interface for saved data

**Error Handling**:
- Mic permission denied → Show friendly message, link to settings
- Storage full → Show "Delete some stories to make room"
- Recording interrupted → Show "Recording stopped, try again?"

**Status**: ❌ NEW

---

### 4. GalleryView

**File**: `src/components/views/GalleryView.tsx`

**Responsibility**:
- Load and display all saved stories
- Navigate to story detail
- Handle story deletion
- Show empty state if no stories

**Props**:
```typescript
{
  stories: StoryRecord[],
  onStoryDeleted: (storyId: string) => void,
  onBack: () => void,
}
```

**State**:
```typescript
{
  selectedStoryId: string | null,
  isDeleteConfirming: boolean,
  deleteTargetId: string | null,
  isLoading: boolean,
  error: string | null,
}
```

**Hooks Used**:
- `useLocalStorage('stories')` — Fetch stories from IndexedDB
- `useMediaQuery()` — Responsive layout

**Key Methods**:
```typescript
async handleDelete(storyId: string) {
  await deleteStory(storyId)  // via hook
  refetchStories()
  onStoryDeleted(storyId)
}

handleSelectStory(storyId: string) {
  setSelectedStoryId(storyId)
}

handleBack() {
  setSelectedStoryId(null)
  onBack()
}
```

**Styling**: `GalleryView.module.css`
- `.gallery` — List container
- `.emptyState` — "Tell your first story" message
- `.storyCardGrid` — Card layout
- `.detail` — Story detail view

**Data Dependencies**:
- `StoryRecord[]` array from storage
- Current selected story

**Status**: ❌ NEW

---

## Feature Components (Dumb Components)

Dumb components receive all data via props. No hooks, no side effects. Just render.

### Wheel Feature

| Component | Props | Renders | CSS |
|---|---|---|---|
| **WheelCanvas** | `rotation, prompts, panelHeight, fontSize` | 3D wheel with panels | `WheelCanvas.module.css` |
| **PromptPanel** | `prompt, index, panelHeight, fontSize` | Single wheel panel with carved text | Inline (simple) |
| **PromptDisplay** | `prompt, isSelected` | Large prompt + flame animation | Inline + module |
| **ContemplationHints** | `prompt, isDeclarationRisk` | Cycling hints (4s each) | Inline |
| **TopicPickerModal** | `isOpen, packs, onSelect, onClose` | Modal with topic pack list | Modal.module.css |

**Data Dependencies**:
- `Prompt` interface from types/story.ts
- `TopicPack` interface from types/story.ts
- Animation state from container

### Recording Feature

| Component | Props | Renders | CSS |
|---|---|---|---|
| **RecordingUI** | `isRecording, duration, waveformData, onStop, onPause` | Waveform + timer + controls | `RecordingUI.module.css` |
| **ReviewScreen** | `audioBlob, duration, onKeep, onRerecord` | Playback + Keep/Re-record buttons | Inline |
| **ConsentFlow** | `onConsent, onEmailChange, onSkip` | Consent script + email input + buttons | `ConsentFlow.module.css` |
| **PhotoPrompt** | `onAddPhoto, onSkip` | "Add Photo" or "Skip" buttons | Inline |

**Data Dependencies**:
- `StoryRecord` interface
- `Blob` for audio
- Form field types

### Gallery Feature

| Component | Props | Renders | CSS |
|---|---|---|---|
| **StoryCard** | `story, onSelect, isSelected` | Card with prompt, date, duration, photo | `StoryCard.module.css` |
| **StoryDetail** | `story, onDelete, onBack` | Full story + player + metadata + delete | `StoryDetail.module.css` |
| **AudioPlayer** | `audioBlob, duration, onPlay, onStop` | Play/pause/scrubber + duration | Inline |
| **DeleteConfirmModal** | `isOpen, storyId, onConfirm, onCancel` | Confirmation dialog | Modal.module.css |

**Data Dependencies**:
- `StoryRecord` interface
- `Blob` for audio
- Formatting utilities for dates

### Navigation

| Component | Props | Renders | CSS |
|---|---|---|---|
| **Navigation** | `onMyStories, onHowToPlay` | Top button group | Inline |
| **HamburgerMenu** | `isOpen, onToggle, onSelect` | Hamburger icon + menu panel | `HamburgerMenu.module.css` |
| **MenuPanel** | `isOpen, items, onSelect` | List of menu items | Inline |

---

## Shared Components (Existing)

Reuse these without modification:

### Form Components
- **FormButton** — Use for all primary/secondary buttons
- **FormInput** — Use for email, text inputs
- **FormField** — Wrap inputs with labels

### Modal System
- **ModalContentWindow** — Wrap any modal content

**Usage Example**:
```tsx
<ModalContentWindow
  title="Delete Story?"
  onClose={handleCancel}
  closeOnBackdropClick={true}
>
  <p>Are you sure you want to delete this story?</p>
  <button onClick={handleConfirmDelete}>Delete</button>
</ModalContentWindow>
```

---

## Hooks & Utilities

### Custom Hooks

#### useWheel(prompts: string[])
**File**: `src/hooks/useWheel.ts`

**Manages**:
- Wheel rotation physics (velocity, friction, deceleration)
- Spin detection and momentum
- Prompt landing calculation
- Pass rule enforcement

**Returns**:
```typescript
{
  rotation: number,
  isSpinning: boolean,
  selectedPrompt: string | null,
  spinCount: number,
  startSpin: (delta: number) => void,
  buttonSpin: () => void,
  resetPhysics: () => void,
  canPass: () => boolean,
}
```

**Usage**:
```tsx
const { rotation, selectedPrompt, startSpin } = useWheel(prompts)
```

#### useRecording()
**File**: `src/hooks/useRecording.ts`

**Manages**:
- MediaRecorder API
- Permission requests
- Audio blob capture
- Pause/resume
- Waveform data collection

**Returns**:
```typescript
{
  isRecording: boolean,
  isPaused: boolean,
  audioBlob: Blob | null,
  duration: number,
  waveformData: number[],
  error: Error | null,
  startRecording: () => Promise<void>,
  pauseRecording: () => void,
  resumeRecording: () => void,
  stopRecording: () => Blob,
}
```

**Usage**:
```tsx
const { startRecording, audioBlob, stopRecording } = useRecording()
await startRecording()
// ... user speaks
const blob = stopRecording()
```

#### useLocalStorage(key: string)
**File**: `src/hooks/useLocalStorage.ts`

**Manages**:
- IndexedDB via localForage
- Async read/write/delete
- Loading state

**Returns**:
```typescript
{
  data: T | null,
  loading: boolean,
  error: Error | null,
  setData: (value: T) => Promise<void>,
  removeData: (id: string) => Promise<void>,
  refetch: () => Promise<void>,
}
```

**Usage**:
```tsx
const { data: stories, setData: saveStory } = useLocalStorage<StoryRecord[]>('stories')
await saveStory(newStory)
```

#### useOnboarding()
**File**: `src/hooks/useOnboarding.ts`

**Manages**:
- First-time user detection
- Onboarding completion tracking

**Returns**:
```typescript
{
  isFirstTime: boolean,
  markOnboardingComplete: () => void,
}
```

#### useMediaQuery(query: string)
**File**: `src/hooks/useMediaQuery.ts`

**Manages**:
- Responsive design queries
- Motion preferences

**Returns**: `boolean`

**Usage**:
```tsx
const prefersReducedMotion = useMediaQuery('(prefers-reduced-motion: reduce)')
const isMobile = useMediaQuery('(max-width: 480px)')
```

### Utility Functions

| Utility | File | Purpose |
|---|---|---|
| `saveStory(story)` | `src/utils/storage.ts` | Save StoryRecord to IndexedDB |
| `getStories()` | `src/utils/storage.ts` | Fetch all stories |
| `deleteStory(id)` | `src/utils/storage.ts` | Delete by ID |
| `selectRandomPrompt(prompts)` | `src/utils/prompt.ts` | Pick from array |
| `calculateWheelLanding(rotation, panelCount)` | `src/utils/prompt.ts` | Which panel landed? |
| `validateEmail(email)` | `src/utils/validation.ts` | Check email format |
| `formatDuration(seconds)` | `src/utils/formatting.ts` | Convert to MM:SS |
| `formatDate(timestamp)` | `src/utils/formatting.ts` | Convert to "2 days ago" |

---

## Styling Approach

### CSS Modules (Complex Features)

Use for views and feature components with multiple styles:

```css
/* WheelView.module.css */
.wheelContainer {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--sp-spacing-xl);
  padding: var(--sp-spacing-md);
}

.wheelCanvas {
  width: min(90vw, 600px);
  aspect-ratio: 1;
  perspective: 800px;
}

.spinning .wheelCanvas {
  animation: wheelSpin 2s var(--sp-easing-physics);
}

@keyframes wheelSpin {
  from { transform: rotateX(0deg); }
  to { transform: rotateX(var(--final-rotation)); }
}
```

**Usage in component**:
```tsx
import styles from './WheelView.module.css'

export function WheelView() {
  return (
    <div className={styles.wheelContainer}>
      <div className={styles.wheelCanvas}>
        {/* wheel content */}
      </div>
    </div>
  )
}
```

### Inline Styles (Simple Variants)

Use for conditional, dynamic styles:

```tsx
<button
  style={{
    opacity: disabled ? 0.6 : 1,
    cursor: disabled ? 'not-allowed' : 'pointer',
    color: 'var(--text-on-dark)',  // Always use tokens!
  }}
>
  Click Me
</button>
```

### CSS Custom Properties (Always)

Reference semantic color variables from `src/tokens/colors.css`:

```css
.button {
  background: var(--color-wood-mid);
  border: 2px solid var(--color-bronze-standard);
  color: var(--text-on-dark);
}

.button:hover {
  border-color: var(--color-bronze-bright);
}

.button:focus {
  outline: 3px solid var(--color-flame-core);
}
```

### Animation Patterns

All animations respect `prefers-reduced-motion`:

```css
@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

.modal {
  animation: fadeIn var(--sp-duration-quick) var(--sp-easing-standard);
}

/* This is already global in src/tokens/colors.css: */
@media (prefers-reduced-motion: reduce) {
  * {
    animation-duration: 0.01ms !important;
  }
}
```

---

## Error Handling Strategy

### Practical Error Recovery (Not Enterprise)

**Philosophy**: Show user-friendly fallbacks. Don't crash the app.

### Pattern 1: Try-Catch with Fallback UI

```tsx
export function RecordingView() {
  const [error, setError] = useState<string | null>(null)

  const handleStartRecording = async () => {
    try {
      await requestMicPermission()
      startAudioCapture()
    } catch (err) {
      if (err.name === 'NotAllowedError') {
        setError('Microphone access denied. Please check browser settings.')
      } else {
        setError('Recording failed. Try again.')
      }
    }
  }

  if (error) {
    return (
      <div className={styles.error}>
        <p>{error}</p>
        <button onClick={() => setError(null)}>Try Again</button>
      </div>
    )
  }

  return <RecordingUI onStartRecording={handleStartRecording} />
}
```

### Pattern 2: Storage Errors

```tsx
async function handleSaveStory(story: StoryRecord) {
  try {
    await saveToIndexedDB(story)
    navigateToGallery()
  } catch (err) {
    if (err.name === 'QuotaExceededError') {
      setError('Storage full. Delete some stories to make room.')
    } else {
      setError('Couldn\'t save story. Try again.')
    }
  }
}
```

### What NOT to Do (Phase 2)

- ❌ Formal Error Boundary component (not MVP)
- ❌ Error tracking service (Sentry, etc.)
- ❌ Detailed error logging
- ❌ Recovery wizards

---

## Integration Checklist

Before component goes to QA:

- ✅ Receives all required props
- ✅ Handles null/undefined gracefully
- ✅ Shows loading state (if async)
- ✅ Shows error fallback (if can fail)
- ✅ Uses CSS Modules (if complex) or inline styles (if simple)
- ✅ Respects `prefers-reduced-motion`
- ✅ Keyboard accessible (if interactive)
- ✅ Touch targets 44×44px minimum
- ✅ Color contrast 4.5:1 (WCAG AA)
- ✅ Renders correctly on 375px, 768px, 1024px
- ✅ All colors use semantic tokens (`var(--color-brass-light)`, etc.)

---

## Implementation Sequence (Critical Path)

### Week 1: Core Loop
1. **WheelView** (most complex, build first)
   - WheelCanvas, PromptPanel, PromptDisplay, ContemplationHints
   - useWheel hook
2. **RecordingView** (depends on wheel selection)
   - RecordingUI, ReviewScreen, ConsentFlow, PhotoPrompt
   - useRecording hook, useLocalStorage hook
3. **Storage** (IndexedDB CRUD)
   - useLocalStorage hook
   - storage.ts utilities

### Week 2: Gallery & Navigation
4. **GalleryView** (displays what was saved)
   - StoryCard, StoryDetail, AudioPlayer, DeleteConfirmModal
5. **Navigation** & **HamburgerMenu**
   - Navigation.tsx, HamburgerMenu.tsx, MenuPanel.tsx

### Week 3: Polish & Content
6. **OnboardingView** (splash screen, first-time intro)
7. **ContentView** (How to Play, Our Story, About, Privacy, Booking)
8. Error handling, animations, accessibility

---

## Notes on Refactoring Existing Code

### Reuse from Legacy

- Wheel physics from `src/legacy/` can inform `useWheel.ts` hook
- Button styles from `buttons.css` already applied via `FormButton`
- Animation keyframes from `animations.css` can be adapted

### Don't Reuse

- Legacy state management patterns (if overly complex)
- Smoke/electricity effects (clean slate per spec)
- Test/debug components

---

*Last Updated: January 8, 2025*
*Approved: All 5 open questions answered and integrated*
