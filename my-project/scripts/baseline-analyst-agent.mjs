#!/usr/bin/env node
/**
 * Baseline Analyst Agent
 *
 * Analyzes the reference animation using the full diff tool stack,
 * then generates a comprehensive baseline specification document.
 *
 * This agent:
 * 1. Captures reference frames from the APNG
 * 2. Runs comprehensive analysis on reference (color, geometry, timing)
 * 3. Extracts detailed metrics using all diff tools
 * 4. Calls Claude AI to write a detailed baseline spec document
 *
 * The output is a NEW REFERENCE-BASELINE-SPEC.md that combines:
 * - Linguistic descriptions (prompt-ready language)
 * - Extensive raw data from analysis tools
 *
 * Usage:
 *   node scripts/baseline-analyst-agent.mjs [options]
 *
 * Options:
 *   --output=DIR      Output directory (default: ./baseline-analysis)
 *   --port=N          Dev server port (default: 5173)
 *   --frames=N        Frames to capture (default: 30)
 *   --spec-output=FILE  Where to write the spec (default: docs/specs/REFERENCE-BASELINE-SPEC-v2.md)
 */

import { spawn, execSync } from 'child_process'
import fs from 'fs/promises'
import path from 'path'
import { fileURLToPath } from 'url'
import { PNG } from 'pngjs'
import { createReadStream } from 'fs'

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const PROJECT_ROOT = path.dirname(__dirname)

// Configuration
const CONFIG = {
  output: './baseline-analysis',
  port: 5173,
  frames: 30,
  cropSize: 465,
  frameDelay: 50,
  specOutput: 'docs/specs/REFERENCE-BASELINE-SPEC-v2.md',
}

// Parse arguments
function parseArgs() {
  const args = process.argv.slice(2)
  for (const arg of args) {
    if (arg.startsWith('--output=')) {
      CONFIG.output = arg.split('=')[1]
    } else if (arg.startsWith('--port=')) {
      CONFIG.port = parseInt(arg.split('=')[1], 10)
    } else if (arg.startsWith('--frames=')) {
      CONFIG.frames = parseInt(arg.split('=')[1], 10)
    } else if (arg.startsWith('--spec-output=')) {
      CONFIG.specOutput = arg.split('=')[1]
    }
  }
  return CONFIG
}

// Run a Node script
function runScript(scriptPath, args = []) {
  return new Promise((resolve, reject) => {
    console.log(`  Running: node ${path.basename(scriptPath)} ${args.join(' ')}`)
    const proc = spawn('node', [scriptPath, ...args], {
      cwd: PROJECT_ROOT,
      stdio: ['inherit', 'pipe', 'pipe'],
    })

    let stdout = ''
    let stderr = ''

    proc.stdout.on('data', data => {
      stdout += data.toString()
      process.stdout.write(data)
    })
    proc.stderr.on('data', data => {
      stderr += data.toString()
      process.stderr.write(data)
    })
    proc.on('close', code => resolve({ code, stdout, stderr }))
    proc.on('error', reject)
  })
}

