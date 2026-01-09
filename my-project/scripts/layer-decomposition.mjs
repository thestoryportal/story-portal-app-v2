#!/usr/bin/env node
/**
 * Reference Layer Decomposition v1.0
 *
 * Decomposes animation into semantic layers for independent matching:
 * - Background (static)
 * - Outer glow (animated, screen blend)
 * - Inner glow (animated, add blend)
 * - Bolts (animated, add blend)
 * - Core hotspot (animated, add blend)
 *
 * Each layer can be analyzed and matched independently for precision.
 *
 * Usage:
 *   import { decomposeFrame, analyzeLayers } from './layer-decomposition.mjs'
 */

import { PNG } from 'pngjs'
import { createReadStream } from 'fs'
import fs from 'fs/promises'

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

// RGB to HSL
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

/**
 * Decompose a frame into semantic layers based on brightness
 */
export async function decomposeFrame(pngOrPath) {
  const png = typeof pngOrPath === 'string' ? await loadPNG(pngOrPath) : pngOrPath
  const { width, height, data } = png

  // Create layer PNGs
  const layers = {
    background: new PNG({ width, height }),
    outerGlow: new PNG({ width, height }),
    innerGlow: new PNG({ width, height }),
    bolts: new PNG({ width, height }),
    coreHotspot: new PNG({ width, height })
  }

  // Initialize all layers to transparent
  for (const layer of Object.values(layers)) {
    for (let i = 0; i < layer.data.length; i += 4) {
      layer.data[i] = 0
      layer.data[i + 1] = 0
      layer.data[i + 2] = 0
      layer.data[i + 3] = 0
    }
  }

  const centerX = width / 2
  const centerY = height / 2

  // Classify each pixel into layers based on brightness and distance from center
  for (let y = 0; y < height; y++) {
    for (let x = 0; x < width; x++) {
      const idx = (y * width + x) * 4
      const r = data[idx]
      const g = data[idx + 1]
      const b = data[idx + 2]
      const brightness = getLuminance(r, g, b)

      const dx = x - centerX
      const dy = y - centerY
      const distance = Math.sqrt(dx * dx + dy * dy)

      // Layer classification by brightness thresholds
      let targetLayer

      if (brightness < 10) {
        // Background
        targetLayer = layers.background
      } else if (brightness >= 200) {
        // Core hotspot (very bright)
        targetLayer = layers.coreHotspot
      } else if (brightness >= 120) {
        // Bolts (bright ridges)
        targetLayer = layers.bolts
      } else if (brightness >= 40) {
        // Inner glow
        targetLayer = layers.innerGlow
      } else {
        // Outer glow (dim)
        targetLayer = layers.outerGlow
      }

      // Copy pixel to target layer
      targetLayer.data[idx] = r
      targetLayer.data[idx + 1] = g
      targetLayer.data[idx + 2] = b
      targetLayer.data[idx + 3] = 255
    }
  }

  return layers
}

/**
 * Analyze properties of each layer
 */
export function analyzeLayerProperties(layers) {
  const analysis = {}

  for (const [layerName, layerPNG] of Object.entries(layers)) {
    const { width, height, data } = layerPNG

    let pixelCount = 0
    let totalBrightness = 0
    let hueSum = 0
    let saturationSum = 0
    let colorCount = 0

    for (let i = 0; i < data.length; i += 4) {
      const r = data[i]
      const g = data[i + 1]
      const b = data[i + 2]
      const brightness = getLuminance(r, g, b)

      if (brightness > 5) {
        pixelCount++
        totalBrightness += brightness

        const hsl = rgbToHsl(r, g, b)
        hueSum += hsl.h
        saturationSum += hsl.s
        colorCount++
      }
    }

    analysis[layerName] = {
      pixelCount,
      coverage: (pixelCount / (width * height)) * 100,
      avgBrightness: colorCount > 0 ? totalBrightness / pixelCount : 0,
      avgHue: colorCount > 0 ? hueSum / colorCount : 0,
      avgSaturation: colorCount > 0 ? saturationSum / colorCount : 0
    }
  }

  return analysis
}

/**
 * Save all layers to disk
 */
