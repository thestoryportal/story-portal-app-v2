#!/usr/bin/env node
/**
 * Animation Pattern Library v1.0
 *
 * Cross-project learning system that stores successful animation patterns
 * and bootstraps new projects from similar patterns.
 *
 * Features:
 * - Pattern storage and retrieval
 * - Similarity matching
 * - Parameter bootstrapping
 * - Convergence history tracking
 *
 * Usage:
 *   import { PatternLibrary } from './pattern-library.mjs'
 */

import fs from 'fs/promises'
import path from 'path'

export class PatternLibrary {
  constructor(storagePath = './animation-patterns.json') {
    this.storagePath = storagePath
    this.patterns = []
  }

  /**
   * Load pattern library from disk
   */
  async load() {
    try {
      const data = await fs.readFile(this.storagePath, 'utf-8')
      const parsed = JSON.parse(data)
      this.patterns = parsed.patterns || []
      return true
    } catch (err) {
      // File doesn't exist or is invalid, start fresh
      this.patterns = []
      return false
    }
  }

  /**
   * Save pattern library to disk
   */
  async save() {
    const data = {
      version: '1.0',
      lastUpdated: new Date().toISOString(),
      patterns: this.patterns
    }
    await fs.writeFile(this.storagePath, JSON.stringify(data, null, 2))
  }

  /**
   * Add a new pattern from a successful iteration
   */
  async addPattern(patternData) {
    const pattern = {
      id: this.generateId(),
      name: patternData.name || 'Unnamed Pattern',
      type: patternData.type || 'electricity',

      // Signature (for matching)
      signature: patternData.signature || {},

      // Optimal parameters that worked
      optimalParams: patternData.optimalParams || {},

      // Color palette
      colorPalette: patternData.colorPalette || [],

      // Convergence info
      convergedIn: patternData.convergedIn || 0,
      finalScore: patternData.finalScore || 0,

      // Metadata
      createdAt: new Date().toISOString(),
      projectSource: patternData.projectSource || 'unknown',

      // Semantics
      semantics: patternData.semantics || {}
    }

    this.patterns.push(pattern)
    await this.save()

    return pattern.id
  }

  /**
   * Find similar patterns based on signature
   */
  findSimilar(targetSignature, limit = 5) {
    if (this.patterns.length === 0) {
      return []
    }

    const similarities = this.patterns.map(pattern => ({
      pattern,
      similarity: this.calculateSimilarity(targetSignature, pattern.signature)
    }))

    // Sort by similarity (descending)
    similarities.sort((a, b) => b.similarity - a.similarity)

    return similarities.slice(0, limit)
  }

  /**
   * Calculate similarity between two signatures (0-1)
   */
  calculateSimilarity(sig1, sig2) {
    if (!sig1 || !sig2) return 0

    let totalWeight = 0
    let matchScore = 0

    // Compare bolt characteristics
    if (sig1.boltCount !== undefined && sig2.boltCount !== undefined) {
      const boltDiff = Math.abs(sig1.boltCount - sig2.boltCount)
      matchScore += Math.max(0, 1 - boltDiff / 10) * 0.3
      totalWeight += 0.3
    }

    if (sig1.avgBoltLength !== undefined && sig2.avgBoltLength !== undefined) {
      const lengthDiff = Math.abs(sig1.avgBoltLength - sig2.avgBoltLength) / sig2.avgBoltLength
      matchScore += Math.max(0, 1 - lengthDiff) * 0.2
      totalWeight += 0.2
    }

    // Compare glow characteristics
    if (sig1.innerGlowRadius !== undefined && sig2.innerGlowRadius !== undefined) {
      const radiusDiff = Math.abs(sig1.innerGlowRadius - sig2.innerGlowRadius) / sig2.innerGlowRadius
      matchScore += Math.max(0, 1 - radiusDiff) * 0.2
      totalWeight += 0.2
    }

    // Compare color
    if (sig1.dominantHue !== undefined && sig2.dominantHue !== undefined) {
      const hueDiff = Math.min(Math.abs(sig1.dominantHue - sig2.dominantHue), 360 - Math.abs(sig1.dominantHue - sig2.dominantHue))
      matchScore += Math.max(0, 1 - hueDiff / 180) * 0.3
      totalWeight += 0.3
    }

    return totalWeight > 0 ? matchScore / totalWeight : 0
  }