// Load PNG file
async function loadPNG(filepath) {
  return new Promise((resolve, reject) => {
    const stream = createReadStream(filepath)
    const png = new PNG()
    stream.pipe(png)
      .on('parsed', () => resolve(png))
      .on('error', reject)
  })
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

// Analyze color distribution in a frame
function analyzeFrameColors(img) {
  const { width, height, data } = img
  const colorCounts = {}
  const hslStats = { h: [], s: [], l: [] }

  let totalR = 0, totalG = 0, totalB = 0
  let maxBrightness = 0
  let brightestColor = null
  let nonBlackPixels = 0

  for (let y = 0; y < height; y++) {
    for (let x = 0; x < width; x++) {
      const idx = (y * width + x) * 4
      const r = data[idx], g = data[idx + 1], b = data[idx + 2], a = data[idx + 3]

      if (a < 128) continue // Skip transparent

      const brightness = r + g + b
      if (brightness > 30) { // Skip near-black
        nonBlackPixels++
        totalR += r
        totalG += g
        totalB += b

        const hsl = rgbToHsl(r, g, b)
        hslStats.h.push(hsl.h)
        hslStats.s.push(hsl.s)
        hslStats.l.push(hsl.l)

        if (brightness > maxBrightness) {
          maxBrightness = brightness
          brightestColor = { r, g, b }
        }

        // Quantize color for distribution
        const qr = Math.floor(r / 16) * 16
        const qg = Math.floor(g / 16) * 16
        const qb = Math.floor(b / 16) * 16
        const key = `${qr},${qg},${qb}`
        colorCounts[key] = (colorCounts[key] || 0) + 1
      }
    }
  }

  // Get top colors
  const topColors = Object.entries(colorCounts)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 10)
    .map(([color, count]) => {
      const [r, g, b] = color.split(',').map(Number)
      return {
        rgb: { r, g, b },
        hex: '#' + [r, g, b].map(v => v.toString(16).padStart(2, '0')).join(''),
        count,
        percentage: ((count / nonBlackPixels) * 100).toFixed(2)
      }
    })

  return {
    avgColor: nonBlackPixels > 0 ? {
      r: Math.round(totalR / nonBlackPixels),
      g: Math.round(totalG / nonBlackPixels),
      b: Math.round(totalB / nonBlackPixels),
    } : null,
    brightestColor,
    hslMeans: {
      h: hslStats.h.length ? hslStats.h.reduce((a, b) => a + b, 0) / hslStats.h.length : 0,
      s: hslStats.s.length ? hslStats.s.reduce((a, b) => a + b, 0) / hslStats.s.length : 0,
      l: hslStats.l.length ? hslStats.l.reduce((a, b) => a + b, 0) / hslStats.l.length : 0,
    },
    topColors,
    nonBlackPixels,
  }
}

// Analyze radial brightness distribution
function analyzeRadialBrightness(img) {
  const { width, height, data } = img
  const centerX = width / 2
  const centerY = height / 2
  const maxRadius = Math.min(width, height) / 2

  const radialBins = []
  const binSize = 10 // pixels

  for (let r = 0; r < maxRadius; r += binSize) {
    const binBrightnesses = []

    for (let y = 0; y < height; y++) {
      for (let x = 0; x < width; x++) {
        const dx = x - centerX
        const dy = y - centerY
        const dist = Math.sqrt(dx * dx + dy * dy)

        if (dist >= r && dist < r + binSize) {
          const idx = (y * width + x) * 4
          const brightness = data[idx] + data[idx + 1] + data[idx + 2]
          binBrightnesses.push(brightness)
        }
      }
    }

    if (binBrightnesses.length > 0) {
      const avg = binBrightnesses.reduce((a, b) => a + b, 0) / binBrightnesses.length
      radialBins.push({
        radiusStart: r,
        radiusEnd: r + binSize,
        avgBrightness: Math.round(avg),
        percentOfMax: 0, // Will calculate after
      })
    }
  }

  // Calculate percent of max
  const maxBrightness = Math.max(...radialBins.map(b => b.avgBrightness))
  radialBins.forEach(b => {
    b.percentOfMax = Math.round((b.avgBrightness / maxBrightness) * 100)
  })

  return radialBins
}

