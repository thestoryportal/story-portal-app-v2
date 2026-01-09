#!/usr/bin/env node
/**
 * Hierarchical Diff Analysis v1.0
 *
 * Multi-resolution coarse-to-fine analysis that prioritizes major issues
 * before addressing minor details. Prevents premature optimization.
 *
 * Analysis Levels:
 * 1. MACRO: Entire frame (missing elements, overall brightness, color palette)
 * 2. REGIONAL: Quadrants/zones (spatial distribution, balance)
 * 3. FEATURE: Individual elements (bolt lengths, glow radii)
 * 4. PIXEL: Fine details (anti-aliasing, color banding)
 *
 * Usage:
 *   import { analyzeHierarchical, getRecommendedPhase } from './hierarchical-diff-analysis.mjs'
 */

import { PNG } from 'pngjs'
import { createReadStream } from 'fs'

/**
 * Analysis severity levels
 */
const SEVERITY = {
  CRITICAL: 'critical',    // Score impact: 20-40 points
  HIGH: 'high',           // Score impact: 10-20 points
  MEDIUM: 'medium',       // Score impact: 5-10 points
  LOW: 'low'              // Score impact: <5 points
}

/**
 * Load PNG image
 */
async function loadPNG(filepath) {
  return new Promise((resolve, reject) => {
    const stream = createReadStream(filepath)
    const png = new PNG()
    stream.pipe(png)
      .on('parsed', () => resolve(png))
      .on('error', reject)
  })
}

/**
 * Get pixel at coordinates
 */
function getPixel(png, x, y) {
  const idx = (png.width * y + x) << 2
  return {
    r: png.data[idx],
    g: png.data[idx + 1],
    b: png.data[idx + 2],
    a: png.data[idx + 3]
  }
}

/**
 * Calculate brightness of pixel
 */
function getBrightness(pixel) {
  return (pixel.r + pixel.g + pixel.b) / 3
}

/**
 * Level 1: MACRO Analysis - Entire Frame
 */
