#!/usr/bin/env node
/**
 * Diff Iteration Orchestrator v4.2
 *
 * Full-stack animation comparison workflow with comprehensive agent separation.
 * ALWAYS starts fresh from baseline - no skip option.
 *
 * v4.2 IMPROVEMENTS:
 *   - Score history tracking for regression detection
 *   - Animation Expert sees previous scores and trend
 *   - Automatic regression warnings when score decreases
 *   - Critical rules to prevent overcorrection
 *
 * WORKFLOW:
 *
 *   PHASE 0: BASELINE ANALYST
 *       └── Specialized agent analyzes reference with full diff stack
 *       └── Generates NEW detailed REFERENCE-BASELINE-SPEC-v2.md
 *           ├── Linguistic descriptions (prompt-ready)
 *           └── Extensive data from analysis tools
 *
 *   PHASE 1: FIRST ANIMATOR ITERATION
 *       └── Animation Expert gets baseline spec AND reference frames
 *       └── Makes first implementation attempt
 *
 *   ITERATION LOOP (2-7):
 *       Step 1: DIFF TOOLS (NO AI - comprehensive raw analysis)
 *           └── Capture → SSIM → Heat maps → Regional → Metrics
 *           └── Single-frame best comparison
 *           └── Sequence/animation temporal analysis
 *           └── Output: ALL possible data and images
 *
 *       Step 2: EXPERT DIFF ANALYST (NEW - analysis only, NO code)
 *           └── Gets: Diff tool outputs (data + images)
 *           └── Describes differences in granular microscopic detail
 *           └── Precision accuracy, NO code modifications
 *
 *       Step 3: ANIMATION EXPERT
 *           └── Gets: Baseline spec + Reference frames + Diff data + Expert analysis
 *           └── Makes targeted code fixes
 *
 *   EXIT: Target reached (95%) OR 7 iterations → Human review
 *
 * Usage:
 *   node scripts/diff-iteration-orchestrator.mjs [options]
 *
 * Options:
 *   --max-iterations=N   Maximum iterations (default: 7)
 *   --target=N           Target similarity percentage (default: 95)
 *   --output=DIR         Output directory (default: ./iteration-output)
 *   --port=N             Dev server port (default: 5173)
 *   --frames=N           Frames to capture per iteration (default: 20)
 */

import { spawn, execSync } from 'child_process'
import fs from 'fs/promises'
import path from 'path'
import { fileURLToPath } from 'url'
import readline from 'readline'

// Global state for interrupt handling
let isInterrupted = false
let currentIterationNum = 0
let rl = null

// Create readline interface for user input
function createReadline() {
  if (rl) return rl
  rl = readline.createInterface({
    input: process.stdin,
    output: process.stdout,
  })
  return rl
}

// Prompt user for feedback
async function promptForFeedback(reason, iterNum, score, config) {
  const rlInterface = createReadline()

  console.log('\n╔════════════════════════════════════════════════════════════════╗')
  if (reason === 'interrupt') {
    console.log('║  ⏸️  PAUSED BY USER (Ctrl+C)                                    ║')
  } else {
    console.log('║  👤 MAX ITERATIONS REACHED                                     ║')
  }
  console.log(`║  Current Score: ${score}/100 (Target: ${config.target}%)                        ║`)
  console.log(`║  Iteration: ${iterNum}                                                   ║`)
  console.log('╠════════════════════════════════════════════════════════════════╣')
  console.log('║  Options:                                                      ║')
  console.log('║    [c] Continue with more iterations                           ║')
  console.log('║    [f] Provide feedback for the next iteration                 ║')
  console.log('║    [q] Quit and generate final report                          ║')
  console.log('╚════════════════════════════════════════════════════════════════╝')

  return new Promise((resolve) => {
    const ask = () => {
      rlInterface.question('\nYour choice (c/f/q): ', async (answer) => {
        const choice = answer.trim().toLowerCase()

        if (choice === 'c') {
          rlInterface.question('How many more iterations? [10]: ', (num) => {
            const moreIterations = parseInt(num) || 10
            resolve({ action: 'continue', moreIterations, feedback: null })
          })
        } else if (choice === 'f') {
          console.log('\nEnter your feedback (press Enter twice to finish):')
          let feedback = ''
          let emptyLineCount = 0

          const feedbackHandler = (line) => {
            if (line === '') {
              emptyLineCount++
              if (emptyLineCount >= 1) {
                rlInterface.removeListener('line', feedbackHandler)
                rlInterface.question('\nHow many more iterations? [10]: ', (num) => {
                  const moreIterations = parseInt(num) || 10
                  resolve({ action: 'continue', moreIterations, feedback: feedback.trim() })
                })
                return
              }
            } else {
              emptyLineCount = 0
            }
            feedback += line + '\n'
          }

          rlInterface.on('line', feedbackHandler)
        } else if (choice === 'q') {
          resolve({ action: 'quit', moreIterations: 0, feedback: null })
        } else {
          console.log('Invalid choice. Please enter c, f, or q.')
          ask()
        }
      })
    }
    ask()
  })
}

// Setup SIGINT handler
function setupInterruptHandler() {
  process.on('SIGINT', () => {
    if (isInterrupted) {
      // Second Ctrl+C - force quit
      console.log('\n\nForce quit.')
      process.exit(1)
    }
    isInterrupted = true
    console.log('\n\n⏸️  Interrupt received. Finishing current step...')
    console.log('   (Press Ctrl+C again to force quit)')
  })
}

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const PROJECT_ROOT = path.dirname(__dirname)

// The baseline spec is generated fresh by the baseline analyst
const BASELINE_SPEC_PATH = 'docs/specs/REFERENCE-BASELINE-SPEC-v2.md'

// Animation source files the expert can modify
const ANIMATION_SOURCE_FILES = [
  'src/legacy/components/electricity/*.ts',
  'src/legacy/components/electricity/*.tsx',
  'src/legacy/hooks/useElectricity*.ts',
]

