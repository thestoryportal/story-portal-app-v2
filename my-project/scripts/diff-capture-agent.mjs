#!/usr/bin/env node
/**
 * Diff Capture Agent Script
 *
 * Lightweight Puppeteer script designed for sub-agent execution.
 * Captures frames from the DiffCaptureTest page with pre-aligned layering.
 *
 * Features:
 * - Uses the new DiffCaptureTest page with masked portal ring
 * - Captures at peak intensity (lockAtPeak mode)
 * - Crops to 465x465 centered on the animation
 * - Outputs frame data for diff analysis
 *
 * Usage:
 *   node scripts/diff-capture-agent.mjs [options]
 *
 * Options:
 *   --frames=N       Number of frames to capture (default: 20)
 *   --output=DIR     Output directory (default: ./capture-output)
 *   --mode=MODE      'live', 'reference', or 'both' (default: 'live')
 *   --viewport=WxH   Viewport size (default: 1280x900)
 *   --wait=MS        Wait time for animation to reach peak (default: 2000)
 *   --crop-size=N    Size of cropped square (default: 465)
 *   --frame-delay=MS Delay between frame captures (default: 50)
 *
 * Workflow:
 *   1. First run: node scripts/diff-capture-agent.mjs --mode=reference
 *      - Captures reference APNG frames to ./capture-output/reference/
 *   2. Then run: node scripts/diff-capture-agent.mjs --mode=live
 *      - Captures live animation frames to ./capture-output/live/
 *   3. Finally: node scripts/diff-analyze-agent.mjs
 *      - Compares and outputs diff score
 */

import puppeteer from 'puppeteer'
import fs from 'fs/promises'
import path from 'path'
import { fileURLToPath } from 'url'

const __dirname = path.dirname(fileURLToPath(import.meta.url))

// Parse command line arguments
function parseArgs() {
  const args = process.argv.slice(2)
  const options = {
    frames: 20,
    output: './capture-output',
    mode: 'live',
    viewport: { width: 1280, height: 900 },
    wait: 2000,
    port: 5173,
    cropSize: 465,
    frameDelay: 50,
  }

  for (const arg of args) {
    if (arg.startsWith('--frames=')) {
      options.frames = parseInt(arg.split('=')[1], 10)
    } else if (arg.startsWith('--output=')) {
      options.output = arg.split('=')[1]
    } else if (arg.startsWith('--mode=')) {
      options.mode = arg.split('=')[1]
    } else if (arg.startsWith('--viewport=')) {
      const [w, h] = arg.split('=')[1].split('x').map(Number)
      options.viewport = { width: w, height: h }
    } else if (arg.startsWith('--wait=')) {
      options.wait = parseInt(arg.split('=')[1], 10)
    } else if (arg.startsWith('--port=')) {
      options.port = parseInt(arg.split('=')[1], 10)
    } else if (arg.startsWith('--crop-size=')) {
      options.cropSize = parseInt(arg.split('=')[1], 10)
    } else if (arg.startsWith('--frame-delay=')) {
      options.frameDelay = parseInt(arg.split('=')[1], 10)
    }
  }

  return options
}

// Calculate clip region for centered crop
function calculateClipRegion(viewport, cropSize) {
  const x = Math.floor((viewport.width - cropSize) / 2)
  const y = Math.floor((viewport.height - cropSize) / 2)
  return {
    x,
    y,
    width: cropSize,
    height: cropSize,
  }
}

// Main capture function for live animation
async function captureLiveFrames(options) {
  console.log('=== LIVE ANIMATION CAPTURE ===')
  console.log(`Options: ${JSON.stringify(options, null, 2)}`)

  // Create output directory
  const outputDir = path.resolve(options.output, 'live')
  await fs.mkdir(outputDir, { recursive: true })

  // Launch browser
  const browser = await puppeteer.launch({
    headless: 'new',
    args: ['--no-sandbox', '--disable-setuid-sandbox'],
  })

  const page = await browser.newPage()
  await page.setViewport(options.viewport)

  // Build URL with capture mode - settings will load from localStorage
  const url = `http://localhost:${options.port}/?diff=capture`
  console.log(`Navigating to: ${url}`)
  await page.goto(url, { waitUntil: 'networkidle0' })

  // Wait for the page to be ready
  await page.waitForFunction(() => {
    return window.__diffCapture !== undefined
  }, { timeout: 10000 })

  // Configure for live capture (settings persist from localStorage)
  await page.evaluate(() => {
    const ctrl = window.__diffCapture
    // Ensure lock at peak and live mode
    ctrl.setLockAtPeak(true)
    ctrl.setShowLive(true)
    ctrl.setShowReference(false)
    ctrl.setIsLooping(true)
    // Trigger the animation
    ctrl.triggerAnimation()
  })

  // Wait for animation to reach peak
  console.log(`Waiting ${options.wait}ms for animation to reach peak...`)
  await new Promise(r => setTimeout(r, options.wait))

  // Verify we're at peak
  const isPeak = await page.evaluate(() => window.__diffCapture.isReady())
  console.log(`Animation at peak: ${isPeak}`)

  // Calculate crop region
  const clip = calculateClipRegion(options.viewport, options.cropSize)
  console.log(`Crop region: ${JSON.stringify(clip)}`)

  // Capture frames
  const frames = []
  console.log(`\nCapturing ${options.frames} frames (${options.cropSize}x${options.cropSize})...`)

  for (let i = 0; i < options.frames; i++) {
    const timestamp = Date.now()
    const filename = `frame_${String(i).padStart(4, '0')}.png`
    const filepath = path.join(outputDir, filename)

    // Take cropped screenshot
    await page.screenshot({
      path: filepath,
      type: 'png',
      clip,
    })

    frames.push({
      index: i,
      filename,
      timestamp,
    })

    console.log(`  Captured: ${filename}`)

    // Wait between frames
    if (i < options.frames - 1) {
      await new Promise(r => setTimeout(r, options.frameDelay))
    }
  }

  // Write metadata
  const metadata = {
    capturedAt: new Date().toISOString(),
    type: 'live',
    options,
    frames,
    viewport: options.viewport,
    cropSize: options.cropSize,
    clip,
  }

  const metaPath = path.join(outputDir, 'capture-metadata.json')
  await fs.writeFile(metaPath, JSON.stringify(metadata, null, 2))
  console.log(`\nMetadata written to: ${metaPath}`)

  await browser.close()

  console.log(`\n✓ Live capture complete! ${frames.length} frames saved to ${outputDir}`)
  return { success: true, frames, outputDir }
}

