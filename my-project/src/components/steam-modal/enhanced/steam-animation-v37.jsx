import React, { useEffect, useRef, useState, useCallback } from 'react';

/**
 * Steam Animation v37
 *
 * UPGRADE APPROACH: Additive enhancements on top of v35 baseline
 *
 * PRESERVED from v35:
 * - 7-stop gradient drawParticle() with alphaMultiplier
 * - getWaft() function for deterministic seed-based movement
 * - All movement multipliers (base: 0.25, outer: 1.2, side: 2.0, etc.)
 * - 3-tier alpha layer system (back: 0.5, mid: 0.7, front: 1.0)
 * - 5-layer canvas architecture
 * - Phase-based animation timing
 *
 * ADDED in v37:
 * - Built-in Perlin noise (no external dependencies)
 * - Noise flow as enhancement ON TOP of existing waft
 * - Texture overlay system (optional, doesn't replace gradients)
 * - Particle rotation and rotationSpeed
 * - Scale evolution (scaleStart -> scaleEnd over lifetime)
 * - Depth property for parallax and sorting
 * - Procedural fallback textures
 *
 * REMOVED:
 * - Debug red border
 */

// ============================================================================
// BUILT-IN PERLIN NOISE IMPLEMENTATION
// ============================================================================

// Permutation table for noise generation
const PERLIN_PERMUTATION = [
  151,160,137,91,90,15,131,13,201,95,96,53,194,233,7,225,140,36,103,30,69,142,
  8,99,37,240,21,10,23,190,6,148,247,120,234,75,0,26,197,62,94,252,219,203,117,
  35,11,32,57,177,33,88,237,149,56,87,174,20,125,136,171,168,68,175,74,165,71,
  134,139,48,27,166,77,146,158,231,83,111,229,122,60,211,133,230,220,105,92,41,
  55,46,245,40,244,102,143,54,65,25,63,161,1,216,80,73,209,76,132,187,208,89,
  18,169,200,196,135,130,116,188,159,86,164,100,109,198,173,186,3,64,52,217,226,
  250,124,123,5,202,38,147,118,126,255,82,85,212,207,206,59,227,47,16,58,17,182,
  189,28,42,223,183,170,213,119,248,152,2,44,154,163,70,221,153,101,155,167,43,
  172,9,129,22,39,253,19,98,108,110,79,113,224,232,178,185,112,104,218,246,97,
  228,251,34,242,193,238,210,144,12,191,179,162,241,81,51,145,235,249,14,239,
  107,49,192,214,31,181,199,106,157,184,84,204,176,115,121,50,45,127,4,150,254,
  138,236,205,93,222,114,67,29,24,72,243,141,128,195,78,66,215,61,156,180
];

// Double the permutation table for overflow handling
const perm = [...PERLIN_PERMUTATION, ...PERLIN_PERMUTATION];

// Fade function for smooth interpolation
const fade = (t) => t * t * t * (t * (t * 6 - 15) + 10);

// Linear interpolation
const lerp = (t, a, b) => a + t * (b - a);

// Gradient function for 3D noise
const grad3D = (hash, x, y, z) => {
  const h = hash & 15;
  const u = h < 8 ? x : y;
  const v = h < 4 ? y : h === 12 || h === 14 ? x : z;
  return ((h & 1) === 0 ? u : -u) + ((h & 2) === 0 ? v : -v);
};

// 3D Perlin noise function
const perlinNoise3D = (x, y, z) => {
  // Find unit cube that contains point
  const X = Math.floor(x) & 255;
  const Y = Math.floor(y) & 255;
  const Z = Math.floor(z) & 255;

  // Find relative x, y, z of point in cube
  x -= Math.floor(x);
  y -= Math.floor(y);
  z -= Math.floor(z);

  // Compute fade curves
  const u = fade(x);
  const v = fade(y);
  const w = fade(z);

  // Hash coordinates of cube corners
  const A = perm[X] + Y;
  const AA = perm[A] + Z;
  const AB = perm[A + 1] + Z;
  const B = perm[X + 1] + Y;
  const BA = perm[B] + Z;
  const BB = perm[B + 1] + Z;

  // Blend results from 8 corners of cube
  return lerp(w,
    lerp(v,
      lerp(u, grad3D(perm[AA], x, y, z), grad3D(perm[BA], x - 1, y, z)),
      lerp(u, grad3D(perm[AB], x, y - 1, z), grad3D(perm[BB], x - 1, y - 1, z))
    ),
    lerp(v,
      lerp(u, grad3D(perm[AA + 1], x, y, z - 1), grad3D(perm[BA + 1], x - 1, y, z - 1)),
      lerp(u, grad3D(perm[AB + 1], x, y - 1, z - 1), grad3D(perm[BB + 1], x - 1, y - 1, z - 1))
    )
  );
};

// ============================================================================
// MAIN COMPONENT
// ============================================================================

