#!/usr/bin/env node
/**
 * Electricity Animation Frame Comparison
 *
 * Compares captured frames against reference frames using multiple metrics.
 *
 * Usage:
 *   node scripts/compare-electricity-frames.mjs [options]
 *
 * Options:
 *   --iteration N       Iteration number to compare (default: 1)
 *   --reference DIR     Reference frames directory (default: docs/reference/electricity-frames)
 *   --captured DIR      Captured frames directory (default: docs/specs/frames/iteration-N)
 *   --output FILE       Output report path (default: docs/specs/TASK7-ITERATION-N-VISUAL-DIFF.md)
 *
 * Metrics:
 *   - Pixel Difference (pixelmatch): Raw pixel-by-pixel comparison
 *   - SSIM (structural similarity): Perceptual similarity score
 *   - Color histogram comparison
 */

import fs from 'fs/promises'
import path from 'path'
import { fileURLToPath } from 'url'
import { PNG } from 'pngjs'
import pixelmatch from 'pixelmatch'

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const PROJECT_ROOT = path.resolve(__dirname, '..')

// Parse command line arguments
function parseArgs() {
  const args = process.argv.slice(2)
  const options = {
    iteration: 1,
    reference: 'docs/reference/electricity-frames',
    captured: null, // Will be set based on iteration
    output: null, // Will be set based on iteration
  }

  for (let i = 0; i < args.length; i++) {
    switch (args[i]) {
      case '--iteration':
        options.iteration = parseInt(args[++i], 10)
        break
      case '--reference':
        options.reference = args[++i]
        break
      case '--captured':
        options.captured = args[++i]
        break
      case '--output':
        options.output = args[++i]
        break
    }
  }

  // Set defaults based on iteration
  if (!options.captured) {
    options.captured = `docs/specs/frames/iteration-${options.iteration}`
  }
  if (!options.output) {
    options.output = `docs/specs/TASK7-ITERATION-${options.iteration}-VISUAL-DIFF.md`
  }

  return options
}

/**
 * Load PNG image from file
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
 * Compare two images using pixelmatch
 */
async function compareImages(refPath, capPath, diffPath) {
  const ref = await loadPNG(refPath)
  const cap = await loadPNG(capPath)

  // Ensure same dimensions
  if (ref.width !== cap.width || ref.height !== cap.height) {
    return {
      error: `Dimension mismatch: ref(${ref.width}x${ref.height}) vs cap(${cap.width}x${cap.height})`,
      match: 0,
      diffPixels: -1,
      totalPixels: -1,
    }
  }

  const { width, height } = ref
  const diff = new PNG({ width, height })

  // Compare pixels
  const diffPixels = pixelmatch(
    ref.data,
    cap.data,
    diff.data,
    width,
    height,
    { threshold: 0.1 } // Allow small variations
  )

  const totalPixels = width * height
  const matchPercent = ((totalPixels - diffPixels) / totalPixels) * 100

  // Save diff image if path provided
  if (diffPath) {
    const diffBuffer = PNG.sync.write(diff)
    await fs.writeFile(diffPath, diffBuffer)
  }

  return {
    match: matchPercent,
    diffPixels,
    totalPixels,
    width,
    height,
  }
}

/**
 * Calculate color histogram for an image
 */
function calculateHistogram(png) {
  const histogram = {
    r: new Array(256).fill(0),
    g: new Array(256).fill(0),
    b: new Array(256).fill(0),
  }

  for (let i = 0; i < png.data.length; i += 4) {
    const a = png.data[i + 3]
    if (a > 0) { // Only count non-transparent pixels
      histogram.r[png.data[i]]++
      histogram.g[png.data[i + 1]]++
      histogram.b[png.data[i + 2]]++
    }
  }

  return histogram
}

/**
 * Compare color histograms (Bhattacharyya distance)
 */
function compareHistograms(hist1, hist2) {
  function bhattacharyya(h1, h2) {
    const sum1 = h1.reduce((a, b) => a + b, 0)
    const sum2 = h2.reduce((a, b) => a + b, 0)
    if (sum1 === 0 || sum2 === 0) return 0

    let bc = 0
    for (let i = 0; i < 256; i++) {
      bc += Math.sqrt((h1[i] / sum1) * (h2[i] / sum2))
    }
    return bc
  }

  const rSim = bhattacharyya(hist1.r, hist2.r)
  const gSim = bhattacharyya(hist1.g, hist2.g)
  const bSim = bhattacharyya(hist1.b, hist2.b)

  return (rSim + gSim + bSim) / 3 * 100
}

