# HANDOFF: Upgrade Steam Animation v35 → v31 with AAA Enhancements

## Context

You are upgrading an existing steam animation React component from v35 to v31. The user has provided:

1. **steam-animation-v35.jsx** - Current implementation (4-layer canvas, particle system, phase-based reveal)
2. **steam-animation-assessment.md** - Technical analysis identifying 8 critical visual limitations and upgrade paths
3. **steam-texture-creation-guide.md** - Instructions for creating steam texture sprites
4. **action-plan-checklist.md** - Week-by-week implementation plan

## Your Mission

Implement the "Enhanced Canvas 2D" approach (Option A from assessment) to achieve 75-80% AAA visual quality while maintaining the existing React + Canvas 2D + Tailwind architecture.

## Critical Success Factors

✅ **Preserve existing architecture**: Keep the 4-layer canvas system, phase-based animation, React hooks pattern  
✅ **Maintain performance**: Target 60fps desktop, 45+ fps mobile  
✅ **Additive changes only**: Don't rebuild from scratch - enhance what exists  
✅ **Keep v35 working**: User may want to compare v35 vs v31  

## Core Enhancements to Implement

Based on the assessment document, implement these 7 key improvements:

### 1. Add Texture-Based Particle Rendering
**Current (v35)**: Simple radial gradients via `createRadialGradient()`  
**Enhanced (v31)**: PNG texture sprites with alpha channel

**Changes needed**:
- Add texture loading system in `useEffect`
- Create fallback procedural textures (if real textures not provided)
- Replace gradient rendering with `ctx.drawImage()`
- Add `textureIndex` property to particles

### 2. Implement Perlin Noise Flow Fields
**Current (v35)**: `getWaft()` function using sine/cosine  
**Enhanced (v31)**: Perlin noise-driven turbulent flow

**Changes needed**:
- Add `simplex-noise` library (npm install required)
- Create noise field in `useRef`
- Replace `getWaft()` calls with noise flow sampling
- Apply noise-based velocity updates

### 3. Add Particle Rotation
**Current (v35)**: No rotation  
**Enhanced (v31)**: Particles spin naturally as they rise

**Changes needed**:
- Add `rotation` and `rotationSpeed` to particle properties
- Use `ctx.save()` / `ctx.translate()` / `ctx.rotate()` / `ctx.restore()` in render
- Update rotation in animation loop

### 4. Implement Scale Evolution
**Current (v35)**: Static particle size  
**Enhanced (v31)**: Particles grow/shrink over lifetime

**Changes needed**:
- Add `scaleStart`, `scaleEnd`, `currentScale` to particles
- Interpolate scale based on `age / maxAge`
- Apply scale when rendering

### 5. Add Multi-Layer Depth System
**Current (v35)**: All particles at same visual depth  
**Enhanced (v31)**: Particles sorted by depth, rendered with depth-based blur

**Changes needed**:
- Add `depth` property (0-1) to particles
- Sort particles by depth before rendering
- Apply `ctx.filter = blur()` based on depth
- Add parallax to movement (depth affects flow strength)

### 6. Implement Glow Pass for Light Scattering
**Current (v35)**: No atmospheric effects  
**Enhanced (v31)**: Soft glow around denser steam areas

**Changes needed**:
- Add second render pass after main particles
- Use `ctx.filter = 'blur(20px)'`
- Render semi-transparent halos at particle positions
- Use `'screen'` composite mode

### 7. Add Object Pooling for Performance
**Current (v35)**: Create/destroy particles on demand  
**Enhanced (v31)**: Reuse particle objects from pool

**Changes needed**:
- Create particle pool in `useRef`
- Add `acquireParticle()` and `releaseParticle()` functions
- Replace all `createParticle()` calls with pool acquisition
- Return particles to pool when they die

## Step-by-Step Implementation Guide

### Phase 1: Setup Dependencies & Textures (Do First)

**Step 1.1: Add simplex-noise dependency**
```javascript
// At top of file, add import
import SimplexNoise from 'simplex-noise';

// In component, create noise ref
const noiseRef = useRef(null);

// In useEffect initialization
useEffect(() => {
  noiseRef.current = new SimplexNoise();
}, []);
```