// Detect bolt-like structures (high brightness linear features)
function analyzeBoltStructure(img) {
  const { width, height, data } = img
  const centerX = width / 2
  const centerY = height / 2

  // Find bright pixels (potential bolt cores)
  const brightPixels = []
  const threshold = 400 // r+g+b threshold for "bright"

  for (let y = 0; y < height; y++) {
    for (let x = 0; x < width; x++) {
      const idx = (y * width + x) * 4
      const brightness = data[idx] + data[idx + 1] + data[idx + 2]
      if (brightness > threshold) {
        const dx = x - centerX
        const dy = y - centerY
        const angle = Math.atan2(dy, dx) * 180 / Math.PI
        const dist = Math.sqrt(dx * dx + dy * dy)
        brightPixels.push({ x, y, brightness, angle, dist })
      }
    }
  }

  // Group by angle to find bolt directions
  const angleHistogram = {}
  const angleBinSize = 15 // degrees

  brightPixels.forEach(p => {
    const bin = Math.floor((p.angle + 180) / angleBinSize) * angleBinSize - 180
    angleHistogram[bin] = (angleHistogram[bin] || 0) + 1
  })

  // Find peaks (bolt directions)
  const sortedAngles = Object.entries(angleHistogram)
    .map(([angle, count]) => ({ angle: parseInt(angle), count }))
    .sort((a, b) => b.count - a.count)

  // Estimate bolt count from peaks
  const peakThreshold = sortedAngles[0]?.count * 0.3 || 0
  const boltDirections = sortedAngles.filter(a => a.count > peakThreshold)

  // Calculate bolt thickness (width of bright regions)
  const thicknesses = []
  // Sample across different angles
  for (let angle = 0; angle < 360; angle += 30) {
    const rad = angle * Math.PI / 180
    let foundBolt = false
    let boltStart = -1

    for (let r = 10; r < Math.min(width, height) / 2; r++) {
      const x = Math.round(centerX + r * Math.cos(rad))
      const y = Math.round(centerY + r * Math.sin(rad))
      if (x < 0 || x >= width || y < 0 || y >= height) break

      const idx = (y * width + x) * 4
      const brightness = data[idx] + data[idx + 1] + data[idx + 2]

      if (brightness > threshold && !foundBolt) {
        foundBolt = true
        boltStart = r
      } else if (brightness <= threshold && foundBolt) {
        // Found end of a bright region - could measure perpendicular width
        foundBolt = false
      }
    }
  }

  return {
    totalBrightPixels: brightPixels.length,
    estimatedBoltCount: Math.min(boltDirections.length, 12),
    boltDirections: boltDirections.slice(0, 10).map(d => d.angle),
    angleDistribution: angleHistogram,
    coverage: {
      minDist: brightPixels.length ? Math.min(...brightPixels.map(p => p.dist)) : 0,
      maxDist: brightPixels.length ? Math.max(...brightPixels.map(p => p.dist)) : 0,
      avgDist: brightPixels.length ? brightPixels.reduce((s, p) => s + p.dist, 0) / brightPixels.length : 0,
    }
  }
}

// Calculate frame-to-frame change
function calculateFrameChange(img1, img2) {
  const { width, height } = img1
  let changedPixels = 0
  let totalDiff = 0

  for (let y = 0; y < height; y++) {
    for (let x = 0; x < width; x++) {
      const idx = (y * width + x) * 4
      const diff = Math.abs(img1.data[idx] - img2.data[idx]) +
                   Math.abs(img1.data[idx + 1] - img2.data[idx + 1]) +
                   Math.abs(img1.data[idx + 2] - img2.data[idx + 2])

      if (diff > 30) { // Threshold for "changed"
        changedPixels++
        totalDiff += diff
      }
    }
  }

  const totalPixels = width * height
  return {
    changedPixels,
    changePercent: ((changedPixels / totalPixels) * 100).toFixed(2),
    avgDiff: changedPixels > 0 ? (totalDiff / changedPixels).toFixed(2) : 0,
  }
}

