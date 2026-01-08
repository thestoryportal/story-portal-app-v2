/**
 * @deprecated Use useElectricityEffectThree or ElectricityR3F instead.
 * This raw WebGL implementation is superseded by the React Three Fiber approach.
 *
 * useElectricityEffect - WebGL-based electricity animation hook
 *
 * Manages the electricity effect with multi-pass rendering:
 * - Pass 1: Render bolts to texture
 * - Pass 2: Render volumetric plasma layer
 * - Pass 3: Multi-scale bloom (tight, medium, wide)
 * - Pass 4: Composite all layers to screen
 */

import { useEffect, useRef } from 'react';
import type { FlashArc, ElectricityState } from '../types';
import { ELECTRICITY_CONFIG } from '../constants';
import {
  boltVertexShader,
  boltFragmentShader,
  blurVertexShader,
  blurFragmentShader,
  plasmaFragmentShader,
  compositeFragmentShader,
} from './shaders';
import {
  initializeBolts,
  updateBoltOpacities,
  createFlashArc,
  generateAnimatedPath,
  generateBranchPath,
  generateFlashPath,
  resetDeterministicRandom,
  type BoltWithBranches,
  type Point,
} from './boltGenerator';

export interface UseElectricityEffectOptions {
  /** Whether the effect is active */
  enabled: boolean;
  /** Canvas ref to render to */
  canvasRef: React.RefObject<HTMLCanvasElement | null>;
}

interface FramebufferPair {
  framebuffer: WebGLFramebuffer;
  texture: WebGLTexture;
}

interface ElectricityStateInternal extends ElectricityState {
  bolts: BoltWithBranches[];
  startTime?: number;
}

/**
 * WebGL electricity rendering with contained bloom
 */