**Step 1.2: Add texture loading system**
```javascript
const texturesRef = useRef([]);
const texturesLoadedRef = useRef(false);

useEffect(() => {
  // Try to load real textures first
  const textureUrls = [
    '/assets/steam/wispy-01.png',
    '/assets/steam/wispy-02.png',
    '/assets/steam/cloud-01.png',
    '/assets/steam/cloud-02.png',
    '/assets/steam/swirl-01.png',
    '/assets/steam/mist-01.png',
  ];

  let loadedCount = 0;
  const textures = [];

  textureUrls.forEach((url, idx) => {
    const img = new Image();
    img.onload = () => {
      loadedCount++;
      textures[idx] = img;
      if (loadedCount === textureUrls.length) {
        texturesRef.current = textures;
        texturesLoadedRef.current = true;
      }
    };
    img.onerror = () => {
      // Create fallback procedural texture
      console.warn(`Texture ${url} failed, using fallback`);
      loadedCount++;
      textures[idx] = createFallbackTexture(idx);
      if (loadedCount === textureUrls.length) {
        texturesRef.current = textures;
        texturesLoadedRef.current = true;
      }
    };
    img.src = url;
  });
}, []);

// Add fallback texture generator
const createFallbackTexture = useCallback((type) => {
  const canvas = document.createElement('canvas');
  canvas.width = 512;
  canvas.height = 512;
  const ctx = canvas.getContext('2d');
  
  // Create procedural smoke-like pattern
  const centerX = 256;
  const centerY = 256;
  
  for (let i = 0; i < 150; i++) {
    const angle = Math.random() * Math.PI * 2;
    const dist = Math.random() * 200;
    const x = centerX + Math.cos(angle) * dist;
    const y = centerY + Math.sin(angle) * dist;
    const size = 20 + Math.random() * 40;
    const alpha = Math.random() * 0.3;
    
    const gradient = ctx.createRadialGradient(x, y, 0, x, y, size);
    gradient.addColorStop(0, `rgba(220, 200, 180, ${alpha})`);
    gradient.addColorStop(1, 'rgba(220, 200, 180, 0)');
    
    ctx.fillStyle = gradient;
    ctx.fillRect(x - size, y - size, size * 2, size * 2);
  }
  
  // Blur for organic look
  ctx.filter = 'blur(16px)';
  ctx.drawImage(canvas, 0, 0);
  ctx.filter = 'none';
  
  return canvas;
}, []);
```

### Phase 2: Enhance Particle Properties

**Step 2.1: Update all createParticle functions**

Find these functions in v35:
- `createBaseParticle`
- `createOuterParticle`
- `createEdgeParticle`
- `createCoverParticle`

Add these properties to EACH:
```javascript
// Add to each particle creation
return {
  // ... existing properties ...
  
  // NEW: Rotation
  rotation: Math.random() * Math.PI * 2,
  rotationSpeed: (Math.random() - 0.5) * 0.02, // Adjust per particle type
  
  // NEW: Scale evolution
  scaleStart: 0.7 + Math.random() * 0.3,
  scaleEnd: 1.2 + Math.random() * 0.4,
  currentScale: 1,
  
  // NEW: Depth
  depth: Math.random(), // 0 = far, 1 = near
  
  // NEW: Texture
  textureIndex: Math.floor(Math.random() * 6), // 0-5 for 6 textures
  
  // NEW: For flow
  vx: 0,
  vy: 0,
};
```

**Adjust rotation speeds per particle type**:
- Base particles: `0.01` (slow)
- Outer particles: `0.025` (faster)
- Edge particles: `0.01` (slow)
- Cover particles: `0.03` (fastest)

### Phase 3: Replace Movement System

**Step 3.1: Create noise flow function**
```javascript
const getNoiseFlow = useCallback((x, y, time) => {
  if (!noiseRef.current) return { x: 0, y: 0 };
  
  const scale = 0.003; // Noise frequency
  const timeScale = 0.0001;
  const t = time * timeScale;
  const noise = noiseRef.current;
  
  return {
    x: noise.noise3D(x * scale, y * scale, t) * 8,
    y: noise.noise3D(x * scale + 1000, y * scale, t) * 8 - 0.5 // Slight upward bias
  };
}, []);
```

**Step 3.2: Replace waft calls in animation loop**