// Main analysis function
async function analyzeReference(config) {
  console.log('╔═══════════════════════════════════════════════════════════════╗')
  console.log('║          BASELINE ANALYST AGENT                               ║')
  console.log('║          Comprehensive Reference Analysis                     ║')
  console.log('╚═══════════════════════════════════════════════════════════════╝')
  console.log()

  const outputDir = path.resolve(PROJECT_ROOT, config.output)
  const framesDir = path.join(outputDir, 'reference-frames')
  await fs.mkdir(outputDir, { recursive: true })
  await fs.mkdir(framesDir, { recursive: true })

  // ─────────────────────────────────────────────────────────────────
  // Step 1: Capture reference frames
  // ─────────────────────────────────────────────────────────────────
  console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━')
  console.log('  STEP 1: Capturing reference frames')
  console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━')

  const captureScript = path.join(__dirname, 'diff-capture-agent.mjs')
  await runScript(captureScript, [
    '--mode=reference',
    `--output=${outputDir}`,
    `--port=${config.port}`,
    `--frames=${config.frames}`,
    `--crop-size=${config.cropSize}`,
    `--frame-delay=${config.frameDelay}`,
  ])

  const refDir = path.join(outputDir, 'reference')

  // ─────────────────────────────────────────────────────────────────
  // Step 2: Run comprehensive diff analysis
  // ─────────────────────────────────────────────────────────────────
  console.log('\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━')
  console.log('  STEP 2: Running comprehensive analysis tools')
  console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━')

  const analyzeScript = path.join(__dirname, 'diff-analyze-comprehensive.mjs')
  await runScript(analyzeScript, [
    `--live=${refDir}`,
    `--reference=${refDir}`,
    `--output=${path.join(outputDir, 'self-analysis')}`,
    '--target=100',
  ])

  // ─────────────────────────────────────────────────────────────────
  // Step 3: Deep frame-by-frame analysis
  // ─────────────────────────────────────────────────────────────────
  console.log('\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━')
  console.log('  STEP 3: Deep frame-by-frame analysis')
  console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━')

  const frameFiles = (await fs.readdir(refDir))
    .filter(f => f.startsWith('frame_') && f.endsWith('.png'))
    .sort()

  const frameAnalyses = []
  const temporalChanges = []

  for (let i = 0; i < frameFiles.length; i++) {
    const framePath = path.join(refDir, frameFiles[i])
    console.log(`  Analyzing frame ${i + 1}/${frameFiles.length}: ${frameFiles[i]}`)

    const img = await loadPNG(framePath)

    const analysis = {
      frameIndex: i,
      filename: frameFiles[i],
      colors: analyzeFrameColors(img),
      radialBrightness: analyzeRadialBrightness(img),
      boltStructure: analyzeBoltStructure(img),
    }

    frameAnalyses.push(analysis)

    // Calculate temporal change from previous frame
    if (i > 0) {
      const prevPath = path.join(refDir, frameFiles[i - 1])
      const prevImg = await loadPNG(prevPath)
      const change = calculateFrameChange(prevImg, img)
      temporalChanges.push({
        from: i - 1,
        to: i,
        ...change,
      })
    }
  }

  // ─────────────────────────────────────────────────────────────────
  // Step 4: Aggregate statistics
  // ─────────────────────────────────────────────────────────────────
  console.log('\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━')
  console.log('  STEP 4: Aggregating statistics')
  console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━')

  // Aggregate color data
  const allTopColors = {}
  frameAnalyses.forEach(fa => {
    fa.colors.topColors.forEach(c => {
      allTopColors[c.hex] = (allTopColors[c.hex] || 0) + c.count
    })
  })
  const dominantColors = Object.entries(allTopColors)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 15)
    .map(([hex, count]) => ({ hex, count }))

  // Aggregate HSL
  const avgHSL = {
    h: frameAnalyses.reduce((s, fa) => s + fa.colors.hslMeans.h, 0) / frameAnalyses.length,
    s: frameAnalyses.reduce((s, fa) => s + fa.colors.hslMeans.s, 0) / frameAnalyses.length,
    l: frameAnalyses.reduce((s, fa) => s + fa.colors.hslMeans.l, 0) / frameAnalyses.length,
  }

  // Aggregate bolt structure
  const avgBoltCount = frameAnalyses.reduce((s, fa) => s + fa.boltStructure.estimatedBoltCount, 0) / frameAnalyses.length
  const allBoltDirections = frameAnalyses.flatMap(fa => fa.boltStructure.boltDirections)

  // Temporal dynamics
  const avgChangePercent = temporalChanges.length > 0
    ? temporalChanges.reduce((s, tc) => s + parseFloat(tc.changePercent), 0) / temporalChanges.length
    : 0

  // Radial brightness profile (average across frames)
  const avgRadialProfile = []
  if (frameAnalyses[0]?.radialBrightness.length > 0) {
    for (let i = 0; i < frameAnalyses[0].radialBrightness.length; i++) {
      const avgBrightness = frameAnalyses.reduce((s, fa) =>
        s + (fa.radialBrightness[i]?.avgBrightness || 0), 0) / frameAnalyses.length
      avgRadialProfile.push({
        ...frameAnalyses[0].radialBrightness[i],
        avgBrightness: Math.round(avgBrightness),
      })
    }
  }

  // Compile full analysis data
  const analysisData = {
    metadata: {
      analyzedAt: new Date().toISOString(),
      frameCount: frameFiles.length,
      frameDimensions: { width: config.cropSize, height: config.cropSize },
      captureSettings: config,
    },
    colorAnalysis: {
      dominantColors,
      averageHSL: avgHSL,
      brightestPixels: frameAnalyses.map(fa => fa.colors.brightestColor).filter(Boolean),
    },
    boltGeometry: {
      estimatedBoltCount: {
        average: avgBoltCount.toFixed(1),
        min: Math.min(...frameAnalyses.map(fa => fa.boltStructure.estimatedBoltCount)),
        max: Math.max(...frameAnalyses.map(fa => fa.boltStructure.estimatedBoltCount)),
      },
      commonDirections: [...new Set(allBoltDirections)].sort((a, b) => a - b),
      coverage: {
        minRadius: Math.min(...frameAnalyses.map(fa => fa.boltStructure.coverage.minDist)),
        maxRadius: Math.max(...frameAnalyses.map(fa => fa.boltStructure.coverage.maxDist)),
        avgRadius: frameAnalyses.reduce((s, fa) => s + fa.boltStructure.coverage.avgDist, 0) / frameAnalyses.length,
      },
    },
    radialBrightnessProfile: avgRadialProfile,
    temporalDynamics: {
      avgFrameChangePercent: avgChangePercent.toFixed(2),
      changeRange: {
        min: temporalChanges.length > 0 ? Math.min(...temporalChanges.map(tc => parseFloat(tc.changePercent))) : 0,
        max: temporalChanges.length > 0 ? Math.max(...temporalChanges.map(tc => parseFloat(tc.changePercent))) : 0,
      },
      frameChanges: temporalChanges,
    },
    perFrameAnalysis: frameAnalyses,
  }

  // Save raw analysis data
  const rawDataPath = path.join(outputDir, 'baseline-analysis-raw.json')
  await fs.writeFile(rawDataPath, JSON.stringify(analysisData, null, 2))
  console.log(`\n✓ Raw analysis data saved to: ${rawDataPath}`)

  // ─────────────────────────────────────────────────────────────────
  // Step 5: Generate spec document with AI
  // ─────────────────────────────────────────────────────────────────
  console.log('\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━')
  console.log('  STEP 5: Generating baseline specification document')
  console.log('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━')

  const specContent = await generateSpecDocument(analysisData, config)

  const specPath = path.resolve(PROJECT_ROOT, config.specOutput)
  await fs.mkdir(path.dirname(specPath), { recursive: true })
  await fs.writeFile(specPath, specContent)

  console.log(`\n✓ Baseline specification saved to: ${specPath}`)

  return {
    success: true,
    analysisData,
    specPath,
    rawDataPath,
  }
}

