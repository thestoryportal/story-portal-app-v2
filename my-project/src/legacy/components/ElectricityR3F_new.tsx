/**
 * ElectricityR3F - React Three Fiber electricity effect
 *
 * Declarative Three.js scene using R3F for the portal electricity animation.
 * Uses LightningStrike geometry with Bloom post-processing.
 */

import { useRef, useMemo, useEffect, useState, useCallback } from 'react'
import { createPortal } from 'react-dom'
import { Canvas, useFrame } from '@react-three/fiber'
import { EffectComposer, Bloom } from '@react-three/postprocessing'
import { LightningStrike, type RayParameters } from 'three-stdlib'
import * as THREE from 'three'
import { useControls, folder, button, Leva } from 'leva'
import { ELECTRICITY_CONFIG } from '../constants'

// Debug mode - set to true to show controls panel
const SHOW_PLASMA_CONTROLS = true
// Playground mode - effect stays on forever for tweaking
const PLASMA_PLAYGROUND_MODE = true

// LocalStorage key for layer persistence
const LAYER_STORAGE_KEY = 'plasma-fx-layers'
// Maximum layers per element type
const MAX_LAYERS_PER_TYPE = 10

// =============================================================================
// LAYER CONFIG INTERFACES - Full Independence (each layer has ALL controls)
// =============================================================================

/**
 * Plasma Layer Configuration
 * Each layer is a complete, independent instance with all shader parameters
 */
interface PlasmaLayerConfig {
  id: string
  name: string
  enabled: boolean

  // Position & Blending
  zDepth: number
  baseOpacity: number
  noiseOffset: number
  colorMult: [number, number, number]

  // Regional Colors (per-layer) - hex strings
  coreColor: string
  innerColor: string
  midColor: string
  outerColor: string
  hotAmberColor: string

  // Chaos Controls (per-layer)
  colorChaos: number
  opacityChaos: number
  centerChaos: number
  chaosSpeed: number
  chaosScale: number

  // HSL Modifiers (per-layer)
  hueShift: number
  saturationMult: number
  brightnessMult: number
  colorTemperature: number

  // Master controls (per-layer)
  glowMult: number
  opacityMult: number

  // Vortex (per-layer)
  vortexEnabled: boolean
  vortexSpeed: number
  vortexTwist: number
  pullStrength: number
  pullPulse: number

  // Tendrils (per-layer)
  tendrilsEnabled: boolean
  numTendrils: number
  tendrilSharpness: number
  tendrilSpeed: number
  tendrilOpacity: number

  // Clouds (per-layer)
  cloudScale: number
  cloudSpeed: number
  wispScale: number
  wispSpeed: number
  emberScale: number
  emberSpeed: number

  // Core Glow (per-layer)
  coreGlowStrength: number
  coreGlowFalloff: number

  // Edge Falloff (per-layer)
  edgeFalloffStart: number
  edgeFalloffEnd: number
  falloffCurve: number

  // Animation (per-layer)
  globalSpeed: number
}

/**
 * Bolt Layer Configuration
 * Each bolt layer can have its own count, colors, and geometry
 */
interface BoltLayerConfig {
  id: string
  name: string
  enabled: boolean
  count: number
  primaryColor: string
  secondaryColor: string
  glowColor: string
  primaryOpacity: number
  secondaryOpacity: number
  glowIntensity: number
  thicknessScale: number
  lengthScale: number
  roughness: number
  straightness: number
}

/**
 * Rim Layer Configuration
 */
interface RimLayerConfig {
  id: string
  name: string
  enabled: boolean
  opacity: number
  innerEdge: number
  outerEdge: number
  chromaticAberration: number
  flicker: number
  color1: string
  color2: string
  zDepth: number
}

/**
 * Outer Glow Layer Configuration
 */
interface OuterGlowLayerConfig {
  id: string
  name: string
  enabled: boolean
  size: number
  intensity: number
  color: string
  softness: number
  zDepth: number
}

/**
 * Complete Layer State - contains all layer arrays
 */
interface LayerState {
  plasma: PlasmaLayerConfig[]
  bolts: BoltLayerConfig[]
  rim: RimLayerConfig[]
  outerGlow: OuterGlowLayerConfig[]
}

// =============================================================================
// DEFAULT LAYER CONFIGURATIONS
// These match the current hardcoded 5 plasma layers exactly
// =============================================================================

function createDefaultPlasmaLayer(index: number, overrides: Partial<PlasmaLayerConfig> = {}): PlasmaLayerConfig {
  return {
    id: `plasma-${index}-${Date.now()}`,
    name: `Layer ${index + 1}`,
    enabled: true,

    // Position & Blending (defaults)
    zDepth: -0.5,
    baseOpacity: 0.2,
    noiseOffset: 0,
    colorMult: [1, 1, 1],

    // Regional Colors
    coreColor: '#FEF6A4',
    innerColor: '#ff6a00',
    midColor: '#C67E16',
    outerColor: '#844913',
    hotAmberColor: '#e6801a',

    // Chaos Controls
    colorChaos: 0,
    opacityChaos: 0,
    centerChaos: 0,
    chaosSpeed: 0.5,
    chaosScale: 3.0,

    // HSL Modifiers
    hueShift: 0,
    saturationMult: 1.0,
    brightnessMult: 1.0,
    colorTemperature: 0,

    // Master
    glowMult: 1.5,
    opacityMult: 1.0,

    // Vortex
    vortexEnabled: true,
    vortexSpeed: 0.12,
    vortexTwist: 2.5,
    pullStrength: 0.15,
    pullPulse: 0.3,

    // Tendrils
    tendrilsEnabled: true,
    numTendrils: 8,
    tendrilSharpness: 4,
    tendrilSpeed: 0.2,
    tendrilOpacity: 0.25,

    // Clouds
    cloudScale: 2.0,
    cloudSpeed: 0.05,
    wispScale: 4.0,
    wispSpeed: 0.12,
    emberScale: 12.0,
    emberSpeed: 0.15,

    // Core Glow
    coreGlowStrength: 0.4,
    coreGlowFalloff: 2.5,

    // Edge Falloff
    edgeFalloffStart: 0.7,
    edgeFalloffEnd: 1.1,
    falloffCurve: 0.6,

    // Animation
    globalSpeed: 1.0,

    ...overrides,
  }
}

function createDefaultBoltLayer(index: number, overrides: Partial<BoltLayerConfig> = {}): BoltLayerConfig {
  return {
    id: `bolt-${index}-${Date.now()}`,
    name: `Bolt Layer ${index + 1}`,
    enabled: true,
    count: index === 0 ? 10 : 14, // Primary: 10, Secondary: 14
    primaryColor: '#F0C058',
    secondaryColor: '#844913',
    glowColor: '#FFD700',
    primaryOpacity: 0.45,
    secondaryOpacity: 0.2,
    glowIntensity: 1.0,
    thicknessScale: index === 0 ? 1.3 : 0.25,
    lengthScale: index === 0 ? 1.0 : 0.45,
    roughness: 0.9,
    straightness: 0.65,
    ...overrides,
  }
}

function createDefaultRimLayer(index: number, overrides: Partial<RimLayerConfig> = {}): RimLayerConfig {
  return {
    id: `rim-${index}-${Date.now()}`,
    name: `Rim Layer ${index + 1}`,
    enabled: true,
    opacity: 0.5,
    innerEdge: 0.3,
    outerEdge: 0.95,
    chromaticAberration: 0.015,
    flicker: 0.4,
    color1: '#cc4400',
    color2: '#881100',
    zDepth: -2.5,
    ...overrides,
  }
}

function createDefaultOuterGlowLayer(index: number, overrides: Partial<OuterGlowLayerConfig> = {}): OuterGlowLayerConfig {
  return {
    id: `outerglow-${index}-${Date.now()}`,
    name: `Outer Glow ${index + 1}`,
    enabled: false, // Disabled by default
    size: 0.15,
    intensity: 0.3,
    color: '#FF6A00',
    softness: 0.5,
    zDepth: -3.0,
    ...overrides,
  }
}

/**
 * Get the default layer state that matches current hardcoded implementation
 */
function getDefaultLayers(): LayerState {
  return {
    plasma: [
      // Layer 1: Deep base - darker, slower
      createDefaultPlasmaLayer(0, {
        name: 'Deep Base',
        zDepth: -2.0,
        noiseOffset: 0,
        baseOpacity: 0.25,
        colorMult: [0.8, 0.75, 0.7],
      }),
      // Layer 2: Main color - primary layer
      createDefaultPlasmaLayer(1, {
        name: 'Main Color',
        zDepth: -1.4,
        noiseOffset: 0.7,
        baseOpacity: 0.2,
        colorMult: [1, 1, 1],
      }),
      // Layer 3: Brighter variation - adds highlights
      createDefaultPlasmaLayer(2, {
        name: 'Highlights',
        zDepth: -1.0,
        noiseOffset: 1.4,
        baseOpacity: 0.18,
        colorMult: [1.2, 1.1, 1],
      }),
      // Layer 4: Warm shift - adds color variation
      createDefaultPlasmaLayer(3, {
        name: 'Warm Shift',
        zDepth: -0.6,
        noiseOffset: 2.1,
        baseOpacity: 0.15,
        colorMult: [1.1, 1, 1.3],
      }),
      // Layer 5: Red shift - deepest color accent
      createDefaultPlasmaLayer(4, {
        name: 'Red Shift',
        zDepth: -0.2,
        noiseOffset: 2.8,
        baseOpacity: 0.12,
        colorMult: [1.0, 0.7, 1.5],
      }),
    ],
    bolts: [
      // Primary bolts layer
      createDefaultBoltLayer(0, { name: 'Primary Bolts' }),
      // Secondary bolts layer
      createDefaultBoltLayer(1, { name: 'Secondary Bolts' }),
    ],
    rim: [
      // Single rim layer
      createDefaultRimLayer(0, { name: 'Rim Glow' }),
    ],
    outerGlow: [
      // Single outer glow layer (disabled by default)
      createDefaultOuterGlowLayer(0, { name: 'Outer Glow' }),
    ],
  }
}

/**
 * Custom hook for managing layer state with localStorage persistence
 */
