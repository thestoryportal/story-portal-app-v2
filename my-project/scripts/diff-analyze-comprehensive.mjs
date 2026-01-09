#!/usr/bin/env node
/**
 * Comprehensive Diff Analysis Agent v2.3
 *
 * Multi-metric analysis for animation frame comparison.
 * Provides granular feedback for animator iteration.
 * Includes single-frame best/worst analysis and sequence/animation temporal analysis.
 *
 * v2.3 IMPROVEMENT: Enhanced luminance guidance. Large luminance differences (>15%)
 * are now flagged as HIGH PRIORITY with specific direction (TOO DARK/TOO BRIGHT)
 * and actual luminance values. Recommendations now use averaged color diffs across
 * all frames instead of just the first frame.
 *
 * v2.2 FIX: Color analysis was including ALL pixels (including black background),
 * which skewed avgHue toward red (hue 0°) and reduced saturation/luminance.
 * This caused conflicting guidance vs baseline spec (which skips black pixels).
 * Fixed to skip near-black pixels (brightness < 30) and use circular mask.
 *
 * v2.1 FIX: maskedSimilarity calculation was broken - it checked pixelmatch's
 * diff output for non-zero pixels, but pixelmatch doesn't output black for
 * matching pixels. This caused maskedSimilarity (and overallScore) to always
 * be 0. Fixed to compare source images directly within the mask.
 *
 * Metrics:
 * - Pixelmatch: Exact pixel differences
 * - SSIM: Structural Similarity Index (perceptual quality)
 * - Heat Map: Visual concentration of differences
 * - Regional Analysis: Per-quadrant breakdown
 * - Color Analysis: Hue/saturation/luminance comparison
 * - Edge Analysis: Structural edge comparison
 *
 * NEW in v2.0:
 * - Single Frame Analysis: Best/worst frame identification with detailed metrics
 * - Sequence Analysis: Temporal consistency, smoothness, trend detection, outlier frames
 *
 * Usage:
 *   node scripts/diff-analyze-comprehensive.mjs [options]
 */

import fs from 'fs/promises'
import path from 'path'
import { PNG } from 'pngjs'
import pixelmatch from 'pixelmatch'
import { createReadStream } from 'fs'
import { fileURLToPath } from 'url'

const __dirname = path.dirname(fileURLToPath(import.meta.url))

// Parse arguments
function parseArgs() {
  const args = process.argv.slice(2)
  const options = {
    live: './capture-output/live',
    reference: './capture-output/reference',
    output: './diff-output',
    threshold: 0.1,
    target: 95,
    regions: 4, // 4x4 grid for regional analysis
  }

  for (const arg of args) {
    if (arg.startsWith('--live=')) options.live = arg.split('=')[1]
    else if (arg.startsWith('--reference=')) options.reference = arg.split('=')[1]
    else if (arg.startsWith('--output=')) options.output = arg.split('=')[1]
    else if (arg.startsWith('--threshold=')) options.threshold = parseFloat(arg.split('=')[1])
    else if (arg.startsWith('--target=')) options.target = parseFloat(arg.split('=')[1])
  }

  return options
}

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

// Save PNG
async function savePNG(png, filepath) {
  const buffer = PNG.sync.write(png)
  await fs.writeFile(filepath, buffer)
}

// RGB to HSL conversion
function rgbToHsl(r, g, b) {
  r /= 255; g /= 255; b /= 255
  const max = Math.max(r, g, b), min = Math.min(r, g, b)
  let h, s, l = (max + min) / 2

  if (max === min) {
    h = s = 0
  } else {
    const d = max - min
    s = l > 0.5 ? d / (2 - max - min) : d / (max + min)
    switch (max) {
      case r: h = ((g - b) / d + (g < b ? 6 : 0)) / 6; break
      case g: h = ((b - r) / d + 2) / 6; break
      case b: h = ((r - g) / d + 4) / 6; break
    }
  }
  return { h: h * 360, s: s * 100, l: l * 100 }
}

// Calculate luminance
function getLuminance(r, g, b) {
  return 0.299 * r + 0.587 * g + 0.114 * b
}

