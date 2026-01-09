#!/usr/bin/env node
/**
 * Motion Fingerprinting v1.0
 *
 * Analyzes motion quality and temporal characteristics of animation sequences:
 * - Flicker frequency (dominant beat)
 * - Rhythm regularity (consistency of changes)
 * - Turbulence (smooth vs chaotic motion)
 * - Persistence time (how long patterns last)
 * - Motion similarity to reference
 *
 * Usage:
 *   import { analyzeMotion, compareMotion } from './motion-fingerprint.mjs'
 */

import { PNG } from 'pngjs'
import { createReadStream } from 'fs'

// Load PNG
async function loadPNG(filepath) {
  return new Promise((resolve, reject) => {
    const stream = createReadStream(filepath)
    const png = new PNG()
    stream.pipe(png)
      .on('parsed', () => resolve(png))
      .on('error', reject)
  })
}

// Get average brightness of an image
function getAverageBrightness(png) {
  const { width, height, data } = png
  let sum = 0
  let count = 0

  for (let i = 0; i < data.length; i += 4) {
    const brightness = 0.299 * data[i] + 0.587 * data[i + 1] + 0.114 * data[i + 2]
    sum += brightness
    count++
  }

  return sum / count
}

// Get brightness variance (how spread out brightness values are)
function getBrightnessVariance(png) {
  const { data } = png
  const values = []

  for (let i = 0; i < data.length; i += 4) {
    const brightness = 0.299 * data[i] + 0.587 * data[i + 1] + 0.114 * data[i + 2]
    values.push(brightness)
  }

  const mean = values.reduce((a, b) => a + b, 0) / values.length
  const variance = values.reduce((sum, val) => sum + (val - mean) ** 2, 0) / values.length

  return { mean, variance, stdDev: Math.sqrt(variance) }
}

// Compute frame-to-frame differences
function computeFrameDifferences(brightnessSequence) {
  const differences = []
  for (let i = 1; i < brightnessSequence.length; i++) {
    differences.push(Math.abs(brightnessSequence[i] - brightnessSequence[i - 1]))
  }
  return differences
}

// Find dominant frequency using simple peak detection
function findDominantFrequency(signal, frameRate = 20) {
  if (signal.length < 4) return 0

  // Count zero crossings (sign changes in differences)
  const diffs = []
  for (let i = 1; i < signal.length; i++) {
    diffs.push(signal[i] - signal[i - 1])
  }

  let crossings = 0
  for (let i = 1; i < diffs.length; i++) {
    if ((diffs[i] > 0 && diffs[i - 1] < 0) || (diffs[i] < 0 && diffs[i - 1] > 0)) {
      crossings++
    }
  }

  // Frequency = crossings per second
  const duration = signal.length / frameRate
  const frequency = crossings / (2 * duration) // Divide by 2 for full cycles

  return frequency
}

// Calculate rhythm regularity (how consistent is the beat)
function calculateRhythmRegularity(brightnessSequence) {
  const diffs = computeFrameDifferences(brightnessSequence)

  if (diffs.length < 2) return 0

  // Calculate coefficient of variation (lower = more regular)
  const mean = diffs.reduce((a, b) => a + b, 0) / diffs.length
  const variance = diffs.reduce((sum, val) => sum + (val - mean) ** 2, 0) / diffs.length
  const stdDev = Math.sqrt(variance)

  // Convert to regularity score (0-1, higher = more regular)
  const cv = mean > 0 ? stdDev / mean : 0
  const regularity = Math.max(0, 1 - Math.min(cv, 1))

  return regularity
}

// Calculate turbulence (how chaotic is the motion)
function calculateTurbulence(brightnessSequence) {
  if (brightnessSequence.length < 3) return 0

  // Measure second derivative (acceleration of change)
  const firstDiff = computeFrameDifferences(brightnessSequence)
  const secondDiff = computeFrameDifferences(firstDiff)

  // High turbulence = high second derivative variance
  const mean = secondDiff.reduce((a, b) => a + b, 0) / secondDiff.length
  const variance = secondDiff.reduce((sum, val) => sum + (val - mean) ** 2, 0) / secondDiff.length

  // Normalize to 0-1 range (assume max turbulence around variance of 100)
  const turbulence = Math.min(variance / 100, 1)

  return turbulence
}

