#!/usr/bin/env node
/**
 * Animation Domain Prompts Library v1.0
 *
 * Rich animation-specific knowledge for injecting into agent prompts.
 * Provides deep domain expertise that general-purpose LLMs lack.
 *
 * Usage:
 *   import { getAnimationPrinciples, getCanvasAPIKnowledge, getCommonPitfalls } from './animation-domain-prompts.mjs'
 *
 * Categories:
 * - Animation Principles (timing, spacing, visual weight)
 * - Canvas 2D API Best Practices
 * - Common Pitfalls and Solutions
 * - Performance Optimization Patterns
 * - Color Theory for Digital Effects
 */

/**
 * Core Animation Principles
 */
export const ANIMATION_PRINCIPLES = `
## 🎬 Core Animation Principles

### Timing and Spacing
- **Fast actions**: 3-5 frames (impacts, flashes, sudden movements)
- **Slow actions**: 12-20 frames (glows, fades, smooth transitions)
- **Easing functions**: Use ease-in-out for natural motion (avoid linear)
  - Accelerating actions: ease-in
  - Decelerating actions: ease-out
  - Breathing/pulsing: ease-in-out (sine curve)

### Visual Weight and Balance
- **Bright elements draw attention** - Distribute evenly for balance
- **Radial symmetry creates stability** - Use for centered energy sources
- **Odd numbers create tension** - Avoid for bolts/elements (3, 5, 7 look unbalanced)
- **Even numbers feel stable** - Prefer 4, 6, 8, 12 for radial patterns

### The 12 Principles Applied to VFX
1. **Squash and Stretch**: Lightning can compress/extend
2. **Anticipation**: Build-up before discharge
3. **Staging**: Clear silhouette, readable at glance
4. **Follow Through**: Energy dissipates, doesn't stop instantly
5. **Timing**: Faster = more energy, slower = more weight
6. **Exaggeration**: Real lightning is boring, amplify for effect
7. **Solid Drawing**: Even 2D needs volume (glows have depth)
8. **Appeal**: Make it satisfying to watch

### Color and Brightness Hierarchy
- **Human eye sensitivity**: Most sensitive to yellow-green (555nm)
- **Brightness hierarchy**: Core > Inner Glow > Outer Glow > Background
- **Glow gradient**: ALWAYS brighter at center, fade to edges
- **Color temperature**:
  - Warm (yellow/orange) = energy, heat, power
  - Cool (blue/white) = electric, clean, technical
  - Never use pure white (looks blown out) - use warm white (255,255,230)

### Temporal Dynamics
- **Variation prevents monotony**: Don't repeat exact same frame
- **Slight randomness**: 5-10% variation in bolt positions per frame
- **Synchronized rhythm**: If multiple elements pulse, sync or deliberately offset
- **Frame rate**: Target 20-30 fps for effects (60fps wastes performance)
`.trim()

/**
 * Canvas 2D API - Animation Patterns
 */