function analyzeMacro(refImage, liveImage) {
  const { width, height } = refImage
  const totalPixels = width * height
  const issues = []

  let refTotalBrightness = 0
  let liveTotalBrightness = 0
  let refColorSum = { r: 0, g: 0, b: 0 }
  let liveColorSum = { r: 0, g: 0, b: 0 }
  let refActivePixels = 0
  let liveActivePixels = 0

  // Sample every 5th pixel for speed
  for (let y = 0; y < height; y += 5) {
    for (let x = 0; x < width; x += 5) {
      const refPixel = getPixel(refImage, x, y)
      const livePixel = getPixel(liveImage, x, y)

      const refBright = getBrightness(refPixel)
      const liveBright = getBrightness(livePixel)

      refTotalBrightness += refBright
      liveTotalBrightness += liveBright

      // Count "active" pixels (bright enough to be part of animation)
      if (refBright > 30) {
        refActivePixels++
        refColorSum.r += refPixel.r
        refColorSum.g += refPixel.g
        refColorSum.b += refPixel.b
      }

      if (liveBright > 30) {
        liveActivePixels++
        liveColorSum.r += livePixel.r
        liveColorSum.g += livePixel.g
        liveColorSum.b += livePixel.b
      }
    }
  }

  const sampledPixels = (width / 5) * (height / 5)

  // Overall brightness comparison
  const avgRefBrightness = refTotalBrightness / sampledPixels
  const avgLiveBrightness = liveTotalBrightness / sampledPixels
  const brightnessDiff = ((avgLiveBrightness - avgRefBrightness) / avgRefBrightness) * 100

  if (Math.abs(brightnessDiff) > 15) {
    issues.push({
      level: 'macro',
      severity: Math.abs(brightnessDiff) > 30 ? SEVERITY.CRITICAL : SEVERITY.HIGH,
      issue: `Overall brightness is ${brightnessDiff > 0 ? 'too high' : 'too low'} by ${Math.abs(brightnessDiff).toFixed(1)}%`,
      recommendation: `Adjust global opacity/brightness by ${(-brightnessDiff).toFixed(0)}%`,
      estimatedImpact: Math.min(Math.abs(brightnessDiff) / 2, 20)
    })
  }

  // Active pixel count (missing/extra elements)
  const activePixelDiff = ((liveActivePixels - refActivePixels) / refActivePixels) * 100

  if (Math.abs(activePixelDiff) > 20) {
    const severity = Math.abs(activePixelDiff) > 40 ? SEVERITY.CRITICAL : SEVERITY.HIGH
    issues.push({
      level: 'macro',
      severity,
      issue: activePixelDiff > 0
        ? `Too many bright pixels (+${activePixelDiff.toFixed(0)}%) - extra elements or glow too large`
        : `Too few bright pixels (${activePixelDiff.toFixed(0)}%) - missing elements or glow too small`,
      recommendation: activePixelDiff > 0
        ? 'Reduce glow radius or remove extra elements'
        : 'Increase glow radius or add missing elements',
      estimatedImpact: Math.min(Math.abs(activePixelDiff) / 3, 25)
    })
  }

  // Color palette comparison
  if (refActivePixels > 0 && liveActivePixels > 0) {
    const avgRefColor = {
      r: refColorSum.r / refActivePixels,
      g: refColorSum.g / refActivePixels,
      b: refColorSum.b / refActivePixels
    }
    const avgLiveColor = {
      r: liveColorSum.r / liveActivePixels,
      g: liveColorSum.g / liveActivePixels,
      b: liveColorSum.b / liveActivePixels
    }

    const colorDiff = Math.sqrt(
      Math.pow(avgRefColor.r - avgLiveColor.r, 2) +
      Math.pow(avgRefColor.g - avgLiveColor.g, 2) +
      Math.pow(avgRefColor.b - avgLiveColor.b, 2)
    )

    if (colorDiff > 30) {
      issues.push({
        level: 'macro',
        severity: colorDiff > 60 ? SEVERITY.HIGH : SEVERITY.MEDIUM,
        issue: `Color palette mismatch (Δ=${colorDiff.toFixed(0)})`,
        recommendation: `Adjust hue/saturation - Ref: rgb(${Math.round(avgRefColor.r)},${Math.round(avgRefColor.g)},${Math.round(avgRefColor.b)}), Live: rgb(${Math.round(avgLiveColor.r)},${Math.round(avgLiveColor.g)},${Math.round(avgLiveColor.b)})`,
        estimatedImpact: Math.min(colorDiff / 5, 15)
      })
    }
  }

  return {
    level: 'MACRO',
    issues,
    metrics: {
      avgRefBrightness,
      avgLiveBrightness,
      brightnessDiff,
      refActivePixels,
      liveActivePixels,
      activePixelDiff
    }
  }
}

/**
 * Level 2: REGIONAL Analysis - Quadrants/Zones
 */
