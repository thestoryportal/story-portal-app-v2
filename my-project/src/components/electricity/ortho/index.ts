/**
 * Orthographic Electricity Module Exports
 */

export { ElectricityOrtho } from './ElectricityOrtho'
export type { ElectricityOrthoProps } from './ElectricityOrtho'

export { OrthoScene, CONTAINER_SIZE } from './scene/OrthoScene'
export type { OrthoSceneProps } from './scene/OrthoScene'

export { Bolt } from './bolts/Bolt'
export type { BoltProps } from './bolts/Bolt'

export { BoltMaterial, createBoltMaterial } from './bolts/BoltMaterial'
export type { BoltMaterialProps } from './bolts/BoltMaterial'

export { generateBolt, generateBolts, DEFAULT_BOLT_CONFIG } from './bolts/BoltGenerator'
export type { BoltPath, BoltSegment, BoltConfig } from './bolts/BoltGenerator'

export { createBoltGeometry, createBoltGeometries, calculateBoltLength } from './bolts/BoltGeometry'

export * from './animation/types'
export * from './utils/seededRandom'
