/**
 * ElectricityOrtho Component
 *
 * CRITICAL PATH: Orthographic R3F Electricity Animation
 *
 * Orthographic R3F implementation of electricity animation.
 * Preserves Canvas 2D animation characteristics with GPU-accelerated rendering.
 *
 * Week 2 Implementation Status:
 * - [x] Orthographic camera setup (1:1 pixel mapping)
 * - [x] Multi-bolt generation (8-10 bolts)
 * - [x] Branching system (1-3 branches per bolt)
 * - [ ] Animation phases (BUILD/PEAK/DECAY) - Week 3
 * - [ ] Multi-layer glow - Week 4
 * - [ ] Plasma background - Week 4
 * - [ ] Bloom post-processing - Week 4
 */

import { useRef, useEffect } from 'react'
import { Canvas } from '@react-three/fiber'
import { OrthoScene } from './scene/OrthoScene'

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
  intensity?: number      // 0-1 for animation phases
  useBoltGroup?: boolean  // Multi-bolt (true) or single bolt (false)

  // Debug options
  showTestCube?: boolean  // Show test cube for camera validation
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
  intensity = 1.0,
  useBoltGroup = true,
  showTestCube = false,
}: ElectricityOrthoProps) {
  const effectiveVisible = isActive !== undefined ? isActive : visible

  // Debug logging - ALWAYS log to trace rendering
  console.log('[ElectricityOrtho] Render called:', {
    visible,
    isActive,
    effectiveVisible,
    showTestCube,
    boltCount,
    intensity,
    useBoltGroup,
  })

  // Early return if not visible
  if (!effectiveVisible) {
    console.log('[ElectricityOrtho] Not visible, returning null')
    return null
  }

  console.log('[ElectricityOrtho] Rendering Canvas...')

  // Debug: Log container dimensions after render
  const containerRef = useRef<HTMLDivElement>(null)
  useEffect(() => {
    if (containerRef.current) {
      const rect = containerRef.current.getBoundingClientRect()
      console.log('[ElectricityOrtho] Container mounted:', {
        width: rect.width,
        height: rect.height,
        top: rect.top,
        left: rect.left,
        visible: rect.width > 0 && rect.height > 0,
      })
    }
  }, [])

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
          zoom: 1, // Will be reconfigured in OrthoScene for 1:1 pixel mapping
        }}
        style={{
          width: '100%',
          height: '100%',
          background: 'transparent',
        }}
        gl={{
          alpha: true,
          antialias: true,
          preserveDrawingBuffer: true, // Needed for frame capture
        }}
        onCreated={(state) => {
          console.log('[ElectricityOrtho] Canvas created:', {
            cameraType: state.camera.type,
            cameraPosition: state.camera.position.toArray(),
            size: state.size,
            gl: state.gl.domElement.tagName,
          })
        }}
        onError={(error) => {
          console.error('[ElectricityOrtho] Canvas error:', error)
        }}
      >
        <OrthoScene
          showTestCube={showTestCube}
          showBolt={showBolt}
          useBoltGroup={useBoltGroup}
          boltCount={boltCount}
          frameNumber={frameNumber}
          intensity={intensity}
        >
          {/* Week 4: Plasma layers, bloom post-processing */}
        </OrthoScene>
      </Canvas>
    </div>
  )
}

export default ElectricityOrtho