export const CANVAS_API_KNOWLEDGE = `
## 🎨 Canvas 2D API - Animation Best Practices

### Creating Realistic Glows

#### ✅ GOOD - Layered Approach
\`\`\`javascript
// Multiple shadow layers create realistic glow
ctx.shadowBlur = 20
ctx.shadowColor = 'rgba(255,220,100,1)'
ctx.fillStyle = 'rgba(255,255,200,0.8)'
ctx.beginPath()
ctx.arc(x, y, 5, 0, Math.PI * 2)
ctx.fill()

// Add outer layer
ctx.shadowBlur = 50
ctx.shadowColor = 'rgba(255,200,50,0.4)'
ctx.arc(x, y, 20, 0, Math.PI * 2)
ctx.fill()
\`\`\`

#### ❌ BAD - Single Large Blur
\`\`\`javascript
// Looks fake, lacks depth
ctx.shadowBlur = 100
ctx.fillStyle = 'yellow'
ctx.arc(x, y, 10, 0, Math.PI * 2)
ctx.fill()
\`\`\`

### Lightning Bolt Paths

#### ✅ GOOD - Segmented with Variation
\`\`\`javascript
// Natural lightning has jagged segments
const segments = 10
for (let i = 0; i < segments; i++) {
  const offset = (Math.random() - 0.5) * amplitude
  ctx.quadraticCurveTo(
    prevX + offset, prevY,
    nextX, nextY
  )
}
\`\`\`

#### ❌ BAD - Straight Lines
\`\`\`javascript
// Looks robotic, lifeless
ctx.lineTo(endX, endY)
\`\`\`

### Blend Modes for Energy Effects

#### ✅ GOOD - Additive Blending
\`\`\`javascript
// Glows combine realistically
ctx.globalCompositeOperation = 'lighter'
// Draw all glows with lighter mode
// Overlapping glows intensify (additive)
\`\`\`

#### ❌ BAD - Normal Blending
\`\`\`javascript
// Glows occlude each other
ctx.globalCompositeOperation = 'source-over'
// Overlapping glows look muddy
\`\`\`

### Transparency and Alpha

#### ✅ GOOD - Premultiplied Alpha
\`\`\`javascript
// When layering multiple transparent elements
const alpha = 0.5
const r = 255 * alpha
const g = 220 * alpha
const b = 100 * alpha
ctx.fillStyle = \`rgba(\${r}, \${g}, \${b}, 1)\`
\`\`\`

#### ❌ BAD - Stacked Alpha
\`\`\`javascript
// Alpha compounds incorrectly
ctx.globalAlpha = 0.5
ctx.fillStyle = 'rgba(255,220,100,0.5)'
// Effective alpha = 0.5 * 0.5 = 0.25 (too dim)
\`\`\`

### Performance Patterns

#### ✅ GOOD - Batch Draw Calls
\`\`\`javascript
// One path for multiple bolts
ctx.beginPath()
bolts.forEach(bolt => {
  ctx.moveTo(bolt.startX, bolt.startY)
  ctx.lineTo(bolt.endX, bolt.endY)
})
ctx.stroke() // Single draw call
\`\`\`

#### ❌ BAD - Individual Draw Calls
\`\`\`javascript
bolts.forEach(bolt => {
  ctx.beginPath()
  ctx.moveTo(bolt.startX, bolt.startY)
  ctx.lineTo(bolt.endX, bolt.endY)
  ctx.stroke() // N draw calls for N bolts
})
\`\`\`

### Canvas State Management

#### ✅ GOOD - Save/Restore Pattern
\`\`\`javascript
ctx.save()
ctx.translate(centerX, centerY)
ctx.rotate(angle)
// Draw transformed content
ctx.restore() // Returns to clean state
\`\`\`

#### ❌ BAD - Manual Undo
\`\`\`javascript
// Easy to forget, causes cumulative errors
ctx.translate(centerX, centerY)
// Draw
ctx.translate(-centerX, -centerY) // Error-prone
\`\`\`
`.trim()

/**
 * Common Pitfalls and Solutions
 */
export const COMMON_PITFALLS = `
## ⚠️ Common Animation Mistakes and Fixes

### Mistake 1: Bolts Disappear at Edges
**Symptom**: Lightning cuts off at canvas boundary
**Cause**: Drawing outside canvas bounds
**Solution**: Clamp coordinates or extend canvas
\`\`\`javascript
const x = Math.max(0, Math.min(canvasWidth, targetX))
const y = Math.max(0, Math.min(canvasHeight, targetY))
\`\`\`

### Mistake 2: Animation Flickers/Stutters
**Symptom**: Visible flashing between frames
**Cause**: Not clearing canvas before redraw
**Solution**: Always clear first
\`\`\`javascript
// FIRST LINE of every frame
ctx.clearRect(0, 0, canvas.width, canvas.height)
\`\`\`

### Mistake 3: Colors Look Washed Out
**Symptom**: Glows appear pale, lack vibrancy
**Cause**: Multiple alpha layers compound incorrectly
**Solution**: Use 'lighter' blend mode OR premultiply alpha
\`\`\`javascript
ctx.globalCompositeOperation = 'lighter'
// Now overlapping glows intensify instead of washing out
\`\`\`

### Mistake 4: Animation is Jittery
**Symptom**: Motion isn't smooth, stutters
**Cause**: Not using consistent time delta
**Solution**: requestAnimationFrame with deltaTime
\`\`\`javascript
let lastTime = 0
function animate(currentTime) {
  const deltaTime = currentTime - lastTime
  lastTime = currentTime

  // Use deltaTime for frame-rate-independent animation
  position += velocity * (deltaTime / 1000)

  requestAnimationFrame(animate)
}
\`\`\`

### Mistake 5: Glow Looks Fake/Uniform
**Symptom**: Glow is flat, no depth perception
**Cause**: Single shadow layer or uniform opacity
**Solution**: Multi-layer glow with varying intensities
\`\`\`javascript
// Bright core
drawGlowLayer(5, 1.0, 15)
// Medium inner glow
drawGlowLayer(20, 0.5, 30)
// Soft outer glow
drawGlowLayer(50, 0.2, 60)
\`\`\`

### Mistake 6: Bolts Don't Look Electric
**Symptom**: Lightning looks like straight lines
**Cause**: No variation, no branching, no jaggedness
**Solution**: Add procedural variation
\`\`\`javascript
// Jitter each segment slightly
const jitter = (Math.random() - 0.5) * 10
const x = baseX + jitter
\`\`\`

### Mistake 7: Performance Degrades Over Time
**Symptom**: Starts smooth, becomes laggy
**Cause**: Creating new objects every frame (memory leak)
**Solution**: Object pooling or reuse
\`\`\`javascript
// BAD: Creates new array every frame
const bolts = []
for (let i = 0; i < count; i++) {
  bolts.push(new Bolt())
}

// GOOD: Reuse existing objects
bolts.forEach(bolt => bolt.update())
\`\`\`

### Mistake 8: Radial Pattern Looks Lopsided
**Symptom**: Uneven distribution of bolts
**Cause**: Using odd numbers or forgetting to normalize angles
**Solution**: Even count with calculated angle steps
\`\`\`javascript
const boltCount = 8 // EVEN number
const angleStep = (Math.PI * 2) / boltCount
for (let i = 0; i < boltCount; i++) {
  const angle = i * angleStep
  // Perfect even distribution
}
\`\`\`
`.trim()

