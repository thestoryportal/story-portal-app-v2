#!/usr/bin/env node
/**
 * Enhanced Diff Visualizations v1.0
 *
 * Generate multiple visualization types for better understanding of differences:
 * - Standard diff (red pixels)
 * - Heat map (intensity gradient)
 * - Side-by-side comparison
 * - Overlay (semi-transparent)
 * - Semantic diff (color-coded by issue type)
 * - Motion vectors (for temporal comparison)
 *
 * Usage:
 *   import { generateAllVisualizations } from './enhanced-diff-viz.mjs'
 */

import { PNG } from 'pngjs'
import fs from 'fs/promises'
import path from 'path'

// Save PNG helper
async function savePNG(png, filepath) {
  const buffer = PNG.sync.write(png)
  await fs.writeFile(filepath, buffer)
}

/**
 * Generate side-by-side comparison (Reference | Live | Diff)
 */
export async function generateSideBySide(refImage, liveImage, diffImage, outputPath) {
  const { width, height } = refImage
  const sideBySide = new PNG({ width: width * 3 + 40, height: height + 60 })

  // Fill background with dark gray
  for (let i = 0; i < sideBySide.data.length; i += 4) {
    sideBySide.data[i] = 30
    sideBySide.data[i + 1] = 30
    sideBySide.data[i + 2] = 30
    sideBySide.data[i + 3] = 255
  }

  // Copy reference image (left)
  copyImage(refImage, sideBySide, 10, 50)

  // Copy live image (middle)
  copyImage(liveImage, sideBySide, width + 20, 50)

  // Copy diff image (right)
  copyImage(diffImage, sideBySide, width * 2 + 30, 50)

  // Add labels (simple - just leave space, actual text would need canvas)
  // Labels would show: "REFERENCE" | "LIVE" | "DIFF"

  await savePNG(sideBySide, outputPath)
  return outputPath
}

/**
 * Generate overlay visualization (reference with semi-transparent live)
 */
export async function generateOverlay(refImage, liveImage, outputPath, opacity = 0.5) {
  const { width, height } = refImage
  const overlay = new PNG({ width, height })

  for (let y = 0; y < height; y++) {
    for (let x = 0; x < width; x++) {
      const idx = (y * width + x) * 4

      // Blend reference and live with opacity
      overlay.data[idx] = refImage.data[idx] * (1 - opacity) + liveImage.data[idx] * opacity
      overlay.data[idx + 1] = refImage.data[idx + 1] * (1 - opacity) + liveImage.data[idx + 1] * opacity
      overlay.data[idx + 2] = refImage.data[idx + 2] * (1 - opacity) + liveImage.data[idx + 2] * opacity
      overlay.data[idx + 3] = 255
    }
  }

  await savePNG(overlay, outputPath)
  return outputPath
}

/**
 * Generate semantic diff (color-coded by issue type)
 * - RED: Missing in live (present in ref, absent in live)
 * - BLUE: Extra in live (absent in ref, present in live)
 * - YELLOW: Color mismatch (present in both but wrong color)
 * - GREEN: Good match
 */
export async function generateSemanticDiff(refImage, liveImage, outputPath, threshold = 25) {
  const { width, height } = refImage
  const semantic = new PNG({ width, height })

  for (let y = 0; y < height; y++) {
    for (let x = 0; x < width; x++) {
      const idx = (y * width + x) * 4

      const refBrightness = (refImage.data[idx] + refImage.data[idx + 1] + refImage.data[idx + 2]) / 3
      const liveBrightness = (liveImage.data[idx] + liveImage.data[idx + 1] + liveImage.data[idx + 2]) / 3

      const refIsBright = refBrightness > threshold
      const liveIsBright = liveBrightness > threshold

      const colorDiff = Math.abs(refImage.data[idx] - liveImage.data[idx]) +
                        Math.abs(refImage.data[idx + 1] - liveImage.data[idx + 1]) +
                        Math.abs(refImage.data[idx + 2] - liveImage.data[idx + 2])

      if (!refIsBright && !liveIsBright) {
        // Both dark - show as dark gray
        semantic.data[idx] = 20
        semantic.data[idx + 1] = 20
        semantic.data[idx + 2] = 20
      } else if (refIsBright && !liveIsBright) {
        // RED: Missing in live
        semantic.data[idx] = 255
        semantic.data[idx + 1] = 50
        semantic.data[idx + 2] = 50
      } else if (!refIsBright && liveIsBright) {
        // BLUE: Extra in live
        semantic.data[idx] = 50
        semantic.data[idx + 1] = 100
        semantic.data[idx + 2] = 255
      } else if (colorDiff > threshold * 2) {
        // YELLOW: Color mismatch
        semantic.data[idx] = 255
        semantic.data[idx + 1] = 255
        semantic.data[idx + 2] = 50
      } else {
        // GREEN: Good match
        semantic.data[idx] = 50
        semantic.data[idx + 1] = 200
        semantic.data[idx + 2] = 50
      }

      semantic.data[idx + 3] = 255
    }
  }

  await savePNG(semantic, outputPath)
  return outputPath
}

/**
 * Generate enhanced heat map with legend
 */
