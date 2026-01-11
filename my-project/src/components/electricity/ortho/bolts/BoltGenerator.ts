/**
 * BoltGenerator.ts
 *
 * Segment-based lightning bolt generation algorithm.
 * Ported from ElectricityAnimation.tsx (Canvas 2D implementation).
 *
 * CRITICAL PATH: Ortho R3F Migration - Week 2 Implementation
 * - Branching system: IMPLEMENTED
 * - Multi-bolt distribution: IMPLEMENTED
 * - Radial pattern generation: IMPLEMENTED
 */

import * as THREE from 'three'
import { setSeed, randomRange, randomInt, seededRandom } from '../utils/seededRandom'

// Segment represents a single line segment in the bolt path
export interface BoltSegment {
  start: THREE.Vector3
  end: THREE.Vector3
  thickness: number
}

// BoltPath contains segments and branches (recursive structure)
export interface BoltPath {
  segments: BoltSegment[]
  branches: BoltPath[]
  thickness: number // Store for branch rendering
}

// Configuration for bolt generation (matches Canvas 2D BOLT_CONFIG)
export interface BoltConfig {
  // Segment generation
  segmentLengthMin: number  // 12-20px per segment
  segmentLengthMax: number
  angleDeviation: number    // ±15° per segment for curved paths

  // Core thickness
  coreThicknessMin: number  // 2-3px core thickness
  coreThicknessMax: number

  // Branching configuration (from Canvas 2D)
  branchesPerBoltMin: number    // 1-3 branches per bolt
  branchesPerBoltMax: number
  branchAngleMin: number        // 25-45° branch angles
  branchAngleMax: number
  branchLengthRatio: number     // 0.60 = 60% of parent length
  branchThicknessRatio: number  // 0.80 = 80% of parent thickness
  branchProbability: number     // 0.75 = 75% chance of branching
  maxBranchDepth: number        // 1 = only primary bolts can branch
}

// Default configuration matching Canvas 2D implementation
export const DEFAULT_BOLT_CONFIG: BoltConfig = {
  // Segment generation
  segmentLengthMin: 12,
  segmentLengthMax: 20,
  angleDeviation: 15, // degrees

  // Core thickness
  coreThicknessMin: 2,
  coreThicknessMax: 3,

  // Branching (from Canvas 2D BOLT_CONFIG)
  branchesPerBoltMin: 1,
  branchesPerBoltMax: 3,
  branchAngleMin: 25,           // degrees
  branchAngleMax: 45,           // degrees
  branchLengthRatio: 0.60,      // 60% of parent length
  branchThicknessRatio: 0.80,   // 80% of parent thickness
  branchProbability: 0.75,      // 75% chance for primary bolts
  maxBranchDepth: 1,            // Only primary bolts can branch
}

/**
 * Generate a single lightning bolt path using segment-based algorithm
 * WITH BRANCHING SUPPORT (ported from Canvas 2D)
 *
 * @param startPoint - Starting point (origin for primary bolts, branch point for branches)
 * @param angle - Starting angle in radians (0-2π for radial distribution)
 * @param length - Total bolt length in pixels (50-220px for variation)
 * @param thickness - Core bolt thickness in pixels (2-3px)
 * @param depth - Recursion depth (0 = primary bolt, 1+ = branch)
 * @param config - Bolt generation configuration
 * @returns BoltPath with segments and branches
 */
export function generateBoltPath(
  startPoint: THREE.Vector2,
  angle: number,
  length: number,
  thickness: number,
  depth: number = 0,
  config: BoltConfig = DEFAULT_BOLT_CONFIG
): BoltPath {
  // Generate 2D points for bolt path
  const points: THREE.Vector2[] = [startPoint.clone()]
  let currentAngle = angle
  let remainingLength = length

  // Track angles at each point for branch calculation
  const anglesAtPoints: number[] = [angle]

  // Generate segments with angle accumulation (key for curved paths)
  while (remainingLength > 0) {
    const segmentLen = Math.min(
      remainingLength,
      randomRange(config.segmentLengthMin, config.segmentLengthMax)
    )

    // Add angle deviation for organic curved appearance
    const deviation = randomRange(-config.angleDeviation, config.angleDeviation) * (Math.PI / 180)
    currentAngle += deviation // ACCUMULATE angle (creates curves)

    const lastPoint = points[points.length - 1]
    points.push(
      new THREE.Vector2(
        lastPoint.x + Math.cos(currentAngle) * segmentLen,
        lastPoint.y + Math.sin(currentAngle) * segmentLen
      )
    )
    anglesAtPoints.push(currentAngle)

    remainingLength -= segmentLen
  }

  // Generate branches (only for primary bolts, depth < maxBranchDepth)
  const branches: BoltPath[] = []
  if (depth < config.maxBranchDepth && points.length > 2) {
    // Branch probability: 75% for primary bolts, 0% for branches
    const branchProbability = depth === 0 ? config.branchProbability : 0
    const shouldBranch = seededRandom() < branchProbability

    if (shouldBranch) {
      const branchCount = randomInt(config.branchesPerBoltMin, config.branchesPerBoltMax)

      for (let i = 0; i < branchCount; i++) {
        // Branch from 30% to 75% along bolt for natural appearance
        const minIndex = Math.floor(points.length * 0.3)
        const maxIndex = Math.floor(points.length * 0.75)
        const branchPointIndex = randomInt(minIndex, maxIndex)
        const branchPoint = points[branchPointIndex]

        // Get angle at branch point (not final currentAngle - this was a bug in Canvas 2D)
        const angleAtBranchPoint = anglesAtPoints[branchPointIndex]

        // Random direction (left or right)
        const branchDirection = seededRandom() > 0.5 ? 1 : -1
        const branchAngle = angleAtBranchPoint + branchDirection * randomRange(
          config.branchAngleMin,
          config.branchAngleMax
        ) * (Math.PI / 180)

        // Branch dimensions
        const branchLength = length * config.branchLengthRatio
        const branchThickness = thickness * config.branchThicknessRatio

        branches.push(
          generateBoltPath(branchPoint, branchAngle, branchLength, branchThickness, depth + 1, config)
        )
      }
    }
  }

  // Convert 2D points to 3D segments (z=0 for all bolts in ortho)
  const segments: BoltSegment[] = []
  for (let i = 0; i < points.length - 1; i++) {
    segments.push({
      start: new THREE.Vector3(points[i].x, points[i].y, 0),
      end: new THREE.Vector3(points[i + 1].x, points[i + 1].y, 0),
      thickness,
    })
  }

  return { segments, branches, thickness }
}