function useLayerState() {
  // Initialize from localStorage or defaults
  const [layers, setLayers] = useState<LayerState>(() => {
    try {
      const saved = localStorage.getItem(LAYER_STORAGE_KEY)
      if (saved) {
        const parsed = JSON.parse(saved) as LayerState
        // Validate structure
        if (parsed.plasma && parsed.bolts && parsed.rim && parsed.outerGlow) {
          return parsed
        }
      }
    } catch (e) {
      console.warn('Failed to load layer state from localStorage:', e)
    }
    return getDefaultLayers()
  })

  // Persist to localStorage on every change
  useEffect(() => {
    try {
      localStorage.setItem(LAYER_STORAGE_KEY, JSON.stringify(layers))
    } catch (e) {
      console.warn('Failed to save layer state to localStorage:', e)
    }
  }, [layers])

  // Add a new layer
  const addLayer = useCallback((type: keyof LayerState) => {
    setLayers((prev) => {
      const current = prev[type]
      if (current.length >= MAX_LAYERS_PER_TYPE) {
        console.warn(`Maximum ${MAX_LAYERS_PER_TYPE} layers reached for ${type}`)
        return prev
      }

      const newIndex = current.length
      let newLayer: PlasmaLayerConfig | BoltLayerConfig | RimLayerConfig | OuterGlowLayerConfig

      switch (type) {
        case 'plasma':
          newLayer = createDefaultPlasmaLayer(newIndex)
          break
        case 'bolts':
          newLayer = createDefaultBoltLayer(newIndex)
          break
        case 'rim':
          newLayer = createDefaultRimLayer(newIndex)
          break
        case 'outerGlow':
          newLayer = createDefaultOuterGlowLayer(newIndex, { enabled: true })
          break
      }

      return {
        ...prev,
        [type]: [...current, newLayer],
      }
    })
  }, [])

  // Remove a layer by ID
  const removeLayer = useCallback((type: keyof LayerState, id: string) => {
    setLayers((prev) => {
      const current = prev[type]
      if (current.length <= 1) {
        console.warn(`Cannot remove last ${type} layer`)
        return prev
      }

      return {
        ...prev,
        [type]: current.filter((layer) => layer.id !== id),
      }
    })
  }, [])

  // Update a specific layer
  const updateLayer = useCallback(
    <T extends keyof LayerState>(
      type: T,
      id: string,
      updates: Partial<LayerState[T][number]>
    ) => {
      setLayers((prev) => ({
        ...prev,
        [type]: prev[type].map((layer) =>
          layer.id === id ? { ...layer, ...updates } : layer
        ),
      }))
    },
    []
  )

  // Reset to defaults
  const resetToDefaults = useCallback(() => {
    setLayers(getDefaultLayers())
  }, [])

  return {
    layers,
    addLayer,
    removeLayer,
    updateLayer,
    resetToDefaults,
  }
}

// =============================================================================
// PER-LAYER REFS SYSTEM
// Each layer gets its own ref for use in R3F useFrame
// =============================================================================

// Parse hex color to RGB array (0-1 range)
function hexToRgb(hex: string): [number, number, number] {
  const result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex)
  return result
    ? [
        parseInt(result[1], 16) / 255,
        parseInt(result[2], 16) / 255,
        parseInt(result[3], 16) / 255,
      ]
    : [0.18, 0.08, 0.03]
}

/**
 * Convert PlasmaLayerConfig to PlasmaControlsRef format
 * This bridges the layer state to the shader uniform structure
 */
function plasmaLayerToRef(layer: PlasmaLayerConfig): PlasmaControlsRef {
  return {
    // Regional colors
    coreColor: hexToRgb(layer.coreColor),
    innerColor: hexToRgb(layer.innerColor),
    midColor: hexToRgb(layer.midColor),
    outerColor: hexToRgb(layer.outerColor),
    hotAmber: hexToRgb(layer.hotAmberColor),

    // Chaos
    colorChaos: layer.colorChaos,
    opacityChaos: layer.opacityChaos,
    centerChaos: layer.centerChaos,
    chaosSpeed: layer.chaosSpeed,
    chaosScale: layer.chaosScale,

    // HSL
    hueShift: layer.hueShift,
    saturationMult: layer.saturationMult,
    brightnessMult: layer.brightnessMult,
    colorTemperature: layer.colorTemperature,

    // Master
    glowMult: layer.glowMult,
    opacityMult: layer.opacityMult,

    // Vortex
    vortexEnabled: layer.vortexEnabled,
    vortexSpeed: layer.vortexSpeed,
    vortexTwist: layer.vortexTwist,
    pullStrength: layer.pullStrength,
    pullPulse: layer.pullPulse,

    // Tendrils
    tendrilsEnabled: layer.tendrilsEnabled,
    numTendrils: layer.numTendrils,
    tendrilSharpness: layer.tendrilSharpness,
    tendrilSpeed: layer.tendrilSpeed,
    tendrilOpacity: layer.tendrilOpacity,

    // Clouds
    cloudScale: layer.cloudScale,
    cloudSpeed: layer.cloudSpeed,
    wispScale: layer.wispScale,
    wispSpeed: layer.wispSpeed,
    emberScale: layer.emberScale,
    emberSpeed: layer.emberSpeed,

    // Core glow
    coreGlowStrength: layer.coreGlowStrength,
    coreGlowFalloff: layer.coreGlowFalloff,

    // Edge falloff
    edgeFalloffStart: layer.edgeFalloffStart,
    edgeFalloffEnd: layer.edgeFalloffEnd,
    falloffCurve: layer.falloffCurve,

    // Animation
    globalSpeed: layer.globalSpeed,
  }
}

/**
 * Convert BoltLayerConfig to BoltControlsRef format
 */
function boltLayerToRef(layer: BoltLayerConfig): BoltControlsRef {
  return {
    primaryColor: hexToRgb(layer.primaryColor),
    secondaryColor: hexToRgb(layer.secondaryColor),
    glowColor: hexToRgb(layer.glowColor),
    primaryOpacity: layer.primaryOpacity,
    secondaryOpacity: layer.secondaryOpacity,
    glowIntensity: layer.glowIntensity,
  }
}

/**
 * Rim controls ref interface
 */
interface RimControlsRef {
  opacity: number
  start: number
  end: number
  aberration: number
  flicker: number
  color1: [number, number, number]
  color2: [number, number, number]
  enabled: boolean
}

/**
 * Convert RimLayerConfig to RimControlsRef format
 */
function rimLayerToRef(layer: RimLayerConfig): RimControlsRef {
  return {
    opacity: layer.opacity,
    start: layer.innerEdge,
    end: layer.outerEdge,
    aberration: layer.chromaticAberration,
    flicker: layer.flicker,
    color1: hexToRgb(layer.color1),
    color2: hexToRgb(layer.color2),
    enabled: layer.enabled,
  }
}

/**
 * Convert OuterGlowLayerConfig to OuterGlowControlsRef format
 */
function outerGlowLayerToRef(layer: OuterGlowLayerConfig): OuterGlowControlsRef {
  return {
    enabled: layer.enabled,
    amount: layer.size,
    intensity: layer.intensity,
    color: hexToRgb(layer.color),
    softness: layer.softness,
  }
}

/**
 * Hook that creates per-layer refs from layer state
 * Returns Maps of refs keyed by layer ID
 */
function useLayerRefs(layers: LayerState) {
  // Create Maps to store refs for each layer
  const plasmaRefsMap = useRef<Map<string, React.RefObject<PlasmaControlsRef>>>(new Map())
  const boltRefsMap = useRef<Map<string, React.RefObject<BoltControlsRef>>>(new Map())
  const rimRefsMap = useRef<Map<string, React.RefObject<RimControlsRef>>>(new Map())
  const outerGlowRefsMap = useRef<Map<string, React.RefObject<OuterGlowControlsRef>>>(new Map())

  // =============================================================================
  // INTENTIONAL REF ACCESS DURING RENDER
  // This is the "ref bridge" pattern that bridges React state to R3F useFrame.
  // The refs are containers that hold the layer state values, and useFrame
  // reads from these refs on every animation frame.
  // =============================================================================

  /* eslint-disable react-hooks/refs -- Intentional ref bridge pattern for R3F animation */
  // Plasma refs - sync with layer state
  const currentPlasmaIds = new Set(layers.plasma.map(l => l.id))
   
  plasmaRefsMap.current.forEach((_, id) => {  
    if (!currentPlasmaIds.has(id)) {
      plasmaRefsMap.current.delete(id)  
    }
  })
  layers.plasma.forEach(layer => {
    if (!plasmaRefsMap.current.has(layer.id)) {  
      plasmaRefsMap.current.set(layer.id, { current: plasmaLayerToRef(layer) })  
    }
  })

  // Bolt refs - sync with layer state
  const currentBoltIds = new Set(layers.bolts.map(l => l.id))
  boltRefsMap.current.forEach((_, id) => {  
    if (!currentBoltIds.has(id)) {
      boltRefsMap.current.delete(id)  
    }
  })
  layers.bolts.forEach(layer => {
    if (!boltRefsMap.current.has(layer.id)) {  
      boltRefsMap.current.set(layer.id, { current: boltLayerToRef(layer) })  
    }
  })

  // Rim refs - sync with layer state
  const currentRimIds = new Set(layers.rim.map(l => l.id))
  rimRefsMap.current.forEach((_, id) => {  
    if (!currentRimIds.has(id)) {
      rimRefsMap.current.delete(id)  
    }
  })
  layers.rim.forEach(layer => {
    if (!rimRefsMap.current.has(layer.id)) {  
      rimRefsMap.current.set(layer.id, { current: rimLayerToRef(layer) })  
    }
  })

  // Outer glow refs - sync with layer state
  const currentOuterGlowIds = new Set(layers.outerGlow.map(l => l.id))
  outerGlowRefsMap.current.forEach((_, id) => {  
    if (!currentOuterGlowIds.has(id)) {
      outerGlowRefsMap.current.delete(id)  
    }
  })
  layers.outerGlow.forEach(layer => {
    if (!outerGlowRefsMap.current.has(layer.id)) {  
      outerGlowRefsMap.current.set(layer.id, { current: outerGlowLayerToRef(layer) })  
    }
  })

  // Update all refs with current layer values (for Leva reactivity)
  // This runs on every render to keep refs in sync with layer state
  layers.plasma.forEach(layer => {
    const ref = plasmaRefsMap.current.get(layer.id)  
    if (ref) {
      ref.current = plasmaLayerToRef(layer)  
    }
  })
  layers.bolts.forEach(layer => {
    const ref = boltRefsMap.current.get(layer.id)  
    if (ref) {
      ref.current = boltLayerToRef(layer)  
    }
  })
  layers.rim.forEach(layer => {
    const ref = rimRefsMap.current.get(layer.id)  
    if (ref) {
      ref.current = rimLayerToRef(layer)  
    }
  })
  layers.outerGlow.forEach(layer => {
    const ref = outerGlowRefsMap.current.get(layer.id)
    if (ref) {
      ref.current = outerGlowLayerToRef(layer)
    }
  })

  return {
    plasmaRefs: plasmaRefsMap.current,
    boltRefs: boltRefsMap.current,
    rimRefs: rimRefsMap.current,
    outerGlowRefs: outerGlowRefsMap.current,
  }
  /* eslint-enable react-hooks/refs */
}

// =============================================================================
// DYNAMIC LEVA CONTROLS GENERATORS
// Generate control schemas for each layer type
// =============================================================================

type UpdateLayerFn = <T extends keyof LayerState>(
  type: T,
  id: string,
  updates: Partial<LayerState[T][number]>
) => void

/**
 * Generate Leva controls for a single plasma layer
 */
