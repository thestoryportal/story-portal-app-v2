# Steam Modal Implementation Package

**Version:** 1.0.0  
**Target:** The Story Portal - Steam/Smoke Modal System  
**Complexity:** Novice-friendly with expert results

---

## What This Package Does

This package implements a theatrical steam/smoke modal system where content materializes from atmospheric steam rather than appearing in a traditional framed modal. It uses your existing `SmokeEffect.tsx` patterns and builds upon them.

### Before vs After

| Before (Failed) | After (This Package) |
|-----------------|----------------------|
| Dark, muddy smoke colors | Warm brown/tan matching existing app |
| Smoke just appears | Smoke "poofs" with animation |
| Modal has visible frame | Frameless - steam IS the container |
| Modals stack behind each other | Proper lifecycle management |
| Low contrast text | High contrast parchment panel |

---

## Prerequisites

Before starting, ensure you have:

- [ ] Node.js 18+ installed
- [ ] The Story Portal codebase cloned
- [ ] Access to the existing `SmokeEffect.tsx` file
- [ ] ~2 hours for full implementation

---

## Quick Start (Single Command)

```bash
# From your project root:
./steam-modal-package/deploy.sh
```

Or follow the step-by-step guide below.

---

## Step-by-Step Implementation Guide

### Step 0: Preparation (5 minutes)

#### 0.1 Verify Existing Files Exist

```bash
# These files MUST exist - we reference them
ls -la src/legacy/components/menu/SmokeEffect.tsx
ls -la src/legacy/styles/animations.css
```

If these don't exist, STOP - you need the original codebase.

#### 0.2 Clean Up Failed Implementation (if any)

```bash
# Remove any failed modal attempts (adjust paths as needed)
rm -f src/components/SteamModal.tsx
rm -f src/components/SteamModal.module.css
rm -f src/components/steam-modal/*.tsx
```

#### 0.3 Create Working Directory

```bash
mkdir -p src/components/steam-modal
mkdir -p src/components/steam-modal/__tests__
mkdir -p src/components/steam-modal/hooks
```

---

### Step 1: Backdrop Component (15 minutes)

**Goal:** Dark, warm-tinted overlay that dims the app

#### 1.1 Copy the Task Spec

The task specification is in: `./tasks/task-01-backdrop.md`

#### 1.2 Implementation

Create `src/components/steam-modal/Backdrop.tsx`:

```tsx
/**
 * Backdrop Component
 * 
 * Creates the darkened, warm-tinted background for the steam modal.
 * Clicking anywhere on the backdrop closes the modal.
 * 
 * REFERENCES:
 * - Colors from design-tokens-quick-ref.md
 * - Z-index: 1001 (below smoke layers)
 */

import { useEffect } from 'react';
import styles from './Backdrop.module.css';

interface BackdropProps {
  isOpen: boolean;
  onClose: () => void;
}

export function Backdrop({ isOpen, onClose }: BackdropProps) {
  // Prevent body scroll when modal is open
  useEffect(() => {
    if (isOpen) {
      document.body.style.overflow = 'hidden';
      return () => {
        document.body.style.overflow = '';
      };
    }
  }, [isOpen]);

  if (!isOpen) return null;

  return (
    <div
      className={styles.backdrop}
      onClick={onClose}
      role="button"
      tabIndex={0}
      aria-label="Close modal"
      onKeyDown={(e) => e.key === 'Escape' && onClose()}
    />
  );
}
```

Create `src/components/steam-modal/Backdrop.module.css`:

```css
.backdrop {
  position: fixed;
  inset: 0;
  z-index: 1001;
  cursor: pointer;
  
  /* Warm dark gradient with vignette - from design system */
  background: radial-gradient(
    ellipse 80% 80% at 50% 45%,
    rgba(20, 12, 8, 0.88) 0%,
    rgba(8, 5, 3, 0.94) 60%,
    rgba(0, 0, 0, 0.97) 100%
  );
  
  /* Entry animation */
  animation: backdropFadeIn 0.3s ease-out forwards;
}

/* Subtle warm tint overlay */
.backdrop::before {
  content: '';
  position: absolute;
  inset: 0;
  background: radial-gradient(
    ellipse at 50% 40%,
    rgba(255, 140, 50, 0.04) 0%,
    transparent 70%
  );
  pointer-events: none;
}

@keyframes backdropFadeIn {
  from {
    opacity: 0;
  }
  to {
    opacity: 1;
  }
}

/* Exit animation - applied via JS */
.backdrop[data-closing="true"] {
  animation: backdropFadeOut 0.3s ease-in forwards;
}

@keyframes backdropFadeOut {
  from {
    opacity: 1;
  }
  to {
    opacity: 0;
  }
}
```

