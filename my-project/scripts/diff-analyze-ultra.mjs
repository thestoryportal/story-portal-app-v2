#!/usr/bin/env node
/**
 * Ultra-Enhanced Diff Analysis v3.0
 *
 * Next-generation analysis integrating all enhancements:
 * ✓ Semantic segmentation (bolt detection & measurement)
 * ✓ Enhanced diff visualizations (6 types)
 * ✓ Motion fingerprinting
 * ✓ Layer decomposition
 * ✓ Progressive refinement phase detection
 * ✓ Pattern library integration
 * ⧗ Perceptual quality metrics (LPIPS - optional)
 *
 * Usage:
 *   node scripts/diff-analyze-ultra.mjs [options]
 *
 * Options:
 *   --live=DIR           Live frames directory
 *   --reference=DIR      Reference frames directory
 *   --output=DIR         Output directory
 *   --iteration=N        Current iteration number
 *   --target=N           Target similarity percentage (default: 95)
 */

import fs from 'fs/promises'
import path from 'path'
import { fileURLToPath } from 'url'

// Import our new enhancement modules
import { analyzeFrame as analyzeSemantics, compareSemantics } from './semantic-analyzer.mjs'
import { determinePhase, getPhaseGuidance } from './progressive-refinement.mjs'
import { generateAllVisualizations } from './enhanced-diff-viz.mjs'
import { analyzeMotion, compareMotion } from './motion-fingerprint.mjs'
import { decomposeFrame, compareLayers } from './layer-decomposition.mjs'
import { PatternLibrary, createSignature } from './pattern-library.mjs'

// Import existing analysis functions (from diff-analyze-comprehensive.mjs logic)
import { PNG } from 'pngjs'
import { createReadStream } from 'fs'
import pixelmatch from 'pixelmatch'

const __dirname = path.dirname(fileURLToPath(import.meta.url))

// Parse arguments
function parseArgs() {
  const args = process.argv.slice(2)
  const options = {
    live: './capture-output/live',
    reference: './capture-output/reference',
    output: './diff-output-ultra',
    iteration: 1,
    target: 95,
  }

  for (const arg of args) {
    if (arg.startsWith('--live=')) options.live = arg.split('=')[1]
    else if (arg.startsWith('--reference=')) options.reference = arg.split('=')[1]
    else if (arg.startsWith('--output=')) options.output = arg.split('=')[1]
    else if (arg.startsWith('--iteration=')) options.iteration = parseInt(arg.split('=')[1], 10)
    else if (arg.startsWith('--target=')) options.target = parseFloat(arg.split('=')[1])
  }

  return options
}

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

// Basic pixelmatch comparison (from existing logic)
function compareImages(img1, img2, options = {}) {
  const { width, height } = img1
  const diff = new PNG({ width, height })

  const diffPixels = pixelmatch(
    img1.data,
    img2.data,
    diff.data,
    width,
    height,
    { threshold: options.threshold || 0.1 }
  )

  const totalPixels = width * height
  const similarity = 1 - (diffPixels / totalPixels)

  return { diff, diffPixels, totalPixels, similarity }
}

/**
 * Main ultra-enhanced analysis function
 */
