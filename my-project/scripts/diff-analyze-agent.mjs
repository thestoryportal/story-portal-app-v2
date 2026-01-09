#!/usr/bin/env node
/**
 * Diff Analyze Agent Script
 *
 * Companion to diff-capture-agent.mjs for analyzing captured frames.
 * Compares live animation frames against reference frames.
 *
 * Features:
 * - Uses pixelmatch for per-pixel comparison
 * - Applies circular mask matching the inner portal ring
 * - Outputs diff images and similarity scores
 * - Summarizes results for agent consumption
 * - Returns structured feedback for iteration
 *
 * Usage:
 *   node scripts/diff-analyze-agent.mjs [options]
 *
 * Options:
 *   --live=DIR        Directory with live frames (default: ./capture-output/live)
 *   --reference=DIR   Directory with reference frames (default: ./capture-output/reference)
 *   --output=DIR      Output directory for diff images (default: ./diff-output)
 *   --threshold=N     Pixelmatch threshold 0-1 (default: 0.1)
 *   --target=N        Target similarity percentage (default: 95)
 */

import fs from 'fs/promises'
import path from 'path'
import { PNG } from 'pngjs'
import pixelmatch from 'pixelmatch'
import { createReadStream } from 'fs'
import { fileURLToPath } from 'url'

const __dirname = path.dirname(fileURLToPath(import.meta.url))

// Parse command line arguments
function parseArgs() {
  const args = process.argv.slice(2)
  const options = {
    live: './capture-output/live',
    reference: './capture-output/reference',
    output: './diff-output',
    threshold: 0.1,
    circularMask: true,
    target: 95,
  }

  for (const arg of args) {
    if (arg.startsWith('--live=')) {
      options.live = arg.split('=')[1]
    } else if (arg.startsWith('--reference=')) {
      options.reference = arg.split('=')[1]
    } else if (arg.startsWith('--output=')) {
      options.output = arg.split('=')[1]
    } else if (arg.startsWith('--threshold=')) {
      options.threshold = parseFloat(arg.split('=')[1])
    } else if (arg.startsWith('--target=')) {
      options.target = parseFloat(arg.split('=')[1])
    } else if (arg === '--no-circular-mask') {
      options.circularMask = false
    }
  }

  return options
}

// Load PNG file
async function loadPNG(filepath) {
  return new Promise((resolve, reject) => {
    const stream = createReadStream(filepath)
    const png = new PNG()
    stream
      .pipe(png)
      .on('parsed', () => resolve(png))
      .on('error', reject)
  })
}

// Save PNG file
async function savePNG(png, filepath) {
  return new Promise((resolve, reject) => {
    const buffer = PNG.sync.write(png)
    fs.writeFile(filepath, buffer)
      .then(resolve)
      .catch(reject)
  })
}

// Check if pixel is inside circular mask (for 465x465 cropped images)
function isInsideCircle(x, y, width, height) {
  const centerX = width / 2
  const centerY = height / 2
  // For 465x465 images, use ~68% radius to match the inner portal ring
  const radius = Math.min(width, height) * 0.34
  const dx = x - centerX
  const dy = y - centerY
  return (dx * dx + dy * dy) <= (radius * radius)
}