// Configuration - NOTE: No skip-baseline option, always start fresh
// frames: Set to 12 to match actual reference APNG frame count (avoids mismatch with captured frames)
const CONFIG = {
  maxIterations: 7,
  target: 95,
  output: './iteration-output',
  port: 5173,
  frames: 12,
  cropSize: 465,
  frameDelay: 50,
  waitTime: 2000,
}

// Parse arguments
function parseArgs() {
  const args = process.argv.slice(2)
  for (const arg of args) {
    if (arg.startsWith('--max-iterations=')) {
      CONFIG.maxIterations = parseInt(arg.split('=')[1], 10)
    } else if (arg.startsWith('--target=')) {
      CONFIG.target = parseInt(arg.split('=')[1], 10)
    } else if (arg.startsWith('--output=')) {
      CONFIG.output = arg.split('=')[1]
    } else if (arg.startsWith('--port=')) {
      CONFIG.port = parseInt(arg.split('=')[1], 10)
    } else if (arg.startsWith('--frames=')) {
      CONFIG.frames = parseInt(arg.split('=')[1], 10)
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

// Run Animation Expert sub-agent with retry logic
async function runAnimationExpert(iterNum, baselineSpecPath, referenceDir, diffFeedback, expertAnalysis, outputDir, isFirstIteration, scoreHistory = [], frameCount = 12) {
  console.log('\n[Animation Expert] Starting AI analysis and code modification...')

  const prompt = buildAnimationExpertPrompt(iterNum, baselineSpecPath, referenceDir, diffFeedback, expertAnalysis, isFirstIteration, scoreHistory, frameCount)
  const promptFile = path.join(outputDir, `iteration-${iterNum}-expert-prompt.md`)
  await fs.writeFile(promptFile, prompt)

  const allowedTools = 'Read,Write,Edit,Glob,Grep,Bash'
  const maxRetries = 3

  for (let attempt = 1; attempt <= maxRetries; attempt++) {
    try {
      if (attempt > 1) {
        console.log(`  Retry attempt ${attempt}/${maxRetries}...`)
        await new Promise(r => setTimeout(r, 2000)) // Wait 2s between retries
      }

      const result = execSync(
        `cat "${promptFile}" | claude -p --allowed-tools "${allowedTools}" --model sonnet`,
        {
          cwd: PROJECT_ROOT,
          encoding: 'utf-8',
          maxBuffer: 10 * 1024 * 1024,
          timeout: 300000,
        }
      )

      const outputFile = path.join(outputDir, `iteration-${iterNum}-expert-output.md`)
      await fs.writeFile(outputFile, result)
      console.log(`  Expert output saved to: ${outputFile}`)

      return { success: true, output: result }
    } catch (err) {
      console.error(`  Animation Expert attempt ${attempt} failed: ${err.message}`)
      if (attempt === maxRetries) {
        return { success: false, error: err.message, attempts: maxRetries }
      }
    }
  }
}

// Run Expert Diff Analyst sub-agent (ANALYSIS ONLY - NO CODE CHANGES) with retry logic
async function runExpertDiffAnalyst(iterNum, analysisReport, outputDir) {
  console.log('\n[Expert Diff Analyst] Starting microscopic visual analysis...')
  console.log('  NOTE: Analysis only - NO code modifications')

  const prompt = buildExpertDiffAnalystPrompt(iterNum, analysisReport, outputDir)
  const promptFile = path.join(outputDir, `iteration-${iterNum}-diff-analyst-prompt.md`)
  await fs.writeFile(promptFile, prompt)

  // Read-only tools - NO Edit, Write, or Bash
  const allowedTools = 'Read,Glob,Grep'
  const maxRetries = 3

  for (let attempt = 1; attempt <= maxRetries; attempt++) {
    try {
      if (attempt > 1) {
        console.log(`  Retry attempt ${attempt}/${maxRetries}...`)
        await new Promise(r => setTimeout(r, 2000)) // Wait 2s between retries
      }

      const result = execSync(
        `cat "${promptFile}" | claude -p --allowed-tools "${allowedTools}" --model sonnet`,
        {
          cwd: PROJECT_ROOT,
          encoding: 'utf-8',
          maxBuffer: 10 * 1024 * 1024,
          timeout: 180000,
        }
      )

      const outputFile = path.join(outputDir, `iteration-${iterNum}-diff-analyst-output.md`)
      await fs.writeFile(outputFile, result)
      console.log(`  Diff analyst output saved to: ${outputFile}`)

      return { success: true, output: result }
    } catch (err) {
      console.error(`  Expert Diff Analyst attempt ${attempt} failed: ${err.message}`)
      if (attempt === maxRetries) {
        return { success: false, error: err.message, attempts: maxRetries }
      }
    }
  }
}

// Build prompt for Expert Diff Analyst (ANALYSIS ONLY)
function buildExpertDiffAnalystPrompt(iterNum, analysisReport, outputDir) {
  const diffImages = analysisReport?.frameResults?.map(f => f.outputs?.diffImage).filter(Boolean) || []
  const heatMaps = analysisReport?.frameResults?.map(f => f.outputs?.heatMap).filter(Boolean) || []
  const bestFrame = analysisReport?.singleFrameAnalysis?.bestMatch || null
  const worstFrame = analysisReport?.singleFrameAnalysis?.worstMatch || null
  const temporalAnalysis = analysisReport?.sequenceAnalysis || null

  return `# Expert Diff Analyst - Iteration ${iterNum}

You are an Expert Diff Analyst specializing in visual comparison with microscopic precision.
Your ONLY job is to ANALYZE and DESCRIBE the differences - you do NOT modify any code.

## YOUR ROLE: ANALYSIS ONLY

**CRITICAL**: You are a VISUAL ANALYST, not a programmer.
- DO NOT suggest code changes
- DO NOT modify any files
- DO NOT write implementation suggestions
- ONLY describe what you SEE in granular, microscopic detail

## Analysis Outputs to Review

### Output Directory
\`${outputDir}\`

### Diff Images (pixel differences marked in red)
${diffImages.map(f => `- \`${f}\``).join('\n')}

### Heat Maps (intensity of differences - blue=low, red=high)
${heatMaps.map(f => `- \`${f}\``).join('\n')}

### Comprehensive Analysis Data
\`${path.join(outputDir, 'comprehensive-analysis.json')}\`

## Analysis Report Summary

\`\`\`json
${JSON.stringify(analysisReport?.summary || {}, null, 2)}
\`\`\`

${bestFrame ? `
### Best Matching Frame (Most Similar)
- Frame Index: ${bestFrame.frameIndex}
- Similarity: ${bestFrame.similarity?.toFixed(2)}%
- Diff Image: \`${bestFrame.diffImage}\`
` : ''}

${worstFrame ? `
### Worst Matching Frame (Most Different)
- Frame Index: ${worstFrame.frameIndex}
- Similarity: ${worstFrame.similarity?.toFixed(2)}%
- Diff Image: \`${worstFrame.diffImage}\`
` : ''}

${temporalAnalysis ? `
### Sequence/Animation Analysis
- Temporal Consistency: ${temporalAnalysis.temporalConsistency?.toFixed(2)}%
- Frame-to-Frame Variance: ${temporalAnalysis.frameToFrameVariance?.toFixed(4)}
- Animation Smoothness: ${temporalAnalysis.smoothness || 'N/A'}
` : ''}

## YOUR TASK

Read the diff images and heat maps. Provide a DETAILED, MICROSCOPIC analysis of:

### 1. SINGLE FRAME ANALYSIS
For the BEST matching frame:
- What differences remain? Describe their exact location (pixels from center, quadrant)
- What is the nature of differences? (color, brightness, shape, edge sharpness)
- How visible are these differences to a human eye?

For the WORST matching frame:
- What is drastically different?
- Are there missing elements? Extra elements?
- Describe the spatial distribution of errors

### 2. SEQUENCE/ANIMATION ANALYSIS
- Are differences consistent across frames or do they vary?
- Are there temporal artifacts (flickering, inconsistent motion)?
- Do bolt positions/shapes change appropriately between reference and live?
- Is the glow animation timing correct?

### 3. REGIONAL BREAKDOWN
For each problem region identified:
- Exact pixel coordinates of the issue center
- Size of the affected area in pixels
- Nature of the visual discrepancy

### 4. COLOR VISUAL ANALYSIS
Describe color differences you can SEE in the images:
- Core bolt color: Is it brighter/dimmer? More yellow/orange/white than reference?
- Glow color: Does the hue appear shifted? Is saturation higher/lower?
- Background bleed: Any unwanted colors bleeding into the animation?
NOTE: Describe what you SEE visually - do not try to extract exact RGB values.

### 5. EDGE AND STRUCTURE ANALYSIS
- Are bolt edges sharp or fuzzy compared to reference?
- Are there anti-aliasing differences?
- Do bolt paths follow similar curves or diverge?

## OUTPUT FORMAT

Provide your analysis in this EXACT format:

\`\`\`
EXPERT DIFF ANALYSIS - ITERATION ${iterNum}
================================================

OVERALL VISUAL ASSESSMENT:
[1-2 sentences describing the general state of match]

SINGLE FRAME ANALYSIS:

Best Frame (#[N]):
- Location of remaining differences: [precise description]
- Nature of differences: [color/brightness/shape/edge]
- Visibility assessment: [barely visible / noticeable / obvious / severe]

Worst Frame (#[N]):
- Primary discrepancies: [list]
- Missing elements: [if any]
- Extra elements: [if any]
- Spatial error distribution: [concentrated/scattered/uniform]

SEQUENCE ANALYSIS:

Temporal Consistency:
- [description of how differences behave across frames]

Animation Timing:
- [does the live animation timing match reference?]

Motion Quality:
- [smoothness, jitter, any temporal artifacts]

REGIONAL BREAKDOWN:

[For each problem region:]
Region [name]:
- Center: approximately [X, Y] pixels from center
- Affected area: ~[N]x[M] pixels
- Issue: [precise description of what's wrong]

COLOR VISUAL DIFFERENCES:

Core Bolt Colors:
- Observed difference: [brighter/dimmer/similar]
- Color shift: [more yellow/more orange/more white/none]
- Intensity match: [too bright/too dim/matches well]

Glow Colors:
- Hue difference: [warmer/cooler/similar to reference]
- Saturation: [more vivid/more muted/similar]
- Overall impression: [description of visual color match]

EDGE ANALYSIS:

- Edge sharpness: [sharper/similar/softer] than reference
- Anti-aliasing: [matches/differs] - [description]
- Path accuracy: [following/diverging from] reference curves

MICROSCOPIC DETAILS:

[Any other granular observations not covered above]
\`\`\`

Remember: DESCRIBE ONLY. Do not suggest fixes or code changes.
Begin by reading the diff images and heat maps, then provide your detailed analysis.
`
}