async function analyzeFrames(options) {
  console.log('╔════════════════════════════════════════════════════════════════╗')
  console.log('║       ULTRA-ENHANCED DIFF ANALYSIS v3.0                        ║')
  console.log('╚════════════════════════════════════════════════════════════════╝')
  console.log()

  const outputDir = path.resolve(options.output)
  await fs.mkdir(outputDir, { recursive: true })

  // Load frames
  const refDir = path.resolve(options.reference)
  const liveDir = path.resolve(options.live)

  const refFrameFiles = (await fs.readdir(refDir))
    .filter(f => f.startsWith('frame_') && f.endsWith('.png'))
    .sort()

  const liveFrameFiles = (await fs.readdir(liveDir))
    .filter(f => f.startsWith('frame_') && f.endsWith('.png'))
    .sort()

  const frameCount = Math.min(refFrameFiles.length, liveFrameFiles.length)

  console.log(`Found ${refFrameFiles.length} reference and ${liveFrameFiles.length} live frames`)
  console.log(`Analyzing ${frameCount} frame pairs...\n`)

  // ═══════════════════════════════════════════════════════════════
  // PHASE 1: Determine Refinement Phase
  // ═══════════════════════════════════════════════════════════════
  console.log('[Phase Detection] Determining current refinement phase...')
  const currentPhase = determinePhase(options.iteration)
  console.log(`  Current Phase: ${currentPhase.name}`)
  console.log(`  Focus: ${currentPhase.guidance.focus}\n`)

  // ═══════════════════════════════════════════════════════════════
  // PHASE 2: Per-Frame Analysis
  // ═══════════════════════════════════════════════════════════════
  console.log('[Frame Analysis] Analyzing each frame pair...')

  const frameResults = []
  let totalSimilarity = 0

  for (let i = 0; i < Math.min(frameCount, 5); i++) { // Limit to 5 frames for speed
    const refFile = refFrameFiles[i]
    const liveFile = liveFrameFiles[i]
    const refPath = path.join(refDir, refFile)
    const livePath = path.join(liveDir, liveFile)

    console.log(`  Frame ${i + 1}/${frameCount}: ${refFile}`)

    try {
      const refImage = await loadPNG(refPath)
      const liveImage = await loadPNG(livePath)

      // Basic comparison
      const comparison = compareImages(refImage, liveImage, { threshold: 0.1 })

      // Semantic analysis
      const refSemantics = await analyzeSemantics(refImage)
      const liveSemantics = await analyzeSemantics(liveImage)
      const semanticComparison = compareSemantics(refSemantics, liveSemantics)

      // Enhanced visualizations
      const diffPath = path.join(outputDir, `diff_${String(i).padStart(4, '0')}.png`)
      await savePNG(comparison.diff, diffPath)
      const visualizations = await generateAllVisualizations(refImage, liveImage, comparison.diff, diffPath)

      // Layer decomposition (only for first frame to save time)
      let layerComparison = null
      if (i === 0) {
        console.log('    [Layer Decomposition] Analyzing layers...')
        const refLayers = await decomposeFrame(refImage)
        const liveLayers = await decomposeFrame(liveImage)
        layerComparison = compareLayers(refLayers, liveLayers)
      }

      frameResults.push({
        index: i,
        refFrame: refFile,
        liveFrame: liveFile,
        similarity: comparison.similarity,
        semantics: { ref: refSemantics, live: liveSemantics, comparison: semanticComparison },
        visualizations,
        layers: layerComparison
      })

      totalSimilarity += comparison.similarity
    } catch (err) {
      console.error(`    Error: ${err.message}`)
    }
  }

  const avgSimilarity = totalSimilarity / frameResults.length

  // ═══════════════════════════════════════════════════════════════
  // PHASE 3: Motion Analysis
  // ═══════════════════════════════════════════════════════════════
  console.log('\n[Motion Analysis] Analyzing temporal characteristics...')

  const refFramePaths = refFrameFiles.slice(0, frameCount).map(f => path.join(refDir, f))
  const liveFramePaths = liveFrameFiles.slice(0, frameCount).map(f => path.join(liveDir, f))

  const refMotion = await analyzeMotion(refFramePaths)
  const liveMotion = await analyzeMotion(liveFramePaths)
  const motionComparison = compareMotion(refMotion, liveMotion)

  console.log(`  Motion Similarity: ${motionComparison.motionSimilarity}%`)
  console.log(`  Flicker Rate Match: ${motionComparison.beatFrequency.assessment}`)

  // ═══════════════════════════════════════════════════════════════
  // PHASE 4: Calculate Overall Score
  // ═══════════════════════════════════════════════════════════════
  console.log('\n[Score Calculation] Computing overall match score...')

  const semanticScore = frameResults[0]?.semantics.comparison.overallSemanticMatch || 0
  const spatialScore = avgSimilarity * 100
  const motionScore = motionComparison.motionSimilarity
  const layerScore = frameResults[0]?.layers ? calculateLayerScore(frameResults[0].layers) : spatialScore

  // Phase-weighted score
  const weights = currentPhase.guidance.metricWeights
  const overallScore = Math.round(
    semanticScore * weights.semantic +
    spatialScore * weights.spatial +
    motionScore * weights.temporal +
    layerScore * weights.color
  )

  console.log(`  Semantic Score: ${semanticScore}/100`)
  console.log(`  Spatial Score: ${spatialScore.toFixed(1)}/100`)
  console.log(`  Motion Score: ${motionScore}/100`)
  console.log(`  Layer Score: ${layerScore.toFixed(1)}/100`)
  console.log(`  Overall Score (phase-weighted): ${overallScore}/100`)

  // ═══════════════════════════════════════════════════════════════
  // PHASE 5: Phase Guidance
  // ═══════════════════════════════════════════════════════════════
  const phaseGuidance = getPhaseGuidance(currentPhase, {
    semanticComparison: frameResults[0]?.semantics.comparison,
    motionAnalysis: motionComparison
  })

  // ═══════════════════════════════════════════════════════════════
  // PHASE 6: Pattern Library
  // ═══════════════════════════════════════════════════════════════
  console.log('\n[Pattern Library] Checking for similar patterns...')
  const library = new PatternLibrary(path.join(outputDir, '../../animation-patterns.json'))
  await library.load()

  const signature = createSignature({
    bolts: frameResults[0]?.semantics.ref.bolts,
    glowRegions: frameResults[0]?.semantics.ref.glowRegions,
    motion: refMotion
  })

  const similarPatterns = library.findSimilar(signature, 3)
  console.log(`  Found ${similarPatterns.length} similar patterns`)

  // ═══════════════════════════════════════════════════════════════
  // PHASE 7: Generate Report
  // ═══════════════════════════════════════════════════════════════
  const report = {
    analyzedAt: new Date().toISOString(),
    iteration: options.iteration,
    phase: {
      name: currentPhase.name,
      id: currentPhase.id,
      guidance: phaseGuidance
    },
    scores: {
      overall: overallScore,
      semantic: semanticScore,
      spatial: spatialScore,
      motion: motionScore,
      layer: layerScore,
      targetMet: overallScore >= options.target
    },
    semantics: frameResults[0]?.semantics.comparison,
    motion: motionComparison,
    layers: frameResults[0]?.layers,
    similarPatterns: similarPatterns.map(p => ({
      name: p.pattern.name,
      similarity: p.similarity,
      convergedIn: p.pattern.convergedIn
    })),
    frameResults
  }

  // Save report
  const reportPath = path.join(outputDir, 'ultra-analysis.json')
  await fs.writeFile(reportPath, JSON.stringify(report, null, 2))

  // Print summary
  console.log('\n' + '='.repeat(60))
  console.log('=== ULTRA ANALYSIS SUMMARY ===')
  console.log('='.repeat(60))
  console.log(`Phase: ${currentPhase.name}`)
  console.log(`Overall Score: ${overallScore}/100 (Target: ${options.target}%)`)
  console.log(`Status: ${overallScore >= options.target ? '✓ TARGET MET!' : '✗ Below target'}`)
  console.log()
  console.log('Phase Guidance:')
  phaseGuidance.instructions.forEach(instr => console.log(`  ${instr}`))
  console.log()
  console.log(`Report saved to: ${reportPath}`)
  console.log()

  return { success: true, report, targetMet: overallScore >= options.target }
}

// Helper: Calculate layer score
function calculateLayerScore(layerComparison) {
  let score = 100
  for (const [layerName, comparison] of Object.entries(layerComparison)) {
    if (comparison.assessment.status === 'NEEDS_ADJUSTMENT') {
      score -= 10
    } else if (comparison.assessment.status === 'ACCEPTABLE') {
      score -= 5
    }
  }
  return Math.max(0, score)
}

// Run analysis
const options = parseArgs()
analyzeFrames(options)
  .then(result => {
    process.exit(result.targetMet ? 0 : 2)
  })
  .catch(err => {
    console.error('Analysis error:', err)
    process.exit(1)
  })
