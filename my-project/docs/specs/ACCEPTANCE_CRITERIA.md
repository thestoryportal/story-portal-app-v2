# Acceptance Criteria Specification

**Version**: 1.0
**Last Updated**: January 8, 2025
**Status**: MVP Definition of Done

---

## Table of Contents

1. [Overview](#1-overview)
2. [Feature Categories](#2-feature-categories)
3. [Core Functionality Criteria](#3-core-functionality-criteria)
4. [Content & Experience Criteria](#4-content--experience-criteria)
5. [Technical Requirements Criteria](#5-technical-requirements-criteria)
6. [Accessibility & Performance Criteria](#6-accessibility--performance-criteria)
7. [Analytics Criteria](#7-analytics-criteria)
8. [Deployment Criteria](#8-deployment-criteria)

---

## 1. Overview

### Purpose

This document defines "**Definition of Done**" for the MVP. Each feature, content screen, and technical requirement has testable acceptance criteria. A feature is complete when ALL its criteria pass.

### Testing Approach

- **Functional**: Does it work as specified?
- **Visual**: Does it match the design system?
- **Performance**: Does it meet speed targets?
- **Accessibility**: Can all users access it?
- **Offline**: Does it work without internet?

### Pass/Fail Criteria

Acceptance criteria use language:
- ✅ **MUST**: Feature is incomplete without this
- ⚠️ **SHOULD**: Feature is better with this, but not blocking
- 📋 **NICE-TO-HAVE**: Post-MVP polish (Phase 2)

---

## 2. Feature Categories

**MVP consists of:**

| Category | Count | Status |
|----------|-------|--------|
| Core Features | 8 | Specified below |
| Content Screens | 5 | Specified below |
| Technical Requirements | 6 | Specified below |
| Accessibility | 4 | Specified below |
| Analytics | 8 | Specified below |

---

## 3. Core Functionality Criteria

### 3.1 The Wheel

**User Story:**
*As a storyteller, I want to spin a wheel and land on a prompt, so that the randomness removes my choice and inspires spontaneity.*

#### 3.1.1 Wheel Rendering

| # | Criterion | Status | Notes |
|---|-----------|--------|-------|
| 1 | Wheel displays 20 prompts arranged in circle (CSS 3D perspective) | MUST | 360° / 20 = 18° per segment |
| 2 | Each prompt segment is visually distinct with different colors/opacity | MUST | Use color-bronze and color-flame from design tokens |
| 3 | Selected prompt is centered at top with visual highlight (flame animation) | MUST | Flame glow around selected segment during contemplation |
| 4 | Wheel rotates smoothly on spin gesture (touch, trackpad, button) | MUST | Target 60fps; use CSS transforms not layout triggers |
| 5 | Touch spin: detect swipe velocity and translate to wheel momentum | MUST | Swipe 200px in 500ms = moderate spin; 500px/300ms = fast spin |
| 6 | Button spin: click "Spin" button triggers 1500–2500ms rotation | MUST | Min 2000ms per WHEEL_CONFIG.MIN_SPIN_DURATION_MS |
| 7 | Trackpad: two-finger drag on macOS/Linux translates to spin | SHOULD | Fallback: trackpad treated as mouse (no spin) |
| 8 | Spin momentum decelerates naturally (friction_factor = 0.97) | MUST | Frame-by-frame deceleration, not abrupt stop |
| 9 | After spin ends, snap wheel to nearest prompt (300–500ms animation) | MUST | Use cubic-bezier ease-out easing |
| 10 | Wheel cannot be spun while already spinning | MUST | Disable spin controls during animation |

#### 3.1.2 Prompt Selection Logic

| # | Criterion | Status | Notes |
|---|-----------|--------|-------|
| 11 | Calculate landing prompt by checking which 18° segment pointer (top center) landed in | MUST | Algorithm: `calculateLandingPrompt(rotationDegrees)` |
| 12 | Display prompt text prominently after snap completes | MUST | White text on dark background (--text-on-dark) |
| 13 | Display facilitation hint if `declaration_risk` is "medium" or "high" | MUST | Hint cycles fade in/out every 4–5 seconds |
| 14 | Hint text is smaller than prompt text and positioned below | SHOULD | Use --font-size-body-sm (smaller than --font-size-body) |
| 15 | Prompt persists until user taps "Record", "Pass", or "New Topics" | MUST | No auto-advance |

#### 3.1.3 Pass Logic

| # | Criterion | Status | Notes |
|---|-----------|--------|-------|
| 16 | Show "Pass" button after first spin lands | MUST | Button text: "This isn't quite right. Let me try again." |
| 17 | Tapping "Pass" resets wheel and allows another spin | MUST | Pass count increments to 1 |
| 18 | Show "Pass" button disappears after second spin | MUST | Message appears: "Okay! This one is it. Let's record." |
| 19 | User cannot pass on second spin (locked in) | MUST | "Pass" button is disabled/hidden on second spin |
| 20 | Pass count resets when user spins again (same session) | MUST | Pass count state: 0 (first spin) → 1 (passed) → 0 (new spin) → 1 (second spin locked) |

#### 3.1.4 New Topics Button

| # | Criterion | Status | Notes |
|---|-----------|--------|-------|
| 21 | "New Topics" button loads a different prompt pack | MUST | Button appears on wheel screen |
| 22 | Tapping "New Topics" loads alternative prompt set (if available in Phase 2) | SHOULD | MVP: only 1 pack, so button loads same pack; Phase 2 enables multiple |
| 23 | Current wheel resets after loading new pack | MUST | No prompt is selected; user must spin again |
| 24 | GA4 event `topic_pack_changed` fires when new pack loads | MUST | See Analytics section |

### 3.2 Contemplation Screen

**User Story:**
*As a storyteller, I want to see the prompt prominently with time to think before recording, so that I'm ready to share authentically.*

#### 3.2.1 Visual Display

| # | Criterion | Status | Notes |
|---|-----------|--------|-------|
| 25 | Prompt text displays in large, readable font (≥ 20px mobile, ≥ 24px desktop) | MUST | Use --font-size-heading-md or larger |
| 26 | Facilitation hint cycles into view below prompt (fade 0→1 opacity, 2s duration) | MUST | Cycles every 4–5 seconds indefinitely until recording starts |
| 27 | Flame animation glows around selected wheel segment | MUST | Use --color-flame-core with radial gradient opacity effect |
| 28 | "Record" button is prominently displayed below hint | MUST | Button color: --color-flame-core (gold) on dark background |
| 29 | Background is dark (--bg-primary) with optional subtle overlay | SHOULD | Minimizes distractions; no busy patterns |

#### 3.2.2 User Actions

| # | Criterion | Status | Notes |
|---|-----------|--------|-------|
| 30 | User can tap "Record" to proceed to recording screen | MUST | Moves to Recording state |
| 30b | User can tap "Go Back" to return to wheel for another pass (if pass available) | MUST | Only visible on first spin; hidden on second spin (locked in) |
| 31 | User can navigate to content screens (How to Play, etc.) without losing prompt state | SHOULD | If user navigates away, return to wheel (don't persist contemplation state) |

### 3.3 Recording

**User Story:**
*As a storyteller, I want to record my voice with simple controls and visual feedback, so that sharing my story feels natural and unedited.*

#### 3.3.1 Consent Flow (Pre-Recording)

| # | Criterion | Status | Notes |
|---|-----------|--------|-------|
| 32 | Before recording starts, show consent screen with verbal confirmation prompt | MUST | Text: "We'd like to record your story. Your voice will be stored on your device. Is that okay?" |
| 33 | Consent screen includes email field (optional) | SHOULD | Label: "Email (optional, for approval before sharing)" |
| 33b | Email field is pre-filled if user previously entered it | SHOULD | Store in browser localStorage or IndexedDB |
| 34 | User taps "I Consent" button to proceed to recording | MUST | Checkboxes not needed (simple tap consent) |
| 35 | User can tap "Skip Recording" or back arrow to return to contemplation | MUST | No penalty; returns to prompt selection |
| 36 | Consent timestamp is recorded (ISO 8601) | MUST | Stored in `StoryRecord.consent.consent_date` |
| 37 | If no email provided, `StoryRecord.consent.email_confirmed` is `false` | MUST | Story can be saved but not shared without email approval (Phase 2) |

#### 3.3.2 Recording Interface

| # | Criterion | Status | Notes |
|---|-----------|--------|-------|
| 38 | "Record" button initiates MediaRecorder and starts audio capture from microphone | MUST | Requests user permission (browser native flow) |
| 39 | While recording, button changes to "Stop" with red accent color | MUST | Color: --color-error (#f44336) |
| 40 | Timer displays elapsed time (mm:ss format) updating every 100ms | MUST | Position: center of screen, large font (≥ 24px) |
| 41 | Visual waveform animation shows live audio input (simple bars, not detailed spectrum) | SHOULD | Use Canvas or SVG bars that animate with RMS level |
| 42 | "Pause" button appears during recording, allows pause/resume | SHOULD | Pause = pause icon, Resume = play icon |
| 43 | If microphone permission is denied, show error: "Microphone access required. Check device settings." | MUST | Disable record button; offer link to help page |
| 44 | If MediaRecorder is unsupported, show error: "Your device doesn't support audio recording. Try a different browser." | MUST | Handle gracefully; offer fallback or skip |

#### 3.3.3 Recording Limits & Constraints

| # | Criterion | Status | Notes |
|---|-----------|--------|-------|
| 45 | Maximum recording duration is 5 minutes (300 seconds) | MUST | At 300s, auto-stop with message: "Time's up! Great job." |
| 46 | When timer reaches 4:45 (285s), show warning: "30 seconds remaining" | SHOULD | Visual/audio cue (subtle flash or tone) |
| 47 | Recording stops cleanly when time limit reached; saves audio blob | MUST | No data loss; blob is immediately persisted |
| 48 | Audio format is WebM (audio/webm;codecs=opus) or MP4 fallback for Safari | MUST | Bitrate: 64–128 kbps mono; sample rate 48 kHz preferred |
| 49 | Audio blob size is estimated: 5-min recording ≈ 2–4MB (mono Opus at 64kbps) | MUST | Inform user: "Recording saved (approx 3 MB)" |

#### 3.3.4 Storage Quota Check

| # | Criterion | Status | Notes |
|---|-----------|--------|-------|
| 50 | Before recording starts, check device storage via `navigator.storage.estimate()` | MUST | See DATA_MODEL.md § 8 for implementation |
| 51 | If available storage < 5MB, show error: "Device storage is full. Delete old stories to record new ones." | MUST | Disable record button; offer link to "My Stories" to delete |
| 52 | If storage is adequate (≥ 5MB available), proceed with recording | MUST | No user interaction needed |
| 53 | If `navigator.storage` API unavailable, assume quota is okay and proceed | SHOULD | Graceful fallback; user may hit quota later |

### 3.4 Story Save & Review

**User Story:**
*As a storyteller, I want to review my recording and save it to my device, so that I can share it later or record another story.*

#### 3.4.1 Post-Recording Screen

| # | Criterion | Status | Notes |
|---|-----------|--------|-------|
| 54 | After recording stops, show playback screen with prompt, audio waveform, duration | MUST | Display: prompt text, "3 min 25 sec recorded" |
| 55 | Play/pause button allows listening to recording before saving | MUST | No editing capability; single-take only (intentional) |
| 56 | "Save Story" button persists audio blob + metadata to IndexedDB | MUST | Creates StoryRecord with consent_confirmed=true |
| 57 | "Delete & Re-record" button discards audio and returns to consent/recording flow | MUST | No blob persisted; session can start over |
| 58 | Playback respects device `prefers-reduced-motion` setting (no animation) | MUST | Media controls only; no unnecessary motion |

#### 3.4.2 Photo Attachment (Optional)

| # | Criterion | Status | Notes |
|---|-----------|--------|-------|
| 59 | "Add Photo" button (optional) on review screen opens file picker | SHOULD | Accepts JPG, PNG, WebP only |
| 60 | Selected photo is compressed to WebP format (max 2MB) | SHOULD | Use Canvas `toBlob()` or native WebP support |
| 61 | Photo preview displays thumbnail on review screen | SHOULD | Thumbnail max 100px x 100px |
| 62 | If photo upload fails, show warning but allow story save without photo | SHOULD | "Couldn't add photo, but your story is saved." |
| 63 | GA4 event `photo_uploaded` fires after successful photo attachment | SHOULD | See Analytics section |

#### 3.4.3 Story Metadata

| # | Criterion | Status | Notes |
|---|-----------|--------|-------|
| 64 | Prompt ID and text are stored with story (denormalized) | MUST | Allows story to be displayed even if prompt changes |
| 65 | Audio duration (seconds) is calculated and stored | MUST | `StoryRecord.audio_duration_seconds = duration` |
| 66 | Story creation timestamp is recorded (ISO 8601) | MUST | `StoryRecord.created_at = now()` |
| 67 | Unique story ID is generated (UUID) | MUST | Use `crypto.randomUUID()` |
| 68 | Storyteller name and pronouns are optional fields | SHOULD | If provided during consent, store with story |
| 69 | Consent metadata is stored (verbal_confirmed=true, date, version) | MUST | Required for sharing in Phase 2 |

#### 3.4.4 Save Confirmation

| # | Criterion | Status | Notes |
|---|-----------|--------|-------|
| 70 | After "Save Story" tapped, show confirmation: "Story saved! Want to record another?" | MUST | Display for 2–3 seconds, then auto-navigate |
| 71 | User can tap "Record Another" to return to wheel (spin again) | MUST | Resets wheel to initial state |
| 72 | User can tap "View My Stories" to navigate to gallery | MUST | Shows all saved stories |
| 73 | If navigation away happens, data is not lost (persisted to IndexedDB) | MUST | User can return later and story is still there |
| 74 | GA4 event `story_saved` fires after successful save | MUST | See Analytics section |

### 3.5 My Stories Gallery

**User Story:**
*As a user, I want to view all my saved stories, listen to them, and delete ones I don't want, so that I can manage my collection.*

#### 3.5.1 Gallery Display

| # | Criterion | Status | Notes |
|---|-----------|--------|-------|
| 75 | Gallery screen lists all saved stories sorted by creation date (newest first) | MUST | Each story shown as card/tile |
| 76 | Each story card displays: prompt text, recording duration, creation date | MUST | Format date: "Jan 8, 2025 · 3 min 25 sec" |
| 77 | If photo attached, show thumbnail on story card | SHOULD | Thumbnail 80px x 80px, rounded corners |
| 78 | Gallery shows count of total stories: "12 Stories" at top | SHOULD | Update count dynamically when stories added/deleted |
| 79 | If no stories exist, show empty state: "No stories yet. Spin the wheel to record your first!" | MUST | Include illustration or icon (steampunk theme) |
| 80 | Gallery is scrollable; performance acceptable with 100+ stories | SHOULD | Use virtualization or pagination if > 50 stories (defer if not needed) |

#### 3.5.2 Story Playback

| # | Criterion | Status | Notes |
|---|-----------|--------|-------|
| 81 | Tapping story card opens detail view with larger prompt display and full audio player | MUST | Player shows play/pause, timeline, current time, duration |
| 82 | Audio playback controls: play/pause, volume control, playback speed (1x/1.5x) | SHOULD | Speed control for accessibility (catch up on details) |
| 83 | Timeline scrubbing allowed (user can drag to seek position in audio) | SHOULD | Helpful for review; not critical |
| 84 | Playback respects device `prefers-reduced-motion` setting | MUST | Media controls only; no decorative animation |
| 85 | Photo (if present) displays full-size with story | SHOULD | Below prompt, above audio player |

#### 3.5.3 Story Deletion

| # | Criterion | Status | Notes |
|---|-----------|--------|-------|
| 86 | Each story card includes delete icon (trash can) in corner | MUST | Icon position: top-right of card |
| 87 | Tapping delete shows confirmation: "Delete this story? You can't undo this." | MUST | Confirmation modal with "Delete" and "Cancel" buttons |
| 88 | Tapping "Delete" removes story from IndexedDB (hard delete in MVP) | MUST | Story is permanently gone; no recovery in MVP |
| 89 | After deletion, gallery updates immediately (story removed from list) | MUST | Count also decrements |
| 90 | GA4 event `story_deleted` fires after successful deletion | MUST | See Analytics section |

#### 3.5.4 Gallery Navigation

| # | Criterion | Status | Notes |
|---|-----------|--------|-------|
| 91 | Gallery is accessible from main navigation (bottom nav or hamburger menu) | MUST | Label: "My Stories" |
| 92 | From gallery, user can navigate back to wheel to record new story | MUST | Button: "Spin Again" or main nav link |
| 93 | Gallery persists across page refreshes (data in IndexedDB, not session) | MUST | User closes tab, reopens app—stories still there |

### 3.6 Offline Functionality

**User Story:**
*As a user, I want the app to work without internet, so that I can record stories anywhere.*

#### 3.6.1 Offline Core Features

| # | Criterion | Status | Notes |
|---|-----------|--------|-------|
| 94 | App shell (UI, wheel, prompts) cached via service worker on first load | MUST | Progressive Web App using vite-plugin-pwa |
| 95 | Prompts cached in IndexedDB after first fetch; available offline | MUST | Wheel works fully offline |
| 96 | Audio recording works offline (no internet required for recording) | MUST | MediaRecorder is local API |
| 97 | Stories saved to IndexedDB immediately (offline persistence) | MUST | No waiting for server sync in MVP |
| 98 | Gallery displays cached stories even if offline | MUST | All read operations from local IndexedDB |
| 99 | If app goes offline during use, show no error (graceful degradation) | MUST | App continues to function normally |
| 100 | If prompts.json fails to load on first visit, show fallback: "Unable to load prompts. Try again when online." | SHOULD | Offer retry button; cache after first success |

#### 3.6.2 Offline Indicators (Phase 2)

| # | Criterion | Status | Notes |
|---|-----------|--------|-------|
| 101 | Status bar shows "Offline" indicator when no internet | NICE-TO-HAVE | MVP: no indicator (all features work offline anyway) |
| 102 | Notification explains stories will sync when online (Phase 2) | NICE-TO-HAVE | Deferred: MVP has no cloud sync |

---

## 4. Content & Experience Criteria

### 4.1 How to Play Screen

**Acceptance Criteria:**

| # | Criterion | Status | Notes |
|---|-----------|--------|-------|
| 103 | Screen explains wheel spinning, prompt landing, recording flow | MUST | Text is clear and friendly, not technical jargon |
| 104 | Includes 3–4 illustrated steps or icons showing the flow | SHOULD | Steampunk aesthetic; use brass, wood, flame colors |
| 105 | Addresses common questions: "Can I pass?", "What if I mess up?", "Is my story safe?" | SHOULD | FAQ-style Q&A or inline callouts |
| 106 | Includes facilitation guidance: "Encourage narrative, not declaration" | SHOULD | Tips for facilitators running group sessions |
| 107 | Accessible from main navigation and from initial welcome/onboarding | MUST | Label: "How to Play" |
| 108 | Desktop layout: centered text column, max 600px width for readability | SHOULD | Mobile: full-width with safe padding |

### 4.2 Our Story Screen

**Acceptance Criteria:**

| # | Criterion | Status | Notes |
|---|-----------|--------|-------|
| 109 | Displays mission statement: "Making empathy contagious" | MUST | Prominently at top |
| 110 | Explains vision and the portal metaphor (from APP_SPECIFICATION.md) | SHOULD | 2–3 paragraphs, clear and inspiring |
| 111 | Describes core values: Spontaneity, Witnessing, Connection, Analog soul | SHOULD | Bullet list or short narrative |
| 112 | Includes mention of steampunk aesthetic philosophy (intentional friction) | SHOULD | 1 paragraph explaining why gears/patina |
| 113 | Accessible from main navigation | MUST | Label: "Our Story" |

### 4.3 Our Work Screen

**Acceptance Criteria:**

| # | Criterion | Status | Notes |
|---|-----------|--------|-------|
| 114 | Displays 5–10 photos of physical Story Portal installations (from /public/assets/images/) | SHOULD | WebP format, optimized for mobile |
| 115 | Each photo includes caption: venue name, date, number of participants | SHOULD | E.g., "Burning Man 2024 · 200+ participants" |
| 116 | Photos are presented in grid or carousel layout | SHOULD | Responsive: 1 column mobile, 2–3 columns desktop |
| 117 | Accessible from main navigation | MUST | Label: "Our Work" |

### 4.4 Privacy Policy Screen

**Acceptance Criteria:**

| # | Criterion | Status | Notes |
|---|-----------|--------|-------|
| 118 | Clearly states: "Your stories stay on your device. We don't store them on our servers." | MUST | First sentence, bold or prominent |
| 119 | Explains consent flow: verbal consent, optional email for approval | SHOULD | Simple language, not legal jargon |
| 120 | States: "You can delete any story anytime. Deletion is permanent." | MUST | Clear consequence: no recovery in MVP |
| 121 | Lists what data is collected for analytics (GA4 events) | SHOULD | "wheel_spin", "story_saved", "story_deleted", etc. |
| 122 | Explains offline functionality: "App works without internet. Data stored locally." | SHOULD | Reassure users about privacy |
| 123 | Includes contact info for privacy questions | SHOULD | Email address (privacy@thestoryportal.org or similar) |
| 124 | Accessible from main navigation and footer | MUST | Label: "Privacy Policy" |

### 4.5 Booking Screen

**Acceptance Criteria:**

| # | Criterion | Status | Notes |
|---|-----------|--------|-------|
| 125 | Displays information for booking physical Story Portal installations | SHOULD | "Interested in hosting The Story Portal at your event?" |
| 126 | Contact form with fields: name, email, event type, date, location, guests | SHOULD | Optional message field |
| 127 | Form validation: email format, required fields marked | SHOULD | Show error: "Please enter a valid email" |
| 128 | On submit, show confirmation: "Thanks! We'll be in touch soon." | SHOULD | Do not require backend in MVP; form can email via SendGrid/Mailgun (Phase 2 integration) |
| 129 | Accessible from main navigation | SHOULD | Label: "Booking" |
| 130 | MVP alternative: Booking link redirects to external form or email | ACCEPTABLE | If building internal form is out of scope, link to Google Form or custom domain |

---

## 5. Technical Requirements Criteria

### 5.1 Build & Deployment

| # | Criterion | Status | Notes |
|---|-----------|--------|-------|
| 131 | App builds with `pnpm build` without errors | MUST | Output: /dist directory ready for deployment |
| 132 | Build size < 500 KB (gzipped) | SHOULD | Includes bundle size monitoring (vite-plugin-visualizer) |
| 133 | Source maps disabled in production build | SHOULD | Security: hide source code from browser dev tools |
| 134 | Environment variables properly managed (no secrets in code) | MUST | Prompts endpoint, GA4 ID, etc. in .env |
| 135 | App deployed to app.thestoryportal.org (or similar staging URL) | MUST | DNS configured; HTTPS enabled |
| 136 | Deploy process documented (CI/CD or manual steps) | SHOULD | README includes: `pnpm build && pnpm preview` or deployment script |

### 5.2 Browser Compatibility

| # | Criterion | Status | Notes |
|---|-----------|--------|-------|
| 137 | App works on iOS 14+ (Safari, Chrome) | MUST | Test on real devices if possible |
| 138 | App works on Android 10+ (Chrome, Firefox) | MUST | Test on real devices or emulator |
| 139 | App works on desktop browsers (Chrome, Safari, Firefox, Edge, latest 2 versions) | MUST | Desktop testing: Windows, macOS, Linux |
| 140 | Touch controls work on all touch devices (no mouse-only interactions) | MUST | Tap, swipe, long-press all functional |
| 141 | Keyboard navigation works (Tab through controls, Enter to activate, Escape to close modals) | MUST | Full keyboard accessibility for desktop users |
| 142 | CSS transforms (3D wheel) work without JavaScript fallback (no degradation needed) | SHOULD | If CSS 3D unavailable, show flat 2D fallback or skip wheel animation |

### 5.3 Local Storage & IndexedDB

| # | Criterion | Status | Notes |
|---|-----------|--------|-------|
| 143 | All stories persist in IndexedDB (via localForage) | MUST | Survive page reload, tab close, browser restart |
| 144 | IndexedDB quota management implemented (check before recording) | MUST | Show error if < 5MB available |
| 145 | Stories retrievable even after clearing cache (if user cleared cookies but not data) | SHOULD | IndexedDB separate from session storage |
| 146 | Blob (audio) storage works natively in IndexedDB (no serialization hacks) | MUST | Store Blob directly, retrieve as Blob |
| 147 | Data corruption recovery: if story record malformed, show warning and skip (don't crash) | SHOULD | Try-catch in story fetch; log to console |

### 5.4 Media Recording

| # | Criterion | Status | Notes |
|---|-----------|--------|-------|
| 148 | MediaRecorder API used for audio capture | MUST | Supported on all modern browsers (iOS 14.5+) |
| 149 | Audio format: WebM (Opus) preferred, MP4 fallback for Safari | MUST | Check browser support, fall back gracefully |
| 150 | Bitrate: 64 kbps mono (acceptable quality for speech, minimal file size) | MUST | Sample rate 48 kHz if available, 44.1 kHz fallback |
| 151 | 5-minute limit enforced (auto-stop at 300 seconds) | MUST | Timer accurate to within ±100ms |
| 152 | Pause/resume working (if implemented) | SHOULD | Media state persisted in memory during session |
| 153 | Microphone permission request shown; graceful error if denied | MUST | Error message clear and actionable |

### 5.5 Service Worker & PWA

| # | Criterion | Status | Notes |
|---|-----------|--------|-------|
| 154 | Service worker registered and caches app shell (index.html, CSS, JS) | MUST | Using vite-plugin-pwa |
| 155 | App installable as PWA on mobile (add to home screen prompt appears) | MUST | manifest.json configured with icons, name, theme color |
| 156 | Installed app launches full-screen (no browser chrome) | SHOULD | display: "standalone" in manifest.json |
| 157 | App icon (192x192, 512x512 PNG or WebP) provided | MUST | Steampunk themed icon (gears, portal, flame) |
| 158 | Offline page available (if offline and not in cache, show helpful message) | SHOULD | "You're offline. Try connecting to the internet or use cached data." |
| 159 | Update detection: if new version deployed, notify user and offer refresh | NICE-TO-HAVE | Deferred: MVP can auto-refresh silently |

### 5.6 Performance

| # | Criterion | Status | Notes |
|---|-----------|--------|-------|
| 160 | Initial app load < 3 seconds (on 4G network, mid-range phone) | MUST | Measure with Lighthouse or WebPageTest |
| 161 | Wheel spin smooth (60fps); no dropped frames | MUST | Test on actual devices, not just desktop |
| 162 | Recording starts < 500ms after "Record" tap | MUST | User perceives immediate response |
| 163 | Story save to IndexedDB < 1 second (including Blob write) | MUST | User sees confirmation quickly |
| 164 | Gallery loads 50 stories in < 1 second | SHOULD | Optimize IndexedDB queries if needed |
| 165 | Lighthouse PWA score ≥ 90 | MUST | Run `pnpm build && lighthouse https://app.thestoryportal.org` |

---

## 6. Accessibility & Performance Criteria

### 6.1 WCAG A Compliance

| # | Criterion | Status | Notes |
|---|-----------|--------|-------|
| 166 | Semantic HTML used (buttons are `<button>`, links are `<a>`, form inputs are `<input>`) | MUST | No `<div onclick>` patterns |
| 167 | Color contrast ≥ 4.5:1 for text on background (WCAG AA standard) | MUST | Use WebAIM contrast checker for all text |
| 168 | Focus indicators visible (outline or highlight) on all interactive elements | MUST | Outline width ≥ 2px, contrast ≥ 3:1 |
| 169 | Touch targets ≥ 44x44 px (WCAG AA) | MUST | Buttons, icons, interactive areas |
| 170 | Alt text provided for all images (informative, not decorative) | MUST | E.g., alt="Steampunk portal with gears" for hero image |
| 171 | Form labels associated with inputs (`<label for="id">`) | MUST | Screen readers announce label + input purpose |

### 6.2 Motion & Animation

| # | Criterion | Status | Notes |
|---|-----------|--------|-------|
| 172 | `@media (prefers-reduced-motion: reduce)` respected globally | MUST | All animations disabled for users with motion sensitivity |
| 173 | Flame glow animation around selected prompt has `animation-duration: 0.01ms` under prefers-reduced-motion | MUST | Instant removal, no animation |
| 174 | Wheel spin animation respects prefers-reduced-motion (snap instantly, no momentum decel) | MUST | Skip momentum, go straight to snap |
| 175 | Facility hint fade-in/fade-out disabled under prefers-reduced-motion | MUST | Hint text always visible, no cycling |
| 176 | Audio playback controls (play/pause) work without animation | MUST | Media controls are inherently accessible |

### 6.3 Responsive Design

| # | Criterion | Status | Notes |
|---|-----------|--------|-------|
| 177 | App responsive on: 320px (small phone), 768px (tablet), 1024px (desktop) | MUST | Test breakpoints: 480px, 768px, 1024px |
| 178 | Wheel renders correctly at all breakpoints (scales to fit viewport) | MUST | CSS `max-width` or `clamp()` for sizing |
| 179 | Typography scales responsively (heading, body, button text readable at all sizes) | MUST | Use `clamp()` or media query font sizes |
| 180 | Safe area insets respected on notched devices (iPhone X+, Android notches) | SHOULD | CSS `env(safe-area-inset-*)` applied to modals, fullscreen content |
| 181 | Landscape orientation supported (wheel spins correctly when rotated) | SHOULD | Test on tablet/phone in landscape mode |

### 6.4 Dark Mode & Color Scheme

| # | Criterion | Status | Notes |
|---|-----------|--------|-------|
| 182 | App uses CSS custom properties from `/src/tokens/colors.css` (no hardcoded hex values) | MUST | All colors reference --color-* or --bg-* variables |
| 183 | Color scheme: light dark (both modes declared in CSS) | SHOULD | `color-scheme: light dark` in :root |
| 184 | Sufficient contrast in all color combinations (test with contrast tools) | MUST | No low-contrast text pairs |
| 185 | Color not the only indicator (e.g., error state uses icon + color, not color alone) | MUST | WCAG A requirement |

---

## 7. Analytics Criteria

### 7.1 GA4 Event Tracking

All events use Google Analytics 4 property. Event names match ANALYTICS_EVENTS constant.

| # | Event | Criterion | Trigger | Notes |
|---|-------|-----------|---------|-------|
| 186 | `wheel_spin` | Event fires when spin completes and prompt lands | After snap animation finishes | Include parameter: `prompt_id` |
| 187 | `prompt_pass` | Event fires when user taps "Pass" | After pass button tapped and wheel resets | Include parameter: `pass_attempt` (1 or 2) |
| 188 | `recording_start` | Event fires when MediaRecorder starts | After consent confirmed, "Record" tapped | Include parameter: `prompt_id` |
| 189 | `recording_complete` | Event fires when user taps "Stop" or 5-min limit reached | After recording stops | Include parameters: `duration_seconds`, `prompt_id` |
| 190 | `recording_abandoned` | Event fires when user abandons recording session | If user navigates away during recording without saving | Include parameter: `duration_recorded_seconds` |
| 191 | `story_saved` | Event fires after story persisted to IndexedDB | After user confirms "Save Story" | Include parameters: `duration_seconds`, `has_photo` (boolean) |
| 192 | `story_deleted` | Event fires after story deleted from IndexedDB | After user confirms deletion | Include parameter: `story_duration_seconds` |
| 193 | `topic_pack_changed` | Event fires when new prompt pack loads | After "New Topics" button tapped | Include parameter: `new_pack_id` (Phase 2) |
| 194 | `photo_uploaded` | Event fires after photo successfully attached (optional) | After photo selected and saved | Include parameter: `photo_size_kb` |
| 195 | All events include `timestamp` (ISO 8601) | MUST | Auto-included by GA4 SDK |

### 7.2 Custom Dimensions (Optional, Phase 2)

| # | Dimension | Criterion | Purpose | Notes |
|---|-----------|-----------|---------|-------|
| 196 | `device_storage_quota` | Tracked on app init | Understand device storage constraints | E.g., "50GB", "128GB", "limited" |
| 197 | `recording_device_type` | Tracked on first successful recording | Optimize audio quality for device | E.g., "smartphone", "tablet", "desktop" |
| 198 | `number_of_stories` | Tracked on gallery load | Measure engagement (how many stories per user) | E.g., "0-5", "5-10", "10+" |

### 7.3 Analytics Implementation

| # | Criterion | Status | Notes |
|---|-----------|--------|-------|
| 199 | GA4 property ID configured in environment variable (VITE_GA4_PROPERTY_ID) | MUST | E.g., "G-XXXXXXXXXX" |
| 200 | Event tracking code implemented before any user interaction | MUST | gtag library loaded in index.html or via npm package |
| 201 | Events fire reliably (test with GA4 DebugView in browser console) | SHOULD | Confirm events appear in GA4 dashboard within 24 hours |
| 202 | Privacy respected: no PII in event payloads (no names, emails, audio content) | MUST | Only IDs, durations, counts—no sensitive data |
| 203 | Analytics can be disabled via settings toggle (Phase 2) or privacy laws | NICE-TO-HAVE | MVP: always enabled, respects `analytics_enabled` flag |

---

## 8. Deployment Criteria

### 8.1 Pre-Deployment Checklist

| # | Criterion | Status | Responsible |
|---|-----------|--------|-------------|
| 204 | All acceptance criteria pass (green checkmark) | MUST | QA/Developer |
| 205 | No console errors or warnings in production build | MUST | Developer |
| 206 | No hardcoded dev URLs (all use environment variables) | MUST | Developer |
| 207 | Secrets (.env, API keys) removed from code and git | MUST | Developer |
| 208 | README.md updated with build/deploy instructions | SHOULD | Developer |
| 209 | git history is clean (meaningful commits, no "WIP" messages) | SHOULD | Developer |
| 210 | Lighthouse score ≥ 90 on all metrics (Performance, Accessibility, Best Practices, SEO, PWA) | MUST | QA |

### 8.2 Deployment Steps

| # | Step | Command | Notes |
|---|------|---------|-------|
| 211 | Build | `pnpm build` | Output: /dist |
| 212 | Test build locally | `pnpm preview` | Simulates production server |
| 213 | Deploy to host | `git push origin main` (if using GitHub Pages) OR manual upload to server | Varies by host (Vercel, Netlify, custom server) |
| 214 | Verify deployment | Visit https://app.thestoryportal.org | Check wheel spins, recording works, gallery loads |
| 215 | Monitor uptime | Use StatusPage or similar | Alert on downtime |

### 8.3 Post-Deployment

| # | Criterion | Status | Notes |
|---|-----------|--------|-------|
| 216 | GA4 events flowing into property (check dashboard 24h after deploy) | SHOULD | Confirm `wheel_spin`, `story_saved` events appear |
| 217 | No 404 errors on assets (check browser Network tab) | MUST | All images, fonts, bundles load successfully |
| 218 | ServiceWorker installed (check browser DevTools → Application → Service Workers) | MUST | Status: "activated and running" |
| 219 | App installable on mobile (prompt appears or via menu) | MUST | Test on iOS and Android |
| 220 | User feedback mechanism set up (e.g., GitHub Issues, form, email) | SHOULD | Users can report bugs or request features |

---

## Summary Table

| Category | Total Criteria | Must-Have | Should-Have | Nice-to-Have |
|----------|----------------|-----------|-------------|--------------|
| Wheel | 24 | 20 | 4 | 0 |
| Recording | 39 | 32 | 5 | 2 |
| Stories & Gallery | 29 | 22 | 6 | 1 |
| Offline | 8 | 7 | 1 | 0 |
| Content Screens | 28 | 13 | 12 | 3 |
| Technical | 40 | 28 | 10 | 2 |
| Accessibility | 20 | 18 | 2 | 0 |
| Analytics | 20 | 14 | 5 | 1 |
| Deployment | 17 | 12 | 4 | 1 |
| **TOTAL** | **225** | **166** | **49** | **10** |

---

## Approval & Sign-Off

**MVP is complete when:**
- ✅ All 166 MUST criteria pass
- ✅ All 49 SHOULD criteria pass (if not, justified deferral to Phase 2)
- ✅ Lighthouse score ≥ 90
- ✅ No critical console errors
- ✅ Works on iOS 14+, Android 10+, desktop browsers
- ✅ Deployed to app.thestoryportal.org

---

*This is a living document. Update criteria as implementation progresses and discoveries emerge.*
