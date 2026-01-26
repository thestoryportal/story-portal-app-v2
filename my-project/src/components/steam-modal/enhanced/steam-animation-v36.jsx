import React, { useEffect, useRef, useState, useCallback } from 'react';
import { createNoise3D } from 'simplex-noise';

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

  // Debug logging for showContent state changes
  useEffect(() => {
    console.log('[v36] showContent changed to:', showContent);
  }, [showContent]);

  useEffect(() => {
    console.log('[v36] revealProgress changed to:', revealProgress);
  }, [revealProgress]);

  // v36: Noise for turbulent flow
  const noiseRef = useRef(null);

  // v36: Texture system
  const texturesRef = useRef([]);
  const texturesLoadedRef = useRef(false);

  // v36: Object pooling
  const particlePoolRef = useRef([]);
  const MAX_POOL_SIZE = 2000;

  // v36: Guard to prevent multiple simultaneous startAnimation calls
  const isStartingRef = useRef(false);

  // v36: Refs for callbacks to make animate function stable
  const createBaseParticleRef = useRef(null);
  const createOuterParticleRef = useRef(null);
  const createEdgeParticleRef = useRef(null);
  const createCoverParticleRef = useRef(null);
  const createSideParticleRef = useRef(null);
  const updateBaseParticlesRef = useRef(null);
  const updateOuterParticlesRef = useRef(null);
  const updateEdgeParticlesRef = useRef(null);
  const updateSideParticlesRef = useRef(null);
  const updateCoverParticlesRef = useRef(null);
  const getVisibleContentBoundsRef = useRef(null);
  const renderGlowPassRef = useRef(null);

  // Container bounds (where scroll container lives)
  const getContentBounds = useCallback((canvas) => {
    const top = 15;
    const height = canvas.height - 45;
    return { top, bottom: top + height, height, centerY: canvas.height / 2 };
  }, []);

  // Visible content bounds with 15px top, 30px bottom margin
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

  // v36: Perlin noise flow field (replaces getWaft)
  const getNoiseFlow = useCallback((x, y, time) => {
    if (!noiseRef.current) return { x: 0, y: 0 };

    const scale = 0.003; // Noise frequency
    const timeScale = 0.0001;
    const t = time * timeScale;
    const noise3D = noiseRef.current;

    return {
      x: noise3D(x * scale, y * scale, t) * 8,
      y: noise3D(x * scale + 1000, y * scale, t) * 8 - 0.5 // Slight upward bias
    };
  }, []);

  const getColor = useCallback(() => {
    const colors = [
      { r: 212, g: 192, b: 168 },
      { r: 205, g: 185, b: 158 },
      { r: 198, g: 178, b: 152 },
      { r: 218, g: 200, b: 175 },
    ];
    return colors[Math.floor(Math.random() * colors.length)];
  }, []);

  // v36: Fallback texture generator - creates high-opacity smoke textures
  // NOTE: These textures need HIGH alpha because they get MULTIPLIED
  // by particle.opacity during rendering. Low texture alpha = invisible particles!
  const createFallbackTexture = useCallback((type) => {
    const canvas = document.createElement('canvas');
    canvas.width = 512;
    canvas.height = 512;
    const ctx = canvas.getContext('2d');

    const centerX = 256;
    const centerY = 256;

    // Create procedural smoke-like pattern with HIGH opacity
    for (let i = 0; i < 120; i++) {
      const angle = Math.random() * Math.PI * 2;
      const dist = Math.random() * 200;
      const x = centerX + Math.cos(angle) * dist;
      const y = centerY + Math.sin(angle) * dist;
      const size = 30 + Math.random() * 60;
      // HIGH alpha (0.6-1.0) - critical for visibility when multiplied by particle.opacity
      const alpha = 0.6 + Math.random() * 0.4;

      const gradient = ctx.createRadialGradient(x, y, 0, x, y, size);
      gradient.addColorStop(0, `rgba(230, 215, 195, ${alpha})`);
      gradient.addColorStop(0.5, `rgba(220, 200, 180, ${alpha * 0.6})`);
      gradient.addColorStop(1, 'rgba(210, 190, 170, 0)');

      ctx.fillStyle = gradient;
      ctx.fillRect(x - size, y - size, size * 2, size * 2);
    }

    // Add bright center core for visibility
    const coreGradient = ctx.createRadialGradient(centerX, centerY, 0, centerX, centerY, 180);
    coreGradient.addColorStop(0, 'rgba(245, 235, 220, 0.95)');
    coreGradient.addColorStop(0.3, 'rgba(235, 220, 200, 0.7)');
    coreGradient.addColorStop(0.6, 'rgba(225, 205, 185, 0.4)');
    coreGradient.addColorStop(1, 'rgba(215, 195, 175, 0)');

    ctx.fillStyle = coreGradient;
    ctx.fillRect(centerX - 180, centerY - 180, 360, 360);

    // Gentle blur for organic look
    ctx.filter = 'blur(12px)';
    ctx.drawImage(canvas, 0, 0);
    ctx.filter = 'none';

    return canvas;
  }, []);

  // v36: Object pooling
  const acquireParticle = useCallback(() => {
    if (particlePoolRef.current.length > 0) {
      return particlePoolRef.current.pop();
    }
    // Create new particle object structure
    return {
      x: 0, y: 0, vx: 0, vy: 0, size: 0, opacity: 0,
      rotation: 0, rotationSpeed: 0, scaleStart: 1, scaleEnd: 1,
      currentScale: 1, depth: 0.5, textureIndex: 0,
      age: 0, maxAge: 0, active: false, targetOpacity: 0,
      seed: 0, waftStrength: 0, driftX: 0, driftY: 0,
      blowStrength: 0, blowAngle: 0, turbulence: 0,
      side: null, zone: null, layer: 'mid', color: { r: 210, g: 190, b: 165 }
    };
  }, []);

  const releaseParticle = useCallback((particle) => {
    if (particlePoolRef.current.length < MAX_POOL_SIZE) {
      particle.active = false;
      particlePoolRef.current.push(particle);
    }
  }, []);

  // Get side margin/padding areas for active wispy steam
  const getSideMarginBounds = useCallback((canvas) => {
    const bounds = getContentBounds(canvas);
    const contentMaxWidth = 576; // max-w-xl
    const contentPadding = 20; // px-5
    const centerX = canvas.width / 2;
    const halfContent = Math.min(contentMaxWidth / 2, canvas.width / 2 - contentPadding);

    return {
      left: { x1: 0, x2: centerX - halfContent + contentPadding * 2 },
      right: { x1: centerX + halfContent - contentPadding * 2, x2: canvas.width },
      top: bounds.top,
      bottom: bounds.bottom
    };
  }, [getContentBounds]);

  // v36: Enhanced side margin particle with new properties
  const createSideParticle = useCallback((canvas, side) => {
    const particle = acquireParticle();
    const margins = getSideMarginBounds(canvas);
    const bounds = getContentBounds(canvas);
    const size = 35 + Math.random() * 50;

    let x;
    if (side === 'left') {
      x = margins.left.x1 + Math.random() * (margins.left.x2 - margins.left.x1);
    } else {
      x = margins.right.x1 + Math.random() * (margins.right.x2 - margins.right.x1);
    }

    // Set all properties
    particle.x = x;
    particle.y = bounds.bottom + Math.random() * 50;
    particle.size = size;
    particle.opacity = 0;
    particle.targetOpacity = 0.12 + Math.random() * 0.08;
    particle.seed = Math.random() * 10000;
    particle.waftStrength = 4 + Math.random() * 5;
    particle.driftX = (Math.random() - 0.5) * 2.5;
    particle.driftY = -1.2 - Math.random() * 1.5;
    particle.blowStrength = 1.5 + Math.random() * 2.5;
    particle.blowAngle = Math.random() * Math.PI * 2;
    particle.turbulence = 2 + Math.random() * 2.5;
    particle.side = side;
    particle.age = 0;
    particle.maxAge = 250 + Math.random() * 150;
    particle.color = getColor();
    particle.active = true;

    // v36: New properties
    particle.rotation = Math.random() * Math.PI * 2;
    particle.rotationSpeed = (Math.random() - 0.5) * 0.03;
    particle.scaleStart = 0.7 + Math.random() * 0.3;
    particle.scaleEnd = 1.2 + Math.random() * 0.4;
    particle.currentScale = particle.scaleStart;
    particle.depth = Math.random();
    particle.textureIndex = Math.floor(Math.random() * 6);
    particle.vx = 0;
    particle.vy = 0;

    return particle;
  }, [acquireParticle, getSideMarginBounds, getContentBounds, getColor]);

  // v36: Enhanced base particle with new properties
  const createBaseParticle = useCallback((canvas) => {
    const particle = acquireParticle();
    const bounds = getContentBounds(canvas);

    particle.x = 10 + Math.random() * (canvas.width - 20);
    particle.y = bounds.top + 5 + Math.random() * (bounds.height - 10);
    particle.size = 75 + Math.random() * 100;
    particle.opacity = 0;
    particle.targetOpacity = 0.42 + Math.random() * 0.2;
    particle.seed = Math.random() * 10000;
    particle.waftStrength = 0.12 + Math.random() * 0.1;
    particle.age = 0;
    particle.maxAge = 1400 + Math.random() * 1000;
    particle.color = getColor();
    particle.active = true;

    // v36: New properties
    particle.rotation = Math.random() * Math.PI * 2;
    particle.rotationSpeed = (Math.random() - 0.5) * 0.01; // Slow rotation
    particle.scaleStart = 0.8 + Math.random() * 0.2;
    particle.scaleEnd = 1.1 + Math.random() * 0.3;
    particle.currentScale = particle.scaleStart;
    particle.depth = Math.random();
    particle.textureIndex = Math.floor(Math.random() * 6);
    particle.vx = 0;
    particle.vy = 0;

    return particle;
  }, [acquireParticle, getContentBounds, getColor]);

  // v36: Enhanced outer particle with new properties
  const createOuterParticle = useCallback((canvas) => {
    const particle = acquireParticle();
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

    particle.x = x;
    particle.y = y;
    particle.size = 35 + Math.random() * 55;
    particle.opacity = 0;
    particle.targetOpacity = 0.22 + Math.random() * 0.08;
    particle.seed = Math.random() * 10000;
    particle.waftStrength = 3 + Math.random() * 4;
    particle.driftX = (Math.random() - 0.5) * 1.5;
    particle.driftY = (Math.random() - 0.5) * 0.8 - 0.15;
    particle.blowStrength = Math.random() * 2;
    particle.blowAngle = Math.random() * Math.PI * 2;
    particle.turbulence = 0.8 + Math.random() * 1.2;
    particle.age = 0;
    particle.maxAge = 200 + Math.random() * 200;
    particle.color = getColor();
    particle.active = true;

    // v36: New properties
    particle.rotation = Math.random() * Math.PI * 2;
    particle.rotationSpeed = (Math.random() - 0.5) * 0.025; // Faster rotation
    particle.scaleStart = 0.7 + Math.random() * 0.3;
    particle.scaleEnd = 1.2 + Math.random() * 0.4;
    particle.currentScale = particle.scaleStart;
    particle.depth = Math.random();
    particle.textureIndex = Math.floor(Math.random() * 6);
    particle.vx = 0;
    particle.vy = 0;

    return particle;
  }, [acquireParticle, getContentBounds, getColor]);

  // v36: Enhanced edge particle with new properties
  const createEdgeParticle = useCallback((canvas, zone, forceX = null) => {
    const particle = acquireParticle();
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

    particle.x = x;
    particle.y = y;
    particle.size = size;
    particle.opacity = 0;
    particle.targetOpacity = 0.58 + Math.random() * 0.17;
    particle.seed = Math.random() * 10000;
    particle.waftStrength = 0.5 + Math.random() * 0.6;
    particle.driftX = (Math.random() - 0.5) * 0.25;
    particle.driftY = (Math.random() - 0.5) * 0.1;
    particle.blowStrength = Math.random() * 0.2;
    particle.blowAngle = Math.random() * Math.PI * 2;
    particle.turbulence = 0.15 + Math.random() * 0.2;
    particle.zone = zone;
    particle.age = 0;
    particle.maxAge = 600 + Math.random() * 400;
    particle.color = getColor();
    particle.active = true;

    // v36: New properties
    particle.rotation = Math.random() * Math.PI * 2;
    particle.rotationSpeed = (Math.random() - 0.5) * 0.01; // Slow rotation
    particle.scaleStart = 0.9 + Math.random() * 0.2;
    particle.scaleEnd = 1.0 + Math.random() * 0.2;
    particle.currentScale = particle.scaleStart;
    particle.depth = Math.random();
    particle.textureIndex = Math.floor(Math.random() * 6);
    particle.vx = 0;
    particle.vy = 0;

    return particle;
  }, [acquireParticle, getVisibleContentBounds, getColor]);

  // v36: Enhanced cover particle with new properties
  const createCoverParticle = useCallback((canvas, phase, forcePos = null, fillProgress = 0) => {
    const particle = acquireParticle();
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

    particle.x = x;
    particle.y = y;
    particle.vx = vx;
    particle.vy = vy;
    particle.size = size;
    particle.opacity = 0;
    particle.targetOpacity = phase === 'burst' ? 0.5 : phase === 'gush' ? 0.45 + Math.random() * 0.15 : 0.15;
    particle.seed = Math.random() * 10000;
    particle.waftStrength = 2 + Math.random() * 3;
    particle.driftX = (Math.random() - 0.5) * 1.0;
    particle.driftY = (Math.random() - 0.5) * 0.6;
    particle.blowStrength = Math.random() * 1.5;
    particle.blowAngle = Math.random() * Math.PI * 2;
    particle.turbulence = 0.6 + Math.random() * 1;
    particle.age = 0;
    particle.maxAge = phase === 'burst' ? 120 + Math.random() * 80 : phase === 'gush' ? 180 + Math.random() * 120 : 100 + Math.random() * 60;
    particle.layer = Math.random() < 0.3 ? 'back' : Math.random() < 0.7 ? 'mid' : 'front';
    particle.color = getColor();
    particle.active = true;

    // v36: New properties
    particle.rotation = Math.random() * Math.PI * 2;
    particle.rotationSpeed = (Math.random() - 0.5) * 0.03; // Fastest rotation
    particle.scaleStart = 0.6 + Math.random() * 0.3;
    particle.scaleEnd = 1.3 + Math.random() * 0.5;
    particle.currentScale = particle.scaleStart;
    particle.depth = Math.random();
    particle.textureIndex = Math.floor(Math.random() * 6);

    return particle;
  }, [acquireParticle, getColor]);

  // v36: New texture-based particle rendering
  const renderParticle = useCallback((ctx, particle) => {
    if (!particle.active || particle.opacity < 0.003) return;
    if (!texturesLoadedRef.current) return;

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

  // v36: Glow pass for atmospheric light scattering
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

  // v36: Enhanced base particles update with noise flow
  const updateBaseParticles = useCallback((ctx, canvas, time, phase) => {
    const bounds = getContentBounds(canvas);
    const deltaTime = 16; // Assuming 60fps

    baseParticlesRef.current = baseParticlesRef.current.filter(p => {
      if (!p.active) return false;

      p.age++;

      // v36: Use noise flow instead of waft
      const flow = getNoiseFlow(p.x, p.y, time);
      const parallax = 0.5 + p.depth * 0.5; // Depth affects movement
      p.vx = flow.x * parallax * 0.1;
      p.vy = flow.y * parallax * 0.1;
      p.x += p.vx * deltaTime * 0.016;
      p.y += p.vy * deltaTime * 0.016;

      // v36: Update rotation and scale
      p.rotation += p.rotationSpeed;
      const lifeFraction = p.age / p.maxAge;
      p.currentScale = p.scaleStart + (p.scaleEnd - p.scaleStart) * lifeFraction;

      if (p.y < bounds.top + 15) p.y += 0.15;
      if (p.y > bounds.bottom - 15) p.y -= 0.15;
      if (p.x < 20) p.x += 0.15;
      if (p.x > canvas.width - 20) p.x -= 0.15;

      const ageRatio = p.age / p.maxAge;
      if (phase >= 3) {
        p.opacity += (p.targetOpacity - p.opacity) * 0.05;
      } else if (ageRatio < 0.1) {
        p.opacity += (p.targetOpacity - p.opacity) * 0.025;
      }
      if (ageRatio > 0.92) p.opacity *= 0.996;

      const shouldKeep = p.opacity > 0.008 && p.age < p.maxAge;
      if (!shouldKeep) {
        releaseParticle(p);
      }
      return shouldKeep;
    });

    // v36: Sort by depth and render
    baseParticlesRef.current.sort((a, b) => a.depth - b.depth);
    baseParticlesRef.current.forEach(p => renderParticle(ctx, p));
  }, [getContentBounds, getNoiseFlow, renderParticle, releaseParticle]);

  // v36: Enhanced outer particles update with noise flow
  const updateOuterParticles = useCallback((ctx, canvas, time) => {
    const bounds = getContentBounds(canvas);
    const deltaTime = 16;

    outerParticlesRef.current = outerParticlesRef.current.filter(p => {
      if (!p.active) return false;

      p.age++;

      // v36: Use noise flow
      const flow = getNoiseFlow(p.x, p.y, time);
      const parallax = 0.5 + p.depth * 0.5;

      if (Math.random() < 0.03) {
        p.blowAngle += (Math.random() - 0.5) * 1.5;
        p.blowStrength = 0.5 + Math.random() * 2.5;
      }

      const turbX = (Math.random() - 0.5) * p.turbulence * 0.5;
      const turbY = (Math.random() - 0.5) * p.turbulence * 0.4;

      p.vx = flow.x * parallax * 0.15;
      p.vy = flow.y * parallax * 0.12;
      p.x += p.vx + p.driftX + Math.cos(p.blowAngle) * p.blowStrength * 0.3 + turbX;
      p.y += p.vy + p.driftY + Math.sin(p.blowAngle) * p.blowStrength * 0.2 + turbY;

      // v36: Update rotation and scale
      p.rotation += p.rotationSpeed;
      const lifeFraction = p.age / p.maxAge;
      p.currentScale = p.scaleStart + (p.scaleEnd - p.scaleStart) * lifeFraction;

      p.driftX += (Math.random() - 0.5) * 0.08;
      p.driftY += (Math.random() - 0.5) * 0.05;
      p.driftX *= 0.98;
      p.driftY *= 0.98;
      p.blowStrength *= 0.96;

      if (p.y > bounds.top - 15 && p.y < bounds.bottom + 15) {
        if (p.y < bounds.centerY) {
          p.y -= 1.2;
          p.driftY -= 0.1;
        } else {
          p.y += 1.2;
          p.driftY += 0.1;
        }
      }

      if (p.x < -p.size) p.x = canvas.width + p.size * 0.5;
      if (p.x > canvas.width + p.size) p.x = -p.size * 0.5;
      if (p.y < -p.size * 0.5) p.y = -p.size * 0.5 + 3;
      if (p.y > canvas.height + p.size * 0.5) p.y = canvas.height + p.size * 0.5 - 3;

      const ageRatio = p.age / p.maxAge;
      if (ageRatio < 0.1) {
        p.opacity += (p.targetOpacity - p.opacity) * 0.04;
      } else if (ageRatio > 0.7) {
        p.opacity *= 0.985;
      }

      const shouldKeep = p.opacity > 0.005 && p.age < p.maxAge;
      if (!shouldKeep) {
        releaseParticle(p);
      }
      return shouldKeep;
    });

    // v36: Sort by depth and render
    outerParticlesRef.current.sort((a, b) => a.depth - b.depth);
    outerParticlesRef.current.forEach(p => renderParticle(ctx, p));
  }, [getContentBounds, getNoiseFlow, renderParticle, releaseParticle]);

  // v36: Enhanced edge particles update with noise flow
  const updateEdgeParticles = useCallback((ctx, canvas, time) => {
    const bounds = getVisibleContentBounds(canvas);
    const deltaTime = 16;

    edgeParticlesRef.current = edgeParticlesRef.current.filter(p => {
      if (!p.active) return false;

      p.age++;

      // v36: Use noise flow
      const flow = getNoiseFlow(p.x, p.y, time);
      const parallax = 0.5 + p.depth * 0.5;

      if (Math.random() < 0.01) {
        p.blowAngle += (Math.random() - 0.5) * 0.5;
        p.blowStrength = 0.05 + Math.random() * 0.2;
      }

      const turbX = (Math.random() - 0.5) * p.turbulence * 0.1;
      const turbY = (Math.random() - 0.5) * p.turbulence * 0.05;

      p.vx = flow.x * parallax * 0.05;
      p.vy = flow.y * parallax * 0.04;
      p.x += p.vx + p.driftX * 0.3 + Math.cos(p.blowAngle) * p.blowStrength * 0.05 + turbX;
      p.y += p.vy + p.driftY * 0.2 + Math.sin(p.blowAngle) * p.blowStrength * 0.03 + turbY;

      // v36: Update rotation and scale
      p.rotation += p.rotationSpeed;
      const lifeFraction = Math.min(p.age / p.maxAge, 1);
      p.currentScale = p.scaleStart + (p.scaleEnd - p.scaleStart) * lifeFraction;

      p.driftX += (Math.random() - 0.5) * 0.015;
      p.driftY += (Math.random() - 0.5) * 0.01;
      p.driftX *= 0.995;
      p.driftY *= 0.995;
      p.blowStrength *= 0.98;

      if (p.zone === 'top') {
        if (p.y > bounds.top - 5) p.y = bounds.top - 5 - Math.random() * 10;
        if (p.y < -p.size * 0.4) p.y = -p.size * 0.4 + 2;
      } else {
        if (p.y < bounds.bottom + 5) p.y = bounds.bottom + 5 + Math.random() * 10;
        if (p.y > canvas.height + p.size * 0.4) p.y = canvas.height + p.size * 0.4 - 2;
      }

      if (p.x < -p.size * 0.4) p.x = canvas.width + p.size * 0.2;
      if (p.x > canvas.width + p.size * 0.4) p.x = -p.size * 0.2;

      // Fixed state - instant full opacity, no fade out
      if (p.opacity < p.targetOpacity) {
        p.opacity = p.targetOpacity;
      }

      return true; // Particles persist permanently
    });

    // v36: Sort by depth and render
    edgeParticlesRef.current.sort((a, b) => a.depth - b.depth);
    edgeParticlesRef.current.forEach(p => renderParticle(ctx, p));
  }, [getVisibleContentBounds, getNoiseFlow, renderParticle]);

  // v36: Enhanced side particles update with noise flow
  const updateSideParticles = useCallback((ctx, canvas, time) => {
    const bounds = getContentBounds(canvas);
    const margins = getSideMarginBounds(canvas);
    const deltaTime = 16;

    sideParticlesRef.current = sideParticlesRef.current.filter(p => {
      if (!p.active) return false;

      p.age++;

      // v36: Use noise flow
      const flow = getNoiseFlow(p.x, p.y, time);
      const parallax = 0.5 + p.depth * 0.5;

      if (Math.random() < 0.1) {
        p.blowAngle += (Math.random() - 0.5) * 2.5;
        p.blowStrength = 1.5 + Math.random() * 3;
      }

      const turbX = (Math.random() - 0.5) * p.turbulence;
      const turbY = (Math.random() - 0.5) * p.turbulence * 0.5;

      p.vx = flow.x * parallax * 0.25;
      p.vy = flow.y * parallax * 0.2;
      p.x += p.vx + p.driftX * 0.6 + Math.cos(p.blowAngle) * p.blowStrength * 0.5 + turbX;
      p.y += p.vy + p.driftY + Math.sin(p.blowAngle) * p.blowStrength * 0.3 + turbY;

      // v36: Update rotation and scale
      p.rotation += p.rotationSpeed;
      const lifeFraction = p.age / p.maxAge;
      p.currentScale = p.scaleStart + (p.scaleEnd - p.scaleStart) * lifeFraction;

      p.driftX += (Math.random() - 0.5) * 0.2;
      p.driftY += (Math.random() - 0.5) * 0.1 - 0.03;
      p.driftX *= 0.96;
      p.driftY *= 0.97;
      p.blowStrength *= 0.92;

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

      if (p.y < bounds.top - p.size) {
        p.y = bounds.bottom + p.size * 0.5;
        p.opacity = 0;
      }

      const ageRatio = p.age / p.maxAge;
      if (ageRatio < 0.12) {
        p.opacity += (p.targetOpacity - p.opacity) * 0.1;
      } else if (ageRatio > 0.7) {
        p.opacity *= 0.96;
      }

      const shouldKeep = p.opacity > 0.003 && p.age < p.maxAge;
      if (!shouldKeep) {
        releaseParticle(p);
      }
      return shouldKeep;
    });

    // v36: Sort by depth and render
    sideParticlesRef.current.sort((a, b) => a.depth - b.depth);
    sideParticlesRef.current.forEach(p => renderParticle(ctx, p));
  }, [getContentBounds, getSideMarginBounds, getNoiseFlow, renderParticle, releaseParticle]);

  // v36: Enhanced cover particles update with noise flow
  const updateCoverParticles = useCallback((ctx, canvas, time, phase, revealProg) => {
    const centerX = canvas.width / 2;
    const centerY = canvas.height / 2;
    const deltaTime = 16;

    coverParticlesRef.current = coverParticlesRef.current.filter(p => {
      if (!p.active) return false;

      p.age++;
      const dx = p.x - centerX;
      const dy = p.y - centerY;

      if (phase >= 3) {
        const blowAngle = Math.atan2(dy, dx);
        const blowForce = (0.8 + revealProg * 2.5) * 0.18;
        p.vx += Math.cos(blowAngle) * blowForce + (Math.random() - 0.5) * 0.3;
        p.vy += Math.sin(blowAngle) * blowForce + (Math.random() - 0.5) * 0.3;
        p.targetOpacity *= 0.85;
        p.opacity *= 0.97;
      }

      const waftMult = phase < 3 ? 0.3 : 0.8;
      // v36: Use noise flow
      const flow = getNoiseFlow(p.x, p.y, time);
      const parallax = 0.5 + p.depth * 0.5;

      const turbX = phase < 3 ? (Math.random() - 0.5) * (p.turbulence || 0.8) * 0.35 : 0;
      const turbY = phase < 3 ? (Math.random() - 0.5) * (p.turbulence || 0.8) * 0.3 : 0;

      p.vx += flow.x * parallax * 0.08 + turbX;
      p.vy += flow.y * parallax * 0.06 + turbY - 0.008;

      p.x += p.vx;
      p.y += p.vy;
      p.vx *= phase < 3 ? 0.99 : 0.96;
      p.vy *= phase < 3 ? 0.99 : 0.96;
      p.size += phase < 3 ? 0.2 : 0.08;

      // v36: Update rotation and scale
      p.rotation += p.rotationSpeed;
      const lifeFraction = p.age / p.maxAge;
      p.currentScale = p.scaleStart + (p.scaleEnd - p.scaleStart) * lifeFraction;

      const ageRatio = p.age / p.maxAge;
      if (phase < 3 && ageRatio < 0.15) {
        p.opacity += (p.targetOpacity - p.opacity) * 0.08;
      } else if (phase < 3 && ageRatio > 0.7) {
        p.opacity *= 0.98;
      }

      const minOpacity = phase >= 4 ? 0.01 : 0.003;
      const shouldKeep = p.opacity > minOpacity && p.age < p.maxAge;
      if (!shouldKeep) {
        releaseParticle(p);
      }
      return shouldKeep;
    });

    // v36: Sort by depth within layers
    const layers = { back: [], mid: [], front: [] };
    coverParticlesRef.current.forEach(p => layers[p.layer].push(p));

    ['back', 'mid', 'front'].forEach(layer => {
      layers[layer].sort((a, b) => a.depth - b.depth);
      layers[layer].forEach(p => renderParticle(ctx, p));
    });
  }, [getNoiseFlow, renderParticle, releaseParticle]);

  // Update callback refs whenever callbacks change
  useEffect(() => {
    createBaseParticleRef.current = createBaseParticle;
    createOuterParticleRef.current = createOuterParticle;
    createEdgeParticleRef.current = createEdgeParticle;
    createCoverParticleRef.current = createCoverParticle;
    createSideParticleRef.current = createSideParticle;
    updateBaseParticlesRef.current = updateBaseParticles;
    updateOuterParticlesRef.current = updateOuterParticles;
    updateEdgeParticlesRef.current = updateEdgeParticles;
    updateSideParticlesRef.current = updateSideParticles;
    updateCoverParticlesRef.current = updateCoverParticles;
    getVisibleContentBoundsRef.current = getVisibleContentBounds;
    renderGlowPassRef.current = renderGlowPass;
  }, [createBaseParticle, createOuterParticle, createEdgeParticle, createCoverParticle, createSideParticle,
      updateBaseParticles, updateOuterParticles, updateEdgeParticles, updateSideParticles, updateCoverParticles,
      getVisibleContentBounds, renderGlowPass]);

  const animate = useCallback((timestamp) => {
    if (!startTimeRef.current) startTimeRef.current = timestamp;
    const elapsed = timestamp - startTimeRef.current;

    // Log elapsed time every 500ms to track progression
    if (Math.floor(elapsed / 500) !== Math.floor((elapsed - 16) / 500)) {
      console.log('[v36] ELAPSED TIME:', Math.floor(elapsed), 'ms');
    }

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

    if (!baseCtx || !outerCtx || !edgeCtx || !coverCtx || !sideCtx) {
      console.log('[v36] animate: missing context, aborting');
      return;
    }

    // Use refs to access latest callback versions
    const createBaseParticle = createBaseParticleRef.current;
    const createOuterParticle = createOuterParticleRef.current;
    const createEdgeParticle = createEdgeParticleRef.current;
    const createCoverParticle = createCoverParticleRef.current;
    const createSideParticle = createSideParticleRef.current;
    const updateBaseParticles = updateBaseParticlesRef.current;
    const updateOuterParticles = updateOuterParticlesRef.current;
    const updateEdgeParticles = updateEdgeParticlesRef.current;
    const updateSideParticles = updateSideParticlesRef.current;
    const updateCoverParticles = updateCoverParticlesRef.current;
    const getVisibleContentBounds = getVisibleContentBoundsRef.current;
    const renderGlowPass = renderGlowPassRef.current;

    let currentPhase = phaseRef.current;
    let currentReveal = 0;

    if (elapsed < 500) {
      currentPhase = 1;
      if (phaseRef.current !== 1) {
        console.log('[v36] *** PHASE TRANSITION to 1 (BURST) ***');
        phaseRef.current = 1;
      }
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
      if (phaseRef.current !== 2) {
        console.log('[v36] *** PHASE TRANSITION to 2 (GUSH) ***');
        phaseRef.current = 2;
      }
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
      if (phaseRef.current !== 3) {
        console.log('[v36] *** PHASE TRANSITION to 3 (REVEAL) *** elapsed:', elapsed);
        phaseRef.current = 3;
      }
      currentReveal = (elapsed - 2800) / 2500;
      console.log('[v36] Phase 3 REVEAL! currentReveal:', currentReveal, 'setting showContent to true');
      setRevealProgress(currentReveal);
      setShowContent(true);

      // Spawn mature state with enhanced top softening
      if (elapsed < 2850 && edgeParticlesRef.current.length < 305) {
        const width = edgeCanvas.width;
        // Layer 1 - base coverage
        for (let i = 0; i < 40; i++) {
          const xPos = (i / 40) * width + (Math.random() - 0.5) * (width / 20);

          const topP = createEdgeParticle(edgeCanvas, 'top', xPos);
          topP.opacity = topP.targetOpacity;
          edgeParticlesRef.current.push(topP);

          const bottomP = createEdgeParticle(edgeCanvas, 'bottom', xPos);
          bottomP.opacity = bottomP.targetOpacity;
          edgeParticlesRef.current.push(bottomP);
        }
        // Layer 2 - offset fill
        for (let i = 0; i < 40; i++) {
          const xPos = ((i + 0.5) / 40) * width + (Math.random() - 0.5) * (width / 20);

          const topP = createEdgeParticle(edgeCanvas, 'top', xPos);
          topP.opacity = topP.targetOpacity;
          edgeParticlesRef.current.push(topP);

          const bottomP = createEdgeParticle(edgeCanvas, 'bottom', xPos);
          bottomP.opacity = bottomP.targetOpacity;
          edgeParticlesRef.current.push(bottomP);
        }
        // Layer 3 - additional density with random placement
        for (let i = 0; i < 40; i++) {
          const xPos = Math.random() * width;

          const topP = createEdgeParticle(edgeCanvas, 'top', xPos);
          topP.opacity = topP.targetOpacity;
          edgeParticlesRef.current.push(topP);

          const bottomP = createEdgeParticle(edgeCanvas, 'bottom', xPos);
          bottomP.opacity = bottomP.targetOpacity;
          edgeParticlesRef.current.push(bottomP);
        }
        // Boundary softening layer
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
        // Extra top softening
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
      if (phaseRef.current !== 4) {
        console.log('[v36] *** PHASE TRANSITION to 4 (MATURE) *** elapsed:', elapsed);
        phaseRef.current = 4;
      }
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

    baseCtx.clearRect(0, 0, baseCanvas.width, baseCanvas.height);
    outerCtx.clearRect(0, 0, outerCanvas.width, outerCanvas.height);
    edgeCtx.clearRect(0, 0, edgeCanvas.width, edgeCanvas.height);
    coverCtx.clearRect(0, 0, coverCanvas.width, coverCanvas.height);
    sideCtx.clearRect(0, 0, sideCanvas.width, sideCanvas.height);

    baseCtx.fillStyle = '#1c1814';
    baseCtx.fillRect(0, 0, baseCanvas.width, baseCanvas.height);

    updateBaseParticles(baseCtx, baseCanvas, elapsed, currentPhase);
    updateOuterParticles(outerCtx, outerCanvas, elapsed);
    updateEdgeParticles(edgeCtx, edgeCanvas, elapsed);
    updateSideParticles(sideCtx, sideCanvas, elapsed);
    updateCoverParticles(coverCtx, coverCanvas, elapsed, currentPhase, currentReveal);

    // v36: Add glow pass for atmospheric light scattering
    if (texturesLoadedRef.current) {
      const allParticles = [
        ...baseParticlesRef.current,
        ...outerParticlesRef.current,
        ...edgeParticlesRef.current,
        ...coverParticlesRef.current
      ].filter(p => p.active);

      renderGlowPass(coverCtx, allParticles, coverCanvas);
    }

    animationRef.current = requestAnimationFrame(animate);
  }, []); // Empty deps - function reference stays stable, uses refs for callbacks

  const startAnimation = useCallback(() => {
    // Guard: Don't start if already running (using ref for immediate protection)
    if (isStartingRef.current || animationRef.current) {
      console.log('[v36] startAnimation called but already running, ignoring');
      return;
    }

    isStartingRef.current = true;
    console.log('[v36] startAnimation called! Starting animation...');

    baseParticlesRef.current = [];
    outerParticlesRef.current = [];
    edgeParticlesRef.current = [];
    coverParticlesRef.current = [];
    sideParticlesRef.current = [];
    startTimeRef.current = null;
    phaseRef.current = 0;
    setShowContent(false);
    setRevealProgress(0);

    console.log('[v36] Calling requestAnimationFrame');
    animationRef.current = requestAnimationFrame(animate);
    console.log('[v36] Animation frame requested, ID:', animationRef.current);

    // Set isStarted AFTER scheduling the animation
    setIsStarted(true);
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
    isStartingRef.current = false; // Reset the guard
    setIsStarted(false);
    setShowContent(false);
    setRevealProgress(0);
  }, []);

  // v36: Initialize noise and textures
  useEffect(() => {
    // Initialize simplex noise
    noiseRef.current = createNoise3D();

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
          console.log('v36: Steam textures loaded successfully');
        }
      };
      img.onerror = () => {
        // Create fallback procedural texture
        console.warn(`v36: Texture ${url} failed, using fallback`);
        loadedCount++;
        textures[idx] = createFallbackTexture(idx);
        if (loadedCount === textureUrls.length) {
          texturesRef.current = textures;
          texturesLoadedRef.current = true;
          console.log('v36: Using fallback textures');
        }
      };
      img.src = url;
    });
  }, [createFallbackTexture]);

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

  const content = [
    { title: "The Art of Steam", text: "Steam has captivated humanity since ancient times. From the mysterious mists of sacred groves to the industrial revolution's mighty engines, vapor has always held a special place in our collective imagination." },
    { title: "Origins & History", text: "The earliest recorded use of steam power dates back to Hero of Alexandria in the 1st century AD. His aeolipile demonstrated the potential of harnessing vapor's energy, planting seeds for the industrial age." },
    { title: "The Science Within", text: "When water reaches 100°C at sea level, molecules gain enough kinetic energy to break free. This transition releases tremendous energy—a single gram absorbs 2,260 joules becoming steam." },
    { title: "Cultural Significance", text: "Across cultures, steam symbolizes transformation and liminal spaces. Japanese onsen traditions celebrate healing. Nordic saunas purify. Turkish hammams center social life around vapor." },
    { title: "Modern Applications", text: "Today, steam powers roughly 80% of the world's electricity. It sterilizes medical equipment, processes food safely, and propels aircraft carriers across vast oceans." },
    { title: "The Future of Vapor", text: "As we seek sustainable solutions, steam remains central to geothermal power, concentrated solar plants, and next-generation nuclear reactors. Ancient technology meets modern innovation." },
  ];

  // Debug render logging
  console.log('[v36 RENDER] showContent:', showContent, 'revealProgress:', revealProgress, 'isStarted:', isStarted, 'phase:', phaseRef.current);

  return (
    <div ref={containerRef} style={{ position: 'relative', width: '100%', overflow: 'hidden', background: '#1c1814', height: '100%' }}>
      <canvas ref={baseCanvasRef} style={{ position: 'absolute', inset: 0, zIndex: 1 }} />
      <canvas ref={outerCanvasRef} style={{ position: 'absolute', inset: 0, zIndex: 2 }} />

      {showContent && (
        <div
          style={{
            position: 'absolute',
            left: 0,
            right: 0,
            zIndex: 6,
            top: 15,
            height: 'calc(100% - 45px)',
            border: '3px solid red',
            boxSizing: 'border-box',
            pointerEvents: 'none',
          }}
        />
      )}
      {showContent && (
        <div
          style={{
            position: 'absolute',
            left: 0,
            right: 0,
            zIndex: 3,
            top: 15,
            height: 'calc(100% - 45px)',
            opacity: Math.min(revealProgress * 2, 1),
          }}
        >
          <div
            ref={contentRef}
            style={{
              width: '100%',
              height: '100%',
              overflowY: 'auto',
              overflowX: 'hidden',
              scrollbarWidth: 'none',
              msOverflowStyle: 'none'
            }}
          >
            <style>{`div::-webkit-scrollbar { display: none; }`}</style>

            <div style={{
              maxWidth: '36rem',
              marginLeft: 'auto',
              marginRight: 'auto',
              paddingLeft: '1.25rem',
              paddingRight: '1.25rem',
              paddingTop: '3rem',
              paddingBottom: '3rem'
            }}>
              <div
                style={{
                  position: 'relative',
                  marginLeft: 'auto',
                  marginRight: 'auto',
                  marginBottom: '1.5rem',
                  opacity: revealProgress > 0.15 ? 1 : 0,
                  transform: `translateY(${revealProgress > 0.15 ? 0 : 15}px)`,
                  transition: 'all 0.5s ease-out',
                }}
              >
                <div
                  style={{
                    position: 'relative',
                    paddingLeft: '2.5rem',
                    paddingRight: '2.5rem',
                    paddingTop: '1.5rem',
                    paddingBottom: '1.5rem',
                    borderRadius: '0.125rem',
                    overflow: 'hidden',
                    background: 'linear-gradient(165deg, #c9a87a 0%, #b8956a 15%, #a07850 35%, #8a6540 55%, #785535 75%, #5c4028 100%)',
                    boxShadow: 'inset 0 1px 2px rgba(255,255,255,0.12), inset 0 -2px 4px rgba(0,0,0,0.2), 0 6px 24px rgba(0,0,0,0.4)',
                  }}
                >
                  <div
                    style={{
                      position: 'absolute',
                      inset: 0,
                      opacity: 0.35,
                      pointerEvents: 'none',
                      backgroundImage: `
                        repeating-linear-gradient(88deg, transparent 0px, transparent 8px, rgba(60,35,20,0.3) 8px, rgba(60,35,20,0.3) 9px, transparent 9px, transparent 25px),
                        repeating-linear-gradient(92deg, transparent 0px, transparent 40px, rgba(20,10,5,0.45) 40px, rgba(20,10,5,0.5) 42px, rgba(20,10,5,0.35) 44px, transparent 44px, transparent 120px),
                        repeating-linear-gradient(85deg, transparent 0px, transparent 60px, rgba(140,80,60,0.12) 60px, rgba(140,80,60,0.08) 62px, transparent 62px)
                      `,
                    }}
                  />
                  <div
                    style={{
                      position: 'absolute',
                      inset: 0,
                      opacity: 0.18,
                      pointerEvents: 'none',
                      background: 'radial-gradient(ellipse at 30% 50%, rgba(120,60,40,0.35) 0%, transparent 50%), radial-gradient(ellipse at 70% 30%, rgba(100,50,35,0.25) 0%, transparent 40%)',
                    }}
                  />

                  <h1
                    style={{
                      fontSize: '1.875rem',
                      letterSpacing: '0.1em',
                      textAlign: 'center',
                      position: 'relative',
                      color: '#2a1a0f',
                      fontFamily: 'Georgia, serif',
                      fontWeight: 700,
                      textShadow: '1px 1px 0 rgba(255,220,180,0.2)',
                    }}
                  >
                    MYSTERIES
                  </h1>
                  <div style={{
                    width: '50%',
                    height: '1px',
                    marginLeft: 'auto',
                    marginRight: 'auto',
                    marginTop: '0.5rem',
                    marginBottom: '0.5rem',
                    background: 'linear-gradient(90deg, transparent, rgba(42,26,15,0.4) 25%, rgba(42,26,15,0.4) 75%, transparent)'
                  }} />
                  <p
                    style={{
                      fontSize: '0.875rem',
                      textAlign: 'center',
                      letterSpacing: '0.1em',
                      textTransform: 'uppercase',
                      position: 'relative',
                      color: '#3d2816',
                      fontFamily: 'Georgia, serif',
                      fontWeight: 700,
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
                  style={{
                    marginBottom: '1.5rem',
                    opacity: revealProgress > 0.25 + i * 0.05 ? 1 : 0,
                    transform: `translateY(${revealProgress > 0.25 + i * 0.05 ? 0 : 12}px)`,
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
              <div style={{ height: '8rem' }} />
            </div>
          </div>
        </div>
      )}

      <canvas ref={edgeCanvasRef} style={{ position: 'absolute', inset: 0, pointerEvents: 'none', zIndex: 4 }} />
      <canvas ref={sideCanvasRef} style={{ position: 'absolute', inset: 0, pointerEvents: 'none', zIndex: 3.5 }} />
      <canvas ref={coverCanvasRef} style={{ position: 'absolute', inset: 0, pointerEvents: 'none', zIndex: 5 }} />

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
          style={{
            position: 'absolute',
            bottom: '1rem',
            right: '1rem',
            paddingLeft: '1rem',
            paddingRight: '1rem',
            paddingTop: '0.5rem',
            paddingBottom: '0.5rem',
            fontSize: '0.875rem',
            borderRadius: '0.5rem',
            zIndex: 10,
            background: 'rgba(60,40,25,0.35)',
            color: 'rgba(210,190,165,0.65)',
            border: '1px solid rgba(210,190,165,0.15)',
            fontWeight: 600,
            cursor: 'pointer',
          }}
        >
          ↺ Reset
        </button>
      )}
    </div>
  );
};

export default SteamAnimation;
