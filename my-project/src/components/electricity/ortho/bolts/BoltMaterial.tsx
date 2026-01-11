/**
 * BoltMaterial.tsx
 *
 * Material component for lightning bolts with additive blending.
 * Supports both static intensity (prop) and animated intensity (ref).
 *
 * For animation, pass intensityRef and the material will update
 * its opacity on every frame via useFrame.
 */

import { useRef, MutableRefObject } from 'react'
import { useFrame } from '@react-three/fiber'
import * as THREE from 'three'

export interface BoltMaterialProps {
  intensity?: number // Static intensity 0-1 (used if intensityRef not provided)
  intensityRef?: MutableRefObject<number> // Animated intensity ref (updates every frame)
  color?: THREE.Color | string
  opacity?: number
}

/**
 * Create material for lightning bolt
 *
 * @param props - Material properties
 * @returns THREE.MeshBasicMaterial with additive blending
 */
export function createBoltMaterial(props: BoltMaterialProps = {}): THREE.MeshBasicMaterial {
  const {
    intensity = 1.0,
    color = '#F0F050',
    opacity = 1.0,
  } = props

  const material = new THREE.MeshBasicMaterial({
    color: color,
    transparent: true,
    opacity: opacity * intensity,
    blending: THREE.AdditiveBlending,
    depthWrite: false,
    side: THREE.DoubleSide,
  })

  return material
}

/**
 * BoltMaterial Component
 * React Three Fiber material that supports animated intensity via ref
 *
 * If intensityRef is provided, the material opacity updates every frame.
 * Otherwise, it uses the static intensity prop.
 */
export function BoltMaterial({
  intensity = 1.0,
  intensityRef,
  color = '#F0F050',
  opacity = 1.0
}: BoltMaterialProps) {
  const materialRef = useRef<THREE.MeshBasicMaterial>(null)

  // If using animated intensity, update material opacity every frame
  useFrame(() => {
    if (materialRef.current && intensityRef) {
      materialRef.current.opacity = opacity * intensityRef.current
    }
  })

  // Initial opacity uses either ref value or static intensity
  const initialOpacity = intensityRef ? opacity * intensityRef.current : opacity * intensity

  return (
    <meshBasicMaterial
      ref={materialRef}
      color={color}
      transparent={true}
      opacity={initialOpacity}
      blending={THREE.AdditiveBlending}
      depthWrite={false}
      side={THREE.DoubleSide}
    />
  )
}

export default BoltMaterial