function analyzeRegional(refImage, liveImage) {
  const { width, height } = refImage
  const centerX = width / 2
  const centerY = height / 2
  const issues = []

  // Define radial zones
  const zones = [
    { name: 'core', minRadius: 0, maxRadius: 40, priority: 1 },
    { name: 'inner', minRadius: 40, maxRadius: 100, priority: 2 },
    { name: 'middle', minRadius: 100, maxRadius: 160, priority: 3 },
    { name: 'outer', minRadius: 160, maxRadius: 230, priority: 4 }
  ]

  for (const zone of zones) {
    let refZoneBrightness = 0
    let liveZoneBrightness = 0
    let zonePixels = 0

    // Sample pixels in this zone
    for (let y = 0; y < height; y += 3) {
      for (let x = 0; x < width; x += 3) {
        const dx = x - centerX
        const dy = y - centerY
        const radius = Math.sqrt(dx * dx + dy * dy)

        if (radius >= zone.minRadius && radius < zone.maxRadius) {
          const refPixel = getPixel(refImage, x, y)
          const livePixel = getPixel(liveImage, x, y)

          refZoneBrightness += getBrightness(refPixel)
          liveZoneBrightness += getBrightness(livePixel)
          zonePixels++
        }
      }
    }

    if (zonePixels === 0) continue

    const avgRefZoneBright = refZoneBrightness / zonePixels
    const avgLiveZoneBright = liveZoneBrightness / zonePixels
    const zoneDiff = ((avgLiveZoneBright - avgRefZoneBright) / Math.max(avgRefZoneBright, 1)) * 100

    if (Math.abs(zoneDiff) > 20) {
      const severity = zone.priority <= 2 ? SEVERITY.HIGH : SEVERITY.MEDIUM
      issues.push({
        level: 'regional',
        zone: zone.name,
        severity,
        issue: `${zone.name.toUpperCase()} zone is ${zoneDiff > 0 ? 'too bright' : 'too dim'} by ${Math.abs(zoneDiff).toFixed(0)}%`,
        recommendation: `Adjust ${zone.name} zone brightness/opacity`,
        estimatedImpact: Math.min(Math.abs(zoneDiff) / 4, 12)
      })
    }
  }

  // Check quadrants for balance
  const quadrants = [
    { name: 'upper-left', x: 0, y: 0, w: width/2, h: height/2 },
    { name: 'upper-right', x: width/2, y: 0, w: width/2, h: height/2 },
    { name: 'lower-left', x: 0, y: height/2, w: width/2, h: height/2 },
    { name: 'lower-right', x: width/2, y: height/2, w: width/2, h: height/2 }
  ]

  const quadrantBrightness = { ref: [], live: [] }

  for (const quad of quadrants) {
    let refQuadBright = 0
    let liveQuadBright = 0
    let quadPixels = 0

    for (let y = quad.y; y < quad.y + quad.h; y += 5) {
      for (let x = quad.x; x < quad.x + quad.w; x += 5) {
        const refPixel = getPixel(refImage, x, y)
        const livePixel = getPixel(liveImage, x, y)

        refQuadBright += getBrightness(refPixel)
        liveQuadBright += getBrightness(livePixel)
        quadPixels++
      }
    }

    quadrantBrightness.ref.push(refQuadBright / quadPixels)
    quadrantBrightness.live.push(liveQuadBright / quadPixels)
  }

  // Check for imbalance (one quadrant much darker/brighter than others)
  const refVariance = calculateVariance(quadrantBrightness.ref)
  const liveVariance = calculateVariance(quadrantBrightness.live)

  if (liveVariance > refVariance * 1.5) {
    issues.push({
      level: 'regional',
      severity: SEVERITY.MEDIUM,
      issue: `Unbalanced spatial distribution - some quadrants significantly brighter/dimmer than others`,
      recommendation: `Improve element distribution for better balance`,
      estimatedImpact: 8
    })
  }

  return {
    level: 'REGIONAL',
    issues,
    zones: zones.map((z, i) => ({ name: z.name, analysis: 'completed' }))
  }
}

/**
 * Level 3: FEATURE Analysis - Individual Elements
 */