// Simple SSIM implementation (Structural Similarity Index)
function calculateSSIM(img1, img2, windowSize = 8) {
  const { width, height } = img1
  const L = 255 // dynamic range
  const k1 = 0.01, k2 = 0.03
  const c1 = (k1 * L) ** 2
  const c2 = (k2 * L) ** 2

  let ssimSum = 0
  let windowCount = 0

  // Slide window across image
  for (let wy = 0; wy < height - windowSize; wy += windowSize) {
    for (let wx = 0; wx < width - windowSize; wx += windowSize) {
      let sum1 = 0, sum2 = 0
      let sq1 = 0, sq2 = 0, cross = 0
      let count = 0

      // Calculate means and variances within window
      for (let y = wy; y < wy + windowSize && y < height; y++) {
        for (let x = wx; x < wx + windowSize && x < width; x++) {
          const idx = (y * width + x) * 4
          const l1 = getLuminance(img1.data[idx], img1.data[idx + 1], img1.data[idx + 2])
          const l2 = getLuminance(img2.data[idx], img2.data[idx + 1], img2.data[idx + 2])

          sum1 += l1
          sum2 += l2
          sq1 += l1 * l1
          sq2 += l2 * l2
          cross += l1 * l2
          count++
        }
      }

      if (count === 0) continue

      const mean1 = sum1 / count
      const mean2 = sum2 / count
      const var1 = (sq1 / count) - (mean1 * mean1)
      const var2 = (sq2 / count) - (mean2 * mean2)
      const covar = (cross / count) - (mean1 * mean2)

      const ssim = ((2 * mean1 * mean2 + c1) * (2 * covar + c2)) /
                   ((mean1 ** 2 + mean2 ** 2 + c1) * (var1 + var2 + c2))

      ssimSum += ssim
      windowCount++
    }
  }

  return windowCount > 0 ? ssimSum / windowCount : 0
}

// Generate heat map showing difference intensity
function generateHeatMap(img1, img2) {
  const { width, height } = img1
  const heatMap = new PNG({ width, height })

  for (let y = 0; y < height; y++) {
    for (let x = 0; x < width; x++) {
      const idx = (y * width + x) * 4

      // Calculate difference magnitude
      const dr = Math.abs(img1.data[idx] - img2.data[idx])
      const dg = Math.abs(img1.data[idx + 1] - img2.data[idx + 1])
      const db = Math.abs(img1.data[idx + 2] - img2.data[idx + 2])
      const diff = (dr + dg + db) / 3

      // Map to heat color (blue -> green -> yellow -> red)
      let r, g, b
      if (diff < 64) {
        // Blue to cyan
        r = 0
        g = diff * 4
        b = 255
      } else if (diff < 128) {
        // Cyan to green
        r = 0
        g = 255
        b = 255 - (diff - 64) * 4
      } else if (diff < 192) {
        // Green to yellow
        r = (diff - 128) * 4
        g = 255
        b = 0
      } else {
        // Yellow to red
        r = 255
        g = 255 - (diff - 192) * 4
        b = 0
      }

      heatMap.data[idx] = r
      heatMap.data[idx + 1] = g
      heatMap.data[idx + 2] = b
      heatMap.data[idx + 3] = 255
    }
  }

  return heatMap
}

// Regional analysis - break image into grid
function analyzeRegions(img1, img2, gridSize = 4) {
  const { width, height } = img1
  const regionWidth = Math.floor(width / gridSize)
  const regionHeight = Math.floor(height / gridSize)
  const regions = []

  for (let gy = 0; gy < gridSize; gy++) {
    for (let gx = 0; gx < gridSize; gx++) {
      const startX = gx * regionWidth
      const startY = gy * regionHeight
      const endX = Math.min(startX + regionWidth, width)
      const endY = Math.min(startY + regionHeight, height)

      let totalDiff = 0
      let pixelCount = 0
      let maxDiff = 0

      for (let y = startY; y < endY; y++) {
        for (let x = startX; x < endX; x++) {
          const idx = (y * width + x) * 4
          const dr = Math.abs(img1.data[idx] - img2.data[idx])
          const dg = Math.abs(img1.data[idx + 1] - img2.data[idx + 1])
          const db = Math.abs(img1.data[idx + 2] - img2.data[idx + 2])
          const diff = (dr + dg + db) / 3

          totalDiff += diff
          maxDiff = Math.max(maxDiff, diff)
          pixelCount++
        }
      }

      const avgDiff = totalDiff / pixelCount
      const similarity = 1 - (avgDiff / 255)

      regions.push({
        gridX: gx,
        gridY: gy,
        position: getRegionName(gx, gy, gridSize),
        similarity: similarity * 100,
        avgDiff,
        maxDiff,
        needsAttention: similarity < 0.9,
      })
    }
  }

  return regions
}

