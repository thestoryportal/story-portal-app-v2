# Steam Modal Component - Formal Specification

## Document Type: Technical Specification
**Authority Level**: 10 (Primary source of truth)
**Created**: 2026-01-20
**Status**: Active

## Overview
This document defines the complete and authoritative specification for the Steam Modal component based on user requirements.

---

## 1. Color Specifications

### 1.1 Steam Color
- **Primary Steam Color**: #C5B389
- **Usage**: This color represents the MOST DENSE steam
- **Implementation**: rgba(197, 179, 137, X) where X is opacity
- **Requirement**: The steam at highest density/percentage uses this exact color

### 1.2 Text Color
- **Text Color**: #433722
- **Usage**: All body text, headings, and content
- **Case**: Regular case (NOT uppercase, NOT all caps)
- **Implementation**: Standard sentence case for readability

---

## 2. Animation Sequence - Steam Formation

### 2.1 Initial State (0ms)
- Screen is clear/empty
- No steam visible
- Content is NOT visible

### 2.2 Phase 1: Steam Begins Seeping (0-800ms)
- **Behavior**: Steam begins forming at LOW density
- **Source**: Seeps QUICKLY from the CENTER of the portal ring/wheel
- **Density**: Starts minimal, builds rapidly
- **Visual**: Small wisps emerging from center point

### 2.3 Phase 2: Density Builds (800-2500ms)
- **Behavior**: Steam continues seeping from center
- **Density**: Rapidly increases as more steam emits
- **Coverage**: Expands outward from center
- **Goal**: Build up enough density to fill content area

### 2.4 Phase 3: Full Density Reached (2500-3500ms)
- **Behavior**: Steam reaches maximum density
- **Color**: Peak #C5B389 concentration in content area
- **Coverage**: Content area is completely filled with dense steam
- **Visual**: Opaque steam cloud where content will sit

### 2.5 Phase 4: Clearing Begins (3500-5500ms)
- **CRITICAL**: Content is positioned BEHIND the steam
- **Behavior**: Steam IN FRONT of content begins to clear/dissipate
- **Mechanism**: Steam drifts away, thins out, reveals what's beneath
- **Visual**: Content is gradually REVEALED as steam clears
- **Result**: Content becomes visible as steam obscuring it disappears

### 2.6 Final State (5500ms+)
- Content is fully visible and readable
- Background steam remains at medium density
- Constant organic drift and movement continues

---

## 3. Content Reveal Mechanism

### 3.1 Critical Distinction
**INCORRECT**: Content fades in on top of steam (opacity animation)
**CORRECT**: Content exists, steam clears away to reveal it

### 3.2 Implementation Requirements
1. Content must be positioned in the DOM with full opacity from start
2. Steam layer must be positioned IN FRONT of content (higher z-index)
3. Steam layer must animate from opaque → transparent
4. Effect must create visual of "clearing mist revealing what's beneath"

---

## 4. Steam Visual Characteristics

### 4.1 Organic Movement
- **Randomness**: HIGH - not predictable patterns
- **Chaos**: Lots of irregular, asymmetric movement
- **Wispiness**: Thin, floating, ethereal tendrils
- **NOT**: Simple swaying left-right motion
- **NOT**: Generic circular gradients that just fade in

### 4.2 Movement Qualities
- Multiple independent wisp elements
- Each wisp moves on different trajectory
- Varying speeds (some fast, some slow)
- Turbulent, unpredictable paths
- Creates sense of atmospheric depth

### 4.3 Density Variation
- Not uniform across the field
- Pockets of higher/lower density
- Constantly shifting patterns
- Natural, organic clustering

---

## 5. Scroll Behavior - Content Boundaries

### 5.1 Current Problem
- Top edge: Hard boundary line when scrolling
- Bottom edge: Hard boundary line when scrolling

### 5.2 Required Solution
**Top Boundary**:
- Gradiated steam opacity (NOT hard edge)
- Content appears to fade INTO steam cloud as it scrolls up
- Smooth transition from visible → obscured by steam
- Opacity gradient: transparent → dense steam (#C5B389)

**Bottom Boundary**:
- Gradiated steam opacity (NOT hard edge)
- Content appears to fade INTO steam cloud as it scrolls down
- Smooth transition from visible → obscured by steam
- Opacity gradient: transparent → dense steam (#C5B389)

### 5.3 Visual Effect
- Content should appear to be scrolling THROUGH a steam cloud
- Top/bottom of content area has soft steam "curtains"
- No visible rectangular boundaries or boxes
- Organic, atmospheric boundaries

---

## 6. Prohibited Elements (Must Be Removed)

### 6.1 Brass Visual Elements
- ❌ NO brass divider lines between content blocks
- ❌ NO brass outlines around any element
- ❌ NO brass borders on panels, headers, or content areas
- ❌ NO brass decorative elements of any kind

### 6.2 Rationale
- Brass conflicts with atmospheric steam aesthetic
- Hard metallic lines break immersion
- Steam should be the primary visual element

---

## 7. Technical Implementation Notes

### 7.1 Z-Index Layering (Front to Back)
1. Clearing steam layer (highest z-index) - starts opaque, clears away
2. Content layer - always at full opacity
3. Background steam layers - various densities for depth
4. Backdrop - darkened background

### 7.2 Color Consistency
- ALL steam uses variations of #C5B389
- Darker/lighter through opacity only
- Do not mix other color bases

### 7.3 Animation Timing
- Steam formation: 0-3500ms (seep and build)
- Steam clearing: 3500-5500ms (reveal content)
- Total to content visible: ~5.5 seconds
- Continuous drift: ongoing after reveal

---

## 8. Validation Checklist

Implementation is correct ONLY when ALL of these are true:

- [ ] Steam color is #C5B389 at highest density
- [ ] Text color is #433722 in regular case
- [ ] Steam seeps from center point, building density
- [ ] Content is revealed BY CLEARING STEAM (not fade-in)
- [ ] Steam has high randomness and organic chaos
- [ ] Scroll boundaries are soft steam gradients (not hard edges)
- [ ] Zero brass dividers or outlines anywhere
- [ ] Steam formation animation is rapid and visible
- [ ] Content appears "behind" steam that clears away

---

## 9. User Acceptance Criteria

The user will accept the implementation when:
1. Visual matches description in sections 1-6
2. Animation sequence follows section 2 exactly
3. Content reveal uses clearing mechanism (section 3)
4. No prohibited elements present (section 6)

## 10. Current Implementation Gaps (2026-01-20)

Based on user feedback, current implementation fails:
1. Steam color wrong/too dark
2. Steam appears suddenly (not seeping from center)
3. Content fades in (not revealed by clearing steam)
4. Hard scroll edges (not soft steam boundaries)
5. Generic animation (not organic/chaotic enough)
6. Brass elements still present

These gaps MUST be addressed before implementation is acceptable.
