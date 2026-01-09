#!/usr/bin/env node
/**
 * Parameter-to-Visual Impact Database v1.0
 *
 * Learning database that records parameter→visual impact mappings.
 * Tracks what code changes produce what visual effects across iterations.
 *
 * Capabilities:
 * - Record parameter changes and their visual/score impacts
 * - Query impact database for predictions
 * - Estimate gradients (∂score/∂parameter)
 * - Cross-project learning aggregation
 * - Confidence tracking based on observation count
 *
 * Usage:
 *   import { ParameterImpactDB } from './parameter-impact-database.mjs'
 */

import fs from 'fs/promises'
import path from 'path'

export class ParameterImpactDB {
  constructor(dbPath = './animation-parameter-impacts.json') {
    this.dbPath = dbPath
    this.data = {
      parameters: {},
      observations: [],
      statistics: {
        totalObservations: 0,
        totalProjects: 0,
        lastUpdated: null
      }
    }
  }

  /**
   * Load database from disk
   */
  async load() {
    try {
      const content = await fs.readFile(this.dbPath, 'utf-8')
      this.data = JSON.parse(content)
      return true
    } catch (err) {
      // File doesn't exist yet - will be created on first save
      return false
    }
  }

  /**
   * Save database to disk
   */
  async save() {
    this.data.statistics.lastUpdated = new Date().toISOString()
    await fs.writeFile(this.dbPath, JSON.stringify(this.data, null, 2))
  }