function generatePlasmaLayerSchema(
  layer: PlasmaLayerConfig,
  onUpdate: (updates: Partial<PlasmaLayerConfig>) => void,
  onRemove: () => void,
  canRemove: boolean
) {
  return folder({
    // Layer Settings
    '⚙️ Settings': folder({
      name: { value: layer.name, label: 'Name', onChange: (v: string) => onUpdate({ name: v }) },
      enabled: { value: layer.enabled, label: 'Enabled', onChange: (v: boolean) => onUpdate({ enabled: v }) },
      zDepth: { value: layer.zDepth, min: -5, max: 0, step: 0.1, label: 'Z-Depth', onChange: (v: number) => onUpdate({ zDepth: v }) },
      baseOpacity: { value: layer.baseOpacity, min: 0, max: 1, step: 0.01, label: 'Base Opacity', onChange: (v: number) => onUpdate({ baseOpacity: v }) },
      noiseOffset: { value: layer.noiseOffset, min: 0, max: 5, step: 0.1, label: 'Noise Offset', onChange: (v: number) => onUpdate({ noiseOffset: v }) },
    }),

    // Regional Colors
    '🌈 Colors': folder({
      coreColor: { value: layer.coreColor, label: '☀️ Core', onChange: (v: string) => onUpdate({ coreColor: v }) },
      innerColor: { value: layer.innerColor, label: '🔥 Inner', onChange: (v: string) => onUpdate({ innerColor: v }) },
      midColor: { value: layer.midColor, label: '🔶 Mid', onChange: (v: string) => onUpdate({ midColor: v }) },
      outerColor: { value: layer.outerColor, label: '🌑 Outer', onChange: (v: string) => onUpdate({ outerColor: v }) },
      hotAmberColor: { value: layer.hotAmberColor, label: '✨ Accent', onChange: (v: string) => onUpdate({ hotAmberColor: v }) },
    }, { collapsed: true }),

    // Chaos Controls
    '🌀 Chaos': folder({
      colorChaos: { value: layer.colorChaos, min: 0, max: 1, step: 0.05, label: 'Color', onChange: (v: number) => onUpdate({ colorChaos: v }) },
      opacityChaos: { value: layer.opacityChaos, min: 0, max: 1, step: 0.05, label: 'Opacity', onChange: (v: number) => onUpdate({ opacityChaos: v }) },
      centerChaos: { value: layer.centerChaos, min: 0, max: 1, step: 0.05, label: 'Center', onChange: (v: number) => onUpdate({ centerChaos: v }) },
      chaosSpeed: { value: layer.chaosSpeed, min: 0, max: 2, step: 0.1, label: 'Speed', onChange: (v: number) => onUpdate({ chaosSpeed: v }) },
      chaosScale: { value: layer.chaosScale, min: 0.5, max: 10, step: 0.5, label: 'Scale', onChange: (v: number) => onUpdate({ chaosScale: v }) },
    }, { collapsed: true }),

    // HSL Modifiers
    '🎚️ HSL': folder({
      hueShift: { value: layer.hueShift, min: -180, max: 180, step: 5, label: 'Hue Shift', onChange: (v: number) => onUpdate({ hueShift: v }) },
      saturationMult: { value: layer.saturationMult, min: 0, max: 2, step: 0.1, label: 'Saturation', onChange: (v: number) => onUpdate({ saturationMult: v }) },
      brightnessMult: { value: layer.brightnessMult, min: 0, max: 2, step: 0.1, label: 'Brightness', onChange: (v: number) => onUpdate({ brightnessMult: v }) },
      colorTemperature: { value: layer.colorTemperature, min: -1, max: 1, step: 0.1, label: 'Temperature', onChange: (v: number) => onUpdate({ colorTemperature: v }) },
    }, { collapsed: true }),

    // Vortex
    '🌀 Vortex': folder({
      vortexEnabled: { value: layer.vortexEnabled, label: 'Enable', onChange: (v: boolean) => onUpdate({ vortexEnabled: v }) },
      vortexSpeed: { value: layer.vortexSpeed, min: 0, max: 0.5, step: 0.01, label: 'Speed', onChange: (v: number) => onUpdate({ vortexSpeed: v }) },
      vortexTwist: { value: layer.vortexTwist, min: 0, max: 8, step: 0.1, label: 'Twist', onChange: (v: number) => onUpdate({ vortexTwist: v }) },
      pullStrength: { value: layer.pullStrength, min: 0, max: 0.5, step: 0.01, label: 'Pull', onChange: (v: number) => onUpdate({ pullStrength: v }) },
      pullPulse: { value: layer.pullPulse, min: 0, max: 2, step: 0.05, label: 'Pulse', onChange: (v: number) => onUpdate({ pullPulse: v }) },
    }, { collapsed: true }),

    // Tendrils
    '👆 Tendrils': folder({
      tendrilsEnabled: { value: layer.tendrilsEnabled, label: 'Enable', onChange: (v: boolean) => onUpdate({ tendrilsEnabled: v }) },
      numTendrils: { value: layer.numTendrils, min: 2, max: 24, step: 1, label: 'Count', onChange: (v: number) => onUpdate({ numTendrils: v }) },
      tendrilSharpness: { value: layer.tendrilSharpness, min: 1, max: 10, step: 0.5, label: 'Sharpness', onChange: (v: number) => onUpdate({ tendrilSharpness: v }) },
      tendrilSpeed: { value: layer.tendrilSpeed, min: 0, max: 1, step: 0.05, label: 'Speed', onChange: (v: number) => onUpdate({ tendrilSpeed: v }) },
      tendrilOpacity: { value: layer.tendrilOpacity, min: 0, max: 1, step: 0.05, label: 'Opacity', onChange: (v: number) => onUpdate({ tendrilOpacity: v }) },
    }, { collapsed: true }),

    // Clouds
    '☁️ Clouds': folder({
      cloudScale: { value: layer.cloudScale, min: 0.5, max: 8, step: 0.1, label: 'Cloud Size', onChange: (v: number) => onUpdate({ cloudScale: v }) },
      cloudSpeed: { value: layer.cloudSpeed, min: 0, max: 0.3, step: 0.01, label: 'Cloud Speed', onChange: (v: number) => onUpdate({ cloudSpeed: v }) },
      wispScale: { value: layer.wispScale, min: 1, max: 12, step: 0.5, label: 'Wisp Size', onChange: (v: number) => onUpdate({ wispScale: v }) },
      wispSpeed: { value: layer.wispSpeed, min: 0, max: 0.5, step: 0.01, label: 'Wisp Speed', onChange: (v: number) => onUpdate({ wispSpeed: v }) },
      emberScale: { value: layer.emberScale, min: 4, max: 30, step: 1, label: 'Ember Size', onChange: (v: number) => onUpdate({ emberScale: v }) },
      emberSpeed: { value: layer.emberSpeed, min: 0, max: 0.5, step: 0.01, label: 'Ember Speed', onChange: (v: number) => onUpdate({ emberSpeed: v }) },
    }, { collapsed: true }),

    // Core Glow
    '💡 Core': folder({
      coreGlowStrength: { value: layer.coreGlowStrength, min: 0, max: 1.5, step: 0.05, label: 'Strength', onChange: (v: number) => onUpdate({ coreGlowStrength: v }) },
      coreGlowFalloff: { value: layer.coreGlowFalloff, min: 0.5, max: 5, step: 0.1, label: 'Falloff', onChange: (v: number) => onUpdate({ coreGlowFalloff: v }) },
    }, { collapsed: true }),

    // Edge Falloff
    '📐 Edge': folder({
      edgeFalloffStart: { value: layer.edgeFalloffStart, min: 0, max: 1, step: 0.05, label: 'Start', onChange: (v: number) => onUpdate({ edgeFalloffStart: v }) },
      edgeFalloffEnd: { value: layer.edgeFalloffEnd, min: 0.5, max: 1.5, step: 0.05, label: 'End', onChange: (v: number) => onUpdate({ edgeFalloffEnd: v }) },
      falloffCurve: { value: layer.falloffCurve, min: 0.1, max: 2, step: 0.1, label: 'Curve', onChange: (v: number) => onUpdate({ falloffCurve: v }) },
    }, { collapsed: true }),

    // Master controls
    '⚙️ Master': folder({
      glowMult: { value: layer.glowMult, min: 0.1, max: 5, step: 0.1, label: 'Glow', onChange: (v: number) => onUpdate({ glowMult: v }) },
      opacityMult: { value: layer.opacityMult, min: 0, max: 3, step: 0.05, label: 'Opacity', onChange: (v: number) => onUpdate({ opacityMult: v }) },
      globalSpeed: { value: layer.globalSpeed, min: 0, max: 3, step: 0.1, label: 'Speed', onChange: (v: number) => onUpdate({ globalSpeed: v }) },
    }, { collapsed: true }),

    // Delete button
    ...(canRemove ? { '🗑️ Delete Layer': button(() => onRemove()) } : {}),
  }, { collapsed: true })
}

/**
 * Generate Leva controls for a single bolt layer
 */
function generateBoltLayerSchema(
  layer: BoltLayerConfig,
  onUpdate: (updates: Partial<BoltLayerConfig>) => void,
  onRemove: () => void,
  canRemove: boolean
) {
  return folder({
    name: { value: layer.name, label: 'Name', onChange: (v: string) => onUpdate({ name: v }) },
    enabled: { value: layer.enabled, label: 'Enabled', onChange: (v: boolean) => onUpdate({ enabled: v }) },
    count: { value: layer.count, min: 1, max: 30, step: 1, label: 'Count', onChange: (v: number) => onUpdate({ count: v }) },
    primaryColor: { value: layer.primaryColor, label: 'Primary Color', onChange: (v: string) => onUpdate({ primaryColor: v }) },
    secondaryColor: { value: layer.secondaryColor, label: 'Secondary Color', onChange: (v: string) => onUpdate({ secondaryColor: v }) },
    glowColor: { value: layer.glowColor, label: 'Glow Color', onChange: (v: string) => onUpdate({ glowColor: v }) },
    primaryOpacity: { value: layer.primaryOpacity, min: 0, max: 1, step: 0.05, label: 'Primary Opacity', onChange: (v: number) => onUpdate({ primaryOpacity: v }) },
    secondaryOpacity: { value: layer.secondaryOpacity, min: 0, max: 1, step: 0.05, label: 'Secondary Opacity', onChange: (v: number) => onUpdate({ secondaryOpacity: v }) },
    glowIntensity: { value: layer.glowIntensity, min: 0, max: 3, step: 0.1, label: 'Glow Intensity', onChange: (v: number) => onUpdate({ glowIntensity: v }) },
    thicknessScale: { value: layer.thicknessScale, min: 0.1, max: 3, step: 0.1, label: 'Thickness', onChange: (v: number) => onUpdate({ thicknessScale: v }) },
    lengthScale: { value: layer.lengthScale, min: 0.1, max: 2, step: 0.1, label: 'Length', onChange: (v: number) => onUpdate({ lengthScale: v }) },
    roughness: { value: layer.roughness, min: 0, max: 1, step: 0.05, label: 'Roughness', onChange: (v: number) => onUpdate({ roughness: v }) },
    straightness: { value: layer.straightness, min: 0, max: 1, step: 0.05, label: 'Straightness', onChange: (v: number) => onUpdate({ straightness: v }) },
    ...(canRemove ? { '🗑️ Delete': button(() => onRemove()) } : {}),
  }, { collapsed: true })
}

/**
 * Generate Leva controls for a single rim layer
 */