// Calculate persistence time (autocorrelation)
function calculatePersistence(brightnessSequence) {
  if (brightnessSequence.length < 5) return 0

  // Simple autocorrelation at lag=1
  let correlation = 0
  for (let i = 1; i < brightnessSequence.length; i++) {
    correlation += brightnessSequence[i] * brightnessSequence[i - 1]
  }

  const norm = brightnessSequence.reduce((sum, val) => sum + val ** 2, 0)
  if (norm === 0) return 0

  // Normalize
  correlation = correlation / norm

  // Convert to persistence time in frames (higher correlation = longer persistence)
  const persistenceFrames = correlation * 10 // Scale factor

  return Math.max(0, persistenceFrames)
}

/**
 * Analyze motion characteristics of a frame sequence
 */
export async function analyzeMotion(framePaths, frameRate = 20) {
  // Load all frames
  const frames = []
  for (const framePath of framePaths) {
    try {
      const png = await loadPNG(framePath)
      frames.push(png)
    } catch (err) {
      console.warn(`Failed to load frame ${framePath}: ${err.message}`)
    }
  }

  if (frames.length < 3) {
    return { error: 'Need at least 3 frames for motion analysis' }
  }

  // Extract brightness sequence
  const brightnessSequence = frames.map(f => getAverageBrightness(f))

  // Calculate all motion metrics
  const beatFrequency = findDominantFrequency(brightnessSequence, frameRate)
  const rhythmRegularity = calculateRhythmRegularity(brightnessSequence)
  const turbulence = calculateTurbulence(brightnessSequence)
  const persistence = calculatePersistence(brightnessSequence)

  // Frame-to-frame variance statistics
  const frameDiffs = computeFrameDifferences(brightnessSequence)
  const avgFrameDiff = frameDiffs.reduce((a, b) => a + b, 0) / frameDiffs.length
  const maxFrameDiff = Math.max(...frameDiffs)

  // Overall variance stats
  const overallVariance = getBrightnessVariance(frames[0]) // Use first frame as sample

  return {
    frameCount: frames.length,
    frameRate,

    // Motion characteristics
    beatFrequency: parseFloat(beatFrequency.toFixed(2)),
    rhythmRegularity: parseFloat(rhythmRegularity.toFixed(3)),
    turbulence: parseFloat(turbulence.toFixed(3)),
    persistence: parseFloat(persistence.toFixed(2)),

    // Frame-to-frame stats
    avgFrameDiff: parseFloat(avgFrameDiff.toFixed(2)),
    maxFrameDiff: parseFloat(maxFrameDiff.toFixed(2)),

    // Brightness sequence for advanced analysis
    brightnessSequence,

    // Classification
    motionQuality: classifyMotionQuality(rhythmRegularity, turbulence),

    timestamp: new Date().toISOString()
  }
}

/**
 * Classify motion quality based on metrics
 */
function classifyMotionQuality(regularity, turbulence) {
  if (regularity > 0.7 && turbulence < 0.3) {
    return 'SMOOTH_REGULAR'
  } else if (regularity > 0.5 && turbulence < 0.5) {
    return 'GOOD'
  } else if (turbulence > 0.7) {
    return 'TOO_CHAOTIC'
  } else if (regularity < 0.3) {
    return 'TOO_IRREGULAR'
  } else {
    return 'ACCEPTABLE'
  }
}

/**
 * Compare motion between reference and live
 */