function analyzeFeature(semanticAnalysis) {
  const issues = []

  if (!semanticAnalysis) {
    return { level: 'FEATURE', issues, note: 'Semantic analysis not available' }
  }

  const { comparison } = semanticAnalysis

  // Bolt count issues
  if (comparison?.bolts?.countDifference) {
    const diff = comparison.bolts.countDifference
    issues.push({
      level: 'feature',
      element: 'bolts',
      severity: Math.abs(diff) >= 4 ? SEVERITY.HIGH : SEVERITY.MEDIUM,
      issue: `Bolt count: ${Math.abs(diff)} bolt${Math.abs(diff) > 1 ? 's' : ''} ${diff > 0 ? 'missing' : 'extra'}`,
      recommendation: `${diff > 0 ? 'Add' : 'Remove'} ${Math.abs(diff)} bolts`,
      estimatedImpact: Math.abs(diff) * 2
    })
  }

  // Bolt length issues
  if (comparison?.bolts?.avgLengthDifferencePercent) {
    const pct = parseFloat(comparison.bolts.avgLengthDifferencePercent)
    if (Math.abs(pct) > 10) {
      issues.push({
        level: 'feature',
        element: 'bolts',
        severity: Math.abs(pct) > 25 ? SEVERITY.HIGH : SEVERITY.MEDIUM,
        issue: `Bolt length: ${Math.abs(pct).toFixed(0)}% ${pct > 0 ? 'too short' : 'too long'}`,
        recommendation: `Adjust boltLength by ${pct > 0 ? '+' : ''}${pct.toFixed(0)}%`,
        estimatedImpact: Math.abs(pct) / 3
      })
    }
  }

  // Glow region issues
  if (comparison?.glowRegions) {
    const glowDiff = comparison.glowRegions.avgRadiusDifferencePercent
    if (glowDiff && Math.abs(parseFloat(glowDiff)) > 15) {
      const pct = parseFloat(glowDiff)
      issues.push({
        level: 'feature',
        element: 'glow',
        severity: SEVERITY.MEDIUM,
        issue: `Glow radius: ${Math.abs(pct).toFixed(0)}% ${pct > 0 ? 'too small' : 'too large'}`,
        recommendation: `Adjust glowRadius by ${pct > 0 ? '+' : ''}${pct.toFixed(0)}%`,
        estimatedImpact: Math.abs(pct) / 4
      })
    }
  }

  return {
    level: 'FEATURE',
    issues
  }
}

/**
 * Level 4: PIXEL Analysis - Fine Details
 */
function analyzePixel(refImage, liveImage, macroScore) {
  const issues = []

  // Only do pixel-level analysis if macro and regional are good (>85%)
  if (macroScore < 85) {
    return {
      level: 'PIXEL',
      issues: [],
      note: 'Pixel-level analysis skipped - fix macro/regional issues first'
    }
  }

  // Sample for anti-aliasing quality
  const { width, height } = refImage
  let edgePixels = 0
  let edgeDifferences = 0

  // Look for edges (brightness gradient > threshold)
  for (let y = 1; y < height - 1; y += 4) {
    for (let x = 1; x < width - 1; x += 4) {
      const centerRef = getBrightness(getPixel(refImage, x, y))
      const centerLive = getBrightness(getPixel(liveImage, x, y))

      if (centerRef > 50) { // Only on bright regions
        const rightRef = getBrightness(getPixel(refImage, x + 1, y))
        const gradient = Math.abs(centerRef - rightRef)

        if (gradient > 30) { // This is an edge
          edgePixels++
          const rightLive = getBrightness(getPixel(liveImage, x + 1, y))
          const liveGradient = Math.abs(centerLive - rightLive)

          if (Math.abs(gradient - liveGradient) > 15) {
            edgeDifferences++
          }
        }
      }
    }
  }

  if (edgePixels > 0) {
    const edgeMatchPercent = ((edgePixels - edgeDifferences) / edgePixels) * 100

    if (edgeMatchPercent < 85) {
      issues.push({
        level: 'pixel',
        severity: SEVERITY.LOW,
        issue: `Edge quality mismatch: ${edgeMatchPercent.toFixed(0)}% of edges match`,
        recommendation: `Fine-tune anti-aliasing, edge sharpness, or line thickness`,
        estimatedImpact: (100 - edgeMatchPercent) / 10
      })
    }
  }

  return {
    level: 'PIXEL',
    issues
  }
}

/**
 * Main hierarchical analysis function
 */
