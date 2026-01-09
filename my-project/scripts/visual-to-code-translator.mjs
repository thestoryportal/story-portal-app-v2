#!/usr/bin/env node
/**
 * Visual-to-Code Translation Agent v1.0
 *
 * Translates visual feedback from Diff Analyst into concrete code parameter changes.
 * Bridges the gap between "what's wrong visually" and "how to fix it in code".
 *
 * Usage:
 *   import { translateFeedback, buildParameterRecommendations } from './visual-to-code-translator.mjs'
 *
 * Capabilities:
 * - Semantic visual feedback → specific parameter changes
 * - Confidence scoring for each recommendation
 * - Priority ordering by expected impact
 * - Reasoning explanations for each change
 */

import fs from 'fs/promises'
import path from 'path'

/**
 * Translation Rules Database
 * Maps visual observations to code parameter changes
 */
const TRANSLATION_RULES = {
  // Bolt Count Rules
  boltCount: {
    patterns: [
      {
        trigger: /missing (\d+) bolts?/i,
        extract: (match) => parseInt(match[1]),
        transform: (current, extracted) => ({
          suggested: current + extracted,
          confidence: 0.95,
          reasoning: `Add ${extracted} bolts to match reference count`
        })
      },
      {
        trigger: /(\d+) (fewer|less) bolts?/i,
        extract: (match) => parseInt(match[1]),
        transform: (current, extracted) => ({
          suggested: current + extracted,
          confidence: 0.93,
          reasoning: `Increase bolt count by ${extracted}`
        })
      },
      {
        trigger: /need (\d+) more bolts?/i,
        extract: (match) => parseInt(match[1]),
        transform: (current, extracted) => ({
          suggested: current + extracted,
          confidence: 0.95,
          reasoning: `Add ${extracted} bolts as identified in visual analysis`
        })
      },
      {
        trigger: /too many bolts?.*?(\d+) extra/i,
        extract: (match) => parseInt(match[1]),
        transform: (current, extracted) => ({
          suggested: current - extracted,
          confidence: 0.90,
          reasoning: `Remove ${extracted} excess bolts`
        })
      }
    ]
  },

  // Bolt Length Rules
  boltLength: {
    patterns: [
      {
        trigger: /bolts? (?:are )?(\d+)%\s*(?:too )?short/i,
        extract: (match) => parseInt(match[1]) / 100,
        transform: (current, extracted) => ({
          suggested: Math.round(current * (1 + extracted)),
          confidence: 0.85,
          reasoning: `Increase length by ${(extracted * 100).toFixed(0)}%: ${current} → ${Math.round(current * (1 + extracted))}`
        })
      },
      {
        trigger: /bolts? (?:are )?(\d+)%\s*(?:too )?long/i,
        extract: (match) => parseInt(match[1]) / 100,
        transform: (current, extracted) => ({
          suggested: Math.round(current * (1 - extracted)),
          confidence: 0.85,
          reasoning: `Decrease length by ${(extracted * 100).toFixed(0)}%: ${current} → ${Math.round(current * (1 - extracted))}`
        })
      },
      {
        trigger: /bolts? should be (\d+)(?:px)? longer/i,
        extract: (match) => parseInt(match[1]),
        transform: (current, extracted) => ({
          suggested: current + extracted,
          confidence: 0.88,
          reasoning: `Add ${extracted}px to bolt length`
        })
      },
      {
        trigger: /increase bolt length.*?(\d+)(?:px)?/i,
        extract: (match) => parseInt(match[1]),
        transform: (current, extracted) => ({
          suggested: current + extracted,
          confidence: 0.80,
          reasoning: `Increase bolt length by ${extracted}px`
        })
      }
    ]
  },

  // Bolt Thickness Rules
  boltThickness: {
    patterns: [
      {
        trigger: /bolts? (?:are )?(\d+)%\s*(?:too )?thin/i,
        extract: (match) => parseInt(match[1]) / 100,
        transform: (current, extracted) => ({
          suggested: Math.round(current * (1 + extracted) * 10) / 10,
          confidence: 0.75,
          reasoning: `Increase thickness by ${(extracted * 100).toFixed(0)}%`
        })
      },
      {
        trigger: /bolts? (?:are )?(\d+)%\s*(?:too )?thick/i,
        extract: (match) => parseInt(match[1]) / 100,
        transform: (current, extracted) => ({
          suggested: Math.round(current * (1 - extracted) * 10) / 10,
          confidence: 0.75,
          reasoning: `Decrease thickness by ${(extracted * 100).toFixed(0)}%`
        })
      }
    ]
  },

  // Glow Opacity/Brightness Rules
  outerGlowOpacity: {
    patterns: [
      {
        trigger: /outer glow (?:is )?(\d+)%\s*(?:too )?dim/i,
        extract: (match) => parseInt(match[1]) / 100,
        transform: (current, extracted) => ({
          suggested: Math.round((current * (1 + extracted)) * 100) / 100,
          confidence: 0.78,
          reasoning: `Increase outer glow opacity by ${(extracted * 100).toFixed(0)}%`
        })
      },
      {
        trigger: /outer glow (?:is )?(\d+)%\s*(?:too )?bright/i,
        extract: (match) => parseInt(match[1]) / 100,
        transform: (current, extracted) => ({
          suggested: Math.round((current * (1 - extracted)) * 100) / 100,
          confidence: 0.78,
          reasoning: `Decrease outer glow opacity by ${(extracted * 100).toFixed(0)}%`
        })
      }
    ]
  },

  innerGlowOpacity: {
    patterns: [
      {
        trigger: /inner glow (?:is )?(\d+)%\s*(?:too )?dim/i,
        extract: (match) => parseInt(match[1]) / 100,
        transform: (current, extracted) => ({
          suggested: Math.round((current * (1 + extracted)) * 100) / 100,
          confidence: 0.78,
          reasoning: `Increase inner glow opacity by ${(extracted * 100).toFixed(0)}%`
        })
      },
      {
        trigger: /inner glow (?:is )?(\d+)%\s*(?:too )?bright/i,
        extract: (match) => parseInt(match[1]) / 100,
        transform: (current, extracted) => ({
          suggested: Math.round((current * (1 - extracted)) * 100) / 100,
          confidence: 0.78,
          reasoning: `Decrease inner glow opacity by ${(extracted * 100).toFixed(0)}%`
        })
      }
    ]
  },

  // Glow Radius Rules
  glowRadius: {
    patterns: [
      {
        trigger: /glow radius (?:is )?(\d+)(?:px)?\s*(?:too )?small/i,
        extract: (match) => parseInt(match[1]),
        transform: (current, extracted) => ({
          suggested: current + extracted,
          confidence: 0.82,
          reasoning: `Increase glow radius by ${extracted}px`
        })
      },
      {
        trigger: /glow (?:should be|needs to be) (\d+)%\s*(?:larger|bigger)/i,
        extract: (match) => parseInt(match[1]) / 100,
        transform: (current, extracted) => ({
          suggested: Math.round(current * (1 + extracted)),
          confidence: 0.80,
          reasoning: `Increase glow radius by ${(extracted * 100).toFixed(0)}%`
        })
      }
    ]
  },

  // Color Hue Rules
  coreColorHue: {
    patterns: [
      {
        trigger: /(?:color|hue) (?:is )?(?:too )?warm(?:er)?/i,
        extract: () => 5, // degrees cooler
        transform: (current, extracted) => ({
          suggested: current - extracted,
          confidence: 0.60,
          reasoning: `Shift hue ${extracted}° cooler (more yellow, less orange)`
        })
      },
      {
        trigger: /(?:color|hue) (?:is )?(?:too )?cool(?:er)?/i,
        extract: () => 5, // degrees warmer
        transform: (current, extracted) => ({
          suggested: current + extracted,
          confidence: 0.60,
          reasoning: `Shift hue ${extracted}° warmer (more orange)`
        })
      },
      {
        trigger: /(?:more|too) orange/i,
        extract: () => 5,
        transform: (current, extracted) => ({
          suggested: current - extracted,
          confidence: 0.65,
          reasoning: `Reduce orange tint by shifting hue ${extracted}° toward yellow`
        })
      },
      {
        trigger: /(?:more|too) yellow/i,
        extract: () => 5,
        transform: (current, extracted) => ({
          suggested: current + extracted,
          confidence: 0.65,
          reasoning: `Reduce yellow by shifting hue ${extracted}° toward orange`
        })
      }
    ]
  },

  // Brightness/Luminance Rules
  coreBrightness: {
    patterns: [
      {
        trigger: /core (?:is )?(\d+)%\s*(?:too )?dim/i,
        extract: (match) => parseInt(match[1]) / 100,
        transform: (current, extracted) => ({
          suggested: Math.round(current * (1 + extracted)),
          confidence: 0.72,
          reasoning: `Increase core brightness by ${(extracted * 100).toFixed(0)}%`
        })
      },
      {
        trigger: /core (?:is )?(\d+)%\s*(?:too )?bright/i,
        extract: (match) => parseInt(match[1]) / 100,
        transform: (current, extracted) => ({
          suggested: Math.round(current * (1 - extracted)),
          confidence: 0.72,
          reasoning: `Decrease core brightness by ${(extracted * 100).toFixed(0)}%`
        })
      }
    ]
  }
}

