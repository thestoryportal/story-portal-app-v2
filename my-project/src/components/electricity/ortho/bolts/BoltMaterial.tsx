/**
 * BoltMaterial.tsx
 *
 * Material component for lightning bolts with additive blending.
 * Week 1 PoC: Simple bright material, no multi-layer glow.
 *
 * Future (Week 3+): Multi-layer glow system with 5 color layers.
 */

import * as THREE from 'three'

export interface BoltMaterialProps {
  intensity?: number // 0-1, for animation
  color?: THREE.Color | string
  opacity?: number
}

/**
 * Create material for lightning bolt
 * Week 1 PoC: Single color with additive blending
 *
 * @param props - Material properties
 * @returns THREE.MeshBasicMaterial with additive blending
 */
export function createBoltMaterial(props: BoltMaterialProps = {}): THREE.MeshBasicMaterial {
  const {
    intensity = 1.0,
    color = '#F0F050', // Bright yellow (Canvas 2D spec: #F0F050)
    opacity = 1.0,
  } = props

  const material = new THREE.MeshBasicMaterial({
    color: color,
    transparent: true,
    opacity: opacity * intensity,
    blending: THREE.AdditiveBlending, // KEY: Additive blending for glow effect
    depthWrite: false, // Don't write to depth buffer (allows overlapping glow)
    side: THREE.DoubleSide, // Render both sides
  })

  return material
}

/**
 * BoltMaterial Component
 * React wrapper for bolt material (for declarative usage in JSX)
 *
 * Week 1 PoC: Pass as children to <mesh>
 */
export function BoltMaterial({ intensity = 1.0, color = '#F0F050', opacity = 1.0 }: BoltMaterialProps) {
  const material = createBoltMaterial({ intensity, color, opacity })

  return <primitive object={material} attach="material" />
}

export default BoltMaterial
