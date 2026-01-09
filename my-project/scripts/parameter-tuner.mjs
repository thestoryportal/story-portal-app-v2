#!/usr/bin/env node
/**
 * Closed-Loop Parameter Tuner v1.0
 *
 * Gradient-based parameter optimization for faster convergence.
 * Instead of AI guessing parameter changes, we compute gradients
 * and suggest optimal next steps.
 *
 * Features:
 * - Finite difference gradient estimation
 * - Adaptive learning rate
 * - Parameter bounds enforcement
 * - Momentum for smoother convergence
 *
 * Usage:
 *   import { ParameterTuner } from './parameter-tuner.mjs'
 */

export class ParameterTuner {
  constructor(config = {}) {
    this.learningRate = config.learningRate || 0.3
    this.momentum = config.momentum || 0.1
    this.minLearningRate = config.minLearningRate || 0.05
    this.maxLearningRate = config.maxLearningRate || 0.5

    this.history = []
    this.velocity = {} // For momentum
  }

  /**
   * Define tunable parameters with bounds
   */
  defineParameters(paramDefs) {
    this.parameters = paramDefs
    // Initialize velocity for each parameter
    for (const key in paramDefs) {
      this.velocity[key] = 0
    }
  }

  /**
   * Record an observation (iteration result)
   */
  recordObservation(params, score, metrics = {}) {
    this.history.push({
      params: { ...params },
      score,
      metrics,
      timestamp: new Date().toISOString()
    })
  }

  /**
   * Estimate gradient using finite differences
   */
  estimateGradient() {
    if (this.history.length < 2) {
      return null // Need at least 2 observations
    }

    const current = this.history[this.history.length - 1]
    const previous = this.history[this.history.length - 2]

    const gradient = {}
    const scoreChange = current.score - previous.score

    for (const key in current.params) {
      const paramChange = current.params[key] - previous.params[key]

      if (Math.abs(paramChange) > 0.001) {
        // Gradient = ∂score/∂param
        gradient[key] = scoreChange / paramChange
      } else {
        gradient[key] = 0
      }
    }

    return gradient
  }

  /**
   * Suggest next parameter values based on gradient
   */
  suggestNextParams(currentParams, targetScore = 95) {
    if (this.history.length < 2) {
      // Not enough data, suggest random exploration
      return this.exploreRandomly(currentParams)
    }

    const gradient = this.estimateGradient()
    if (!gradient) {
      return this.exploreRandomly(currentParams)
    }

    const currentScore = this.history[this.history.length - 1].score
    const scoreGap = targetScore - currentScore

    // Adaptive learning rate based on score gap
    const adaptiveLR = this.adaptLearningRate(scoreGap)

    const suggestions = {}

    for (const key in currentParams) {
      const paramDef = this.parameters[key]
      if (!paramDef) continue

      // Apply gradient descent with momentum
      const gradientStep = gradient[key] || 0
      this.velocity[key] = this.momentum * this.velocity[key] + adaptiveLR * gradientStep

      let newValue = currentParams[key] + this.velocity[key]

      // Enforce bounds
      if (paramDef.min !== undefined) {
        newValue = Math.max(paramDef.min, newValue)
      }
      if (paramDef.max !== undefined) {
        newValue = Math.min(paramDef.max, newValue)
      }

      // Apply step size if defined
      if (paramDef.step) {
        newValue = Math.round(newValue / paramDef.step) * paramDef.step
      }

      suggestions[key] = newValue
    }

    return {
      suggested: suggestions,
      gradient,
      learningRate: adaptiveLR,
      confidence: this.calculateConfidence(gradient)
    }
  }

  /**
   * Adapt learning rate based on score gap
   */
  adaptLearningRate(scoreGap) {
    if (scoreGap > 30) {
      // Large gap - be more aggressive
      return Math.min(this.maxLearningRate, this.learningRate * 1.5)
    } else if (scoreGap > 10) {
      // Medium gap - standard learning rate
      return this.learningRate
    } else {
      // Small gap - be conservative
      return Math.max(this.minLearningRate, this.learningRate * 0.5)
    }
  }