// Build prompt for Animation Expert
function buildAnimationExpertPrompt(iterNum, baselineSpecPath, referenceDir, diffFeedback, expertAnalysis, isFirstIteration, scoreHistory = [], frameCount = 12) {
  // Build score history section
  let scoreHistorySection = ''
  if (scoreHistory.length > 0) {
    const lastScore = scoreHistory[scoreHistory.length - 1]
    const prevScore = scoreHistory.length > 1 ? scoreHistory[scoreHistory.length - 2] : null
    const bestScore = Math.max(...scoreHistory)
    const trend = prevScore !== null ? (lastScore > prevScore ? '📈 IMPROVING' : lastScore < prevScore ? '📉 REGRESSING' : '➡️ STABLE') : 'N/A'

    scoreHistorySection = `
## ⚠️ SCORE HISTORY - READ THIS FIRST

**Current Score:** ${lastScore}/100
**Previous Score:** ${prevScore !== null ? prevScore + '/100' : 'N/A'}
**Best Score Achieved:** ${bestScore}/100
**Trend:** ${trend}
**History:** ${scoreHistory.map((s, i) => `iter${i + 2}:${s}`).join(' → ')}

${lastScore < (prevScore || 0) ? `
### 🚨 REGRESSION DETECTED!
Your last change DECREASED the score from ${prevScore} to ${lastScore}.
**DO NOT** continue in the same direction. Consider:
1. The previous iteration was closer to correct
2. Your last change overcorrected or broke something
3. You may need to REVERT some changes or take a different approach
` : ''}

${lastScore < bestScore ? `
### ⚠️ Below Best Score
The best score was ${bestScore}, but current is ${lastScore}.
Something that worked before may have been lost. Review what changed.
` : ''}
`
  }

  const basePrompt = `# Animation Expert - Iteration ${iterNum}

You are an Animation Expert sub-agent specializing in electricity/lightning visual effects.
Your job is to implement and refine the electricity animation to match the reference.
${scoreHistorySection}

## 🎯 CRITICAL RULES

1. **DO NOT overcorrect** - If feedback says "too dim", increase by 10-20%, not 200%
2. **Preserve what works** - If colors were good last iteration, don't change them
3. **Small incremental changes** - One property at a time when possible
4. **Check the score history** - If you're regressing, STOP and reconsider

## Your GROUND TRUTH Document

**CRITICAL**: Before doing ANYTHING, you MUST read this baseline specification:

\`${baselineSpecPath}\`

This document contains:
- Exact color values (hex codes, RGB, HSL)
- Bolt geometry specifications (count, thickness, length, angles)
- Radial brightness profile (center to edge falloff)
- Temporal dynamics (frame-to-frame change rates)
- Glow characteristics

Read it completely. Every value in this document is measured from the reference animation.

## Reference Animation Frames

The reference frames you are matching against are in:
\`${referenceDir}\`

These are the EXACT images from the reference APNG animation:
- frame_0000.png through frame_${String(frameCount - 1).padStart(4, '0')}.png (${frameCount} frames)
- Each is 465x465 pixels, centered on the portal
- You can view these to see exactly what the target animation looks like

## Animation Source Files

The electricity animation code is in:
${ANIMATION_SOURCE_FILES.map(p => `- \`${p}\``).join('\n')}