// Compare two images with optional circular mask
// v1.1 FIX: Compare source images directly instead of checking pixelmatch diff output
// (pixelmatch doesn't output black for matching pixels, so old approach always gave 0%)
function compareImages(img1, img2, options = {}) {
  const { width, height } = img1
  const diff = new PNG({ width, height })

  // Get pixelmatch diff count
  const rawDiff = pixelmatch(
    img1.data,
    img2.data,
    diff.data,
    width,
    height,
    { threshold: options.threshold || 0.1 }
  )

  // Calculate masked comparison by comparing source images directly
  let totalMaskedPixels = 0
  let maskedDiffSum = 0
  const DIFF_THRESHOLD = 25 // Pixel difference threshold

  if (options.circularMask) {
    for (let y = 0; y < height; y++) {
      for (let x = 0; x < width; x++) {
        const idx = (y * width + x) * 4
        const inMask = isInsideCircle(x, y, width, height)

        if (inMask) {
          totalMaskedPixels++
          // Compare source images directly (not the diff output)
          const dr = Math.abs(img1.data[idx] - img2.data[idx])
          const dg = Math.abs(img1.data[idx + 1] - img2.data[idx + 1])
          const db = Math.abs(img1.data[idx + 2] - img2.data[idx + 2])
          const avgDiff = (dr + dg + db) / 3
          // Accumulate normalized difference (0-1 scale)
          maskedDiffSum += avgDiff / 255
        } else {
          // Darken outside mask in diff image
          diff.data[idx] = 30
          diff.data[idx + 1] = 30
          diff.data[idx + 2] = 30
          diff.data[idx + 3] = 255
        }
      }
    }
  }

  const totalPixels = width * height
  const rawSimilarity = 1 - (rawDiff / totalPixels)
  // Calculate similarity as 1 - average normalized difference
  const maskedSimilarity = options.circularMask && totalMaskedPixels > 0
    ? 1 - (maskedDiffSum / totalMaskedPixels)
    : rawSimilarity

  return {
    diff,
    rawDiffPixels: rawDiff,
    maskedDiffPixels: Math.round(maskedDiffSum * totalMaskedPixels), // Approximate for reporting
    totalPixels,
    totalMaskedPixels,
    rawSimilarity,
    maskedSimilarity,
    width,
    height,
  }
}