// Generate the spec document using Claude AI
async function generateSpecDocument(analysisData, config) {
  console.log('  Calling Claude AI to generate comprehensive specification...')

  const prompt = buildSpecGenerationPrompt(analysisData)
  const promptPath = path.join(path.resolve(PROJECT_ROOT, config.output), 'spec-generation-prompt.md')
  await fs.writeFile(promptPath, prompt)

  try {
    const result = execSync(
      `cat "${promptPath}" | claude -p --model sonnet`,
      {
        cwd: PROJECT_ROOT,
        encoding: 'utf-8',
        maxBuffer: 10 * 1024 * 1024,
        timeout: 300000,
      }
    )
    return result
  } catch (err) {
    console.warn(`  AI generation failed, using template: ${err.message}`)
    return generateTemplateSpec(analysisData)
  }
}

// Build the prompt for spec generation
function buildSpecGenerationPrompt(data) {
  return `# Task: Generate Comprehensive Baseline Specification

You are a technical documentation expert specializing in animation and visual effects.
Generate a VERY detailed baseline specification document for an electricity/lightning animation effect.

## Requirements

The document must include:

1. **Linguistic Descriptions** - Rich, prompt-ready language that an AI animator can understand
   - Describe visual qualities in natural language
   - Use evocative but precise terminology
   - Include "should look like" and "should feel like" descriptions

2. **Extensive Data Tables** - All measured values from the analysis
   - Color values (hex, RGB, HSL)
   - Geometry measurements
   - Timing data
   - Radial brightness profiles

3. **Implementation Guidance** - Specific values an animator needs
   - Exact color codes to use
   - Specific numeric ranges for bolt geometry
   - Temporal dynamics targets

## Analysis Data

Here is the complete analysis data to incorporate:

\`\`\`json
${JSON.stringify(data, null, 2)}
\`\`\`

## Output Format

Write a complete markdown document with these sections:

1. **Header** - Title, version, date, purpose
2. **Executive Summary** - 2-3 paragraph overview of the effect
3. **Color Palette** - Dominant colors, gradients, HSL characteristics
4. **Bolt Geometry** - Count, directions, coverage, thickness
5. **Radial Brightness Profile** - Center to edge falloff
6. **Temporal Dynamics** - Frame-to-frame change rate, flicker
7. **Glow Characteristics** - Inner/outer glow specifications
8. **Implementation Checklist** - Quick reference for animators
9. **Raw Data Appendix** - Full data tables

Make it VERY detailed. This is the ground truth document that animators will reference.
Include specific hex colors, pixel measurements, percentages, and timing values.

IMPORTANT: Output the COMPLETE markdown document directly. Do NOT ask questions or request confirmation.
Do NOT say "Would you like me to save this?" - just output the full document content.
Start your output with "# Electricity Animation Reference Baseline Specification" and include ALL sections.

Write the complete specification now:
`
}

