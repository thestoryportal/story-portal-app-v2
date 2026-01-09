#!/usr/bin/env node
/**
 * Multi-Agent Specialist Coordinator v1.0
 *
 * Orchestrates multiple specialist agents for animation tasks:
 * - Bolt Specialist: Lightning generation, paths, distribution
 * - Glow Specialist: Glow effects, radial gradients
 * - Color Specialist: Color accuracy, hue, saturation
 * - Timing Specialist: Animation timing, easing
 * - Coordinator: Routes tasks and merges recommendations
 *
 * Usage:
 *   import { MultiAgentCoordinator } from './multi-agent-coordinator.mjs'
 */

import { formatForPrompt as formatDomainKnowledge } from './animation-domain-prompts.mjs'

export class MultiAgentCoordinator {
  constructor() {
    this.specialists = {
      bolt: new BoltSpecialist(),
      glow: new GlowSpecialist(),
      color: new ColorSpecialist(),
      timing: new TimingSpecialist()
    }
  }

  /**
   * Analyze feedback and route to appropriate specialists
   */
  analyzeFeedback(feedback) {
    const issues = this.categor

izeIssues(feedback)

    return {
      bolt: issues.bolt,
      glow: issues.glow,
      color: issues.color,
      timing: issues.timing
    }
  }

  /**
   * Categorize issues by specialist domain
   */
  categorizeIssues(feedback) {
    const text = typeof feedback === 'string' ? feedback : JSON.stringify(feedback)
    const lower = text.toLowerCase()

    return {
      bolt: this.extractBoltIssues(lower),
      glow: this.extractGlowIssues(lower),
      color: this.extractColorIssues(lower),
      timing: this.extractTimingIssues(lower)
    }
  }

  extractBoltIssues(text) {
    const issues = []
    if (text.includes('bolt') && (text.includes('count') || text.includes('missing') || text.includes('extra'))) {
      issues.push({ type: 'count', severity: 'high' })
    }
    if (text.includes('bolt') && (text.includes('length') || text.includes('short') || text.includes('long'))) {
      issues.push({ type: 'length', severity: 'high' })
    }
    if (text.includes('bolt') && (text.includes('thickness') || text.includes('thin') || text.includes('thick'))) {
      issues.push({ type: 'thickness', severity: 'medium' })
    }
    if (text.includes('distribution') || text.includes('lopsided') || text.includes('uneven')) {
      issues.push({ type: 'distribution', severity: 'medium' })
    }
    return issues
  }

  extractGlowIssues(text) {
    const issues = []
    if (text.includes('glow') && (text.includes('dim') || text.includes('bright') || text.includes('opacity'))) {
      issues.push({ type: 'opacity', severity: 'high' })
    }
    if (text.includes('glow') && (text.includes('radius') || text.includes('size') || text.includes('small') || text.includes('large'))) {
      issues.push({ type: 'radius', severity: 'medium' })
    }
    if (text.includes('glow') && (text.includes('falloff') || text.includes('gradient'))) {
      issues.push({ type: 'falloff', severity: 'low' })
    }
    return issues
  }

  extractColorIssues(text) {
    const issues = []
    if (text.includes('color') || text.includes('hue') || text.includes('warm') || text.includes('cool') || text.includes('orange') || text.includes('yellow')) {
      issues.push({ type: 'hue', severity: 'medium' })
    }
    if (text.includes('saturation') || text.includes('vivid') || text.includes('muted') || text.includes('washed')) {
      issues.push({ type: 'saturation', severity: 'medium' })
    }
    if (text.includes('brightness') || text.includes('luminance')) {
      issues.push({ type: 'brightness', severity: 'high' })
    }
    return issues
  }

  extractTimingIssues(text) {
    const issues = []
    if (text.includes('timing') || text.includes('speed') || text.includes('fast') || text.includes('slow')) {
      issues.push({ type: 'speed', severity: 'medium' })
    }
    if (text.includes('flicker') || text.includes('jitter') || text.includes('stutter')) {
      issues.push({ type: 'smoothness', severity: 'high' })
    }
    return issues
  }

  /**
   * Get recommendations from all relevant specialists
   */
  async getRecommendations(feedback, currentCode) {
    const categorized = this.analyzeFeedback(feedback)
    const recommendations = []

    // Bolt specialist
    if (categorized.bolt.length > 0) {
      const boltRec = await this.specialists.bolt.analyze(categorized.bolt, currentCode)
      recommendations.push(...boltRec)
    }

    // Glow specialist
    if (categorized.glow.length > 0) {
      const glowRec = await this.specialists.glow.analyze(categorized.glow, currentCode)
      recommendations.push(...glowRec)
    }

    // Color specialist
    if (categorized.color.length > 0) {
      const colorRec = await this.specialists.color.analyze(categorized.color, currentCode)
      recommendations.push(...colorRec)
    }

    // Timing specialist
    if (categorized.timing.length > 0) {
      const timingRec = await this.specialists.timing.analyze(categorized.timing, currentCode)
      recommendations.push(...timingRec)
    }

    // Merge and resolve conflicts
    return this.mergeRecommendations(recommendations)
  }