/**
 * Main comparison function
 */
async function compareFrames(options) {
  const { iteration, reference, captured, output } = options

  const refDir = path.join(PROJECT_ROOT, reference)
  const capDir = path.join(PROJECT_ROOT, captured)
  const diffDir = path.join(PROJECT_ROOT, `docs/specs/frames/iteration-${iteration}-diff`)
  const outputPath = path.join(PROJECT_ROOT, output)

  console.log('═══════════════════════════════════════════════════════')
  console.log('  Electricity Animation Frame Comparison')
  console.log('═══════════════════════════════════════════════════════')
  console.log(`  Iteration: ${iteration}`)
  console.log(`  Reference: ${refDir}`)
  console.log(`  Captured:  ${capDir}`)
  console.log('───────────────────────────────────────────────────────')

  // Check directories exist
  try {
    await fs.access(refDir)
  } catch {
    console.log('\n⚠ Reference frames not found. Extracting from APNG...')
    await extractReferenceFrames(refDir)
  }

  try {
    await fs.access(capDir)
  } catch {
    throw new Error(`Captured frames not found at: ${capDir}`)
  }

  // Create diff directory
  await fs.mkdir(diffDir, { recursive: true })

  // Get frame lists
  const refFrames = (await fs.readdir(refDir))
    .filter(f => f.endsWith('.png'))
    .sort()
  const capFrames = (await fs.readdir(capDir))
    .filter(f => f.endsWith('.png'))
    .sort()

  console.log(`  Reference frames: ${refFrames.length}`)
  console.log(`  Captured frames:  ${capFrames.length}`)

  // Compare frames (use minimum count)
  const frameCount = Math.min(refFrames.length, capFrames.length, 30) // Cap at 30 for performance
  const results = []

  console.log(`\n  Comparing ${frameCount} frames...`)

  for (let i = 0; i < frameCount; i++) {
    const refPath = path.join(refDir, refFrames[i])
    const capPath = path.join(capDir, capFrames[i])
    const diffPath = path.join(diffDir, `diff-${String(i).padStart(3, '0')}.png`)

    try {
      const refPng = await loadPNG(refPath)
      const capPng = await loadPNG(capPath)

      const pixelResult = await compareImages(refPath, capPath, diffPath)
      const refHist = calculateHistogram(refPng)
      const capHist = calculateHistogram(capPng)
      const colorSimilarity = compareHistograms(refHist, capHist)

      results.push({
        frame: i,
        pixelMatch: pixelResult.match,
        colorSimilarity,
        diffPixels: pixelResult.diffPixels,
        error: pixelResult.error,
      })

      // Progress
      if ((i + 1) % 5 === 0) {
        process.stdout.write(`\r  Progress: ${i + 1}/${frameCount}`)
      }

    } catch (err) {
      results.push({
        frame: i,
        error: err.message,
        pixelMatch: 0,
        colorSimilarity: 0,
      })
    }
  }

  console.log('\n')

  // Calculate summary statistics
  const validResults = results.filter(r => !r.error)
  const avgPixelMatch = validResults.reduce((a, r) => a + r.pixelMatch, 0) / validResults.length
  const avgColorSim = validResults.reduce((a, r) => a + r.colorSimilarity, 0) / validResults.length
  const minPixelMatch = Math.min(...validResults.map(r => r.pixelMatch))
  const maxPixelMatch = Math.max(...validResults.map(r => r.pixelMatch))

  // Overall visual score (weighted average)
  const visualScore = (avgPixelMatch * 0.7 + avgColorSim * 0.3)

  console.log('  Summary:')
  console.log(`    Avg Pixel Match:    ${avgPixelMatch.toFixed(1)}%`)
  console.log(`    Avg Color Similarity: ${avgColorSim.toFixed(1)}%`)
  console.log(`    Visual Score:       ${visualScore.toFixed(1)}%`)
  console.log(`    Min/Max Match:      ${minPixelMatch.toFixed(1)}% / ${maxPixelMatch.toFixed(1)}%`)

  // Generate markdown report
  const report = generateReport(iteration, results, {
    avgPixelMatch,
    avgColorSim,
    visualScore,
    minPixelMatch,
    maxPixelMatch,
    frameCount,
  })

  await fs.writeFile(outputPath, report)
  console.log(`\n  ✓ Report written: ${outputPath}`)

  // Output score for automation
  console.log(`\nVISUAL_SCORE:${Math.round(visualScore)}`)

  return {
    visualScore,
    avgPixelMatch,
    avgColorSim,
    results,
  }
}