export async function analyzeHierarchical(refImagePath, liveImagePath, options = {}) {
  const {
    semanticAnalysis = null,
    currentScore = 0
  } = options

  // Load images
  const refImage = await loadPNG(refImagePath)
  const liveImage = await loadPNG(liveImagePath)

  // Run all analysis levels
  const macroResults = analyzeMacro(refImage, liveImage)
  const regionalResults = analyzeRegional(refImage, liveImage)
  const featureResults = analyzeFeature(semanticAnalysis)
  const pixelResults = analyzePixel(refImage, liveImage, currentScore)

  // Aggregate all issues
  const allIssues = [
    ...macroResults.issues,
    ...regionalResults.issues,
    ...featureResults.issues,
    ...pixelResults.issues
  ]

  // Sort by severity and estimated impact
  const severityOrder = { critical: 4, high: 3, medium: 2, low: 1 }
  allIssues.sort((a, b) => {
    const severityDiff = severityOrder[b.severity] - severityOrder[a.severity]
    if (severityDiff !== 0) return severityDiff
    return (b.estimatedImpact || 0) - (a.estimatedImpact || 0)
  })

  // Determine recommended focus level
  const criticalCount = allIssues.filter(i => i.severity === SEVERITY.CRITICAL).length
  const highCount = allIssues.filter(i => i.severity === SEVERITY.HIGH).length

  let recommendedLevel = 'FEATURE'
  if (criticalCount > 0 || highCount >= 2) {
    recommendedLevel = 'MACRO'
  } else if (highCount > 0 || allIssues.filter(i => i.level === 'regional').length > 0) {
    recommendedLevel = 'REGIONAL'
  } else if (currentScore >= 85) {
    recommendedLevel = 'PIXEL'
  }

  return {
    timestamp: new Date().toISOString(),
    levels: {
      macro: macroResults,
      regional: regionalResults,
      feature: featureResults,
      pixel: pixelResults
    },
    allIssues,
    summary: {
      totalIssues: allIssues.length,
      bySeverity: {
        critical: criticalCount,
        high: highCount,
        medium: allIssues.filter(i => i.severity === SEVERITY.MEDIUM).length,
        low: allIssues.filter(i => i.severity === SEVERITY.LOW).length
      },
      estimatedTotalImpact: allIssues.reduce((sum, i) => sum + (i.estimatedImpact || 0), 0)
    },
    recommendation: {
      focusLevel: recommendedLevel,
      priority: allIssues.slice(0, 3), // Top 3 issues
      guidance: getGuidanceForLevel(recommendedLevel)
    }
  }
}

/**
 * Get recommended phase based on score and iteration
 */
export function getRecommendedPhase(currentScore, iterationNumber) {
  if (currentScore < 75 || iterationNumber <= 2) {
    return {
      phase: 'STRUCTURAL',
      focus: 'Fix macro and regional issues - element count, distribution, overall brightness',
      levels: ['MACRO', 'REGIONAL'],
      ignoreForNow: ['Pixel-level details', 'Anti-aliasing', 'Minor color shifts']
    }
  } else if (currentScore < 88 || iterationNumber <= 4) {
    return {
      phase: 'REFINEMENT',
      focus: 'Fix feature-level issues - individual element properties',
      levels: ['REGIONAL', 'FEATURE'],
      ignoreForNow: ['Edge quality', 'Micro color variations']
    }
  } else {
    return {
      phase: 'POLISH',
      focus: 'Fix pixel-level details - fine-tune for perfection',
      levels: ['FEATURE', 'PIXEL'],
      ignoreForNow: []
    }
  }
}

/**
 * Helper: Calculate variance
 */
function calculateVariance(values) {
  const mean = values.reduce((sum, v) => sum + v, 0) / values.length
  const squaredDiffs = values.map(v => Math.pow(v - mean, 2))
  return squaredDiffs.reduce((sum, v) => sum + v, 0) / values.length
}

/**
 * Helper: Get guidance for level
 */
function getGuidanceForLevel(level) {
  const guidance = {
    MACRO: 'Focus on big-picture issues: Are major elements missing? Is overall brightness correct? Fix structural problems before details.',
    REGIONAL: 'Focus on spatial distribution: Is brightness balanced across zones? Are elements evenly distributed? Fix regional issues before individual elements.',
    FEATURE: 'Focus on individual elements: Are bolt lengths correct? Are glow radii appropriate? Fine-tune element properties.',
    PIXEL: 'Focus on fine details: Edge quality, anti-aliasing, color precision. Polish for perfection.'
  }
  return guidance[level] || guidance.FEATURE
}

export default {
  analyzeHierarchical,
  getRecommendedPhase,
  SEVERITY
}
