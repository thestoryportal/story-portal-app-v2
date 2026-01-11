/**
 * OrthoScene Component
 *
 * Three.js scene with orthographic camera for 2D electricity rendering.
 * Uses 1:1 pixel mapping to 465x465 container (matches capture pipeline).
 *
 * CRITICAL PATH: Ortho R3F Migration - Week 2 Implementation
 * - Multi-bolt rendering: IMPLEMENTED (via BoltGroup)
 * - Branching support: IMPLEMENTED
 * - Orthographic camera: IMPLEMENTED (1:1 pixel mapping)
 */

import { useThree, useFrame } from '@react-three/fiber'
import { useEffect, useRef } from 'react'
import * as THREE from 'three'
import { Bolt, BoltGroup } from '../bolts/Bolt'

// Fixed reference dimensions (matches ElectricityAnimation canvas size)
export const CONTAINER_SIZE = 465

// Canonical color palette from spec
export const COLORS = {
  corePeak: '#FEFDE6',    // Near white (254, 253, 230)
  coreAvg: '#FBE9A2',     // Pale golden (251, 233, 162)
  glowInner: '#DAA041',   // Bright amber (218, 160, 65)
  glowOuter: '#894F18',   // Deep amber/brown (137, 79, 24)
  // Simplified for Week 2 - bright yellow for visibility
  boltCore: '#F0F050',
}

export interface OrthoSceneProps {
  children?: React.ReactNode
  showTestCube?: boolean    // For camera validation
  showBolt?: boolean        // Show bolts (single or group)
  useBoltGroup?: boolean    // Use multi-bolt group (true) or single bolt (false)
  boltCount?: number        // Number of bolts in group (8-10 recommended)
  frameNumber?: number      // For animation (0-42)
  intensity?: number        // 0-1 for animation phases
  color?: string            // Bolt color override
}

export function OrthoScene({
  children,
  showTestCube = false,
  showBolt = true,
  useBoltGroup = true,      // Default to multi-bolt group
  boltCount = 10,           // 10 bolts for production
  frameNumber = 0,
  intensity = 1.0,
  color = COLORS.boltCore,
}: OrthoSceneProps) {
  const { camera, size } = useThree()

  // Configure orthographic camera - called on mount and on resize
  // Must set fixed frustum bounds each time to override R3F's automatic sizing
  useEffect(() => {
    if (camera instanceof THREE.OrthographicCamera) {
      // Set up 1:1 pixel mapping to 465x465 reference dimensions
      // This ensures no depth distortion and predictable sizing
      const halfSize = CONTAINER_SIZE / 2

      camera.left = -halfSize      // -232.5
      camera.right = halfSize       // 232.5
      camera.top = halfSize         // 232.5
      camera.bottom = -halfSize     // -232.5
      camera.near = 0.1
      camera.far = 1000

      // Position camera looking down Z axis
      camera.position.set(0, 0, 10)
      camera.lookAt(0, 0, 0)
      camera.updateProjectionMatrix()

      console.log('[OrthoScene] Orthographic camera configured:', {
        left: camera.left,
        right: camera.right,
        top: camera.top,
        bottom: camera.bottom,
        frustumSize: CONTAINER_SIZE,
        canvasSize: { width: size.width, height: size.height },
      })
    } else {
      console.warn('[OrthoScene] Camera is not OrthographicCamera:', camera.type)
    }
  }, [camera, size]) // Run on camera change AND size change to maintain our frustum

  // Debug: Log camera state every second to verify frustum persists
  const frameCountRef = useRef(0)
  useFrame(() => {
    frameCountRef.current++
    if (frameCountRef.current % 60 === 0 && camera instanceof THREE.OrthographicCamera) {
      console.log('[OrthoScene] Frame check - camera frustum:', {
        left: camera.left.toFixed(1),
        right: camera.right.toFixed(1),
        frame: frameCountRef.current,
      })
    }
  })

  return (
    <>
      {/* Test cube for camera validation */}
      {showTestCube && (
        <mesh position={[0, 0, 0]}>
          <boxGeometry args={[50, 50, 50]} />
          <meshBasicMaterial color="#ff6600" wireframe />
        </mesh>
      )}

      {/* Bolt rendering */}
      {showBolt && useBoltGroup && (
        <BoltGroup
          boltCount={boltCount}
          frameNumber={frameNumber}
          intensity={intensity}
          color={color}
        />
      )}

      {/* Single bolt for testing/debugging */}
      {showBolt && !useBoltGroup && (
        <Bolt
          angle={Math.PI / 4} // 45 degrees
          length={150}        // Medium length
          thickness={2.5}     // 2.5px thickness
          frameNumber={frameNumber}
          intensity={intensity}
          color={color}
        />
      )}

      {/* Child components (plasma, rim glow, etc. - Week 4) */}
      {children}
    </>
  )
}