function generateRimLayerSchema(
  layer: RimLayerConfig,
  onUpdate: (updates: Partial<RimLayerConfig>) => void,
  onRemove: () => void,
  canRemove: boolean
) {
  return folder({
    name: { value: layer.name, label: 'Name', onChange: (v: string) => onUpdate({ name: v }) },
    enabled: { value: layer.enabled, label: 'Enabled', onChange: (v: boolean) => onUpdate({ enabled: v }) },
    opacity: { value: layer.opacity, min: 0, max: 1, step: 0.05, label: 'Opacity', onChange: (v: number) => onUpdate({ opacity: v }) },
    innerEdge: { value: layer.innerEdge, min: 0, max: 0.9, step: 0.05, label: 'Inner Edge', onChange: (v: number) => onUpdate({ innerEdge: v }) },
    outerEdge: { value: layer.outerEdge, min: 0.5, max: 1.1, step: 0.05, label: 'Outer Edge', onChange: (v: number) => onUpdate({ outerEdge: v }) },
    chromaticAberration: { value: layer.chromaticAberration, min: 0, max: 0.08, step: 0.005, label: 'Chromatic', onChange: (v: number) => onUpdate({ chromaticAberration: v }) },
    flicker: { value: layer.flicker, min: 0, max: 1, step: 0.05, label: 'Flicker', onChange: (v: number) => onUpdate({ flicker: v }) },
    color1: { value: layer.color1, label: 'Color 1', onChange: (v: string) => onUpdate({ color1: v }) },
    color2: { value: layer.color2, label: 'Color 2', onChange: (v: string) => onUpdate({ color2: v }) },
    zDepth: { value: layer.zDepth, min: -5, max: 0, step: 0.1, label: 'Z-Depth', onChange: (v: number) => onUpdate({ zDepth: v }) },
    ...(canRemove ? { '🗑️ Delete': button(() => onRemove()) } : {}),
  }, { collapsed: true })
}

/**
 * Generate Leva controls for a single outer glow layer
 */
function generateOuterGlowLayerSchema(
  layer: OuterGlowLayerConfig,
  onUpdate: (updates: Partial<OuterGlowLayerConfig>) => void,
  onRemove: () => void,
  canRemove: boolean
) {
  return folder({
    name: { value: layer.name, label: 'Name', onChange: (v: string) => onUpdate({ name: v }) },
    enabled: { value: layer.enabled, label: 'Enabled', onChange: (v: boolean) => onUpdate({ enabled: v }) },
    size: { value: layer.size, min: 0, max: 0.5, step: 0.01, label: 'Size', onChange: (v: number) => onUpdate({ size: v }) },
    intensity: { value: layer.intensity, min: 0, max: 1, step: 0.05, label: 'Intensity', onChange: (v: number) => onUpdate({ intensity: v }) },
    color: { value: layer.color, label: 'Color', onChange: (v: string) => onUpdate({ color: v }) },
    softness: { value: layer.softness, min: 0, max: 1, step: 0.05, label: 'Softness', onChange: (v: number) => onUpdate({ softness: v }) },
    zDepth: { value: layer.zDepth, min: -5, max: 0, step: 0.1, label: 'Z-Depth', onChange: (v: number) => onUpdate({ zDepth: v }) },
    ...(canRemove ? { '🗑️ Delete': button(() => onRemove()) } : {}),
  }, { collapsed: true })
}

/**
 * Generate the complete Leva controls schema for all layers
 */
function generateAllLayerControls(
  layers: LayerState,
  updateLayer: UpdateLayerFn,
  addLayer: (type: keyof LayerState) => void,
  removeLayer: (type: keyof LayerState, id: string) => void,
  resetToDefaults: () => void,
  cfg: typeof ELECTRICITY_CONFIG
) {
  // Generate plasma layer controls
  const plasmaLayerControls: Record<string, ReturnType<typeof folder>> = {}
  layers.plasma.forEach((layer, index) => {
    const key = `📊 ${index + 1}: ${layer.name}`
    plasmaLayerControls[key] = generatePlasmaLayerSchema(
      layer,
      (updates) => updateLayer('plasma', layer.id, updates),
      () => removeLayer('plasma', layer.id),
      layers.plasma.length > 1
    )
  })

  // Generate bolt layer controls
  const boltLayerControls: Record<string, ReturnType<typeof folder>> = {}
  layers.bolts.forEach((layer, index) => {
    const key = `⚡ ${index + 1}: ${layer.name}`
    boltLayerControls[key] = generateBoltLayerSchema(
      layer,
      (updates) => updateLayer('bolts', layer.id, updates),
      () => removeLayer('bolts', layer.id),
      layers.bolts.length > 1
    )
  })

  // Generate rim layer controls
  const rimLayerControls: Record<string, ReturnType<typeof folder>> = {}
  layers.rim.forEach((layer, index) => {
    const key = `💫 ${index + 1}: ${layer.name}`
    rimLayerControls[key] = generateRimLayerSchema(
      layer,
      (updates) => updateLayer('rim', layer.id, updates),
      () => removeLayer('rim', layer.id),
      layers.rim.length > 1
    )
  })

  // Generate outer glow layer controls
  const outerGlowLayerControls: Record<string, ReturnType<typeof folder>> = {}
  layers.outerGlow.forEach((layer, index) => {
    const key = `🌟 ${index + 1}: ${layer.name}`
    outerGlowLayerControls[key] = generateOuterGlowLayerSchema(
      layer,
      (updates) => updateLayer('outerGlow', layer.id, updates),
      () => removeLayer('outerGlow', layer.id),
      layers.outerGlow.length > 1
    )
  })

  return {
    // Plasma Layers folder
    '🔥 Plasma Layers': folder({
      [`➕ Add Plasma (${layers.plasma.length}/${MAX_LAYERS_PER_TYPE})`]: button(() => addLayer('plasma')),
      ...plasmaLayerControls,
    }),

    // Bolt Layers folder
    '⚡ Bolt Layers': folder({
      [`➕ Add Bolts (${layers.bolts.length}/${MAX_LAYERS_PER_TYPE})`]: button(() => addLayer('bolts')),
      ...boltLayerControls,
    }),

    // Rim Layers folder
    '💫 Rim Layers': folder({
      [`➕ Add Rim (${layers.rim.length}/${MAX_LAYERS_PER_TYPE})`]: button(() => addLayer('rim')),
      ...rimLayerControls,
    }),

    // Outer Glow Layers folder
    '🌟 Outer Glow Layers': folder({
      [`➕ Add Glow (${layers.outerGlow.length}/${MAX_LAYERS_PER_TYPE})`]: button(() => addLayer('outerGlow')),
      ...outerGlowLayerControls,
    }),

    // Bloom (global) - at top level for direct access
    bloomIntensity: { value: cfg.r3fBloomIntensity, min: 0, max: 2, step: 0.05, label: '✨ Bloom Intensity' },
    bloomThreshold: { value: cfg.r3fBloomLuminanceThreshold, min: 0, max: 1, step: 0.05, label: '✨ Bloom Threshold' },
    bloomRadius: { value: cfg.r3fBloomRadius, min: 0, max: 1, step: 0.05, label: '✨ Bloom Radius' },

    // Presets folder
    '💾 Presets': folder({
      'Load Default': button(() => resetToDefaults()),
      'Reset All': button(() => resetToDefaults()),
    }),
  }
}

interface ElectricityR3FProps {
  visible: boolean
}

interface BoltControlsRef {
  primaryColor: [number, number, number]
  secondaryColor: [number, number, number]
  glowColor: [number, number, number]
  primaryOpacity: number
  secondaryOpacity: number
  glowIntensity: number
}

interface LightningBoltProps {
  angle: number
  radius: number
  startTime: number
  isPrimary?: boolean // 8 prominent bolts vs thin secondary
  thicknessScale?: number // Multiplier for bolt thickness
  lengthScale?: number // Multiplier for bolt length
  controlsRef: React.RefObject<BoltControlsRef> // Live color controls
}

/**
 * PopoutWindow - Renders children into a separate browser window
 * The window is resizable and can be positioned anywhere on screen
 */
interface PopoutWindowProps {
  children: React.ReactNode
  title?: string
  width?: number
  height?: number
  onClose?: () => void
  onBlocked?: () => void
}

// eslint-disable-next-line @typescript-eslint/no-unused-vars -- Feature ready, pending integration
function PopoutWindow({
  children,
  title = 'Plasma FX Controls',
  width = 380,
  height = 800,
  onClose,
  onBlocked,
}: PopoutWindowProps) {
  const [container, setContainer] = useState<HTMLDivElement | null>(null)
  const windowRef = useRef<Window | null>(null)

  useEffect(() => {
    // Calculate position - use screen coordinates for multi-monitor support
    // Position near the right edge of the current screen
    const screenLeft = window.screen.availLeft ?? 0
    const screenTop = window.screen.availTop ?? 0
    const screenWidth = window.screen.availWidth
    const screenHeight = window.screen.availHeight

    // Default to right side of current screen, but allow user to move anywhere
    const left = screenLeft + screenWidth - width - 50
    const top = screenTop + Math.min(100, (screenHeight - height) / 2)

    // Open the popout window with features that allow full window behavior
    const popout = window.open(
      '',
      'PlasmaFXControls',
      `width=${width},height=${height},left=${left},top=${top},resizable=yes,scrollbars=yes,menubar=no,toolbar=no,location=no,status=no`
    )

    if (!popout) {
      console.warn('Popout window blocked by browser. Using inline controls.')
      onBlocked?.()
      return
    }

    windowRef.current = popout

    // Set up the popout window document
    popout.document.title = title

    // Add base styles to the popout window
    const style = popout.document.createElement('style')
    style.textContent = `
      * {
        margin: 0;
        padding: 0;
        box-sizing: border-box;
      }
      html, body {
        width: 100%;
        height: 100%;
        background: #1a1a2e;
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        overflow: auto;
      }
      #popout-root {
        width: 100%;
        min-height: 100%;
        padding: 10px;
      }
      /* Leva overrides for popout */
      [class*="leva-"] {
        --leva-sizes-rootWidth: 100% !important;
        --leva-colors-elevation1: #252540 !important;
        --leva-colors-elevation2: #1a1a2e !important;
        --leva-colors-elevation3: #2d2d4a !important;
      }
    `
    popout.document.head.appendChild(style)

    // Copy Leva styles from main window to popout
    const mainStyles = document.querySelectorAll('style')
    mainStyles.forEach((mainStyle) => {
      if (mainStyle.textContent?.includes('leva')) {
        const clonedStyle = popout.document.createElement('style')
        clonedStyle.textContent = mainStyle.textContent
        popout.document.head.appendChild(clonedStyle)
      }
    })

    // Create container for React portal
    const rootDiv = popout.document.createElement('div')
    rootDiv.id = 'popout-root'
    popout.document.body.appendChild(rootDiv)
    // Intentional: trigger re-render after popout window is ready for portal
    setContainer(rootDiv) // eslint-disable-line react-hooks/set-state-in-effect

    // Handle window close
    const handleUnload = () => {
      onClose?.()
    }
    popout.addEventListener('beforeunload', handleUnload)

    // Cleanup on unmount
    return () => {
      popout.removeEventListener('beforeunload', handleUnload)
      popout.close()
      windowRef.current = null
    }
  }, [title, width, height, onClose, onBlocked])

  // Render children into the popout window via portal
  if (!container) return null
  return createPortal(children, container)
}

/**
 * PopoutControlsWrapper - Manages popout state and renders Leva appropriately
 * TODO: Wire up to main component to enable popout controls
 */
interface PopoutControlsWrapperProps {
  children: React.ReactNode
}

// eslint-disable-next-line @typescript-eslint/no-unused-vars -- Feature ready, pending integration
function PopoutControlsWrapper({ children }: PopoutControlsWrapperProps) {
  // Simple hide/show state - controls hidden by default to save space
  const [isVisible, setIsVisible] = useState(false)

  return (
    <>
      {/* Minimal toggle button - always visible */}
      <div style={{ position: 'fixed', top: 10, right: 10, zIndex: 9999 }}>
        <button
          onClick={() => setIsVisible(!isVisible)}
          style={{
            background: isVisible ? '#4CAF50' : '#ff6a00',
            color: 'white',
            border: 'none',
            borderRadius: 6,
            padding: '8px 12px',
            cursor: 'pointer',
            fontSize: 12,
            fontWeight: 'bold',
            boxShadow: '0 2px 8px rgba(0,0,0,0.3)',
          }}
        >
          {isVisible ? '✕ Hide Controls' : '⚡ Show Controls'}
        </button>
      </div>

      {/* Controls - only rendered when visible */}
      {isVisible && children}
    </>
  )
}

