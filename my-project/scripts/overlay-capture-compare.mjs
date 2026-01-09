#!/usr/bin/env node
/**
 * Overlay Capture & Compare
 *
 * Captures screenshots with:
 * 1. Reference APNG overlaid on the UI
 * 2. Live animation overlaid on the UI
 *
 * Optionally crops to focal area for cleaner comparison.
 *
 * Usage:
 *   node scripts/overlay-capture-compare.mjs [options]
 *
 * Options:
 *   --iteration N     Iteration number for output naming (default: 1)
 *   --frames N        Number of frames to capture (default: 20)
 *   --interval N      Milliseconds between captures (default: 150)
 *   --url URL         Dev server URL (default: http://localhost:5173)
 *   --output DIR      Output directory (default: docs/specs/overlay-frames)
 *   --capture-only    Only capture, don't compare
 *   --compare-only    Only compare existing captures
 *   --crop            Crop to focal area (recommended for cleaner diff)
 *   --no-crop         Capture full page (default)
 */

import puppeteer from 'puppeteer'
import fs from 'fs/promises'
import path from 'path'
import { fileURLToPath } from 'url'
import { PNG } from 'pngjs'
import pixelmatch from 'pixelmatch'
import focalConfig, { getCircularMask } from './focal-config.mjs'

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const PROJECT_ROOT = path.resolve(__dirname, '..')

// Parse command line arguments
function parseArgs() {
  const args = process.argv.slice(2)
  const options = {
    iteration: 1,
    frames: 20,
    interval: 150,
    url: 'http://localhost:5173',
    output: 'docs/specs/overlay-frames',
    captureOnly: false,
    compareOnly: false,
    crop: true, // Default to cropping for cleaner diffs
    width: focalConfig.VIEWPORT.width,
    height: focalConfig.VIEWPORT.height,
  }

  for (let i = 0; i < args.length; i++) {
    switch (args[i]) {
      case '--iteration':
        options.iteration = parseInt(args[++i], 10)
        break
      case '--frames':
        options.frames = parseInt(args[++i], 10)
        break
      case '--interval':
        options.interval = parseInt(args[++i], 10)
        break
      case '--url':
        options.url = args[++i]
        break
      case '--output':
        options.output = args[++i]
        break
      case '--capture-only':
        options.captureOnly = true
        break
      case '--compare-only':
        options.compareOnly = true
        break
      case '--crop':
        options.crop = true
        break
      case '--no-crop':
        options.crop = false
        break
      case '--width':
        options.width = parseInt(args[++i], 10)
        break
      case '--height':
        options.height = parseInt(args[++i], 10)
        break
    }
  }

  return options
}

/**
 * Wait for a specific duration
 */
function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms))
}

/**
 * Capture frames from a specific mode
 */
async function captureMode(page, mode, options, outputDir) {
  const { url, frames, interval, crop } = options
  const modeDir = path.join(outputDir, mode)
  await fs.mkdir(modeDir, { recursive: true })

  // Get crop bounds if cropping is enabled
  const cropBounds = crop ? focalConfig.getCropBounds() : null

  // Navigate to the overlay mode
  const targetUrl = `${url}?overlay=${mode}${mode === 'live' ? '&auto=true' : ''}`
  console.log(`    Loading: ${targetUrl}`)

  await page.goto(targetUrl, { waitUntil: 'networkidle0', timeout: 30000 })

  // Wait for page to fully render
  await sleep(1000)

  // For live mode, wait for animation to start
  if (mode === 'live') {
    console.log('    Waiting for animation to trigger...')

    // Try to trigger via global function
    await page.evaluate(() => {
      if (typeof window.__triggerElectricity === 'function') {
        window.__triggerElectricity()
      }
    })

    // Wait for animation to reach peak phase (~1 second into animation)
    await sleep(1200)
  } else {
    // Reference mode - APNG starts immediately, wait for it to be visible
    await sleep(500)
  }

  // Hide the mode indicator for clean captures
  await page.evaluate(() => {
    const indicator = document.getElementById('overlay-mode-indicator')
    if (indicator) indicator.style.display = 'none'
  })

  // Capture frames
  const cropInfo = crop ? ` (cropped to ${cropBounds.width}x${cropBounds.height})` : ' (full page)'
  console.log(`    Capturing ${frames} frames${cropInfo}...`)
  const capturedFrames = []

  for (let i = 0; i < frames; i++) {
    const frameNum = String(i).padStart(3, '0')
    const framePath = path.join(modeDir, `frame-${frameNum}.png`)

    // Screenshot options
    const screenshotOptions = {
      path: framePath,
      type: 'png',
      fullPage: false,
    }

    // Add clip region if cropping
    if (cropBounds) {
      screenshotOptions.clip = {
        x: cropBounds.x,
        y: cropBounds.y,
        width: cropBounds.width,
        height: cropBounds.height,
      }
    }

    await page.screenshot(screenshotOptions)

    capturedFrames.push(framePath)

    if ((i + 1) % 5 === 0) {
      process.stdout.write(`\r    Progress: ${i + 1}/${frames}`)
    }

    if (i < frames - 1) {
      await sleep(interval)
    }
  }

  console.log(`\n    ✓ Captured ${frames} ${mode} frames`)

  return capturedFrames
}

