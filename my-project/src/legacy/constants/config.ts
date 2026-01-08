/**
 * Configuration constants for the Story Portal
 */

import type { SteamLocation } from '../types'

// === TEST MODE FLAGS ===
export const TEST_MODE = false
export const DISABLE_PANEL_ANIMATION = true

// === ELECTRICITY EFFECT CONFIGURATION ===
export const ELECTRICITY_DEBUG = false

export const ELECTRICITY_CONFIG = {
  // === DETERMINISTIC MODE (for iteration pipeline) ===
  // Set to a number to enable repeatable bolt patterns for comparison.
  // Set to null for random (production) behavior.
  // When enabled, call resetDeterministicRandom() at effect start.
  deterministicSeed: 42 as number | null, // 42 = iteration mode, null = production mode
  // === EFFECT TIMING ===
  // NOTE: scenario.json is the source of truth for capture pipeline timing.
  // These values are used by:
  //   - useWheelSelection.ts (effect duration, topic swap delay)
  effectDurationMs: 8000, // Iter 42: Even longer effect (8 seconds)
  topicSwapDelayMs: 2000, // When wheel topics actually swap
  // Capture timing is defined in scenario.json (1200-2000ms peak-only window)
  // Calibrated 2025-12-24 for mask alignment and peak stability

  // Bolt structure - more dense with varied secondary bolts
  numMainBolts: 24, // Iter 37: More bolts for density
  boltThicknessMin: 0.8, // THICKER main bolts for chunky look
  boltThicknessMax: 1.4,
  branchThicknessMin: 0.4, // THICKER branches
  branchThicknessMax: 0.7,
  branchesPerBoltMin: 6, // Irregular branching
  branchesPerBoltMax: 12,
  subBranchChance: 0.65, // Sub-branch probability

  // Animation speeds
  boltSpeedMin: 2.0,
  boltSpeedMax: 4.0,
  jitterSpeedMin: 5.0,
  jitterSpeedMax: 10.0,
  microFlickerAmount: 0.25, // Per-frame thickness variation

  // Per-bolt opacity animation (appear/disappear dynamically)
  boltFadeInSpeed: 0.08, // How fast bolts fade in
  boltFadeOutSpeed: 0.05, // How fast bolts fade out
  boltOnDurationMin: 0.3, // Min time bolt stays visible (seconds)
  boltOnDurationMax: 1.2, // Max time bolt stays visible
  boltOffDurationMin: 0.1, // Min time bolt stays hidden
  boltOffDurationMax: 0.6, // Max time bolt stays hidden

  // Energy surge cycles (3-second cycles: build, peak, calm)
  surgeCycleDuration: 3.0, // Full cycle in seconds
  surgeBuildPhase: 0.4, // 0-40%: energy builds
  surgePeakPhase: 0.6, // 40-60%: peak intensity
  // 60-100%: calm phase
  surgePeakBrightness: 1.35, // Brightness multiplier at peak
  surgePeakWidth: 1.25, // Bolt width multiplier at peak
  surgeBaseBrightness: 0.85, // Brightness during calm

  // Central glow with 2Hz pulse
  centerPulseFrequency: 2.0, // Hz - pulses per second
  centerPulseAmount: 0.2, // Pulse intensity variation

  // Plasma volumetric layer - Iter 37: Bigger center glow, more amber
  plasmaDensity: 0.7, // More fill
  plasmaSwirlSpeed: 0.15, // Noise animation speed
  plasmaCenterBrightness: 1.4, // BIGGER center glow
  plasmaNoiseScale: 1.8, // Slightly larger features

  // Multi-scale bloom - INCREASED for warm fill
  bloomTightRadius: 4.0, // Good tight glow
  bloomMedRadius: 9.0, // More spread
  bloomWideRadius: 15.0, // More wide
  bloomTightWeight: 0.9, // Iteration 5: Reduced from 1.3 to reveal bolt structure
  bloomMedWeight: 0.35, // Iteration 6: Reduced from 0.55 to sharpen bolts
  bloomWideWeight: 0.35, // Good wide
  rimBloomBoost: 1.4, // Good rim boost

  // Colors - Bright golden bolts for visibility
  coreColor: [0.85, 0.65, 0.25] as [number, number, number], // Bright golden - primary bolts
  midColor: [0.75, 0.55, 0.2] as [number, number, number], // Medium golden
  outerColor: [0.6, 0.4, 0.15] as [number, number, number], // Darker golden for depth
  plasmaInner: [0.7, 0.45, 0.15] as [number, number, number], // Warm golden plasma
  plasmaOuter: [0.4, 0.25, 0.08] as [number, number, number], // Deep amber outer

  // Glass reflection layer
  glassOpacity: 0.12, // Subtle glass overlay
  glassReflectionStrength: 0.08, // Reflection highlight
  glassBlur: 0.5, // Slight blur for depth

  // === R3F LightningStrike Parameters ===
  // These control the three-stdlib LightningStrike geometry
  lightningRadius0: 0.025, // Iter 26: Moderate thickness (was 0.015 too thin, 0.04 too thick)
  lightningRadius1: 0.008, // Iter 26: Tapered edge
  lightningMinRadius: 0.005, // Minimum radius before termination
  lightningMaxIterations: 7, // Recursion depth for segments
  lightningRoughness: 0.9, // 0-1: how jagged/erratic the path (higher = more jagged)
  lightningStraightness: 0.65, // 0-1: how linear vs meandering (higher = straighter)
  lightningRamificationMin: 4, // Minimum branch count per bolt
  lightningRamificationMax: 8, // Maximum branch count per bolt
  lightningRecursionProbability: 0.6, // Chance of sub-branches
  lightningMaxSubrayRecursion: 2, // Max depth for sub-branches
  lightningTimeScaleMin: 0.8, // Animation speed variation (min)
  lightningTimeScaleMax: 1.2, // Animation speed variation (max)
  lightningSubrayPeriod: 2.0, // Sub-ray animation period
  lightningSubrayDutyCycle: 0.5, // Sub-ray on/off ratio

  // R3F Bloom post-processing - Updated for APNG reference match
  r3fBloomIntensity: 0.3, // Keep low
  r3fBloomLuminanceThreshold: 0.6, // High threshold
  r3fBloomLuminanceSmoothing: 0.5,
  r3fBloomRadius: 20, // Baseline radius in pixels, scales to ~35px at peak with formula: 20 + (intensity * 15)

  // R3F Portal dimensions
  r3fPortalRadius: 1.8, // World units for bolt reach

  // Compositing - WARM FILL with orange color
  globalIntensity: 1.5, // Iter 28b: Moderate intensity
  toneMapExposure: 3.2, // Iter 28b: Standard exposure
  portalRadius: 0.5, // Standard portal radius
  centerGlowStrength: 0.62, // Iter 28b: Moderate center glow
} as const