// Fallback template if AI fails
function generateTemplateSpec(data) {
  const colors = data.colorAnalysis.dominantColors.slice(0, 8)
  const hsl = data.colorAnalysis.averageHSL
  const bolts = data.boltGeometry
  const temporal = data.temporalDynamics
  const radial = data.radialBrightnessProfile

  return `# Electricity Animation Reference Baseline Specification

**Version**: 2.0 (Auto-generated)
**Date**: ${new Date().toISOString().split('T')[0]}
**Source**: Comprehensive frame analysis of reference APNG
**Purpose**: Canonical baseline for implementation accuracy scoring

---

## Executive Summary

This specification defines the visual characteristics of the electricity animation effect based on comprehensive frame-by-frame analysis of ${data.metadata.frameCount} reference frames at ${data.metadata.frameDimensions.width}x${data.metadata.frameDimensions.height} pixels.

The effect consists of ${bolts.estimatedBoltCount.average} primary lightning bolts emanating from the center, with a warm amber/golden color palette. The animation exhibits ${temporal.avgFrameChangePercent}% visual change per frame, creating a dynamic, energetic appearance.

---

## Section 1: Color Palette

### Dominant Colors (Measured)

| Rank | Hex Code | Usage Count | Description |
|------|----------|-------------|-------------|
${colors.map((c, i) => `| ${i + 1} | ${c.hex} | ${c.count} | ${getColorDescription(c.hex)} |`).join('\n')}

### HSL Characteristics

| Property | Value | Notes |
|----------|-------|-------|
| Average Hue | ${hsl.h.toFixed(1)}° | Amber/orange range |
| Average Saturation | ${hsl.s.toFixed(1)}% | Rich, warm tones |
| Average Lightness | ${hsl.l.toFixed(1)}% | Medium brightness |

### Color Temperature

- **Primary Palette**: Warm amber to golden yellow
- **Brightest Points**: Near-white with warm tint
- **Edge Colors**: Deep amber/brown
- **Temperature**: Evokes molten metal, heated copper

---

## Section 2: Bolt Geometry

### Bolt Count

| Metric | Value |
|--------|-------|
| Average | ${bolts.estimatedBoltCount.average} bolts |
| Minimum | ${bolts.estimatedBoltCount.min} bolts |
| Maximum | ${bolts.estimatedBoltCount.max} bolts |

### Angular Distribution

Primary bolt directions detected (degrees from center):
${bolts.commonDirections.slice(0, 10).map(d => `- ${d}°`).join('\n')}

### Coverage Area

| Metric | Value (pixels) |
|--------|----------------|
| Minimum Radius | ${bolts.coverage.minRadius.toFixed(1)} |
| Maximum Radius | ${bolts.coverage.maxRadius.toFixed(1)} |
| Average Radius | ${bolts.coverage.avgRadius.toFixed(1)} |

---

## Section 3: Radial Brightness Profile

| Distance from Center | Brightness (0-765) | % of Maximum |
|---------------------|-------------------|--------------|
${radial.map(r => `| ${r.radiusStart}-${r.radiusEnd}px | ${r.avgBrightness} | ${r.percentOfMax}% |`).join('\n')}

### Falloff Characteristics

- **Center**: Maximum brightness (hotspot)
- **Mid-range**: Gradual falloff following bolt intensity
- **Edge**: Rapid falloff near portal boundary

---

## Section 4: Temporal Dynamics

### Frame-to-Frame Change

| Metric | Value |
|--------|-------|
| Average Change | ${temporal.avgFrameChangePercent}% per frame |
| Minimum Change | ${temporal.changeRange.min.toFixed(2)}% |
| Maximum Change | ${temporal.changeRange.max.toFixed(2)}% |

### Animation Feel

- **Dynamism**: High - constant visual renewal
- **Flicker**: Organic, random bolt regeneration
- **Coherence**: Bolts morph rather than teleport

---

## Section 5: Implementation Checklist

### Colors to Use
- Bolt Core Peak: Use brightest detected color
- Inner Glow: ${colors[2]?.hex || '#DAA041'}
- Outer Glow: ${colors[5]?.hex || '#894F18'}

### Geometry Targets
- [ ] ${bolts.estimatedBoltCount.average} primary bolts
- [ ] Bolts reach ${bolts.coverage.maxRadius.toFixed(0)}px from center
- [ ] Distribute bolts across ${bolts.commonDirections.length}+ directions

### Timing Targets
- [ ] ${temporal.avgFrameChangePercent}% visual change per frame
- [ ] 30fps animation rate
- [ ] Organic, non-rhythmic flicker

---

## Appendix: Raw Analysis Metadata

\`\`\`json
${JSON.stringify(data.metadata, null, 2)}
\`\`\`

---

*Auto-generated baseline specification. For human-refined version, run with AI generation enabled.*
`
}

// Helper to describe a color
function getColorDescription(hex) {
  const r = parseInt(hex.slice(1, 3), 16)
  const g = parseInt(hex.slice(3, 5), 16)
  const b = parseInt(hex.slice(5, 7), 16)
  const brightness = r + g + b

  if (brightness > 600) return 'Bright core / highlight'
  if (brightness > 400) return 'Mid-tone amber'
  if (brightness > 200) return 'Deep amber / glow'
  return 'Dark edge / shadow'
}

// Run
const config = parseArgs()
analyzeReference(config)
  .then(result => {
    if (result.success) {
      console.log('\n╔═══════════════════════════════════════════════════════════════╗')
      console.log('║  ✓ BASELINE ANALYSIS COMPLETE                                 ║')
      console.log('╚═══════════════════════════════════════════════════════════════╝')
      console.log(`\nSpec document: ${result.specPath}`)
      console.log(`Raw data: ${result.rawDataPath}`)
      process.exit(0)
    } else {
      process.exit(1)
    }
  })
  .catch(err => {
    console.error('Baseline analysis failed:', err)
    process.exit(1)
  })