// Get human-readable region name
function getRegionName(gx, gy, gridSize) {
  const vPos = gy < gridSize / 2 ? 'top' : 'bottom'
  const hPos = gx < gridSize / 2 ? 'left' : 'right'
  const vMid = gy >= gridSize / 4 && gy < gridSize * 3 / 4 ? 'center' : vPos
  const hMid = gx >= gridSize / 4 && gx < gridSize * 3 / 4 ? 'center' : hPos
  return `${vMid}-${hMid}`
}

// Color distribution analysis
// v2.2 FIX: Now skips black pixels and uses circular mask for consistency with baseline analysis
function analyzeColors(img1, img2) {
  const { width, height } = img1
  const BRIGHTNESS_THRESHOLD = 30 // Skip near-black pixels (matches baseline-analyst-agent.mjs)

  let hueSum1 = 0, hueSum2 = 0
  let satSum1 = 0, satSum2 = 0
  let lumSum1 = 0, lumSum2 = 0
  let count = 0

  // Helper to check if inside the circular effect area
  const isInCircle = (x, y) => {
    const centerX = width / 2
    const centerY = height / 2
    const radius = Math.min(width, height) * 0.34
    const dx = x - centerX
    const dy = y - centerY
    return (dx * dx + dy * dy) <= (radius * radius)
  }

  for (let y = 0; y < height; y++) {
    for (let x = 0; x < width; x++) {
      // Only analyze pixels inside the circular effect area
      if (!isInCircle(x, y)) continue

      const idx = (y * width + x) * 4

      // Calculate brightness for both images
      const brightness1 = img1.data[idx] + img1.data[idx + 1] + img1.data[idx + 2]
      const brightness2 = img2.data[idx] + img2.data[idx + 1] + img2.data[idx + 2]

      // Skip near-black pixels in BOTH images (only compare colored pixels)
      // This matches baseline-analyst-agent.mjs methodology
      if (brightness1 < BRIGHTNESS_THRESHOLD && brightness2 < BRIGHTNESS_THRESHOLD) continue

      const hsl1 = rgbToHsl(img1.data[idx], img1.data[idx + 1], img1.data[idx + 2])
      const hsl2 = rgbToHsl(img2.data[idx], img2.data[idx + 1], img2.data[idx + 2])

      hueSum1 += hsl1.h
      hueSum2 += hsl2.h
      satSum1 += hsl1.s
      satSum2 += hsl2.s
      lumSum1 += hsl1.l
      lumSum2 += hsl2.l
      count++
    }
  }

  // Handle edge case where no colored pixels found
  if (count === 0) {
    return {
      reference: { avgHue: 0, avgSaturation: 0, avgLuminance: 0 },
      live: { avgHue: 0, avgSaturation: 0, avgLuminance: 0 },
      difference: { hueDiff: 0, saturationDiff: 0, luminanceDiff: 0 },
    }
  }

  return {
    reference: {
      avgHue: hueSum1 / count,
      avgSaturation: satSum1 / count,
      avgLuminance: lumSum1 / count,
    },
    live: {
      avgHue: hueSum2 / count,
      avgSaturation: satSum2 / count,
      avgLuminance: lumSum2 / count,
    },
    difference: {
      hueDiff: Math.abs(hueSum1 - hueSum2) / count,
      saturationDiff: Math.abs(satSum1 - satSum2) / count,
      luminanceDiff: Math.abs(lumSum1 - lumSum2) / count,
    },
  }
}