/**
 * Extract current parameter values from code files
 */
async function extractCurrentParameters(codeFiles) {
  const parameters = {}

  // Common parameter patterns in TypeScript/JavaScript
  const patterns = {
    boltCount: /(?:const|let|var)?\s*boltCount\s*[=:]\s*(\d+)/,
    boltLength: /(?:const|let|var)?\s*boltLength\s*[=:]\s*(\d+)/,
    boltThickness: /(?:const|let|var)?\s*boltThickness\s*[=:]\s*([\d.]+)/,
    outerGlowOpacity: /(?:const|let|var)?\s*outerGlowOpacity\s*[=:]\s*([\d.]+)/,
    innerGlowOpacity: /(?:const|let|var)?\s*innerGlowOpacity\s*[=:]\s*([\d.]+)/,
    glowRadius: /(?:const|let|var)?\s*glowRadius\s*[=:]\s*(\d+)/,
    coreColorHue: /(?:const|let|var)?\s*(?:hue|coreColorHue)\s*[=:]\s*(\d+)/,
    coreBrightness: /(?:const|let|var)?\s*(?:brightness|coreBrightness)\s*[=:]\s*(\d+)/
  }

  for (const file of codeFiles) {
    try {
      const content = await fs.readFile(file, 'utf-8')

      for (const [param, pattern] of Object.entries(patterns)) {
        const match = content.match(pattern)
        if (match && !parameters[param]) {
          const value = parseFloat(match[1])
          parameters[param] = { value, file, confidence: 1.0 }
        }
      }
    } catch (err) {
      console.warn(`Could not read ${file}: ${err.message}`)
    }
  }

  return parameters
}

