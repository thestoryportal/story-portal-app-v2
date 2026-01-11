/**
 * ElectricityOrtho Component
 *
 * CRITICAL PATH: Orthographic R3F Electricity Animation
 *
 * Orthographic R3F implementation of electricity animation.
 * Preserves Canvas 2D animation characteristics with GPU-accelerated rendering.
 *
 * Implementation Status:
 * - [x] Orthographic camera setup (1:1 pixel mapping)
 * - [x] Multi-bolt generation (8-10 bolts)
 * - [x] Branching system (1-3 branches per bolt)
 * - [x] Animation phases (BUILD/PEAK/DECAY)
 * - [ ] Multi-layer glow - Future
 * - [ ] Plasma background - Future
 * - [ ] Bloom post-processing - Future
 */

import { useRef, useEffect } from 'react'
import { Canvas } from '@react-three/fiber'
import { OrthoScene } from './scene/OrthoScene'
import { useAnimationPhase } from './animation/useAnimationPhase'
import type { AnimationPhase } from './animation/types'

export interface ElectricityOrthoProps {
  visible?: boolean
  isActive?: boolean // Alias for visible
  lockAtPeak?: boolean // Freeze at peak intensity (for captures)
  elementVisibility?: {
    bolts?: boolean
    plasma?: boolean
    rimGlow?: boolean
  }
  onPhaseChange?: (phase: string) => void
  onComplete?: () => void
  fillContainer?: boolean // Fill parent vs viewport-based sizing

  // Bolt configuration
  boltCount?: number      // Number of bolts (8-10 recommended)
  frameNumber?: number    // For animation (0-42)
  useBoltGroup?: boolean  // Multi-bolt (true) or single bolt (false)

  // Debug options
  showTestCube?: boolean  // Show test cube for camera validation
}

/**
 * Internal animated scene component
 * Must be inside Canvas to use useFrame for animation
 */
interface AnimatedSceneProps {
  isActive: boolean
  lockAtPeak: boolean
  showTestCube: boolean
  showBolt: boolean
  useBoltGroup: boolean
  boltCount: number
  frameNumber: number
  onPhaseChange?: (phase: string) => void
  onComplete?: () => void
}

function AnimatedScene({
  isActive,
  lockAtPeak,
  showTestCube,
  showBolt,
  useBoltGroup,
  boltCount,
  frameNumber,
  onPhaseChange,
  onComplete,
}: AnimatedSceneProps) {
  // Animation phase hook - manages BUILD/PEAK/DECAY timing
  // Returns intensityRef for direct Three.js material updates (no re-renders)
  const { intensityRef } = useAnimationPhase({
    isActive,
    lockAtPeak,
    onPhaseChange: (p: AnimationPhase) => {
      onPhaseChange?.(p)
    },
    onComplete,
  })

  return (
    <OrthoScene
      showTestCube={showTestCube}
      showBolt={showBolt}
      useBoltGroup={useBoltGroup}
      boltCount={boltCount}
      frameNumber={frameNumber}
      intensityRef={intensityRef}
    />
  )
}

export function ElectricityOrtho({
  visible = true,
  isActive,
  lockAtPeak = false,
  elementVisibility,
  onPhaseChange,
  onComplete,
  fillContainer = true,
  boltCount = 10,
  frameNumber = 0,
  useBoltGroup = true,
  showTestCube = false,
}: ElectricityOrthoProps) {
  const effectiveVisible = isActive !== undefined ? isActive : visible

  // Debug logging
  console.log('[ElectricityOrtho] Render called:', {
    visible,
    isActive,
    effectiveVisible,
    lockAtPeak,
    boltCount,
  })

  // Use ref outside conditional to maintain hook order
  const containerRef = useRef<HTMLDivElement>(null)

  // Debug: Log container dimensions after render
  useEffect(() => {
    if (containerRef.current && effectiveVisible) {
      const rect = containerRef.current.getBoundingClientRect()
      console.log('[ElectricityOrtho] Container mounted:', {
        width: rect.width,
        height: rect.height,
        visible: rect.width > 0 && rect.height > 0,
      })
    }
  }, [effectiveVisible])

  // Early return if not visible - BUT this causes remount issues
  // For animation stability, we always render but control visibility via CSS
  // However, we also need the Canvas to be present for useFrame to work
  if (!effectiveVisible) {
    console.log('[ElectricityOrtho] Not visible, returning null')
    return null
  }

  // Show bolts unless test cube is enabled or explicitly hidden
  const showBolt = !showTestCube && (elementVisibility?.bolts !== false)

  return (
    <div
      ref={containerRef}
      style={{
        position: 'absolute',
        top: 0,
        left: 0,
        width: fillContainer ? '100%' : '465px',
        height: fillContainer ? '100%' : '465px',
        pointerEvents: 'none',
        zIndex: 27,
      }}
    >
      <Canvas
        orthographic
        camera={{
          position: [0, 0, 10],
          near: 0.1,
          far: 1000,
          zoom: 1,
        }}
        style={{
          width: '100%',
          height: '100%',
          background: 'transparent',
        }}
        gl={{
          alpha: true,
          antialias: true,
          preserveDrawingBuffer: true,
        }}
        onCreated={(state) => {
          console.log('[ElectricityOrtho] Canvas created:', {
            cameraType: state.camera.type,
            size: state.size,
          })
        }}
      >
        <AnimatedScene
          isActive={effectiveVisible}
          lockAtPeak={lockAtPeak}
          showTestCube={showTestCube}
          showBolt={showBolt}
          useBoltGroup={useBoltGroup}
          boltCount={boltCount}
          frameNumber={frameNumber}
          onPhaseChange={onPhaseChange}
          onComplete={onComplete}
        />
      </Canvas>
    </div>
  )
}

export default ElectricityOrtho
