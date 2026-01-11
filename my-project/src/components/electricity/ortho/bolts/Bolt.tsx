/**
 * Bolt.tsx
 *
 * React components for rendering lightning bolts with branches.
 * Combines BoltGenerator, BoltGeometry, and BoltMaterial.
 *
 * CRITICAL PATH: Ortho R3F Migration - Week 2 Implementation
 * - Single bolt with branches: IMPLEMENTED
 * - Multi-bolt group: IMPLEMENTED
 * - Intensity-based opacity: IMPLEMENTED
 */

import { useMemo } from 'react'
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
  intensity?: number // 0-1 for animation
  color?: string
  config?: BoltConfig
}

/**
 * Renders a single bolt path (including its branches recursively)
 */
function BoltPathMesh({
  path,
  intensity,
  color,
  depth = 0,
}: {
  path: BoltPath
  intensity: number
  color: string
  depth?: number
}) {
  const geometry = useMemo(() => {
    return createBoltGeometry(path, 8)
  }, [path])

  // Branches render dimmer (70% of parent intensity per Canvas 2D)
  const branchIntensity = intensity * 0.70

  return (
    <>
      <mesh geometry={geometry} position={[0, 0, 0]}>
        <BoltMaterial intensity={intensity} color={color} opacity={1.0} />
      </mesh>
      {/* Recursively render branches */}
      {path.branches.map((branch, index) => (
        <BoltPathMesh
          key={`branch-${depth}-${index}`}
          path={branch}
          intensity={branchIntensity}
          color={color}
          depth={depth + 1}
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
  color = '#F0F050',
  config = DEFAULT_BOLT_CONFIG,
}: BoltProps) {
  // Generate bolt path with branches (memoized for performance)
  const boltPath = useMemo(() => {
    return generateBolt(angle, length, thickness, frameNumber, config)
  }, [angle, length, thickness, frameNumber, config])

  // Debug: Log bolt info on mount
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

  return <BoltPathMesh path={boltPath} intensity={intensity} color={color} />
}

export interface BoltGroupProps {
  boltCount?: number // Number of bolts (8-10 for production)
  frameNumber?: number // For animation (0-42)
  intensity?: number // 0-1 for animation phases
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
  color = '#F0F050',
  config = DEFAULT_BOLT_CONFIG,
}: BoltGroupProps) {
  // Generate all bolts with branches
  const bolts = useMemo(() => {
    return generateBolts(boltCount, frameNumber, config)
  }, [boltCount, frameNumber, config])

  // Debug: Log group info
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
          color={color}
        />
      ))}
    </group>
  )
}

export default Bolt