export async function saveLayers(layers, outputDir, baseName = 'frame') {
  const saved = {}

  for (const [layerName, layerPNG] of Object.entries(layers)) {
    const filename = `${baseName}_layer_${layerName}.png`
    const filepath = `${outputDir}/${filename}`
    await savePNG(layerPNG, filepath)
    saved[layerName] = filepath
  }

  return saved
}

/**
 * Compare layers between reference and live
 */
export function compareLayers(refLayers, liveLayers) {
  const refAnalysis = analyzeLayerProperties(refLayers)
  const liveAnalysis = analyzeLayerProperties(liveLayers)

  const comparison = {}

  for (const layerName of Object.keys(refAnalysis)) {
    const ref = refAnalysis[layerName]
    const live = liveAnalysis[layerName]

    const coverageDiff = ((live.coverage - ref.coverage) / ref.coverage) * 100
    const brightnessDiff = ((live.avgBrightness - ref.avgBrightness) / ref.avgBrightness) * 100
    const hueDiff = live.avgHue - ref.avgHue
    const saturationDiff = ((live.avgSaturation - ref.avgSaturation) / ref.avgSaturation) * 100

    comparison[layerName] = {
      reference: ref,
      live,
      differences: {
        coveragePercent: parseFloat(coverageDiff.toFixed(1)),
        brightnessPercent: parseFloat(brightnessDiff.toFixed(1)),
        hueDegrees: parseFloat(hueDiff.toFixed(1)),
        saturationPercent: parseFloat(saturationDiff.toFixed(1))
      },
      assessment: assessLayerMatch(coverageDiff, brightnessDiff, hueDiff)
    }
  }

  return comparison
}

/**
 * Assess if a layer matches well
 */
function assessLayerMatch(coverageDiff, brightnessDiff, hueDiff) {
  const issues = []

  if (Math.abs(coverageDiff) > 20) {
    issues.push(`Coverage ${coverageDiff > 0 ? 'too large' : 'too small'}`)
  }
  if (Math.abs(brightnessDiff) > 15) {
    issues.push(`Brightness ${brightnessDiff > 0 ? 'too high' : 'too low'}`)
  }
  if (Math.abs(hueDiff) > 10) {
    issues.push(`Hue shifted by ${hueDiff.toFixed(1)}°`)
  }

  if (issues.length === 0) {
    return { status: 'GOOD', issues: [] }
  } else if (issues.length <= 1) {
    return { status: 'ACCEPTABLE', issues }
  } else {
    return { status: 'NEEDS_ADJUSTMENT', issues }
  }
}

/**
 * Generate layer-specific recommendations
 */
export function generateLayerRecommendations(layerComparison) {
  const recommendations = []

  for (const [layerName, comparison] of Object.entries(layerComparison)) {
    if (comparison.assessment.status === 'NEEDS_ADJUSTMENT') {
      for (const issue of comparison.assessment.issues) {
        recommendations.push({
          layer: layerName,
          priority: 'HIGH',
          issue,
          action: generateLayerAction(layerName, issue)
        })
      }
    }
  }

  return recommendations
}

function generateLayerAction(layerName, issue) {
  const actions = {
    coreHotspot: {
      'too high': 'Reduce core brightness parameter',
      'too low': 'Increase core brightness parameter',
      'too large': 'Reduce hotspot radius',
      'too small': 'Increase hotspot radius'
    },
    bolts: {
      'too high': 'Reduce bolt brightness/intensity',
      'too low': 'Increase bolt brightness/intensity',
      'too large': 'Reduce bolt count or thickness',
      'too small': 'Increase bolt count or length'
    },
    innerGlow: {
      'too high': 'Reduce inner glow intensity',
      'too low': 'Increase inner glow intensity',
      'too large': 'Reduce inner glow radius',
      'too small': 'Increase inner glow radius'
    },
    outerGlow: {
      'too high': 'Reduce outer glow intensity',
      'too low': 'Increase outer glow intensity',
      'too large': 'Reduce outer glow radius/falloff',
      'too small': 'Increase outer glow radius/falloff'
    }
  }

  const layerActions = actions[layerName] || {}

  for (const [keyword, action] of Object.entries(layerActions)) {
    if (issue.includes(keyword)) {
      return action
    }
  }

  return `Adjust ${layerName} parameters to match reference`
}

export default {
  decomposeFrame,
  analyzeLayerProperties,
  saveLayers,
  compareLayers,
  generateLayerRecommendations
}