  /**
   * Record an observation of parameter change → visual impact
   */
  async recordObservation(observation) {
    const {
      project,
      iteration,
      parameter,
      oldValue,
      newValue,
      scoreBefore,
      scoreAfter,
      visualEffect,
      context = {}
    } = observation

    const change = newValue - oldValue
    const scoreImpact = scoreAfter - scoreBefore

    // Create observation record
    const record = {
      id: `obs_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
      timestamp: new Date().toISOString(),
      project,
      iteration,
      parameter,
      oldValue,
      newValue,
      change,
      scoreBefore,
      scoreAfter,
      scoreImpact,
      visualEffect,
      context
    }

    // Add to observations list
    this.data.observations.push(record)

    // Update parameter-specific data
    if (!this.data.parameters[parameter]) {
      this.data.parameters[parameter] = {
        name: parameter,
        impacts: [],
        learnings: [],
        statistics: {
          observationCount: 0,
          avgScoreImpact: 0,
          bestChange: null,
          worstChange: null
        }
      }
    }

    const paramData = this.data.parameters[parameter]

    // Add impact record
    paramData.impacts.push({
      change: `${change > 0 ? '+' : ''}${change}`,
      visualEffect,
      scoreImpact: scoreImpact.toFixed(2),
      context: `From ${oldValue} to ${newValue}`,
      project,
      confidence: this.calculateConfidence(parameter, change)
    })

    // Update statistics
    paramData.statistics.observationCount++
    paramData.statistics.avgScoreImpact =
      (paramData.statistics.avgScoreImpact * (paramData.statistics.observationCount - 1) + scoreImpact) /
      paramData.statistics.observationCount

    if (!paramData.statistics.bestChange || scoreImpact > paramData.statistics.bestChange.scoreImpact) {
      paramData.statistics.bestChange = {
        change,
        scoreImpact,
        from: oldValue,
        to: newValue
      }
    }

    if (!paramData.statistics.worstChange || scoreImpact < paramData.statistics.worstChange.scoreImpact) {
      paramData.statistics.worstChange = {
        change,
        scoreImpact,
        from: oldValue,
        to: newValue
      }
    }

    // Extract learnings
    this.extractLearnings(parameter)

    // Update global statistics
    this.data.statistics.totalObservations++

    await this.save()

    return record.id
  }

  /**
   * Query impact database for predictions
   */
  query(options) {
    const {
      parameter,
      currentValue,
      desiredChange,
      suggestedValue,
      changeType // 'increase' | 'decrease'
    } = options

    const paramData = this.data.parameters[parameter]

    if (!paramData || paramData.impacts.length === 0) {
      return {
        available: false,
        reason: 'No historical data for this parameter'
      }
    }

    // Calculate intended change
    const change = suggestedValue ? suggestedValue - currentValue : desiredChange

    // Find similar changes in history
    const similarChanges = paramData.impacts.filter(impact => {
      const historicalChange = parseFloat(impact.change)
      const sameDirection = (historicalChange > 0 && change > 0) || (historicalChange < 0 && change < 0)
      const similarMagnitude = Math.abs(historicalChange / change) > 0.5 && Math.abs(historicalChange / change) < 2
      return sameDirection && similarMagnitude
    })

    if (similarChanges.length === 0) {
      // Estimate based on gradient
      const gradient = this.estimateGradient(parameter, currentValue)
      const expectedScoreImpact = gradient * change

      return {
        available: true,
        suggestedChange: change,
        expectedScoreImpact: parseFloat(expectedScoreImpact.toFixed(2)),
        confidence: 0.4, // Low confidence - extrapolating
        similarCases: 0,
        method: 'gradient_estimation',
        gradient
      }
    }

    // Average score impact from similar changes
    const avgScoreImpact = similarChanges.reduce((sum, c) => sum + parseFloat(c.scoreImpact), 0) / similarChanges.length

    return {
      available: true,
      suggestedChange: change,
      expectedScoreImpact: parseFloat(avgScoreImpact.toFixed(2)),
      confidence: this.calculateConfidence(parameter, change),
      similarCases: similarChanges.length,
      method: 'historical_average',
      examples: similarChanges.slice(0, 3).map(c => ({
        change: c.change,
        scoreImpact: c.scoreImpact,
        visualEffect: c.visualEffect
      }))
    }
  }

  /**
   * Estimate gradient (∂score/∂parameter) at a given value
   */
  estimateGradient(parameter, value) {
    const paramData = this.data.parameters[parameter]

    if (!paramData || paramData.impacts.length < 2) {
      return 0 // Can't estimate with < 2 observations
    }

    // Find observations near this value
    const observations = this.data.observations
      .filter(obs => obs.parameter === parameter)
      .filter(obs => Math.abs(obs.oldValue - value) < value * 0.3) // Within 30% of target value

    if (observations.length < 2) {
      // Fall back to global gradient for this parameter
      const allObs = this.data.observations.filter(obs => obs.parameter === parameter)
      const totalScoreChange = allObs.reduce((sum, obs) => sum + obs.scoreImpact, 0)
      const totalParamChange = allObs.reduce((sum, obs) => sum + Math.abs(obs.change), 0)
      return totalParamChange > 0 ? totalScoreChange / totalParamChange : 0
    }

    // Calculate local gradient using finite differences
    let gradientSum = 0
    let count = 0

    for (const obs of observations) {
      if (obs.change !== 0) {
        const localGradient = obs.scoreImpact / obs.change
        gradientSum += localGradient
        count++
      }
    }

    return count > 0 ? gradientSum / count : 0
  }

  /**
   * Calculate confidence based on observation count and consistency
   */
  calculateConfidence(parameter, change) {
    const paramData = this.data.parameters[parameter]

    if (!paramData) return 0.1

    const observationCount = paramData.statistics.observationCount

    // Base confidence on observation count
    let confidence = Math.min(observationCount / 10, 0.7) // Max 0.7 from count

    // Find similar changes
    const similarChanges = paramData.impacts.filter(impact => {
      const historicalChange = parseFloat(impact.change)
      return (historicalChange > 0 && change > 0) || (historicalChange < 0 && change < 0)
    })

    if (similarChanges.length > 0) {
      // Check consistency of impacts
      const impacts = similarChanges.map(c => parseFloat(c.scoreImpact))
      const avgImpact = impacts.reduce((sum, i) => sum + i, 0) / impacts.length
      const variance = impacts.reduce((sum, i) => sum + Math.pow(i - avgImpact, 2), 0) / impacts.length
      const stdDev = Math.sqrt(variance)

      // Lower variance = higher confidence
      const consistencyBonus = stdDev < 2 ? 0.2 : stdDev < 5 ? 0.1 : 0
      confidence += consistencyBonus
    }

    return Math.min(confidence, 0.95) // Cap at 0.95
  }

  /**
   * Extract learnings from observation patterns
   */
  extractLearnings(parameter) {
    const paramData = this.data.parameters[parameter]
    const observations = this.data.observations.filter(obs => obs.parameter === parameter)

    if (observations.length < 3) return // Need enough data

    const learnings = []

    // Learning 1: Linear relationship detection
    const gradient = this.estimateGradient(parameter, observations[0].oldValue)
    if (Math.abs(gradient) > 0.5) {
      const direction = gradient > 0 ? 'increase' : 'decrease'
      learnings.push(
        `${direction === 'increase' ? 'Increasing' : 'Decreasing'} ${parameter} typically improves score (gradient ≈ ${gradient.toFixed(2)})`
      )
    }

    // Learning 2: Diminishing returns detection
    const sortedByValue = [...observations].sort((a, b) => a.newValue - b.newValue)
    if (sortedByValue.length >= 5) {
      const lowValueImpacts = sortedByValue.slice(0, 2).map(o => o.scoreImpact / Math.abs(o.change))
      const highValueImpacts = sortedByValue.slice(-2).map(o => o.scoreImpact / Math.abs(o.change))

      const avgLow = lowValueImpacts.reduce((sum, i) => sum + i, 0) / lowValueImpacts.length
      const avgHigh = highValueImpacts.reduce((sum, i) => sum + i, 0) / highValueImpacts.length

      if (avgLow > avgHigh * 1.5) {
        const threshold = sortedByValue[Math.floor(sortedByValue.length / 2)].newValue
        learnings.push(`Diminishing returns detected after ${parameter} ≈ ${threshold.toFixed(0)}`)
      }
    }

    // Learning 3: Optimal range detection
    const positiveImpacts = observations.filter(obs => obs.scoreImpact > 2)
    if (positiveImpacts.length >= 3) {
      const values = positiveImpacts.map(obs => obs.newValue)
      const minOptimal = Math.min(...values)
      const maxOptimal = Math.max(...values)
      learnings.push(`Optimal range appears to be ${minOptimal.toFixed(0)} - ${maxOptimal.toFixed(0)}`)
    }

    // Learning 4: Avoid certain ranges
    const negativeImpacts = observations.filter(obs => obs.scoreImpact < -5)
    if (negativeImpacts.length >= 2) {
      const values = negativeImpacts.map(obs => obs.newValue)
      const avgBad = values.reduce((sum, v) => sum + v, 0) / values.length
      learnings.push(`Avoid ${parameter} near ${avgBad.toFixed(0)} (historically poor results)`)
    }

    paramData.learnings = learnings
  }

  /**
   * Get all learnings for a parameter
   */
  getLearnings(parameter) {
    const paramData = this.data.parameters[parameter]
    return paramData?.learnings || []
  }

  /**
   * Get statistics summary
   */
  getStatistics() {
    return {
      ...this.data.statistics,
      parameterCount: Object.keys(this.data.parameters).length,
      parameters: Object.entries(this.data.parameters).map(([name, data]) => ({
        name,
        observations: data.statistics.observationCount,
        avgImpact: data.statistics.avgScoreImpact.toFixed(2),
        learnings: data.learnings.length
      }))
    }
  }

  /**
   * Get recommended next value for a parameter
   */
  getRecommendation(parameter, currentValue, targetScoreIncrease = 10) {
    const gradient = this.estimateGradient(parameter, currentValue)

    if (gradient === 0) {
      return {
        available: false,
        reason: 'Insufficient data to make recommendation'
      }
    }

    // Calculate required change to achieve target score increase
    const requiredChange = targetScoreIncrease / gradient
    const suggestedValue = currentValue + requiredChange

    const paramData = this.data.parameters[parameter]
    const learnings = paramData?.learnings || []

    return {
      available: true,
      currentValue,
      suggestedValue: parseFloat(suggestedValue.toFixed(2)),
      change: parseFloat(requiredChange.toFixed(2)),
      expectedScoreIncrease: targetScoreIncrease,
      confidence: this.calculateConfidence(parameter, requiredChange),
      gradient,
      learnings
    }
  }

  /**
   * Clear all data (for testing)
   */
  async clear() {
    this.data = {
      parameters: {},
      observations: [],
      statistics: {
        totalObservations: 0,
        totalProjects: 0,
        lastUpdated: null
      }
    }
    await this.save()
  }
}

/**
 * Recorder function to be called after each iteration
 */
export async function recordIterationImpact(options) {
  const {
    project,
    iteration,
    parameterChanges, // Array of { parameter, oldValue, newValue }
    scoreBefore,
    scoreAfter,
    visualAnalysis,
    dbPath
  } = options

  const db = new ParameterImpactDB(dbPath)
  await db.load()

  const recordIds = []

  for (const change of parameterChanges) {
    const visualEffect = extractVisualEffect(change.parameter, visualAnalysis)

    const id = await db.recordObservation({
      project,
      iteration,
      parameter: change.parameter,
      oldValue: change.oldValue,
      newValue: change.newValue,
      scoreBefore,
      scoreAfter,
      visualEffect,
      context: {
        otherChanges: parameterChanges.filter(c => c.parameter !== change.parameter).map(c => c.parameter)
      }
    })

    recordIds.push(id)
  }

  return recordIds
}

/**
 * Helper: Extract visual effect description for parameter
 */
function extractVisualEffect(parameter, visualAnalysis) {
  if (!visualAnalysis) return 'Unknown visual effect'

  const text = typeof visualAnalysis === 'string' ? visualAnalysis : JSON.stringify(visualAnalysis)

  // Try to find mentions of this parameter's effect
  const patterns = {
    boltCount: /(\d+ (?:more|fewer|less|additional) bolts?)/i,
    boltLength: /(bolts? (?:are )?\d+%? (?:longer|shorter|too long|too short))/i,
    glowRadius: /(glow (?:is )?\d+%? (?:larger|smaller|bigger))/i,
    outerGlowOpacity: /(outer glow (?:is )?\d+%? (?:brighter|dimmer))/i
  }

  const pattern = patterns[parameter]
  if (pattern) {
    const match = text.match(pattern)
    if (match) return match[1]
  }

  return `Change in ${parameter}`
}

export default {
  ParameterImpactDB,
  recordIterationImpact
}