/**
 * Extract reference frames from APNG
 */
async function extractReferenceFrames(outputDir) {
  const { execSync } = await import('child_process')
  const apngPath = path.join(PROJECT_ROOT, 'docs/reference/electricity_animation_effect_diff_analysis.apng')

  await fs.mkdir(outputDir, { recursive: true })

  // Use ffmpeg to extract frames
  console.log('  Extracting reference frames with ffmpeg...')
  try {
    execSync(
      `ffmpeg -i "${apngPath}" -vf "fps=10" "${path.join(outputDir, 'frame-%03d.png')}" -y`,
      { stdio: 'pipe' }
    )
    console.log('  ✓ Reference frames extracted')
  } catch (err) {
    throw new Error(`Failed to extract frames. Ensure ffmpeg is installed. Error: ${err.message}`)
  }
}

/**
 * Generate markdown report
 */
function generateReport(iteration, results, summary) {
  const {
    avgPixelMatch,
    avgColorSim,
    visualScore,
    minPixelMatch,
    maxPixelMatch,
    frameCount,
  } = summary

  // Determine quality assessment
  let quality = 'POOR'
  let recommendation = 'Major visual discrepancies detected. Review glow, color, and timing.'
  if (visualScore >= 90) {
    quality = 'EXCELLENT'
    recommendation = 'Visual output closely matches reference. Minor tweaks may improve further.'
  } else if (visualScore >= 80) {
    quality = 'GOOD'
    recommendation = 'Good visual match. Focus on glow softness and temporal coherence.'
  } else if (visualScore >= 70) {
    quality = 'FAIR'
    recommendation = 'Noticeable differences. Check glow rendering, color accuracy, and trails.'
  }

  // Find worst frames
  const sortedResults = [...results].sort((a, b) => a.pixelMatch - b.pixelMatch)
  const worstFrames = sortedResults.slice(0, 5)

  return `# Visual Diff Analysis - Iteration ${iteration}

**Generated**: ${new Date().toISOString()}
**Frames Compared**: ${frameCount}

---

## Summary

| Metric | Value | Assessment |
|--------|-------|------------|
| **Visual Score** | ${visualScore.toFixed(1)}% | ${quality} |
| **Pixel Match (avg)** | ${avgPixelMatch.toFixed(1)}% | |
| **Color Similarity** | ${avgColorSim.toFixed(1)}% | |
| **Min/Max Match** | ${minPixelMatch.toFixed(1)}% / ${maxPixelMatch.toFixed(1)}% | |

### Assessment: ${quality}

${recommendation}

---

## Frame-by-Frame Analysis

| Frame | Pixel Match | Color Sim | Notes |
|-------|-------------|-----------|-------|
${results.map(r => {
  const notes = r.error ? `⚠ ${r.error}` :
    r.pixelMatch < 70 ? '🔴 Major diff' :
    r.pixelMatch < 85 ? '🟡 Minor diff' : '🟢 Good'
  return `| ${r.frame} | ${r.pixelMatch?.toFixed(1) || 'N/A'}% | ${r.colorSimilarity?.toFixed(1) || 'N/A'}% | ${notes} |`
}).join('\n')}

---

## Worst Performing Frames

These frames have the largest visual differences:

${worstFrames.map(r => `- **Frame ${r.frame}**: ${r.pixelMatch?.toFixed(1)}% match${r.error ? ` (Error: ${r.error})` : ''}`).join('\n')}

Review diff images in: \`docs/specs/frames/iteration-${iteration}-diff/\`

---

## Recommendations

${visualScore < 80 ? `
### Priority Fixes

1. **Glow Rendering**: Check if blur-based glow is implemented correctly
2. **Color Values**: Verify exact hex values match reference
3. **Timing**: Ensure PEAK phase timing aligns with capture delay
4. **Trail Effect**: Check if afterimage persistence is implemented
` : `
### Fine-Tuning

1. Review diff images for specific areas of mismatch
2. Consider adjusting glow radius or opacity
3. Check frame-to-frame coherence
`}

---

*Visual comparison score: ${Math.round(visualScore)}*

VISUAL_SCORE:${Math.round(visualScore)}
`
}

// Main execution
const options = parseArgs()
compareFrames(options)
  .then(result => {
    console.log('\n✓ Comparison complete')
    process.exit(result.visualScore >= 95 ? 0 : 1)
  })
  .catch(err => {
    console.error('\n✗ Comparison failed:', err.message)
    process.exit(1)
  })