// Simple edge detection (Sobel-like)
function detectEdges(img) {
  const { width, height } = img
  const edges = new Uint8Array(width * height)

  for (let y = 1; y < height - 1; y++) {
    for (let x = 1; x < width - 1; x++) {
      const idx = y * width + x

      // Get luminance of surrounding pixels
      const getL = (ox, oy) => {
        const i = ((y + oy) * width + (x + ox)) * 4
        return getLuminance(img.data[i], img.data[i + 1], img.data[i + 2])
      }

      // Sobel operators
      const gx = -getL(-1, -1) + getL(1, -1) - 2 * getL(-1, 0) + 2 * getL(1, 0) - getL(-1, 1) + getL(1, 1)
      const gy = -getL(-1, -1) - 2 * getL(0, -1) - getL(1, -1) + getL(-1, 1) + 2 * getL(0, 1) + getL(1, 1)

      edges[idx] = Math.min(255, Math.sqrt(gx * gx + gy * gy))
    }
  }

  return edges
}

// Compare edge maps
function compareEdges(img1, img2) {
  const edges1 = detectEdges(img1)
  const edges2 = detectEdges(img2)

  let totalDiff = 0
  let edgePixels = 0

  for (let i = 0; i < edges1.length; i++) {
    if (edges1[i] > 30 || edges2[i] > 30) {
      totalDiff += Math.abs(edges1[i] - edges2[i])
      edgePixels++
    }
  }

  const avgEdgeDiff = edgePixels > 0 ? totalDiff / edgePixels : 0
  return {
    edgeSimilarity: 1 - (avgEdgeDiff / 255),
    edgePixelCount: edgePixels,
  }
}

// Circular mask check
function isInsideCircle(x, y, width, height) {
  const centerX = width / 2
  const centerY = height / 2
  const radius = Math.min(width, height) * 0.34
  const dx = x - centerX
  const dy = y - centerY
  return (dx * dx + dy * dy) <= (radius * radius)
}

// Comprehensive frame analysis
async function analyzeFrame(refPath, livePath, outputDir, frameIndex) {
  const refImg = await loadPNG(refPath)
  const liveImg = await loadPNG(livePath)

  const { width, height } = refImg

  // 1. Pixelmatch analysis
  const diffImg = new PNG({ width, height })
  const pixelDiff = pixelmatch(
    refImg.data, liveImg.data, diffImg.data,
    width, height, { threshold: 0.1 }
  )
  const pixelSimilarity = 1 - (pixelDiff / (width * height))

  // 2. SSIM analysis
  const ssim = calculateSSIM(refImg, liveImg)

  // 3. Generate heat map
  const heatMap = generateHeatMap(refImg, liveImg)

  // 4. Regional analysis
  const regions = analyzeRegions(refImg, liveImg, 4)
  const problemRegions = regions.filter(r => r.needsAttention)

  // 5. Color analysis
  const colorAnalysis = analyzeColors(refImg, liveImg)

  // 6. Edge analysis
  const edgeAnalysis = compareEdges(refImg, liveImg)

  // 7. Masked analysis (inside circle only)
  // FIX: Compare source images directly, not the diff output
  // The old code checked diffImg pixels for non-zero RGB, but pixelmatch
  // doesn't output black for matching pixels, causing maskedSimilarity = 0 always
  let maskedDiffSum = 0, maskedTotal = 0
  const DIFF_THRESHOLD = 25 // Pixel difference threshold (0-255)
  for (let y = 0; y < height; y++) {
    for (let x = 0; x < width; x++) {
      if (isInsideCircle(x, y, width, height)) {
        maskedTotal++
        const idx = (y * width + x) * 4
        // Compare source images directly
        const dr = Math.abs(refImg.data[idx] - liveImg.data[idx])
        const dg = Math.abs(refImg.data[idx + 1] - liveImg.data[idx + 1])
        const db = Math.abs(refImg.data[idx + 2] - liveImg.data[idx + 2])
        const avgDiff = (dr + dg + db) / 3
        // Accumulate normalized difference (0-1 scale)
        maskedDiffSum += avgDiff / 255
      }
    }
  }
  // Calculate similarity as 1 - average normalized difference
  const maskedSimilarity = maskedTotal > 0 ? 1 - (maskedDiffSum / maskedTotal) : 0

  // Save outputs
  const diffPath = path.join(outputDir, `diff_${String(frameIndex).padStart(4, '0')}.png`)
  const heatPath = path.join(outputDir, `heat_${String(frameIndex).padStart(4, '0')}.png`)
  await savePNG(diffImg, diffPath)
  await savePNG(heatMap, heatPath)

  return {
    frameIndex,
    dimensions: { width, height },
    metrics: {
      pixelSimilarity: pixelSimilarity * 100,
      maskedSimilarity: maskedSimilarity * 100,
      ssim: ssim * 100,
      edgeSimilarity: edgeAnalysis.edgeSimilarity * 100,
    },
    colorAnalysis,
    problemRegions: problemRegions.map(r => ({
      position: r.position,
      similarity: r.similarity.toFixed(1) + '%',
    })),
    outputs: {
      diffImage: path.basename(diffPath),
      heatMap: path.basename(heatPath),
    },
  }
}

