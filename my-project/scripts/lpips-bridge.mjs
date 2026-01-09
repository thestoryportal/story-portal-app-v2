#!/usr/bin/env node
/**
 * LPIPS Bridge v1.0
 *
 * Node.js bridge to Python LPIPS calculator.
 * Provides perceptual quality metrics that correlate better with human perception.
 *
 * Prerequisites:
 *   Python 3.7+ with: torch, torchvision, lpips, pillow
 *   Install: pip install torch torchvision lpips pillow
 *
 * Usage:
 *   import { calculateLPIPS, isLPIPSAvailable } from './lpips-bridge.mjs'
 */

import { spawn } from 'child_process'
import { fileURLToPath } from 'url'
import path from 'path'
import fs from 'fs/promises'

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const PYTHON_SCRIPT = path.join(__dirname, 'lpips-calculator.py')

/**
 * Check if LPIPS is available (Python + dependencies installed)
 */
export async function isLPIPSAvailable() {
  try {
    const result = await checkPythonDependencies()
    return result.available
  } catch {
    return false
  }
}

/**
 * Check Python dependencies
 */
async function checkPythonDependencies() {
  return new Promise((resolve) => {
    const proc = spawn('python3', ['-c', 'import torch, lpips, PIL; print("OK")'])

    let stdout = ''
    let stderr = ''

    proc.stdout.on('data', data => { stdout += data.toString() })
    proc.stderr.on('data', data => { stderr += data.toString() })

    proc.on('close', code => {
      if (code === 0 && stdout.includes('OK')) {
        resolve({ available: true })
      } else {
        resolve({
          available: false,
          error: 'Python dependencies not installed',
          message: 'Install with: pip install torch torchvision lpips pillow',
          details: stderr
        })
      }
    })

    proc.on('error', () => {
      resolve({
        available: false,
        error: 'Python not found',
        message: 'Python 3.7+ required'
      })
    })
  })
}

/**
 * Calculate LPIPS between two images
 *
 * @param {string} image1Path - Path to first image
 * @param {string} image2Path - Path to second image
 * @param {object} options - Options { useGPU: false, timeout: 30000 }
 * @returns {Promise<object>} LPIPS result
 */
export async function calculateLPIPS(image1Path, image2Path, options = {}) {
  const {
    useGPU = false,
    timeout = 30000
  } = options

  // Check if Python script exists
  try {
    await fs.access(PYTHON_SCRIPT)
  } catch {
    return {
      error: 'LPIPS calculator script not found',
      available: false
    }
  }

  // Check if images exist
  try {
    await fs.access(image1Path)
    await fs.access(image2Path)
  } catch (err) {
    return {
      error: 'Image file not found',
      details: err.message
    }
  }

  return new Promise((resolve) => {
    const args = [PYTHON_SCRIPT, image1Path, image2Path, '--output=json']
    if (useGPU) args.push('--gpu')

    const proc = spawn('python3', args)

    let stdout = ''
    let stderr = ''

    proc.stdout.on('data', data => { stdout += data.toString() })
    proc.stderr.on('data', data => { stderr += data.toString() })

    const timeoutId = setTimeout(() => {
      proc.kill()
      resolve({
        error: 'LPIPS calculation timeout',
        timeout: timeout / 1000
      })
    }, timeout)

    proc.on('close', code => {
      clearTimeout(timeoutId)

      if (code === 0) {
        try {
          const result = JSON.parse(stdout)
          resolve(result)
        } catch {
          resolve({
            error: 'Failed to parse LPIPS output',
            stdout,
            stderr
          })
        }
      } else {
        try {
          const errorResult = JSON.parse(stdout)
          resolve(errorResult)
        } catch {
          resolve({
            error: 'LPIPS calculation failed',
            code,
            stderr
          })
        }
      }
    })

    proc.on('error', err => {
      clearTimeout(timeoutId)
      resolve({
        error: 'Failed to spawn Python process',
        details: err.message
      })
    })
  })
}

/**
 * Calculate LPIPS for multiple frame pairs
 *
 * @param {Array} framePairs - Array of {ref, live} paths
 * @param {object} options - Options
 * @returns {Promise<object>} Aggregate LPIPS results
 */
export async function calculateLPIPSSequence(framePairs, options = {}) {
  const results = []
  let totalDistance = 0
  let totalSimilarity = 0

  console.log(`[LPIPS] Analyzing ${framePairs.length} frame pairs...`)

  for (let i = 0; i < framePairs.length; i++) {
    const { ref, live } = framePairs[i]
    console.log(`  Frame ${i + 1}/${framePairs.length}...`)

    const result = await calculateLPIPS(ref, live, options)

    if (result.error) {
      console.warn(`  Warning: ${result.error}`)
      continue
    }

    results.push({
      index: i,
      refPath: ref,
      livePath: live,
      ...result
    })

    totalDistance += result.lpips_distance
    totalSimilarity += result.similarity_percent
  }

  if (results.length === 0) {
    return {
      error: 'No frames could be analyzed',
      attempted: framePairs.length
    }
  }

  const avgDistance = totalDistance / results.length
  const avgSimilarity = totalSimilarity / results.length

  return {
    frameCount: results.length,
    avgLPIPSDistance: parseFloat(avgDistance.toFixed(4)),
    avgSimilarity: parseFloat(avgSimilarity.toFixed(2)),
    perceptualQuality: classifyQuality(avgDistance),
    results,
    timestamp: new Date().toISOString()
  }
}

function classifyQuality(avgDistance) {
  if (avgDistance < 0.1) return 'EXCELLENT'
  if (avgDistance < 0.3) return 'GOOD'
  if (avgDistance < 0.6) return 'FAIR'
  return 'POOR'
}

/**
 * Get LPIPS status and installation instructions
 */
export async function getLPIPSStatus() {
  const scriptExists = await fs.access(PYTHON_SCRIPT).then(() => true).catch(() => false)
  const dependencies = await checkPythonDependencies()

  return {
    scriptPath: PYTHON_SCRIPT,
    scriptExists,
    pythonAvailable: dependencies.available,
    dependencies: dependencies.available ? 'OK' : 'MISSING',
    installInstructions: dependencies.available
      ? null
      : 'pip install torch torchvision lpips pillow',
    ready: scriptExists && dependencies.available
  }
}

export default {
  calculateLPIPS,
  calculateLPIPSSequence,
  isLPIPSAvailable,
  getLPIPSStatus
}