// Seeded random for deterministic bolt variation
function seededRandom(seed: number): number {
  const x = Math.sin(seed * 12.9898) * 43758.5453
  return x - Math.floor(x)
}

/**
 * Individual lightning bolt component
 */
function LightningBolt({
  angle,
  radius,
  startTime,
  isPrimary = true,
  thicknessScale = 1.0,
  lengthScale = 1.0,
  controlsRef,
}: LightningBoltProps) {
  const meshRef = useRef<THREE.Mesh>(null)
  const cfg = ELECTRICITY_CONFIG

  // Create LightningStrike geometry with deterministic variation based on angle
  const strike = useMemo(() => {
    const seed = angle * 1000 // Use angle as seed for variation
    const timeScaleRange = cfg.lightningTimeScaleMax - cfg.lightningTimeScaleMin
    const ramificationRange = cfg.lightningRamificationMax - cfg.lightningRamificationMin

    // Apply thickness and length scales
    const effectiveRadius = radius * lengthScale
    const r0 = cfg.lightningRadius0 * thicknessScale
    const r1 = cfg.lightningRadius1 * thicknessScale

    const rayParams: RayParameters = {
      sourceOffset: new THREE.Vector3(0, 0, 0),
      destOffset: new THREE.Vector3(
        Math.cos(angle) * effectiveRadius,
        Math.sin(angle) * effectiveRadius,
        0
      ),
      radius0: r0,
      radius1: r1,
      minRadius: cfg.lightningMinRadius,
      maxIterations: cfg.lightningMaxIterations,
      isEternal: true,
      timeScale: cfg.lightningTimeScaleMin + seededRandom(seed) * timeScaleRange,
      propagationTimeFactor: 0.1,
      vanishingTimeFactor: 0.9,
      subrayPeriod: cfg.lightningSubrayPeriod,
      subrayDutyCycle: cfg.lightningSubrayDutyCycle,
      maxSubrayRecursion: cfg.lightningMaxSubrayRecursion,
      ramification: Math.floor(
        cfg.lightningRamificationMin + seededRandom(seed + 1) * ramificationRange
      ),
      recursionProbability: cfg.lightningRecursionProbability,
      roughness: cfg.lightningRoughness,
      straightness: cfg.lightningStraightness,
    }
    return new LightningStrike(rayParams)
  }, [angle, radius, cfg, lengthScale, thicknessScale])

  // Animation loop - updates geometry and reads live colors from ref
  useFrame((state) => {
    const elapsed = Date.now() - startTime
    const time = state.clock.getElapsedTime()

    // Update lightning geometry
    strike.update(time)

    // Calculate intensity (fade in/out over 8 seconds - Iter 42)
    // Playground mode: stay at full intensity forever
    let intensity: number
    if (PLASMA_PLAYGROUND_MODE) {
      intensity = elapsed < 400 ? 0.3 + (elapsed / 400) ** 2 * 0.7 : 1
    } else if (elapsed < 400) {
      intensity = 0.3 + (elapsed / 400) ** 2 * 0.7
    } else if (elapsed < 7400) {
      intensity = 1
    } else if (elapsed < 8000) {
      intensity = 1 - ((elapsed - 7400) / 600) ** 2
    } else {
      intensity = 0
    }

    // Surge cycle
    const elapsedSec = elapsed / 1000
    const cyclePos = (elapsedSec % cfg.surgeCycleDuration) / cfg.surgeCycleDuration
    let surge: number
    if (cyclePos < cfg.surgeBuildPhase) {
      surge =
        cfg.surgeBaseBrightness +
        (cfg.surgePeakBrightness - cfg.surgeBaseBrightness) * (cyclePos / cfg.surgeBuildPhase) ** 2
    } else if (cyclePos < cfg.surgePeakPhase) {
      surge = cfg.surgePeakBrightness
    } else {
      surge =
        cfg.surgePeakBrightness -
        (cfg.surgePeakBrightness - cfg.surgeBaseBrightness) *
          ((cyclePos - cfg.surgePeakPhase) / (1 - cfg.surgePeakPhase))
    }

    // Update material with LIVE colors from ref
    if (meshRef.current && controlsRef.current) {
      const mat = meshRef.current.material as THREE.MeshBasicMaterial
      const ctrl = controlsRef.current

      // Get color based on primary/secondary
      const colorRgb = isPrimary ? ctrl.primaryColor : ctrl.secondaryColor
      const baseOpacity = isPrimary ? ctrl.primaryOpacity : ctrl.secondaryOpacity

      // Apply glow intensity multiplier
      const glowMult = ctrl.glowIntensity

      // Update color
      mat.color.setRGB(
        colorRgb[0] * glowMult,
        colorRgb[1] * glowMult,
        colorRgb[2] * glowMult
      )

      // Update opacity
      mat.opacity = intensity * surge * baseOpacity
    }
  })

  // Cleanup
  useEffect(() => {
    return () => {
      strike.dispose()
    }
  }, [strike])

  // Initial color (will be updated live by useFrame)
  const initialColor = new THREE.Color(cfg.coreColor[0], cfg.coreColor[1], cfg.coreColor[2])

  return (
    <mesh ref={meshRef} geometry={strike}>
      <meshBasicMaterial
        color={initialColor}
        transparent
        opacity={0.45}
        side={THREE.DoubleSide}
        depthWrite={false}
        blending={THREE.AdditiveBlending}
      />
    </mesh>
  )
}

/**
 * Plasma background glow - supports multiple layers at different depths
 * ALL parameters are controllable via Leva through the controlsRef
 */
interface PlasmaControlsRef {
  // === REGIONAL COLORS (4 zones from center to edge) ===
  coreColor: [number, number, number] // Hot center
  innerColor: [number, number, number] // Inner glow
  midColor: [number, number, number] // Middle transition
  outerColor: [number, number, number] // Edge/ambient
  hotAmber: [number, number, number] // Accent highlight

  // === CHAOS CONTROLS ===
  colorChaos: number // 0-1: How much colors vary via noise
  opacityChaos: number // 0-1: How much opacity varies
  centerChaos: number // 0-1: Chaos specifically at the core
  chaosSpeed: number // How fast chaos animates
  chaosScale: number // Size of chaos noise patterns

  // === HSL MODIFIERS (applied on top of base colors) ===
  hueShift: number // -180 to 180 degrees
  saturationMult: number // 0-2 multiplier
  brightnessMult: number // 0-2 multiplier
  colorTemperature: number // -1 (cool) to 1 (warm)

  // Master controls
  glowMult: number
  opacityMult: number

  // Vortex
  vortexEnabled: boolean
  vortexSpeed: number
  vortexTwist: number
  pullStrength: number
  pullPulse: number

  // Tendrils
  tendrilsEnabled: boolean
  numTendrils: number
  tendrilSharpness: number
  tendrilSpeed: number
  tendrilOpacity: number

  // Clouds
  cloudScale: number
  cloudSpeed: number
  wispScale: number
  wispSpeed: number
  emberScale: number
  emberSpeed: number

  // Core glow
  coreGlowStrength: number
  coreGlowFalloff: number

  // Edge falloff
  edgeFalloffStart: number
  edgeFalloffEnd: number
  falloffCurve: number

  // Animation
  globalSpeed: number
}

interface PlasmaProps {
  startTime: number
  zDepth?: number // z-position for layering
  noiseOffset?: number // Offset for noise variation
  baseOpacity?: number // Base layer opacity (multiplied by ref values)
  innerColorMult?: [number, number, number] // Multipliers for inner color from ref
  controlsRef: React.RefObject<PlasmaControlsRef | null> // Ref to live control values
}