/**
 * Load PNG from file
 */
async function loadPNG(filePath) {
  const buffer = await fs.readFile(filePath)
  return new Promise((resolve, reject) => {
    const png = new PNG()
    png.parse(buffer, (err, data) => {
      if (err) reject(err)
      else resolve(data)
    })
  })
}

/**
 * Check if a pixel is inside the circular mask
 * For cropped images, the center is at (width/2, height/2)
 */
function isInsideCircle(x, y, width, height, radius) {
  const centerX = width / 2
  const centerY = height / 2
  const dx = x - centerX
  const dy = y - centerY
  return (dx * dx + dy * dy) <= (radius * radius)
}

/**
 * Compare reference and live frames with circular masking
 * Only pixels inside the circular mask are compared
 */
async function compareFrames(options, outputDir) {
  const refDir = path.join(outputDir, 'reference')
  const liveDir = path.join(outputDir, 'live')
  const diffDir = path.join(outputDir, 'diff')

  await fs.mkdir(diffDir, { recursive: true })

  const refFrames = (await fs.readdir(refDir)).filter(f => f.endsWith('.png')).sort()
  const liveFrames = (await fs.readdir(liveDir)).filter(f => f.endsWith('.png')).sort()

  const frameCount = Math.min(refFrames.length, liveFrames.length)

  // Get circular mask info if cropping is enabled
  const cropBounds = options.crop ? focalConfig.getCropBounds() : null
  const useCircularMask = cropBounds?.isCircular && cropBounds?.circleRadius
  const maskRadius = cropBounds?.circleRadius || 0

  if (useCircularMask) {
    console.log(`  Comparing ${frameCount} frames with circular mask (r=${maskRadius}px)...`)
  } else {
    console.log(`  Comparing ${frameCount} frame pairs...`)
  }

  const results = []
  let totalDiffPixels = 0
  let totalPixels = 0

  for (let i = 0; i < frameCount; i++) {
    const refPath = path.join(refDir, refFrames[i])
    const livePath = path.join(liveDir, liveFrames[i])
    const diffPath = path.join(diffDir, `diff-${String(i).padStart(3, '0')}.png`)

    try {
      const refPng = await loadPNG(refPath)
      const livePng = await loadPNG(livePath)

      if (refPng.width !== livePng.width || refPng.height !== livePng.height) {
        results.push({
          frame: i,
          error: `Size mismatch: ref(${refPng.width}x${refPng.height}) vs live(${livePng.width}x${livePng.height})`,
          match: 0,
        })
        continue
      }

      const { width, height } = refPng
      const diff = new PNG({ width, height })

      // Run pixelmatch to get diff image
      pixelmatch(
        refPng.data,
        livePng.data,
        diff.data,
        width,
        height,
        { threshold: 0.1, includeAA: false }
      )

      // Count diff pixels only within the circular mask
      let frameDiffPixels = 0
      let framePixels = 0

      for (let y = 0; y < height; y++) {
        for (let x = 0; x < width; x++) {
          // Check if pixel is inside the circular mask
          const inMask = useCircularMask
            ? isInsideCircle(x, y, width, height, maskRadius)
            : true

          if (inMask) {
            framePixels++

            // Check if this pixel differs (diff image has non-zero RGB for differences)
            const idx = (y * width + x) * 4
            const diffR = diff.data[idx]
            const diffG = diff.data[idx + 1]
            const diffB = diff.data[idx + 2]

            // Pixelmatch marks differences with colored pixels (typically magenta)
            if (diffR > 0 || diffG > 0 || diffB > 0) {
              frameDiffPixels++
            }
          } else {
            // Outside mask - make diff image transparent/dark to show mask
            const idx = (y * width + x) * 4
            diff.data[idx] = 30     // Dark R
            diff.data[idx + 1] = 30 // Dark G
            diff.data[idx + 2] = 30 // Dark B
            diff.data[idx + 3] = 255 // Opaque
          }
        }
      }

      const matchPercent = framePixels > 0
        ? ((framePixels - frameDiffPixels) / framePixels) * 100
        : 0

      totalDiffPixels += frameDiffPixels
      totalPixels += framePixels

      // Save diff image
      const diffBuffer = PNG.sync.write(diff)
      await fs.writeFile(diffPath, diffBuffer)

      results.push({
        frame: i,
        match: matchPercent,
        diffPixels: frameDiffPixels,
        totalPixels: framePixels,
      })

      if ((i + 1) % 5 === 0) {
        process.stdout.write(`\r  Progress: ${i + 1}/${frameCount}`)
      }

    } catch (err) {
      results.push({
        frame: i,
        error: err.message,
        match: 0,
      })
    }
  }

  console.log('\n')

  // Calculate overall score
  const overallMatch = totalPixels > 0
    ? ((totalPixels - totalDiffPixels) / totalPixels) * 100
    : 0

  const validResults = results.filter(r => !r.error)
  const avgMatch = validResults.length > 0
    ? validResults.reduce((a, r) => a + r.match, 0) / validResults.length
    : 0

  return {
    frameCount,
    overallMatch,
    avgMatch,
    totalDiffPixels,
    totalPixels,
    results,
    usedCircularMask: useCircularMask,
    maskRadius,
  }
}