/**
 * Generate a single lightning bolt (convenience wrapper)
 * Seeds RNG and calls generateBoltPath
 *
 * @param angle - Starting angle in radians (0-2π for radial distribution)
 * @param length - Total bolt length in pixels (50-220px for variation)
 * @param thickness - Core bolt thickness in pixels (2-3px)
 * @param frameNumber - Frame number for deterministic seeding (0-11)
 * @param config - Bolt generation configuration
 * @returns BoltPath with segments and branches
 */
export function generateBolt(
  angle: number,
  length: number,
  thickness: number,
  frameNumber: number = 0,
  config: BoltConfig = DEFAULT_BOLT_CONFIG
): BoltPath {
  // Seed RNG for deterministic generation
  // Formula from Canvas 2D: seed = 1000 + frameNumber * 137 + angle * 100
  setSeed(1000 + frameNumber * 137 + Math.floor(angle * 100))

  // Generate bolt starting at origin
  return generateBoltPath(
    new THREE.Vector2(0, 0),
    angle,
    length,
    thickness,
    0, // depth = 0 for primary bolt
    config
  )
}

/**
 * Generate multiple bolts in radial pattern
 * CRITICAL PATH: Ortho R3F Migration - Full implementation with branching
 *
 * @param boltCount - Number of bolts (8-10 for production, 1 for testing)
 * @param frameNumber - Frame number for animation (0-42 for 43 frames)
 * @param config - Bolt generation configuration
 * @returns Array of BoltPath objects with branches
 */
export function generateBolts(
  boltCount: number = 10,
  frameNumber: number = 0,
  config: BoltConfig = DEFAULT_BOLT_CONFIG
): BoltPath[] {
  // Seed RNG at start for consistent multi-bolt generation
  setSeed(2000 + frameNumber * 173)

  const bolts: BoltPath[] = []

  // Radial distribution with slight randomization
  const angleStep = (Math.PI * 2) / boltCount
  // Slow rotation over frames for visual interest (full rotation over 43 frames)
  const rotationOffset = (frameNumber / 43) * angleStep * 0.5

  for (let i = 0; i < boltCount; i++) {
    // Base angle with slight random variation (±5°)
    const baseAngle = i * angleStep + rotationOffset
    const angleVariation = (seededRandom() - 0.5) * (10 * Math.PI / 180) // ±5°
    const angle = baseAngle + angleVariation

    // Length variation matching Canvas 2D distribution:
    // 40% short (50-80px), 30% medium (100-150px), 30% long (180-220px)
    const rand = seededRandom()
    let length: number
    if (rand < 0.4) {
      length = randomRange(50, 80) // Short bolts
    } else if (rand < 0.7) {
      length = randomRange(100, 150) // Medium bolts
    } else {
      length = randomRange(180, 220) // Long bolts (reach edge)
    }

    // Thickness variation
    const thickness = randomRange(config.coreThicknessMin, config.coreThicknessMax)

    // Generate bolt with branching
    bolts.push(generateBolt(angle, length, thickness, frameNumber, config))
  }

  return bolts
}

/**
 * Count total segments including branches (for debugging)
 */
export function countTotalSegments(path: BoltPath): number {
  let count = path.segments.length
  for (const branch of path.branches) {
    count += countTotalSegments(branch)
  }
  return count
}

/**
 * Count total branches in a bolt path (for debugging)
 */
export function countTotalBranches(path: BoltPath): number {
  let count = path.branches.length
  for (const branch of path.branches) {
    count += countTotalBranches(branch)
  }
  return count
}