export function compareMotion(refMotion, liveMotion) {
  if (!refMotion || !liveMotion) {
    return { error: 'Both reference and live motion data required' }
  }

  const freqDiff = ((liveMotion.beatFrequency - refMotion.beatFrequency) / refMotion.beatFrequency) * 100
  const regularityDiff = ((liveMotion.rhythmRegularity - refMotion.rhythmRegularity) / refMotion.rhythmRegularity) * 100
  const turbulenceDiff = ((liveMotion.turbulence - refMotion.turbulence) / (refMotion.turbulence || 0.01)) * 100

  // Calculate overall motion similarity (0-100)
  let similarity = 100

  // Penalize frequency mismatch
  similarity -= Math.abs(freqDiff) * 0.5

  // Penalize rhythm mismatch
  similarity -= Math.abs(regularityDiff) * 0.3

  // Penalize turbulence mismatch
  similarity -= Math.abs(turbulenceDiff) * 0.2

  similarity = Math.max(0, Math.min(100, similarity))

  return {
    beatFrequency: {
      reference: refMotion.beatFrequency,
      live: liveMotion.beatFrequency,
      differencePercent: parseFloat(freqDiff.toFixed(1)),
      assessment: Math.abs(freqDiff) < 15 ? 'GOOD' : Math.abs(freqDiff) < 30 ? 'ACCEPTABLE' : 'NEEDS_ADJUSTMENT'
    },

    rhythmRegularity: {
      reference: refMotion.rhythmRegularity,
      live: liveMotion.rhythmRegularity,
      differencePercent: parseFloat(regularityDiff.toFixed(1)),
      assessment: Math.abs(regularityDiff) < 20 ? 'GOOD' : 'NEEDS_ADJUSTMENT'
    },

    turbulence: {
      reference: refMotion.turbulence,
      live: liveMotion.turbulence,
      differencePercent: parseFloat(turbulenceDiff.toFixed(1)),
      assessment: Math.abs(turbulenceDiff) < 25 ? 'GOOD' : 'NEEDS_ADJUSTMENT'
    },

    motionSimilarity: parseFloat(similarity.toFixed(1)),

    overallAssessment: similarity >= 85 ? 'EXCELLENT' : similarity >= 70 ? 'GOOD' : similarity >= 50 ? 'ACCEPTABLE' : 'POOR',

    recommendations: generateMotionRecommendations(freqDiff, regularityDiff, turbulenceDiff, refMotion, liveMotion)
  }
}

/**
 * Generate actionable recommendations
 */
function generateMotionRecommendations(freqDiff, regularityDiff, turbulenceDiff, refMotion, liveMotion) {
  const recommendations = []

  if (Math.abs(freqDiff) > 15) {
    recommendations.push({
      priority: 'HIGH',
      issue: `Flicker rate is ${freqDiff > 0 ? 'too fast' : 'too slow'} by ${Math.abs(freqDiff).toFixed(1)}%`,
      action: `${freqDiff > 0 ? 'Decrease' : 'Increase'} animation frequency/timing parameters`
    })
  }

  if (Math.abs(regularityDiff) > 20) {
    if (liveMotion.rhythmRegularity < refMotion.rhythmRegularity) {
      recommendations.push({
        priority: 'MEDIUM',
        issue: 'Motion is too irregular compared to reference',
        action: 'Stabilize timing parameters to create more consistent rhythm'
      })
    } else {
      recommendations.push({
        priority: 'LOW',
        issue: 'Motion is too regular (less variation than reference)',
        action: 'Add slight randomness to timing parameters'
      })
    }
  }

  if (Math.abs(turbulenceDiff) > 25) {
    if (liveMotion.turbulence > refMotion.turbulence) {
      recommendations.push({
        priority: 'HIGH',
        issue: 'Motion is too chaotic/jittery',
        action: 'Smooth animation transitions, reduce rapid changes'
      })
    } else {
      recommendations.push({
        priority: 'MEDIUM',
        issue: 'Motion is too smooth (less dynamic than reference)',
        action: 'Increase variation in animation parameters'
      })
    }
  }

  if (recommendations.length === 0) {
    recommendations.push({
      priority: 'INFO',
      issue: 'Motion characteristics are well-matched',
      action: 'No motion adjustments needed'
    })
  }

  return recommendations
}

export default {
  analyzeMotion,
  compareMotion
}
