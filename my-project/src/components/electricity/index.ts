/**
 * Electricity Animation Components
 *
 * IMPORTANT: Canvas 2D (ElectricityAnimation) is DEPRECATED.
 * Use ElectricityOrtho (Orthographic R3F) for all new implementations.
 * See .claude/guardrails.md for details.
 *
 * Migration: Replace `import { ElectricityAnimation }` with:
 *   import { ElectricityOrtho } from '../components/electricity/ortho'
 */

// PRIMARY: Orthographic R3F implementation (USE THIS)
export { ElectricityOrtho } from './ortho'
export type { ElectricityOrthoProps } from './ortho'

// DEPRECATED: Canvas 2D implementation (DO NOT USE FOR NEW CODE)
// Kept for backwards compatibility during migration
// @deprecated Use ElectricityOrtho from './ortho' instead
export { ElectricityAnimation } from './ElectricityAnimation'
export type { ElectricityAnimationProps } from './ElectricityAnimation'

// Default export points to the new Ortho implementation
export { ElectricityOrtho as default } from './ortho'