#### 1.3 Verify

```bash
# Start dev server and test
npm run dev

# Open browser console and run:
# document.querySelector('[class*="backdrop"]') should exist when modal opens
```

#### 1.4 Checkpoint

- [ ] Backdrop covers entire viewport
- [ ] Warm vignette visible (not pure black)
- [ ] Click anywhere closes modal
- [ ] Body scroll disabled when open

**STOP HERE** - Get human approval before proceeding to Step 2.

---

### Step 2: Steam Field (25 minutes)

**Goal:** Animated smoke/steam background using EXISTING keyframes

#### 2.1 Critical Requirement

You MUST use colors from the existing `SmokeEffect.tsx`:

```tsx
// CORRECT - From SmokeEffect.tsx
rgba(140, 120, 100, 0.95)  // Main cloud
rgba(130, 110, 90, 0.9)    // Wisps
rgba(120, 100, 80, 0.8)    // Secondary

// WRONG - Do NOT use amber (spec was incorrect)
rgba(255, 160, 80, 0.08)   // NO!
```

#### 2.2 Implementation

Create `src/components/steam-modal/SteamField.tsx`:

```tsx
/**
 * SteamField Component
 * 
 * Creates the atmospheric steam background using CSS layers.
 * 
 * CRITICAL: Uses colors from SmokeEffect.tsx, NOT amber.
 * CRITICAL: Reuses existing keyframes from animations.css
 * 
 * REFERENCES:
 * - SmokeEffect.tsx for color palette
 * - animations.css for keyframes
 * - Z-index: 1002-1003 (above backdrop, below content)
 */

import { useMemo } from 'react';
import styles from './SteamField.module.css';

interface SteamFieldProps {
  isOpen: boolean;
  density?: 'light' | 'medium' | 'dense';
}

export function SteamField({ isOpen, density = 'medium' }: SteamFieldProps) {
  // Generate unique animation delays for organic feel
  const delays = useMemo(() => ({
    baseCloud: Math.random() * -4,
    wispLeft: Math.random() * -6,
    wispRight: Math.random() * -8,
    risingUpper: Math.random() * -3,
    puffA: Math.random() * -2,
    puffB: Math.random() * -4,
  }), []);

  if (!isOpen) return null;

  const densityClass = styles[`density_${density}`];

  return (
    <div className={`${styles.steamField} ${densityClass}`}>
      {/* Layer 1: Base Cloud (center) */}
      <div 
        className={styles.baseCloud}
        style={{ animationDelay: `${delays.baseCloud}s` }}
      />
      
      {/* Layer 2: Wisp Left */}
      <div 
        className={styles.wispLeft}
        style={{ animationDelay: `${delays.wispLeft}s` }}
      />
      
      {/* Layer 3: Wisp Right */}
      <div 
        className={styles.wispRight}
        style={{ animationDelay: `${delays.wispRight}s` }}
      />
      
      {/* Layer 4: Rising Steam */}
      <div 
        className={styles.risingUpper}
        style={{ animationDelay: `${delays.risingUpper}s` }}
      />
      
      {/* Layer 5-6: Accent Puffs */}
      <div 
        className={styles.puffA}
        style={{ animationDelay: `${delays.puffA}s` }}
      />
      <div 
        className={styles.puffB}
        style={{ animationDelay: `${delays.puffB}s` }}
      />
    </div>
  );
}
```

Create `src/components/steam-modal/SteamField.module.css`:

```css
/**
 * SteamField Styles
 * 
 * CRITICAL COLOR NOTE:
 * These colors are from SmokeEffect.tsx (warm brown/tan).
 * The original spec incorrectly specified amber - IGNORE THAT.
 * 
 * Color palette (from SmokeEffect.tsx):
 * - Main: rgba(140, 120, 100, X)
 * - Secondary: rgba(130, 110, 90, X)
 * - Tertiary: rgba(120, 100, 80, X)
 */

.steamField {
  position: fixed;
  inset: 0;
  z-index: 1002;
  overflow: hidden;
  pointer-events: none;
}

/* Entry animation for the whole field */
.steamField {
  animation: steamFieldEntry 0.6s cubic-bezier(0.25, 0.46, 0.45, 0.94) forwards;
}

@keyframes steamFieldEntry {
  from {
    opacity: 0;
    transform: scale(0.8);
  }
  to {
    opacity: 1;
    transform: scale(1);
  }
}

/* ============================================
   Layer 1: Base Cloud (Center)
   ============================================ */
.baseCloud {
  position: absolute;
  top: 50%;
  left: 50%;
  width: 120%;
  height: 100%;
  transform: translate(-50%, -50%);
  
  /* Warm brown from SmokeEffect.tsx */
  background: radial-gradient(
    ellipse 60% 50% at 50% 50%,
    rgba(140, 120, 100, 0.12) 0%,
    rgba(120, 100, 80, 0.06) 40%,
    transparent 70%
  );
  
  filter: blur(40px);
  opacity: 0.6;
  
  animation: steamBaseFloat 8s ease-in-out infinite;
}

@keyframes steamBaseFloat {
  0%, 100% {
    transform: translate(-50%, -50%) scale(1);
  }
  50% {
    transform: translate(-50%, -52%) scale(1.03);
  }
}

/* ============================================
   Layer 2-3: Side Wisps
   ============================================ */
.wispLeft {
  position: absolute;
  top: 30%;
  left: 5%;
  width: 40%;
  height: 60%;
  
  /* Warm brown from SmokeEffect.tsx */
  background: radial-gradient(
    ellipse at 30% 50%,
    rgba(130, 110, 90, 0.08) 0%,
    transparent 60%
  );
  
  filter: blur(30px);
  
  /* Reuse existing animation */
  animation: smokeLingerLeft 12s ease-in-out infinite;
}

.wispRight {
  position: absolute;
  top: 30%;
  right: 5%;
  width: 40%;
  height: 60%;
  
  background: radial-gradient(
    ellipse at 70% 50%,
    rgba(130, 110, 90, 0.08) 0%,
    transparent 60%
  );
  
  filter: blur(30px);
  
  animation: smokeLingerRight 14s ease-in-out infinite;
}

/* ============================================
   Layer 4: Rising Steam
   ============================================ */
.risingUpper {
  position: absolute;
  bottom: 40%;
  left: 50%;
  width: 80%;
  height: 50%;
  transform: translateX(-50%);
  
  background: radial-gradient(
    ellipse 50% 80% at 50% 100%,
    rgba(140, 120, 100, 0.07) 0%,
    transparent 60%
  );
  
  filter: blur(35px);
  
  animation: smokeLingerUp 10s ease-in-out infinite;
}

/* ============================================
   Layer 5-6: Accent Puffs
   ============================================ */
.puffA,
.puffB {
  position: absolute;
  width: 15%;
  height: 20%;
  border-radius: 50%;
  
  background: radial-gradient(
    circle,
    rgba(130, 110, 90, 0.1) 0%,
    transparent 70%
  );
  
  filter: blur(20px);
}

.puffA {
  top: 25%;
  left: 20%;
  animation: steamPuffDrift 6s ease-in-out infinite;
}

.puffB {
  top: 60%;
  right: 25%;
  animation: steamPuffDrift 7s ease-in-out infinite reverse;
}

@keyframes steamPuffDrift {
  0%, 100% {
    transform: translate(0, 0) scale(1);
    opacity: 0.5;
  }
  50% {
    transform: translate(10px, -15px) scale(1.1);
    opacity: 0.7;
  }
}

/* ============================================
   Density Variants
   ============================================ */
.density_light .baseCloud { opacity: 0.4; }
.density_light .wispLeft,
.density_light .wispRight { opacity: 0.6; }

.density_medium .baseCloud { opacity: 0.6; }
.density_medium .wispLeft,
.density_medium .wispRight { opacity: 0.8; }

.density_dense .baseCloud { opacity: 0.8; }
.density_dense .wispLeft,
.density_dense .wispRight { opacity: 1; }

/* ============================================
   Reuse existing keyframes from animations.css
   If these don't exist, add them:
   ============================================ */
@keyframes smokeLingerLeft {
  0% {
    transform: translate(0, 0);
    opacity: 0.6;
  }
  50% {
    transform: translate(-30px, -20px);
    opacity: 0.8;
  }
  100% {
    transform: translate(0, 0);
    opacity: 0.6;
  }
}

@keyframes smokeLingerRight {
  0% {
    transform: translate(0, 0);
    opacity: 0.6;
  }
  50% {
    transform: translate(30px, -15px);
    opacity: 0.8;
  }
  100% {
    transform: translate(0, 0);
    opacity: 0.6;
  }
}

@keyframes smokeLingerUp {
  0% {
    transform: translateX(-50%) translateY(0);
    opacity: 0.5;
  }
  50% {
    transform: translateX(-50%) translateY(-40px);
    opacity: 0.7;
  }
  100% {
    transform: translateX(-50%) translateY(0);
    opacity: 0.5;
  }
}
```