/**
 * Performance Optimization Patterns
 */
export const PERFORMANCE_PATTERNS = `
## ⚡ Performance Optimization Patterns

### Performance Budget
- **Target**: 60fps (16.67ms per frame)
- **Animation budget**: 8-10ms (leave headroom for browser)
- **Measure**: Use Performance API to profile

### Optimization Techniques

#### 1. Minimize Draw Calls
\`\`\`javascript
// Batch similar operations
ctx.beginPath()
elements.forEach(el => {
  ctx.moveTo(el.x1, el.y1)
  ctx.lineTo(el.x2, el.y2)
})
ctx.stroke() // One call instead of N
\`\`\`

#### 2. Cache Static Elements
\`\`\`javascript
// Pre-render unchanging parts to offscreen canvas
const cachedBg = document.createElement('canvas')
const cachectx = cachedBg.getContext('2d')
renderBackground(cachectx) // Once

// Every frame: just copy cached version
ctx.drawImage(cachedBg, 0, 0)
\`\`\`

#### 3. Reduce Shadow Blur Radius
\`\`\`javascript
// Shadow blur is expensive
// Use smallest blur that looks good
ctx.shadowBlur = 20 // Acceptable
// NOT
ctx.shadowBlur = 200 // Way too expensive
\`\`\`

#### 4. Avoid Setting Same State Repeatedly
\`\`\`javascript
// BAD: Setting fillStyle every iteration
for (const bolt of bolts) {
  ctx.fillStyle = 'yellow' // Wasteful
  ctx.fill()
}

// GOOD: Set once
ctx.fillStyle = 'yellow'
for (const bolt of bolts) {
  ctx.fill()
}
\`\`\`

#### 5. Use Integer Pixel Coordinates
\`\`\`javascript
// Fractional pixels force anti-aliasing
const x = Math.round(calculatedX)
const y = Math.round(calculatedY)
// Renders faster and crisper
\`\`\`

#### 6. Limit Particle Count
\`\`\`javascript
// More isn't always better
const MAX_PARTICLES = 100 // Reasonable limit
if (particles.length > MAX_PARTICLES) {
  particles = particles.slice(0, MAX_PARTICLES)
}
\`\`\`
`.trim()

/**
 * Color Theory for Digital Effects
 */
