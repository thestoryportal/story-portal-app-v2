/**
 * Bolt.tsx
 *
 * React components for rendering lightning bolts with branches.
 * Combines BoltGenerator, BoltGeometry, and BoltMaterial.
 *
 * CRITICAL PATH: Ortho R3F Migration
 * - Single bolt with branches: IMPLEMENTED
 * - Multi-bolt group: IMPLEMENTED
 * - Intensity-based opacity: IMPLEMENTED (via intensityRef for animation)
 */

import { useMemo, MutableRefObject } from 'react'
import {
  generateBolt,
  generateBolts,
  DEFAULT_BOLT_CONFIG,
  countTotalBranches,
} from './BoltGenerator'
import type { BoltPath, BoltConfig } from './BoltGenerator'
import { createBoltGeometry } from './BoltGeometry'
import { BoltMaterial } from './BoltMaterial'

export interface BoltProps {
  angle: number // Radians (0-2π)
  length: number // Pixels
  thickness: number // Pixels
  frameNumber?: number // For deterministic generation
  intensity?: number // 0-1 for static animation
  intensityRef?: MutableRefObject<number> // For animated intensity (updates every frame)
  color?: string
  config?: BoltConfig
}

/**
 * Renders a single bolt path (including its branches recursively)
 */
function BoltPathMesh({
  path,
  intensity,
  intensityRef,
  color,
  depth = 0,
  branchDimFactor = 0.70, // Branches render at 70% of parent intensity
}: {
  path: BoltPath
  intensity: number
  intensityRef?: MutableRefObject<number>
  color: string
  depth?: number
  branchDimFactor?: number
}) {
  const geometry = useMemo(() => {
    return createBoltGeometry(path, 8)
  }, [path])

  // For branches, we need to scale the intensity
  // If using intensityRef, we create a derived ref that applies the branch dimming
  // For simplicity in this implementation, branches use the same ref
  // The dimming is applied via opacity prop instead
  const branchOpacity = Math.pow(branchDimFactor, depth)

  return (
    <>
      <mesh geometry={geometry} position={[0, 0, 0]}>
        <BoltMaterial
          intensity={intensity}
          intensityRef={intensityRef}
          color={color}
          opacity={branchOpacity}
        />
      </mesh>
      {/* Recursively render branches */}
      {path.branches.map((branch, index) => (
        <BoltPathMesh
          key={`branch-${depth}-${index}`}
          path={branch}
          intensity={intensity}
          intensityRef={intensityRef}
          color={color}
          depth={depth + 1}
          branchDimFactor={branchDimFactor}
        />
      ))}
    </>
  )
}

/**
 * Bolt Component
 * Renders a single lightning bolt with branches using TubeGeometry
 */
export function Bolt({
  angle,
  length,
  thickness,
  frameNumber = 0,
  intensity = 1.0,
  intensityRef,
  color = '#F0F050',
  config = DEFAULT_BOLT_CONFIG,
}: BoltProps) {
  // Generate bolt path with branches (memoized for performance)
  const boltPath = useMemo(() => {
    return generateBolt(angle, length, thickness, frameNumber, config)
  }, [angle, length, thickness, frameNumber, config])

  // Debug: Log bolt info on mount (only once)
  useMemo(() => {
    const branchCount = countTotalBranches(boltPath)
    console.log('[Bolt] Generated:', {
      angle: (angle * 180) / Math.PI,
      length,
      thickness,
      segments: boltPath.segments.length,
      branches: branchCount,
    })
  }, [angle, length, thickness, boltPath])

  return (
    <BoltPathMesh
      path={boltPath}
      intensity={intensity}
      intensityRef={intensityRef}
      color={color}
    />
  )
}

export interface BoltGroupProps {
  boltCount?: number // Number of bolts (8-10 for production)
  frameNumber?: number // For animation (0-42)
  intensity?: number // 0-1 for static animation phases
  intensityRef?: MutableRefObject<number> // For animated intensity
  color?: string
  config?: BoltConfig
}

/**
 * BoltGroup Component
 * Renders multiple lightning bolts in radial pattern with branches
 * CRITICAL PATH: Main component for Ortho electricity animation
 */
export function BoltGroup({
  boltCount = 10,
  frameNumber = 0,
  intensity = 1.0,
  intensityRef,
  color = '#F0F050',
  config = DEFAULT_BOLT_CONFIG,
}: BoltGroupProps) {
  // Generate all bolts with branches
  const bolts = useMemo(() => {
    return generateBolts(boltCount, frameNumber, config)
  }, [boltCount, frameNumber, config])

  // Debug: Log group info (only once)
  useMemo(() => {
    const totalBranches = bolts.reduce((sum, bolt) => sum + countTotalBranches(bolt), 0)
    console.log('[BoltGroup] Generated:', {
      boltCount: bolts.length,
      totalBranches,
      frameNumber,
    })
  }, [bolts, frameNumber])

  return (
    <group>
      {bolts.map((bolt, index) => (
        <BoltPathMesh
          key={`bolt-${index}`}
          path={bolt}
          intensity={intensity}
          intensityRef={intensityRef}
          color={color}
        />
      ))}
    </group>
  )
}

export default Bolt