// Reference frame extraction (captures APNG animation frames)
async function captureReferenceFrames(options) {
  console.log('=== REFERENCE ANIMATION CAPTURE ===')
  console.log(`Options: ${JSON.stringify(options, null, 2)}`)

  // Create output directory
  const outputDir = path.resolve(options.output, 'reference')
  await fs.mkdir(outputDir, { recursive: true })

  // Launch browser
  const browser = await puppeteer.launch({
    headless: 'new',
    args: ['--no-sandbox', '--disable-setuid-sandbox'],
  })

  const page = await browser.newPage()
  await page.setViewport(options.viewport)

  // Navigate to diff page
  const url = `http://localhost:${options.port}/?diff=capture`
  console.log(`Navigating to: ${url}`)
  await page.goto(url, { waitUntil: 'networkidle0' })

  // Wait for page to be ready
  await page.waitForFunction(() => {
    return window.__diffCapture !== undefined
  }, { timeout: 10000 })

  // Configure for reference only (settings persist from localStorage)
  await page.evaluate(() => {
    const ctrl = window.__diffCapture
    ctrl.setShowLive(false)
    ctrl.setShowReference(true)
  })

  // Wait for APNG to load and start animating
  console.log('Waiting for reference APNG to load...')
  await new Promise(r => setTimeout(r, 1000))

  // Calculate crop region
  const clip = calculateClipRegion(options.viewport, options.cropSize)
  console.log(`Crop region: ${JSON.stringify(clip)}`)

  // Capture frames from the APNG animation
  const frames = []
  console.log(`\nCapturing ${options.frames} reference frames (${options.cropSize}x${options.cropSize})...`)

  for (let i = 0; i < options.frames; i++) {
    const timestamp = Date.now()
    const filename = `frame_${String(i).padStart(4, '0')}.png`
    const filepath = path.join(outputDir, filename)

    // Take cropped screenshot
    await page.screenshot({
      path: filepath,
      type: 'png',
      clip,
    })

    frames.push({
      index: i,
      filename,
      timestamp,
    })

    console.log(`  Captured: ${filename}`)

    // Wait between frames to capture APNG animation
    if (i < options.frames - 1) {
      await new Promise(r => setTimeout(r, options.frameDelay))
    }
  }

  // Write metadata
  const metadata = {
    capturedAt: new Date().toISOString(),
    type: 'reference',
    options,
    frames,
    viewport: options.viewport,
    cropSize: options.cropSize,
    clip,
  }

  const metaPath = path.join(outputDir, 'capture-metadata.json')
  await fs.writeFile(metaPath, JSON.stringify(metadata, null, 2))
  console.log(`\nMetadata written to: ${metaPath}`)

  await browser.close()

  console.log(`\n✓ Reference capture complete! ${frames.length} frames saved to ${outputDir}`)
  return { success: true, frames, outputDir }
}

// Run the capture
const options = parseArgs()

async function main() {
  try {
    if (options.mode === 'reference') {
      const result = await captureReferenceFrames(options)
      console.log('\nReference extraction result:', result.success ? 'SUCCESS' : 'FAILED')
      process.exit(result.success ? 0 : 1)
    } else if (options.mode === 'live') {
      const result = await captureLiveFrames(options)
      console.log('\nLive capture result:', result.success ? 'SUCCESS' : 'FAILED')
      process.exit(result.success ? 0 : 1)
    } else if (options.mode === 'both') {
      // Capture reference first, then live
      console.log('Capturing both reference and live frames...\n')

      const refResult = await captureReferenceFrames(options)
      if (!refResult.success) {
        console.error('Reference capture failed')
        process.exit(1)
      }

      console.log('\n' + '='.repeat(50) + '\n')

      const liveResult = await captureLiveFrames(options)
      if (!liveResult.success) {
        console.error('Live capture failed')
        process.exit(1)
      }

      console.log('\n✓ Both captures complete!')
      process.exit(0)
    } else {
      console.error(`Unknown mode: ${options.mode}`)
      process.exit(1)
    }
  } catch (err) {
    console.error('Capture failed:', err)
    process.exit(1)
  }
}

main()