/**
 * Generate markdown report
 */
function generateReport(iteration, comparison, options) {
  const { frameCount, overallMatch, avgMatch, results } = comparison

  // Determine quality level
  let quality = 'POOR'
  let color = '🔴'
  if (overallMatch >= 95) {
    quality = 'EXCELLENT'
    color = '🟢'
  } else if (overallMatch >= 85) {
    quality = 'GOOD'
    color = '🟡'
  } else if (overallMatch >= 70) {
    quality = 'FAIR'
    color = '🟠'
  }

  // Find worst frames
  const sortedResults = [...results].filter(r => !r.error).sort((a, b) => a.match - b.match)
  const worstFrames = sortedResults.slice(0, 5)
  const bestFrames = sortedResults.slice(-5).reverse()

  return `# Overlay Visual Comparison - Iteration ${iteration}

**Generated**: ${new Date().toISOString()}
**Method**: Full-page overlay comparison
**Frames Compared**: ${frameCount}

---

## Summary

| Metric | Value |
|--------|-------|
| **Overall Match** | ${color} ${overallMatch.toFixed(1)}% |
| **Average Frame Match** | ${avgMatch.toFixed(1)}% |
| **Quality Rating** | ${quality} |
| **Total Pixels Compared** | ${comparison.totalPixels.toLocaleString()} |
| **Different Pixels** | ${comparison.totalDiffPixels.toLocaleString()} |

---

## Interpretation

This comparison shows the difference between:
- **Reference**: The target APNG animation overlaid on the full UI
- **Live**: Your Canvas implementation overlaid on the full UI

Since the surrounding UI is identical in both captures, **all differences are in the animation area**.

${overallMatch >= 90 ? `
✅ **Excellent match!** The live animation closely matches the reference.
` : overallMatch >= 75 ? `
⚠️ **Good progress.** Some visual differences remain in the animation.
` : `
❌ **Significant differences.** The animation needs more work to match the reference.
`}

---

## Frame Analysis

### Worst Performing Frames
${worstFrames.map(r => `- Frame ${r.frame}: ${r.match.toFixed(1)}% match (${r.diffPixels.toLocaleString()} diff pixels)`).join('\n')}

### Best Performing Frames
${bestFrames.map(r => `- Frame ${r.frame}: ${r.match.toFixed(1)}% match`).join('\n')}

---

## All Frames

| Frame | Match % | Diff Pixels | Status |
|-------|---------|-------------|--------|
${results.map(r => {
  if (r.error) return `| ${r.frame} | ERROR | - | ${r.error} |`
  const status = r.match >= 95 ? '🟢' : r.match >= 85 ? '🟡' : r.match >= 70 ? '🟠' : '🔴'
  return `| ${r.frame} | ${r.match.toFixed(1)}% | ${r.diffPixels.toLocaleString()} | ${status} |`
}).join('\n')}

---

## Diff Images

Visual diff images saved to: \`docs/specs/overlay-frames/iteration-${iteration}/diff/\`

Pink/red pixels in diff images indicate areas of difference between reference and live.

---

OVERLAY_SCORE:${Math.round(overallMatch)}
`
}