// Main analysis function
async function analyzeFrames(options) {
  console.log('=== DIFF ANALYSIS AGENT ===')
  console.log(`Options: ${JSON.stringify(options, null, 2)}`)

  // Create output directory
  const outputDir = path.resolve(options.output)
  await fs.mkdir(outputDir, { recursive: true })

  // Load reference frames
  const refDir = path.resolve(options.reference)
  let refFrameFiles
  try {
    const files = await fs.readdir(refDir)
    refFrameFiles = files
      .filter(f => f.startsWith('frame_') && f.endsWith('.png'))
      .sort()
    console.log(`Found ${refFrameFiles.length} reference frames in ${refDir}`)
  } catch (err) {
    console.error(`Failed to read reference frames: ${err.message}`)
    return { success: false, error: 'Reference frames directory not found' }
  }

  // Load live frames
  const liveDir = path.resolve(options.live)
  let liveFrameFiles
  try {
    const files = await fs.readdir(liveDir)
    liveFrameFiles = files
      .filter(f => f.startsWith('frame_') && f.endsWith('.png'))
      .sort()
    console.log(`Found ${liveFrameFiles.length} live frames in ${liveDir}`)
  } catch (err) {
    console.error(`Failed to read live frames: ${err.message}`)
    return { success: false, error: 'Live frames directory not found' }
  }

  if (refFrameFiles.length === 0) {
    return { success: false, error: 'No reference frames found' }
  }

  if (liveFrameFiles.length === 0) {
    return { success: false, error: 'No live frames found' }
  }

  // Use minimum frame count for comparison
  const frameCount = Math.min(refFrameFiles.length, liveFrameFiles.length)
  console.log(`\nComparing ${frameCount} frame pairs...`)

  // Analyze each frame pair
  const results = []
  let totalSimilarity = 0

  for (let i = 0; i < frameCount; i++) {
    const refFile = refFrameFiles[i]
    const liveFile = liveFrameFiles[i]
    const refPath = path.join(refDir, refFile)
    const livePath = path.join(liveDir, liveFile)

    console.log(`\nAnalyzing frame ${i + 1}/${frameCount}: ${refFile} vs ${liveFile}`)

    try {
      const refImage = await loadPNG(refPath)
      const liveImage = await loadPNG(livePath)

      // Check dimensions
      if (refImage.width !== liveImage.width || refImage.height !== liveImage.height) {
        console.warn(`  Dimension mismatch: ref=${refImage.width}x${refImage.height} vs live=${liveImage.width}x${liveImage.height}`)
        continue
      }

      const comparison = compareImages(refImage, liveImage, {
        threshold: options.threshold,
        circularMask: options.circularMask,
      })

      // Save diff image
      const diffFilename = `diff_${String(i).padStart(4, '0')}.png`
      const diffPath = path.join(outputDir, diffFilename)
      await savePNG(comparison.diff, diffPath)

      const result = {
        index: i,
        refFrame: refFile,
        liveFrame: liveFile,
        rawSimilarity: comparison.rawSimilarity,
        maskedSimilarity: comparison.maskedSimilarity,
        diffPixels: comparison.maskedDiffPixels,
        totalMaskedPixels: comparison.totalMaskedPixels,
        diffImage: diffFilename,
      }

      results.push(result)
      totalSimilarity += comparison.maskedSimilarity

      const simPercent = (comparison.maskedSimilarity * 100).toFixed(2)
      const rawPercent = (comparison.rawSimilarity * 100).toFixed(2)
      console.log(`  Similarity: ${simPercent}% (masked), ${rawPercent}% (raw)`)
    } catch (err) {
      console.error(`  Error analyzing frame ${i}: ${err.message}`)
    }
  }

  if (results.length === 0) {
    return { success: false, error: 'No frames could be analyzed' }
  }

  // Calculate summary statistics
  const avgSimilarity = totalSimilarity / results.length
  const minSimilarity = Math.min(...results.map(r => r.maskedSimilarity))
  const maxSimilarity = Math.max(...results.map(r => r.maskedSimilarity))
  const score = Math.round(avgSimilarity * 100)
  const targetMet = score >= options.target

  // Find worst frames for feedback
  const sortedByWorst = [...results].sort((a, b) => a.maskedSimilarity - b.maskedSimilarity)
  const worstFrames = sortedByWorst.slice(0, 3)

  const summary = {
    analyzedAt: new Date().toISOString(),
    options,
    frameCount: results.length,
    averageSimilarity: avgSimilarity,
    minSimilarity,
    maxSimilarity,
    score,
    targetScore: options.target,
    targetMet,
    worstFrames: worstFrames.map(f => ({
      index: f.index,
      similarity: (f.maskedSimilarity * 100).toFixed(2) + '%',
      diffImage: f.diffImage,
    })),
    results,
  }

  // Write summary
  const summaryPath = path.join(outputDir, 'analysis-summary.json')
  await fs.writeFile(summaryPath, JSON.stringify(summary, null, 2))

  // Print final summary
  console.log('\n' + '='.repeat(50))
  console.log('=== ANALYSIS SUMMARY ===')
  console.log('='.repeat(50))
  console.log(`Frames analyzed: ${results.length}`)
  console.log(`Average similarity: ${(avgSimilarity * 100).toFixed(2)}%`)
  console.log(`Min similarity: ${(minSimilarity * 100).toFixed(2)}%`)
  console.log(`Max similarity: ${(maxSimilarity * 100).toFixed(2)}%`)
  console.log(`\n>>> SCORE: ${score}/100 <<<`)
  console.log(`Target: ${options.target}%`)
  console.log(`Status: ${targetMet ? '✓ TARGET MET!' : '✗ Below target - iteration needed'}`)

  if (!targetMet) {
    console.log('\nWorst performing frames:')
    worstFrames.forEach(f => {
      console.log(`  - Frame ${f.index}: ${(f.maskedSimilarity * 100).toFixed(2)}% (see ${f.diffImage})`)
    })
  }

  console.log(`\nSummary written to: ${summaryPath}`)
  console.log(`Diff images written to: ${outputDir}`)

  return { success: true, summary, targetMet }
}

// Run analysis
const options = parseArgs()
analyzeFrames(options)
  .then(result => {
    if (result.success) {
      console.log('\n✓ Analysis completed successfully!')
      // Exit with code 0 if target met, 2 if below target (for iteration workflow)
      process.exit(result.targetMet ? 0 : 2)
    } else {
      console.error('\n✗ Analysis failed:', result.error)
      process.exit(1)
    }
  })
  .catch(err => {
    console.error('Analysis error:', err)
    process.exit(1)
  })