export function useElectricityEffect({ enabled, canvasRef }: UseElectricityEffectOptions): void {
  const electricAnimFrameRef = useRef<number | null>(null);
  const electricStateRef = useRef<ElectricityStateInternal>({
    time: 0,
    bolts: [],
    initialized: false,
  });
  const flashArcsRef = useRef<FlashArc[]>([]);

  useEffect(() => {
    if (!enabled || !canvasRef.current) {
      return;
    }

    const canvas = canvasRef.current;
    const gl = canvas.getContext('webgl', {
      alpha: true,
      premultipliedAlpha: false,
      antialias: true,
      preserveDrawingBuffer: true,
    });

    if (!gl) {
      console.error('WebGL not supported');
      return;
    }

    const state = electricStateRef.current;
    const centerX = 201,  // Adjusted right 2px
      centerY = 193; // Adjusted down 3px
    const resolution = 400;

    // Initialize bolts on first run
    if (!state.initialized) {
      // Reset PRNG for deterministic captures (iteration pipeline)
      resetDeterministicRandom();
      state.bolts = initializeBolts();
      state.time = 0;
      state.startTime = Date.now();
      state.initialized = true;
      flashArcsRef.current = [];
    }

    // === Shader Compilation Helpers ===
    const compileShader = (source: string, type: number): WebGLShader | null => {
      const shader = gl.createShader(type);
      if (!shader) return null;
      gl.shaderSource(shader, source);
      gl.compileShader(shader);
      if (!gl.getShaderParameter(shader, gl.COMPILE_STATUS)) {
        console.error('Shader compile error:', gl.getShaderInfoLog(shader));
        gl.deleteShader(shader);
        return null;
      }
      return shader;
    };

    const createProgram = (vertexSource: string, fragmentSource: string): WebGLProgram | null => {
      const vertexShader = compileShader(vertexSource, gl.VERTEX_SHADER);
      const fragmentShader = compileShader(fragmentSource, gl.FRAGMENT_SHADER);
      if (!vertexShader || !fragmentShader) return null;

      const program = gl.createProgram();
      if (!program) return null;

      gl.attachShader(program, vertexShader);
      gl.attachShader(program, fragmentShader);
      gl.linkProgram(program);
      if (!gl.getProgramParameter(program, gl.LINK_STATUS)) {
        console.error('Program link error:', gl.getProgramInfoLog(program));
        return null;
      }
      return program;
    };

    // === Create Programs ===
    const boltProgram = createProgram(boltVertexShader, boltFragmentShader);
    const blurProgram = createProgram(blurVertexShader, blurFragmentShader);
    const plasmaProgram = createProgram(blurVertexShader, plasmaFragmentShader);
    const compositeProgram = createProgram(blurVertexShader, compositeFragmentShader);

    if (!boltProgram || !blurProgram || !plasmaProgram || !compositeProgram) {
      console.error('Failed to create shader programs');
      return;
    }

    // === Create Framebuffers and Textures ===
    const createFramebuffer = (): FramebufferPair | null => {
      const fb = gl.createFramebuffer();
      const tex = gl.createTexture();
      if (!fb || !tex) return null;

      gl.bindTexture(gl.TEXTURE_2D, tex);
      gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, resolution, resolution, 0, gl.RGBA, gl.UNSIGNED_BYTE, null);
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR);
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR);
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE);
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
      gl.bindFramebuffer(gl.FRAMEBUFFER, fb);
      gl.framebufferTexture2D(gl.FRAMEBUFFER, gl.COLOR_ATTACHMENT0, gl.TEXTURE_2D, tex, 0);
      return { framebuffer: fb, texture: tex };
    };

    // Framebuffers for multi-pass rendering
    const plasmaFB = createFramebuffer();
    const boltsFB = createFramebuffer();
    const blurFB1 = createFramebuffer();
    const blurFB2 = createFramebuffer();
    const bloomTightFB = createFramebuffer();
    const bloomMedFB = createFramebuffer();
    const bloomWideFB = createFramebuffer();

    if (!plasmaFB || !boltsFB || !blurFB1 || !blurFB2 || !bloomTightFB || !bloomMedFB || !bloomWideFB) {
      console.error('Failed to create framebuffers');
      return;
    }

    // === Fullscreen Quad for Post-Processing ===
    const quadBuffer = gl.createBuffer();
    gl.bindBuffer(gl.ARRAY_BUFFER, quadBuffer);
    gl.bufferData(
      gl.ARRAY_BUFFER,
      new Float32Array([-1, -1, 0, 0, 1, -1, 1, 0, -1, 1, 0, 1, 1, 1, 1, 1]),
      gl.STATIC_DRAW
    );

    // === Bolt Vertex Buffer ===
    const boltBuffer = gl.createBuffer();

    // === Render Function ===
    let lastFrameTime = Date.now();
    let renderActive = true;

    const render = () => {
      try {
        if (!renderActive) return;

        const currentTime = Date.now();
        const deltaTime = (currentTime - lastFrameTime) / 1000;
        lastFrameTime = currentTime;

        state.time += 0.03;
        const elapsed = currentTime - (state.startTime || currentTime);
        const elapsedSec = elapsed / 1000;
        const cfg = ELECTRICITY_CONFIG;

        // === SURGE CYCLE: 3-second cycles (build, peak, calm) ===
        const cyclePosition = (elapsedSec % cfg.surgeCycleDuration) / cfg.surgeCycleDuration;
        let surgeMultiplier: number;
        if (cyclePosition < cfg.surgeBuildPhase) {
          const buildProgress = cyclePosition / cfg.surgeBuildPhase;
          surgeMultiplier =
            cfg.surgeBaseBrightness + (cfg.surgePeakBrightness - cfg.surgeBaseBrightness) * (buildProgress * buildProgress);
        } else if (cyclePosition < cfg.surgePeakPhase) {
          surgeMultiplier = cfg.surgePeakBrightness;
        } else {
          const calmProgress = (cyclePosition - cfg.surgePeakPhase) / (1.0 - cfg.surgePeakPhase);
          surgeMultiplier = cfg.surgePeakBrightness - (cfg.surgePeakBrightness - cfg.surgeBaseBrightness) * calmProgress;
        }

        // === 2Hz CENTER PULSE ===
        const pulsePhase = elapsedSec * cfg.centerPulseFrequency * Math.PI * 2;
        const centerPulse = 1.0 + Math.sin(pulsePhase) * cfg.centerPulseAmount;

        // === WIDTH MULTIPLIER during surge peaks ===
        const widthMultiplier =
          cyclePosition >= cfg.surgeBuildPhase && cyclePosition < cfg.surgePeakPhase
            ? cfg.surgePeakWidth
            : 1.0 + (surgeMultiplier - cfg.surgeBaseBrightness) * 0.3;

        // Calculate base intensity with timing
        let intensity: number;
        if (elapsed < 200) {
          const buildUp = elapsed / 200;
          intensity = 0.3 + buildUp * buildUp * 0.7;
        } else if (elapsed < 2600) {
          intensity = 1;
        } else if (elapsed < 3000) {
          const fadeProgress = (elapsed - 2600) / 400;
          intensity = 1 - fadeProgress * fadeProgress;
        } else {
          intensity = 0;
        }

        const finalIntensity = intensity * surgeMultiplier;

        if (intensity <= 0.01 && elapsed > 2000) {
          gl.bindFramebuffer(gl.FRAMEBUFFER, null);
          gl.clearColor(0, 0, 0, 0);
          gl.clear(gl.COLOR_BUFFER_BIT);
          return;
        }

        // === UPDATE PER-BOLT OPACITIES ===
        updateBoltOpacities(state.bolts, deltaTime, surgeMultiplier);

        // Spawn flash bolts
        const flashChance = cyclePosition < cfg.surgePeakPhase ? 0.09 : 0.04;
        if (elapsed < 1800 && Math.random() < flashChance * intensity) {
          flashArcsRef.current.push(createFlashArc());
        }

        // Clean expired flash arcs
        const now = Date.now();
        flashArcsRef.current = flashArcsRef.current.filter((arc) => {
          arc.life = now - (arc as FlashArc & { birth?: number }).id;
          return arc.life < arc.maxLife;
        });

        // === PASS 1: Render bolts to texture ===
        gl.bindFramebuffer(gl.FRAMEBUFFER, boltsFB.framebuffer);
        gl.viewport(0, 0, resolution, resolution);
        gl.clearColor(0, 0, 0, 0);
        gl.clear(gl.COLOR_BUFFER_BIT);
        gl.enable(gl.BLEND);
        gl.blendFunc(gl.SRC_ALPHA, gl.ONE);

        gl.useProgram(boltProgram);
        const posLoc = gl.getAttribLocation(boltProgram, 'a_position');
        const alphaLoc = gl.getAttribLocation(boltProgram, 'a_alpha');
        const resLoc = gl.getUniformLocation(boltProgram, 'u_resolution');
        const coreColorLoc = gl.getUniformLocation(boltProgram, 'u_coreColor');
        const midColorLoc = gl.getUniformLocation(boltProgram, 'u_midColor');
        const outerColorLoc = gl.getUniformLocation(boltProgram, 'u_outerColor');
        const intensityLoc = gl.getUniformLocation(boltProgram, 'u_intensity');

        gl.uniform2f(resLoc, resolution, resolution);

        // Collect all bolt segments
        const segments: number[] = [];
        const flickerCfg = cfg.microFlickerAmount;

        const addBoltPath = (points: Point[], thickness: number, isMain: boolean, boltOpacity: number = 1.0) => {
          if (points.length < 2) return;
          const flicker = 1.0 + (Math.random() - 0.5) * flickerCfg;
          const baseW = thickness * flicker * widthMultiplier * (isMain ? 2.0 : 1.4);

          for (let i = 0; i < points.length - 1; i++) {
            const p1 = points[i];
            const p2 = points[i + 1];
            const dx = p2.x - p1.x;
            const dy = p2.y - p1.y;
            const len = Math.sqrt(dx * dx + dy * dy);
            if (len < 0.1) continue;
            const nx = -dy / len;
            const ny = dx / len;

            const taper = 1.0 - Math.abs(i / (points.length - 1) - 0.5) * 0.3;
            const w = baseW * taper;
            const alpha = (isMain ? 0.92 : 0.78) * boltOpacity;

            segments.push(
              p1.x - nx * w, p1.y - ny * w, alpha,
              p1.x + nx * w, p1.y + ny * w, alpha,
              p2.x - nx * w, p2.y - ny * w, alpha,
              p2.x + nx * w, p2.y + ny * w, alpha,
              p2.x - nx * w, p2.y - ny * w, alpha,
              p1.x + nx * w, p1.y + ny * w, alpha
            );
          }
        };

        // Generate and collect all bolt paths
        state.bolts.forEach((bolt) => {
          if (bolt.opacity < 0.05) return;

          const effectiveThickness = bolt.thickness * finalIntensity;
          if (effectiveThickness < 0.1) return;

          const points = generateAnimatedPath(bolt, state.time, centerX, centerY);

          // Sub-branches
          bolt.branches.forEach((branch) => {
            if (branch.subBranches) {
              branch.subBranches.forEach((sub) => {
                const branchStartIdx = Math.floor(branch.startT * (points.length - 1));
                const branchStart = points[branchStartIdx];
                const branchPath = generateBranchPath(branchStart, branch, state.time, bolt.noise);
                const subStartIdx = Math.floor(sub.startT * (branchPath.length - 1));
                const subStart = branchPath[subStartIdx];
                const subBranch = { angle: branch.angle + sub.angleOffset, length: sub.length, speed: 4, seed: sub.seed };
                const subPath = generateBranchPath(subStart, subBranch, state.time, bolt.noise);
                addBoltPath(subPath, sub.thickness * finalIntensity, false, bolt.opacity * 0.7);
              });
            }
          });

          // Branches
          bolt.branches.forEach((branch) => {
            const startIdx = Math.floor(branch.startT * (points.length - 1));
            const startPoint = points[startIdx];
            const branchPoints = generateBranchPath(startPoint, branch, state.time, bolt.noise);
            addBoltPath(branchPoints, branch.thickness * finalIntensity, false, bolt.opacity * 0.85);
          });

          // Main bolt
          addBoltPath(points, effectiveThickness, true, bolt.opacity);
        });

        // Flash arcs
        flashArcsRef.current.forEach((arc) => {
          const lifeRatio = arc.life / arc.maxLife;
          const flashIntensity = lifeRatio < 0.25 ? lifeRatio / 0.25 : 1 - (lifeRatio - 0.25) / 0.75;
          if (flashIntensity > 0.15) {
            const points = generateFlashPath(arc, state.time, centerX, centerY);
            addBoltPath(points, arc.thickness * flashIntensity * widthMultiplier, true, 1.0);
          }
        });

        if (segments.length > 0) {
          const data = new Float32Array(segments);
          gl.bindBuffer(gl.ARRAY_BUFFER, boltBuffer);
          gl.bufferData(gl.ARRAY_BUFFER, data, gl.DYNAMIC_DRAW);

          gl.enableVertexAttribArray(posLoc);
          gl.enableVertexAttribArray(alphaLoc);
          gl.vertexAttribPointer(posLoc, 2, gl.FLOAT, false, 12, 0);
          gl.vertexAttribPointer(alphaLoc, 1, gl.FLOAT, false, 12, 8);

          gl.uniform3f(coreColorLoc, cfg.coreColor[0], cfg.coreColor[1], cfg.coreColor[2]);
          gl.uniform3f(midColorLoc, cfg.midColor[0], cfg.midColor[1], cfg.midColor[2]);
          gl.uniform3f(outerColorLoc, cfg.outerColor[0], cfg.outerColor[1], cfg.outerColor[2]);
          gl.uniform1f(intensityLoc, finalIntensity);
          gl.drawArrays(gl.TRIANGLES, 0, segments.length / 3);
        }

        // === PASS 2: Render volumetric plasma layer ===
        gl.bindFramebuffer(gl.FRAMEBUFFER, plasmaFB.framebuffer);
        gl.clearColor(0, 0, 0, 0);
        gl.clear(gl.COLOR_BUFFER_BIT);
        gl.blendFunc(gl.SRC_ALPHA, gl.ONE_MINUS_SRC_ALPHA);

        gl.useProgram(plasmaProgram);
        gl.bindBuffer(gl.ARRAY_BUFFER, quadBuffer);

        const plasmaPosLoc = gl.getAttribLocation(plasmaProgram, 'a_position');
        const plasmaTexLoc = gl.getAttribLocation(plasmaProgram, 'a_texCoord');
        gl.enableVertexAttribArray(plasmaPosLoc);
        gl.enableVertexAttribArray(plasmaTexLoc);
        gl.vertexAttribPointer(plasmaPosLoc, 2, gl.FLOAT, false, 16, 0);
        gl.vertexAttribPointer(plasmaTexLoc, 2, gl.FLOAT, false, 16, 8);

        gl.uniform1f(gl.getUniformLocation(plasmaProgram, 'u_time'), state.time);
        gl.uniform2f(gl.getUniformLocation(plasmaProgram, 'u_center'), 0.5, 0.5);
        gl.uniform1f(gl.getUniformLocation(plasmaProgram, 'u_intensity'), finalIntensity);
        gl.uniform1f(gl.getUniformLocation(plasmaProgram, 'u_density'), cfg.plasmaDensity);
        gl.uniform1f(gl.getUniformLocation(plasmaProgram, 'u_centerBright'), cfg.plasmaCenterBrightness * centerPulse);
        gl.uniform1f(gl.getUniformLocation(plasmaProgram, 'u_noiseScale'), cfg.plasmaNoiseScale);
        gl.uniform3f(gl.getUniformLocation(plasmaProgram, 'u_innerColor'), cfg.plasmaInner[0], cfg.plasmaInner[1], cfg.plasmaInner[2]);
        gl.uniform3f(gl.getUniformLocation(plasmaProgram, 'u_outerColor'), cfg.plasmaOuter[0], cfg.plasmaOuter[1], cfg.plasmaOuter[2]);
        gl.uniform1f(gl.getUniformLocation(plasmaProgram, 'u_portalRadius'), cfg.portalRadius);

        gl.drawArrays(gl.TRIANGLE_STRIP, 0, 4);

        // === Helper function for blur pass ===
        const runBlurPass = (sourceTex: WebGLTexture, destFB: FramebufferPair, direction: [number, number], radius: number) => {
          gl.bindFramebuffer(gl.FRAMEBUFFER, destFB.framebuffer);
          gl.clearColor(0, 0, 0, 0);
          gl.clear(gl.COLOR_BUFFER_BIT);
          gl.blendFunc(gl.ONE, gl.ONE);

          gl.useProgram(blurProgram);
          gl.bindBuffer(gl.ARRAY_BUFFER, quadBuffer);

          const blurPosLoc = gl.getAttribLocation(blurProgram, 'a_position');
          const blurTexLoc = gl.getAttribLocation(blurProgram, 'a_texCoord');
          gl.enableVertexAttribArray(blurPosLoc);
          gl.enableVertexAttribArray(blurTexLoc);
          gl.vertexAttribPointer(blurPosLoc, 2, gl.FLOAT, false, 16, 0);
          gl.vertexAttribPointer(blurTexLoc, 2, gl.FLOAT, false, 16, 8);

          gl.activeTexture(gl.TEXTURE0);
          gl.bindTexture(gl.TEXTURE_2D, sourceTex);
          gl.uniform1i(gl.getUniformLocation(blurProgram, 'u_texture'), 0);
          gl.uniform2f(gl.getUniformLocation(blurProgram, 'u_resolution'), resolution, resolution);
          gl.uniform2f(gl.getUniformLocation(blurProgram, 'u_direction'), direction[0], direction[1]);
          gl.uniform1f(gl.getUniformLocation(blurProgram, 'u_radius'), radius);

          gl.drawArrays(gl.TRIANGLE_STRIP, 0, 4);
        };

        // === PASS 3: Multi-scale bloom ===
        runBlurPass(boltsFB.texture, blurFB1, [1.0, 0.0], cfg.bloomTightRadius);
        runBlurPass(blurFB1.texture, bloomTightFB, [0.0, 1.0], cfg.bloomTightRadius);

        runBlurPass(boltsFB.texture, blurFB1, [1.0, 0.0], cfg.bloomMedRadius);
        runBlurPass(blurFB1.texture, bloomMedFB, [0.0, 1.0], cfg.bloomMedRadius);

        runBlurPass(boltsFB.texture, blurFB1, [1.0, 0.0], cfg.bloomWideRadius);
        runBlurPass(blurFB1.texture, bloomWideFB, [0.0, 1.0], cfg.bloomWideRadius);

        // === PASS 4: Composite all layers to screen ===
        gl.bindFramebuffer(gl.FRAMEBUFFER, null);
        gl.viewport(0, 0, resolution, resolution);
        gl.clearColor(0, 0, 0, 0);
        gl.clear(gl.COLOR_BUFFER_BIT);
        gl.blendFunc(gl.SRC_ALPHA, gl.ONE_MINUS_SRC_ALPHA);

        gl.useProgram(compositeProgram);
        gl.bindBuffer(gl.ARRAY_BUFFER, quadBuffer);

        const compPosLoc = gl.getAttribLocation(compositeProgram, 'a_position');
        const compTexLoc = gl.getAttribLocation(compositeProgram, 'a_texCoord');
        gl.enableVertexAttribArray(compPosLoc);
        gl.enableVertexAttribArray(compTexLoc);
        gl.vertexAttribPointer(compPosLoc, 2, gl.FLOAT, false, 16, 0);
        gl.vertexAttribPointer(compTexLoc, 2, gl.FLOAT, false, 16, 8);

        // Bind all textures
        gl.activeTexture(gl.TEXTURE0);
        gl.bindTexture(gl.TEXTURE_2D, boltsFB.texture);
        gl.uniform1i(gl.getUniformLocation(compositeProgram, 'u_bolts'), 0);

        gl.activeTexture(gl.TEXTURE1);
        gl.bindTexture(gl.TEXTURE_2D, plasmaFB.texture);
        gl.uniform1i(gl.getUniformLocation(compositeProgram, 'u_plasma'), 1);

        gl.activeTexture(gl.TEXTURE2);
        gl.bindTexture(gl.TEXTURE_2D, bloomTightFB.texture);
        gl.uniform1i(gl.getUniformLocation(compositeProgram, 'u_bloomTight'), 2);

        gl.activeTexture(gl.TEXTURE3);
        gl.bindTexture(gl.TEXTURE_2D, bloomMedFB.texture);
        gl.uniform1i(gl.getUniformLocation(compositeProgram, 'u_bloomMed'), 3);

        gl.activeTexture(gl.TEXTURE4);
        gl.bindTexture(gl.TEXTURE_2D, bloomWideFB.texture);
        gl.uniform1i(gl.getUniformLocation(compositeProgram, 'u_bloomWide'), 4);

        // Set uniforms
        gl.uniform1f(gl.getUniformLocation(compositeProgram, 'u_intensity'), finalIntensity);
        gl.uniform2f(gl.getUniformLocation(compositeProgram, 'u_center'), 0.5, 0.5);
        gl.uniform1f(gl.getUniformLocation(compositeProgram, 'u_portalRadius'), cfg.portalRadius);
        gl.uniform1f(gl.getUniformLocation(compositeProgram, 'u_bloomTightWeight'), cfg.bloomTightWeight);
        gl.uniform1f(gl.getUniformLocation(compositeProgram, 'u_bloomMedWeight'), cfg.bloomMedWeight);
        gl.uniform1f(gl.getUniformLocation(compositeProgram, 'u_bloomWideWeight'), cfg.bloomWideWeight);
        gl.uniform1f(gl.getUniformLocation(compositeProgram, 'u_exposure'), cfg.toneMapExposure);
        gl.uniform1f(gl.getUniformLocation(compositeProgram, 'u_centerGlow'), cfg.centerGlowStrength);
        gl.uniform1f(gl.getUniformLocation(compositeProgram, 'u_centerPulse'), centerPulse);
        gl.uniform1f(gl.getUniformLocation(compositeProgram, 'u_rimBloomBoost'), cfg.rimBloomBoost);
        gl.uniform1f(gl.getUniformLocation(compositeProgram, 'u_glassOpacity'), cfg.glassOpacity);
        gl.uniform1f(gl.getUniformLocation(compositeProgram, 'u_glassReflection'), cfg.glassReflectionStrength);
        gl.uniform3f(gl.getUniformLocation(compositeProgram, 'u_ambientColor'), 1.0, 0.6, 0.1);

        gl.drawArrays(gl.TRIANGLE_STRIP, 0, 4);

        electricAnimFrameRef.current = requestAnimationFrame(render);
      } catch (err) {
        console.error('Electricity render error:', err);
        electricAnimFrameRef.current = requestAnimationFrame(render);
      }
    };

    render();

    // Cleanup
    return () => {
      renderActive = false;
      if (electricAnimFrameRef.current) {
        cancelAnimationFrame(electricAnimFrameRef.current);
      }
      gl.deleteProgram(boltProgram);
      gl.deleteProgram(blurProgram);
      gl.deleteProgram(plasmaProgram);
      gl.deleteProgram(compositeProgram);
      gl.deleteFramebuffer(plasmaFB.framebuffer);
      gl.deleteFramebuffer(boltsFB.framebuffer);
      gl.deleteFramebuffer(blurFB1.framebuffer);
      gl.deleteFramebuffer(blurFB2.framebuffer);
      gl.deleteFramebuffer(bloomTightFB.framebuffer);
      gl.deleteFramebuffer(bloomMedFB.framebuffer);
      gl.deleteFramebuffer(bloomWideFB.framebuffer);
      gl.deleteTexture(plasmaFB.texture);
      gl.deleteTexture(boltsFB.texture);
      gl.deleteTexture(blurFB1.texture);
      gl.deleteTexture(blurFB2.texture);
      gl.deleteTexture(bloomTightFB.texture);
      gl.deleteTexture(bloomMedFB.texture);
      gl.deleteTexture(bloomWideFB.texture);
      if (quadBuffer) gl.deleteBuffer(quadBuffer);
      if (boltBuffer) gl.deleteBuffer(boltBuffer);
      state.initialized = false;
      state.startTime = undefined;
      flashArcsRef.current = [];
    };
  }, [enabled, canvasRef]);
}