function PlasmaBackground({
  startTime,
  zDepth = -0.5,
  noiseOffset = 0,
  baseOpacity = 0.2,
  innerColorMult = [1, 1, 1],
  controlsRef,
}: PlasmaProps) {
  const materialRef = useRef<THREE.ShaderMaterial>(null)

  // Comprehensive uniforms for ALL controllable parameters
  const uniforms = useMemo(
    () => ({
      // Time & intensity
      u_time: { value: 0 },
      u_intensity: { value: 1.0 },
      u_globalSpeed: { value: 1.0 },

      // Regional colors (4 zones)
      u_coreColor: { value: new THREE.Vector3(1.0, 0.9, 0.5) },
      u_innerColor: { value: new THREE.Vector3(0.5, 0.3, 0.1) },
      u_midColor: { value: new THREE.Vector3(0.3, 0.15, 0.05) },
      u_outerColor: { value: new THREE.Vector3(0.005, 0.002, 0.001) },
      u_hotAmber: { value: new THREE.Vector3(0.9, 0.5, 0.15) },
      u_noiseOffset: { value: noiseOffset },
      u_opacity: { value: baseOpacity },

      // Chaos controls
      u_colorChaos: { value: 0.0 },
      u_opacityChaos: { value: 0.0 },
      u_centerChaos: { value: 0.0 },
      u_chaosSpeed: { value: 0.5 },
      u_chaosScale: { value: 3.0 },

      // HSL modifiers
      u_hueShift: { value: 0.0 },
      u_saturationMult: { value: 1.0 },
      u_brightnessMult: { value: 1.0 },
      u_colorTemperature: { value: 0.0 },

      // Vortex
      u_vortexEnabled: { value: 1.0 },
      u_vortexSpeed: { value: 0.12 },
      u_vortexTwist: { value: 2.5 },
      u_pullStrength: { value: 0.15 },
      u_pullPulse: { value: 0.3 },

      // Tendrils
      u_tendrilsEnabled: { value: 1.0 },
      u_numTendrils: { value: 8.0 },
      u_tendrilSharpness: { value: 4.0 },
      u_tendrilSpeed: { value: 0.2 },
      u_tendrilOpacity: { value: 0.25 },

      // Clouds
      u_cloudScale: { value: 2.0 },
      u_cloudSpeed: { value: 0.05 },
      u_wispScale: { value: 4.0 },
      u_wispSpeed: { value: 0.12 },
      u_emberScale: { value: 12.0 },
      u_emberSpeed: { value: 0.15 },

      // Core glow
      u_coreGlowStrength: { value: 0.4 },
      u_coreGlowFalloff: { value: 2.5 },

      // Edge falloff
      u_edgeFalloffStart: { value: 0.7 },
      u_edgeFalloffEnd: { value: 1.1 },
      u_falloffCurve: { value: 0.6 },
    }),
    [noiseOffset, baseOpacity]
  )

  useFrame((state) => {
    const elapsed = Date.now() - startTime

    // Intensity calculation - 8 second duration (Iter 42)
    // Playground mode: stay at full intensity forever
    let intensity: number
    if (PLASMA_PLAYGROUND_MODE) {
      intensity = elapsed < 400 ? 0.3 + (elapsed / 400) ** 2 * 0.7 : 1
    } else if (elapsed < 400) {
      intensity = 0.3 + (elapsed / 400) ** 2 * 0.7
    } else if (elapsed < 7400) {
      intensity = 1
    } else if (elapsed < 8000) {
      intensity = 1 - ((elapsed - 7400) / 600) ** 2
    } else {
      intensity = 0
    }

    // Update ALL uniforms LIVE from ref - this is the key for Leva reactivity!
    if (materialRef.current && controlsRef.current) {
      const ctrl = controlsRef.current
      const finalOpacity = baseOpacity * ctrl.glowMult * ctrl.opacityMult
      const mat = materialRef.current

      // Time & intensity
      mat.uniforms.u_time.value = state.clock.getElapsedTime()
      mat.uniforms.u_intensity.value = intensity
      mat.uniforms.u_globalSpeed.value = ctrl.globalSpeed
      mat.uniforms.u_opacity.value = finalOpacity

      // Regional colors (4 zones) - apply layer multipliers to inner
      mat.uniforms.u_coreColor.value.set(ctrl.coreColor[0], ctrl.coreColor[1], ctrl.coreColor[2])
      mat.uniforms.u_innerColor.value.set(
        ctrl.innerColor[0] * innerColorMult[0],
        ctrl.innerColor[1] * innerColorMult[1],
        ctrl.innerColor[2] * innerColorMult[2]
      )
      mat.uniforms.u_midColor.value.set(ctrl.midColor[0], ctrl.midColor[1], ctrl.midColor[2])
      mat.uniforms.u_outerColor.value.set(ctrl.outerColor[0], ctrl.outerColor[1], ctrl.outerColor[2])
      mat.uniforms.u_hotAmber.value.set(ctrl.hotAmber[0], ctrl.hotAmber[1], ctrl.hotAmber[2])

      // Chaos controls
      mat.uniforms.u_colorChaos.value = ctrl.colorChaos
      mat.uniforms.u_opacityChaos.value = ctrl.opacityChaos
      mat.uniforms.u_centerChaos.value = ctrl.centerChaos
      mat.uniforms.u_chaosSpeed.value = ctrl.chaosSpeed
      mat.uniforms.u_chaosScale.value = ctrl.chaosScale

      // HSL modifiers
      mat.uniforms.u_hueShift.value = ctrl.hueShift
      mat.uniforms.u_saturationMult.value = ctrl.saturationMult
      mat.uniforms.u_brightnessMult.value = ctrl.brightnessMult
      mat.uniforms.u_colorTemperature.value = ctrl.colorTemperature

      // Vortex
      mat.uniforms.u_vortexEnabled.value = ctrl.vortexEnabled ? 1.0 : 0.0
      mat.uniforms.u_vortexSpeed.value = ctrl.vortexSpeed
      mat.uniforms.u_vortexTwist.value = ctrl.vortexTwist
      mat.uniforms.u_pullStrength.value = ctrl.pullStrength
      mat.uniforms.u_pullPulse.value = ctrl.pullPulse

      // Tendrils
      mat.uniforms.u_tendrilsEnabled.value = ctrl.tendrilsEnabled ? 1.0 : 0.0
      mat.uniforms.u_numTendrils.value = ctrl.numTendrils
      mat.uniforms.u_tendrilSharpness.value = ctrl.tendrilSharpness
      mat.uniforms.u_tendrilSpeed.value = ctrl.tendrilSpeed
      mat.uniforms.u_tendrilOpacity.value = ctrl.tendrilOpacity

      // Clouds
      mat.uniforms.u_cloudScale.value = ctrl.cloudScale
      mat.uniforms.u_cloudSpeed.value = ctrl.cloudSpeed
      mat.uniforms.u_wispScale.value = ctrl.wispScale
      mat.uniforms.u_wispSpeed.value = ctrl.wispSpeed
      mat.uniforms.u_emberScale.value = ctrl.emberScale
      mat.uniforms.u_emberSpeed.value = ctrl.emberSpeed

      // Core glow
      mat.uniforms.u_coreGlowStrength.value = ctrl.coreGlowStrength
      mat.uniforms.u_coreGlowFalloff.value = ctrl.coreGlowFalloff

      // Edge falloff
      mat.uniforms.u_edgeFalloffStart.value = ctrl.edgeFalloffStart
      mat.uniforms.u_edgeFalloffEnd.value = ctrl.edgeFalloffEnd
      mat.uniforms.u_falloffCurve.value = ctrl.falloffCurve
    }
  })

  return (
    <mesh position={[0, 0, zDepth]}>
      <circleGeometry args={[2.5, 64]} />
      <shaderMaterial
        ref={materialRef}
        transparent
        depthWrite={false}
        blending={THREE.AdditiveBlending}
        uniforms={uniforms}
        vertexShader={`
          varying vec2 vUv;
          void main() {
            vUv = uv;
            gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
          }
        `}
        fragmentShader={`
          // Time & intensity
          uniform float u_time;
          uniform float u_intensity;
          uniform float u_globalSpeed;
          uniform float u_opacity;

          // Regional colors (4 zones)
          uniform vec3 u_coreColor;
          uniform vec3 u_innerColor;
          uniform vec3 u_midColor;
          uniform vec3 u_outerColor;
          uniform vec3 u_hotAmber;
          uniform float u_noiseOffset;

          // Chaos controls
          uniform float u_colorChaos;
          uniform float u_opacityChaos;
          uniform float u_centerChaos;
          uniform float u_chaosSpeed;
          uniform float u_chaosScale;

          // HSL modifiers
          uniform float u_hueShift;
          uniform float u_saturationMult;
          uniform float u_brightnessMult;
          uniform float u_colorTemperature;

          // Vortex
          uniform float u_vortexEnabled;
          uniform float u_vortexSpeed;
          uniform float u_vortexTwist;
          uniform float u_pullStrength;
          uniform float u_pullPulse;

          // Tendrils
          uniform float u_tendrilsEnabled;
          uniform float u_numTendrils;
          uniform float u_tendrilSharpness;
          uniform float u_tendrilSpeed;
          uniform float u_tendrilOpacity;

          // Clouds
          uniform float u_cloudScale;
          uniform float u_cloudSpeed;
          uniform float u_wispScale;
          uniform float u_wispSpeed;
          uniform float u_emberScale;
          uniform float u_emberSpeed;

          // Core glow
          uniform float u_coreGlowStrength;
          uniform float u_coreGlowFalloff;

          // Edge falloff
          uniform float u_edgeFalloffStart;
          uniform float u_edgeFalloffEnd;
          uniform float u_falloffCurve;

          varying vec2 vUv;

          // ============ UTILITY FUNCTIONS ============

          float hash(vec2 p) {
            return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453);
          }

          float noise(vec2 p) {
            vec2 i = floor(p);
            vec2 f = fract(p);
            f = f * f * (3.0 - 2.0 * f);
            float a = hash(i);
            float b = hash(i + vec2(1.0, 0.0));
            float c = hash(i + vec2(0.0, 1.0));
            float d = hash(i + vec2(1.0, 1.0));
            return mix(mix(a, b, f.x), mix(c, d, f.x), f.y);
          }

          // Fractal Brownian Motion for organic swirls
          float fbm(vec2 p) {
            float value = 0.0;
            float amplitude = 0.5;
            for (int i = 0; i < 4; i++) {
              value += amplitude * noise(p);
              p *= 2.0;
              amplitude *= 0.5;
            }
            return value;
          }

          // RGB to HSL conversion
          vec3 rgb2hsl(vec3 c) {
            float maxC = max(max(c.r, c.g), c.b);
            float minC = min(min(c.r, c.g), c.b);
            float l = (maxC + minC) / 2.0;
            float h = 0.0;
            float s = 0.0;

            if (maxC != minC) {
              float d = maxC - minC;
              s = l > 0.5 ? d / (2.0 - maxC - minC) : d / (maxC + minC);

              if (maxC == c.r) {
                h = (c.g - c.b) / d + (c.g < c.b ? 6.0 : 0.0);
              } else if (maxC == c.g) {
                h = (c.b - c.r) / d + 2.0;
              } else {
                h = (c.r - c.g) / d + 4.0;
              }
              h /= 6.0;
            }
            return vec3(h, s, l);
          }

          // HSL to RGB conversion
          float hue2rgb(float p, float q, float t) {
            if (t < 0.0) t += 1.0;
            if (t > 1.0) t -= 1.0;
            if (t < 1.0/6.0) return p + (q - p) * 6.0 * t;
            if (t < 1.0/2.0) return q;
            if (t < 2.0/3.0) return p + (q - p) * (2.0/3.0 - t) * 6.0;
            return p;
          }

          vec3 hsl2rgb(vec3 hsl) {
            float h = hsl.x;
            float s = hsl.y;
            float l = hsl.z;

            if (s == 0.0) {
              return vec3(l);
            }

            float q = l < 0.5 ? l * (1.0 + s) : l + s - l * s;
            float p = 2.0 * l - q;

            return vec3(
              hue2rgb(p, q, h + 1.0/3.0),
              hue2rgb(p, q, h),
              hue2rgb(p, q, h - 1.0/3.0)
            );
          }

          // Apply HSL modifiers to a color
          vec3 applyHSLModifiers(vec3 color, float hueShift, float satMult, float brightMult, float temp) {
            vec3 hsl = rgb2hsl(color);

            // Hue shift (in degrees, convert to 0-1)
            hsl.x = fract(hsl.x + hueShift / 360.0);

            // Saturation multiplier
            hsl.y = clamp(hsl.y * satMult, 0.0, 1.0);

            // Brightness multiplier
            hsl.z = clamp(hsl.z * brightMult, 0.0, 1.0);

            vec3 result = hsl2rgb(hsl);

            // Color temperature: negative = cool (blue), positive = warm (orange)
            if (temp > 0.0) {
              result.r += temp * 0.1;
              result.b -= temp * 0.1;
            } else {
              result.r += temp * 0.1;
              result.b -= temp * 0.1;
            }

            return clamp(result, 0.0, 1.0);
          }

          // ============ MAIN SHADER ============

          void main() {
            float t = u_time * u_globalSpeed;
            vec2 centered = vUv - 0.5;
            float dist = length(centered) * 2.0;
            float angle = atan(centered.y, centered.x);

            // CHAOS NOISE - used to vary colors and opacity
            float chaosNoise = fbm(centered * u_chaosScale + t * u_chaosSpeed);
            float chaosNoise2 = noise(centered * u_chaosScale * 1.5 - t * u_chaosSpeed * 0.7);

            // VORTEX: Spiral pull toward center
            float vortexTwist = (1.0 - dist) * u_vortexTwist;
            float spiralAngle = angle + t * u_vortexSpeed * u_vortexEnabled + vortexTwist * u_vortexEnabled;

            float pullStrength = u_pullStrength * sin(t * u_pullPulse + dist * 3.0) * u_vortexEnabled;
            float spiralDist = dist * (1.0 - pullStrength * (1.0 - dist));
            vec2 swirlCentered = vec2(cos(spiralAngle), sin(spiralAngle)) * spiralDist * 0.5;

            // Edge falloff
            float falloff = 1.0 - smoothstep(u_edgeFalloffStart, u_edgeFalloffEnd, dist);
            falloff = pow(falloff, u_falloffCurve);

            // Opacity chaos - varies transparency across the effect
            float opacityVar = 1.0 - u_opacityChaos * (chaosNoise2 * 0.5);

            // Swirling noise patterns
            vec2 offsetCentered = swirlCentered + u_noiseOffset;
            float clouds = fbm(offsetCentered * u_cloudScale + t * u_cloudSpeed);
            float wisps = noise(offsetCentered * u_wispScale + vec2(t * u_wispSpeed, -t * u_wispSpeed * 0.67)) * 0.6;
            float embers = noise(offsetCentered * u_emberScale - t * u_emberSpeed) * 0.3;
            embers *= smoothstep(0.4, 0.6, noise(offsetCentered * (u_emberScale * 0.67) + t * 0.1));

            float n = clouds + wisps + embers;
            float density = smoothstep(0.25, 0.75, n);

            // ============ REGIONAL COLOR BLENDING ============
            // 4 zones: core (0-0.2), inner (0.2-0.5), mid (0.5-0.8), outer (0.8-1.0)

            float radialHeat = 1.0 - smoothstep(0.0, 0.8, dist);

            // Zone weights based on distance
            float coreWeight = 1.0 - smoothstep(0.0, 0.25, dist);
            float innerWeight = smoothstep(0.0, 0.2, dist) * (1.0 - smoothstep(0.3, 0.55, dist));
            float midWeight = smoothstep(0.3, 0.5, dist) * (1.0 - smoothstep(0.6, 0.85, dist));
            float outerWeight = smoothstep(0.6, 0.8, dist);

            // Normalize weights
            float totalWeight = coreWeight + innerWeight + midWeight + outerWeight + 0.001;

            // Blend regional colors
            vec3 baseColor = (
              u_coreColor * coreWeight +
              u_innerColor * innerWeight +
              u_midColor * midWeight +
              u_outerColor * outerWeight
            ) / totalWeight;

            // Apply color chaos - shifts between zones based on noise
            vec3 chaosShiftColor = mix(u_innerColor, u_midColor, chaosNoise);
            baseColor = mix(baseColor, chaosShiftColor, u_colorChaos * chaosNoise2);

            // Apply HSL modifiers
            baseColor = applyHSLModifiers(baseColor, u_hueShift, u_saturationMult, u_brightnessMult, u_colorTemperature);

            // Apply falloff to color
            float colorVar = fbm(offsetCentered * 1.5 + t * 0.02);
            vec3 color = mix(u_outerColor, baseColor, falloff * (0.5 + colorVar * 0.3 + radialHeat * 0.2));

            // Glow boost
            float glowBoost = 1.0 + density * 0.6 * radialHeat;
            color *= glowBoost;

            // CORE GLOW with CENTER CHAOS
            float centerChaosVar = 1.0 + u_centerChaos * (chaosNoise - 0.5) * 2.0;
            float coreGlow = pow(radialHeat, u_coreGlowFalloff) * density * u_coreGlowStrength * centerChaosVar;

            // Apply chaos to core color too
            vec3 coreAccent = mix(u_hotAmber, u_coreColor, u_centerChaos * chaosNoise2);
            coreAccent = applyHSLModifiers(coreAccent, u_hueShift, u_saturationMult, u_brightnessMult, u_colorTemperature);
            color += coreAccent * coreGlow;

            // Alpha with opacity chaos
            float alpha = falloff * 0.45 * u_intensity * (0.4 + density * 0.6) * u_opacity * opacityVar;

            // Ember flicker with color variation
            float sparkle = pow(embers, 3.0) * radialHeat;
            vec3 sparkleColor = mix(u_innerColor, u_coreColor, chaosNoise);
            sparkleColor = applyHSLModifiers(sparkleColor, u_hueShift, u_saturationMult, u_brightnessMult, u_colorTemperature);
            color += sparkleColor * sparkle * 0.4;

            // TENDRILS with chaos color variation
            if (u_tendrilsEnabled > 0.5) {
              float tendrilAngle = angle + t * u_tendrilSpeed;
              float tendril = sin(tendrilAngle * u_numTendrils) * 0.5 + 0.5;
              tendril = pow(tendril, u_tendrilSharpness);

              float tendrilFade = smoothstep(0.1, 0.4, dist) * (1.0 - smoothstep(0.7, 1.0, dist));
              float tendrilNoise = noise(vec2(tendrilAngle * 2.0, t * 0.5 + dist * 3.0));

              float tendrilAlpha = tendril * tendrilFade * tendrilNoise * u_tendrilOpacity;

              // Tendril color varies with chaos
              vec3 tendrilColor = mix(u_innerColor, u_midColor, u_colorChaos * chaosNoise);
              tendrilColor = applyHSLModifiers(tendrilColor, u_hueShift, u_saturationMult, u_brightnessMult, u_colorTemperature);
              color += tendrilColor * tendrilAlpha * 1.3;
            }

            gl_FragColor = vec4(color, alpha);
          }
        `}
      />
    </mesh>
  )
}