#### 2.3 Verify

Open the app and check:
- Smoke should be warm brown/tan (NOT amber/orange)
- Smoke should animate smoothly
- Performance should be 60fps

#### 2.4 Checkpoint

- [ ] Colors match SmokeEffect.tsx (warm brown, not amber)
- [ ] Animations are smooth (60fps)
- [ ] Steam is denser at edges, clearer at center
- [ ] No visible frame or border

**STOP HERE** - Get human approval before proceeding to Step 3.

---

### Step 3: Content Panel (20 minutes)

**Goal:** Readable text area with HIGH CONTRAST

#### 3.1 Critical Requirement

This was the CRITICAL failure point in the previous implementation:

```css
/* CORRECT - High contrast */
background: #f4e4c8;  /* Parchment */
color: #2a1a0a;       /* Dark brown */
/* Contrast ratio: 14:1 (exceeds WCAG AAA) */

/* WRONG - What failed before */
background: transparent or dark;
color: #f4e4c8 (light on dark = low contrast);
```

#### 3.2 Implementation

Create `src/components/steam-modal/ContentPanel.tsx`:

```tsx
/**
 * ContentPanel Component
 * 
 * The readable content area with HIGH CONTRAST text.
 * 
 * CRITICAL: Background is parchment (#f4e4c8), text is dark brown (#2a1a0a)
 * This provides 14:1 contrast ratio (WCAG AAA compliant).
 * 
 * REFERENCES:
 * - phase-1-foundation-spec.md Section 4
 * - design-tokens-quick-ref.md for colors
 */

import { ReactNode } from 'react';
import styles from './ContentPanel.module.css';

interface ContentPanelProps {
  children: ReactNode;
  title?: string;
}

export function ContentPanel({ children, title }: ContentPanelProps) {
  return (
    <div className={styles.contentPanel}>
      {title && (
        <h2 className={styles.sectionTitle}>{title}</h2>
      )}
      <div className={styles.bodyContent}>
        {children}
      </div>
    </div>
  );
}

// Sub-component for paragraphs with staggered animation
export function ContentParagraph({ 
  children, 
  index = 0 
}: { 
  children: ReactNode; 
  index?: number;
}) {
  return (
    <p 
      className={styles.bodyText}
      style={{ animationDelay: `${0.4 + (index * 0.1)}s` }}
    >
      {children}
    </p>
  );
}

// Sub-component for dividers
export function ContentDivider() {
  return <hr className={styles.divider} />;
}
```

Create `src/components/steam-modal/ContentPanel.module.css`:

