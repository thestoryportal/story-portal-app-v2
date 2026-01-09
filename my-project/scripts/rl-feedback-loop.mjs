#!/usr/bin/env node
/**
 * Reinforcement Learning Feedback Loop v1.0
 *
 * Prompt-based RL (no model training required).
 * Records reward history and injects learnings into agent prompts.
 *
 * Reward Signal:
 * - Score increase: +delta
 * - Score decrease: -delta
 * - Reached target: +50 bonus
 * - Fixed critical issue: +10
 * - Wrong direction: -5
 *
 * Usage:
 *   import { RLFeedbackLoop } from './rl-feedback-loop.mjs'
 */

import fs from 'fs/promises'

export class RLFeedbackLoop {
  constructor(dbPath = './rl-feedback.json') {
    this.dbPath = dbPath
    this.data = {
      experiences: [],
      learnings: [],
      statistics: {
        totalExperiences: 0,
        avgReward: 0,
        bestAction: null,
        worstAction: null
      }
    }
  }

  async load() {
    try {
      const content = await fs.readFile(this.dbPath, 'utf-8')
      this.data = JSON.parse(content)
    } catch {
      // New database
    }
  }

  async save() {
    await fs.writeFile(this.dbPath, JSON.stringify(this.data, null, 2))
  }

  /**
   * Record an experience (state, action, reward)
   */
  async recordExperience(experience) {
    const {
      iteration,
      state, // Current animation state (parameters)
      action, // What was changed
      scoreBefore,
      scoreAfter,
      targetReached,
      criticalIssueFixed
    } = experience

    // Calculate reward
    const scoreDelta = scoreAfter - scoreBefore
    let reward = scoreDelta

    if (targetReached) {
      reward += 50
    }

    if (criticalIssueFixed) {
      reward += 10
    }

    if (scoreDelta < -5) {
      reward -= 5 // Penalty for wrong direction
    }

    const record = {
      id: `exp_${Date.now()}`,
      timestamp: new Date().toISOString(),
      iteration,
      state,
      action,
      scoreBefore,
      scoreAfter,
      scoreDelta,
      reward,
      targetReached: targetReached || false,
      criticalIssueFixed: criticalIssueFixed || false
    }

    this.data.experiences.push(record)

    // Update statistics
    this.updateStatistics(record)

    // Extract learnings
    this.extractLearnings()

    await this.save()

    return record.id
  }

  /**
   * Update statistics
   */
  updateStatistics(record) {
    const stats = this.data.statistics

    stats.totalExperiences++

    // Update average reward
    stats.avgReward = (stats.avgReward * (stats.totalExperiences - 1) + record.reward) / stats.totalExperiences

    // Track best action
    if (!stats.bestAction || record.reward > stats.bestAction.reward) {
      stats.bestAction = {
        action: record.action,
        reward: record.reward,
        scoreDelta: record.scoreDelta
      }
    }

    // Track worst action
    if (!stats.worstAction || record.reward < stats.worstAction.reward) {
      stats.worstAction = {
        action: record.action,
        reward: record.reward,
        scoreDelta: record.scoreDelta
      }
    }
  }

  /**
   * Extract learnings from experience history
   */
  extractLearnings() {
    const learnings = []

    // Learning 1: Actions that consistently improve score
    const actionGroups = {}
    for (const exp of this.data.experiences) {
      const actionKey = JSON.stringify(exp.action)
      if (!actionGroups[actionKey]) {
        actionGroups[actionKey] = []
      }
      actionGroups[actionKey].push(exp)
    }

    for (const [actionKey, exps] of Object.entries(actionGroups)) {
      if (exps.length >= 2) {
        const avgReward = exps.reduce((sum, e) => sum + e.reward, 0) / exps.length

        if (avgReward > 5) {
          const action = JSON.parse(actionKey)
          learnings.push({
            type: 'positive',
            lesson: `${action.description || 'Action'} typically improves score by +${avgReward.toFixed(1)} (${exps.length} observations)`,
            confidence: Math.min(exps.length / 5, 1.0)
          })
        } else if (avgReward < -5) {
          const action = JSON.parse(actionKey)
          learnings.push({
            type: 'negative',
            lesson: `AVOID: ${action.description || 'Action'} typically decreases score by ${avgReward.toFixed(1)} (${exps.length} observations)`,
            confidence: Math.min(exps.length / 5, 1.0)
          })
        }
      }
    }

    // Learning 2: Parameter ranges that work well
    const parameterSuccesses = {}
    for (const exp of this.data.experiences.filter(e => e.reward > 5)) {
      if (exp.state) {
        for (const [param, value] of Object.entries(exp.state)) {
          if (!parameterSuccesses[param]) {
            parameterSuccesses[param] = []
          }
          parameterSuccesses[param].push(value)
        }
      }
    }

    for (const [param, values] of Object.entries(parameterSuccesses)) {
      if (values.length >= 3) {
        const min = Math.min(...values)
        const max = Math.max(...values)
        const avg = values.reduce((sum, v) => sum + v, 0) / values.length

        learnings.push({
          type: 'range',
          lesson: `${param} works well in range ${min.toFixed(0)}-${max.toFixed(0)} (avg: ${avg.toFixed(0)})`,
          confidence: Math.min(values.length / 10, 0.9)
        })
      }
    }

    // Learning 3: Sequential patterns (what to do after what)
    if (this.data.experiences.length >= 4) {
      const recent = this.data.experiences.slice(-4)
      const successfulSequence = recent.every(e => e.scoreDelta > 0)

      if (successfulSequence) {
        const sequence = recent.map(e => e.action.description || 'action').join(' → ')
        learnings.push({
          type: 'sequence',
          lesson: `Successful sequence: ${sequence}`,
          confidence: 0.7
        })
      }
    }

    this.data.learnings = learnings
  }

