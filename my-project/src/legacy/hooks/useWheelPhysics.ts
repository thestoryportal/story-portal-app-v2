/**
 * useWheelPhysics - Manages wheel rotation physics
 *
 * Handles rotation, velocity, friction, easing, and spin mechanics.
 */

import { useState, useRef, useCallback, useEffect } from 'react';
import type { WheelPhysicsState, WheelPhysicsActions, WheelPhysicsRefs } from '../types';

export interface UseWheelPhysicsOptions {
  /** Whether test mode is enabled (affects friction and easing) */
  testMode?: boolean;
  /** Callback when wheel stops on a prompt */
  onWheelStop?: (selectedIndex: number, finalRotation: number) => void;
}

export interface UseWheelPhysicsReturn {
  state: WheelPhysicsState;
  actions: WheelPhysicsActions;
  refs: WheelPhysicsRefs;
}

/**
 * Wheel physics hook for rotation and momentum
 */
export function useWheelPhysics(options: UseWheelPhysicsOptions = {}): UseWheelPhysicsReturn {
  const { testMode = false, onWheelStop } = options;

  // Visual state (synced with React)
  const [rotation, setRotation] = useState(0);
  const [cylinderRadius, setCylinderRadius] = useState(110);
  const [panelHeight, setPanelHeight] = useState(41);
  const [fontSize, setFontSize] = useState(16);
  const [wheelTilt, setWheelTilt] = useState(12);

  // Physics refs (no React re-render needed)
  const velocityRef = useRef(0);
  const rotationRef = useRef(0);
  const animationRef = useRef<number | null>(null);
  const isCoastingRef = useRef(false);
  const lastInputTimeRef = useRef(0);
  const spinDirectionRef = useRef(1);
  const spinFrictionRef = useRef(0.985);
  const recentLandingsRef = useRef<number[]>([]);
  const frameCountRef = useRef(0);
  const targetPromptRef = useRef<number | null>(null);
  const easingPhaseRef = useRef(false);
  const lastKnownDirectionRef = useRef(1);

  // DOM refs
  const wheelContainerRef = useRef<HTMLDivElement | null>(null);
  const wheelRotationRef = useRef<HTMLDivElement | null>(null);
  const isHoveringRef = useRef(false);

  // Store callbacks in refs to avoid stale closures in animation loop
  const testModeRef = useRef(testMode);
  const onWheelStopRef = useRef(onWheelStop);

  // Keep refs up to date
  useEffect(() => {
    testModeRef.current = testMode;
  }, [testMode]);

  useEffect(() => {
    onWheelStopRef.current = onWheelStop;
  }, [onWheelStop]);

  // Animation loop - use a ref-based approach to avoid self-reference issues
  const animateFnRef = useRef<() => void>(() => {});

  // Initialize the animation function
  useEffect(() => {
    animateFnRef.current = () => {
      const now = Date.now();
      frameCountRef.current++;

      // Mark as coasting after 150ms of no input
      if (
        !isCoastingRef.current &&
        now - lastInputTimeRef.current > 150 &&
        Math.abs(velocityRef.current) > 2
      ) {
        isCoastingRef.current = true;
      }

      const absVel = Math.abs(velocityRef.current);

      // PHASE 1: High velocity spinning - apply friction, throttle updates
      if (absVel >= 1.5 && !easingPhaseRef.current) {
        // Track direction while we have clear velocity
        if (absVel > 0.5) {
          lastKnownDirectionRef.current = velocityRef.current >= 0 ? 1 : -1;
        }

        // TEST MODE: Very high friction for immediate stop when released
        // NORMAL MODE: Variable friction set at spin start
        velocityRef.current *= testModeRef.current ? 0.5 : spinFrictionRef.current;
        rotationRef.current += velocityRef.current;

        // Throttle DOM updates at higher speeds
        let shouldUpdate = true;
        if (absVel >= 8) {
          shouldUpdate = frameCountRef.current % 3 === 0;
        } else if (absVel >= 3) {
          shouldUpdate = frameCountRef.current % 2 === 0;
        }

        if (shouldUpdate && wheelRotationRef.current) {
          wheelRotationRef.current.style.setProperty('--wheel-rotation', `${rotationRef.current}deg`);
        }

        animationRef.current = requestAnimationFrame(animateFnRef.current);
        return;
      }

      // PHASE 2: Entering easing phase - calculate target prompt once
      // TEST MODE: Skip easing, just stop where released
      if (testModeRef.current) {
        if (absVel < 1.5) {
          velocityRef.current = 0;
          animationRef.current = null;
          return;
        }
        animationRef.current = requestAnimationFrame(animateFnRef.current);
        return;
      }

      if (!easingPhaseRef.current) {
        easingPhaseRef.current = true;
        const promptInterval = 18;
        const spinDirection = lastKnownDirectionRef.current;

        // Calculate current position relative to prompt boundaries
        const currentPromptIndex = rotationRef.current / promptInterval;

        // Target the nearest prompt in spin direction - pure physics
        let targetIndex;
        if (spinDirection > 0) {
          targetIndex = Math.ceil(currentPromptIndex);
        } else {
          targetIndex = Math.floor(currentPromptIndex);
        }

        targetPromptRef.current = targetIndex * promptInterval;
      }

      // PHASE 3: Smooth easing toward target prompt
      const target = targetPromptRef.current!;
      const diff = target - rotationRef.current;

      // Smoothly ease toward target
      const easeSpeed = 0.08;
      const movement = diff * easeSpeed;

      rotationRef.current += movement;

      if (wheelRotationRef.current) {
        wheelRotationRef.current.style.setProperty('--wheel-rotation', `${rotationRef.current}deg`);
      }

      // PHASE 4: Stop when we're very close to target
      if (Math.abs(diff) < 0.1) {
        rotationRef.current = target;
        if (wheelRotationRef.current) {
          wheelRotationRef.current.style.setProperty('--wheel-rotation', `${target}deg`);
        }

        velocityRef.current = 0;
        isCoastingRef.current = false;
        easingPhaseRef.current = false;
        targetPromptRef.current = null;
        animationRef.current = null;

        const timeSinceLastInput = now - lastInputTimeRef.current;
        if (timeSinceLastInput > 200) {
          const currentTilt = wheelContainerRef.current
            ? wheelContainerRef.current.offsetWidth < 400
              ? 14
              : wheelContainerRef.current.offsetWidth < 600
                ? 17
                : 20
            : 15;

          const adjustedRotation = target + currentTilt;
          let normalizedRotation = adjustedRotation % 360;
          if (normalizedRotation < 0) normalizedRotation += 360;

          let selectedIndex = Math.round(normalizedRotation / 18) % 20;
          if (selectedIndex >= 20) selectedIndex = 0;
          if (selectedIndex < 0) selectedIndex = 19;

          // Track this landing in recent history (keep last 10)
          recentLandingsRef.current = [selectedIndex, ...recentLandingsRef.current].slice(0, 10);

          // Notify parent component
          onWheelStopRef.current?.(selectedIndex, target);
        }
        return;
      }

      animationRef.current = requestAnimationFrame(animateFnRef.current);
    };
  }, []);

  // Wrapper to start animation
  const startAnimation = useCallback(() => {
    if (!animationRef.current) {
      animationRef.current = requestAnimationFrame(animateFnRef.current);
    }
  }, []);

  // Manual spin from drag gesture
  const startSpin = useCallback(
    (delta: number) => {
      // Reset easing phase if re-spinning
      easingPhaseRef.current = false;
      targetPromptRef.current = null;

      // When starting a new spin from rest, add hidden offset for randomness
      if (Math.abs(velocityRef.current) < 2) {
        const randomPromptOffset = Math.floor(Math.random() * 20) * 18;
        const partialOffset = Math.random() * 17;
        const hiddenOffset = randomPromptOffset + partialOffset;

        rotationRef.current += hiddenOffset;

        if (wheelRotationRef.current) {
          wheelRotationRef.current.style.transition = 'none';
          wheelRotationRef.current.style.setProperty('--wheel-rotation', `${rotationRef.current}deg`);
          void wheelRotationRef.current.offsetHeight; // Force reflow
        }

        spinFrictionRef.current = 0.982 + Math.random() * 0.006;
      }

      // Use momentum-based velocity that favors the current gesture direction
      const currentVel = velocityRef.current;
      const inputVel = delta * 0.5;

      // If input is in same direction as current velocity, add momentum
      if (Math.sign(inputVel) === Math.sign(currentVel) || Math.abs(currentVel) < 1) {
        velocityRef.current = currentVel * 0.85 + inputVel;
      } else {
        velocityRef.current = currentVel * 0.7 + inputVel * 0.6;
      }

      // Cap maximum velocity
      const maxVelocity = 100;
      if (velocityRef.current > maxVelocity) velocityRef.current = maxVelocity;
      if (velocityRef.current < -maxVelocity) velocityRef.current = -maxVelocity;

      // Set direction based on resulting velocity
      lastKnownDirectionRef.current = velocityRef.current >= 0 ? 1 : -1;

      lastInputTimeRef.current = Date.now();
      isCoastingRef.current = false;

      startAnimation();
    },
    [startAnimation]
  );

  // Button-triggered automatic spin
  const buttonSpin = useCallback(() => {
    if (isCoastingRef.current) return;

    // Reset easing phase
    easingPhaseRef.current = false;
    targetPromptRef.current = null;

    // Random offset aligned to prompt boundaries (0-19 prompts = 0-342°)
    const randomPromptOffset = Math.floor(Math.random() * 20) * 18;
    // Plus a small partial offset within the prompt (0-17°) for extra variance
    const partialOffset = Math.random() * 17;
    const hiddenOffset = randomPromptOffset + partialOffset;

    rotationRef.current += hiddenOffset;

    // Apply instantly - no transition, no visual change
    if (wheelRotationRef.current) {
      wheelRotationRef.current.style.transition = 'none';
      wheelRotationRef.current.style.setProperty('--wheel-rotation', `${rotationRef.current}deg`);
      void wheelRotationRef.current.offsetHeight; // Force reflow
    }

    // Vary friction slightly for different travel distances
    spinFrictionRef.current = 0.982 + Math.random() * 0.006;

    // Wide velocity range for varied travel distance
    const baseVelocity = 40 + Math.random() * 35;

    // NEGATIVE velocity for forward/downward spin
    velocityRef.current = -baseVelocity;
    lastKnownDirectionRef.current = -1;
    lastInputTimeRef.current = Date.now();
    isCoastingRef.current = false;

    startAnimation();
  }, [startAnimation]);

  // Responsive radius scaling
  useEffect(() => {
    const updateRadius = () => {
      if (wheelContainerRef.current) {
        const wheelSize = wheelContainerRef.current.offsetWidth;
        // The viewport is now 66% of container width with tighter clipping
        const calculatedRadius = wheelSize * 0.32;
        // Min 130 for small phones, max 320 for large screens
        const boundedRadius = Math.min(Math.max(calculatedRadius, 130), 320);
        setCylinderRadius(boundedRadius);

        // Panel height must scale with radius to prevent gaps
        const calculatedPanelHeight = boundedRadius * 0.34;
        const boundedPanelHeight = Math.min(Math.max(calculatedPanelHeight, 36), 110);
        setPanelHeight(boundedPanelHeight);

        // Font size scales with panel height for readability
        const calculatedFontSize = boundedPanelHeight * 0.42;
        const boundedFontSize = Math.min(Math.max(calculatedFontSize, 14), 28);
        setFontSize(boundedFontSize);

        // Wheel tilt for 3D depth effect
        const calculatedTilt = wheelSize < 400 ? 14 : wheelSize < 600 ? 17 : 20;
        setWheelTilt(calculatedTilt);
      }
    };

    updateRadius();
    window.addEventListener('resize', updateRadius);
    return () => window.removeEventListener('resize', updateRadius);
  }, []);

  // Reset animation state
  const resetPhysics = useCallback(() => {
    velocityRef.current = 0;
    isCoastingRef.current = false;
    easingPhaseRef.current = false;
    targetPromptRef.current = null;
    if (animationRef.current) {
      cancelAnimationFrame(animationRef.current);
      animationRef.current = null;
    }
  }, []);

  return {
    state: {
      rotation,
      cylinderRadius,
      panelHeight,
      fontSize,
      wheelTilt,
    },
    actions: {
      setRotation,
      setCylinderRadius,
      setPanelHeight,
      setFontSize,
      setWheelTilt,
      startSpin,
      buttonSpin,
      resetPhysics,
    },
    refs: {
      velocityRef,
      rotationRef,
      animationRef,
      isCoastingRef,
      lastInputTimeRef,
      spinDirectionRef,
      spinFrictionRef,
      recentLandingsRef,
      wheelContainerRef,
      wheelRotationRef,
      isHoveringRef,
    },
  };
}