  /**
   * Bootstrap parameters from a similar pattern
   */
  bootstrap(patternId) {
    const pattern = this.patterns.find(p => p.id === patternId)
    if (!pattern) {
      return null
    }

    return {
      suggestedParams: { ...pattern.optimalParams },
      colorPalette: [...pattern.colorPalette],
      expectedIterations: pattern.convergedIn || 7,
      confidence: pattern.finalScore >= 95 ? 'HIGH' : pattern.finalScore >= 85 ? 'MEDIUM' : 'LOW',
      source: {
        patternName: pattern.name,
        createdAt: pattern.createdAt,
        finalScore: pattern.finalScore
      }
    }
  }

  /**
   * Get pattern by ID
   */
  getPattern(patternId) {
    return this.patterns.find(p => p.id === patternId)
  }

  /**
   * Get all patterns
   */
  getAllPatterns() {
    return this.patterns
  }

  /**
   * Get statistics
   */
  getStatistics() {
    if (this.patterns.length === 0) {
      return {
        totalPatterns: 0,
        avgConvergenceIterations: 0,
        avgFinalScore: 0,
        bestPattern: null
      }
    }

    const avgIterations = this.patterns.reduce((sum, p) => sum + p.convergedIn, 0) / this.patterns.length
    const avgScore = this.patterns.reduce((sum, p) => sum + p.finalScore, 0) / this.patterns.length
    const bestPattern = this.patterns.reduce((best, p) =>
      p.finalScore > best.finalScore ? p : best
    )

    return {
      totalPatterns: this.patterns.length,
      avgConvergenceIterations: parseFloat(avgIterations.toFixed(1)),
      avgFinalScore: parseFloat(avgScore.toFixed(1)),
      bestPattern: {
        id: bestPattern.id,
        name: bestPattern.name,
        score: bestPattern.finalScore,
        iterations: bestPattern.convergedIn
      }
    }
  }

  /**
   * Generate unique ID
   */
  generateId() {
    return `pattern_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
  }

  /**
   * Export pattern for sharing
   */
  exportPattern(patternId) {
    const pattern = this.getPattern(patternId)
    if (!pattern) return null

    return {
      ...pattern,
      exportedAt: new Date().toISOString(),
      exportVersion: '1.0'
    }
  }

  /**
   * Import pattern from export
   */
  async importPattern(exportedPattern) {
    // Remove export metadata
    const { exportedAt, exportVersion, ...pattern } = exportedPattern

    // Assign new ID to avoid conflicts
    pattern.id = this.generateId()
    pattern.importedAt = new Date().toISOString()

    this.patterns.push(pattern)
    await this.save()

    return pattern.id
  }
}

/**
 * Create signature from analysis data
 */
export function createSignature(analysisData) {
  const signature = {}

  // Extract key characteristics
  if (analysisData.bolts) {
    signature.boltCount = analysisData.bolts.count
    signature.avgBoltLength = analysisData.bolts.avgLength
    signature.avgBoltThickness = analysisData.bolts.avgThickness
  }

  if (analysisData.glowRegions) {
    signature.innerGlowRadius = analysisData.glowRegions.inner?.radius
    signature.outerGlowRadius = analysisData.glowRegions.outer?.radius
  }

  if (analysisData.color) {
    signature.dominantHue = analysisData.color.avgHue
    signature.avgSaturation = analysisData.color.avgSaturation
    signature.avgLuminance = analysisData.color.avgLuminance
  }

  if (analysisData.motion) {
    signature.beatFrequency = analysisData.motion.beatFrequency
    signature.rhythmRegularity = analysisData.motion.rhythmRegularity
  }

  return signature
}

/**
 * Example usage helper
 */
export async function saveSuccessfulIteration(libraryPath, iterationData) {
  const library = new PatternLibrary(libraryPath)
  await library.load()

  const patternId = await library.addPattern({
    name: iterationData.name || 'Electricity Animation',
    type: 'electricity',
    signature: createSignature(iterationData.analysis),
    optimalParams: iterationData.finalParams,
    colorPalette: iterationData.colorPalette || [],
    convergedIn: iterationData.iterations,
    finalScore: iterationData.finalScore,
    projectSource: iterationData.projectName || 'unknown',
    semantics: iterationData.semantics || {}
  })

  console.log(`Pattern saved with ID: ${patternId}`)
  return patternId
}

export default PatternLibrary