  /**
   * Get relevant lessons for current state
   */
  getRelevantLessons(currentState, limit = 5) {
    // Filter high-confidence learnings
    const relevant = this.data.learnings
      .filter(l => l.confidence > 0.5)
      .sort((a, b) => b.confidence - a.confidence)
      .slice(0, limit)

    return relevant
  }

  /**
   * Format lessons for prompt injection
   */
  formatLessonsForPrompt(currentState) {
    const lessons = this.getRelevantLessons(currentState)

    if (lessons.length === 0) {
      return "No RL learnings available yet."
    }

    let output = `## 🧠 REINFORCEMENT LEARNING INSIGHTS\n\n`
    output += `Based on ${this.data.statistics.totalExperiences} past experiences:\n\n`

    for (const lesson of lessons) {
      const emoji = lesson.type === 'positive' ? '✅' :
                    lesson.type === 'negative' ? '❌' :
                    lesson.type === 'range' ? '📊' : '🔄'

      output += `${emoji} ${lesson.lesson} (confidence: ${(lesson.confidence * 100).toFixed(0)}%)\n`
    }

    output += `\n### Best Action Ever\n`
    if (this.data.statistics.bestAction) {
      output += `${JSON.stringify(this.data.statistics.bestAction.action, null, 2)}\n`
      output += `Reward: +${this.data.statistics.bestAction.reward.toFixed(1)} (Score: +${this.data.statistics.bestAction.scoreDelta})\n`
    } else {
      output += `No best action recorded yet.\n`
    }

    output += `\n### Worst Action (AVOID)\n`
    if (this.data.statistics.worstAction) {
      output += `${JSON.stringify(this.data.statistics.worstAction.action, null, 2)}\n`
      output += `Reward: ${this.data.statistics.worstAction.reward.toFixed(1)} (Score: ${this.data.statistics.worstAction.scoreDelta})\n`
    } else {
      output += `No worst action recorded yet.\n`
    }

    output += `\n**Use these insights to guide your next actions.**\n`

    return output
  }

  /**
   * Clear all data (for testing)
   */
  async clear() {
    this.data = {
      experiences: [],
      learnings: [],
      statistics: {
        totalExperiences: 0,
        avgReward: 0,
        bestAction: null,
        worstAction: null
      }
    }
    await this.save()
  }
}

/**
 * Helper: Record iteration as RL experience
 */
export async function recordIteration(options) {
  const {
    iteration,
    parametersBefore,
    parametersAfter,
    scoreBefore,
    scoreAfter,
    targetReached,
    criticalIssueFixed,
    dbPath
  } = options

  const rl = new RLFeedbackLoop(dbPath)
  await rl.load()

  // Determine what changed
  const changes = []
  for (const [param, valueBefore] of Object.entries(parametersBefore)) {
    const valueAfter = parametersAfter[param]
    if (valueAfter !== undefined && valueBefore !== valueAfter) {
      changes.push(`${param}: ${valueBefore} → ${valueAfter}`)
    }
  }

  await rl.recordExperience({
    iteration,
    state: parametersBefore,
    action: {
      description: changes.join(', '),
      parameters: parametersAfter
    },
    scoreBefore,
    scoreAfter,
    targetReached,
    criticalIssueFixed
  })

  return rl.data.statistics
}

export default {
  RLFeedbackLoop,
  recordIteration
}