export type ElectricityConfigType = typeof ELECTRICITY_CONFIG

// === STEAM SPAWN LOCATIONS ===
export const STEAM_LOCATIONS: SteamLocation[] = [
  // Top Left Vent - the cross/wheel shaped vent (all openings)
  { id: 'vent-tl-1', left: '26%', top: '11%', type: 'vent' },
  { id: 'vent-tl-2', left: '27.5%', top: '11%', type: 'vent' },
  { id: 'vent-tl-3', left: '29%', top: '13%', type: 'vent' },
  { id: 'vent-tl-4', left: '29%', top: '15%', type: 'vent' },
  { id: 'vent-tl-5', left: '27.5%', top: '17%', type: 'vent' },
  { id: 'vent-tl-6', left: '26%', top: '17%', type: 'vent' },
  { id: 'vent-tl-7', left: '24.5%', top: '15%', type: 'vent' },
  { id: 'vent-tl-8', left: '24.5%', top: '13%', type: 'vent' },
  { id: 'vent-tl-9', left: '27%', top: '14%', type: 'vent' },

  // Top Left Vent - slightly to the right (~15px)
  { id: 'vent-tl2-1', left: '28%', top: '11%', type: 'vent' },
  { id: 'vent-tl2-2', left: '29.5%', top: '11%', type: 'vent' },
  { id: 'vent-tl2-3', left: '31%', top: '13%', type: 'vent' },
  { id: 'vent-tl2-4', left: '31%', top: '15%', type: 'vent' },
  { id: 'vent-tl2-5', left: '29.5%', top: '17%', type: 'vent' },
  { id: 'vent-tl2-6', left: '28%', top: '17%', type: 'vent' },
  { id: 'vent-tl2-7', left: '29%', top: '14%', type: 'vent' },

  // Bottom Right Vent - horizontal slotted vent (all from openings)
  { id: 'vent-br-1', right: '16%', bottom: '18.5%', type: 'vent' },
  { id: 'vent-br-2', right: '18%', bottom: '18.5%', type: 'vent' },
  { id: 'vent-br-3', right: '20%', bottom: '18.5%', type: 'vent' },
  { id: 'vent-br-4', right: '17%', bottom: '18.75%', type: 'vent' },
  { id: 'vent-br-5', right: '19%', bottom: '18.75%', type: 'vent' },
  { id: 'vent-br-6', right: '21%', bottom: '18.75%', type: 'vent' },
  { id: 'vent-br-7', right: '16.5%', bottom: '18.5%', type: 'vent' },
  { id: 'vent-br-8', right: '18.5%', bottom: '18.5%', type: 'vent' },
  // First extension left
  { id: 'vent-br-9', right: '22%', bottom: '18.5%', type: 'vent' },
  { id: 'vent-br-10', right: '24%', bottom: '18.5%', type: 'vent' },
  { id: 'vent-br-11', right: '23%', bottom: '18.75%', type: 'vent' },
  { id: 'vent-br-12', right: '25%', bottom: '18.75%', type: 'vent' },
  { id: 'vent-br-13', right: '20.5%', bottom: '18.5%', type: 'vent' },
  { id: 'vent-br-14', right: '22.5%', bottom: '18.5%', type: 'vent' },
  // Second extension left
  { id: 'vent-br-15', right: '26%', bottom: '18.5%', type: 'vent' },
  { id: 'vent-br-16', right: '27%', bottom: '18.75%', type: 'vent' },
  { id: 'vent-br-17', right: '24.5%', bottom: '18.5%', type: 'vent' },
  { id: 'vent-br-18', right: '26.5%', bottom: '18.5%', type: 'vent' },
]

