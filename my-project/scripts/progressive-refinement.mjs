#!/usr/bin/env node
/**
 * Progressive Refinement Protocol v1.0
 *
 * Phase-based iteration strategy to prevent oscillation and ensure
 * systematic convergence to target animation.
 *
 * Phases:
 * 1. STRUCTURAL MATCH (iterations 1-3): Bolt count, length, distribution
 * 2. COLOR CALIBRATION (iterations 4-5): Color palette precision
 * 3. TEMPORAL REFINEMENT (iterations 6-7): Motion characteristics
 * 4. POLISH (iterations 8+): Final perceptual match
 *
 * Usage:
 *   import { determinePhase, getPhaseGuidance } from './progressive-refinement.mjs'
 */

export const PHASES = {
  STRUCTURAL: {
    id: 'structural',
    name: 'Structural Match',
    iterationRange: [1, 3],
    goals: [
      'Get bolt count correct',
      'Match bolt length distribution',
      'Achieve correct coverage area',
      'Ensure glow radii are in range'
    ],
    primaryMetrics: ['bolts.count', 'bolts.avgLength', 'glowRegions.inner.radius', 'glowRegions.outer.radius'],
    ignoreMetrics: ['color.hue', 'color.saturation', 'temporal.flicker'],
    successCriteria: {
      semanticMatch: 85,
      description: '>85% structural similarity'
    },
    guidance: {
      focus: 'Focus ONLY on geometry and structure. Ignore color precision and timing issues.',
      metricWeights: {
        semantic: 0.6,
        spatial: 0.3,
        color: 0.05,
        temporal: 0.05
      }
    }
  },

  COLOR: {
    id: 'color',
    name: 'Color Calibration',
    iterationRange: [4, 5],
    goals: [
      'Match hue values precisely',
      'Calibrate saturation levels',
      'Adjust luminance/brightness',
      'Fine-tune color gradients'
    ],
    primaryMetrics: ['color.hue', 'color.saturation', 'color.luminance'],
    ignoreMetrics: ['temporal.flicker', 'temporal.rhythm'],
    successCriteria: {
      hueDifference: 5,
      luminanceDifference: 10,
      description: '<5° hue, <10% luminance difference'
    },
    guidance: {
      focus: 'Structural match achieved. Now focus ONLY on color precision. Do not adjust geometry.',
      metricWeights: {
        semantic: 0.1,
        spatial: 0.1,
        color: 0.7,
        temporal: 0.1
      }
    }
  },

  TEMPORAL: {
    id: 'temporal',
    name: 'Temporal Refinement',
    iterationRange: [6, 7],
    goals: [
      'Match motion characteristics',
      'Calibrate flicker frequency',
      'Adjust rhythm patterns',
      'Ensure temporal smoothness'
    ],
    primaryMetrics: ['temporal.flicker', 'temporal.rhythm', 'temporal.smoothness', 'motion.similarity'],
    ignoreMetrics: ['spatial.minor'],
    successCriteria: {
      motionSimilarity: 85,
      description: '>85% motion similarity'
    },
    guidance: {
      focus: 'Structure and color are good. Now focus ONLY on motion and timing. Do not change geometry or colors.',
      metricWeights: {
        semantic: 0.05,
        spatial: 0.05,
        color: 0.1,
        temporal: 0.8
      }
    }
  },

  POLISH: {
    id: 'polish',
    name: 'Final Polish',
    iterationRange: [8, 20],
    goals: [
      'Achieve final perceptual match',
      'Fine-tune all remaining details',
      'Optimize overall quality',
      'Reach target score'
    ],
    primaryMetrics: ['perceptual.lpips', 'overall.score'],
    ignoreMetrics: [],
    successCriteria: {
      overallScore: 95,
      description: '≥95% overall match'
    },
    guidance: {
      focus: 'Make small, targeted adjustments to reach final target. Balance all aspects.',
      metricWeights: {
        semantic: 0.2,
        spatial: 0.2,
        color: 0.3,
        temporal: 0.3
      }
    }
  }
}

/**
 * Determine which phase we're in based on iteration number and scores
 */
export function determinePhase(iterationNum, scoreHistory = {}) {
  // Default phase-by-iteration
  if (iterationNum <= 3) {
    return PHASES.STRUCTURAL
  } else if (iterationNum <= 5) {
    return PHASES.COLOR
  } else if (iterationNum <= 7) {
    return PHASES.TEMPORAL
  } else {
    return PHASES.POLISH
  }

  // Advanced: Could also check if phase goals are met early and advance
  // For now, using simple iteration-based progression
}

/**
 * Get phase-specific guidance for the Animation Expert
 */
export function getPhaseGuidance(phase, analysisData = {}) {
  const phaseInfo = typeof phase === 'string'
    ? Object.values(PHASES).find(p => p.id === phase)
    : phase

  if (!phaseInfo) return null

  return {
    phase: phaseInfo.name,
    iteration: phaseInfo.iterationRange,

    primaryGoals: phaseInfo.goals,

    focus: phaseInfo.guidance.focus,

    criticalMetrics: phaseInfo.primaryMetrics,
    ignoreForNow: phaseInfo.ignoreMetrics,

    successCriteria: phaseInfo.successCriteria,

    metricWeights: phaseInfo.guidance.metricWeights,

    instructions: generatePhaseInstructions(phaseInfo, analysisData)
  }
}