```css
/**
 * ContentPanel Styles
 * 
 * CRITICAL CONTRAST REQUIREMENT:
 * - Background: #f4e4c8 (parchment)
 * - Text: #2a1a0a (dark brown)
 * - Contrast ratio: 14:1 (WCAG AAA)
 * 
 * DO NOT CHANGE THESE COLORS without verifying contrast.
 */

.contentPanel {
  position: relative;
  z-index: 1004;
  
  max-width: 800px;
  max-height: calc(85vh - 200px);
  margin: 80px auto 0;
  padding: 32px 40px 40px;
  
  overflow-y: auto;
  overflow-x: hidden;
  
  /* CRITICAL: Parchment background for readability */
  background: #f4e4c8;
  border-radius: 8px;
  
  /* Subtle depth */
  box-shadow:
    inset 0 0 20px rgba(139, 111, 71, 0.1),
    0 4px 20px rgba(0, 0, 0, 0.3);
  
  /* Entry animation */
  animation: contentPanelEntry 0.5s ease-out forwards;
  animation-delay: 0.3s;
  opacity: 0;
}

@keyframes contentPanelEntry {
  from {
    opacity: 0;
    transform: translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

/* ============================================
   Section Headings
   ============================================ */
.sectionTitle {
  font-family: 'Carnivalee Freakshow', serif;
  font-size: 24px;
  /* CRITICAL: Dark brown for high contrast */
  color: #2a1a0a;
  margin: 0 0 16px 0;
  text-transform: uppercase;
  letter-spacing: 1px;
}

/* Decorative underline */
.sectionTitle::after {
  content: '';
  display: block;
  width: 100%;
  height: 2px;
  background: linear-gradient(
    90deg,
    transparent 0%,
    #c89038 20%,
    #8B6F47 50%,
    #c89038 80%,
    transparent 100%
  );
  margin-top: 8px;
}

/* ============================================
   Body Text
   ============================================ */
.bodyText {
  font-family: 'Molly Sans', sans-serif;
  font-size: 16px;
  line-height: 1.6;
  /* CRITICAL: Dark brown for high contrast */
  color: #2a1a0a;
  margin-bottom: 16px;
  
  /* Entry animation */
  opacity: 0;
  transform: translateY(12px);
  animation: textEmerge 0.5s ease-out forwards;
}

@keyframes textEmerge {
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

/* ============================================
   Dividers
   ============================================ */
.divider {
  height: 1px;
  margin: 32px 0;
  border: none;
  background: linear-gradient(
    90deg,
    transparent 0%,
    rgba(139, 111, 71, 0.3) 15%,
    rgba(139, 111, 71, 0.5) 50%,
    rgba(139, 111, 71, 0.3) 85%,
    transparent 100%
  );
}

/* ============================================
   Scrollbar Styling
   ============================================ */
.contentPanel::-webkit-scrollbar {
  width: 8px;
}

.contentPanel::-webkit-scrollbar-track {
  background: rgba(139, 111, 71, 0.1);
  border-radius: 4px;
}

.contentPanel::-webkit-scrollbar-thumb {
  background: rgba(139, 111, 71, 0.4);
  border-radius: 4px;
}

.contentPanel::-webkit-scrollbar-thumb:hover {
  background: rgba(139, 111, 71, 0.6);
}

/* ============================================
   Body Content Container
   ============================================ */
.bodyContent {
  /* Container for children */
}
```

#### 3.3 Verify Contrast

```bash
# Use browser dev tools:
# 1. Inspect the content panel
# 2. Check computed styles
# 3. Background should be #f4e4c8
# 4. Text color should be #2a1a0a
# 5. Use contrast checker: https://webaim.org/resources/contrastchecker/
```

#### 3.4 Checkpoint

