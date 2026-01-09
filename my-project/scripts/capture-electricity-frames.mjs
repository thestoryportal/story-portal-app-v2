#!/usr/bin/env node
/**
 * Electricity Animation Frame Capture
 *
 * Captures frames from the electricity animation test harness for visual comparison.
 *
 * Usage:
 *   node scripts/capture-electricity-frames.mjs [options]
 *
 * Options:
 *   --iteration N     Iteration number for output naming (default: 1)
 *   --frames N        Number of frames to capture (default: 30)
 *   --interval N      Milliseconds between captures (default: 100)
 *   --delay N         Delay before starting capture in ms (default: 1000, captures PEAK phase)
 *   --url URL         Dev server URL (default: http://localhost:5173)
 *   --output DIR      Output directory (default: docs/specs/frames)
 *
 * Example:
 *   node scripts/capture-electricity-frames.mjs --iteration 2 --frames 20 --delay 1000
 */

import puppeteer from 'puppeteer'
import fs from 'fs/promises'
import path from 'path'
import { fileURLToPath } from 'url'

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const PROJECT_ROOT = path.resolve(__dirname, '..')

// Parse command line arguments
function parseArgs() {
  const args = process.argv.slice(2)
  const options = {
    iteration: 1,
    frames: 30,
    interval: 100,
    delay: 1000, // Start capture after BUILD phase (900ms) to catch PEAK
    url: 'http://localhost:5173',
    output: 'docs/specs/frames',
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
      case '--delay':
        options.delay = parseInt(args[++i], 10)
        break
      case '--url':
        options.url = args[++i]
        break
      case '--output':
        options.output = args[++i]
        break
    }
  }

  return options
}

async function captureFrames(options) {
  const {
    iteration,
    frames,
    interval,
    delay,
    url,
    output,
  } = options

  // Create output directory
  const outputDir = path.join(PROJECT_ROOT, output, `iteration-${iteration}`)
  await fs.mkdir(outputDir, { recursive: true })

  console.log('═══════════════════════════════════════════════════════')
  console.log('  Electricity Animation Frame Capture')
  console.log('═══════════════════════════════════════════════════════')
  console.log(`  Iteration: ${iteration}`)
  console.log(`  Frames: ${frames}`)
  console.log(`  Interval: ${interval}ms`)
  console.log(`  Delay: ${delay}ms (capture starts after BUILD phase)`)
  console.log(`  Output: ${outputDir}`)
  console.log('───────────────────────────────────────────────────────')

  // Launch browser
  const browser = await puppeteer.launch({
    headless: true,
    args: ['--no-sandbox', '--disable-setuid-sandbox'],
  })

  try {
    const page = await browser.newPage()

    // Set viewport to ensure consistent capture
    await page.setViewport({
      width: 800,
      height: 800,
      deviceScaleFactor: 1,
    })

    // Navigate to test harness
    const testUrl = `${url}?test=electricity&auto=true`
    console.log(`  Loading: ${testUrl}`)
    await page.goto(testUrl, { waitUntil: 'networkidle2' })

    // Wait for the capture target element
    await page.waitForSelector('#electricity-capture-target')
    console.log('  ✓ Test harness loaded')

    // Wait for animation to start
    await page.evaluate(() => {
      return new Promise((resolve) => {
        window.addEventListener('electricity-start', resolve, { once: true })
        // Fallback timeout
        setTimeout(resolve, 2000)
      })
    })
    console.log('  ✓ Animation started')

    // Wait for specified delay (to capture PEAK phase)
    console.log(`  Waiting ${delay}ms to reach PEAK phase...`)
    await new Promise(r => setTimeout(r, delay))

    // Get the capture target element
    const captureTarget = await page.$('#electricity-capture-target')
    if (!captureTarget) {
      throw new Error('Capture target element not found')
    }

    // Capture frames
    console.log(`  Capturing ${frames} frames...`)
    const capturedFrames = []

    for (let i = 0; i < frames; i++) {
      const frameNum = String(i).padStart(3, '0')
      const framePath = path.join(outputDir, `frame-${frameNum}.png`)

      // Capture the element (already correct size: 465x465)
      await captureTarget.screenshot({
        path: framePath,
        type: 'png',
      })

      capturedFrames.push(framePath)

      // Progress indicator
      if ((i + 1) % 5 === 0 || i === frames - 1) {
        process.stdout.write(`\r  Progress: ${i + 1}/${frames} frames`)
      }

      // Wait for next frame
      if (i < frames - 1) {
        await new Promise(r => setTimeout(r, interval))
      }
    }

    console.log('\n  ✓ Capture complete')

    // Write manifest
    const manifest = {
      iteration,
      timestamp: new Date().toISOString(),
      frameCount: frames,
      interval,
      delay,
      url: testUrl,
      frames: capturedFrames.map(f => path.basename(f)),
    }

    await fs.writeFile(
      path.join(outputDir, 'manifest.json'),
      JSON.stringify(manifest, null, 2)
    )

    console.log(`  ✓ Manifest written`)
    console.log('═══════════════════════════════════════════════════════')
    console.log(`  Output: ${outputDir}`)
    console.log('═══════════════════════════════════════════════════════')

    return { success: true, outputDir, manifest }

  } finally {
    await browser.close()
  }
}

// Main execution
const options = parseArgs()
captureFrames(options)
  .then(result => {
    if (result.success) {
      console.log('\n✓ Frame capture successful')
      process.exit(0)
    }
  })
  .catch(err => {
    console.error('\n✗ Frame capture failed:', err.message)
    process.exit(1)
  })