/**
 * Generate phase-specific instructions based on current analysis
 */
function generatePhaseInstructions(phase, analysisData) {
  const instructions = []

  switch (phase.id) {
    case 'structural':
      instructions.push('📐 STRUCTURAL PHASE: Focus on geometry only')
      instructions.push('✓ DO: Adjust bolt count, length, thickness, glow radii')
      instructions.push('✗ IGNORE: Color precision, fine timing details')

      if (analysisData.semanticComparison) {
        const { bolts, glow } = analysisData.semanticComparison
        if (bolts && Math.abs(bolts.countDifference) > 2) {
          instructions.push(`⚠️ PRIORITY: ${bolts.countDifference > 0 ? 'Reduce' : 'Add'} ${Math.abs(bolts.countDifference)} bolts`)
        }
        if (bolts && Math.abs(parseFloat(bolts.lengthDifferencePercent)) > 20) {
          instructions.push(`⚠️ PRIORITY: Bolt length is ${bolts.lengthDifferencePercent}% off - adjust`)
        }
      }
      break

    case 'color':
      instructions.push('🎨 COLOR PHASE: Focus on color precision')
      instructions.push('✓ DO: Adjust hue, saturation, luminance, color gradients')
      instructions.push('✗ IGNORE: Geometry (keep current structure), timing')
      instructions.push('⚠️ DO NOT change bolt count or glow radii unless severely broken')

      if (analysisData.colorAnalysis) {
        const { hueDifference, luminanceDifference } = analysisData.colorAnalysis
        if (Math.abs(hueDifference) > 5) {
          instructions.push(`⚠️ PRIORITY: Hue is ${hueDifference.toFixed(1)}° off`)
        }
        if (Math.abs(luminanceDifference) > 10) {
          instructions.push(`⚠️ PRIORITY: Brightness is ${luminanceDifference.toFixed(1)}% ${luminanceDifference > 0 ? 'too bright' : 'too dark'}`)
        }
      }
      break

    case 'temporal':
      instructions.push('⏱️ TEMPORAL PHASE: Focus on motion and timing')
      instructions.push('✓ DO: Adjust flicker rate, rhythm, animation timing')
      instructions.push('✗ IGNORE: Geometry and colors (already calibrated)')
      instructions.push('⚠️ DO NOT change structural or color properties')

      if (analysisData.motionAnalysis) {
        const { flickerRate, smoothness } = analysisData.motionAnalysis
        if (flickerRate && Math.abs(flickerRate.difference) > 15) {
          instructions.push(`⚠️ PRIORITY: Flicker rate is ${flickerRate.difference}% off`)
        }
      }
      break

    case 'polish':
      instructions.push('✨ POLISH PHASE: Final refinements')
      instructions.push('✓ DO: Make small, balanced adjustments across all properties')
      instructions.push('⚠️ Changes should be minimal and targeted')
      instructions.push('Goal: Achieve ≥95% overall score')
      break
  }

  return instructions
}

/**
 * Calculate phase-weighted score
 */
export function calculatePhaseScore(metrics, phase) {
  const phaseInfo = typeof phase === 'string'
    ? Object.values(PHASES).find(p => p.id === phase)
    : phase

  if (!phaseInfo || !metrics) return null

  const weights = phaseInfo.guidance.metricWeights
  let weightedScore = 0

  if (metrics.semantic && weights.semantic) {
    weightedScore += metrics.semantic * weights.semantic
  }
  if (metrics.spatial && weights.spatial) {
    weightedScore += metrics.spatial * weights.spatial
  }
  if (metrics.color && weights.color) {
    weightedScore += metrics.color * weights.color
  }
  if (metrics.temporal && weights.temporal) {
    weightedScore += metrics.temporal * weights.temporal
  }

  return Math.round(weightedScore)
}

/**
 * Check if phase goals are met
 */
export function isPhaseComplete(phase, metrics) {
  const phaseInfo = typeof phase === 'string'
    ? Object.values(PHASES).find(p => p.id === phase)
    : phase

  if (!phaseInfo || !metrics) return false

  const { successCriteria } = phaseInfo

  switch (phaseInfo.id) {
    case 'structural':
      return metrics.semantic >= (successCriteria.semanticMatch || 85)

    case 'color':
      return (
        metrics.color?.hueDifference <= (successCriteria.hueDifference || 5) &&
        metrics.color?.luminanceDifference <= (successCriteria.luminanceDifference || 10)
      )

    case 'temporal':
      return metrics.motion?.similarity >= (successCriteria.motionSimilarity || 85)

    case 'polish':
      return metrics.overall >= (successCriteria.overallScore || 95)

    default:
      return false
  }
}

export default {
  PHASES,
  determinePhase,
  getPhaseGuidance,
  calculatePhaseScore,
  isPhaseComplete
}