export async function generateEnhancedHeatMap(refImage, liveImage, outputPath) {
  const { width, height } = refImage
  const heatMap = new PNG({ width, height })

  let maxDiff = 0
  const diffs = []

  // First pass: calculate all differences
  for (let y = 0; y < height; y++) {
    for (let x = 0; x < width; x++) {
      const idx = (y * width + x) * 4
      const dr = Math.abs(refImage.data[idx] - liveImage.data[idx])
      const dg = Math.abs(refImage.data[idx + 1] - liveImage.data[idx + 1])
      const db = Math.abs(refImage.data[idx + 2] - liveImage.data[idx + 2])
      const diff = (dr + dg + db) / 3

      diffs.push(diff)
      if (diff > maxDiff) maxDiff = diff
    }
  }

  // Second pass: generate heat map colors
  let idx = 0
  for (let y = 0; y < height; y++) {
    for (let x = 0; x < width; x++) {
      const pixelIdx = (y * width + x) * 4
      const diff = diffs[idx++]
      const normalized = maxDiff > 0 ? diff / maxDiff : 0

      // Enhanced color gradient: black -> blue -> cyan -> green -> yellow -> orange -> red
      let r, g, b
      if (normalized < 0.16) {
        // Black to blue
        const t = normalized / 0.16
        r = 0
        g = 0
        b = Math.floor(255 * t)
      } else if (normalized < 0.33) {
        // Blue to cyan
        const t = (normalized - 0.16) / 0.17
        r = 0
        g = Math.floor(255 * t)
        b = 255
      } else if (normalized < 0.5) {
        // Cyan to green
        const t = (normalized - 0.33) / 0.17
        r = 0
        g = 255
        b = Math.floor(255 * (1 - t))
      } else if (normalized < 0.66) {
        // Green to yellow
        const t = (normalized - 0.5) / 0.16
        r = Math.floor(255 * t)
        g = 255
        b = 0
      } else if (normalized < 0.83) {
        // Yellow to orange
        const t = (normalized - 0.66) / 0.17
        r = 255
        g = Math.floor(255 * (1 - t * 0.5))
        b = 0
      } else {
        // Orange to red
        const t = (normalized - 0.83) / 0.17
        r = 255
        g = Math.floor(128 * (1 - t))
        b = 0
      }

      heatMap.data[pixelIdx] = r
      heatMap.data[pixelIdx + 1] = g
      heatMap.data[pixelIdx + 2] = b
      heatMap.data[pixelIdx + 3] = 255
    }
  }

  await savePNG(heatMap, outputPath)
  return outputPath
}

/**
 * Generate difference magnitude visualization
 */
export async function generateDifferenceMagnitude(refImage, liveImage, outputPath) {
  const { width, height } = refImage
  const magnitude = new PNG({ width, height })

  for (let y = 0; y < height; y++) {
    for (let x = 0; x < width; x++) {
      const idx = (y * width + x) * 4

      const dr = Math.abs(refImage.data[idx] - liveImage.data[idx])
      const dg = Math.abs(refImage.data[idx + 1] - liveImage.data[idx + 1])
      const db = Math.abs(refImage.data[idx + 2] - liveImage.data[idx + 2])
      const diff = (dr + dg + db) / 3

      // Grayscale based on difference magnitude
      magnitude.data[idx] = diff
      magnitude.data[idx + 1] = diff
      magnitude.data[idx + 2] = diff
      magnitude.data[idx + 3] = 255
    }
  }

  await savePNG(magnitude, outputPath)
  return outputPath
}

/**
 * Generate all visualizations for a frame pair
 */
export async function generateAllVisualizations(refImage, liveImage, diffImage, baseOutputPath) {
  const dir = path.dirname(baseOutputPath)
  const baseName = path.basename(baseOutputPath, '.png')

  const outputs = {
    standard: baseOutputPath, // Already generated diff
    sideBySide: path.join(dir, `${baseName}_sidebyside.png`),
    overlay: path.join(dir, `${baseName}_overlay.png`),
    semantic: path.join(dir, `${baseName}_semantic.png`),
    heatmap: path.join(dir, `${baseName}_heatmap_enhanced.png`),
    magnitude: path.join(dir, `${baseName}_magnitude.png`)
  }

  try {
    await Promise.all([
      generateSideBySide(refImage, liveImage, diffImage, outputs.sideBySide),
      generateOverlay(refImage, liveImage, outputs.overlay),
      generateSemanticDiff(refImage, liveImage, outputs.semantic),
      generateEnhancedHeatMap(refImage, liveImage, outputs.heatmap),
      generateDifferenceMagnitude(refImage, liveImage, outputs.magnitude)
    ])

    return outputs
  } catch (err) {
    console.error(`Error generating visualizations: ${err.message}`)
    return { error: err.message }
  }
}

// Helper: copy image to another at offset
function copyImage(source, dest, offsetX, offsetY) {
  const { width, height } = source
  for (let y = 0; y < height; y++) {
    for (let x = 0; x < width; x++) {
      const srcIdx = (y * width + x) * 4
      const destIdx = ((y + offsetY) * dest.width + (x + offsetX)) * 4

      dest.data[destIdx] = source.data[srcIdx]
      dest.data[destIdx + 1] = source.data[srcIdx + 1]
      dest.data[destIdx + 2] = source.data[srcIdx + 2]
      dest.data[destIdx + 3] = source.data[srcIdx + 3]
    }
  }
}

export default {
  generateAllVisualizations,
  generateSideBySide,
  generateOverlay,
  generateSemanticDiff,
  generateEnhancedHeatMap,
  generateDifferenceMagnitude
}
