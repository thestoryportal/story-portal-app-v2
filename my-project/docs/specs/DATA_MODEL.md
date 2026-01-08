# Data Model Specification

**Version**: 1.0
**Last Updated**: January 8, 2025
**Status**: MVP Ready

---

## Table of Contents

1. [Overview](#1-overview)
2. [Core Data Structures](#2-core-data-structures)
3. [TypeScript Interfaces](#3-typescript-interfaces)
4. [IndexedDB Schema](#4-indexeddb-schema)
5. [CRUD Operations](#5-crud-operations)
6. [Business Logic](#6-business-logic)
7. [Validation Rules](#7-validation-rules)
8. [Storage & Quota Management](#8-storage--quota-management)
9. [Constants](#9-constants)
10. [Phase 2 Extensions](#10-phase-2-extensions)

---

## 1. Overview

### Design Philosophy

The Story Portal's data model is intentionally **local-first and offline-first**. All data lives in IndexedDB on the user's device; there is no backend in MVP. This ensures:

- **Privacy**: Stories never leave the device unless user explicitly shares (Phase 2)
- **Offline-first**: Core functionality works without internet
- **Simplicity**: No server sync, auth, or database complexity during MVP
- **Accessibility**: Disability accommodation features are built-in (no server-side calculations needed)

### Data Ownership

**The user owns all their data.** The app provides no account system in MVP, so all data persists only on that device. Users can:
- View all their stories locally
- Delete stories anytime
- Export stories if we add export features (Phase 2)
- Clear all data by clearing browser storage

### Principles

1. **Blob Storage is Native**: IndexedDB handles audio Blobs natively. No special serialization required—just store and retrieve directly.
2. **UUID Generation is Lightweight**: Use native `crypto.randomUUID()` browser API (zero dependencies). Alternative `nanoid` is lightweight but not required for MVP.
3. **Validation is Architectural**: Document validation rules as a specification table (what to validate), not as code implementations. Code validation happens in components/hooks.
4. **Graceful Quota Management**: Before recording, check device storage using `navigator.storage.estimate()`. If full, show user message: *"Device storage is full. Delete old stories to record new ones."* and prevent recording.

---

## 2. Core Data Structures

### 2.1 Prompt

Represents a single prompt displayed on the wheel. Immutable—prompts come from `/docs/prompts.json`.

```
{
  id: string (UUID)
  text: string (60–90 characters)
  category?: string (e.g., "Love & Relationships", deferred to Phase 2)
  declaration_risk: "low" | "medium" | "high"
  facilitation_hint?: string (guide for storyteller, 20–50 words)
  created_at: ISO 8601 timestamp
}
```

**Example:**
```json
{
  "id": "a1b2-c3d4-e5f6-g7h8",
  "text": "Tell us about a moment when you realized someone truly saw you.",
  "category": "Intimacy",
  "declaration_risk": "medium",
  "facilitation_hint": "Instead of explaining what being 'seen' means to you, tell us about a specific moment.",
  "created_at": "2024-12-20T10:30:00Z"
}
```

### 2.2 Story Record

Represents a single story recorded and stored locally. This is the primary record the user creates when they spin the wheel, get a prompt, and record their response.

```
{
  id: string (UUID, unique story identifier)
  prompt_id: string (UUID reference to Prompt)
  prompt_text: string (denormalized copy at time of recording)
  audio_blob: Blob (WebM or MP4 format, max 5 min, 2–4MB typical)
  audio_duration_seconds: number
  audio_format: "audio/webm" | "audio/mp4"

  // Metadata
  created_at: ISO 8601 timestamp
  updated_at: ISO 8601 timestamp

  // Optional attachments
  photo?: {
    blob: Blob (WebP, max 2MB)
    filename: string
    upload_date: ISO 8601 timestamp
  }

  // Story metadata
  storyteller_name?: string (optional, entered during consent flow)
  storyteller_pronouns?: string (optional, e.g., "they/them")

  // Consent tracking
  consent: {
    verbal_confirmed: boolean (user tapped consent before recording)
    email_confirmed?: boolean (Phase 2: email approval)
    consent_date: ISO 8601 timestamp
    consent_version: string (e.g., "1.0" for tracking consent law changes)
  }

  // Sharing status (Phase 2)
  sharing_status: "private" | "shared" (default: "private" in MVP)
  shared_link?: string (Phase 2)

  // Deletion tracking
  marked_for_deletion?: boolean (soft delete, user can recover)
  deleted_at?: ISO 8601 timestamp
}
```

**Example:**
```json
{
  "id": "story-uuid-12345",
  "prompt_id": "a1b2-c3d4-e5f6-g7h8",
  "prompt_text": "Tell us about a moment when you realized someone truly saw you.",
  "audio_blob": <Blob>,
  "audio_duration_seconds": 187,
  "audio_format": "audio/webm",
  "created_at": "2025-01-08T14:22:00Z",
  "updated_at": "2025-01-08T14:22:00Z",
  "photo": null,
  "storyteller_name": "Maya",
  "storyteller_pronouns": "she/her",
  "consent": {
    "verbal_confirmed": true,
    "consent_date": "2025-01-08T14:22:00Z",
    "consent_version": "1.0"
  },
  "sharing_status": "private"
}
```

### 2.3 Topic Pack

Represents a set of prompts bundled together (e.g., "Love & Relationships," "Everyday Wisdom"). In MVP, there's only one pack ("Default"). Phase 2 allows switching between packs.

```
{
  id: string (UUID)
  name: string (e.g., "Love & Relationships")
  description?: string
  prompts: Prompt[] (array of 20 prompts in rotation order)
  created_at: ISO 8601 timestamp
  active: boolean (only one pack active at a time in MVP)
}
```

### 2.4 Onboarding State

Tracks whether the user has seen onboarding screens.

```
{
  has_seen_how_to_play: boolean
  has_seen_consent_explanation: boolean
  last_onboarding_date: ISO 8601 timestamp
  version: string (e.g., "1.0" for onboarding content updates)
}
```

### 2.5 App Settings (MVP Future)

Stores user preferences. **Note**: MVP has no Settings screen, but data structure is defined for Phase 2.

```
{
  theme: "light" | "dark" | "system" (default: "system")
  accessibility: {
    prefers_reduced_motion: boolean (read from OS via CSS media query, not user-set)
    high_contrast: boolean (Phase 2)
    enable_captions: boolean (Phase 2)
  }
  privacy: {
    analytics_enabled: boolean (default: true)
    crash_reports_enabled: boolean (default: true)
  }
}
```

---

## 3. TypeScript Interfaces

All interfaces are organized by concern in `/src/types/`:

### `/src/types/story.ts`

```typescript
export interface Prompt {
  id: string;
  text: string;
  category?: string;
  declaration_risk: 'low' | 'medium' | 'high';
  facilitation_hint?: string;
  created_at: string; // ISO 8601
}

export interface PhotoMetadata {
  blob: Blob;
  filename: string;
  upload_date: string; // ISO 8601
}

export interface ConsentData {
  verbal_confirmed: boolean;
  email_confirmed?: boolean;
  consent_date: string; // ISO 8601
  consent_version: string;
}

export interface StoryRecord {
  id: string;
  prompt_id: string;
  prompt_text: string;
  audio_blob: Blob;
  audio_duration_seconds: number;
  audio_format: 'audio/webm' | 'audio/mp4';
  created_at: string;
  updated_at: string;
  photo?: PhotoMetadata;
  storyteller_name?: string;
  storyteller_pronouns?: string;
  consent: ConsentData;
  sharing_status: 'private' | 'shared';
  shared_link?: string;
  marked_for_deletion?: boolean;
  deleted_at?: string;
}

export interface TopicPack {
  id: string;
  name: string;
  description?: string;
  prompts: Prompt[];
  created_at: string;
  active: boolean;
}

export interface OnboardingState {
  has_seen_how_to_play: boolean;
  has_seen_consent_explanation: boolean;
  last_onboarding_date: string;
  version: string;
}

export interface AppSettings {
  theme: 'light' | 'dark' | 'system';
  accessibility: {
    prefers_reduced_motion: boolean;
    high_contrast?: boolean;
    enable_captions?: boolean;
  };
  privacy: {
    analytics_enabled: boolean;
    crash_reports_enabled: boolean;
  };
}
```

### `/src/types/wheel.ts`

```typescript
export interface WheelState {
  current_prompt: Prompt | null;
  current_topic_pack_id: string;
  last_spin_timestamp: string | null;
  pass_count: number; // 0, 1, or 2 (2 = locked in)
  is_spinning: boolean;
  landed_prompt_index: number | null;
}

export interface WheelPhysics {
  initial_velocity: number; // pixels/frame
  friction: number; // 0–1 deceleration factor
  snap_threshold: number; // degrees to snap to prompt
  min_spin_duration: number; // milliseconds (e.g., 2000ms min spin)
}
```

### `/src/types/recording.ts`

```typescript
export interface RecordingState {
  is_recording: boolean;
  audio_chunks: Blob[]; // collected during recording
  duration_seconds: number;
  is_paused: boolean;
  error?: string; // e.g., "microphone_permission_denied"
}

export interface RecordingConfig {
  max_duration_seconds: number; // 300 (5 min)
  mime_type: string; // "audio/webm;codecs=opus" or "audio/mp4"
  audio_bitrate: number; // 64000–128000 bps
  sample_rate: number; // 48000 Hz ideal
}
```

### `/src/types/ui.ts`

```typescript
export interface NavigationState {
  current_screen: 'wheel' | 'contemplation' | 'recording' | 'gallery' | 'content';
  // 'wheel' = spinning wheel view
  // 'contemplation' = prompt display + facilitation hints
  // 'recording' = recording interface with controls
  // 'gallery' = "My Stories" view
  // 'content' = How to Play, Our Story, Our Work, Privacy Policy, Booking
}

export interface UIError {
  id: string;
  message: string;
  type: 'warning' | 'error' | 'critical';
  timestamp: string;
  dismissible: boolean;
}

export interface FeatureFlags {
  enable_photo_upload: boolean; // should be true in MVP
  enable_topic_pack_switching: boolean; // true in MVP
  enable_analytics: boolean; // true in MVP
  enable_offline_mode: boolean; // true in MVP
}
```

---

## 4. IndexedDB Schema

### Database: `StoryPortalDB` (version 1)

Uses **localForage** to abstract IndexedDB API. Direct IndexedDB schema (if needed):

#### Object Store: `stories`

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| `id` (key) | string | PRIMARY KEY, unique | UUID |
| `prompt_id` | string | indexed | For querying by prompt |
| `audio_blob` | Blob | required | WebM or MP4 |
| `audio_duration_seconds` | number | required | 0–300 |
| `created_at` | string | indexed | ISO 8601 timestamp |
| `updated_at` | string | indexed | For sorting recent stories |
| `consent.verbal_confirmed` | boolean | required | Must be true to store |
| `storyteller_name` | string | optional | Free-text field |
| `sharing_status` | string | indexed | "private" or "shared" |
| `marked_for_deletion` | boolean | indexed | For soft deletes |

**Indexes:**
- `created_at` — for "Most Recent" sorting
- `prompt_id` — for querying stories by prompt
- `sharing_status` — for Phase 2 filtering
- `marked_for_deletion` — for soft-delete recovery

#### Object Store: `prompts`

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| `id` (key) | string | PRIMARY KEY, unique | UUID |
| `text` | string | required | 60–90 chars |
| `declaration_risk` | string | indexed | "low", "medium", "high" |
| `facilitation_hint` | string | optional | 20–50 words |
| `created_at` | string | indexed | Populated from `/docs/prompts.json` |

#### Object Store: `topic_packs`

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| `id` (key) | string | PRIMARY KEY, unique | UUID |
| `name` | string | required | E.g., "Default" |
| `prompts` (array) | string[] | required | Array of prompt IDs |
| `active` | boolean | indexed | Only one true at a time |

#### Object Store: `onboarding`

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| `id` (key) | string | PRIMARY KEY | Always "onboarding" |
| `has_seen_how_to_play` | boolean | required | Default: false |
| `has_seen_consent_explanation` | boolean | required | Default: false |
| `version` | string | required | "1.0" |

#### Object Store: `settings`

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| `id` (key) | string | PRIMARY KEY | Always "app_settings" |
| `theme` | string | required | "light" \| "dark" \| "system" |
| `analytics_enabled` | boolean | required | Default: true |

---

## 5. CRUD Operations

### Stories CRUD

**Create Story**
```typescript
async function saveStory(story: StoryRecord): Promise<void> {
  // Validation: story.consent.verbal_confirmed must be true
  // Validation: audio_blob must be Blob type
  // Validation: audio_duration_seconds <= 300
  await localforage.setItem(`story_${story.id}`, story);
  // Trigger GA4 event: story_saved
}
```

**Read Story**
```typescript
async function getStory(storyId: string): Promise<StoryRecord | null> {
  const story = await localforage.getItem(`story_${storyId}`);
  return story as StoryRecord | null;
}
```

**Read All Stories (with pagination)**
```typescript
async function getAllStories(
  limit: number = 50,
  offset: number = 0
): Promise<StoryRecord[]> {
  // Returns stories sorted by created_at DESC
  // Implementation note: localForage doesn't support pagination natively
  // Solution: fetch all, then slice in JavaScript (acceptable for MVP <1000 stories)
  const keys = await localforage.keys();
  const storyKeys = keys.filter(k => k.startsWith('story_'));
  const stories = await Promise.all(
    storyKeys.map(k => localforage.getItem(k))
  );
  return (stories as StoryRecord[])
    .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
    .slice(offset, offset + limit);
}
```

**Update Story**
```typescript
async function updateStory(storyId: string, updates: Partial<StoryRecord>): Promise<void> {
  const story = await getStory(storyId);
  if (!story) throw new Error('Story not found');
  const updated = {
    ...story,
    ...updates,
    updated_at: new Date().toISOString(),
  };
  await localforage.setItem(`story_${storyId}`, updated);
}
```

**Delete Story (Soft Delete)**
```typescript
async function deleteStory(storyId: string, soft: boolean = true): Promise<void> {
  if (soft) {
    // Mark for deletion (user can recover in Phase 2)
    await updateStory(storyId, {
      marked_for_deletion: true,
      deleted_at: new Date().toISOString(),
    });
  } else {
    // Hard delete (permanent)
    await localforage.removeItem(`story_${storyId}`);
  }
  // Trigger GA4 event: story_deleted
}
```

### Prompts CRUD

**Load Prompts** (from `/docs/prompts.json`)
```typescript
async function loadPrompts(): Promise<Prompt[]> {
  try {
    const response = await fetch('/docs/prompts.json');
    const prompts = await response.json();
    // Cache in IndexedDB
    for (const prompt of prompts) {
      await localforage.setItem(`prompt_${prompt.id}`, prompt);
    }
    return prompts;
  } catch (error) {
    // Fallback: return cached prompts if offline
    const keys = await localforage.keys();
    const cachedPromptKeys = keys.filter(k => k.startsWith('prompt_'));
    return Promise.all(
      cachedPromptKeys.map(k => localforage.getItem(k))
    );
  }
}
```

**Get Prompt by ID**
```typescript
async function getPrompt(promptId: string): Promise<Prompt | null> {
  return await localforage.getItem(`prompt_${promptId}`);
}
```

---

## 6. Business Logic

### Wheel Spin & Prompt Selection

**Algorithm: `calculateLandingPrompt()`**

```typescript
interface SpinInput {
  topicPackId: string;
  rotationDegrees: number; // 0–360, where user ended spin
  prompts: Prompt[]; // 20 prompts in order around wheel
}

function calculateLandingPrompt(input: SpinInput): Prompt {
  // 1. Divide wheel into 20 segments (360 / 20 = 18 degrees each)
  const segmentSize = 360 / input.prompts.length;

  // 2. Find which segment the pointer (top center) landed in
  // Account for CSS perspective: wheel rotates but pointer is fixed at top
  const adjustedDegrees = (360 - input.rotationDegrees) % 360;
  const segmentIndex = Math.floor(adjustedDegrees / segmentSize);

  // 3. Return the prompt at that index
  return input.prompts[segmentIndex];
}
```

**Snap-to-Prompt Logic:**
After spin momentum ends (natural deceleration), snap wheel to nearest segment so selected prompt is centered at top. Animation: 300–500ms cubic-bezier ease-out.

### Pass Logic

- **First spin**: User may pass. Wheel resets, spins again.
- **Second spin**: No pass allowed—user is locked in.
- **Visual feedback**: After pass, show message: "Okay! Let's spin again. This next one is the one."

### Recording Session Flow

1. User lands on prompt → Contemplation screen appears
2. User taps "Record" → Check storage quota via `navigator.storage.estimate()`
3. If quota full → Show error: *"Device storage is full. Delete old stories to record new ones."* and disable record button
4. If quota available → Consent screen appears
5. User confirms consent (verbal + tap) → MediaRecorder starts
6. User records (max 300 seconds)
7. User taps "Stop" → Stop recording, save Blob to IndexedDB as StoryRecord
8. Confirmation screen → Gallery button or "Record Another"

### Photo Upload (MVP)

Optional feature. If user taps "Add Photo":
1. Open file picker (images only, max 2MB)
2. Convert to WebP (via Canvas or built-in support)
3. Attach to StoryRecord.photo blob + metadata
4. Display success: "Photo added"

---

## 7. Validation Rules

All validation happens at **component/hook level**, not in data layer. This table defines the rules; implementation is per-component.

| Field | Rule | Error Message | Trigger |
|-------|------|---------------|---------|
| `audio_blob` | Must be Blob type, MIME type `audio/webm` or `audio/mp4` | "Invalid audio format" | Before saving story |
| `audio_duration_seconds` | Must be > 0 and ≤ 300 | "Recording too long (max 5 min)" | During/after recording |
| `consent.verbal_confirmed` | Must be true | "Consent required to save story" | Before saving story |
| `storyteller_name` | If provided, must be 1–50 characters | "Name too long" | Consent screen form |
| `prompt_id` | Must match existing Prompt in prompts store | "Prompt not found" | Before creating story |
| `photo.blob` | If provided, must be Blob, max 2MB | "Photo too large (max 2MB)" | Photo upload |
| `photo.blob` (MIME) | If provided, must be `image/webp`, `image/jpeg`, or `image/png` | "Unsupported image format" | Photo upload |
| Storage quota | Device storage available > 5MB | "Device storage is full. Delete old stories to record new ones." | Before recording |
| Duplicate story ID | No two stories can have same `id` | "Story already exists" | Save operation (caught by localForage unique key constraint) |

---

## 8. Storage & Quota Management

### Quota Checking

Before user taps "Record," check device storage:

```typescript
async function checkStorageQuota(): Promise<boolean> {
  if (!navigator.storage) return true; // Assume available if API unavailable
  const estimate = await navigator.storage.estimate();
  const quotaBytes = estimate.quota;
  const usedBytes = estimate.usage;
  const availableBytes = quotaBytes - usedBytes;

  // Reserve 5MB buffer for system + other data
  const minRequiredBytes = 5 * 1024 * 1024;

  return availableBytes >= minRequiredBytes;
}

async function handleRecordingStart(): Promise<void> {
  const hasQuota = await checkStorageQuota();
  if (!hasQuota) {
    showError("Device storage is full. Delete old stories to record new ones.");
    disableRecordButton();
    return;
  }
  // Proceed with recording
}
```

### Typical Storage Footprint

- **One 5-minute story**: 2–4MB (WebM Opus codec, ~64kbps mono)
- **One photo**: 0.5–1.5MB (WebP, compressed)
- **100 stories**: ~300MB (without photos)
- **Default IndexedDB quota**: 50–100MB (browser-dependent)

### Storage Graceful Degradation

**When storage is full:**
1. Show user message (as above)
2. Disable "Record" button
3. Suggest: "Go to My Stories and delete old recordings to free up space"
4. Do NOT prevent app from running—existing stories are readable

**Storage recovery:**
- User deletes stories → space freed immediately
- Re-check quota before next recording attempt

---

## 9. Constants

All magic numbers and configuration defined in `/src/constants.ts`:

```typescript
// Recording configuration
export const RECORDING_CONFIG = {
  MAX_DURATION_SECONDS: 300, // 5 minutes
  MIME_TYPE: 'audio/webm;codecs=opus', // Safari fallback: 'audio/mp4'
  AUDIO_BITRATE: 64000, // 64 kbps (mono)
  SAMPLE_RATE: 48000, // Hz
  PAUSE_RESUME_ENABLED: true,
};

// Wheel configuration
export const WHEEL_CONFIG = {
  PROMPTS_PER_WHEEL: 20,
  SEGMENT_SIZE_DEGREES: 18, // 360 / 20
  SNAP_DURATION_MS: 400,
  SNAP_EASING: 'cubic-bezier(0.25, 0.46, 0.45, 0.94)', // ease-out
  MIN_SPIN_DURATION_MS: 2000,
  FRICTION_FACTOR: 0.97, // deceleration per frame
};

// UI configuration
export const UI_CONFIG = {
  CONTEMPLATION_HINT_CYCLE_MS: 4500, // fade in/out every 4.5s
  RECORDING_TIMER_UPDATE_MS: 100, // update timer every 100ms
  TOUCH_TARGET_MIN_PX: 44, // WCAG AA target size
};

// Storage configuration
export const STORAGE_CONFIG = {
  MIN_QUOTA_BYTES: 5 * 1024 * 1024, // 5 MB minimum required
  DB_NAME: 'StoryPortalDB',
  DB_VERSION: 1,
};

// UUID generation
export const generateStoryId = (): string => {
  // Use native crypto.randomUUID() — no dependencies
  return `story_${crypto.randomUUID()}`;
};

export const generatePromptId = (): string => {
  return crypto.randomUUID();
};

// Analytics events (GA4)
export const ANALYTICS_EVENTS = {
  WHEEL_SPIN: 'wheel_spin',
  PROMPT_PASS: 'prompt_pass',
  RECORDING_START: 'recording_start',
  RECORDING_COMPLETE: 'recording_complete',
  RECORDING_ABANDONED: 'recording_abandoned',
  STORY_SAVED: 'story_saved',
  STORY_DELETED: 'story_deleted',
  TOPIC_PACK_CHANGED: 'topic_pack_changed',
  PHOTO_UPLOADED: 'photo_uploaded',
};
```

---

## 10. Phase 2 Extensions

### Cloud Sync

When backend is available (Phase 2), extend StoryRecord with:

```typescript
{
  // ... existing fields ...

  // Cloud sync status
  sync_status: 'local' | 'syncing' | 'synced' | 'sync_error';
  server_id?: string; // UUID returned by backend
  last_sync_attempt?: string; // ISO 8601 timestamp
  sync_error?: string; // error message if sync_status = 'sync_error'
}
```

Background sync uploads newly-created stories to Supabase when online.

### Story Sharing

Add to StoryRecord:
```typescript
{
  sharing_status: 'private' | 'shared';
  shared_link?: string; // e.g., "https://app.thestoryportal.org/story/abc123"
  share_expiration?: string; // ISO 8601 (optional—shared link never expires by default)
}
```

Facilitators can generate time-limited links for group sessions.

### Email Consent Approval

Extend ConsentData with email field:
```typescript
{
  // ... existing fields ...
  storyteller_email?: string;
  email_confirmation_sent?: string; // ISO 8601 timestamp
  email_confirmed?: boolean; // default: false
}
```

If storyteller provides email, app sends confirmation link. Story can only be shared after email approval.

---

## Summary

This data model supports a **local-first, privacy-centric MVP** that stores all stories on the user's device. It's simple, offline-capable, and extensible for Phase 2 features. No backend complexity, no database migration headaches—just IndexedDB and browser APIs.

**Key Decisions:**
- Blob storage is native (no serialization)
- UUID generation via native `crypto.randomUUID()`
- Validation rules defined, not coded
- Storage quota checked before recording
- Soft deletes enable recovery (Phase 2)
- Phase 2 extensions are minimal sketches only

---

*This is a living document. Update as architectural decisions evolve.*
