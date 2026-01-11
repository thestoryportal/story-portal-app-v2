/**
 * useAnimationPhase Hook
 *
 * Manages the animation phase state machine for electricity animation.
 * Phases: idle → build → peak → decay → complete
 *
 * Timing (from spec):
 * - BUILD: 0-900ms (intensity 0→1)
 * - PEAK: 900-2200ms (intensity 1.0)
 * - DECAY: 2200-3000ms (intensity 1→0)
 * - Total: 3000ms
 *
 * IMPORTANT: This hook uses refs for animation state and does NOT trigger
 * React re-renders during animation. The intensity is accessed via a ref
 * that can be read by Three.js materials.
 */

import { useRef, useEffect, useMemo, MutableRefObject } from 'react'
import { useFrame } from '@react-three/fiber'
import type { AnimationPhase, TimingConfig, ElectricityAnimationCallbacks } from './types'
import { DEFAULT_TIMING } from './types'

export interface UseAnimationPhaseOptions extends ElectricityAnimationCallbacks {
  /** Whether animation is active */
  isActive: boolean
  /** Lock at peak intensity (for captures) */
  lockAtPeak?: boolean
  /** Custom timing configuration */
  timing?: TimingConfig
}

export interface AnimationPhaseState {
  /** Current animation phase */
  phase: AnimationPhase
  /** Current intensity (0-1) */
  intensity: number
  /** Ref to current intensity (for direct Three.js material access) */
  intensityRef: MutableRefObject<number>
  /** Elapsed time in ms */
  elapsed: number
}

/**
 * Calculate intensity based on elapsed time and timing config
 */
function calculateIntensity(elapsed: number, timing: TimingConfig): number {
  const { buildDuration, peakDuration } = timing
  const peakEnd = buildDuration + peakDuration
  const totalDuration = timing.totalDuration

  if (elapsed <= 0) {
    return 0
  }

  // BUILD phase: 0 → 1
  if (elapsed < buildDuration) {
    const t = elapsed / buildDuration
    return easeOutQuad(t)
  }

  // PEAK phase: hold at 1.0
  if (elapsed < peakEnd) {
    return 1.0
  }

  // DECAY phase: 1 → 0
  if (elapsed < totalDuration) {
    const decayElapsed = elapsed - peakEnd
    const decayDuration = timing.decayDuration
    const t = decayElapsed / decayDuration
    return 1.0 - easeInQuad(t)
  }

  // Complete
  return 0
}

/**
 * Determine phase based on elapsed time
 */
function calculatePhase(elapsed: number, timing: TimingConfig): AnimationPhase {
  const { buildDuration, peakDuration, totalDuration } = timing
  const peakEnd = buildDuration + peakDuration

  if (elapsed <= 0) return 'idle'
  if (elapsed < buildDuration) return 'build'
  if (elapsed < peakEnd) return 'peak'
  if (elapsed < totalDuration) return 'decay'
  return 'complete'
}

// Easing functions
function easeOutQuad(t: number): number {
  return t * (2 - t)
}

function easeInQuad(t: number): number {
  return t * t
}

/**
 * Animation phase hook for electricity animation
 *
 * Must be used inside a React Three Fiber Canvas context (uses useFrame)
 *
 * NOTE: Does NOT cause React re-renders during animation.
 * Access intensity via the returned intensityRef for material updates.
 */