/**
 * Main execution
 */
async function main() {
  const options = parseArgs()
  const { iteration, compareOnly, captureOnly } = options

  const outputDir = path.join(PROJECT_ROOT, options.output, `iteration-${iteration}`)

  console.log('═══════════════════════════════════════════════════════════')
  console.log('  Overlay Capture & Compare')
  console.log('═══════════════════════════════════════════════════════════')
  console.log(`  Iteration: ${iteration}`)
  console.log(`  Output: ${outputDir}`)
  console.log(`  Viewport: ${options.width}x${options.height}`)
  console.log('───────────────────────────────────────────────────────────')

  if (!compareOnly) {
    // Launch browser
    const browser = await puppeteer.launch({
      headless: true,
      args: ['--no-sandbox', '--disable-setuid-sandbox'],
    })

    try {
      const page = await browser.newPage()
      await page.setViewport({
        width: options.width,
        height: options.height,
        deviceScaleFactor: 1,
      })

      // Capture reference frames
      console.log('\n  [1/2] Capturing REFERENCE frames...')
      await captureMode(page, 'reference', options, outputDir)

      // Small delay between modes
      await sleep(1000)

      // Capture live frames
      console.log('\n  [2/2] Capturing LIVE frames...')
      await captureMode(page, 'live', options, outputDir)

    } finally {
      await browser.close()
    }

    console.log('\n  ✓ Capture complete')
  }

  if (!captureOnly) {
    // Compare frames
    console.log('\n  Comparing reference vs live...')
    const comparison = await compareFrames(options, outputDir)

    console.log('───────────────────────────────────────────────────────────')
    console.log(`  Overall Match: ${comparison.overallMatch.toFixed(1)}%`)
    console.log(`  Average Frame: ${comparison.avgMatch.toFixed(1)}%`)
    console.log('───────────────────────────────────────────────────────────')

    // Generate report
    const report = generateReport(iteration, comparison, options)
    const reportPath = path.join(PROJECT_ROOT, 'docs/specs', `TASK7-ITERATION-${iteration}-OVERLAY-DIFF.md`)
    await fs.writeFile(reportPath, report)
    console.log(`\n  ✓ Report: ${reportPath}`)

    // Output score for automation
    console.log(`\nOVERLAY_SCORE:${Math.round(comparison.overallMatch)}`)

    return comparison
  }
}

main()
  .then(() => {
    console.log('\n✓ Complete')
    process.exit(0)
  })
  .catch(err => {
    console.error('\n✗ Failed:', err.message)
    console.error(err.stack)
    process.exit(1)
  })
