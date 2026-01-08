# The Story Portal — App Specification

**Version**: 1.0  
**Last Updated**: December 21, 2024  
**Status**: Living Document

---

## Table of Contents

1. [Vision & Mission](#1-vision--mission)
2. [User Personas](#2-user-personas)
3. [Feature Requirements](#3-feature-requirements)
4. [Technical Requirements](#4-technical-requirements)
5. [Content Requirements](#5-content-requirements)
6. [UX Principles](#6-ux-principles)
7. [Success Metrics](#7-success-metrics)
8. [Constraints & Assumptions](#8-constraints--assumptions)

---

## 1. Vision & Mission

### Mission

**Making empathy contagious.**

### Vision

The Story Portal connects individuals to the vast world of shared human experience. Through the simple ritual of spinning a wheel and responding to an unexpected prompt, storytellers bypass their inner editor and express their truth—raw, unpolished, and profoundly connecting.

### The Portal Metaphor

The Story Portal opens doorways between people. When the wheel spins, it selects not just a topic but a threshold—an invitation to cross from isolation into connection. The storyteller steps through first, offering a piece of their lived experience. Listeners follow, recognizing themselves in another's joy, folly, grief, or wonder.

### Why It Works

Traditional storytelling platforms reward curation—the carefully chosen photo, the edited narrative. The Story Portal inverts this. The spinning wheel removes choice. The spontaneity removes rehearsal. What remains is authenticity, and authenticity is the doorway to empathy.

### Core Values

1. **Spontaneity unlocks truth** — The unexpected prompt bypasses the inner editor
2. **Every story deserves a witness** — Listening with full attention is an act of empathy
3. **Connection across difference** — Shared experience transcends background and belief
4. **Analog soul, digital reach** — The warmth of a campfire story, accessible anywhere

### On the Steampunk Aesthetic

The Story Portal's visual identity—gears, patina, hand-forged metal—isn't decoration. It's philosophy. In an age of frictionless, algorithmic content, The Story Portal is deliberately *mechanical*. The wheel must be spun. The prompt must be accepted. The story must be told aloud, not typed. This intentional friction creates ritual, and ritual creates meaning.

---

## 2. User Personas

### Primary Persona: The Connector

**"I want deeper conversations with the people in my life, but I don't know how to start them."**

- 25-70 years old, socially active but dissatisfied with surface-level interactions
- Brings The Story Portal to group gatherings as a facilitation tool
- Often records others' stories rather than telling their own first
- Frustrated by social media's performative hollowness

**Aha Moment**: When a listener approaches a storyteller afterward saying "I went through something similar"—and realizes they created that connection.

### Secondary Persona: The Reluctant Storyteller

**"I'm not a storyteller. I don't have any good stories."**

- Believes their experiences are "ordinary"
- Deflects: "I'll just watch" / "Skip me"
- With gentle facilitation, tells stories that silence the room
- Often emotional afterward—surprised by their own depth

**What they need**: Low-pressure invitation, normalization ("The wheel is just asking you a question"), permission to be imperfect.

**Aha Moment**: Seeing impact on listeners—tears, laughter, recognition—realizes "I AM a storyteller."

### Secondary Persona: The Facilitator

**"I need a tool to create genuine connection in my group."**

- Team leads, retreat organizers, therapists, coaches
- Uses app as structured activity within larger programs
- Needs tool for genuine connection, not shallow icebreakers

**Aha Moment**: Seeing team members who never connected suddenly in deep conversation after a session.

### Behavior to Redirect: The Declarer

When prompts read as questions, some respond with statements rather than narratives. "What I love about myself" → "My resilience" (declaration) vs. "Let me tell you about the night I almost gave up" (story).

**Design implication**: Facilitation hints guide toward narrative.

---

## 3. Feature Requirements

### Core Experience

#### The Wheel
- 3D spinning wheel displaying 20 prompts
- Touch, trackpad, and button-based spin controls
- Realistic physics: momentum, friction, natural deceleration
- Snap-to-prompt landing with clear visual highlight
- "New Topics" button to load different prompt sets
- Works offline (prompts stored locally)

#### Pass & Topic Rules
- User may pass on first spin; second spin is final
- New Topics requires friction mechanism (honor system or time-based)

#### Audio Recording
- Record button appears after wheel lands
- Visual feedback during recording (waveform, timer)
- Maximum 5 minutes, pause/resume, re-record option
- Works offline (stores locally)to My Stories

#### Story Storage (Local)
- IndexedDB via localForage
- Each story: audio blob, prompt, timestamp, duration, storyteller info, consent status, optional photo

#### Consent Flow
- Verbal consent prompt in audio
- Tap-to-confirm before recording
- Email field for approval flow
- Easy deletion at any time

### Content Screens

| Screen | Purpose |
|--------|---------|
| How to Play | Instructions, facilitation guidance |
| Our Story | Origin, mission, philosophy |
| Our Work | Photos of physical installations |
| Privacy Policy | Data handling, user rights |
| Booking | Physical experience inquiries |

### Phase 2
- User accounts + cloud sync
- Story sharing via link/QR
- Video recording option
- Prompt categories/filtering

### Future Vision
- Community spaces
- Public discovery
- Facilitator/Pro features
- Accessibility (TTS, transcription)

---

## 4. Technical Requirements

### Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                    Client (PWA)                         │
│  React 19 + TypeScript + Vite                           │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐  │
│  │  3D Wheel   │  │   Audio     │  │  Local Storage  │  │
│  │ (CSS 3D +   │  │  Recorder   │  │  (IndexedDB)    │  │
│  │  Canvas)    │  │             │  │                 │  │
│  └─────────────┘  └─────────────┘  └─────────────────┘  │
└─────────────────────────────────────────────────────────┘
                          │
                          │ (Phase 2: when connected)
                          ▼
┌─────────────────────────────────────────────────────────┐
│                 Backend (Supabase)                       │
│  Auth │ PostgreSQL │ File Storage │ Edge Functions      │
└─────────────────────────────────────────────────────────┘
```

### Frontend Stack (Current Implementation)

| Category | Technology | Notes |
|----------|------------|-------|
| Framework | React 19.2.0 | Latest stable |
| Build | Vite 7.2.4 | Fast HMR |
| Language | TypeScript 5.9.3 | Strict mode |
| 3D Wheel | CSS 3D Transforms | Sufficient for current needs |
| Portal Effects | ReactJS/React Three/React Spring/WebGL | Electricity animation |
| Package Manager | pnpm | Required |

### To Add

| Package | Purpose | Install |
|---------|---------|---------|
| localforage | IndexedDB wrapper | `pnpm add localforage` |
| vite-plugin-pwa | PWA/offline | `pnpm add -D vite-plugin-pwa` |

### Audio Recording Architecture

```typescript
// Core recording flow
MediaRecorder API
  → Blob (audio/webm or audio/mp4)
  → localForage.setItem(`story_${id}`, blob)
  → StoriesView reads from localForage
```

**Constraints:**
- Format: WebM (Opus) preferred, MP4 fallback for Safari
- Quality: 64-128kbps mono
- Duration: 5-minute limit (~2-4MB per story)
- No editing: single-take only

### Offline Architecture

1. App shell cached via service worker
2. Prompts cached in IndexedDB on first load
3. Stories saved locally immediately
4. Phase 2: Background sync uploads when online

### Performance Targets

| Metric | Target |
|--------|--------|
| Wheel frame rate | 60fps |
| Audio recording start | < 500ms from tap |
| App load time | < 3 seconds |
| Lighthouse PWA score | > 90 |

---

## 5. Content Requirements

### Prompt Database

**Location**: `docs/prompts.json`

- To be determined amount of prompts, maybe categorized in phase 2
- `declaration_risk` field flags prompts needing facilitation hints
- `facilitation_hint` provides narrative coaching

**Possible future categories**: Love & Relationships, Family, Transformation, Fear & Courage, Adventures, Humor, Life & Death, Identity, Work & Achievement, Dreams & Spirituality, Intimacy, Wisdom, Whimsy, Festival

### Declaration Risk Handling

Some current prompts flagged as high declaration risk. For these, show facilitation hint:
- "Tell us how you learned this wisdom"
- "When did you discover this about yourself?"
- "Tell us about a time this showed"

### Prompt Design Principles

1. Invite narrative, not declaration
2. Specificity unlocks memory
3. Balance depth and accessibility
4. Prompts are inspirational, not literal

---

## 6. UX Principles

### Design Philosophy

**The Story Portal is not social media.**

| Social Media | Story Portal |
|--------------|--------------|
| Infinite scroll | Intentional, finite experience |
| Likes/followers | Meaningful witnessing |
| Algorithmic feed | Random wheel spin |
| Edited content | Spontaneous single-take |

**Mantra**: Slow down. Be present. Listen.

### Core Principles

1. **Ritual over efficiency** — Wheel animation should feel substantial
2. **Everyone has stories** — Never make users feel they need to be "good"
3. **Spontaneity unlocks authenticity** — No prompt browsing before spin
4. **Audio is intimate** — Recording should feel conversational
5. **Consent is sacred** — Prominent, unambiguous consent flow
6. **Facilitation built into UX** — Hints appear naturally

### The Contemplation State

Between spin and record, show:
1. Prompt prominently displayed
2. Flame animation around selected panel
3. Cycling facilitation cues (fade in/out every 4-5s)

### Steampunk Aesthetic Enforcement

| Use | Avoid |
|-----|-------|
| Brass, amber, aged paper, wood | Cold blues, whites, grays |
| Gears, patina, mechanical feel | Sterile, minimal, flat design |
| Substantial animations | Slick, frictionless transitions |

---

## 7. Success Metrics

### North Star Metric

**Stories Shared Per Active User** — Target: 3+ in first 30 days

### Key Performance Indicators

| Category | Metric | Target |
|----------|--------|--------|
| Activation | First spin rate | >80% |
| Activation | First story rate | >50% |
| Engagement | Stories per user | 3+ in 30 days |
| Engagement | Pass rate | <30% |
| Retention | Day 7 return | >30% |
| Retention | Day 30 return | >20% |

### Analytics: Google Analytics 4

Key events: `wheel_spin`, `prompt_pass`, `recording_start`, `recording_complete`, `story_saved`, `topic_pack_changed`

---

## 8. Constraints & Assumptions

### Resource Constraints
- Solo developer + Claude and agentic assistance
- Free tier infrastructure only
- Scope-driven timeline

### Scope Boundaries (NOT in MVP)
- User accounts, cloud sync
- Video recording
- Social network features
- Custom prompt creation
- Multi-language

### Definition of Done (MVP)

**Core Functionality**
- [ ] Spin wheel, land on prompt
- [ ] Pass once, accept second
- [ ] Contemplation screen with hints
- [ ] Record audio (up to 5 minutes)
- [ ] Optional photo attachment
- [ ] Consent flow
- [ ] Local story storage
- [ ] My Stories gallery
- [ ] Topic pack switching
- [ ] Offline core features

**Content & Polish**
- [ ] All content screens complete
- [ ] Steampunk aesthetic consistent
- [ ] Animations complete
- [ ] Sound design implemented

**Technical**
- [ ] PWA installable
- [ ] Works on 2018+ smartphones
- [ ] GA4 tracking
- [ ] Deployed to app.thestoryportal.org

---

*This is a living document. Update as decisions are made.*
