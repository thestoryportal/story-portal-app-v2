#!/usr/bin/env node
/**
 * Animation Knowledge Base v1.0 (Simplified)
 *
 * Stores and retrieves animation knowledge for agent reference.
 * Simplified implementation focusing on project history and FAQs.
 *
 * Full RAG with vector embeddings can be added later.
 * This version uses simple keyword matching and categorization.
 *
 * Usage:
 *   import { KnowledgeBase } from './animation-knowledge-base.mjs'
 */

import fs from 'fs/promises'

export class AnimationKnowledgeBase {
  constructor(dbPath = './animation-knowledge.json') {
    this.dbPath = dbPath
    this.knowledge = {
      faqs: [],
      projectHistory: [],
      apiReference: [],
      bestPractices: []
    }
  }

  async load() {
    try {
      const content = await fs.readFile(this.dbPath, 'utf-8')
      this.knowledge = JSON.parse(content)
    } catch {
      // Initialize with defaults
      await this.initializeDefaults()
    }
  }

  async save() {
    await fs.writeFile(this.dbPath, JSON.stringify(this.knowledge, null, 2))
  }

  /**
   * Search knowledge base
   */
  search(query, limit = 3) {
    const queryLower = query.toLowerCase()
    const results = []

    // Search FAQs
    for (const faq of this.knowledge.faqs) {
      if (faq.question.toLowerCase().includes(queryLower) ||
          faq.keywords?.some(k => queryLower.includes(k.toLowerCase()))) {
        results.push({ type: 'faq', content: faq, relevance: 1.0 })
      }
    }

    // Search project history
    for (const entry of this.knowledge.projectHistory) {
      if (entry.description?.toLowerCase().includes(queryLower)) {
        results.push({ type: 'history', content: entry, relevance: 0.8 })
      }
    }

    // Search best practices
    for (const practice of this.knowledge.bestPractices) {
      if (practice.title?.toLowerCase().includes(queryLower) ||
          practice.tags?.some(t => queryLower.includes(t.toLowerCase()))) {
        results.push({ type: 'practice', content: practice, relevance: 0.9 })
      }
    }

    return results.slice(0, limit)
  }

  /**
   * Add project history entry
   */
  async addHistoryEntry(entry) {
    this.knowledge.projectHistory.unshift({
      ...entry,
      timestamp: new Date().toISOString()
    })

    // Keep last 50 entries
    if (this.knowledge.projectHistory.length > 50) {
      this.knowledge.projectHistory = this.knowledge.projectHistory.slice(0, 50)
    }

    await this.save()
  }

  /**
   * Initialize with default knowledge
   */
  async initializeDefaults() {
    this.knowledge = {
      faqs: [
        {
          question: "How do I create a smooth radial glow?",
          answer: "Use multi-layer shadows with 'lighter' blend mode. Create 3 layers: core (high opacity, small blur), mid (medium opacity, medium blur), outer (low opacity, large blur).",
          keywords: ["glow", "radial", "smooth"]
        },
        {
          question: "Why do my bolts look lopsided?",
          answer: "Use even numbers for bolt count (8, 12, 16). Odd numbers create asymmetry. Calculate angles as (2π / boltCount) for even distribution.",
          keywords: ["bolts", "distribution", "lopsided", "uneven"]
        },
        {
          question: "How can I make colors more vibrant?",
          answer: "Use 'lighter' composite operation for glows. Avoid stacking alpha - it compounds incorrectly. Use premultiplied alpha or blend modes instead.",
          keywords: ["color", "vibrant", "washed out", "pale"]
        }
      ],
      projectHistory: [],
      apiReference: [
        {
          api: "ctx.globalCompositeOperation = 'lighter'",
          description: "Additive blending - overlapping glows intensify realistically",
          useCase: "Glow effects, energy beams, light sources"
        },
        {
          api: "ctx.shadowBlur",
          description: "Creates blur/glow effect. Expensive - use sparingly",
          useCase: "Glows, soft shadows. Keep radius < 100 for performance"
        }
      ],
      bestPractices: [
        {
          title: "Use even bolt counts",
          description: "8, 12, 16 bolts create balanced radial symmetry",
          tags: ["bolts", "distribution"]
        },
        {
          title: "Multi-layer glows",
          description: "3-5 layers create realistic depth. Single layer looks flat",
          tags: ["glow", "depth"]
        }
      ]
    }

    await this.save()
  }

  /**
   * Format search results for prompt
   */
  formatResults(results) {
    if (results.length === 0) {
      return "No relevant knowledge found."
    }

    let output = "## 📚 Knowledge Base Results\n\n"

    for (const result of results) {
      if (result.type === 'faq') {
        output += `**Q: ${result.content.question}**\n`
        output += `A: ${result.content.answer}\n\n`
      } else if (result.type === 'history') {
        output += `**History:** ${result.content.description}\n`
        if (result.content.outcome) {
          output += `Outcome: ${result.content.outcome}\n`
        }
        output += `\n`
      } else if (result.type === 'practice') {
        output += `**Best Practice:** ${result.content.title}\n`
        output += `${result.content.description}\n\n`
      }
    }

    return output
  }
}

export default { AnimationKnowledgeBase }