`

  if (isFirstIteration) {
    return basePrompt + `
## Your Task (First Iteration)

This is the FIRST iteration. You have the baseline specification AND reference frames.

1. **Read the baseline spec** - Understand exactly what the animation should look like
2. **View reference frames** - Look at the actual target images
3. **Review current implementation** - Read the animation source files
4. **Identify gaps** - Compare current code to spec requirements
5. **Make targeted changes** - Adjust colors, geometry, timing to match spec

Focus on the most impactful properties first:
- Color palette (bolt core, inner glow, outer glow)
- Bolt count and distribution
- Glow radii and falloff

## Output Format

After making changes, output:

\`\`\`
BASELINE SPEC VALUES TARGETED:
- [property]: [spec value] → [your implementation]

REFERENCE FRAME OBSERVATIONS:
- [what you observed in the reference frames]

CHANGES MADE:
- [file]: [description of change]

CONFIDENCE LEVEL:
- [High/Medium/Low] - [reason]

AREAS NEEDING ATTENTION:
- [any properties you couldn't fully address]
\`\`\`

Begin by reading the baseline specification and viewing reference frames, then implement.
`
  } else {
    return basePrompt + `
## Diff Analysis Feedback (Iteration ${iterNum})

The diff tools have compared your implementation to the reference. Here are the results:

\`\`\`json
${JSON.stringify(diffFeedback, null, 2)}
\`\`\`

## Expert Diff Analyst Report

An Expert Diff Analyst has provided a detailed microscopic analysis of the visual differences:

\`\`\`
${expertAnalysis || 'Expert analysis not available'}
\`\`\`

## Your Task

1. **Re-read the baseline spec** - Ground truth for all values
2. **Review the Expert Diff Analyst report** - Understand the EXACT visual differences
3. **View reference vs live frames** - Compare them directly if needed
4. **Correlate problems to spec values** - What specific values need adjustment?
5. **Make targeted fixes** - Only change what the analysis identifies as wrong

### Interpreting Feedback

From Diff Tools:
- **SSIM < 90%**: Structural differences - shapes, forms are wrong
- **Edge Match < 85%**: Bolt shapes differ - check path generation
- **Color differences**: Hue/saturation/luminance drift - adjust color values
- **Problem regions**: Focus on the areas flagged as problematic
- **Heat maps**: Red areas show where differences concentrate

From Expert Analysis:
- **Single frame analysis**: Focus on worst frame issues first
- **Sequence analysis**: Check for timing/animation flow issues
- **Regional breakdown**: Target the specific pixel regions mentioned
- **Color precision**: Exact RGB values to match

## Output Format

After making changes, output:

\`\`\`
EXPERT ANALYSIS ISSUES ADDRESSED:
- [issue from expert report]: [how you fixed it]

DIFF METRICS TARGETED:
- [metric]: Was [old value], targeting [spec value]

CHANGES MADE:
- [file]: [description of change]

EXPECTED IMPROVEMENT:
- [which metrics should improve and why]

REMAINING GAPS:
- [issues that need more iteration]
\`\`\`

Begin by re-reading the baseline spec and expert analysis, then make targeted fixes.
`
  }
}

// Check dev server
async function checkDevServer(port) {
  const http = await import('http')
  return new Promise(resolve => {
    const req = http.request({
      hostname: 'localhost',
      port,
      path: '/',
      method: 'HEAD',
      timeout: 3000,
    }, () => resolve(true))
    req.on('error', () => resolve(false))
    req.on('timeout', () => { req.destroy(); resolve(false) })
    req.end()
  })
}

// Load/save state
async function loadState(outputDir) {
  const statePath = path.join(outputDir, 'iteration-state.json')
  try {
    return JSON.parse(await fs.readFile(statePath, 'utf-8'))
  } catch {
    return {
      currentIteration: 0,
      history: [],
      baselineGenerated: false,
      startedAt: new Date().toISOString(),
    }
  }
}