// Analyze single best and worst frames
function analyzeSingleFrames(results) {
  if (results.length === 0) return null

  // Sort by masked similarity to find best and worst
  const sorted = [...results].sort((a, b) => b.metrics.maskedSimilarity - a.metrics.maskedSimilarity)

  const bestMatch = sorted[0]
  const worstMatch = sorted[sorted.length - 1]

  return {
    bestMatch: {
      frameIndex: bestMatch.frameIndex,
      similarity: bestMatch.metrics.maskedSimilarity,
      ssim: bestMatch.metrics.ssim,
      diffImage: bestMatch.outputs?.diffImage,
      heatMap: bestMatch.outputs?.heatMap,
      problemRegions: bestMatch.problemRegions,
    },
    worstMatch: {
      frameIndex: worstMatch.frameIndex,
      similarity: worstMatch.metrics.maskedSimilarity,
      ssim: worstMatch.metrics.ssim,
      diffImage: worstMatch.outputs?.diffImage,
      heatMap: worstMatch.outputs?.heatMap,
      problemRegions: worstMatch.problemRegions,
    },
    similaritySpread: bestMatch.metrics.maskedSimilarity - worstMatch.metrics.maskedSimilarity,
    medianSimilarity: sorted[Math.floor(sorted.length / 2)].metrics.maskedSimilarity,
  }
}

// Analyze sequence/animation temporal characteristics
function analyzeSequence(results) {
  if (results.length < 2) return null

  // Calculate frame-to-frame similarity variance
  const similarities = results.map(r => r.metrics.maskedSimilarity)
  const mean = similarities.reduce((a, b) => a + b, 0) / similarities.length
  const variance = similarities.reduce((sum, s) => sum + Math.pow(s - mean, 2), 0) / similarities.length

  // Calculate frame-to-frame change consistency
  const frameChanges = []
  for (let i = 1; i < results.length; i++) {
    const change = Math.abs(results[i].metrics.maskedSimilarity - results[i - 1].metrics.maskedSimilarity)
    frameChanges.push(change)
  }
  const avgFrameChange = frameChanges.reduce((a, b) => a + b, 0) / frameChanges.length
  const maxFrameChange = Math.max(...frameChanges)

  // Detect temporal patterns (improving, degrading, or stable)
  const firstThird = similarities.slice(0, Math.floor(similarities.length / 3))
  const lastThird = similarities.slice(-Math.floor(similarities.length / 3))
  const firstAvg = firstThird.reduce((a, b) => a + b, 0) / firstThird.length
  const lastAvg = lastThird.reduce((a, b) => a + b, 0) / lastThird.length

  let temporalTrend = 'stable'
  if (lastAvg - firstAvg > 2) temporalTrend = 'improving'
  else if (firstAvg - lastAvg > 2) temporalTrend = 'degrading'

  // Calculate smoothness (how consistent frame-to-frame changes are)
  const changeVariance = frameChanges.reduce((sum, c) => sum + Math.pow(c - avgFrameChange, 2), 0) / frameChanges.length
  let smoothness = 'smooth'
  if (changeVariance > 10) smoothness = 'jittery'
  else if (changeVariance > 5) smoothness = 'slightly_uneven'

  // Identify outlier frames (sudden drops in similarity)
  const outlierFrames = []
  for (let i = 0; i < similarities.length; i++) {
    if (similarities[i] < mean - 2 * Math.sqrt(variance)) {
      outlierFrames.push({
        frameIndex: results[i].frameIndex,
        similarity: similarities[i],
        deviation: (mean - similarities[i]).toFixed(2) + '% below mean',
      })
    }
  }

  return {
    temporalConsistency: 100 - Math.sqrt(variance),
    frameToFrameVariance: variance,
    avgFrameChange,
    maxFrameChange,
    temporalTrend,
    smoothness,
    outlierFrames,
    frameCount: results.length,
    similarityRange: {
      min: Math.min(...similarities),
      max: Math.max(...similarities),
      spread: Math.max(...similarities) - Math.min(...similarities),
    },
  }
}

