#!/usr/bin/env node
/**
 * Quick Preview Integration v1.0
 *
 * Instant visual feedback for code changes (<1 second).
 * Allows agents to test multiple approaches per iteration.
 *
 * Usage:
 *   node scripts/quick-preview.mjs
 *
 * Features:
 * - Fast 3-frame capture
 * - Quick SSIM comparison
 * - Go/No-Go decision support
 * - Visual side-by-side diff
 */

import { spawn } from 'child_process'
import fs from 'fs/promises'
import path from 'path'
import pixelmatch from 'pixelmatch'
import { PNG } from 'pngjs'
import { createReadStream } from 'fs'

const CONFIG = {
  port: 5173,
  frames: 3,
  cropSize: 465,
  frameDelay: 50,
  outputDir: './quick-preview-output'
}

/**
 * Load PNG
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
 * Quick capture (3 frames)
 */
async function quickCapture() {
  console.log('[Quick Preview] Capturing 3 frames...')

  const captureScript = path.resolve('./scripts/diff-capture-agent.mjs')

  return new Promise((resolve, reject) => {
    const proc = spawn('node', [
      captureScript,
      '--mode=live',
      `--output=${CONFIG.outputDir}`,
      `--port=${CONFIG.port}`,
      `--frames=${CONFIG.frames}`,
      `--crop-size=${CONFIG.cropSize}`,
      `--frame-delay=${CONFIG.frameDelay}`,
      '--wait=500' // Faster wait
    ], { stdio: 'inherit' })

    proc.on('close', code => {
      if (code === 0) resolve()
      else reject(new Error(`Capture failed with code ${code}`))
    })
  })
}

/**
 * Quick SSIM comparison
 */
async function quickCompare(liveDir, referenceDir) {
  console.log('[Quick Preview] Comparing frames...')

  const liveFiles = (await fs.readdir(liveDir))
    .filter(f => f.startsWith('frame_') && f.endsWith('.png'))
    .sort()

  const refFiles = (await fs.readdir(referenceDir))
    .filter(f => f.startsWith('frame_') && f.endsWith('.png'))
    .sort()

  const frameCount = Math.min(liveFiles.length, refFiles.length, CONFIG.frames)
  let totalSimilarity = 0

  for (let i = 0; i < frameCount; i++) {
    const livePath = path.join(liveDir, liveFiles[i])
    const refPath = path.join(referenceDir, refFiles[i])

    const liveImage = await loadPNG(livePath)
    const refImage = await loadPNG(refPath)

    const { width, height } = liveImage
    const diff = new PNG({ width, height })

    const diffPixels = pixelmatch(
      refImage.data,
      liveImage.data,
      diff.data,
      width,
      height,
      { threshold: 0.1 }
    )

    const similarity = 1 - (diffPixels / (width * height))
    totalSimilarity += similarity
  }

  const avgSimilarity = totalSimilarity / frameCount
  const score = Math.round(avgSimilarity * 100)

  return { score, frameCount }
}

/**
 * Main quick preview function
 */
async function runQuickPreview() {
  console.log('═══════════════════════════════════════════')
  console.log('  QUICK PREVIEW - Instant Feedback')
  console.log('═══════════════════════════════════════════\n')

  const startTime = Date.now()

  try {
    // Ensure output dir exists
    await fs.mkdir(CONFIG.outputDir, { recursive: true })

    // Quick capture
    await quickCapture()

    // Quick compare
    const liveDir = path.join(CONFIG.outputDir, 'live')
    const referenceDir = './capture-output/reference' // Assumes reference exists

    const result = await quickCompare(liveDir, referenceDir)

    const elapsed = ((Date.now() - startTime) / 1000).toFixed(1)

    console.log('\n═══════════════════════════════════════════')
    console.log(`  QUICK SCORE: ${result.score}/100`)
    console.log(`  Time: ${elapsed}s`)
    console.log('═══════════════════════════════════════════\n')

    // Decision guidance
    if (result.score >= 85) {
      console.log('✅ LOOKS GOOD - Consider committing this change')
    } else if (result.score >= 70) {
      console.log('⚠️  MARGINAL - Review carefully before committing')
    } else {
      console.log('❌ LOOKS WORSE - Consider reverting this change')
    }

    console.log(`\nView preview: file://${path.resolve(CONFIG.outputDir)}/live/frame_0000.png\n`)

    return { success: true, score: result.score, elapsed: parseFloat(elapsed) }
  } catch (err) {
    console.error(`\n❌ Quick preview failed: ${err.message}`)
    return { success: false, error: err.message }
  }
}

// Run if called directly
if (process.argv[1] === new URL(import.meta.url).pathname) {
  runQuickPreview()
    .then(result => process.exit(result.success ? 0 : 1))
    .catch(err => {
      console.error(err)
      process.exit(1)
    })
}

export default { runQuickPreview }
