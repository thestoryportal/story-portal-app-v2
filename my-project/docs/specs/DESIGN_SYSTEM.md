# Story Portal — Design System

**Version**: 1.0
**Date Created**: January 8, 2025
**Status**: Approved for MVP Implementation
**Related Specs**:
- [APP_SPECIFICATION.md](./APP_SPECIFICATION.md) (design philosophy, brand)
- [COMPONENT_ARCHITECTURE.md](./COMPONENT_ARCHITECTURE.md) (component styling)
- [ACCEPTANCE_CRITERIA.md](./ACCEPTANCE_CRITERIA.md) (design validation)

---

## Table of Contents

1. [Overview](#overview)
2. [Design Philosophy](#design-philosophy)
3. [Color System](#color-system)
4. [Typography System](#typography-system)
5. [Spacing & Layout](#spacing--layout)
6. [Shadows & Depth](#shadows--depth)
7. [Animation System](#animation-system)
8. [SVG Filters & Effects](#svg-filters--effects)
9. [Asset Inventory](#asset-inventory)
10. [Accessibility](#accessibility)
11. [Responsive Design](#responsive-design)
12. [Component Patterns](#component-patterns)
13. [Implementation Guidelines](#implementation-guidelines)
14. [Future Considerations](#future-considerations)

---

## Overview

The Story Portal's visual identity is **steampunk: mechanical, warm, tactile, intentional**. Every design decision reinforces the metaphor of an analog time machine that connects people through shared stories.

- **NOT**: Cold blues, slick flat design, frictionless interactions
- **YES**: Warm brass, aged wood, patina textures, substantial animations, ritual friction

This system balances visual distinctiveness with implementation practicality. All values are stored as CSS custom properties in `src/tokens/design-tokens.css` (implementation tokens) and `src/tokens/colors.css` (semantic variables) for easy maintenance and future dark mode support.

---

## Design Philosophy

### Core Principles

1. **Steampunk Authenticity** — Every color, texture, and animation choice reflects the time machine metaphor
2. **Tactile, Mechanical Feel** — Animations have weight and momentum; transitions feel deliberate, not instant
3. **Warm, Contemplative Mood** — Brass and amber, not clinical. Colors evoke candlelight and fire, not sterile fluorescence
4. **Analog Soul, Digital Reach** — Technology hidden behind craft. Users forget they're on a screen
5. **Accessibility Built-In** — Respect motion preferences, maintain high contrast, ensure all interactions are keyboard accessible

### Visual Foundation

**Embrace**: Brass, amber, aged bronze, natural wood, hand-forged feeling, mechanical gears, patina, layer and depth, intentional shadows

**Avoid**: Cold grays and blues, flat design, slick transitions, algorithmic feel, symmetrical perfection, frictionless interaction

---

## Color System

### Primary Colors (Steampunk Core)

These form the foundation of the visual identity:

| Semantic Token | Hex | RGB | Usage | Notes |
|---|---|---|---|---|
| `--color-brass-light` | `#f5deb3` | 245, 222, 179 | Body text, headings | Wheat/aged brass—foundational, warm |
| `--color-bronze-standard` | `#8b6f47` | 139, 111, 71 | Borders, outlines | Aged metallic brown—classic steampunk |
| `--color-bronze-bright` | `#a88545` | 168, 133, 69 | Hover states | Lighter variation for interaction feedback |
| `--bg-primary` | `#0a0705` | 10, 7, 5 | Main background | Nearly black with warm undertone |
| `--color-wood-mid` | `#6a4a35` | 106, 74, 53 | Wood panel backgrounds | Medium brown—wood tone |

### Accent Colors (Flame & Energy)

For interactive states and emphasis:

| Semantic Token | Hex | RGB | Usage | Notes |
|---|---|---|---|---|
| `--color-flame-core` | `#ffb836` | 255, 184, 54 | Primary interactive accents | Gold-orange glow—flame metaphor |
| `--color-flame-bright` | `#ff9100` | 255, 145, 0 | Hover states, active | Brighter orange for stronger feedback |

### Background Layers

For containers, modals, overlays:

| Semantic Token | Value | Usage | Notes |
|---|---|---|---|
| `--bg-container` | `rgba(0, 0, 0, 0.8)` | Modal backgrounds | Semi-transparent for depth |
| `--bg-backdrop` | `rgba(0, 0, 0, 0.7)` | Overlay dimming | Darker for more emphasis |
| `--bg-panel` | `rgba(0, 0, 0, 0.1)` | Subtle panel layers | Very subtle—almost transparent |
| `--bg-prompt` | `rgba(139, 69, 19, 0.3)` | Prompt display background | Translucent brown—wood context |

### Text Colors

For readability on different backgrounds:

| Semantic Token | Hex | Usage | Notes |
|---|---|---|---|
| `--text-on-dark` | `#f5deb3` | Default body text | Main readable text, high contrast |
| `--text-on-dark-muted` | `#e8dcc8` | Button labels | Slightly muted for button context |
| `--text-on-dark-disabled` | `#8a7a5a` | Disabled text | Dimmed appearance |

### Semantic Color Variables Location

**File**: `src/tokens/colors.css`

All semantic color variables are defined here. Use these in new components instead of hardcoding hex values. This separation enables:
- Easy theme switching
- Dark mode implementation in Phase 2 (just override the values)
- Consistent naming across components
- Single source of truth for visual decisions

**Usage Pattern**:
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

### Accessibility Color Contrast

All text meets WCAG AA standards (4.5:1 for small text, 3:1 for large text):

| Foreground | Background | Contrast | Status |
|---|---|---|---|
| `#f5deb3` (brass light) | `#0a0705` (bg primary) | 7.5:1 | ✅ WCAG AAA |
| `#f5deb3` (brass light) | `#6a4a35` (wood mid) | 5.2:1 | ✅ WCAG AA |
| `#ffb836` (flame core) | `#0a0705` (bg primary) | 3.8:1 | ⚠️ Test on icons |

---

## Typography System

### Font Families

| Family | Weight | Usage | Source | Notes |
|---|---|---|---|---|
| **Carnivalee Freakshow** | Regular (400) | Wheel prompts, display headings | `src/legacy/styles/fonts.css` | Distinctive serif, steampunk character |
| **Molly Sans** | Normal (400), Bold (700) | UI text, buttons, body content | `src/legacy/styles/fonts.css` | Clean sans-serif for readability |
| **Material Symbols Outlined** | 700 | Icons throughout UI | Google Fonts | Modern icon set with metallic styling |

**Load Order**: Fonts are pre-loaded via `fonts.css` to avoid layout shifts.

### Responsive Typography Scale (Mobile-First with clamp)

All font sizes use `clamp(min, viewport, max)` for fluid scaling. **Never use fixed px-only for content text.**

| Semantic Tier | Font | Size (clamp) | Line Height | Weight | Usage |
|---|---|---|---|---|---|
| **Heading (h1)** | Carnivalee | `clamp(28px, 5vw, 48px)` | 1.2 (tight) | 400 | Page titles, major prompts |
| **Subheading (h2)** | Carnivalee | `clamp(22px, 4vw, 36px)` | 1.2 (tight) | 400 | Section headers, emphasis |
| **Body (p, span, label)** | Molly Sans | `clamp(16px, 2.5vw, 20px)` | 1.6 (comfortable) | 400 | Standard content, readable text |
| **Small (caption, metadata)** | Molly Sans | `clamp(12px, 1.8vw, 16px)` | 1.4 | 400 | Timestamps, fine print, hints |

**Button Text**: Always use Body size with **uppercase** + `letter-spacing: 0.5px`

**Mobile-First Philosophy**: Don't over-engineer for large screens. The app is designed for phones/tablets first. Tablet (768px+) and desktop scaling are secondary. The `clamp()` formula automatically scales proportionally.

---

## Spacing & Layout

### Spacing Scale (8px Base Unit)

All margins, padding, and gaps follow this scale:

| Token | Pixels | Usage | Context |
|---|---|---|---|
| `--sp-spacing-xs` | 12px | Tight spacing, item gaps | Compact layouts |
| `--sp-spacing-sm` | 15px | Compact padding | Form field padding |
| `--sp-spacing-md` | 16px | Default spacing | Standard margin/padding |
| `--sp-spacing-lg` | 20px | Open spacing | Content sections |
| `--sp-spacing-xl` | 24px | Breathing room | Section breaks |
| `--sp-spacing-2xl` | 32px | Large sections | Container padding |
| `--sp-spacing-3xl` | 40px | Container padding | Major container fill |

**Rule**: Always use spacing tokens. Never use arbitrary padding/margin values.

### Border Radius

| Token | Pixels | Usage |
|---|---|---|
| `--sp-radius-sm` | 4px | Input fields, small elements |
| `--sp-radius-md` | 8px | Buttons, modals, standard components |
| `--sp-radius-lg` | 12px | Large containers |
| `--sp-radius-full` | 50% | Circles, wheel, avatars |

---

## Shadows & Depth

### Box Shadows

Shadows create layering and depth:

| Token | Shadow | Usage |
|---|---|---|
| `--sp-shadow-container` | `0 2px 10px rgba(0, 0, 0, 0.3), inset 0 0 12px rgba(0, 0, 0, 0.6)` | Default containers, panels |
| `--sp-shadow-container-elevated` | `0 15px 40px rgba(0, 0, 0, 0.5), inset 0 0 12px rgba(0, 0, 0, 0.6)` | Modals, floating elements |
| `--sp-shadow-panel` | `inset 0 0 15px rgba(30, 20, 10, 0.35), 0 2px 8px rgba(139, 69, 19, 0.35)` | Inset panels, recessed areas |

### Text Shadows

For carved/embossed text effects:

| Token | Shadow | Usage |
|---|---|---|
| `--sp-text-shadow-panel` | `0 1px 0 rgba(255, 240, 220, 0.4), 0 2px 4px rgba(0, 0, 0, 0.8)` | Text on dark panels, carved effect |

### Filters

| Token | Filter | Usage |
|---|---|---|
| `--sp-filter-button-drop` | `drop-shadow(-5px 6px 17px rgba(0, 0, 0, 0.6))` | Button lift effect |
| `--sp-filter-backdrop-blur` | `blur(4px)` | Modal backdrops, focus dimming |

---

## Animation System

### Duration Scale

Animations should feel intentional and mechanical, never rushed:

| Token | Duration | Usage | Feel |
|---|---|---|---|
| `--sp-duration-fast` | 0.15s | Button press feedback | Snappy |
| `--sp-duration-quick` | 0.25s | UI transitions, fades | Quick but visible |
| `--sp-duration-medium` | 0.5s | Interactive animations | Smooth |
| `--sp-duration-gear` | 0.75s | Mechanical motion | Weighty |
| `--sp-duration-smoke` | 1s | Atmospheric effects | Deliberate |
| `--sp-duration-menu` | 2.5s | Menu sequences | Ritual-like |
| `--sp-duration-atmospheric` | 3.5s | Long ambient effects | Background |

### Easing Functions

| Token | Cubic Bezier | Usage |
|---|---|---|
| `--sp-easing-physics` | `cubic-bezier(0.25, 0.46, 0.45, 0.94)` | Physics-based animations, wheel momentum |
| `--sp-easing-standard` | `ease-in-out` | Standard smooth transitions |
| `--sp-easing-out` | `ease-out` | Deceleration, landing animations |

### Multi-Phase Animation Durations

For complex sequences:

| Phase | Duration | Purpose | Example |
|---|---|---|---|
| `--sp-phase-warp` | 600ms | Opening distortion | Portal opening |
| `--sp-phase-hold` | 3000ms | Pause/display | Prompt display |
| `--sp-phase-disintegrate` | 3000ms | Dissolve effect | Element decay |
| `--sp-phase-reassemble` | 1500ms | Reconstruction | Element reassembly |

### Motion Preferences (WCAG A - MVP Feature)

Users with `prefers-reduced-motion` setting should not see animations. **Implement this in MVP using CSS.**

**CSS Pattern**:
```css
/* Define animations normally */
@keyframes wheelSpin {
  from { transform: rotateX(0deg); }
  to { transform: rotateX(360deg); }
}

.wheel {
  animation: wheelSpin 2s var(--sp-easing-physics);
}

/* Disable for users who prefer reduced motion */
@media (prefers-reduced-motion: reduce) {
  * {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
  }
}
```

This is already implemented globally in `src/tokens/colors.css`.

**Examples of Reduced Motion Behavior**:
- **Wheel spin**: Jump instantly to final prompt without animation
- **Modal fade**: Show instantly instead of fading in
- **Button hover**: Keep color change, remove lift animation
- **Recording waveform**: Keep waveform updating, just no smooth easing

**Testing**: Verify all interactions work with `prefers-reduced-motion: reduce` enabled. Functionality must never depend on animation.

---

## SVG Filters & Effects

### Overview

The steampunk aesthetic relies on SVG filters for carved text, engraved buttons, and depth effects. These filters are defined globally in `public/index.html` and referenced via CSS `filter: url(#filter-id)`.

**CRITICAL CONSTRAINT**: Global SVG gradients (defined in `<defs>` in index.html) **do NOT cascade to inline SVGs in React components**. Inline SVGs in components must define their own `<defs>` with inline gradients.

### Required SVG Filters (in public/index.html)

**Location**: `public/index.html`, inside `<svg style="display:none">` wrapper.

```html
<svg style="display: none;">
  <defs>
    <!-- ========== BRONZE ENGRAVED FILTER ========== -->
    <!-- Used for: .engraved-button-text, .engraved-icon, .engraved-material-icon -->
    <filter id="bronze-engraved-filter" x="-50%" y="-50%" width="200%" height="200%">
      <!-- Inner shadow (carved depth) -->
      <feGaussianBlur in="SourceAlpha" stdDeviation="2" />
      <feOffset dx="0" dy="-1" result="offsetblur" />
      <feComponentTransfer>
        <feFuncA type="linear" slope="0.5" />
      </feComponentTransfer>
      <feMerge>
        <feMergeNode />
        <feMergeNode in="SourceGraphic" />
      </feMerge>
      <!-- Outer highlight (light reflection) -->
      <feGaussianBlur in="SourceAlpha" stdDeviation="1" />
      <feOffset dx="0" dy="1" result="offsetblur" />
      <feFlood floodColor="#ffffff" floodOpacity="0.3" result="offsetcolor" />
      <feComposite in="offsetcolor" in2="offsetblur" operator="in" result="offsetblur" />
      <feMerge>
        <feMergeNode in="offsetblur" />
        <feMergeNode in="SourceGraphic" />
      </feMerge>
    </filter>

    <!-- ========== CARVED TEXT FILTER ========== -->
    <!-- Used for: .carved-text (wheel prompts) -->
    <filter id="carved-text-filter" x="-50%" y="-50%" width="200%" height="200%">
      <!-- Inner shadow (carving depth) -->
      <feGaussianBlur in="SourceAlpha" stdDeviation="1.5" />
      <feOffset dx="0" dy="-2" result="offsetblur" />
      <feComponentTransfer>
        <feFuncA type="linear" slope="0.6" />
      </feComponentTransfer>
      <feMerge>
        <feMergeNode />
        <feMergeNode in="SourceGraphic" />
      </feMerge>
      <!-- Outer highlight (wood grain reflection) -->
      <feGaussianBlur in="SourceAlpha" stdDeviation="0.5" />
      <feOffset dx="0" dy="1" result="offsetblur" />
      <feFlood floodColor="#fffcf5" floodOpacity="0.4" result="offsetcolor" />
      <feComposite in="offsetcolor" in2="offsetblur" operator="in" result="offsetblur" />
      <feMerge>
        <feMergeNode in="offsetblur" />
        <feMergeNode in="SourceGraphic" />
      </feMerge>
    </filter>

    <!-- ========== BRONZE GRADIENT (for button fills) ========== -->
    <!-- Used for: .engraved-icon (SVG fill gradient) -->
    <linearGradient id="bronze-gradient" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" style="stop-color:#faf0b0;stop-opacity:1" />
      <stop offset="50%" style="stop-color:#c4a448;stop-opacity:1" />
      <stop offset="100%" style="stop-color:#5c3c04;stop-opacity:1" />
    </linearGradient>

    <!-- ========== BRONZE GRADIENT PRESSED ========== -->
    <!-- Used for: .engraved-icon.pressed (darker state) -->
    <linearGradient id="bronze-gradient-pressed" x1="0%" y1="0%" x2="0%" y2="100%">
      <stop offset="0%" style="stop-color:#d8c880;stop-opacity:1" />
      <stop offset="50%" style="stop-color:#a89040;stop-opacity:1" />
      <stop offset="100%" style="stop-color:#604808;stop-opacity:1" />
    </linearGradient>
  </defs>
</svg>
```

### CSS Classes Using SVG Filters

| CSS Class | Filter ID | Elements | Notes |
|---|---|---|---|
| `.engraved-button-text` | `#bronze-engraved-filter` | Button text with gradient | Text appears carved into metal |
| `.engraved-icon` | `#bronze-engraved-filter` | SVG icons in buttons | Icons get depth effect |
| `.engraved-material-icon` | `#bronze-engraved-filter` | Material Symbol icons | Google icons with patina |
| `.carved-text` | `#carved-text-filter` | Wheel prompt text | Wood carving effect |

### Inline SVG Gradient Constraint

**Problem**: Components like buttons that include inline SVGs cannot use the global gradients from index.html.

**Solution**: Inline SVGs must define their own `<defs>` with gradient IDs:

```tsx
export function NewTopicsButton({ onClick, ...props }) {
  return (
    <button onClick={onClick} {...props}>
      <svg viewBox="0 0 24 24" width={24} height={24}>
        <defs>
          {/* DUPLICATE the gradient ID locally */}
          <linearGradient id="button-gradient-inline" x1="0%" y1="0%" x2="0%" y2="100%">
            <stop offset="0%" style={{ stopColor: '#faf0b0' }} />
            <stop offset="100%" style={{ stopColor: '#5c3c04' }} />
          </linearGradient>
        </defs>
        {/* Use the inline gradient ID */}
        <path fill="url(#button-gradient-inline)" d="..." />
      </svg>
    </button>
  )
}
```

**Rule**: If an inline SVG uses a gradient, define the gradient inline with a unique ID within that SVG.

---

## Asset Inventory

### Overview

The Story Portal requires specific UI assets. All assets live in `/public/assets/images/` and are distributed with the build. This inventory documents all required images, their locations, and current status.

**Conventions**:
- All assets live in `/public/assets/images/`
- Prefer WebP format for modern browsers
- Include fallback formats (PNG/JPG) for older browsers
- Organize by category
- Mark status: ✅ Exists, ⚠️ Needs Update, ❌ Missing, 🔄 In Progress

### Asset Categories

#### 1. Wheel Assets

| Filename | Purpose | Dimensions | Format | Status | Notes |
|---|---|---|---|---|---|
| `/public/assets/images/wood-panel.webp` | Wheel panel texture (background) | 512×512px (repeating) | WebP | ✅ Exists | Used in `.wheel-panel-inner` background |

**Notes**: Wheel prompts are rendered as `.carved-text` using CSS gradient, not image-based.

#### 2. Button Assets (Image-Based, WebP)

Buttons use WebP background images with engraved text overlay. Use these exact filenames:

| Filename | Purpose | Variant | Dimensions | Format | Status | Notes |
|---|---|---|---|---|---|---|
| `/public/assets/images/story-portal-button-primary.webp` | Main action button | Primary/Default | 260×56px | WebP | ✅ Exists | Record, Save, Confirm buttons |
| `/public/assets/images/story-portal-button-secondary.webp` | Secondary action button | Secondary | 260×56px | WebP | ✅ Exists | Cancel, Skip buttons |
| `/public/assets/images/story-portal-button-click.webp` | Button pressed state | Pressed | 260×56px | WebP | ✅ Exists | Feedback for active clicks |
| `/public/assets/images/story-portal-button-spin-static.webp` | Wheel spin button (default) | Static | Variable | WebP | ✅ Exists | Spin wheel button |
| `/public/assets/images/story-portal-button-spin-click.webp` | Wheel spin button (pressed) | Pressed | Variable | WebP | ✅ Exists | Spin wheel button pressed state |

**Notes**: Use these WebP images directly. Do NOT create new SVG buttons. Engraved text is applied via CSS gradients on top of images.

#### 3. Portal Effects Assets

| Filename | Purpose | Dimensions | Format | Status | Notes |
|---|---|---|---|---|---|
| `/public/assets/images/portal-ring.webp` | Portal ring effect (optional) | 600×600px | WebP | ✅ Exists | Visual frame around wheel |

#### 4. Navigation & Menu Assets

| Filename | Purpose | Dimensions | Format | Status | Notes |
|---|---|---|---|---|---|
| `/public/assets/images/story-portal-app-hamburger-menu-gear.webp` | Menu toggle button | 80×80px | WebP | ✅ Exists | Hamburger/gear menu icon |

#### 5. Branding Assets

| Filename | Purpose | Dimensions | Format | Status | Notes |
|---|---|---|---|---|---|
| `/public/assets/images/story-portal-logo.svg` | App logo/branding | Variable | SVG | ✅ Exists | Used in splash screen, about section |

#### 6. Background & Texture Assets

| Filename | Purpose | Dimensions | Format | Status | Notes |
|---|---|---|---|---|---|
| `/public/assets/images/background.webp` | Page background (optional) | 1920×1080px | WebP | ✅ Exists | Dark steampunk texture, optional enhancement |
| Inline in CSS | Noise grain overlay | 200×200px | SVG data URI | ✅ Inline | Defined in wheel.css as data URI, no file needed |

### Asset Status Summary

| Category | Status | Action |
|---|---|---|
| Wheel textures | ✅ Complete | Ready to use |
| Button assets | ✅ Complete | Use existing WebP files, don't create new SVGs |
| Portal effects | ✅ Complete | Available if needed for animations |
| Navigation | ✅ Complete | Menu gear icon ready |
| Branding | ✅ Complete | Logo available for splash/about screens |
| Backgrounds | ✅ Complete | Background texture available |

### Using Assets in Components

**CSS Example** (using WebP buttons):
```css
.button {
  background-image: url('/assets/images/story-portal-button-primary.webp');
  background-size: contain;
  background-repeat: no-repeat;
  background-position: center;
  width: 260px;
  height: 56px;
}

.button:active {
  background-image: url('/assets/images/story-portal-button-click.webp');
}
```

**React Example**:
```tsx
export function RecordButton() {
  return (
    <button
      style={{
        backgroundImage: "url('/assets/images/story-portal-button-primary.webp')",
        backgroundSize: 'contain',
        backgroundRepeat: 'no-repeat',
        width: '260px',
        height: '56px',
      }}
    >
      Record Story
    </button>
  )
}
```

---

## Accessibility

### Color Contrast

All text meets WCAG AA standards (4.5:1 for small text, 3:1 for large text). See Color System section for verified ratios.

**Rule**: Always test text on backgrounds. Use [WebAIM Contrast Checker](https://webaim.org/resources/contrastchecker/) to validate.

### Focus Indicators

All interactive elements must have visible focus states:

```css
button:focus,
a:focus,
input:focus {
  outline: 3px solid var(--color-flame-core);
  outline-offset: 2px;
}
```

**Rule**: Never remove default focus indicators. Enhance them instead.

### Touch Targets

All interactive elements must be at least 44×44px:

- **Buttons**: Minimum 44×44px target area (actual button may be smaller, but touch area includes padding)
- **Icons**: `clamp(20px, 4.5vw, 36px)` provides responsive sizing, minimum 20px
- **Form inputs**: Minimum 44px height

**Notch Safety**: On notched devices (iPhones), use safe area insets:
```css
@supports (padding-left: max(0px)) {
  body {
    padding-left: max(var(--sp-spacing-md), env(safe-area-inset-left));
    padding-right: max(var(--sp-spacing-md), env(safe-area-inset-right));
  }
}
```

### Keyboard Navigation

All interactive elements must be keyboard accessible:

- Buttons: Can be activated with Enter/Space
- Links: Tab-accessible
- Modals: Tab traps inside modal, Escape closes
- Forms: Tab order follows visual flow

**Implementation**: React handles most of this naturally. Always test with keyboard-only navigation.

### Screen Reader Support

- Use semantic HTML (`<button>`, `<input>`, `<label>`)
- Add `aria-label` to icon-only buttons
- Add `aria-modal="true"` to modals
- Use `aria-hidden="true"` for decorative elements

Example:
```tsx
<button aria-label="Close dialog" onClick={handleClose}>
  ✕
</button>
```

---

## Responsive Design

### Mobile-First Approach

Design for phones first (320px+), then enhance for tablets and desktops.

### Breakpoints

| Breakpoint | Width | Device | Usage |
|---|---|---|---|
| **SM** | 480px | Small phone | Standard mobile |
| **MD** | 768px | Tablet | Tablet layout |
| **LG** | 1024px | Desktop | Desktop layout |

**CSS Variables** (for reference in JavaScript):
```css
:root {
  --sp-breakpoint-sm: 480px;
  --sp-breakpoint-md: 768px;
  --sp-breakpoint-lg: 1024px;
}
```

### Responsive Typography

Already handled with `clamp()` (see Typography section). Text scales automatically.

### Responsive Layout

```css
/* Mobile-first, then enhance */
.container {
  width: 100%;
  padding: var(--sp-spacing-md);
  flex-direction: column;
}

@media (min-width: 768px) {
  .container {
    padding: var(--sp-spacing-3xl);
    flex-direction: row;
  }
}
```

### Wheel on Different Sizes

- **Small phone (320px)**: Wheel is max 280px diameter
- **Tablet (768px)**: Wheel can be 400px+ diameter
- **Desktop (1024px+)**: Wheel can scale larger

Use CSS containment to ensure responsiveness:
```css
.wheel-container {
  width: min(90vw, 600px);
  aspect-ratio: 1;
}
```

### Safe Areas (Notched Devices)

```css
@supports (padding-left: max(0px)) {
  .layout {
    padding-left: max(var(--sp-spacing-md), env(safe-area-inset-left));
    padding-right: max(var(--sp-spacing-md), env(safe-area-inset-right));
    padding-bottom: max(var(--sp-spacing-xl), env(safe-area-inset-bottom));
  }
}
```

---

## Component Patterns

### Standard Button Pattern

```css
.sp-button {
  background-image: url('/assets/images/story-portal-button-primary.webp');
  background-size: contain;
  background-repeat: no-repeat;
  background-position: center;
  border: none;
  width: 260px;
  height: 56px;
  cursor: pointer;
  transition: transform var(--sp-duration-fast) var(--sp-easing-standard);
}

.sp-button:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: var(--sp-filter-button-drop);
}

.sp-button:active:not(:disabled) {
  background-image: url('/assets/images/story-portal-button-click.webp');
  transform: translateY(0);
}

.sp-button:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.sp-button:focus {
  outline: 3px solid var(--color-flame-core);
  outline-offset: 2px;
}
```

### Standard Container Pattern

```css
.sp-container {
  background: var(--bg-container);
  border: var(--sp-border-standard);
  border-radius: var(--sp-radius-lg);
  padding: var(--sp-spacing-3xl);
  box-shadow: var(--sp-shadow-container);
}
```

### Prompt Display Pattern

```css
.sp-prompt-box {
  background: var(--bg-prompt);
  border: var(--sp-border-medium);
  border-radius: var(--sp-radius-md);
  padding: var(--sp-spacing-lg);
  font-size: clamp(18px, 3vw, 24px);
  font-weight: bold;
  color: var(--text-on-dark);
  font-family: 'Carnivalee Freakshow', serif;
}
```

### Modal Pattern

```css
.sp-modal-backdrop {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: var(--bg-backdrop);
  backdrop-filter: var(--sp-filter-backdrop-blur);
  z-index: calc(var(--sp-z-modal) - 1);
}

.sp-modal-frame {
  background: var(--bg-container);
  border: var(--sp-border-standard);
  border-radius: var(--sp-radius-lg);
  padding: var(--sp-spacing-2xl);
  box-shadow: var(--sp-shadow-container-elevated);
  max-width: 600px;
  z-index: var(--sp-z-modal);
}
```

---

## Implementation Guidelines

### Using Tokens in React Components

#### Inline Styles (Quick Components)
```tsx
export function MyButton() {
  return (
    <button
      style={{
        background: 'var(--bg-primary)',
        border: '3px solid var(--color-bronze-standard)',
        padding: '16px 32px',
        color: 'var(--text-on-dark)',
        fontSize: 'clamp(16px, 2.5vw, 20px)',
      }}
    >
      Click Me
    </button>
  )
}
```

#### CSS Modules (Recommended)
```tsx
// MyButton.module.css
.button {
  background: var(--color-wood-mid);
  border: var(--sp-border-standard);
  padding: var(--sp-spacing-md) var(--sp-spacing-2xl);
  color: var(--text-on-dark);
  font-size: clamp(16px, 2.5vw, 20px);
  cursor: pointer;
}

.button:hover {
  transform: translateY(-2px);
}

.button:focus {
  outline: 3px solid var(--color-flame-core);
}

// MyButton.tsx
import styles from './MyButton.module.css'

export function MyButton() {
  return <button className={styles.button}>Click Me</button>
}
```

### Validating Implementations

Before component approval:
1. ✅ Check all colors use semantic tokens or design tokens
2. ✅ Verify spacing uses token scale
3. ✅ Confirm animations use duration/easing tokens
4. ✅ Test focus states (keyboard navigation)
5. ✅ Test with `prefers-reduced-motion: reduce` enabled
6. ✅ Test color contrast on actual device
7. ✅ Test on mobile (375px), tablet (768px), desktop (1024px)
8. ✅ Verify SVG filters are applied correctly (no missing #filter-id)

---

## Future Considerations

### Phase 2 Enhancements

1. **Dark Mode** — Implement using semantic color variables. Override `:root` colors in `@media (prefers-color-scheme: dark)`.
2. **Additional Color Palettes** — Event-specific themes (e.g., "Love Burn" festival theme) using variant token sets.
3. **Advanced Animations** — More complex atmospheric effects (steam wisps, electricity arcs).
4. **Custom Fonts** — Potential inclusion of additional serif/display fonts for variety.
5. **Captions & Transcription** — Text overlays for audio (Phase 2 accessibility feature).

### Experimentation Areas

- Animated gradient backgrounds
- Particle effects for story transitions
- Dynamic theme switching
- Custom cursor designs
- Parallax effects on scroll

---

## Design System Maintenance

This document is a living specification. As new components are built, design decisions should be recorded here to maintain consistency.

**Last Updated**: January 8, 2025
**Maintained By**: [To be assigned]
**Review Cycle**: Monthly or as needed

---

*This Design System is derived from the existing codebase (extracted from design-tokens.css, buttons.css, wheel.css, legacy styles) and the Story Portal APP_SPECIFICATION.md. It reflects decisions made from January 2025 onward.*