// Generate animator feedback report
function generateFeedback(results, options) {
  const avgMetrics = {
    pixelSimilarity: 0,
    maskedSimilarity: 0,
    ssim: 0,
    edgeSimilarity: 0,
  }

  results.forEach(r => {
    avgMetrics.pixelSimilarity += r.metrics.pixelSimilarity
    avgMetrics.maskedSimilarity += r.metrics.maskedSimilarity
    avgMetrics.ssim += r.metrics.ssim
    avgMetrics.edgeSimilarity += r.metrics.edgeSimilarity
  })

  Object.keys(avgMetrics).forEach(k => {
    avgMetrics[k] /= results.length
  })

  // Single frame analysis
  const singleFrameAnalysis = analyzeSingleFrames(results)

  // Sequence/animation analysis
  const sequenceAnalysis = analyzeSequence(results)

  // Aggregate problem regions - track both occurrences and unique frames
  const regionIssues = {}
  const regionFrames = {} // Track which frames have issues in each region
  results.forEach((r, frameIdx) => {
    r.problemRegions.forEach(pr => {
      regionIssues[pr.position] = (regionIssues[pr.position] || 0) + 1
      if (!regionFrames[pr.position]) regionFrames[pr.position] = new Set()
      regionFrames[pr.position].add(frameIdx)
    })
  })

  // Sort by frequency (total occurrences)
  const sortedIssues = Object.entries(regionIssues)
    .sort((a, b) => b[1] - a[1])
    .map(([region, count]) => ({
      region,
      occurrences: count,
      framesAffected: regionFrames[region]?.size || 0
    }))

  // Generate recommendations
  const recommendations = []

  // Color recommendations - calculate average color differences across all frames
  const avgColorDiffs = {
    hueDiff: results.reduce((sum, r) => sum + (r.colorAnalysis?.difference?.hueDiff || 0), 0) / results.length,
    saturationDiff: results.reduce((sum, r) => sum + (r.colorAnalysis?.difference?.saturationDiff || 0), 0) / results.length,
    luminanceDiff: results.reduce((sum, r) => sum + (r.colorAnalysis?.difference?.luminanceDiff || 0), 0) / results.length,
  }
  const refLuminance = results[0]?.colorAnalysis?.reference?.avgLuminance || 0
  const liveLuminance = results[0]?.colorAnalysis?.live?.avgLuminance || 0

  // PRIORITY: Luminance/brightness is often the most impactful visual difference
  if (avgColorDiffs.luminanceDiff > 15) {
    const direction = liveLuminance < refLuminance ? 'TOO DARK' : 'TOO BRIGHT'
    recommendations.push(`[HIGH PRIORITY] Animation is ${direction}! Luminance: live ${liveLuminance.toFixed(1)}% vs reference ${refLuminance.toFixed(1)}% (${avgColorDiffs.luminanceDiff.toFixed(1)}% difference). Increase bolt core brightness, glow intensity, and overall opacity.`)
  } else if (avgColorDiffs.luminanceDiff > 5) {
    recommendations.push(`Brightness difference detected (${avgColorDiffs.luminanceDiff.toFixed(1)}%). Adjust glow intensity and bolt core brightness.`)
  }

  if (avgMetrics.ssim < 90) {
    recommendations.push('SSIM score low - structural differences detected. Check overall shape and form.')
  }
  if (avgMetrics.edgeSimilarity < 85) {
    recommendations.push('Edge similarity low - bolt shapes may differ. Review bolt generation parameters.')
  }

  // Other color recommendations
  if (avgColorDiffs.hueDiff > 10) {
    recommendations.push(`Hue difference detected (${avgColorDiffs.hueDiff.toFixed(1)}°). Adjust color tint.`)
  }
  if (avgColorDiffs.saturationDiff > 5) {
    recommendations.push(`Saturation difference detected (${avgColorDiffs.saturationDiff.toFixed(1)}%). Adjust color vibrancy.`)
  }

  // Regional recommendations
  if (sortedIssues.length > 0) {
    const topIssue = sortedIssues[0]
    recommendations.push(`Most problematic area: ${topIssue.region} (${topIssue.framesAffected}/${results.length} frames affected, ${topIssue.occurrences} total occurrences)`)
  }

  // Single frame recommendations
  if (singleFrameAnalysis) {
    if (singleFrameAnalysis.similaritySpread > 10) {
      recommendations.push(`High frame variance detected (${singleFrameAnalysis.similaritySpread.toFixed(1)}% spread). Animation consistency needs work.`)
    }
    recommendations.push(`Focus on worst frame #${singleFrameAnalysis.worstMatch.frameIndex} (${singleFrameAnalysis.worstMatch.similarity.toFixed(1)}% similarity)`)
  }

  // Sequence recommendations
  if (sequenceAnalysis) {
    if (sequenceAnalysis.smoothness === 'jittery') {
      recommendations.push('Animation is jittery - frame-to-frame changes are inconsistent.')
    }
    if (sequenceAnalysis.temporalTrend === 'degrading') {
      recommendations.push('Animation quality degrades over time - later frames are worse.')
    }
    if (sequenceAnalysis.outlierFrames.length > 0) {
      recommendations.push(`${sequenceAnalysis.outlierFrames.length} outlier frame(s) detected with sudden quality drops.`)
    }
  }

  return {
    overallScore: Math.round(avgMetrics.maskedSimilarity),
    targetScore: options.target,
    targetMet: avgMetrics.maskedSimilarity >= options.target,
    metrics: {
      pixelMatch: avgMetrics.pixelSimilarity.toFixed(2) + '%',
      maskedMatch: avgMetrics.maskedSimilarity.toFixed(2) + '%',
      ssim: avgMetrics.ssim.toFixed(2) + '%',
      edgeMatch: avgMetrics.edgeSimilarity.toFixed(2) + '%',
    },
    singleFrameAnalysis,
    sequenceAnalysis,
    problemAreas: sortedIssues.slice(0, 3),
    recommendations,
  }
}