export const COLOR_THEORY = `
## 🎨 Color Theory for Digital Effects

### Color Temperature
- **Warm colors** (red/orange/yellow): Energy, heat, aggression
  - Lightning: Yellow-white (255, 255, 230)
  - Fire: Orange-yellow (255, 200, 100)

- **Cool colors** (blue/cyan/white): Technology, ice, calm
  - Electric: Blue-white (200, 230, 255)
  - Frost: Cyan (150, 230, 255)

### Luminance Hierarchy
1. **Core/Hotspot**: 90-100% brightness (nearly white)
2. **Inner Glow**: 70-80% brightness (vibrant color)
3. **Outer Glow**: 40-50% brightness (faded)
4. **Background**: 10-20% brightness (subtle)

### Color Harmony for Glows
- **Monochromatic**: Single hue, vary lightness
  - Core: HSL(45°, 100%, 90%)
  - Inner: HSL(45°, 90%, 70%)
  - Outer: HSL(45°, 70%, 40%)

- **Analogous**: Adjacent hues (warm spectrum)
  - Core: Yellow (45°)
  - Inner: Yellow-orange (35°)
  - Outer: Orange (25°)

### Avoiding Common Color Mistakes
- **Pure white (255,255,255)**: Looks blown out, use warm white (255,255,230)
- **Pure black (0,0,0)**: Too dark, use near-black (15,15,20)
- **Oversaturation**: Real energy isn't neon, use 80-90% saturation
- **Muddy overlaps**: Use additive blending to preserve vibrancy

### Color Space Conversions
\`\`\`javascript
// RGB to HSL (useful for hue shifts)
function rgbToHsl(r, g, b) {
  r /= 255; g /= 255; b /= 255
  const max = Math.max(r, g, b)
  const min = Math.min(r, g, b)
  let h, s, l = (max + min) / 2

  if (max === min) {
    h = s = 0 // achromatic
  } else {
    const d = max - min
    s = l > 0.5 ? d / (2 - max - min) : d / (max + min)
    switch (max) {
      case r: h = ((g - b) / d + (g < b ? 6 : 0)) / 6; break
      case g: h = ((b - r) / d + 2) / 6; break
      case b: h = ((r - g) / d + 4) / 6; break
    }
  }

  return [h * 360, s * 100, l * 100]
}
\`\`\`
`.trim()

/**
 * Get prompt knowledge by agent type
 */
export function getKnowledgeForAgent(agentType) {
  const knowledgeSets = {
    'animation-expert': [
      ANIMATION_PRINCIPLES,
      CANVAS_API_KNOWLEDGE,
      COMMON_PITFALLS,
      PERFORMANCE_PATTERNS,
      COLOR_THEORY
    ],
    'diff-analyst': [
      ANIMATION_PRINCIPLES,
      COLOR_THEORY
    ],
    'bolt-specialist': [
      CANVAS_API_KNOWLEDGE,
      PERFORMANCE_PATTERNS,
      `### Lightning-Specific Patterns
- Radial distribution with even counts (8, 12, 16)
- Jagged segments with 10-20% amplitude variation
- Tapering thickness (thicker at base, thinner at tip)
- Slight rotation offset per frame (5-10°)`
    ],
    'glow-specialist': [
      CANVAS_API_KNOWLEDGE,
      COLOR_THEORY,
      `### Glow-Specific Patterns
- Multi-layer composition (3-5 layers)
- Exponential falloff (center bright, edges soft)
- Additive blending for realistic overlap
- Pulsing: sine wave with 0.1-0.3 amplitude`
    ],
    'color-specialist': [
      COLOR_THEORY,
      `### Color Matching Strategies
- Use HSL for perceptual color matching
- Match luminance first, then hue, then saturation
- Allow 5° hue tolerance, 10% lightness tolerance
- Warm colors advance, cool colors recede`
    ],
    'timing-specialist': [
      ANIMATION_PRINCIPLES,
      `### Timing-Specific Patterns
- Easing function library: ease-in, ease-out, ease-in-out
- Pulse frequency: 2-5 Hz for energy effects
- Frame-to-frame delta: 5-15% for smooth motion
- Avoid linear timing (looks robotic)`
    ]
  }

  return knowledgeSets[agentType] || knowledgeSets['animation-expert']
}

/**
 * Format knowledge for prompt injection
 */
export function formatForPrompt(agentType = 'animation-expert') {
  const knowledge = getKnowledgeForAgent(agentType)

  return `
# 📚 ANIMATION DOMAIN KNOWLEDGE

The following is specialized knowledge about animation, Canvas API, and visual effects.
Study this carefully and apply these principles in your work.

${knowledge.join('\n\n---\n\n')}

---

**Remember**: This knowledge is crucial for creating professional-quality animations.
Reference these principles when making decisions about parameters and code structure.
`.trim()
}

export default {
  ANIMATION_PRINCIPLES,
  CANVAS_API_KNOWLEDGE,
  COMMON_PITFALLS,
  PERFORMANCE_PATTERNS,
  COLOR_THEORY,
  getKnowledgeForAgent,
  formatForPrompt
}