  /**
   * Calculate confidence in gradient estimate
   */
  calculateConfidence(gradient) {
    if (this.history.length < 3) return 'LOW'

    // Check if recent gradients are consistent
    if (this.history.length >= 3) {
      const last3 = this.history.slice(-3)
      const scoreChanges = []
      for (let i = 1; i < last3.length; i++) {
        scoreChanges.push(last3[i].score - last3[i - 1].score)
      }

      // If all changes have same sign, confidence is higher
      const allPositive = scoreChanges.every(c => c > 0)
      const allNegative = scoreChanges.every(c => c < 0)

      if (allPositive || allNegative) {
        return 'HIGH'
      }
    }

    return 'MEDIUM'
  }

  /**
   * Explore randomly when not enough data
   */
  exploreRandomly(currentParams) {
    const exploration = {}

    for (const key in currentParams) {
      const paramDef = this.parameters[key]
      if (!paramDef) continue

      // Random perturbation within step size
      const perturbation = (Math.random() - 0.5) * (paramDef.step || 1) * 2

      let newValue = currentParams[key] + perturbation

      // Enforce bounds
      if (paramDef.min !== undefined) {
        newValue = Math.max(paramDef.min, newValue)
      }
      if (paramDef.max !== undefined) {
        newValue = Math.min(paramDef.max, newValue)
      }

      exploration[key] = newValue
    }

    return {
      suggested: exploration,
      mode: 'EXPLORATION',
      confidence: 'LOW'
    }
  }

  /**
   * Detect if we're stuck in local minimum
   */
  isStuck() {
    if (this.history.length < 5) return false

    const last5Scores = this.history.slice(-5).map(h => h.score)
    const variance = this.calculateVariance(last5Scores)

    // If variance is very low, we might be stuck
    return variance < 1.0
  }

  /**
   * Calculate variance of an array
   */
  calculateVariance(values) {
    const mean = values.reduce((a, b) => a + b, 0) / values.length
    const variance = values.reduce((sum, val) => sum + (val - mean) ** 2, 0) / values.length
    return variance
  }

  /**
   * Get optimization summary
   */
  getSummary() {
    if (this.history.length === 0) {
      return { message: 'No optimization history yet' }
    }

    const scores = this.history.map(h => h.score)
    const bestScore = Math.max(...scores)
    const bestIteration = this.history.find(h => h.score === bestScore)

    const currentScore = scores[scores.length - 1]
    const improvement = currentScore - scores[0]

    return {
      totalIterations: this.history.length,
      currentScore,
      bestScore,
      bestParams: bestIteration.params,
      totalImprovement: parseFloat(improvement.toFixed(2)),
      improvementRate: parseFloat((improvement / this.history.length).toFixed(2)),
      isStuck: this.isStuck(),
      trend: this.analyzeTrend(scores)
    }
  }

  /**
   * Analyze score trend
   */
  analyzeTrend(scores) {
    if (scores.length < 3) return 'INSUFFICIENT_DATA'

    const recent = scores.slice(-3)
    const older = scores.slice(-6, -3)

    if (recent.length < 3 || older.length === 0) return 'BUILDING'

    const recentAvg = recent.reduce((a, b) => a + b, 0) / recent.length
    const olderAvg = older.reduce((a, b) => a + b, 0) / older.length

    if (recentAvg > olderAvg + 2) return 'IMPROVING'
    if (recentAvg < olderAvg - 2) return 'REGRESSING'
    return 'STABLE'
  }
}

/**
 * Example parameter definitions for electricity animation
 */
export const ELECTRICITY_PARAMS = {
  boltLength: {
    current: 120,
    min: 80,
    max: 220,
    step: 10,
    description: 'Length of lightning bolts'
  },
  boltCount: {
    current: 8,
    min: 4,
    max: 16,
    step: 1,
    description: 'Number of bolts'
  },
  glowRadius: {
    current: 45,
    min: 20,
    max: 80,
    step: 5,
    description: 'Inner glow radius'
  },
  outerGlowRadius: {
    current: 120,
    min: 60,
    max: 180,
    step: 10,
    description: 'Outer glow radius'
  },
  flickerRate: {
    current: 0.1,
    min: 0.05,
    max: 0.3,
    step: 0.02,
    description: 'Flicker frequency'
  },
  coreBrightness: {
    current: 0.95,
    min: 0.5,
    max: 1.0,
    step: 0.05,
    description: 'Core hotspot brightness'
  }
}

export default ParameterTuner