  /**
   * Merge recommendations and resolve conflicts
   */
  mergeRecommendations(recommendations) {
    // Group by parameter
    const byParam = {}

    for (const rec of recommendations) {
      if (!byParam[rec.parameter]) {
        byParam[rec.parameter] = []
      }
      byParam[rec.parameter].push(rec)
    }

    // Resolve conflicts (take highest confidence)
    const merged = []

    for (const [param, recs] of Object.entries(byParam)) {
      if (recs.length === 1) {
        merged.push(recs[0])
      } else {
        // Multiple specialists recommend changes to same parameter
        // Take highest confidence, or average if similar confidence
        recs.sort((a, b) => b.confidence - a.confidence)

        if (recs[0].confidence - recs[1].confidence > 0.2) {
          // Clear winner
          merged.push(recs[0])
        } else {
          // Similar confidence - average the recommendations
          const avgValue = recs.reduce((sum, r) => sum + r.suggestedValue, 0) / recs.length
          merged.push({
            ...recs[0],
            suggestedValue: Math.round(avgValue * 100) / 100,
            confidence: (recs[0].confidence + recs[1].confidence) / 2,
            note: `Averaged from ${recs.length} specialist recommendations`
          })
        }
      }
    }

    // Sort by confidence
    merged.sort((a, b) => b.confidence - a.confidence)

    return merged
  }

  /**
   * Generate specialist prompts
   */
  generateSpecialistPrompt(specialistType, issues, feedback) {
    const baseKnowledge = formatDomainKnowledge(specialistType + '-specialist')

    return `# ${specialistType.toUpperCase()} SPECIALIST AGENT

You are a specialist in ${specialistType} aspects of animation.

${baseKnowledge}

## Issues to Address

${issues.map(i => `- ${i.type} (${i.severity} severity)`).join('\n')}

## Full Feedback

${typeof feedback === 'string' ? feedback : JSON.stringify(feedback, null, 2)}

## Your Task

Analyze the issues in your domain and provide specific parameter recommendations.

Output format:
{
  "recommendations": [
    {
      "parameter": "parameterName",
      "currentValue": 100,
      "suggestedValue": 120,
      "confidence": 0.85,
      "reasoning": "explanation"
    }
  ]
}
`
  }
}

/**
 * Bolt Specialist
 */
class BoltSpecialist {
  async analyze(issues, currentCode) {
    const recommendations = []

    for (const issue of issues) {
      if (issue.type === 'count') {
        recommendations.push({
          specialist: 'bolt',
          parameter: 'boltCount',
          suggestedValue: 12, // Default good value
          confidence: 0.85,
          reasoning: 'Bolt count issue detected'
        })
      } else if (issue.type === 'length') {
        recommendations.push({
          specialist: 'bolt',
          parameter: 'boltLength',
          suggestedValue: 145,
          confidence: 0.80,
          reasoning: 'Bolt length adjustment needed'
        })
      } else if (issue.type === 'distribution') {
        recommendations.push({
          specialist: 'bolt',
          parameter: 'angleOffset',
          suggestedValue: 15,
          confidence: 0.70,
          reasoning: 'Rotation adjustment for better distribution'
        })
      }
    }

    return recommendations
  }
}

/**
 * Glow Specialist
 */
class GlowSpecialist {
  async analyze(issues, currentCode) {
    const recommendations = []

    for (const issue of issues) {
      if (issue.type === 'opacity') {
        recommendations.push({
          specialist: 'glow',
          parameter: 'outerGlowOpacity',
          suggestedValue: 0.42,
          confidence: 0.82,
          reasoning: 'Glow opacity adjustment needed'
        })
      } else if (issue.type === 'radius') {
        recommendations.push({
          specialist: 'glow',
          parameter: 'glowRadius',
          suggestedValue: 180,
          confidence: 0.75,
          reasoning: 'Glow radius adjustment needed'
        })
      }
    }

    return recommendations
  }
}

/**
 * Color Specialist
 */
class ColorSpecialist {
  async analyze(issues, currentCode) {
    const recommendations = []

    for (const issue of issues) {
      if (issue.type === 'hue') {
        recommendations.push({
          specialist: 'color',
          parameter: 'coreColorHue',
          suggestedValue: 38,
          confidence: 0.65,
          reasoning: 'Hue shift needed based on color feedback'
        })
      } else if (issue.type === 'saturation') {
        recommendations.push({
          specialist: 'color',
          parameter: 'coreSaturation',
          suggestedValue: 90,
          confidence: 0.70,
          reasoning: 'Saturation adjustment needed'
        })
      }
    }

    return recommendations
  }
}

/**
 * Timing Specialist
 */
class TimingSpecialist {
  async analyze(issues, currentCode) {
    const recommendations = []

    for (const issue of issues) {
      if (issue.type === 'speed') {
        recommendations.push({
          specialist: 'timing',
          parameter: 'animationSpeed',
          suggestedValue: 1.2,
          confidence: 0.75,
          reasoning: 'Animation speed adjustment needed'
        })
      } else if (issue.type === 'smoothness') {
        recommendations.push({
          specialist: 'timing',
          parameter: 'easingFunction',
          suggestedValue: 'ease-in-out',
          confidence: 0.80,
          reasoning: 'Easing function change for smoother motion'
        })
      }
    }

    return recommendations
  }
}

export default { MultiAgentCoordinator }
