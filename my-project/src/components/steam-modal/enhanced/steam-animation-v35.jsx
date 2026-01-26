import React, { useEffect, useRef, useState, useCallback } from 'react';

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

  // Container bounds (where scroll container lives)
  // v33: Container bounds with 15px top, 30px bottom margin
  const getContentBounds = useCallback((canvas) => {
    const top = 15;
    const height = canvas.height - 45;
    return { top, bottom: top + height, height, centerY: canvas.height / 2 };
  }, []);

  // v33: Visible content bounds with 15px top, 30px bottom margin
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

  const getWaft = useCallback((seed, time, strength = 1) => {
    const t = time * 0.0001;
    const x = Math.sin(t + seed) * Math.cos(t * 0.7 + seed * 0.5) * strength;
    const y = (Math.sin(t * 0.8 + seed * 1.2) * Math.cos(t * 0.5 + seed) - 0.15) * strength;
    return { x, y };
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

  // v35: Get side margin/padding areas for active wispy steam
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

  // v35: Create side margin particle - 50% less dense, very active
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
      x,
      y: bounds.bottom + Math.random() * 50, // Start near bottom to float up
      size,
      opacity: 0,
      targetOpacity: 0.12 + Math.random() * 0.08, // 50% less dense
      seed: Math.random() * 10000,
      waftStrength: 4 + Math.random() * 5, // Very active wafting
      driftX: (Math.random() - 0.5) * 2.5,
      driftY: -1.2 - Math.random() * 1.5, // Strong upward float
      blowStrength: 1.5 + Math.random() * 2.5,
      blowAngle: Math.random() * Math.PI * 2,
      turbulence: 2 + Math.random() * 2.5,
      side,
      age: 0,
      maxAge: 250 + Math.random() * 150,
      color: getColor(),
    };
  }, [getSideMarginBounds, getContentBounds, getColor]);

  const createBaseParticle = useCallback((canvas) => {
    const bounds = getContentBounds(canvas);
    return {
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
    };
  }, [getContentBounds, getColor]);

  // v19: EXACT V9 LOGIC but using VISIBLE content bounds
  // This creates the same geometry as v9's 80px padding but with 24px padding
  const createEdgeParticle = useCallback((canvas, zone, forceX = null) => {
    const bounds = getVisibleContentBounds(canvas);
    const size = 110 + Math.random() * 70;

    let x, y;
    x = forceX !== null ? forceX : Math.random() * canvas.width;

    if (zone === 'top') {
      // V9 logic: offset by size * 0.3, spread over 50% of outer zone
      const topZone = bounds.top; // Now relative to VISIBLE content
      y = topZone - size * 0.3 - Math.random() * (topZone * 0.5);
    } else {
      const bottomZone = canvas.height - bounds.bottom;
      y = bounds.bottom + size * 0.3 + Math.random() * (bottomZone * 0.5);
    }

    return {
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
    };
  }, [getColor]);

  const drawParticle = useCallback((ctx, p, alphaMultiplier = 1) => {
    if (p.opacity < 0.003) return;
    const c = p.color;
    const alpha = p.opacity * alphaMultiplier;

    const gradient = ctx.createRadialGradient(p.x, p.y, 0, p.x, p.y, p.size);
    gradient.addColorStop(0, `rgba(${c.r + 12}, ${c.g + 12}, ${c.b + 8}, ${alpha * 0.9})`);
    gradient.addColorStop(0.2, `rgba(${c.r + 5}, ${c.g + 5}, ${c.b + 3}, ${alpha * 0.7})`);
    gradient.addColorStop(0.4, `rgba(${c.r}, ${c.g}, ${c.b}, ${alpha * 0.5})`);
    gradient.addColorStop(0.6, `rgba(${c.r - 5}, ${c.g - 5}, ${c.b - 3}, ${alpha * 0.3})`);
    gradient.addColorStop(0.8, `rgba(${c.r - 10}, ${c.g - 10}, ${c.b - 6}, ${alpha * 0.12})`);
    gradient.addColorStop(0.92, `rgba(${c.r - 15}, ${c.g - 15}, ${c.b - 10}, ${alpha * 0.04})`);
    gradient.addColorStop(1, `rgba(${c.r - 15}, ${c.g - 15}, ${c.b - 10}, 0)`);

    ctx.beginPath();
    ctx.arc(p.x, p.y, p.size, 0, Math.PI * 2);
    ctx.fillStyle = gradient;
    ctx.fill();
  }, []);

  const updateBaseParticles = useCallback((ctx, canvas, time, phase) => {
    const bounds = getContentBounds(canvas);

    baseParticlesRef.current = baseParticlesRef.current.filter(p => {
      p.age++;
      const w = getWaft(p.seed, time, p.waftStrength);
      p.x += w.x * 0.25;
      p.y += w.y * 0.2;
      
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
      
      return p.opacity > 0.008 && p.age < p.maxAge;
    });

    baseParticlesRef.current.forEach(p => drawParticle(ctx, p));
  }, [getContentBounds, getWaft, drawParticle]);

  const updateOuterParticles = useCallback((ctx, canvas, time) => {
    const bounds = getContentBounds(canvas);

    outerParticlesRef.current = outerParticlesRef.current.filter(p => {
      p.age++;
      const w = getWaft(p.seed, time, p.waftStrength);
      
      if (Math.random() < 0.03) {
        p.blowAngle += (Math.random() - 0.5) * 1.5;
        p.blowStrength = 0.5 + Math.random() * 2.5;
      }
      
      const turbX = (Math.random() - 0.5) * p.turbulence * 0.5;
      const turbY = (Math.random() - 0.5) * p.turbulence * 0.4;
      
      p.x += w.x * 1.2 + p.driftX + Math.cos(p.blowAngle) * p.blowStrength * 0.3 + turbX;
      p.y += w.y * 0.9 + p.driftY + Math.sin(p.blowAngle) * p.blowStrength * 0.2 + turbY;
      
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
      
      return p.opacity > 0.005 && p.age < p.maxAge;
    });

    outerParticlesRef.current.forEach(p => drawParticle(ctx, p));
  }, [getContentBounds, getWaft, drawParticle]);

  // v19: EXACT V9 LOGIC but using VISIBLE content bounds
  const updateEdgeParticles = useCallback((ctx, canvas, time) => {
    const bounds = getVisibleContentBounds(canvas);

    edgeParticlesRef.current = edgeParticlesRef.current.filter(p => {
      p.age++;
      
      const w = getWaft(p.seed, time, p.waftStrength);
      
      if (Math.random() < 0.01) {
        p.blowAngle += (Math.random() - 0.5) * 0.5;
        p.blowStrength = 0.05 + Math.random() * 0.2;
      }
      
      const turbX = (Math.random() - 0.5) * p.turbulence * 0.1;
      const turbY = (Math.random() - 0.5) * p.turbulence * 0.05;
      
      p.x += w.x * 0.3 + p.driftX * 0.3 + Math.cos(p.blowAngle) * p.blowStrength * 0.05 + turbX;
      p.y += w.y * 0.2 + p.driftY * 0.2 + Math.sin(p.blowAngle) * p.blowStrength * 0.03 + turbY;
      
      p.driftX += (Math.random() - 0.5) * 0.015;
      p.driftY += (Math.random() - 0.5) * 0.01;
      p.driftX *= 0.995;
      p.driftY *= 0.995;
      p.blowStrength *= 0.98;
      
      // v19: V9 boundary logic but using VISIBLE bounds
      if (p.zone === 'top') {
        if (p.y > bounds.top - 5) p.y = bounds.top - 5 - Math.random() * 10;
        if (p.y < -p.size * 0.4) p.y = -p.size * 0.4 + 2;
      } else {
        if (p.y < bounds.bottom + 5) p.y = bounds.bottom + 5 + Math.random() * 10;
        if (p.y > canvas.height + p.size * 0.4) p.y = canvas.height + p.size * 0.4 - 2;
      }
      
      if (p.x < -p.size * 0.4) p.x = canvas.width + p.size * 0.2;
      if (p.x > canvas.width + p.size * 0.4) p.x = -p.size * 0.2;
      
      // v26: Fixed state - instant full opacity, no fade out
      if (p.opacity < p.targetOpacity) {
        p.opacity = p.targetOpacity;
      }
      
      return true; // Particles persist permanently
    });

    edgeParticlesRef.current.forEach(p => drawParticle(ctx, p));
  }, [getVisibleContentBounds, getWaft, drawParticle]);

  // v35: Update side margin particles - very active wisps floating upward
  const updateSideParticles = useCallback((ctx, canvas, time) => {
    const bounds = getContentBounds(canvas);
    const margins = getSideMarginBounds(canvas);

    sideParticlesRef.current = sideParticlesRef.current.filter(p => {
      p.age++;
      
      const w = getWaft(p.seed, time, p.waftStrength);
      
      // Frequent direction changes for very active movement
      if (Math.random() < 0.1) {
        p.blowAngle += (Math.random() - 0.5) * 2.5;
        p.blowStrength = 1.5 + Math.random() * 3;
      }
      
      // High turbulence for wispy effect
      const turbX = (Math.random() - 0.5) * p.turbulence;
      const turbY = (Math.random() - 0.5) * p.turbulence * 0.5;
      
      // Strong wafting, blowing, and upward float
      p.x += w.x * 2 + p.driftX * 0.6 + Math.cos(p.blowAngle) * p.blowStrength * 0.5 + turbX;
      p.y += w.y * 1.2 + p.driftY + Math.sin(p.blowAngle) * p.blowStrength * 0.3 + turbY;
      
      // Drift variation for organic movement
      p.driftX += (Math.random() - 0.5) * 0.2;
      p.driftY += (Math.random() - 0.5) * 0.1 - 0.03; // Bias upward
      p.driftX *= 0.96;
      p.driftY *= 0.97;
      p.blowStrength *= 0.92;
      
      // Keep within side margins loosely
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
      
      // Respawn at bottom when floating off top
      if (p.y < bounds.top - p.size) {
        p.y = bounds.bottom + p.size * 0.5;
        p.opacity = 0;
      }
      
      // Fade in/out
      const ageRatio = p.age / p.maxAge;
      if (ageRatio < 0.12) {
        p.opacity += (p.targetOpacity - p.opacity) * 0.1;
      } else if (ageRatio > 0.7) {
        p.opacity *= 0.96;
      }
      
      return p.opacity > 0.003 && p.age < p.maxAge;
    });

    sideParticlesRef.current.forEach(p => drawParticle(ctx, p));
  }, [getContentBounds, getSideMarginBounds, getWaft, drawParticle]);

  const updateCoverParticles = useCallback((ctx, canvas, time, phase, revealProg) => {
    const centerX = canvas.width / 2;
    const centerY = canvas.height / 2;

    coverParticlesRef.current = coverParticlesRef.current.filter(p => {
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
      const w = getWaft(p.seed, time, (p.waftStrength || 2) * waftMult);
      
      const turbX = phase < 3 ? (Math.random() - 0.5) * (p.turbulence || 0.8) * 0.35 : 0;
      const turbY = phase < 3 ? (Math.random() - 0.5) * (p.turbulence || 0.8) * 0.3 : 0;
      
      p.vx += w.x * 0.05 + turbX;
      p.vy += w.y * 0.04 + turbY - 0.008;
      
      p.x += p.vx;
      p.y += p.vy;
      p.vx *= phase < 3 ? 0.99 : 0.96;
      p.vy *= phase < 3 ? 0.99 : 0.96;
      p.size += phase < 3 ? 0.2 : 0.08;
      
      const ageRatio = p.age / p.maxAge;
      if (phase < 3 && ageRatio < 0.15) {
        p.opacity += (p.targetOpacity - p.opacity) * 0.08;
      } else if (phase < 3 && ageRatio > 0.7) {
        p.opacity *= 0.98;
      }
      
      const minOpacity = phase >= 4 ? 0.01 : 0.003;
      return p.opacity > minOpacity && p.age < p.maxAge;
    });

    const layers = { back: [], mid: [], front: [] };
    coverParticlesRef.current.forEach(p => layers[p.layer].push(p));

    ['back', 'mid', 'front'].forEach(layer => {
      const alphaMultiplier = layer === 'back' ? 0.5 : layer === 'mid' ? 0.7 : 1;
      layers[layer].forEach(p => drawParticle(ctx, p, alphaMultiplier));
    });
  }, [getWaft, drawParticle]);

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
      
      // v33: Spawn mature state with enhanced top softening
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
        // v27: Boundary softening layer - particles closer to edge with lower opacity
        const bounds = getVisibleContentBounds(edgeCanvas);
        for (let i = 0; i < 20; i++) {
          const xPos = (i / 20) * width + (Math.random() - 0.5) * (width / 12);
          
          // Top boundary - position closer to content edge
          const topP = createEdgeParticle(edgeCanvas, 'top', xPos);
          topP.y = bounds.top - topP.size * 0.15 - Math.random() * 20;
          topP.opacity = 0.25 + Math.random() * 0.15;
          topP.targetOpacity = topP.opacity;
          edgeParticlesRef.current.push(topP);
          
          // Bottom boundary - position closer to content edge
          const bottomP = createEdgeParticle(edgeCanvas, 'bottom', xPos);
          bottomP.y = bounds.bottom + bottomP.size * 0.15 + Math.random() * 20;
          bottomP.opacity = 0.25 + Math.random() * 0.15;
          bottomP.targetOpacity = bottomP.opacity;
          edgeParticlesRef.current.push(bottomP);
        }
        // v33: Extra top softening - very close to edge with subtle opacity
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
      // v35: Active wispy side margin steam
      if (Math.random() < 0.4 && sideParticlesRef.current.length < 40) {
        sideParticlesRef.current.push(createSideParticle(sideCanvas, 'left'));
        sideParticlesRef.current.push(createSideParticle(sideCanvas, 'right'));
      }
      // v26: No ongoing edge spawning - state is fixed
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
      // v35: Active wispy side margin steam
      if (Math.random() < 0.35 && sideParticlesRef.current.length < 40) {
        sideParticlesRef.current.push(createSideParticle(sideCanvas, 'left'));
        sideParticlesRef.current.push(createSideParticle(sideCanvas, 'right'));
      }
      // v26: No ongoing edge spawning - state is fixed
    }

    phaseRef.current = currentPhase;

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

    animationRef.current = requestAnimationFrame(animate);
  }, [createBaseParticle, createOuterParticle, createEdgeParticle, createCoverParticle, createSideParticle,
      updateBaseParticles, updateOuterParticles, updateEdgeParticles, updateSideParticles, updateCoverParticles]);

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

  return (
    <div ref={containerRef} className="relative w-full overflow-hidden" style={{ background: '#1c1814', height: '100%' }}>
      <canvas ref={baseCanvasRef} className="absolute inset-0" style={{ zIndex: 1 }} />
      <canvas ref={outerCanvasRef} className="absolute inset-0" style={{ zIndex: 2 }} />
      
      {/* v35: Red debug outline */}
      {showContent && (
        <div 
          className="absolute inset-x-0"
          style={{ 
            zIndex: 6,
            top: 15,
            height: 'calc(100% - 45px)',
            border: '3px solid red',
            boxSizing: 'border-box',
            pointerEvents: 'none',
          }}
        />
      )}
      {/* v33: Content area with 15px top, 30px bottom margin */}
      {showContent && (
        <div 
          className="absolute inset-x-0"
          style={{ 
            zIndex: 3,
            top: 15,
            height: 'calc(100% - 45px)',
            opacity: Math.min(revealProgress * 2, 1),
          }}
        >
          <div 
            ref={contentRef}
            className="w-full h-full overflow-y-auto overflow-x-hidden"
            style={{ scrollbarWidth: 'none', msOverflowStyle: 'none' }}
          >
            <style>{`div::-webkit-scrollbar { display: none; }`}</style>
            
            {/* v33: pt-12 pb-12 - padding to keep content away from edges */}
            <div className="max-w-xl mx-auto px-5 pt-12 pb-12">
              <div 
                className="relative mx-auto mb-6"
                style={{
                  opacity: revealProgress > 0.15 ? 1 : 0,
                  transform: `translateY(${revealProgress > 0.15 ? 0 : 15}px)`,
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
              <div className="h-32" />
            </div>
          </div>
        </div>
      )}
      
      <canvas ref={edgeCanvasRef} className="absolute inset-0 pointer-events-none" style={{ zIndex: 4 }} />
      <canvas ref={sideCanvasRef} className="absolute inset-0 pointer-events-none" style={{ zIndex: 3.5 }} />
      <canvas ref={coverCanvasRef} className="absolute inset-0 pointer-events-none" style={{ zIndex: 5 }} />
      
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