async function saveState(outputDir, state) {
  await fs.writeFile(
    path.join(outputDir, 'iteration-state.json'),
    JSON.stringify(state, null, 2)
  )
}

// Main orchestration
async function main() {
  const config = parseArgs()

  // Setup interrupt handler for Ctrl+C feedback
  setupInterruptHandler()

  console.log('╔════════════════════════════════════════════════════════════════╗')
  console.log('║         DIFF ITERATION ORCHESTRATOR v4.2                       ║')
  console.log('║         With Score History & Regression Detection              ║')
  console.log('╠════════════════════════════════════════════════════════════════╣')
  console.log(`║  Max Iterations: ${String(config.maxIterations).padEnd(3)} │ Target: ${config.target}%                        ║`)
  console.log('║  Press Ctrl+C anytime to pause and provide feedback            ║')
  console.log('╠════════════════════════════════════════════════════════════════╣')
  console.log('║  Phase 0: Baseline Analyst → Generate spec from reference      ║')
  console.log('║  Phase 1: Animation Expert → First impl (spec + ref frames)    ║')
  console.log('║  Loop:    Diff Tools → Expert Analyst → Animation Expert       ║')
  console.log('╚════════════════════════════════════════════════════════════════╝')
  console.log()

  // Check dev server
  console.log('Checking dev server...')
  if (!await checkDevServer(config.port)) {
    console.error(`\n✗ Dev server not running at http://localhost:${config.port}`)
    console.error(`  Start it with: pnpm dev`)
    process.exit(1)
  }
  console.log(`✓ Dev server running\n`)

  // Check Claude CLI
  try {
    execSync('which claude', { stdio: 'pipe' })
    console.log('✓ Claude CLI available\n')
  } catch {
    console.error('✗ Claude CLI not found - required for this workflow')
    process.exit(1)
  }

  // Setup directories
  const outputDir = path.resolve(PROJECT_ROOT, config.output)
  const captureDir = path.join(outputDir, 'capture-output')
  const referenceDir = path.join(captureDir, 'reference')
  const liveDir = path.join(captureDir, 'live')

  await fs.mkdir(outputDir, { recursive: true })
  await fs.mkdir(captureDir, { recursive: true })

  let state = await loadState(outputDir)

  const baselineAnalystScript = path.join(__dirname, 'baseline-analyst-agent.mjs')
  const captureScript = path.join(__dirname, 'diff-capture-agent.mjs')
  const analyzeScript = path.join(__dirname, 'diff-analyze-comprehensive.mjs')
  const baselineSpecPath = path.resolve(PROJECT_ROOT, BASELINE_SPEC_PATH)

  // ═══════════════════════════════════════════════════════════════════
  // PHASE 0: BASELINE ANALYST (ALWAYS RUNS - No skip option)
  // ═══════════════════════════════════════════════════════════════════

  if (!state.baselineGenerated) {
    console.log('╔════════════════════════════════════════════════════════════════╗')
    console.log('║  PHASE 0: BASELINE ANALYST                                     ║')
    console.log('║  Generating comprehensive baseline specification (ALWAYS)      ║')
    console.log('╚════════════════════════════════════════════════════════════════╝')
    console.log()

    const baselineResult = await runScript(baselineAnalystScript, [
      `--output=${path.join(outputDir, 'baseline-analysis')}`,
      `--port=${config.port}`,
      `--frames=${config.frames}`,
      `--spec-output=${BASELINE_SPEC_PATH}`,
    ])

    if (baselineResult.code !== 0) {
      console.error('\n✗ Baseline analysis failed!')
      process.exit(1)
    }

    // Copy reference frames for later comparison
    const baselineRefDir = path.join(outputDir, 'baseline-analysis', 'reference')
    try {
      const files = await fs.readdir(baselineRefDir)
      const frameFiles = files.filter(f => f.startsWith('frame_') && f.endsWith('.png'))
      await fs.mkdir(referenceDir, { recursive: true })
      for (const file of files) {
        await fs.copyFile(
          path.join(baselineRefDir, file),
          path.join(referenceDir, file)
        )
      }
      state.referenceFrameCount = frameFiles.length
      console.log(`\n✓ Reference frames copied to: ${referenceDir} (${frameFiles.length} frames)`)
    } catch (err) {
      console.warn(`  Could not copy reference frames: ${err.message}`)
    }

    state.baselineGenerated = true
    state.baselineSpecPath = baselineSpecPath
    state.referenceFramesDir = referenceDir
    await saveState(outputDir, state)

    console.log('\n✓ Baseline specification generated!')
    console.log(`  Spec: ${baselineSpecPath}`)
    console.log(`  Reference frames: ${referenceDir}\n`)
  }

  // ═══════════════════════════════════════════════════════════════════
  // PHASE 1: FIRST ANIMATOR ITERATION (Spec + Reference Frames)
  // ═══════════════════════════════════════════════════════════════════

  if (state.currentIteration === 0) {
    state.currentIteration = 1
    const iterNum = 1

    console.log('╔════════════════════════════════════════════════════════════════╗')
    console.log('║  PHASE 1: FIRST ANIMATOR ITERATION                             ║')
    console.log('║  Animation Expert receives baseline spec + reference frames    ║')
    console.log('╚════════════════════════════════════════════════════════════════╝')
    console.log()

    const iterOutputDir = path.join(outputDir, `iteration-${iterNum}`)
    await fs.mkdir(iterOutputDir, { recursive: true })

    const iterStartTime = Date.now()

    // Run Animation Expert with baseline spec AND reference frames (no diff feedback yet)
    const expertResult = await runAnimationExpert(
      iterNum,
      baselineSpecPath,
      referenceDir,         // Reference frames directory
      null,                 // No diff feedback for first iteration
      null,                 // No expert analysis for first iteration
      iterOutputDir,
      true,                 // isFirstIteration
      [],                   // No score history yet
      state.referenceFrameCount || 12  // Actual frame count
    )

    const iterDuration = ((Date.now() - iterStartTime) / 1000).toFixed(1)

    state.history.push({
      iteration: iterNum,
      phase: 'first_implementation',
      expertRan: expertResult.success,
      duration: `${iterDuration}s`,
      timestamp: new Date().toISOString(),
      outputDir: iterOutputDir,
    })
    await saveState(outputDir, state)

    console.log('\n───────────────────────────────────────────────────────────────')
    console.log(`  Iteration 1 Complete (First Implementation)`)
    console.log(`  Animation Expert: ${expertResult.success ? 'Made changes' : 'Failed'}`)
    console.log(`  Duration: ${iterDuration}s`)
    console.log('───────────────────────────────────────────────────────────────')

    // Let HMR settle
    console.log('\n  Waiting for code changes to settle...')
    await new Promise(r => setTimeout(r, 3000))
  }

  // ═══════════════════════════════════════════════════════════════════
  // ITERATION LOOP (2-7): Diff Tools → Expert Diff Analyst → Animation Expert
  // ═══════════════════════════════════════════════════════════════════

  while (state.currentIteration < config.maxIterations) {
    state.currentIteration++
    const iterNum = state.currentIteration

    console.log()
    console.log('╔════════════════════════════════════════════════════════════════╗')
    console.log(`║  ITERATION ${iterNum} of ${config.maxIterations}                                               ║`)
    console.log('╚════════════════════════════════════════════════════════════════╝')

    const iterStartTime = Date.now()
    const iterOutputDir = path.join(outputDir, `iteration-${iterNum}`)
    await fs.mkdir(iterOutputDir, { recursive: true })

    // ─────────────────────────────────────────────────────────────────
    // Step 1/3: DIFF TOOLS (No AI - comprehensive raw analysis)
    // ─────────────────────────────────────────────────────────────────
    console.log('\n[Step 1/3] Running Diff Tools (capture + comprehensive analyze)...')
    console.log('           NO AI interpretation - ALL possible data outputs\n')

    // Capture live frames
    await runScript(captureScript, [
      '--mode=live',
      `--output=${captureDir}`,
      `--port=${config.port}`,
      `--frames=${config.frames}`,
      `--crop-size=${config.cropSize}`,
      `--frame-delay=${config.frameDelay}`,
      `--wait=${config.waitTime}`,
    ])

    // Run comprehensive analysis (includes single-frame and sequence analysis)
    await runScript(analyzeScript, [
      `--live=${liveDir}`,
      `--reference=${referenceDir}`,
      `--output=${iterOutputDir}`,
      `--target=${config.target}`,
    ])

    // Read analysis results (raw data, no interpretation)
    let analysisReport = null
    let score = 0
    let targetMet = false

    try {
      const reportPath = path.join(iterOutputDir, 'comprehensive-analysis.json')
      const reportData = await fs.readFile(reportPath, 'utf-8')
      analysisReport = JSON.parse(reportData)
      score = analysisReport.summary?.overallScore || 0
      targetMet = analysisReport.summary?.targetMet || false
    } catch (err) {
      console.warn(`  Could not read analysis report: ${err.message}`)
    }

    console.log(`\n  Diff Tools Complete. Score: ${score}/100`)

    // Check if target reached BEFORE running expert analysts
    if (targetMet) {
      console.log('\n╔════════════════════════════════════════════════════════════════╗')
      console.log('║  🎯 TARGET REACHED!                                            ║')
      console.log(`║  Score: ${score}/100 in ${iterNum} iteration(s)                             ║`)
      console.log('╚════════════════════════════════════════════════════════════════╝')

      state.history.push({
        iteration: iterNum,
        phase: 'diff_analysis',
        score,
        targetMet: true,
        timestamp: new Date().toISOString(),
        outputDir: iterOutputDir,
      })
      await saveState(outputDir, state)
      await generateFinalReport(outputDir, state, config, 'target_met')
      process.exit(0)
    }

    // ─────────────────────────────────────────────────────────────────
    // Step 2/3: EXPERT DIFF ANALYST (Analysis ONLY - NO code changes)
    // ─────────────────────────────────────────────────────────────────
    console.log('\n[Step 2/3] Running Expert Diff Analyst...')
    console.log('           Microscopic visual analysis - NO code modifications\n')

    const diffAnalystResult = await runExpertDiffAnalyst(
      iterNum,
      analysisReport,
      iterOutputDir
    )

    console.log(`  Expert Diff Analyst: ${diffAnalystResult.success ? 'Analysis complete' : 'Failed'}`)

    // ─────────────────────────────────────────────────────────────────
    // Step 3/3: ANIMATION EXPERT (Gets EVERYTHING - makes code changes)
    // ─────────────────────────────────────────────────────────────────
    console.log('\n[Step 3/3] Running Animation Expert...')
    console.log('           Receives: Baseline Spec + Ref Frames + Diff Data + Expert Analysis\n')

    // Include human feedback if available
    let expertAnalysis = diffAnalystResult.output || null
    if (state.humanFeedback) {
      console.log('           Including human feedback from previous pause\n')
      expertAnalysis = `## Human Feedback (Priority)\n\n${state.humanFeedback}\n\n---\n\n${expertAnalysis || ''}`
      // Clear feedback after use
      state.humanFeedback = null
      await saveState(outputDir, state)
    }

    // Extract score history from state for regression detection
    const scoreHistory = state.history
      .filter(h => h.score !== undefined)
      .map(h => h.score)

    const expertResult = await runAnimationExpert(
      iterNum,
      baselineSpecPath,
      referenceDir,                        // Reference frames directory
      analysisReport?.summary || null,     // Diff tool metrics
      expertAnalysis,                      // Expert diff analyst report + human feedback
      iterOutputDir,
      false,                               // Not first iteration
      scoreHistory,                        // Score history for regression detection
      state.referenceFrameCount || 12     // Actual frame count
    )

    const iterDuration = ((Date.now() - iterStartTime) / 1000).toFixed(1)

    state.history.push({
      iteration: iterNum,
      phase: 'full_analysis_and_fix',
      score,
      diffAnalystRan: diffAnalystResult.success,
      expertRan: expertResult.success,
      duration: `${iterDuration}s`,
      timestamp: new Date().toISOString(),
      outputDir: iterOutputDir,
    })
    await saveState(outputDir, state)

    console.log('\n───────────────────────────────────────────────────────────────')
    console.log(`  Iteration ${iterNum} Complete`)
    console.log(`  Score: ${score}/100 (Target: ${config.target}%)`)
    console.log(`  Expert Diff Analyst: ${diffAnalystResult.success ? 'Analyzed' : 'Failed'}`)
    console.log(`  Animation Expert: ${expertResult.success ? 'Made changes' : 'Failed'}`)
    console.log(`  Duration: ${iterDuration}s`)
    console.log('───────────────────────────────────────────────────────────────')

    // Check for interrupt
    if (isInterrupted) {
      isInterrupted = false // Reset for potential continue
      const result = await promptForFeedback('interrupt', iterNum, score, config)

      if (result.action === 'quit') {
        await generateFinalReport(outputDir, state, config, 'user_quit')
        if (rl) rl.close()
        process.exit(0)
      }

      // Store feedback for next iteration
      if (result.feedback) {
        state.humanFeedback = result.feedback
        await saveState(outputDir, state)
        console.log('\n✓ Feedback saved. Will be included in next Animation Expert prompt.')
      }

      // Extend max iterations
      config.maxIterations = state.currentIteration + result.moreIterations
      console.log(`\n  Continuing with ${result.moreIterations} more iterations (new max: ${config.maxIterations})`)
    }

    if (iterNum < config.maxIterations) {
      console.log(`\n  Gap to target: ${config.target - score} points`)
      console.log('  Continuing to next iteration...')

      // Let HMR settle
      await new Promise(r => setTimeout(r, 2000))
    }
  }

  // ═══════════════════════════════════════════════════════════════════
  // MAX ITERATIONS - PROMPT FOR FEEDBACK
  // ═══════════════════════════════════════════════════════════════════

  const lastScore = state.history.filter(h => h.score !== undefined).pop()?.score || 0

  while (true) {
    const result = await promptForFeedback('max_iterations', state.currentIteration, lastScore, config)

    if (result.action === 'quit') {
      await generateFinalReport(outputDir, state, config, 'user_quit')
      if (rl) rl.close()
      process.exit(0)
    }

    // Store feedback and continue
    if (result.feedback) {
      state.humanFeedback = result.feedback
      await saveState(outputDir, state)
      console.log('\n✓ Feedback saved. Will be included in next Animation Expert prompt.')
    }

    // Extend max iterations and continue the loop
    config.maxIterations = state.currentIteration + result.moreIterations
    console.log(`\n  Continuing with ${result.moreIterations} more iterations...`)

    // Re-enter the main loop by recursively continuing
    // This is a bit hacky but works - alternative is refactoring to a true while loop
    isInterrupted = false

    // Continue iterations
    while (state.currentIteration < config.maxIterations) {
      state.currentIteration++
      const iterNum = state.currentIteration
      currentIterationNum = iterNum

      console.log()
      console.log('╔════════════════════════════════════════════════════════════════╗')
      console.log(`║  ITERATION ${iterNum} of ${config.maxIterations}                                               ║`)
      console.log('╚════════════════════════════════════════════════════════════════╝')

      const iterStartTime = Date.now()
      const iterOutputDir = path.join(outputDir, `iteration-${iterNum}`)
      await fs.mkdir(iterOutputDir, { recursive: true })

      // Step 1: Diff Tools
      console.log('\n[Step 1/3] Running Diff Tools...')
      await runScript(captureScript, [
        '--mode=live',
        `--output=${captureDir}`,
        `--port=${config.port}`,
        `--frames=${config.frames}`,
        `--crop-size=${config.cropSize}`,
        `--frame-delay=${config.frameDelay}`,
        `--wait=${config.waitTime}`,
      ])

      await runScript(analyzeScript, [
        `--live=${liveDir}`,
        `--reference=${referenceDir}`,
        `--output=${iterOutputDir}`,
        `--target=${config.target}`,
      ])

      let analysisReport = null
      let score = 0
      let targetMet = false

      try {
        const reportPath = path.join(iterOutputDir, 'comprehensive-analysis.json')
        const reportData = await fs.readFile(reportPath, 'utf-8')
        analysisReport = JSON.parse(reportData)
        score = analysisReport.summary?.overallScore || 0
        targetMet = analysisReport.summary?.targetMet || false
      } catch (err) {
        console.warn(`  Could not read analysis report: ${err.message}`)
      }

      console.log(`\n  Score: ${score}/100`)

      if (targetMet) {
        console.log('\n🎯 TARGET REACHED!')
        state.history.push({ iteration: iterNum, score, targetMet: true, timestamp: new Date().toISOString() })
        await saveState(outputDir, state)
        await generateFinalReport(outputDir, state, config, 'target_met')
        if (rl) rl.close()
        process.exit(0)
      }

      // Step 2: Expert Diff Analyst
      console.log('\n[Step 2/3] Running Expert Diff Analyst...')
      const diffAnalystResult = await runExpertDiffAnalyst(iterNum, analysisReport, iterOutputDir)

      // Step 3: Animation Expert (include human feedback if available)
      console.log('\n[Step 3/3] Running Animation Expert...')

      // Include human feedback in the expert prompt if available
      let expertAnalysis = diffAnalystResult.output || null
      if (state.humanFeedback) {
        expertAnalysis = `## Human Feedback (Priority)\n\n${state.humanFeedback}\n\n---\n\n${expertAnalysis || ''}`
        // Clear feedback after use
        state.humanFeedback = null
        await saveState(outputDir, state)
      }

      // Extract score history for regression detection
      const scoreHistory = state.history
        .filter(h => h.score !== undefined)
        .map(h => h.score)

      const expertResult = await runAnimationExpert(
        iterNum, baselineSpecPath, referenceDir,
        analysisReport?.summary || null, expertAnalysis, iterOutputDir, false, scoreHistory,
        state.referenceFrameCount || 12
      )

      const iterDuration = ((Date.now() - iterStartTime) / 1000).toFixed(1)
      state.history.push({
        iteration: iterNum, score, diffAnalystRan: diffAnalystResult.success,
        expertRan: expertResult.success, duration: `${iterDuration}s`,
        timestamp: new Date().toISOString(), outputDir: iterOutputDir,
      })
      await saveState(outputDir, state)

      console.log(`\n  Iteration ${iterNum} Complete. Score: ${score}/100`)

      // Check for interrupt
      if (isInterrupted) {
        isInterrupted = false
        break // Exit inner loop to prompt for feedback
      }

      await new Promise(r => setTimeout(r, 2000))
    }

    // If we exited the inner loop due to interrupt, continue outer loop to prompt
    if (state.currentIteration >= config.maxIterations) {
      // Max reached again, will prompt in next outer loop iteration
    }
  }
}