// Main analysis
async function main() {
  const options = parseArgs()
  console.log('=== COMPREHENSIVE DIFF ANALYSIS ===\n')

  const outputDir = path.resolve(options.output)
  await fs.mkdir(outputDir, { recursive: true })

  // Get frame lists
  const refDir = path.resolve(options.reference)
  const liveDir = path.resolve(options.live)

  const refFiles = (await fs.readdir(refDir))
    .filter(f => f.startsWith('frame_') && f.endsWith('.png')).sort()
  const liveFiles = (await fs.readdir(liveDir))
    .filter(f => f.startsWith('frame_') && f.endsWith('.png')).sort()

  const frameCount = Math.min(refFiles.length, liveFiles.length)
  console.log(`Analyzing ${frameCount} frame pairs...\n`)

  const results = []
  for (let i = 0; i < frameCount; i++) {
    console.log(`Frame ${i + 1}/${frameCount}...`)
    const result = await analyzeFrame(
      path.join(refDir, refFiles[i]),
      path.join(liveDir, liveFiles[i]),
      outputDir,
      i
    )
    results.push(result)
    console.log(`  SSIM: ${result.metrics.ssim.toFixed(1)}%, Masked: ${result.metrics.maskedSimilarity.toFixed(1)}%`)
  }

  // Generate feedback
  const feedback = generateFeedback(results, options)

  // Save comprehensive report with all analysis data
  const report = {
    analyzedAt: new Date().toISOString(),
    summary: feedback,
    singleFrameAnalysis: feedback.singleFrameAnalysis,
    sequenceAnalysis: feedback.sequenceAnalysis,
    frameResults: results,
  }

  const reportPath = path.join(outputDir, 'comprehensive-analysis.json')
  await fs.writeFile(reportPath, JSON.stringify(report, null, 2))

  // Print summary
  console.log('\n' + '='.repeat(60))
  console.log('COMPREHENSIVE ANALYSIS COMPLETE (v2.1 - maskedSimilarity fix)')
  console.log('='.repeat(60))
  console.log(`\n>>> OVERALL SCORE: ${feedback.overallScore}/100 <<<`)
  console.log(`Target: ${feedback.targetScore}%`)
  console.log(`Status: ${feedback.targetMet ? '✓ TARGET MET!' : '✗ ITERATION NEEDED'}\n`)

  console.log('METRICS:')
  console.log(`  Pixel Match:  ${feedback.metrics.pixelMatch}`)
  console.log(`  Masked Match: ${feedback.metrics.maskedMatch}`)
  console.log(`  SSIM:         ${feedback.metrics.ssim}`)
  console.log(`  Edge Match:   ${feedback.metrics.edgeMatch}`)

  // Single frame analysis
  if (feedback.singleFrameAnalysis) {
    const sfa = feedback.singleFrameAnalysis
    console.log('\nSINGLE FRAME ANALYSIS:')
    console.log(`  Best Frame:  #${sfa.bestMatch.frameIndex} (${sfa.bestMatch.similarity.toFixed(1)}% match)`)
    console.log(`  Worst Frame: #${sfa.worstMatch.frameIndex} (${sfa.worstMatch.similarity.toFixed(1)}% match)`)
    console.log(`  Spread:      ${sfa.similaritySpread.toFixed(1)}%`)
    console.log(`  Median:      ${sfa.medianSimilarity.toFixed(1)}%`)
  }

  // Sequence analysis
  if (feedback.sequenceAnalysis) {
    const seq = feedback.sequenceAnalysis
    console.log('\nSEQUENCE/ANIMATION ANALYSIS:')
    console.log(`  Temporal Consistency: ${seq.temporalConsistency.toFixed(1)}%`)
    console.log(`  Smoothness:          ${seq.smoothness}`)
    console.log(`  Temporal Trend:      ${seq.temporalTrend}`)
    console.log(`  Frame-to-Frame Var:  ${seq.frameToFrameVariance.toFixed(4)}`)
    if (seq.outlierFrames.length > 0) {
      console.log(`  Outlier Frames:      ${seq.outlierFrames.map(f => `#${f.frameIndex}`).join(', ')}`)
    }
  }

  if (feedback.problemAreas.length > 0) {
    console.log('\nPROBLEM AREAS:')
    feedback.problemAreas.forEach(a => {
      console.log(`  - ${a.region}: ${a.framesAffected} frames, ${a.occurrences} occurrences`)
    })
  }

  if (feedback.recommendations.length > 0) {
    console.log('\nRECOMMENDATIONS FOR ANIMATOR:')
    feedback.recommendations.forEach((r, i) => {
      console.log(`  ${i + 1}. ${r}`)
    })
  }

  console.log(`\nOutputs saved to: ${outputDir}`)
  console.log(`  - Diff images: diff_*.png`)
  console.log(`  - Heat maps: heat_*.png`)
  console.log(`  - Full report: comprehensive-analysis.json`)
  console.log(`  - Contains: singleFrameAnalysis, sequenceAnalysis, frameResults`)

  process.exit(feedback.targetMet ? 0 : 2)
}

main().catch(err => {
  console.error('Analysis failed:', err)
  process.exit(1)
})