/**
 * Translate visual feedback into parameter recommendations
 */
export function translateFeedback(visualFeedback, currentParameters) {
  const recommendations = []

  // Normalize feedback to string
  const feedbackText = typeof visualFeedback === 'string'
    ? visualFeedback
    : JSON.stringify(visualFeedback)

  // Try each parameter's translation rules
  for (const [paramName, rules] of Object.entries(TRANSLATION_RULES)) {
    for (const rule of rules.patterns) {
      const match = feedbackText.match(rule.trigger)

      if (match) {
        const extracted = rule.extract(match)
        const current = currentParameters[paramName]

        if (current !== undefined) {
          const transformation = rule.transform(current, extracted)

          recommendations.push({
            parameter: paramName,
            currentValue: current,
            suggestedValue: transformation.suggested,
            confidence: transformation.confidence,
            reasoning: transformation.reasoning,
            matchedPattern: rule.trigger.source
          })
        }
      }
    }
  }

  return recommendations
}

/**
 * Build comprehensive parameter recommendations with priority ordering
 */
export async function buildParameterRecommendations(options) {
  const {
    visualAnalysis,
    semanticAnalysis,
    codeFiles,
    impactDatabase = null
  } = options

  // Extract current parameters from code
  const currentParams = await extractCurrentParameters(codeFiles)
  const currentValues = Object.entries(currentParams).reduce((acc, [key, data]) => {
    acc[key] = data.value
    return acc
  }, {})

  // Translate visual feedback
  const visualRecommendations = translateFeedback(visualAnalysis, currentValues)

  // Translate semantic feedback if available
  let semanticRecommendations = []
  if (semanticAnalysis?.bolts) {
    const bolts = semanticAnalysis.bolts
    if (bolts.countDifference) {
      semanticRecommendations.push({
        parameter: 'boltCount',
        currentValue: currentValues.boltCount || 8,
        suggestedValue: (currentValues.boltCount || 8) + bolts.countDifference,
        confidence: 0.95,
        reasoning: `Semantic analysis: ${Math.abs(bolts.countDifference)} bolts ${bolts.countDifference > 0 ? 'missing' : 'extra'}`
      })
    }
    if (bolts.avgLengthDifferencePercent) {
      const pct = parseFloat(bolts.avgLengthDifferencePercent) / 100
      const current = currentValues.boltLength || 120
      semanticRecommendations.push({
        parameter: 'boltLength',
        currentValue: current,
        suggestedValue: Math.round(current * (1 + pct)),
        confidence: 0.88,
        reasoning: `Semantic analysis: Bolts ${pct > 0 ? 'too short' : 'too long'} by ${Math.abs(pct * 100).toFixed(0)}%`
      })
    }
  }

  // Merge and deduplicate recommendations
  const allRecommendations = [...visualRecommendations, ...semanticRecommendations]
  const merged = mergeRecommendations(allRecommendations)

  // Consult impact database if available
  if (impactDatabase) {
    for (const rec of merged) {
      const impact = impactDatabase.query({
        parameter: rec.parameter,
        currentValue: rec.currentValue,
        suggestedValue: rec.suggestedValue
      })

      if (impact) {
        rec.expectedScoreImpact = impact.expectedScoreImpact
        rec.historicalSuccess = impact.confidence
      }
    }
  }

  // Priority ordering by confidence * expected impact
  merged.sort((a, b) => {
    const scoreA = a.confidence * (a.expectedScoreImpact || 5)
    const scoreB = b.confidence * (b.expectedScoreImpact || 5)
    return scoreB - scoreA
  })

  return {
    recommendations: merged,
    priority: merged.map(r => r.parameter),
    summary: generateSummary(merged),
    confidence: merged.length > 0 ? merged[0].confidence : 0,
    estimatedScoreImprovement: merged.reduce((sum, r) => sum + (r.expectedScoreImpact || 5), 0)
  }
}

