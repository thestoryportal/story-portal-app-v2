#!/usr/bin/env node
/**
 * Extract Reference Frames from APNG
 *
 * Extracts frames from the reference electricity animation APNG
 * for use in visual comparison testing.
 *
 * Usage:
 *   node scripts/extract-reference-frames.mjs
 *
 * Requirements:
 *   - ffmpeg installed and in PATH
 */

import { execSync } from 'child_process'
import fs from 'fs/promises'
import path from 'path'
import { fileURLToPath } from 'url'

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const PROJECT_ROOT = path.resolve(__dirname, '..')

const APNG_PATH = path.join(PROJECT_ROOT, 'docs/reference/electricity_animation_effect_diff_analysis.apng')
const OUTPUT_DIR = path.join(PROJECT_ROOT, 'docs/reference/electricity-frames')

async function extractFrames() {
  console.log('═══════════════════════════════════════════════════════')
  console.log('  Reference Frame Extraction')
  console.log('═══════════════════════════════════════════════════════')

  // Check if APNG exists
  try {
    await fs.access(APNG_PATH)
    console.log(`  Source: ${APNG_PATH}`)
  } catch {
    console.error('✗ Reference APNG not found at:', APNG_PATH)
    process.exit(1)
  }

  // Create output directory
  await fs.mkdir(OUTPUT_DIR, { recursive: true })
  console.log(`  Output: ${OUTPUT_DIR}`)

  // Check for ffmpeg
  try {
    execSync('ffmpeg -version', { stdio: 'pipe' })
    console.log('  ✓ ffmpeg found')
  } catch {
    console.error('✗ ffmpeg not found. Please install ffmpeg.')
    console.error('  macOS: brew install ffmpeg')
    console.error('  Linux: apt install ffmpeg')
    process.exit(1)
  }

  // Extract frames at 10fps (30 frames from 3 second animation)
  // This gives us ~30 frames covering the full animation
  console.log('\n  Extracting frames...')

  try {
    // First, get info about the APNG
    const probeOutput = execSync(
      `ffprobe -v error -select_streams v:0 -show_entries stream=width,height,nb_frames -of csv=p=0 "${APNG_PATH}"`,
      { encoding: 'utf-8' }
    ).trim()

    const [width, height, totalFrames] = probeOutput.split(',')
    console.log(`  Source: ${width}x${height}, ${totalFrames} frames`)

    // Extract frames - use fps filter to get reasonable number
    // Reference is 128 frames at 30fps = 4.27s
    // We'll extract at 10fps to get ~42 frames, then use first 30
    execSync(
      `ffmpeg -y -i "${APNG_PATH}" -vf "fps=10" "${path.join(OUTPUT_DIR, 'frame-%03d.png')}"`,
      { stdio: 'pipe' }
    )

    // Count extracted frames
    const files = await fs.readdir(OUTPUT_DIR)
    const frameFiles = files.filter(f => f.startsWith('frame-') && f.endsWith('.png'))

    console.log(`  ✓ Extracted ${frameFiles.length} frames`)

    // Write manifest
    const manifest = {
      source: 'electricity_animation_effect_diff_analysis.apng',
      extractedAt: new Date().toISOString(),
      dimensions: { width: parseInt(width), height: parseInt(height) },
      sourceFrames: parseInt(totalFrames),
      extractedFrames: frameFiles.length,
      fps: 10,
      frames: frameFiles.sort(),
    }

    await fs.writeFile(
      path.join(OUTPUT_DIR, 'manifest.json'),
      JSON.stringify(manifest, null, 2)
    )

    console.log('\n═══════════════════════════════════════════════════════')
    console.log('  ✓ Reference frames ready for comparison')
    console.log(`  Location: ${OUTPUT_DIR}`)
    console.log('═══════════════════════════════════════════════════════')

  } catch (err) {
    console.error('✗ Frame extraction failed:', err.message)
    process.exit(1)
  }
}

extractFrames()
