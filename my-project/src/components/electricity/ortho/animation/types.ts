/**
 * Animation Type Definitions
 *
 * Defines types for the ReactSpring-based animation system.
 */

export type AnimationPhase = 'idle' | 'build' | 'peak' | 'decay' | 'complete'

export interface SpringValues {
  intensity: number
}

export interface ElectricityAnimationCallbacks {
  onPhaseChange?: (phase: AnimationPhase) => void
  onComplete?: () => void
}

export interface TimingConfig {
  buildDuration: number    // BUILD phase: 0 → 1 intensity (default: 900ms)
  peakDuration: number     // PEAK phase: hold at 1.0 (default: 1300ms)
  decayDuration: number    // DECAY phase: 1 → 0 intensity (default: 800ms)
  totalDuration: number    // Total animation time (default: 3000ms)
}

export const DEFAULT_TIMING: TimingConfig = {
  buildDuration: 900,
  peakDuration: 1300,
  decayDuration: 800,
  totalDuration: 3000,
}