Find everywhere `getWaft()` is called, replace with:
```javascript
// OLD v35:
// const waft = getWaft(particle.seed, time);
// particle.x += waft.x * waftStrength;
// particle.y += waft.y * waftStrength;

// NEW v31:
const flow = getNoiseFlow(particle.x, particle.y, time);
const parallax = 0.5 + particle.depth * 0.5; // Depth affects movement
particle.vx = flow.x * parallax * 0.1;
particle.vy = flow.y * parallax * 0.1;
particle.x += particle.vx * deltaTime * 0.016;
particle.y += particle.vy * deltaTime * 0.016;

// Also update rotation and scale
particle.rotation += particle.rotationSpeed;
const lifeFraction = particle.age / particle.maxAge;
particle.currentScale = particle.scaleStart + (particle.scaleEnd - particle.scaleStart) * lifeFraction;
```

### Phase 4: Update Rendering System

**Step 4.1: Add depth sorting before rendering**

In your main animation loop, before rendering particles:
```javascript
// Sort all particles by depth (far to near)
const allParticles = [
  ...baseParticlesRef.current,
  ...outerParticlesRef.current,
  ...edgeParticlesRef.current,
  ...coverParticlesRef.current
].filter(p => p.active);

allParticles.sort((a, b) => a.depth - b.depth);
```

**Step 4.2: Replace gradient rendering with texture rendering**

Find your particle drawing code (likely uses `createRadialGradient`), replace with:
```javascript
const renderParticle = useCallback((ctx, particle) => {
  if (!texturesLoadedRef.current || !particle.active) return;
  
  const texture = texturesRef.current[particle.textureIndex];
  if (!texture) return;

  const scale = particle.currentScale || 1;
  const size = particle.size * scale;
  const blur = (1 - particle.depth) * 2; // Far = blurry, near = sharp

  ctx.save();
  
  // Apply depth-based blur
  if (blur > 0.1) {
    ctx.filter = `blur(${blur}px)`;
  }

  // Transform for rotation
  ctx.translate(particle.x, particle.y);
  ctx.rotate(particle.rotation);
  
  // Render texture
  ctx.globalAlpha = particle.opacity;
  ctx.globalCompositeOperation = 'screen'; // Better blending than 'lighter'
  
  ctx.drawImage(
    texture,
    -size / 2,
    -size / 2,
    size,
    size
  );
  
  ctx.restore();
}, []);
```

**Step 4.3: Add glow pass**

After rendering all particles, add:
```javascript
const renderGlowPass = useCallback((ctx, particles, canvas) => {
  ctx.globalCompositeOperation = 'screen';
  ctx.filter = 'blur(20px)';

  particles.forEach(p => {
    if (!p.active || p.opacity < 0.1) return;
    
    const size = p.size * (p.currentScale || 1) * 1.5;
    const gradient = ctx.createRadialGradient(
      p.x, p.y, 0,
      p.x, p.y, size
    );
    
    gradient.addColorStop(0, `rgba(255, 245, 220, ${p.opacity * 0.3})`);
    gradient.addColorStop(0.5, `rgba(255, 245, 220, ${p.opacity * 0.15})`);
    gradient.addColorStop(1, 'rgba(255, 245, 220, 0)');

    ctx.fillStyle = gradient;
    ctx.beginPath();
    ctx.arc(p.x, p.y, size, 0, Math.PI * 2);
    ctx.fill();
  });

  ctx.filter = 'none';
}, []);

// Call after rendering particles:
renderGlowPass(ctx, allParticles, canvas);
```

### Phase 5: Add Object Pooling (Optional but Recommended)

**Step 5.1: Create particle pool**
```javascript
const particlePoolRef = useRef([]);
const MAX_POOL_SIZE = 2000;

const acquireParticle = useCallback(() => {
  if (particlePoolRef.current.length > 0) {
    return particlePoolRef.current.pop();
  }
  // Create new particle object structure
  return {
    x: 0, y: 0, vx: 0, vy: 0, size: 0, opacity: 0,
    rotation: 0, rotationSpeed: 0, scaleStart: 1, scaleEnd: 1,
    currentScale: 1, depth: 0.5, textureIndex: 0,
    age: 0, maxAge: 0, active: false,
    // ... add all other properties
  };
}, []);

const releaseParticle = useCallback((particle) => {
  if (particlePoolRef.current.length < MAX_POOL_SIZE) {
    particle.active = false;
    particlePoolRef.current.push(particle);
  }
}, []);
```

**Step 5.2: Update particle creation/destruction**