export function useAnimationPhase({
  isActive,
  lockAtPeak = false,
  timing = DEFAULT_TIMING,
  onPhaseChange,
  onComplete,
}: UseAnimationPhaseOptions): AnimationPhaseState {
  // All state stored in refs to avoid re-renders during animation
  const intensityRef = useRef(0)
  const phaseRef = useRef<AnimationPhase>('idle')
  const elapsedRef = useRef(0)

  // Animation control refs
  const startTimeRef = useRef<number | null>(null)
  const lastPhaseRef = useRef<AnimationPhase>('idle')
  const completedRef = useRef(false)
  const isActiveRef = useRef(isActive)
  const wasActiveRef = useRef(false) // Track if we've seen isActive=true

  // Keep isActive ref in sync
  useEffect(() => {
    isActiveRef.current = isActive
  }, [isActive])

  // Reset animation when isActive transitions from false to true
  // IMPORTANT: This effect runs AFTER first frame, so check if animation already started
  useEffect(() => {
    if (isActive && !wasActiveRef.current) {
      // First time becoming active
      wasActiveRef.current = true

      // Only reset if animation hasn't already started (useFrame may have run first)
      if (startTimeRef.current === null) {
        lastPhaseRef.current = 'idle'
        completedRef.current = false
        intensityRef.current = 0
        phaseRef.current = 'idle'
        elapsedRef.current = 0
        console.log('[useAnimationPhase] Animation starting, initializing state')
      } else {
        console.log('[useAnimationPhase] Animation already in progress, skipping reset')
      }
    } else if (!isActive && wasActiveRef.current) {
      // Becoming inactive - reset for next activation
      wasActiveRef.current = false
      startTimeRef.current = null
      completedRef.current = false
      intensityRef.current = 0
      phaseRef.current = 'idle'
      elapsedRef.current = 0
      console.log('[useAnimationPhase] Animation stopped, isActive transition true→false')
    }
    // If isActive is true and wasActive is already true, don't reset (effect re-fired)
  }, [isActive])

  // Animation loop - runs every frame, updates refs WITHOUT causing re-renders
  useFrame((state) => {
    if (!isActiveRef.current || completedRef.current) return

    // Initialize start time on first frame
    if (startTimeRef.current === null) {
      startTimeRef.current = state.clock.getElapsedTime() * 1000
      console.log('[useAnimationPhase] Start time set:', startTimeRef.current.toFixed(0))
    }

    // Calculate elapsed time
    const currentTime = state.clock.getElapsedTime() * 1000
    const elapsed = currentTime - startTimeRef.current
    elapsedRef.current = elapsed

    // Handle lockAtPeak
    if (lockAtPeak) {
      const currentPhase = calculatePhase(elapsed, timing)
      if (currentPhase === 'peak' || currentPhase === 'decay' || currentPhase === 'complete') {
        // Still log phase transition even when locked
        if (currentPhase !== lastPhaseRef.current && lastPhaseRef.current !== 'peak') {
          console.log('[useAnimationPhase] Phase:', lastPhaseRef.current, '→', currentPhase,
            `(${Math.round(elapsed)}ms) [lockAtPeak active]`)
          lastPhaseRef.current = 'peak' // Lock to peak
          onPhaseChange?.('peak')
        }
        intensityRef.current = 1.0
        phaseRef.current = 'peak'
        return
      }
    }

    // Calculate current phase and intensity
    const currentPhase = calculatePhase(elapsed, timing)
    const currentIntensity = calculateIntensity(elapsed, timing)

    // Update refs (no React re-render)
    intensityRef.current = currentIntensity
    phaseRef.current = currentPhase

    // Handle phase transitions (only log and callback on phase change)
    if (currentPhase !== lastPhaseRef.current) {
      console.log('[useAnimationPhase] Phase:', lastPhaseRef.current, '→', currentPhase,
        `(${Math.round(elapsed)}ms, intensity=${currentIntensity.toFixed(2)})`)
      lastPhaseRef.current = currentPhase
      onPhaseChange?.(currentPhase)

      // Handle completion
      if (currentPhase === 'complete' && !completedRef.current) {
        completedRef.current = true
        console.log('[useAnimationPhase] Animation complete')
        onComplete?.()
      }
    }
  })

  // Return current state - note these are refs, so values may be stale in React render
  // Use intensityRef.current for real-time values in Three.js
  return useMemo(() => ({
    phase: phaseRef.current,
    intensity: intensityRef.current,
    intensityRef,
    elapsed: elapsedRef.current,
  }), []) // Empty deps - object structure never changes, only ref values do
}

export default useAnimationPhase
