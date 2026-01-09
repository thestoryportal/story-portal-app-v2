#!/usr/bin/env node
/**
 * Semantic Analyzer v1.0
 *
 * Provides semantic understanding of electricity animation frames:
 * - Bolt detection (count, angles, lengths, thickness)
 * - Glow region analysis (inner/outer radii, intensities)
 * - Hotspot detection and measurement
 * - Structural comparison at semantic level
 *
 * Usage:
 *   import { analyzeFrame, compareSemantics } from './semantic-analyzer.mjs'
 */

import { PNG } from 'pngjs'
import { createReadStream } from 'fs'

// Load PNG file
export async function loadPNG(filepath) {
  return new Promise((resolve, reject) => {
    const stream = createReadStream(filepath)
    const png = new PNG()
    stream.pipe(png)
      .on('parsed', () => resolve(png))
      .on('error', reject)
  })
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

// Get luminance
function getLuminance(r, g, b) {
  return 0.299 * r + 0.587 * g + 0.114 * b
}

// Check if pixel is bright (part of bolt or glow)
function isBright(r, g, b, threshold = 30) {
  return r > threshold || g > threshold || b > threshold
}

// Detect bolts using ridge detection and connected components
export function detectBolts(png) {
  const { width, height, data } = png
  const centerX = width / 2
  const centerY = height / 2

  // Create brightness map
  const brightnessMap = new Float32Array(width * height)
  for (let y = 0; y < height; y++) {
    for (let x = 0; x < width; x++) {
      const idx = (y * width + x) * 4
      const brightness = getLuminance(data[idx], data[idx + 1], data[idx + 2])
      brightnessMap[y * width + x] = brightness
    }
  }

  // Detect bright ridges (bolts are high-brightness ridges radiating from center)
  const bolts = []
  const visited = new Set()
  const minBoltBrightness = 100

  // Scan in radial pattern from center
  for (let angle = 0; angle < 360; angle += 15) {
    const rad = (angle * Math.PI) / 180
    let boltPixels = []
    let maxRadius = Math.min(width, height) * 0.4

    for (let r = 30; r < maxRadius; r++) {
      const x = Math.round(centerX + r * Math.cos(rad))
      const y = Math.round(centerY + r * Math.sin(rad))

      if (x < 0 || x >= width || y < 0 || y >= height) break

      const idx = (y * width + x) * 4
      const brightness = getLuminance(data[idx], data[idx + 1], data[idx + 2])

      if (brightness > minBoltBrightness) {
        boltPixels.push({ x, y, brightness, distance: r })
      } else if (boltPixels.length > 10) {
        // Bolt ended
        break
      }
    }

    // If we found a significant bolt path
    if (boltPixels.length > 15) {
      const avgBrightness = boltPixels.reduce((sum, p) => sum + p.brightness, 0) / boltPixels.length
      const length = boltPixels[boltPixels.length - 1].distance - boltPixels[0].distance

      // Estimate thickness by checking perpendicular width
      const midPoint = boltPixels[Math.floor(boltPixels.length / 2)]
      const perpAngle = rad + Math.PI / 2
      let thickness = 0
      for (let offset = 1; offset <= 10; offset++) {
        const px = Math.round(midPoint.x + offset * Math.cos(perpAngle))
        const py = Math.round(midPoint.y + offset * Math.sin(perpAngle))
        if (px >= 0 && px < width && py >= 0 && py < height) {
          const idx = (py * width + px) * 4
          const b = getLuminance(data[idx], data[idx + 1], data[idx + 2])
          if (b > minBoltBrightness * 0.5) thickness++
          else break
        }
      }
      thickness *= 2 // Both sides

      bolts.push({
        angle,
        length,
        thickness: thickness || 2,
        brightness: avgBrightness / 255,
        pixelCount: boltPixels.length
      })
    }
  }

  return bolts
}

// Detect glow regions (inner and outer)
export function detectGlowRegions(png) {
  const { width, height, data } = png
  const centerX = width / 2
  const centerY = height / 2

  // Sample brightness at various radii
  const radialProfile = []
  const maxRadius = Math.min(width, height) * 0.45

  for (let r = 0; r < maxRadius; r += 5) {
    let samples = []
    const angleStep = Math.max(1, Math.floor(360 / (2 * Math.PI * r + 1)))

    for (let angle = 0; angle < 360; angle += angleStep) {
      const rad = (angle * Math.PI) / 180
      const x = Math.round(centerX + r * Math.cos(rad))
      const y = Math.round(centerY + r * Math.sin(rad))

      if (x >= 0 && x < width && y >= 0 && y < height) {
        const idx = (y * width + x) * 4
        const brightness = getLuminance(data[idx], data[idx + 1], data[idx + 2])
        const hsl = rgbToHsl(data[idx], data[idx + 1], data[idx + 2])

        if (brightness > 10) { // Skip near-black
          samples.push({ brightness, hue: hsl.h, saturation: hsl.s })
        }
      }
    }

    if (samples.length > 0) {
      radialProfile.push({
        radius: r,
        avgBrightness: samples.reduce((s, p) => s + p.brightness, 0) / samples.length,
        avgHue: samples.reduce((s, p) => s + p.hue, 0) / samples.length,
        avgSaturation: samples.reduce((s, p) => s + p.saturation, 0) / samples.length,
        sampleCount: samples.length
      })
    }
  }

  // Find glow regions by detecting brightness gradient changes
  let innerGlowRadius = 0
  let outerGlowRadius = 0
  let maxBrightness = 0
  let maxBrightnessRadius = 0

  for (let i = 0; i < radialProfile.length; i++) {
    if (radialProfile[i].avgBrightness > maxBrightness) {
      maxBrightness = radialProfile[i].avgBrightness
      maxBrightnessRadius = radialProfile[i].radius
    }
  }

  // Inner glow: from center to first major drop
  for (let i = 1; i < radialProfile.length; i++) {
    const gradient = radialProfile[i].avgBrightness - radialProfile[i - 1].avgBrightness
    if (gradient < -5 && radialProfile[i].radius > 20) {
      innerGlowRadius = radialProfile[i].radius
      break
    }
  }

  // Outer glow: where brightness drops to near-black
  for (let i = radialProfile.length - 1; i >= 0; i--) {
    if (radialProfile[i].avgBrightness > 15) {
      outerGlowRadius = radialProfile[i].radius
      break
    }
  }

  // Get color samples for each region
  const innerGlowSample = radialProfile.find(p => p.radius <= innerGlowRadius) || radialProfile[0]
  const outerGlowSample = radialProfile[radialProfile.length - 1]

  return {
    inner: {
      radius: innerGlowRadius,
      intensity: innerGlowSample ? innerGlowSample.avgBrightness / 255 : 0,
      color: innerGlowSample ? {
        hue: innerGlowSample.avgHue,
        saturation: innerGlowSample.avgSaturation
      } : null
    },
    outer: {
      radius: outerGlowRadius,
      intensity: outerGlowSample ? outerGlowSample.avgBrightness / 255 : 0,
      color: outerGlowSample ? {
        hue: outerGlowSample.avgHue,
        saturation: outerGlowSample.avgSaturation
      } : null
    },
    radialProfile
  }
}

// Detect hotspot (brightest central region)
export function detectHotspot(png) {
  const { width, height, data } = png
  const centerX = width / 2
  const centerY = height / 2

  let maxBrightness = 0
  let hotspotX = centerX
  let hotspotY = centerY
  let brightPixels = []

  // Search in central region
  const searchRadius = 60
  for (let y = centerY - searchRadius; y <= centerY + searchRadius; y++) {
    for (let x = centerX - searchRadius; x <= centerX + searchRadius; x++) {
      if (x >= 0 && x < width && y >= 0 && y < height) {
        const idx = (y * width + x) * 4
        const brightness = getLuminance(data[idx], data[idx + 1], data[idx + 2])

        if (brightness > 200) {
          brightPixels.push({ x, y, brightness })
          if (brightness > maxBrightness) {
            maxBrightness = brightness
            hotspotX = x
            hotspotY = y
          }
        }
      }
    }
  }

  // Calculate hotspot radius (where brightness > 90% of max)
  let radius = 0
  if (brightPixels.length > 0) {
    const threshold = maxBrightness * 0.9
    const corePixels = brightPixels.filter(p => p.brightness >= threshold)
    if (corePixels.length > 0) {
      const distances = corePixels.map(p =>
        Math.sqrt((p.x - hotspotX) ** 2 + (p.y - hotspotY) ** 2)
      )
      radius = Math.max(...distances)
    }
  }

  return {
    x: hotspotX,
    y: hotspotY,
    radius: radius || 15,
    brightness: maxBrightness / 255,
    pixelCount: brightPixels.length
  }
}

// Full semantic analysis of a frame
export async function analyzeFrame(pngOrPath) {
  const png = typeof pngOrPath === 'string' ? await loadPNG(pngOrPath) : pngOrPath

  const bolts = detectBolts(png)
  const glowRegions = detectGlowRegions(png)
  const hotspot = detectHotspot(png)

  return {
    bolts: {
      count: bolts.length,
      details: bolts,
      avgLength: bolts.length > 0 ? bolts.reduce((s, b) => s + b.length, 0) / bolts.length : 0,
      avgThickness: bolts.length > 0 ? bolts.reduce((s, b) => s + b.thickness, 0) / bolts.length : 0,
      avgBrightness: bolts.length > 0 ? bolts.reduce((s, b) => s + b.brightness, 0) / bolts.length : 0
    },
    glowRegions,
    hotspot,
    timestamp: new Date().toISOString()
  }
}

// Compare two semantic analyses
export function compareSemantics(refAnalysis, liveAnalysis) {
  const boltCountDiff = liveAnalysis.bolts.count - refAnalysis.bolts.count
  const boltLengthDiff = ((liveAnalysis.bolts.avgLength - refAnalysis.bolts.avgLength) / refAnalysis.bolts.avgLength) * 100
  const boltThicknessDiff = ((liveAnalysis.bolts.avgThickness - refAnalysis.bolts.avgThickness) / refAnalysis.bolts.avgThickness) * 100

  const innerRadiusDiff = ((liveAnalysis.glowRegions.inner.radius - refAnalysis.glowRegions.inner.radius) / refAnalysis.glowRegions.inner.radius) * 100
  const outerRadiusDiff = ((liveAnalysis.glowRegions.outer.radius - refAnalysis.glowRegions.outer.radius) / refAnalysis.glowRegions.outer.radius) * 100

  const hotspotBrightnessDiff = ((liveAnalysis.hotspot.brightness - refAnalysis.hotspot.brightness) / refAnalysis.hotspot.brightness) * 100

  return {
    bolts: {
      countDifference: boltCountDiff,
      countMatch: boltCountDiff === 0,
      lengthDifferencePercent: boltLengthDiff.toFixed(1),
      thicknessDifferencePercent: boltThicknessDiff.toFixed(1),
      assessment: Math.abs(boltCountDiff) <= 2 && Math.abs(boltLengthDiff) < 20 ? 'GOOD' : 'NEEDS_ADJUSTMENT'
    },
    glow: {
      innerRadiusDifferencePercent: innerRadiusDiff.toFixed(1),
      outerRadiusDifferencePercent: outerRadiusDiff.toFixed(1),
      assessment: Math.abs(innerRadiusDiff) < 15 && Math.abs(outerRadiusDiff) < 15 ? 'GOOD' : 'NEEDS_ADJUSTMENT'
    },
    hotspot: {
      brightnessDifferencePercent: hotspotBrightnessDiff.toFixed(1),
      assessment: Math.abs(hotspotBrightnessDiff) < 20 ? 'GOOD' : 'NEEDS_ADJUSTMENT'
    },
    overallSemanticMatch: calculateOverallMatch(boltCountDiff, boltLengthDiff, innerRadiusDiff, outerRadiusDiff)
  }
}

function calculateOverallMatch(boltCountDiff, boltLengthDiff, innerRadiusDiff, outerRadiusDiff) {
  let score = 100

  // Penalize bolt count mismatch heavily
  score -= Math.abs(boltCountDiff) * 8

  // Penalize geometry differences
  score -= Math.abs(boltLengthDiff) * 0.5
  score -= Math.abs(innerRadiusDiff) * 0.3
  score -= Math.abs(outerRadiusDiff) * 0.2

  return Math.max(0, Math.min(100, score))
}

export default {
  analyzeFrame,
  compareSemantics,
  detectBolts,
  detectGlowRegions,
  detectHotspot,
  loadPNG
}