/**
 * Merge duplicate recommendations for same parameter
 */
function mergeRecommendations(recommendations) {
  const byParam = {}

  for (const rec of recommendations) {
    if (!byParam[rec.parameter]) {
      byParam[rec.parameter] = rec
    } else {
      // Take higher confidence recommendation
      if (rec.confidence > byParam[rec.parameter].confidence) {
        byParam[rec.parameter] = rec
      }
    }
  }

  return Object.values(byParam)
}

/**
 * Generate human-readable summary
 */
function generateSummary(recommendations) {
  if (recommendations.length === 0) {
    return "No specific parameter recommendations identified from feedback."
  }

  const lines = recommendations.map(rec =>
    `${rec.parameter}: ${rec.currentValue} → ${rec.suggestedValue} (confidence: ${(rec.confidence * 100).toFixed(0)}%)`
  )

  return lines.join('\n')
}

/**
 * Format recommendations for Animation Expert prompt
 */
export function formatForPrompt(recommendationsResult) {
  const { recommendations, estimatedScoreImprovement } = recommendationsResult

  if (recommendations.length === 0) {
    return "No specific parameter changes recommended. Review visual feedback and make informed adjustments."
  }

  let output = `## 🎯 PARAMETER RECOMMENDATIONS (Visual-to-Code Translation)\n\n`
  output += `**Estimated Score Improvement**: +${estimatedScoreImprovement.toFixed(1)} points\n\n`

  for (let i = 0; i < recommendations.length; i++) {
    const rec = recommendations[i]
    const priority = i === 0 ? '🔥 HIGHEST PRIORITY' : i === 1 ? '⚡ HIGH PRIORITY' : '📌 RECOMMENDED'

    output += `### ${priority}: ${rec.parameter}\n`
    output += `- **Current**: ${rec.currentValue}\n`
    output += `- **Suggested**: ${rec.suggestedValue}\n`
    output += `- **Confidence**: ${(rec.confidence * 100).toFixed(0)}%\n`
    output += `- **Reasoning**: ${rec.reasoning}\n`

    if (rec.expectedScoreImpact) {
      output += `- **Expected Impact**: +${rec.expectedScoreImpact.toFixed(1)} points\n`
    }

    output += `\n`
  }

  output += `---\n\n`
  output += `**Implementation Priority**: ${recommendations.map((r, i) => `${i+1}. ${r.parameter}`).join(', ')}\n\n`
  output += `These recommendations are derived from visual and semantic analysis. Apply them systematically, testing after each change.\n`

  return output
}

export default {
  translateFeedback,
  buildParameterRecommendations,
  formatForPrompt
}