Replace:
```javascript
// OLD:
const particle = createBaseParticle(canvas);
baseParticlesRef.current.push(particle);

// NEW:
const particle = acquireParticle();
initializeBaseParticle(particle, canvas); // Set all properties
baseParticlesRef.current.push(particle);
```

And when removing:
```javascript
// OLD:
baseParticlesRef.current = baseParticlesRef.current.filter(p => p.age < p.maxAge);

// NEW:
baseParticlesRef.current = baseParticlesRef.current.filter(p => {
  if (p.age >= p.maxAge) {
    releaseParticle(p);
    return false;
  }
  return true;
});
```

## Verification Checklist

After implementation, verify:

### Visual Quality
- [ ] Particles have irregular, organic shapes (not perfect circles)
- [ ] Movement is chaotic and turbulent (not smooth sine waves)
- [ ] Particles rotate as they move
- [ ] Particles grow larger over their lifetime
- [ ] Some particles are sharp (near), some blurry (far)
- [ ] Soft glow around denser steam areas
- [ ] No obvious repetition or tiling patterns

### Performance
- [ ] 60fps on desktop (check DevTools Performance tab)
- [ ] 45+ fps on mobile test device
- [ ] No memory leaks (particles return to pool)
- [ ] Smooth animation with no stuttering

### Functionality
- [ ] All 5 animation phases still work (burst, gush, settle, reveal, ambient)
- [ ] Content reveal timing unchanged
- [ ] Scroll container interaction still works
- [ ] Reset button functions correctly

### Technical
- [ ] No console errors
- [ ] Textures load (or fallbacks work)
- [ ] simplex-noise imports correctly
- [ ] All existing props/features preserved

## Common Issues & Solutions

### Issue: Textures not loading
**Solution**: Check paths match public directory structure. Fallbacks should generate automatically.

### Issue: Performance drops below 45fps
**Solution**: 
- Reduce particle counts by 20%
- Lower texture resolution (512 → 256)
- Disable blur on far particles
- Skip glow pass on mobile

### Issue: Particles look too sharp/digital
**Solution**:
- Increase blur amounts in texture creation
- Add slight global blur: `ctx.filter = 'blur(0.5px)'`
- Use more varied texture indices

### Issue: Movement too chaotic/random
**Solution**:
- Reduce noise strength (8 → 5)
- Increase noise scale (0.003 → 0.005)
- Add damping to velocity

### Issue: Rotation looks unnatural
**Solution**:
- Reduce rotationSpeed values by 50%
- Vary rotation speed more per particle type
- Tie rotation to velocity direction

## Package.json Addition

User needs to run:
```bash
npm install simplex-noise
```

Add to dependencies:
```json
"dependencies": {
  "simplex-noise": "^4.0.1"
}
```

## File Naming

Save the upgraded version as:
- **steam-animation-v31.jsx** (new enhanced version)
- Keep **steam-animation-v35.jsx** (original for comparison)

## Success Criteria

You've successfully upgraded to v31 when:

1. ✅ Visual quality reaches 75-80% AAA standards (vs 40% in v35)
2. ✅ Performance maintains 60fps desktop, 45+ mobile
3. ✅ All existing features/phases work identically
4. ✅ Code remains clean, readable, maintainable
5. ✅ User can compare v35 vs v31 side-by-side

## Additional Context from Provided Documents

Review these sections from the provided documents:

**From assessment.md**:
- "Current Implementation Analysis" → Understand v35 architecture
- "Critical Visual Limitations" → Know what you're fixing
- "Option A: Enhanced Canvas 2D" → Full implementation approach
- "Implementation Priority Matrix" → Order of changes

**From action-plan-checklist.md**:
- "Week 1 Tasks" → Immediate actions (textures + noise)
- "Week 2 Tasks" → Secondary enhancements (rotation + depth)
- "Testing Checklist" → Validation criteria

**From texture-creation-guide.md**:
- "Quick Comparison: Which Method?" → If user asks about textures
- "Fallback texture" → Reference for procedural generation

## Final Notes

- **Don't overthink it**: These are additive changes to working code
- **Test incrementally**: Add one enhancement at a time
- **Preserve v35**: Keep original file for user comparison
- **Performance first**: If FPS drops, scale back enhancements
- **Ask questions**: If anything is unclear, ask the user

Good luck! You're upgrading a solid foundation to AAA quality. 🚂💨