// === DEFAULT TEXT EFFECT CONFIG ===
export const DEFAULT_TEXT_EFFECT_CONFIG = {
  // Extrusion geometry
  extrudeDepth: 7,
  extrudeOffsetX: -0.05,
  extrudeOffsetY: -0.05,
  extrudeMaxOffset: 7,

  // Extrusion colors (base/darkest)
  extrudeBaseR: 188,
  extrudeBaseG: 132,
  extrudeBaseB: 59,

  // Extrusion color step
  extrudeStepR: 17,
  extrudeStepG: 4,
  extrudeStepB: 0,

  // Front face gradient
  faceTopColor: '#f2dfc0',
  faceMidColor: '#e3bf7d',
  faceBottomColor: '#f18741',
  faceGradientMidStop: 45,

  // Bevel highlight
  highlightEnabled: true,
  highlightTopColor: '#e8d4b8',
  highlightTopOpacity: 0.8,
  highlightMidColor: '#d4b892',
  highlightMidOpacity: 0.25,
  highlightMidStop: 30,
  highlightBottomColor: '#8b7355',
  highlightBottomOpacity: 0.25,

  // Text shadow
  textShadowEnabled: true,
  textShadowOffsetX: 0,
  textShadowOffsetY: 2,
  textShadowBlur: 1.5,
  textShadowColor: '#1a1008',
  textShadowOpacity: 1,

  // Outer stroke
  outerStrokeEnabled: true,
  outerStrokeColor: '#523e21',
  outerStrokeWidth: 2,

  // Texture overlay
  textureOverlayEnabled: true,
  textureOverlayOpacity: 0.85,
  textureBlendMode: 'hard-light',
  textureGradientEnabled: true,
  textureGradientType: 'horizontal' as const,
  textureGradientTopOpacity: 1,
  textureGradientMidOpacity: 0.7,
  textureGradientBottomOpacity: 0.25,
  textureGradientMidStop: 50,
} as const

// === DEFAULT BUTTON SHADOW CONFIG ===
export const DEFAULT_BUTTON_SHADOW_CONFIG = {
  enabled: true,
  offsetX: -5,
  offsetY: 6,
  blur: 17,
  spread: 0,
  color: '#000000',
  opacity: 0.6,
  layers: 4,
  layerMult: 1.5,
} as const