- [ ] Background is parchment (#f4e4c8)
- [ ] ALL text is dark brown (#2a1a0a)
- [ ] Text is clearly readable
- [ ] Contrast ratio is 14:1 or higher

**STOP HERE** - Get human approval before proceeding to Step 4.

---

### Step 4: Panel Header (15 minutes)

**Goal:** Wooden panel title that tumbles in from above

#### 4.1 Implementation

Create `src/components/steam-modal/PanelHeader.tsx`:

```tsx
/**
 * PanelHeader Component
 * 
 * Wooden panel that animates in from above.
 * Uses the same style as hamburger menu panels.
 * 
 * REFERENCES:
 * - MenuPanelItem.tsx for wooden panel styling
 * - wood-panel.webp texture
 */

import styles from './PanelHeader.module.css';

interface PanelHeaderProps {
  title: string;
}

export function PanelHeader({ title }: PanelHeaderProps) {
  return (
    <div className={styles.header}>
      {/* Corner rivets */}
      <div className={`${styles.rivet} ${styles.rivetTL}`} />
      <div className={`${styles.rivet} ${styles.rivetTR}`} />
      <div className={`${styles.rivet} ${styles.rivetBL}`} />
      <div className={`${styles.rivet} ${styles.rivetBR}`} />
      
      {/* Title text */}
      <h1 className={styles.title}>{title}</h1>
    </div>
  );
}
```

Create `src/components/steam-modal/PanelHeader.module.css`:

```css
/**
 * PanelHeader Styles
 * 
 * Wooden panel styling matching the hamburger menu panels.
 */

.header {
  position: fixed;
  top: 20px;
  left: 50%;
  transform: translateX(-50%);
  z-index: 1003;
  
  min-width: 300px;
  max-width: 600px;
  padding: 16px 40px;
  
  /* Wood texture background */
  background: 
    linear-gradient(
      180deg,
      rgba(74, 53, 32, 0.95) 0%,
      rgba(58, 42, 26, 0.98) 50%,
      rgba(42, 30, 18, 1) 100%
    );
  background-color: #4a3520;
  
  /* Bronze border */
  border: 3px solid #8B6F47;
  border-radius: 8px;
  
  /* Depth */
  box-shadow:
    0 4px 20px rgba(0, 0, 0, 0.5),
    inset 0 1px 0 rgba(255, 200, 100, 0.1),
    inset 0 -2px 4px rgba(0, 0, 0, 0.3);
  
  /* Entry animation - tumble in */
  animation: headerTumbleIn 0.5s cubic-bezier(0.25, 0.46, 0.45, 0.94) forwards;
  animation-delay: 0.15s;
  opacity: 0;
  transform: translateX(-50%) perspective(1000px) rotateX(-90deg) translateY(-100px);
  transform-origin: top center;
}

@keyframes headerTumbleIn {
  0% {
    opacity: 0;
    transform: translateX(-50%) perspective(1000px) rotateX(-90deg) translateY(-100px);
  }
  60% {
    opacity: 1;
    transform: translateX(-50%) perspective(1000px) rotateX(10deg) translateY(0);
  }
  80% {
    transform: translateX(-50%) perspective(1000px) rotateX(-5deg) translateY(0);
  }
  100% {
    opacity: 1;
    transform: translateX(-50%) perspective(1000px) rotateX(0deg) translateY(0);
  }
}

/* ============================================
   Title Text
   ============================================ */
.title {
  font-family: 'Carnivalee Freakshow', serif;
  font-size: 28px;
  color: #f5deb3;
  text-align: center;
  margin: 0;
  letter-spacing: 2px;
  text-transform: uppercase;
  
  /* Text shadow for depth */
  text-shadow:
    0 1px 0 rgba(255, 240, 220, 0.4),
    0 2px 4px rgba(0, 0, 0, 0.8);
}

/* ============================================
   Corner Rivets
   ============================================ */
.rivet {
  position: absolute;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: radial-gradient(
    circle at 30% 30%,
    #d4a045 0%,
    #8B6F47 50%,
    #5a4030 100%
  );
  box-shadow:
    inset 0 1px 2px rgba(255, 220, 150, 0.5),
    0 1px 2px rgba(0, 0, 0, 0.5);
}

.rivetTL { top: 8px; left: 8px; }
.rivetTR { top: 8px; right: 8px; }
.rivetBL { bottom: 8px; left: 8px; }
.rivetBR { bottom: 8px; right: 8px; }
```

#### 4.2 Checkpoint

- [ ] Header tumbles in from above (not instant)
- [ ] Wooden texture visible
- [ ] Bronze border present
- [ ] Corner rivets visible
- [ ] Title text is centered and readable

**STOP HERE** - Get human approval before proceeding to Step 5.

---

### Step 5: Close Button (10 minutes)

**Goal:** Brass circular button in top-right

#### 5.1 Implementation

Create `src/components/steam-modal/CloseButton.tsx`:

```tsx
/**
 * CloseButton Component
 * 
 * Simple brass circular button for closing the modal.
 * Full valve wheel design comes in Phase 3.
 */

import styles from './CloseButton.module.css';

interface CloseButtonProps {
  onClick: () => void;
}

export function CloseButton({ onClick }: CloseButtonProps) {
  return (
    <button
      className={styles.closeButton}
      onClick={onClick}
      aria-label="Close modal"
      type="button"
    >
      <span className={styles.icon}>×</span>
    </button>
  );
}
```

Create `src/components/steam-modal/CloseButton.module.css`:

```css
/**
 * CloseButton Styles
 * 
 * Brass circular button matching design system.
 */

.closeButton {
  position: fixed;
  top: 24px;
  right: 24px;
  z-index: 1006;
  
  width: 44px;
  height: 44px;
  padding: 0;
  
  /* Brass gradient */
  background: linear-gradient(
    180deg,
    #6a5a4a 0%,
    #4a3a2a 40%,
    #2a1a0a 100%
  );
  
  border: 2px solid #8B6F47;
  border-radius: 50%;
  cursor: pointer;
  
  /* Depth */
  box-shadow:
    0 4px 12px rgba(0, 0, 0, 0.4),
    inset 0 1px 0 rgba(255, 200, 100, 0.15),
    inset 0 -2px 4px rgba(0, 0, 0, 0.3);
  
  /* Entry animation */
  animation: closeFadeIn 0.2s ease-out forwards;
  animation-delay: 0.8s;
  opacity: 0;
  
  transition: transform 0.15s ease, box-shadow 0.15s ease;
}

@keyframes closeFadeIn {
  to {
    opacity: 0.8;
  }
}

.closeButton:hover {
  opacity: 1 !important;
  transform: translateY(-2px);
  
  background: linear-gradient(
    180deg,
    #7a6a5a 0%,
    #5a4a3a 40%,
    #3a2a1a 100%
  );
  
  box-shadow:
    0 6px 20px rgba(0, 0, 0, 0.5),
    0 0 15px rgba(255, 184, 54, 0.1),
    inset 0 1px 0 rgba(255, 200, 100, 0.2),
    inset 0 -2px 4px rgba(0, 0, 0, 0.2);
}

.closeButton:active {
  transform: translateY(1px);
  
  box-shadow:
    0 2px 6px rgba(0, 0, 0, 0.4),
    inset 0 2px 4px rgba(0, 0, 0, 0.4);
}

.closeButton:focus-visible {
  outline: 2px solid #ffb836;
  outline-offset: 2px;
}

.icon {
  font-size: 24px;
  line-height: 1;
  color: #f5deb3;
  display: block;
}
```

#### 5.2 Checkpoint

- [ ] Button is positioned top-right
- [ ] Brass appearance
- [ ] Hover effect works
- [ ] Click closes modal
- [ ] Keyboard accessible (Tab + Enter)

**STOP HERE** - Get human approval before proceeding to Step 6.

---

### Step 6: Main Component Assembly (20 minutes)

**Goal:** Combine all components with proper lifecycle management

#### 6.1 Critical Requirement

The modal lifecycle MUST:
- Mount/unmount completely (no stacking)
- Clean up event listeners
- Handle Escape key
- Trap focus

#### 6.2 Implementation

Create `src/components/steam-modal/SteamModal.tsx`:

```tsx
/**
 * SteamModal Component
 * 
 * Main modal assembly combining all sub-components.
 * 
 * CRITICAL: Proper lifecycle management to prevent stacking.
 */

import { useEffect, useCallback, useRef, ReactNode } from 'react';
import { createPortal } from 'react-dom';
import { Backdrop } from './Backdrop';
import { SteamField } from './SteamField';
import { PanelHeader } from './PanelHeader';
import { ContentPanel } from './ContentPanel';
import { CloseButton } from './CloseButton';
import styles from './SteamModal.module.css';

interface SteamModalProps {
  isOpen: boolean;
  onClose: () => void;
  title: string;
  children: ReactNode;
  variant?: 'standard' | 'form' | 'gallery' | 'legal';
  steamDensity?: 'light' | 'medium' | 'dense';
}

export function SteamModal({
  isOpen,
  onClose,
  title,
  children,
  variant = 'standard',
  steamDensity = 'medium',
}: SteamModalProps) {
  const modalRef = useRef<HTMLDivElement>(null);
  const previousActiveElement = useRef<HTMLElement | null>(null);

  // Handle escape key
  const handleKeyDown = useCallback((event: KeyboardEvent) => {
    if (event.key === 'Escape') {
      onClose();
    }
  }, [onClose]);

  // Setup and cleanup
  useEffect(() => {
    if (isOpen) {
      // Store current focus
      previousActiveElement.current = document.activeElement as HTMLElement;
      
      // Add escape listener
      document.addEventListener('keydown', handleKeyDown);
      
      // Focus the modal
      modalRef.current?.focus();
      
      return () => {
        document.removeEventListener('keydown', handleKeyDown);
        
        // Restore focus
        previousActiveElement.current?.focus();
      };
    }
  }, [isOpen, handleKeyDown]);

  // Don't render if not open
  if (!isOpen) return null;

  // Determine steam density based on variant
  const actualDensity = variant === 'legal' ? 'light' : 
                        variant === 'form' ? 'light' :
                        steamDensity;

  // Render via portal to ensure proper stacking
  return createPortal(
    <div 
      ref={modalRef}
      className={styles.modalContainer}
      role="dialog"
      aria-modal="true"
      aria-labelledby="modal-title"
      tabIndex={-1}
    >
      {/* Layer 1: Backdrop */}
      <Backdrop isOpen={isOpen} onClose={onClose} />
      
      {/* Layer 2: Steam Field */}
      <SteamField isOpen={isOpen} density={actualDensity} />
      
      {/* Layer 3: Panel Header */}
      <PanelHeader title={title} />
      
      {/* Layer 4: Content */}
      <ContentPanel title="">
        {children}
      </ContentPanel>
      
      {/* Layer 6: Close Button */}
      <CloseButton onClick={onClose} />
    </div>,
    document.body
  );
}

// Re-export sub-components for convenience
export { ContentParagraph, ContentDivider } from './ContentPanel';
```

Create `src/components/steam-modal/SteamModal.module.css`:

```css
/**
 * SteamModal Container Styles
 */

.modalContainer {
  /* Container for all modal layers */
  position: fixed;
  inset: 0;
  z-index: 1000;
  
  /* Prevent any overflow */
  overflow: hidden;
}

/* Focus trap indicator */
.modalContainer:focus {
  outline: none;
}
```

Create `src/components/steam-modal/index.ts`:

```tsx
/**
 * Steam Modal Exports
 */

export { SteamModal, ContentParagraph, ContentDivider } from './SteamModal';
export type { } from './SteamModal';
```

#### 6.3 Usage Example

```tsx
import { useState } from 'react';
import { SteamModal, ContentParagraph, ContentDivider } from './components/steam-modal';

function App() {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <>
      <button onClick={() => setIsOpen(true)}>Open Modal</button>
      
      <SteamModal
        isOpen={isOpen}
        onClose={() => setIsOpen(false)}
        title="Our Story"
        variant="standard"
      >
        <ContentParagraph index={0}>
          Welcome to The Story Portal, where tales come alive through 
          the breath of the machine.
        </ContentParagraph>
        
        <ContentDivider />
        
        <ContentParagraph index={1}>
          Every story you share becomes part of our collective memory,
          preserved in steam and brass.
        </ContentParagraph>
      </SteamModal>
    </>
  );
}
```

#### 6.4 Final Checkpoint

- [ ] Modal opens without stacking issues
- [ ] Modal closes completely (no remnants)
- [ ] Escape key closes modal
- [ ] Click outside closes modal
- [ ] All animations play correctly
- [ ] Text is readable (high contrast)
- [ ] Steam colors match SmokeEffect.tsx

---

## Troubleshooting

### Issue: Modals Stack Behind Each Other

**Cause:** Multiple modal instances are being mounted.

**Fix:** Ensure your state management only has ONE modal state:

```tsx
// WRONG - Multiple states
const [isStoryOpen, setStoryOpen] = useState(false);
const [isBookingOpen, setBookingOpen] = useState(false);

// RIGHT - Single state with content
const [modalContent, setModalContent] = useState<null | 'story' | 'booking'>(null);
```

### Issue: Smoke is Amber/Orange Instead of Brown

**Cause:** Using colors from the spec instead of SmokeEffect.tsx.

**Fix:** Check your SteamField.module.css colors:

```css
/* WRONG */
rgba(255, 160, 80, 0.08)

/* RIGHT */
rgba(140, 120, 100, 0.12)
```

### Issue: Text is Hard to Read

**Cause:** Missing or incorrect contrast colors.

**Fix:** Verify ContentPanel.module.css:

```css
.contentPanel {
  background: #f4e4c8;  /* Must be this exact color */
}

.bodyText {
  color: #2a1a0a;  /* Must be this exact color */
}
```

### Issue: Animations Don't Play

**Cause:** CSS animations not loading or conflicting.

**Fix:** Check that CSS modules are being imported correctly and no `animation: none` overrides exist.

---

## Phase 2 & 3 Preview

After completing Phase 1 and getting human approval, you can proceed to:

- **Phase 2:** Interactive canvas wisps, enhanced steam layers, texture overlays
- **Phase 3:** Coalescence entry animation, dissipation exit, valve wheel button, sound effects
- **Phase 4:** Accessibility audit, reduced motion, high contrast mode

These phases build on the Phase 1 foundation and use the same atomic task approach.

---

## Support

If you encounter issues:

1. Check the Troubleshooting section above
2. Verify all checkpoints passed
3. Compare your colors to SmokeEffect.tsx
4. Ensure single modal state management

---

_End of README_