const SteamAnimation = () => {
  const baseCanvasRef = useRef(null);
  const outerCanvasRef = useRef(null);
  const edgeCanvasRef = useRef(null);
  const coverCanvasRef = useRef(null);
  const sideCanvasRef = useRef(null);
  const containerRef = useRef(null);
  const contentRef = useRef(null);

  const baseParticlesRef = useRef([]);
  const outerParticlesRef = useRef([]);
  const edgeParticlesRef = useRef([]);
  const coverParticlesRef = useRef([]);
  const sideParticlesRef = useRef([]);

  const animationRef = useRef(null);
  const phaseRef = useRef(0);
  const startTimeRef = useRef(null);
  const [isStarted, setIsStarted] = useState(false);
  const [showContent, setShowContent] = useState(false);
  const [revealProgress, setRevealProgress] = useState(0);

  // v37: Texture system refs
  const texturesRef = useRef([]);
  const texturesLoadedRef = useRef(false);

  // ============================================================================
  // v37: TEXTURE SYSTEM (Optional enhancement, not required for rendering)
  // ============================================================================

  // Create procedural fallback texture
  const createFallbackTexture = useCallback((type) => {
    const canvas = document.createElement('canvas');
    canvas.width = 256;
    canvas.height = 256;
    const ctx = canvas.getContext('2d');

    const centerX = 128;
    const centerY = 128;

    // Different procedural patterns based on type
    const patterns = [
      { blobs: 80, spread: 100, blur: 12 },  // wispy
      { blobs: 60, spread: 90, blur: 14 },   // soft cloud
      { blobs: 100, spread: 110, blur: 10 }, // dense
      { blobs: 40, spread: 80, blur: 16 },   // diffuse
      { blobs: 70, spread: 95, blur: 11 },   // swirl-like
      { blobs: 50, spread: 85, blur: 15 },   // mist
    ];

    const p = patterns[type % patterns.length];

    for (let i = 0; i < p.blobs; i++) {
      const angle = Math.random() * Math.PI * 2;
      const dist = Math.random() * p.spread;
      const x = centerX + Math.cos(angle) * dist;
      const y = centerY + Math.sin(angle) * dist;
      const size = 15 + Math.random() * 35;
      const alpha = 0.15 + Math.random() * 0.25;

      const gradient = ctx.createRadialGradient(x, y, 0, x, y, size);
      gradient.addColorStop(0, `rgba(255, 255, 255, ${alpha})`);
      gradient.addColorStop(0.5, `rgba(255, 255, 255, ${alpha * 0.4})`);
      gradient.addColorStop(1, 'rgba(255, 255, 255, 0)');

      ctx.fillStyle = gradient;
      ctx.beginPath();
      ctx.arc(x, y, size, 0, Math.PI * 2);
      ctx.fill();
    }

    // Apply blur for organic look
    ctx.filter = `blur(${p.blur}px)`;
    ctx.drawImage(canvas, 0, 0);
    ctx.filter = 'none';

    return canvas;
  }, []);

  // Load textures on mount (optional - rendering works without them)
  useEffect(() => {
    // Generate procedural fallback textures immediately
    const textures = [];
    for (let i = 0; i < 6; i++) {
      textures[i] = createFallbackTexture(i);
    }
    texturesRef.current = textures;
    texturesLoadedRef.current = true;
  }, [createFallbackTexture]);

  // ============================================================================
  // PRESERVED v35 BOUNDS FUNCTIONS
  // ============================================================================

  const getContentBounds = useCallback((canvas) => {
    const top = 15;
    const height = canvas.height - 45;
    return { top, bottom: top + height, height, centerY: canvas.height / 2 };
  }, []);

  const getVisibleContentBounds = useCallback((canvas) => {
    const padding = -51;
    const containerTop = 15;
    const containerHeight = canvas.height - 45;
    return {
      top: containerTop + padding,
      bottom: containerTop + containerHeight - padding,
      containerTop,
      containerBottom: containerTop + containerHeight
    };
  }, []);

  // ============================================================================
  // PRESERVED v35 getWaft() - Core deterministic movement
  // ============================================================================

  const getWaft = useCallback((seed, time, strength = 1) => {
    const t = time * 0.0001;
    const x = Math.sin(t + seed) * Math.cos(t * 0.7 + seed * 0.5) * strength;
    const y = (Math.sin(t * 0.8 + seed * 1.2) * Math.cos(t * 0.5 + seed) - 0.15) * strength;
    return { x, y };
  }, []);

  // ============================================================================
  // v37 NEW: Perlin noise flow (ENHANCEMENT on top of waft, not replacement)
  // ============================================================================

  const getNoiseFlow = useCallback((x, y, time, strength = 1) => {
    const scale = 0.004;
    const timeScale = 0.00008;
    const t = time * timeScale;

    return {
      x: perlinNoise3D(x * scale, y * scale, t) * strength,
      y: perlinNoise3D(x * scale + 100, y * scale, t) * strength - 0.02 * strength
    };
  }, []);

  // ============================================================================
  // PRESERVED v35 getColor()
  // ============================================================================

  const getColor = useCallback(() => {
    const colors = [
      { r: 212, g: 192, b: 168 },
      { r: 205, g: 185, b: 158 },
      { r: 198, g: 178, b: 152 },
      { r: 218, g: 200, b: 175 },
    ];
    return colors[Math.floor(Math.random() * colors.length)];
  }, []);

  // ============================================================================
  // PRESERVED v35 getSideMarginBounds()
  // ============================================================================

  const getSideMarginBounds = useCallback((canvas) => {
    const bounds = getContentBounds(canvas);
    const contentMaxWidth = 576;
    const contentPadding = 20;
    const centerX = canvas.width / 2;
    const halfContent = Math.min(contentMaxWidth / 2, canvas.width / 2 - contentPadding);

    return {
      left: { x1: 0, x2: centerX - halfContent + contentPadding * 2 },
      right: { x1: centerX + halfContent - contentPadding * 2, x2: canvas.width },
      top: bounds.top,
      bottom: bounds.bottom
    };
  }, [getContentBounds]);

  // ============================================================================
  // ENHANCED PARTICLE CREATION FUNCTIONS
  // (v35 properties preserved, v37 properties ADDED)
  // ============================================================================

  const createSideParticle = useCallback((canvas, side) => {
    const margins = getSideMarginBounds(canvas);
    const bounds = getContentBounds(canvas);
    const size = 35 + Math.random() * 50;

    let x;
    if (side === 'left') {
      x = margins.left.x1 + Math.random() * (margins.left.x2 - margins.left.x1);
    } else {
      x = margins.right.x1 + Math.random() * (margins.right.x2 - margins.right.x1);
    }

    return {
      // PRESERVED v35 properties
      x,
      y: bounds.bottom + Math.random() * 50,
      size,
      opacity: 0,
      targetOpacity: 0.12 + Math.random() * 0.08,
      seed: Math.random() * 10000,
      waftStrength: 4 + Math.random() * 5,
      driftX: (Math.random() - 0.5) * 2.5,
      driftY: -1.2 - Math.random() * 1.5,
      blowStrength: 1.5 + Math.random() * 2.5,
      blowAngle: Math.random() * Math.PI * 2,
      turbulence: 2 + Math.random() * 2.5,
      side,
      age: 0,
      maxAge: 250 + Math.random() * 150,
      color: getColor(),

      // NEW v37 properties - subtle scale for side particles
      rotation: Math.random() * Math.PI * 2,
      rotationSpeed: (Math.random() - 0.5) * 0.03,
      scaleStart: 0.95 + Math.random() * 0.1,
      scaleEnd: 1.0 + Math.random() * 0.1,
      currentScale: 1,
      depth: 0.3 + Math.random() * 0.7,
      textureIndex: Math.floor(Math.random() * 6),
    };
  }, [getSideMarginBounds, getContentBounds, getColor]);

  const createBaseParticle = useCallback((canvas) => {
    const bounds = getContentBounds(canvas);
    return {
      // PRESERVED v35 properties
      x: 10 + Math.random() * (canvas.width - 20),
      y: bounds.top + 5 + Math.random() * (bounds.height - 10),
      size: 75 + Math.random() * 100,
      opacity: 0,
      targetOpacity: 0.42 + Math.random() * 0.2,
      seed: Math.random() * 10000,
      waftStrength: 0.12 + Math.random() * 0.1,
      age: 0,
      maxAge: 1400 + Math.random() * 1000,
      color: getColor(),

      // NEW v37 properties
      rotation: Math.random() * Math.PI * 2,
      rotationSpeed: (Math.random() - 0.5) * 0.008,
      scaleStart: 0.9 + Math.random() * 0.1,
      scaleEnd: 1.05 + Math.random() * 0.15,
      currentScale: 1,
      depth: Math.random(),
      textureIndex: Math.floor(Math.random() * 6),
    };
  }, [getContentBounds, getColor]);

  const createOuterParticle = useCallback((canvas) => {
    const bounds = getContentBounds(canvas);
    let x, y;

    if (Math.random() < 0.7) {
      x = Math.random() * canvas.width;
      y = Math.random() < 0.5
        ? Math.random() * bounds.top
        : bounds.bottom + Math.random() * (canvas.height - bounds.bottom);
    } else {
      x = Math.random() < 0.5 ? Math.random() * 80 : canvas.width - Math.random() * 80;
      y = Math.random() < 0.5 ? Math.random() * bounds.top : bounds.bottom + Math.random() * (canvas.height - bounds.bottom);
    }

    return {
      // PRESERVED v35 properties
      x, y,
      size: 35 + Math.random() * 55,
      opacity: 0,
      targetOpacity: 0.22 + Math.random() * 0.08,
      seed: Math.random() * 10000,
      waftStrength: 3 + Math.random() * 4,
      driftX: (Math.random() - 0.5) * 1.5,
      driftY: (Math.random() - 0.5) * 0.8 - 0.15,
      blowStrength: Math.random() * 2,
      blowAngle: Math.random() * Math.PI * 2,
      turbulence: 0.8 + Math.random() * 1.2,
      age: 0,
      maxAge: 200 + Math.random() * 200,
      color: getColor(),

      // NEW v37 properties - subtle scale for outer particles
      rotation: Math.random() * Math.PI * 2,
      rotationSpeed: (Math.random() - 0.5) * 0.02,
      scaleStart: 0.9 + Math.random() * 0.15,
      scaleEnd: 1.0 + Math.random() * 0.15,
      currentScale: 1,
      depth: Math.random(),
      textureIndex: Math.floor(Math.random() * 6),
    };
  }, [getContentBounds, getColor]);

  const createEdgeParticle = useCallback((canvas, zone, forceX = null) => {
    const bounds = getVisibleContentBounds(canvas);
    const size = 110 + Math.random() * 70;

    let x, y;
    x = forceX !== null ? forceX : Math.random() * canvas.width;

    if (zone === 'top') {
      const topZone = bounds.top;
      y = topZone - size * 0.3 - Math.random() * (topZone * 0.5);
    } else {
      const bottomZone = canvas.height - bounds.bottom;
      y = bounds.bottom + size * 0.3 + Math.random() * (bottomZone * 0.5);
    }

    return {
      // PRESERVED v35 properties
      x, y,
      size,
      opacity: 0,
      targetOpacity: 0.58 + Math.random() * 0.17,
      seed: Math.random() * 10000,
      waftStrength: 0.5 + Math.random() * 0.6,
      driftX: (Math.random() - 0.5) * 0.25,
      driftY: (Math.random() - 0.5) * 0.1,
      blowStrength: Math.random() * 0.2,
      blowAngle: Math.random() * Math.PI * 2,
      turbulence: 0.15 + Math.random() * 0.2,
      zone,
      age: 0,
      maxAge: 600 + Math.random() * 400,
      color: getColor(),

      // NEW v37 properties
      rotation: Math.random() * Math.PI * 2,
      rotationSpeed: (Math.random() - 0.5) * 0.006,
      scaleStart: 0.95 + Math.random() * 0.1,
      scaleEnd: 1.02 + Math.random() * 0.08,
      currentScale: 1,
      depth: 0.4 + Math.random() * 0.6,
      textureIndex: Math.floor(Math.random() * 6),
    };
  }, [getVisibleContentBounds, getColor]);

  const createCoverParticle = useCallback((canvas, phase, forcePos = null, fillProgress = 0) => {
    const centerX = canvas.width / 2;
    const centerY = canvas.height / 2;

    let x, y, vx, vy, size;

    if (phase === 'burst') {
      const angle = Math.random() * Math.PI * 2;
      const dist = Math.random() * 10;
      x = centerX + Math.cos(angle) * dist;
      y = centerY + Math.sin(angle) * dist;
      const speed = 5 + Math.random() * 7;
      vx = Math.cos(angle) * speed;
      vy = Math.sin(angle) * speed;
      size = 60 + Math.random() * 80;
    } else if (phase === 'gush') {
      const spawnRadius = 15 + fillProgress * 120;
      const angle = Math.random() * Math.PI * 2;
      const dist = Math.random() * spawnRadius;
      x = centerX + Math.cos(angle) * dist;
      y = centerY + Math.sin(angle) * dist;
      const speed = 3 + Math.random() * 5;
      vx = Math.cos(angle) * speed + (Math.random() - 0.5) * 1.5;
      vy = Math.sin(angle) * speed + (Math.random() - 0.5) * 1.5;
      size = 70 + Math.random() * 90;
    } else if (forcePos) {
      x = forcePos.x;
      y = forcePos.y;
      vx = (Math.random() - 0.5) * 1;
      vy = (Math.random() - 0.5) * 1 - 0.3;
      size = 30 + Math.random() * 50;
    } else {
      const edgeAngle = Math.random() * Math.PI * 2;
      const maxR = Math.min(canvas.width, canvas.height) * 0.45;
      x = centerX + Math.cos(edgeAngle) * maxR * (0.7 + Math.random() * 0.3);
      y = centerY + Math.sin(edgeAngle) * maxR * (0.7 + Math.random() * 0.3);
      vx = (Math.random() - 0.5) * 0.8;
      vy = (Math.random() - 0.5) * 0.8 - 0.2;
      size = 25 + Math.random() * 40;
    }

    return {
      // PRESERVED v35 properties
      x, y, vx, vy, size,
      opacity: 0,
      targetOpacity: phase === 'burst' ? 0.5 : phase === 'gush' ? 0.45 + Math.random() * 0.15 : 0.15,
      seed: Math.random() * 10000,
      waftStrength: 2 + Math.random() * 3,
      driftX: (Math.random() - 0.5) * 1.0,
      driftY: (Math.random() - 0.5) * 0.6,
      blowStrength: Math.random() * 1.5,
      blowAngle: Math.random() * Math.PI * 2,
      turbulence: 0.6 + Math.random() * 1,
      age: 0,
      maxAge: phase === 'burst' ? 120 + Math.random() * 80 : phase === 'gush' ? 180 + Math.random() * 120 : 100 + Math.random() * 60,
      layer: Math.random() < 0.3 ? 'back' : Math.random() < 0.7 ? 'mid' : 'front',
      color: getColor(),

      // NEW v37 properties - cover particles SHRINK over lifetime for better reveal
      rotation: Math.random() * Math.PI * 2,
      rotationSpeed: (Math.random() - 0.5) * 0.025,
      scaleStart: 1.0 + Math.random() * 0.2,
      scaleEnd: 0.6 + Math.random() * 0.3,
      currentScale: 1,
      depth: Math.random(),
      textureIndex: Math.floor(Math.random() * 6),
    };
  }, [getColor]);

  // ============================================================================
  // PRESERVED v35 drawParticle() - Core gradient rendering with alphaMultiplier
  // ============================================================================

  const drawParticle = useCallback((ctx, p, alphaMultiplier = 1) => {
    if (p.opacity < 0.003) return;
    const c = p.color;
    const alpha = p.opacity * alphaMultiplier;

    // PRESERVED: Full 7-stop gradient from v35
    // v37 ENABLED: Scale evolution
    const effectiveSize = p.size * (p.currentScale || 1);
    const gradient = ctx.createRadialGradient(p.x, p.y, 0, p.x, p.y, effectiveSize);
    gradient.addColorStop(0, `rgba(${c.r + 12}, ${c.g + 12}, ${c.b + 8}, ${alpha * 0.9})`);
    gradient.addColorStop(0.2, `rgba(${c.r + 5}, ${c.g + 5}, ${c.b + 3}, ${alpha * 0.7})`);
    gradient.addColorStop(0.4, `rgba(${c.r}, ${c.g}, ${c.b}, ${alpha * 0.5})`);
    gradient.addColorStop(0.6, `rgba(${c.r - 5}, ${c.g - 5}, ${c.b - 3}, ${alpha * 0.3})`);
    gradient.addColorStop(0.8, `rgba(${c.r - 10}, ${c.g - 10}, ${c.b - 6}, ${alpha * 0.12})`);
    gradient.addColorStop(0.92, `rgba(${c.r - 15}, ${c.g - 15}, ${c.b - 10}, ${alpha * 0.04})`);
    gradient.addColorStop(1, `rgba(${c.r - 15}, ${c.g - 15}, ${c.b - 10}, 0)`);

    ctx.beginPath();
    ctx.arc(p.x, p.y, effectiveSize, 0, Math.PI * 2);
    ctx.fillStyle = gradient;
    ctx.fill();

    // v37 ENABLED: Texture overlay
    if (texturesLoadedRef.current && p.textureIndex !== undefined && alpha > 0.05) {
      const texture = texturesRef.current[p.textureIndex];
      if (texture) {
        ctx.save();
        ctx.translate(p.x, p.y);
        ctx.rotate(p.rotation || 0);
        ctx.globalAlpha = alpha * 0.25;
        ctx.globalCompositeOperation = 'screen';
        ctx.drawImage(texture, -effectiveSize * 0.8, -effectiveSize * 0.8, effectiveSize * 1.6, effectiveSize * 1.6);
        ctx.restore();
      }
    }
  }, []);

  // ============================================================================
  // ENHANCED UPDATE FUNCTIONS
  // (PRESERVED v35 movement + ADDED v37 noise enhancement)
  // ============================================================================

  const updateBaseParticles = useCallback((ctx, canvas, time, phase) => {
    const bounds = getContentBounds(canvas);

    baseParticlesRef.current = baseParticlesRef.current.filter(p => {
      p.age++;

      // PRESERVED v35: Original waft-based movement
      const w = getWaft(p.seed, time, p.waftStrength);
      p.x += w.x * 0.25;
      p.y += w.y * 0.2;

      // v37 ENABLED: Noise flow
      const noise = getNoiseFlow(p.x, p.y, time, 0.3);
      p.x += noise.x * 0.08;
      p.y += noise.y * 0.06;

      // v37 ENABLED: Update rotation and scale
      p.rotation = (p.rotation || 0) + (p.rotationSpeed || 0);
      const lifeFraction = p.age / p.maxAge;
      p.currentScale = (p.scaleStart || 1) + ((p.scaleEnd || 1) - (p.scaleStart || 1)) * lifeFraction;

      // PRESERVED v35: Boundary constraints
      if (p.y < bounds.top + 15) p.y += 0.15;
      if (p.y > bounds.bottom - 15) p.y -= 0.15;
      if (p.x < 20) p.x += 0.15;
      if (p.x > canvas.width - 20) p.x -= 0.15;

      // PRESERVED v35: Opacity handling
      const ageRatio = p.age / p.maxAge;
      if (phase >= 3) {
        p.opacity += (p.targetOpacity - p.opacity) * 0.05;
      } else if (ageRatio < 0.1) {
        p.opacity += (p.targetOpacity - p.opacity) * 0.025;
      }
      if (ageRatio > 0.92) p.opacity *= 0.996;

      return p.opacity > 0.008 && p.age < p.maxAge;
    });

    baseParticlesRef.current.forEach(p => drawParticle(ctx, p));
  }, [getContentBounds, getWaft, getNoiseFlow, drawParticle]);

  const updateOuterParticles = useCallback((ctx, canvas, time) => {
    const bounds = getContentBounds(canvas);

    outerParticlesRef.current = outerParticlesRef.current.filter(p => {
      p.age++;

      // PRESERVED v35: Original waft-based movement with full multipliers
      const w = getWaft(p.seed, time, p.waftStrength);

      if (Math.random() < 0.03) {
        p.blowAngle += (Math.random() - 0.5) * 1.5;
        p.blowStrength = 0.5 + Math.random() * 2.5;
      }

      const turbX = (Math.random() - 0.5) * p.turbulence * 0.5;
      const turbY = (Math.random() - 0.5) * p.turbulence * 0.4;

      // PRESERVED v35: Full movement multipliers (1.2, 0.9)
      p.x += w.x * 1.2 + p.driftX + Math.cos(p.blowAngle) * p.blowStrength * 0.3 + turbX;
      p.y += w.y * 0.9 + p.driftY + Math.sin(p.blowAngle) * p.blowStrength * 0.2 + turbY;

      // v37 ENABLED: Add noise flow on top
      const noise = getNoiseFlow(p.x, p.y, time, 0.5);
      p.x += noise.x * 0.15;
      p.y += noise.y * 0.12;

      // v37 ENABLED: Update rotation and scale
      p.rotation = (p.rotation || 0) + (p.rotationSpeed || 0);
      const lifeFraction = p.age / p.maxAge;
      p.currentScale = (p.scaleStart || 1) + ((p.scaleEnd || 1) - (p.scaleStart || 1)) * lifeFraction;

      // PRESERVED v35: Drift updates
      p.driftX += (Math.random() - 0.5) * 0.08;
      p.driftY += (Math.random() - 0.5) * 0.05;
      p.driftX *= 0.98;
      p.driftY *= 0.98;
      p.blowStrength *= 0.96;

      // PRESERVED v35: Content area avoidance
      if (p.y > bounds.top - 15 && p.y < bounds.bottom + 15) {
        if (p.y < bounds.centerY) {
          p.y -= 1.2;
          p.driftY -= 0.1;
        } else {
          p.y += 1.2;
          p.driftY += 0.1;
        }
      }

      // PRESERVED v35: Wrapping
      if (p.x < -p.size) p.x = canvas.width + p.size * 0.5;
      if (p.x > canvas.width + p.size) p.x = -p.size * 0.5;
      if (p.y < -p.size * 0.5) p.y = -p.size * 0.5 + 3;
      if (p.y > canvas.height + p.size * 0.5) p.y = canvas.height + p.size * 0.5 - 3;

      // PRESERVED v35: Opacity handling
      const ageRatio = p.age / p.maxAge;
      if (ageRatio < 0.1) {
        p.opacity += (p.targetOpacity - p.opacity) * 0.04;
      } else if (ageRatio > 0.7) {
        p.opacity *= 0.985;
      }

      return p.opacity > 0.005 && p.age < p.maxAge;
    });

    outerParticlesRef.current.forEach(p => drawParticle(ctx, p));
  }, [getContentBounds, getWaft, getNoiseFlow, drawParticle]);

  const updateEdgeParticles = useCallback((ctx, canvas, time) => {
    const bounds = getVisibleContentBounds(canvas);

    edgeParticlesRef.current = edgeParticlesRef.current.filter(p => {
      p.age++;

      // PRESERVED v35: Original waft movement
      const w = getWaft(p.seed, time, p.waftStrength);

      if (Math.random() < 0.01) {
        p.blowAngle += (Math.random() - 0.5) * 0.5;
        p.blowStrength = 0.05 + Math.random() * 0.2;
      }

      const turbX = (Math.random() - 0.5) * p.turbulence * 0.1;
      const turbY = (Math.random() - 0.5) * p.turbulence * 0.05;

      // PRESERVED v35: Movement with original multipliers
      p.x += w.x * 0.3 + p.driftX * 0.3 + Math.cos(p.blowAngle) * p.blowStrength * 0.05 + turbX;
      p.y += w.y * 0.2 + p.driftY * 0.2 + Math.sin(p.blowAngle) * p.blowStrength * 0.03 + turbY;

      // v37 ENABLED: Subtle noise enhancement
      const noise = getNoiseFlow(p.x, p.y, time, 0.2);
      p.x += noise.x * 0.04;
      p.y += noise.y * 0.03;

      // v37 ENABLED: Update rotation and scale
      p.rotation = (p.rotation || 0) + (p.rotationSpeed || 0);
      const lifeFraction = Math.min(p.age / p.maxAge, 1);
      p.currentScale = (p.scaleStart || 1) + ((p.scaleEnd || 1) - (p.scaleStart || 1)) * lifeFraction;

      // PRESERVED v35: Drift updates
      p.driftX += (Math.random() - 0.5) * 0.015;
      p.driftY += (Math.random() - 0.5) * 0.01;
      p.driftX *= 0.995;
      p.driftY *= 0.995;
      p.blowStrength *= 0.98;

      // PRESERVED v35: Zone boundary logic
      if (p.zone === 'top') {
        if (p.y > bounds.top - 5) p.y = bounds.top - 5 - Math.random() * 10;
        if (p.y < -p.size * 0.4) p.y = -p.size * 0.4 + 2;
      } else {
        if (p.y < bounds.bottom + 5) p.y = bounds.bottom + 5 + Math.random() * 10;
        if (p.y > canvas.height + p.size * 0.4) p.y = canvas.height + p.size * 0.4 - 2;
      }

      if (p.x < -p.size * 0.4) p.x = canvas.width + p.size * 0.2;
      if (p.x > canvas.width + p.size * 0.4) p.x = -p.size * 0.2;

      // PRESERVED v35: Fixed state - instant full opacity
      if (p.opacity < p.targetOpacity) {
        p.opacity = p.targetOpacity;
      }

      return true;
    });

    edgeParticlesRef.current.forEach(p => drawParticle(ctx, p));
  }, [getVisibleContentBounds, getWaft, getNoiseFlow, drawParticle]);

  const updateSideParticles = useCallback((ctx, canvas, time) => {
    const bounds = getContentBounds(canvas);
    const margins = getSideMarginBounds(canvas);

    sideParticlesRef.current = sideParticlesRef.current.filter(p => {
      p.age++;

      // PRESERVED v35: Original waft with high strength
      const w = getWaft(p.seed, time, p.waftStrength);

      // PRESERVED v35: Frequent direction changes
      if (Math.random() < 0.1) {
        p.blowAngle += (Math.random() - 0.5) * 2.5;
        p.blowStrength = 1.5 + Math.random() * 3;
      }

      // PRESERVED v35: High turbulence
      const turbX = (Math.random() - 0.5) * p.turbulence;
      const turbY = (Math.random() - 0.5) * p.turbulence * 0.5;

      // PRESERVED v35: Strong waft multipliers (2.0, 1.2)
      p.x += w.x * 2 + p.driftX * 0.6 + Math.cos(p.blowAngle) * p.blowStrength * 0.5 + turbX;
      p.y += w.y * 1.2 + p.driftY + Math.sin(p.blowAngle) * p.blowStrength * 0.3 + turbY;

      // v37 ENABLED: Add noise for extra organic movement
      const noise = getNoiseFlow(p.x, p.y, time, 0.6);
      p.x += noise.x * 0.2;
      p.y += noise.y * 0.15;

      // v37 ENABLED: Update rotation and scale
      p.rotation = (p.rotation || 0) + (p.rotationSpeed || 0);
      const lifeFraction = p.age / p.maxAge;
      p.currentScale = (p.scaleStart || 1) + ((p.scaleEnd || 1) - (p.scaleStart || 1)) * lifeFraction;

      // PRESERVED v35: Drift updates
      p.driftX += (Math.random() - 0.5) * 0.2;
      p.driftY += (Math.random() - 0.5) * 0.1 - 0.03;
      p.driftX *= 0.96;
      p.driftY *= 0.97;
      p.blowStrength *= 0.92;

      // PRESERVED v35: Side margin constraints
      if (p.side === 'left') {
        if (p.x > margins.left.x2 + p.size * 0.3) {
          p.driftX -= 0.3;
        }
        if (p.x < -p.size * 0.5) p.x = -p.size * 0.3;
      } else {
        if (p.x < margins.right.x1 - p.size * 0.3) {
          p.driftX += 0.3;
        }
        if (p.x > canvas.width + p.size * 0.5) p.x = canvas.width + p.size * 0.3;
      }

      // PRESERVED v35: Respawn at bottom
      if (p.y < bounds.top - p.size) {
        p.y = bounds.bottom + p.size * 0.5;
        p.opacity = 0;
      }

      // PRESERVED v35: Opacity handling
      const ageRatio = p.age / p.maxAge;
      if (ageRatio < 0.12) {
        p.opacity += (p.targetOpacity - p.opacity) * 0.1;
      } else if (ageRatio > 0.7) {
        p.opacity *= 0.96;
      }

      return p.opacity > 0.003 && p.age < p.maxAge;
    });

    sideParticlesRef.current.forEach(p => drawParticle(ctx, p));
  }, [getContentBounds, getSideMarginBounds, getWaft, getNoiseFlow, drawParticle]);

  const updateCoverParticles = useCallback((ctx, canvas, time, phase, revealProg) => {
    const centerX = canvas.width / 2;
    const centerY = canvas.height / 2;

    coverParticlesRef.current = coverParticlesRef.current.filter(p => {
      p.age++;
      const dx = p.x - centerX;
      const dy = p.y - centerY;

      // v37: Calculate distance from center for clearing
      const distFromCenter = Math.sqrt(dx * dx + dy * dy);
      const maxDist = Math.max(canvas.width, canvas.height) * 0.5;

      // PRESERVED v35: Phase 3+ blow-away behavior (v37: AGGRESSIVE fade for content reveal)
      if (phase >= 3) {
        const blowAngle = Math.atan2(dy, dx);
        // v37: Much stronger blow force, especially near center
        const centerBoost = 1 + (1 - distFromCenter / maxDist) * 3;
        const blowForce = (1.5 + revealProg * 5) * 0.3 * centerBoost;
        p.vx += Math.cos(blowAngle) * blowForce + (Math.random() - 0.5) * 0.8;
        p.vy += Math.sin(blowAngle) * blowForce + (Math.random() - 0.5) * 0.8;
        // v37: VERY fast opacity fade - exponential decay
        p.targetOpacity *= 0.6;
        p.opacity *= 0.65;  // Much faster than 0.88
        // v37: Accelerate shrinking during reveal
        p.currentScale = (p.currentScale || 1) * 0.92;

        // v37: Aggressive central clearing - larger radius, faster fade
        const clearRadius = 200 + revealProg * 400;
        if (distFromCenter < clearRadius) {
          p.opacity *= 0.5;  // Kill particles in center zone fast
        }

        // v37: Hard cutoff - remove very faint particles immediately
        if (p.opacity < 0.05) {
          p.opacity = 0;
        }
      }

      // PRESERVED v35: Waft movement
      const waftMult = phase < 3 ? 0.3 : 0.8;
      const w = getWaft(p.seed, time, (p.waftStrength || 2) * waftMult);

      const turbX = phase < 3 ? (Math.random() - 0.5) * (p.turbulence || 0.8) * 0.35 : 0;
      const turbY = phase < 3 ? (Math.random() - 0.5) * (p.turbulence || 0.8) * 0.3 : 0;

      p.vx += w.x * 0.05 + turbX;
      p.vy += w.y * 0.04 + turbY - 0.008;

      // v37 ENABLED: Add noise during phases 1-2
      if (phase < 3) {
        const noise = getNoiseFlow(p.x, p.y, time, 0.4);
        p.vx += noise.x * 0.02;
        p.vy += noise.y * 0.015;
      }

      p.x += p.vx;
      p.y += p.vy;
      p.vx *= phase < 3 ? 0.99 : 0.94;
      p.vy *= phase < 3 ? 0.99 : 0.94;
      p.size += phase < 3 ? 0.2 : 0.05;

      // v37 ENABLED: Update rotation and scale (only during phases 1-2, phase 3+ uses accelerated shrinking above)
      p.rotation = (p.rotation || 0) + (p.rotationSpeed || 0);
      if (phase < 3) {
        const lifeFraction = p.age / p.maxAge;
        p.currentScale = (p.scaleStart || 1) + ((p.scaleEnd || 1) - (p.scaleStart || 1)) * lifeFraction;
      }

      // PRESERVED v35: Opacity handling
      const ageRatio = p.age / p.maxAge;
      if (phase < 3 && ageRatio < 0.15) {
        p.opacity += (p.targetOpacity - p.opacity) * 0.08;
      } else if (phase < 3 && ageRatio > 0.7) {
        p.opacity *= 0.98;
      }

      const minOpacity = phase >= 4 ? 0.01 : 0.003;
      return p.opacity > minOpacity && p.age < p.maxAge;
    });

    // PRESERVED v35: Layer system with alphaMultiplier
    const layers = { back: [], mid: [], front: [] };
    coverParticlesRef.current.forEach(p => layers[p.layer].push(p));

    // v37: Sort each layer by depth for enhanced rendering
    ['back', 'mid', 'front'].forEach(layer => {
      // PRESERVED v35: Alpha multipliers (0.5, 0.7, 1.0)
      const alphaMultiplier = layer === 'back' ? 0.5 : layer === 'mid' ? 0.7 : 1;
      // v37 ENABLED: Depth sorting
      layers[layer].sort((a, b) => (a.depth || 0) - (b.depth || 0));
      layers[layer].forEach(p => drawParticle(ctx, p, alphaMultiplier));
    });
  }, [getWaft, getNoiseFlow, drawParticle]);

  // ============================================================================
  // PRESERVED v35 ANIMATION LOOP (with v37 enhancements integrated)
  // ============================================================================

  const animate = useCallback((timestamp) => {
    if (!startTimeRef.current) startTimeRef.current = timestamp;
    const elapsed = timestamp - startTimeRef.current;

    const baseCanvas = baseCanvasRef.current;
    const outerCanvas = outerCanvasRef.current;
    const edgeCanvas = edgeCanvasRef.current;
    const coverCanvas = coverCanvasRef.current;
    const sideCanvas = sideCanvasRef.current;

    const baseCtx = baseCanvas?.getContext('2d');
    const outerCtx = outerCanvas?.getContext('2d');
    const edgeCtx = edgeCanvas?.getContext('2d');
    const coverCtx = coverCanvas?.getContext('2d');
    const sideCtx = sideCanvas?.getContext('2d');

    if (!baseCtx || !outerCtx || !edgeCtx || !coverCtx || !sideCtx) return;

    let currentPhase = phaseRef.current;
    let currentReveal = 0;

    // PRESERVED v35: All phase timing and spawning logic
    if (elapsed < 500) {
      currentPhase = 1;
      if (elapsed >= 50) {
        const activeProgress = (elapsed - 50) / 450;
        const spawnCount = Math.floor(activeProgress * activeProgress * 18);
        const spreadAngle = Math.PI * 0.17 + activeProgress * Math.PI * 1.83;

        for (let i = 0; i < spawnCount; i++) {
          const p = createCoverParticle(coverCanvas, 'burst');
          p.x = coverCanvas.width / 2;
          p.y = coverCanvas.height / 2;
          const angle = Math.random() * spreadAngle - spreadAngle / 2;
          const frameRotation = (elapsed * 0.01) % (Math.PI * 2);
          const finalAngle = angle + frameRotation;
          const speed = 5 + activeProgress * 8 + Math.random() * 4;
          p.vx = Math.cos(finalAngle) * speed;
          p.vy = Math.sin(finalAngle) * speed;
          p.size = (25 + Math.random() * 30) * (0.4 + activeProgress * 0.9);
          p.targetOpacity = 0.35 + activeProgress * 0.25 + Math.random() * 0.15;
          p.maxAge = 100 + activeProgress * 100 + Math.random() * 60;
          coverParticlesRef.current.push(p);
        }
      }
    } else if (elapsed < 2800) {
      currentPhase = 2;
      const fillProgress = (elapsed - 500) / 2300;
      const centerX = coverCanvas.width / 2;
      const centerY = coverCanvas.height / 2;
      const maxReach = Math.max(coverCanvas.width, coverCanvas.height) * 0.7;
      const currentRadius = 50 + fillProgress * maxReach;
      const gushRate = fillProgress < 0.3 ? 0.95 : fillProgress < 0.6 ? 0.85 : 0.7;

      if (Math.random() < gushRate) {
        const particleCount = Math.floor(6 + (1 - fillProgress) * 6);
        for (let i = 0; i < particleCount; i++) {
          const p = createCoverParticle(coverCanvas, 'gush', null, fillProgress);
          const angle = Math.random() * Math.PI * 2;
          const dist = Math.random() * currentRadius;
          p.x = centerX + Math.cos(angle) * dist;
          p.y = centerY + Math.sin(angle) * dist;
          const outAngle = Math.atan2(p.y - centerY, p.x - centerX);
          const outSpeed = 3 + Math.random() * 4;
          p.vx = Math.cos(outAngle) * outSpeed + (Math.random() - 0.5) * 2;
          p.vy = Math.sin(outAngle) * outSpeed + (Math.random() - 0.5) * 2;
          p.size = 70 + Math.random() * 80;
          p.targetOpacity = 0.42 + Math.random() * 0.18;
          p.maxAge = 200 + Math.random() * 150;
          coverParticlesRef.current.push(p);
        }
      }

      if (fillProgress > 0.25 && Math.random() < 0.55) {
        const p = createCoverParticle(coverCanvas, 'gush', null, fillProgress);
        const edgeX = Math.random() < 0.5 ? Math.random() * 0.25 : 0.75 + Math.random() * 0.25;
        const edgeY = Math.random() < 0.5 ? Math.random() * 0.25 : 0.75 + Math.random() * 0.25;
        p.x = coverCanvas.width * edgeX;
        p.y = coverCanvas.height * edgeY;
        p.vx = (p.x < centerX ? -1 : 1) * (1.5 + Math.random() * 2);
        p.vy = (p.y < centerY ? -1 : 1) * (1.5 + Math.random() * 2);
        p.size = 90 + Math.random() * 100;
        p.targetOpacity = 0.38 + Math.random() * 0.17;
        p.maxAge = 220 + Math.random() * 100;
        coverParticlesRef.current.push(p);
      }
    } else if (elapsed < 5300) {
      currentPhase = 3;
      currentReveal = (elapsed - 2800) / 2500;
      setRevealProgress(currentReveal);
      setShowContent(true);

      // PRESERVED v35: Edge particle spawning
      if (elapsed < 2850 && edgeParticlesRef.current.length < 305) {
        const width = edgeCanvas.width;
        for (let i = 0; i < 40; i++) {
          const xPos = (i / 40) * width + (Math.random() - 0.5) * (width / 20);

          const topP = createEdgeParticle(edgeCanvas, 'top', xPos);
          topP.opacity = topP.targetOpacity;
          edgeParticlesRef.current.push(topP);

          const bottomP = createEdgeParticle(edgeCanvas, 'bottom', xPos);
          bottomP.opacity = bottomP.targetOpacity;
          edgeParticlesRef.current.push(bottomP);
        }
        for (let i = 0; i < 40; i++) {
          const xPos = ((i + 0.5) / 40) * width + (Math.random() - 0.5) * (width / 20);

          const topP = createEdgeParticle(edgeCanvas, 'top', xPos);
          topP.opacity = topP.targetOpacity;
          edgeParticlesRef.current.push(topP);

          const bottomP = createEdgeParticle(edgeCanvas, 'bottom', xPos);
          bottomP.opacity = bottomP.targetOpacity;
          edgeParticlesRef.current.push(bottomP);
        }
        for (let i = 0; i < 40; i++) {
          const xPos = Math.random() * width;

          const topP = createEdgeParticle(edgeCanvas, 'top', xPos);
          topP.opacity = topP.targetOpacity;
          edgeParticlesRef.current.push(topP);

          const bottomP = createEdgeParticle(edgeCanvas, 'bottom', xPos);
          bottomP.opacity = bottomP.targetOpacity;
          edgeParticlesRef.current.push(bottomP);
        }
        const bounds = getVisibleContentBounds(edgeCanvas);
        for (let i = 0; i < 20; i++) {
          const xPos = (i / 20) * width + (Math.random() - 0.5) * (width / 12);

          const topP = createEdgeParticle(edgeCanvas, 'top', xPos);
          topP.y = bounds.top - topP.size * 0.15 - Math.random() * 20;
          topP.opacity = 0.25 + Math.random() * 0.15;
          topP.targetOpacity = topP.opacity;
          edgeParticlesRef.current.push(topP);

          const bottomP = createEdgeParticle(edgeCanvas, 'bottom', xPos);
          bottomP.y = bounds.bottom + bottomP.size * 0.15 + Math.random() * 20;
          bottomP.opacity = 0.25 + Math.random() * 0.15;
          bottomP.targetOpacity = bottomP.opacity;
          edgeParticlesRef.current.push(bottomP);
        }
        for (let i = 0; i < 25; i++) {
          const xPos = (i / 25) * width + (Math.random() - 0.5) * (width / 10);

          const topP = createEdgeParticle(edgeCanvas, 'top', xPos);
          topP.y = bounds.top - topP.size * 0.05 - Math.random() * 10;
          topP.opacity = 0.15 + Math.random() * 0.12;
          topP.targetOpacity = topP.opacity;
          edgeParticlesRef.current.push(topP);
        }
      }

      if (Math.random() < 0.6 && baseParticlesRef.current.length < 150) {
        baseParticlesRef.current.push(createBaseParticle(baseCanvas));
        baseParticlesRef.current.push(createBaseParticle(baseCanvas));
        baseParticlesRef.current.push(createBaseParticle(baseCanvas));
      }
      if (Math.random() < 0.5 && outerParticlesRef.current.length < 60) {
        outerParticlesRef.current.push(createOuterParticle(outerCanvas));
        outerParticlesRef.current.push(createOuterParticle(outerCanvas));
      }
      if (Math.random() < 0.4 && sideParticlesRef.current.length < 40) {
        sideParticlesRef.current.push(createSideParticle(sideCanvas, 'left'));
        sideParticlesRef.current.push(createSideParticle(sideCanvas, 'right'));
      }
    } else {
      currentPhase = 4;
      currentReveal = 1;
      setRevealProgress(1);

      if (Math.random() < 0.3 && baseParticlesRef.current.length < 150) {
        baseParticlesRef.current.push(createBaseParticle(baseCanvas));
        baseParticlesRef.current.push(createBaseParticle(baseCanvas));
      }
      if (Math.random() < 0.3 && outerParticlesRef.current.length < 60) {
        outerParticlesRef.current.push(createOuterParticle(outerCanvas));
        outerParticlesRef.current.push(createOuterParticle(outerCanvas));
      }
      if (Math.random() < 0.35 && sideParticlesRef.current.length < 40) {
        sideParticlesRef.current.push(createSideParticle(sideCanvas, 'left'));
        sideParticlesRef.current.push(createSideParticle(sideCanvas, 'right'));
      }
    }

    phaseRef.current = currentPhase;

    // Clear all canvases
    baseCtx.clearRect(0, 0, baseCanvas.width, baseCanvas.height);
    outerCtx.clearRect(0, 0, outerCanvas.width, outerCanvas.height);
    edgeCtx.clearRect(0, 0, edgeCanvas.width, edgeCanvas.height);
    coverCtx.clearRect(0, 0, coverCanvas.width, coverCanvas.height);
    sideCtx.clearRect(0, 0, sideCanvas.width, sideCanvas.height);

    baseCtx.fillStyle = '#1c1814';
    baseCtx.fillRect(0, 0, baseCanvas.width, baseCanvas.height);

    // Update and render all particle systems
    updateBaseParticles(baseCtx, baseCanvas, elapsed, currentPhase);
    updateOuterParticles(outerCtx, outerCanvas, elapsed);
    updateEdgeParticles(edgeCtx, edgeCanvas, elapsed);
    updateSideParticles(sideCtx, sideCanvas, elapsed);
    updateCoverParticles(coverCtx, coverCanvas, elapsed, currentPhase, currentReveal);

    animationRef.current = requestAnimationFrame(animate);
  }, [createBaseParticle, createOuterParticle, createEdgeParticle, createCoverParticle, createSideParticle,
      updateBaseParticles, updateOuterParticles, updateEdgeParticles, updateSideParticles, updateCoverParticles]);

  // ============================================================================
  // PRESERVED v35 CONTROL FUNCTIONS
  // ============================================================================

  const startAnimation = useCallback(() => {
    setIsStarted(true);
    baseParticlesRef.current = [];
    outerParticlesRef.current = [];
    edgeParticlesRef.current = [];
    coverParticlesRef.current = [];
    sideParticlesRef.current = [];
    startTimeRef.current = null;
    phaseRef.current = 0;
    setShowContent(false);
    setRevealProgress(0);
    animationRef.current = requestAnimationFrame(animate);
  }, [animate]);

  const resetAnimation = useCallback(() => {
    if (animationRef.current) {
      cancelAnimationFrame(animationRef.current);
      animationRef.current = null;
    }
    baseParticlesRef.current = [];
    outerParticlesRef.current = [];
    edgeParticlesRef.current = [];
    coverParticlesRef.current = [];
    sideParticlesRef.current = [];
    [baseCanvasRef, outerCanvasRef, edgeCanvasRef, coverCanvasRef, sideCanvasRef].forEach(ref => {
      const ctx = ref.current?.getContext('2d');
      if (ctx) ctx.clearRect(0, 0, ref.current.width, ref.current.height);
    });
    startTimeRef.current = null;
    phaseRef.current = 0;
    setIsStarted(false);
    setShowContent(false);
    setRevealProgress(0);
  }, []);

  // ============================================================================
  // PRESERVED v35 RESIZE HANDLING
  // ============================================================================

  useEffect(() => {
    const resize = () => {
      const container = containerRef.current;
      if (container) {
        [baseCanvasRef, outerCanvasRef, edgeCanvasRef, coverCanvasRef, sideCanvasRef].forEach(ref => {
          if (ref.current) {
            ref.current.width = container.clientWidth;
            ref.current.height = container.clientHeight;
          }
        });
      }
    };
    resize();
    window.addEventListener('resize', resize);
    return () => window.removeEventListener('resize', resize);
  }, []);

  useEffect(() => () => {
    if (animationRef.current) cancelAnimationFrame(animationRef.current);
  }, []);

  // ============================================================================
  // PRESERVED v35 CONTENT
  // ============================================================================

  const content = [
    { title: "The Art of Steam", text: "Steam has captivated humanity since ancient times. From the mysterious mists of sacred groves to the industrial revolution's mighty engines, vapor has always held a special place in our collective imagination." },
    { title: "Origins & History", text: "The earliest recorded use of steam power dates back to Hero of Alexandria in the 1st century AD. His aeolipile demonstrated the potential of harnessing vapor's energy, planting seeds for the industrial age." },
    { title: "The Science Within", text: "When water reaches 100°C at sea level, molecules gain enough kinetic energy to break free. This transition releases tremendous energy—a single gram absorbs 2,260 joules becoming steam." },
    { title: "Cultural Significance", text: "Across cultures, steam symbolizes transformation and liminal spaces. Japanese onsen traditions celebrate healing. Nordic saunas purify. Turkish hammams center social life around vapor." },
    { title: "Modern Applications", text: "Today, steam powers roughly 80% of the world's electricity. It sterilizes medical equipment, processes food safely, and propels aircraft carriers across vast oceans." },
    { title: "The Future of Vapor", text: "As we seek sustainable solutions, steam remains central to geothermal power, concentrated solar plants, and next-generation nuclear reactors. Ancient technology meets modern innovation." },
  ];

  // ============================================================================
  // RENDER - v37: Debug border REMOVED
  // ============================================================================

  return (
    <div ref={containerRef} className="relative w-full overflow-hidden" style={{ position: 'relative', background: '#1c1814', height: '100%' }}>
      <canvas ref={baseCanvasRef} className="absolute inset-0" style={{ position: 'absolute', top: 0, left: 0, right: 0, bottom: 0, zIndex: 1 }} />
      <canvas ref={outerCanvasRef} className="absolute inset-0" style={{ position: 'absolute', top: 0, left: 0, right: 0, bottom: 0, zIndex: 2 }} />

      {/* v37: Debug border REMOVED (was present in v35) */}

      {/* Content area with 15px top, 30px bottom margin */}
      {/* Inline positioning required since Tailwind classes don't apply correctly */}
      {/* DEBUG: Force content to always render to test z-index layering */}
      {(showContent || isStarted) && (
        <div
          className="absolute inset-x-0"
          style={{
            position: 'absolute',
            left: 0,
            right: 0,
            zIndex: 3,
            top: 15,
            height: 'calc(100% - 45px)',
            opacity: Math.min(1, revealProgress * 2),
            transition: 'opacity 0.3s ease-out',
          }}
        >
          <div
            ref={contentRef}
            className="w-full h-full overflow-y-auto overflow-x-hidden"
            style={{ scrollbarWidth: 'none', msOverflowStyle: 'none' }}
          >
            <style>{`div::-webkit-scrollbar { display: none; }`}</style>

            <div className="max-w-xl mx-auto px-5 pt-12 pb-12">
              <div
                className="relative mx-auto mb-6"
                style={{
                  opacity: Math.min(1, revealProgress * 1.5),
                  transform: `translateY(${Math.max(0, (1 - revealProgress) * 20)}px)`,
                  transition: 'all 0.5s ease-out',
                }}
              >
                <div
                  className="relative px-10 py-6 rounded-sm overflow-hidden"
                  style={{
                    background: 'linear-gradient(165deg, #c9a87a 0%, #b8956a 15%, #a07850 35%, #8a6540 55%, #785535 75%, #5c4028 100%)',
                    boxShadow: 'inset 0 1px 2px rgba(255,255,255,0.12), inset 0 -2px 4px rgba(0,0,0,0.2), 0 6px 24px rgba(0,0,0,0.4)',
                  }}
                >
                  <div
                    className="absolute inset-0 opacity-35 pointer-events-none"
                    style={{
                      backgroundImage: `
                        repeating-linear-gradient(88deg, transparent 0px, transparent 8px, rgba(60,35,20,0.3) 8px, rgba(60,35,20,0.3) 9px, transparent 9px, transparent 25px),
                        repeating-linear-gradient(92deg, transparent 0px, transparent 40px, rgba(20,10,5,0.45) 40px, rgba(20,10,5,0.5) 42px, rgba(20,10,5,0.35) 44px, transparent 44px, transparent 120px),
                        repeating-linear-gradient(85deg, transparent 0px, transparent 60px, rgba(140,80,60,0.12) 60px, rgba(140,80,60,0.08) 62px, transparent 62px)
                      `,
                    }}
                  />
                  <div
                    className="absolute inset-0 opacity-18 pointer-events-none"
                    style={{
                      background: 'radial-gradient(ellipse at 30% 50%, rgba(120,60,40,0.35) 0%, transparent 50%), radial-gradient(ellipse at 70% 30%, rgba(100,50,35,0.25) 0%, transparent 40%)',
                    }}
                  />

                  <h1
                    className="text-3xl tracking-widest text-center relative"
                    style={{
                      color: '#2a1a0f',
                      fontFamily: 'Georgia, serif',
                      fontWeight: 700,
                      letterSpacing: '0.22em',
                      textShadow: '1px 1px 0 rgba(255,220,180,0.2)',
                    }}
                  >
                    MYSTERIES
                  </h1>
                  <div className="mx-auto my-2" style={{ width: '50%', height: '1px', background: 'linear-gradient(90deg, transparent, rgba(42,26,15,0.4) 25%, rgba(42,26,15,0.4) 75%, transparent)' }} />
                  <p
                    className="text-sm text-center tracking-widest uppercase relative"
                    style={{
                      color: '#3d2816',
                      fontFamily: 'Georgia, serif',
                      fontWeight: 700,
                      letterSpacing: '0.28em',
                      textShadow: '1px 1px 0 rgba(255,220,180,0.12)',
                    }}
                  >
                    of Vapor & Mist
                  </p>
                </div>
              </div>

              {content.map((section, i) => (
                <div
                  key={i}
                  className="mb-6"
                  style={{
                    opacity: Math.min(1, Math.max(0, (revealProgress - i * 0.05) * 1.8)),
                    transform: `translateY(${Math.max(0, (1 - revealProgress) * 15)}px)`,
                    transition: `all 0.5s ease-out ${i * 0.04}s`,
                  }}
                >
                  <h2
                    style={{
                      color: '#3d2815',
                      fontFamily: 'Georgia, serif',
                      fontSize: '1.1rem',
                      fontWeight: 700,
                      marginBottom: '0.4rem',
                      textShadow: '0 1px 1px rgba(210,190,165,0.35)',
                      borderBottom: '1px solid rgba(61,40,21,0.2)',
                      paddingBottom: '0.35rem',
                    }}
                  >
                    {section.title}
                  </h2>
                  <p
                    style={{
                      color: '#2d1c10',
                      fontFamily: 'Georgia, serif',
                      fontSize: '0.92rem',
                      fontWeight: 700,
                      lineHeight: 1.8,
                      textShadow: '0 1px 1px rgba(210,190,165,0.25)',
                    }}
                  >
                    {section.text}
                  </p>
                </div>
              ))}
              <div className="h-32" />
            </div>
          </div>
        </div>
      )}

      <canvas ref={edgeCanvasRef} className="absolute inset-0 pointer-events-none" style={{ position: 'absolute', top: 0, left: 0, right: 0, bottom: 0, zIndex: 4 }} />
      <canvas ref={sideCanvasRef} className="absolute inset-0 pointer-events-none" style={{ position: 'absolute', top: 0, left: 0, right: 0, bottom: 0, zIndex: 3.5 }} />
      <canvas ref={coverCanvasRef} className="absolute inset-0 pointer-events-none" style={{ position: 'absolute', top: 0, left: 0, right: 0, bottom: 0, zIndex: 5 }} />

      {!isStarted && (
        <div style={{
          position: 'absolute',
          inset: 0,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 10002
        }}>
          <button
            onClick={startAnimation}
            style={{
              padding: '20px 40px',
              fontSize: '18px',
              letterSpacing: '0.05em',
              background: 'linear-gradient(145deg, #a08060, #705030)',
              color: '#f5efe5',
              borderRadius: '8px',
              boxShadow: '0 8px 32px rgba(0,0,0,0.45)',
              border: 'none',
              fontFamily: 'Georgia, serif',
              fontWeight: 700,
              cursor: 'pointer',
              transition: 'transform 0.2s',
            }}
            onMouseEnter={(e) => e.currentTarget.style.transform = 'scale(1.05)'}
            onMouseLeave={(e) => e.currentTarget.style.transform = 'scale(1)'}
            onMouseDown={(e) => e.currentTarget.style.transform = 'scale(0.95)'}
            onMouseUp={(e) => e.currentTarget.style.transform = 'scale(1.05)'}
          >
            ☰ Open Menu
          </button>
        </div>
      )}

      {isStarted && phaseRef.current >= 4 && (
        <button
          onClick={resetAnimation}
          className="absolute bottom-4 right-4 px-4 py-2 text-sm rounded-lg"
          style={{
            zIndex: 10,
            background: 'rgba(60,40,25,0.35)',
            color: 'rgba(210,190,165,0.65)',
            border: '1px solid rgba(210,190,165,0.15)',
            fontWeight: 600,
          }}
        >
          ↺ Reset
        </button>
      )}
    </div>
  );
};

export default SteamAnimation;