/**
 * Outer glow layer - extends BEYOND the portal ring boundary
 * This creates a soft halo that bleeds onto the portal frame
 */
interface OuterGlowControlsRef {
  enabled: boolean
  amount: number
  intensity: number
  color: [number, number, number]
  softness: number
}

interface OuterGlowProps {
  startTime: number
  controlsRef: React.RefObject<OuterGlowControlsRef>
}

function OuterGlowLayer({ startTime, controlsRef }: OuterGlowProps) {
  const materialRef = useRef<THREE.ShaderMaterial>(null)

  const uniforms = useMemo(
    () => ({
      u_time: { value: 0 },
      u_intensity: { value: 1.0 },
      u_glowIntensity: { value: 0.3 },
      u_glowColor: { value: new THREE.Vector3(1.0, 0.4, 0.0) },
      u_softness: { value: 0.5 },
      u_innerRadius: { value: 0.8 }, // Start fade at 80% radius
      u_outerRadius: { value: 1.0 }, // Main glow ends at 100%
      u_overflowRadius: { value: 1.15 }, // Extends to 115%
    }),
    []
  )

  useFrame((state) => {
    const elapsed = Date.now() - startTime

    // Intensity based on effect timing
    let intensity: number
    if (PLASMA_PLAYGROUND_MODE) {
      intensity = elapsed < 400 ? elapsed / 400 : 1
    } else if (elapsed < 400) {
      intensity = elapsed / 400
    } else if (elapsed < 7400) {
      intensity = 1
    } else if (elapsed < 8000) {
      intensity = 1 - (elapsed - 7400) / 600
    } else {
      intensity = 0
    }

    if (materialRef.current && controlsRef.current) {
      const ctrl = controlsRef.current
      const mat = materialRef.current

      mat.uniforms.u_time.value = state.clock.getElapsedTime()
      mat.uniforms.u_intensity.value = intensity
      mat.uniforms.u_glowIntensity.value = ctrl.intensity
      mat.uniforms.u_glowColor.value.set(ctrl.color[0], ctrl.color[1], ctrl.color[2])
      mat.uniforms.u_softness.value = ctrl.softness
      mat.uniforms.u_overflowRadius.value = 1.0 + ctrl.amount
    }
  })

  return (
    <mesh position={[0, 0, -3.0]}>
      {/* Larger geometry to extend past the portal */}
      <circleGeometry args={[3.5, 64]} />
      <shaderMaterial
        ref={materialRef}
        transparent
        depthWrite={false}
        blending={THREE.AdditiveBlending}
        uniforms={uniforms}
        vertexShader={`
          varying vec2 vUv;
          void main() {
            vUv = uv;
            gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
          }
        `}
        fragmentShader={`
          uniform float u_time;
          uniform float u_intensity;
          uniform float u_glowIntensity;
          uniform vec3 u_glowColor;
          uniform float u_softness;
          uniform float u_innerRadius;
          uniform float u_outerRadius;
          uniform float u_overflowRadius;
          varying vec2 vUv;

          float hash(vec2 p) {
            return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453);
          }

          float noise(vec2 p) {
            vec2 i = floor(p);
            vec2 f = fract(p);
            f = f * f * (3.0 - 2.0 * f);
            float a = hash(i);
            float b = hash(i + vec2(1.0, 0.0));
            float c = hash(i + vec2(0.0, 1.0));
            float d = hash(i + vec2(1.0, 1.0));
            return mix(mix(a, b, f.x), mix(c, d, f.x), f.y);
          }

          void main() {
            vec2 centered = vUv - 0.5;
            float dist = length(centered) * 2.0;
            float angle = atan(centered.y, centered.x);

            // Only show glow in the OUTER region (from innerRadius to overflowRadius)
            // The main effect covers 0 to outerRadius, this covers outerRadius to overflow
            float ringFade = smoothstep(u_innerRadius, u_outerRadius, dist);
            float outerFade = 1.0 - smoothstep(u_outerRadius, u_overflowRadius, dist);

            // This creates a ring shape that starts fading at innerRadius,
            // peaks near outerRadius, and fades out at overflowRadius
            float ring = ringFade * outerFade;

            // Add some animated variation
            float flicker = 0.8 + 0.2 * noise(vec2(angle * 3.0, u_time * 2.0));
            float pulse = 0.9 + 0.1 * sin(u_time * 1.5 + angle * 2.0);

            // Softer falloff based on softness control
            ring = pow(ring, 1.0 - u_softness * 0.5);

            vec3 color = u_glowColor;
            float alpha = ring * flicker * pulse * u_glowIntensity * u_intensity;

            // Add some color variation based on angle
            color.r += 0.1 * sin(angle * 3.0 + u_time);
            color.g -= 0.05 * sin(angle * 5.0 - u_time * 0.7);

            gl_FragColor = vec4(color, alpha);
          }
        `}
      />
    </mesh>
  )
}

/**
 * Main electricity scene with all lightning bolts
 */