// Generate final report
async function generateFinalReport(outputDir, state, config, reason) {
  const reportPath = path.join(outputDir, 'FINAL-REPORT.md')

  let recommendations = []
  let problemAreas = []
  let latestMetrics = {}

  const lastIter = state.history.filter(h => h.score !== undefined).pop()
  if (lastIter?.outputDir) {
    try {
      const analysisPath = path.join(lastIter.outputDir, 'comprehensive-analysis.json')
      const data = await fs.readFile(analysisPath, 'utf-8')
      const analysis = JSON.parse(data)
      recommendations = analysis.summary?.recommendations || []
      problemAreas = analysis.summary?.problemAreas || []
      latestMetrics = analysis.summary?.metrics || {}
    } catch {}
  }

  const scoredIterations = state.history.filter(h => h.score !== undefined)
  const scoreHistory = scoredIterations.map(h => `${h.iteration}: ${h.score}/100`).join(' → ')
  const bestScore = scoredIterations.length > 0
    ? Math.max(...scoredIterations.map(h => h.score))
    : 0

  let report = `# Animation Diff - Final Report

**Generated:** ${new Date().toISOString()}
**Status:** ${reason === 'target_met' ? '✓ TARGET MET' : '⚠ HUMAN REVIEW NEEDED'}
**Iterations:** ${state.currentIteration}/${config.maxIterations}

## Workflow Used (v4.2 - Score History & Regression Detection)

1. **Phase 0**: Baseline Analyst generated spec from reference (ALWAYS)
2. **Phase 1**: Animation Expert made first implementation (spec + reference frames)
3. **Loop**: Diff Tools → Expert Diff Analyst → Animation Expert

## Baseline Specification

The ground truth document for this run:
\`${BASELINE_SPEC_PATH}\`

## Score Summary

| Metric | Value |
|--------|-------|
| Final Score | ${lastIter?.score || 'N/A'}/100 |
| Target Score | ${config.target}/100 |
| Best Score | ${bestScore}/100 |

### Score Progression
\`\`\`
${scoreHistory || 'No scored iterations yet'}
\`\`\`

## Latest Metrics

| Metric | Value |
|--------|-------|
| Pixel Match | ${latestMetrics.pixelMatch || 'N/A'} |
| Masked Match | ${latestMetrics.maskedMatch || 'N/A'} |
| SSIM | ${latestMetrics.ssim || 'N/A'} |
| Edge Match | ${latestMetrics.edgeMatch || 'N/A'} |

`

  if (problemAreas.length > 0) {
    report += `## Problem Areas

| Region | Affected Frames |
|--------|-----------------|
${problemAreas.map(a => `| ${a.region} | ${a.frequency} |`).join('\n')}

`
  }

  if (recommendations.length > 0) {
    report += `## Recommendations

${recommendations.map((r, i) => `${i + 1}. ${r}`).join('\n')}

`
  }

  report += `## Iteration History

| Iter | Phase | Score | Expert | Duration |
|------|-------|-------|--------|----------|
${state.history.map(h => `| ${h.iteration} | ${h.phase} | ${h.score || '-'}/100 | ${h.expertRan ? 'Yes' : 'No'} | ${h.duration || '-'} |`).join('\n')}

## Output Structure

\`\`\`
${outputDir}/
├── FINAL-REPORT.md
├── iteration-state.json
├── baseline-analysis/
│   ├── baseline-analysis-raw.json
│   └── reference/
├── capture-output/
│   ├── reference/
│   └── live/
└── iteration-N/
    ├── diff_*.png
    ├── heat_*.png
    ├── comprehensive-analysis.json
    ├── iteration-N-expert-prompt.md
    └── iteration-N-expert-output.md
\`\`\`

## Next Steps

${reason === 'target_met' ? `
Animation has reached ${config.target}% similarity!

Verify quality:
1. Visual inspection at http://localhost:${config.port}/?diff=capture
2. Review heat maps in latest iteration folder
3. Compare against baseline spec requirements
` : `
Manual intervention needed:

1. Review the baseline spec: \`${BASELINE_SPEC_PATH}\`
2. Check heat maps in \`${outputDir}/iteration-${state.currentIteration}/\`
3. Read Expert Diff Analyst outputs for detailed visual analysis
4. Read Animation Expert outputs for attempted fixes
5. Make manual adjustments

To restart completely fresh:
\`\`\`bash
rm -rf "${outputDir}"
node scripts/diff-iteration-orchestrator.mjs
\`\`\`
`}

---
*Generated by diff-iteration-orchestrator.mjs v4.2*
`

  await fs.writeFile(reportPath, report)
  console.log(`\n📄 Final report: ${reportPath}`)

  if (recommendations.length > 0) {
    console.log('\n📋 Key Recommendations:')
    recommendations.slice(0, 3).forEach((r, i) => console.log(`   ${i + 1}. ${r}`))
  }
}

main().catch(err => {
  console.error('Orchestrator error:', err)
  process.exit(1)
})