function ElectricityScene({ startTime }: { startTime: number }) {
  const cfg = ELECTRICITY_CONFIG
  const numBolts = cfg.numMainBolts
  const portalRadius = cfg.r3fPortalRadius

  // =============================================================================
  // DYNAMIC LAYER STATE - Each layer independently configurable
  // =============================================================================
  const { layers, addLayer, removeLayer, updateLayer, resetToDefaults } = useLayerState()
  const { plasmaRefs, boltRefs, rimRefs, outerGlowRefs } = useLayerRefs(layers)

  // =============================================================================
  // DYNAMIC LAYER CONTROLS - Generated from layer state
  // =============================================================================
  const layerControls = useControls(
    'Plasma FX',
    () => generateAllLayerControls(layers, updateLayer, addLayer, removeLayer, resetToDefaults, cfg),
    [layers]
  )

  // =============================================================================
  // REFS are now managed by useLayerRefs above - each layer has its own ref
  // The refs are updated automatically when layer state changes
  // =============================================================================

  // Get the first bolt layer ref for lightning bolts
  // (Bolts share a single color config from the first bolt layer)
  const firstBoltLayer = layers.bolts[0]
  const firstBoltRef = firstBoltLayer ? boltRefs.get(firstBoltLayer.id) : null

  // 10 prominent primary bolts + remaining thin/short secondary bolts
  const NUM_PRIMARY = 10

  const bolts = useMemo(() => {
    return Array.from({ length: numBolts }, (_, i) => {
      const angle = (i / numBolts) * Math.PI * 2
      const seed = i * 137.5

      // Every Nth bolt is primary (evenly spaced)
      const spacing = numBolts / NUM_PRIMARY
      const isPrimary = i % Math.round(spacing) === 0 && Math.floor(i / spacing) < NUM_PRIMARY

      // Secondary bolts: thin, VERY varied lengths, darker
      const thicknessScale = isPrimary ? 1.3 : 0.15 + seededRandom(seed) * 0.25 // 0.15-0.4x (thinner)
      const lengthScale = isPrimary ? 1.0 : 0.2 + seededRandom(seed + 1) * 0.5 // 0.2-0.7x (more varied, some very short)

      return { angle, isPrimary, thicknessScale, lengthScale }
    })
  }, [numBolts])

  return (
    <>
      {/* Camera */}
      <perspectiveCamera position={[0, 0, 5]} />

      {/* RIM GLOW LAYERS - rendered dynamically from layer state */}
      {layers.rim.filter(layer => layer.enabled).map(layer => {
        const layerRef = rimRefs.get(layer.id)
        if (!layerRef) return null
        return (
          <mesh key={layer.id} position={[0, 0, -2.5]}>
            <circleGeometry args={[2.5, 64]} />
            <shaderMaterial
              transparent
              depthWrite={false}
              blending={THREE.AdditiveBlending}
              uniforms={{
                u_time: { value: 0 },
                u_intensity: { value: 1.0 },
                u_rimOpacity: { value: 0.5 },
                u_rimStart: { value: 0.3 },
                u_rimEnd: { value: 0.95 },
                u_aberration: { value: 0.015 },
                u_flicker: { value: 0.4 },
                u_color1: { value: new THREE.Vector3(0.8, 0.4, 0.1) },
                u_color2: { value: new THREE.Vector3(0.5, 0.2, 0.1) },
              }}
              vertexShader={`
                varying vec2 vUv;
                void main() {
                  vUv = uv;
                  gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
                }
              `}
              fragmentShader={`
                uniform float u_time;
                uniform float u_intensity;
                uniform float u_rimOpacity;
                uniform float u_rimStart;
                uniform float u_rimEnd;
                uniform float u_aberration;
                uniform float u_flicker;
                uniform vec3 u_color1;
                uniform vec3 u_color2;
                varying vec2 vUv;

                float hash(vec2 p) {
                  return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453);
                }

                float noise(vec2 p) {
                  vec2 i = floor(p);
                  vec2 f = fract(p);
                  f = f * f * (3.0 - 2.0 * f);
                  float a = hash(i);
                  float b = hash(i + vec2(1.0, 0.0));
                  float c = hash(i + vec2(0.0, 1.0));
                  float d = hash(i + vec2(1.0, 1.0));
                  return mix(mix(a, b, f.x), mix(c, d, f.x), f.y);
                }

                void main() {
                  vec2 centered = vUv - 0.5;
                  float dist = length(centered) * 2.0;
                  float angle = atan(centered.y, centered.x);

                  // RIM: transparent center, glow at edge - controlled by uniforms
                  float rim = smoothstep(u_rimStart, u_rimEnd, dist);
                  rim *= 1.0 - smoothstep(u_rimEnd, u_rimEnd + 0.15, dist);

                  // Flickering rim variation - controlled by u_flicker
                  float flicker = noise(vec2(angle * 3.0, u_time * 2.0)) * u_flicker + (1.0 - u_flicker * 0.5);
                  float pulse = 0.8 + 0.2 * sin(u_time * 1.5 + angle * 2.0);

                  // Blend between the two rim colors
                  float colorShift = noise(vec2(angle * 2.0 + u_time * 0.1, 0.0));
                  vec3 rimColor = mix(u_color1, u_color2, smoothstep(0.3, 0.7, colorShift));

                  // CHROMATIC ABERRATION - controlled by u_aberration
                  float aberrationAmount = u_aberration * (0.7 + 0.3 * sin(u_time * 3.0 + angle * 4.0));
                  vec2 redOffset = centered * (1.0 + aberrationAmount);
                  vec2 blueOffset = centered * (1.0 - aberrationAmount);

                  float redRim = smoothstep(u_rimStart, u_rimEnd, length(redOffset) * 2.0);
                  float blueRim = smoothstep(u_rimStart, u_rimEnd, length(blueOffset) * 2.0);

                  rimColor.r *= 1.0 + (redRim - rim) * 2.0;
                  rimColor.b *= 1.0 + (blueRim - rim) * 1.5;

                  float alpha = rim * flicker * pulse * u_rimOpacity * u_intensity;

                  gl_FragColor = vec4(rimColor, alpha);
                }
              `}
              ref={(mat) => {
                if (mat && layerRef.current) {
                  const updateRim = () => {
                    const elapsed = Date.now() - startTime
                    // Playground mode: stay on forever
                    let intensity: number
                    if (PLASMA_PLAYGROUND_MODE) {
                      intensity = elapsed < 400 ? elapsed / 400 : 1
                    } else {
                      intensity = elapsed < 400 ? elapsed / 400 : elapsed > 7400 ? 1 - (elapsed - 7400) / 600 : 1
                    }
                    mat.uniforms.u_time.value = elapsed / 1000
                    mat.uniforms.u_intensity.value = Math.max(0, intensity)
                    // Update from layer ref!
                    const ctrl = layerRef.current
                    if (ctrl) {
                      mat.uniforms.u_rimOpacity.value = ctrl.opacity
                      mat.uniforms.u_rimStart.value = ctrl.start
                      mat.uniforms.u_rimEnd.value = ctrl.end
                      mat.uniforms.u_aberration.value = ctrl.aberration
                      mat.uniforms.u_flicker.value = ctrl.flicker
                      mat.uniforms.u_color1.value.set(ctrl.color1[0], ctrl.color1[1], ctrl.color1[2])
                      mat.uniforms.u_color2.value.set(ctrl.color2[0], ctrl.color2[1], ctrl.color2[2])
                    }
                    requestAnimationFrame(updateRim)
                  }
                  updateRim()
                }
              }}
            />
          </mesh>
        )
      })}

      {/* PLASMA LAYERS - dynamically rendered from layer state */}
      {layers.plasma.filter(layer => layer.enabled).map(layer => {
        const layerRef = plasmaRefs.get(layer.id)
        if (!layerRef) return null
        return (
          <PlasmaBackground
            key={layer.id}
            startTime={startTime}
            zDepth={layer.zDepth}
            noiseOffset={layer.noiseOffset}
            baseOpacity={layer.baseOpacity}
            innerColorMult={layer.colorMult}
            controlsRef={layerRef}
          />
        )
      })}

      {/* OUTER GLOW LAYERS - dynamically rendered from layer state */}
      {layers.outerGlow.filter(layer => layer.enabled).map(layer => {
        const layerRef = outerGlowRefs.get(layer.id)
        if (!layerRef) return null
        return (
          <OuterGlowLayer
            key={layer.id}
            startTime={startTime}
            controlsRef={layerRef}
          />
        )
      })}

      {/* Lightning bolts - use first bolt layer's colors for all bolts */}
      {firstBoltRef && bolts.map((bolt, i) => (
        <LightningBolt
          key={i}
          angle={bolt.angle}
          radius={portalRadius}
          startTime={startTime}
          isPrimary={bolt.isPrimary}
          thicknessScale={bolt.thicknessScale}
          lengthScale={bolt.lengthScale}
          controlsRef={firstBoltRef}
        />
      ))}

      {/* Post-processing - using config values (bloom controls are in Leva panel) */}
      <EffectComposer>
        <Bloom
          intensity={(layerControls as unknown as Record<string, number>).bloomIntensity ?? cfg.r3fBloomIntensity}
          luminanceThreshold={(layerControls as unknown as Record<string, number>).bloomThreshold ?? cfg.r3fBloomLuminanceThreshold}
          luminanceSmoothing={cfg.r3fBloomLuminanceSmoothing}
          radius={(layerControls as unknown as Record<string, number>).bloomRadius ?? cfg.r3fBloomRadius}
        />
      </EffectComposer>
    </>
  )
}

/**
 * Wrapper that tracks visibility changes
 */
function ElectricityWrapper({ startTime }: { startTime: number }) {
  return (
    <Canvas
      gl={{ alpha: true, antialias: true, preserveDrawingBuffer: true }}
      camera={{ position: [0, 0, 5], fov: 45 }}
      style={{ background: 'transparent' }}
    >
      <ElectricityScene startTime={startTime} />
    </Canvas>
  )
}

/**
 * Electricity effect component using React Three Fiber
 *
 * Uses a stable key/startTime pair that only updates when transitioning to visible.
 * The Canvas persists for the full effect duration without flickering.
 */
export function ElectricityR3F({ visible }: ElectricityR3FProps) {
  // State for canvas instance (key + startTime captured together)
  const [instance, setInstance] = useState<{ key: number; startTime: number } | null>(null)
  const wasVisibleRef = useRef(false)

  // Handle visibility transitions with deferred state update
  useEffect(() => {
    if (visible && !wasVisibleRef.current) {
      // Becoming visible - capture startTime NOW, defer state update
      const now = Date.now()
      const timer = setTimeout(() => {
        setInstance({ key: now, startTime: now })
      }, 0)
      wasVisibleRef.current = visible
      return () => clearTimeout(timer)
    } else if (!visible && wasVisibleRef.current) {
      // Becoming hidden - clear instance (UNLESS playground mode)
      if (!PLASMA_PLAYGROUND_MODE) {
        const timer = setTimeout(() => {
          setInstance(null)
        }, 0)
        wasVisibleRef.current = visible
        return () => clearTimeout(timer)
      }
      // In playground mode, keep the instance alive!
    }
    wasVisibleRef.current = visible
    return undefined
  }, [visible])

  // Don't render until we have an instance
  // Playground mode: once triggered, stay visible forever
  if (PLASMA_PLAYGROUND_MODE && instance) {
    // Stay on - ignore visible prop once we have an instance
  } else if (!visible || !instance) {
    return null
  }

  return (
    <>
      {/* Leva control panel - positioned on LEFT side to not cover the centered effect */}
      {SHOW_PLASMA_CONTROLS && (
        <>
          {/* CSS to reposition Leva to the left side */}
          <style>{`
            .leva-c-kWgxhW {
              /* Move to left side instead of right */
              left: 10px !important;
              right: auto !important;
              /* Limit width to not cover effect */
              max-width: 320px !important;
              /* Limit height and make scrollable */
              max-height: calc(100vh - 80px) !important;
              overflow-y: auto !important;
            }
          `}</style>
          <Leva
            collapsed={false}
            fill={true}
            flat={true}
            oneLineLabels={true}
            titleBar={{
              drag: true,
              title: '⚡ Plasma FX',
              filter: true,
            }}
            theme={{
              colors: {
                accent1: '#ff6a00',
                accent2: '#ff9500',
                accent3: '#ffb800',
              },
              sizes: {
                rootWidth: '320px',
                controlWidth: '140px',
                scrubberWidth: '8px',
                scrubberHeight: '16px',
                rowHeight: '24px',
                folderTitleHeight: '28px',
              },
              fontSizes: {
                root: '10px',
              },
              space: {
                sm: '4px',
                md: '8px',
                rowGap: '4px',
                colGap: '4px',
              },
            }}
          />
        </>
      )}
      {/* Container for the electricity effect - allows overflow for outer glow */}
      <div
        style={{
          position: 'absolute',
          left: '50%',
          top: '50%',
          transform: 'translate(-50%, -50%)',
          // Slightly larger container to accommodate outer glow overflow
          width: 'calc(min(100%, 100vh - 40px) * 0.88)',
          height: 'calc(min(100%, 100vh - 40px) * 0.88)',
          // NO overflow:hidden - allows glow to extend past circular bounds
          // The shader handles edge falloff for the main effect
          zIndex: 27,
          pointerEvents: 'none',
        }}
      >
        <ElectricityWrapper key={instance.key} startTime={instance.startTime} />
      </div>
    </>
  )
}
