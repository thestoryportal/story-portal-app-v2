#!/usr/bin/env node
/**
 * Animation Code Pattern Library v1.0
 *
 * Curated library of working animation code patterns with proven results.
 * Enables code reuse and bootstrapping from successful implementations.
 *
 * Pattern Categories:
 * - Bolt Generation
 * - Glow Effects
 * - Animation Timing
 * - Color Composition
 *
 * Usage:
 *   import { PatternLibrary, searchPatterns } from './animation-pattern-library.mjs'
 */

import fs from 'fs/promises'
import path from 'path'
import { fileURLToPath } from 'url'

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const PATTERNS_DIR = path.join(__dirname, 'animation-patterns')

export class AnimationPatternLibrary {
  constructor() {
    this.patterns = []
  }

  /**
   * Load all patterns from directory
   */
  async load() {
    try {
      const files = await fs.readdir(PATTERNS_DIR)
      const jsonFiles = files.filter(f => f.endsWith('.json'))

      for (const file of jsonFiles) {
        const content = await fs.readFile(path.join(PATTERNS_DIR, file), 'utf-8')
        const pattern = JSON.parse(content)
        this.patterns.push(pattern)
      }

      return this.patterns.length
    } catch (err) {
      console.warn(`Could not load patterns: ${err.message}`)
      return 0
    }
  }

  /**
   * Search patterns by description or characteristics
   */
  search(query) {
    const searchTerms = query.toLowerCase().split(' ')

    return this.patterns
      .map(pattern => {
        let score = 0

        // Match against name
        if (searchTerms.some(term => pattern.name.toLowerCase().includes(term))) {
          score += 10
        }

        // Match against description
        if (searchTerms.some(term => pattern.description?.toLowerCase().includes(term))) {
          score += 5
        }

        // Match against visual characteristics
        if (pattern.visualCharacteristics) {
          const charLower = pattern.visualCharacteristics.toLowerCase()
          searchTerms.forEach(term => {
            if (charLower.includes(term)) score += 3
          })
        }

        // Match against use case
        if (pattern.useCase) {
          const useCaseLower = pattern.useCase.toLowerCase()
          searchTerms.forEach(term => {
            if (useCaseLower.includes(term)) score += 4
          })
        }

        // Match against tags
        if (pattern.tags) {
          searchTerms.forEach(term => {
            if (pattern.tags.some(tag => tag.toLowerCase().includes(term))) {
              score += 6
            }
          })
        }

        return { pattern, score }
      })
      .filter(result => result.score > 0)
      .sort((a, b) => b.score - a.score)
      .map(result => result.pattern)
  }

  /**
   * Get pattern by ID
   */
  getById(id) {
    return this.patterns.find(p => p.id === id)
  }

  /**
   * Get patterns by category
   */
  getByCategory(category) {
    return this.patterns.filter(p => p.category === category)
  }

  /**
   * Add new pattern
   */
  async addPattern(pattern) {
    const id = pattern.id || `pattern_${Date.now()}`
    const filename = `${id}.json`

    pattern.id = id
    pattern.addedAt = new Date().toISOString()

    await fs.writeFile(
      path.join(PATTERNS_DIR, filename),
      JSON.stringify(pattern, null, 2)
    )

    this.patterns.push(pattern)
    return id
  }

  /**
   * Format pattern for code insertion
   */
  formatForCode(patternId, parameters = {}) {
    const pattern = this.getById(patternId)
    if (!pattern) return null

    let code = pattern.code

    // Replace parameter placeholders
    for (const [key, value] of Object.entries(parameters)) {
      const placeholder = new RegExp(`\\{${key}\\}`, 'g')
      code = code.replace(placeholder, value)
    }

    return {
      code,
      imports: pattern.imports || [],
      notes: pattern.implementationNotes || []
    }
  }

  /**
   * Get recommended patterns for a use case
   */
  getRecommendations(useCase, limit = 3) {
    const results = this.search(useCase)
      .filter(p => p.provenEffectiveness > 0.8)
      .slice(0, limit)

    return results.map(p => ({
      id: p.id,
      name: p.name,
      description: p.description,
      effectiveness: p.provenEffectiveness,
      usedInProjects: p.usedInProjects || 0
    }))
  }
}

/**
 * Quick pattern search function
 */
export async function searchPatterns(query) {
  const library = new AnimationPatternLibrary()
  await library.load()
  return library.search(query)
}

/**
 * Get pattern by ID
 */
export async function getPattern(id) {
  const library = new AnimationPatternLibrary()
  await library.load()
  return library.getById(id)
}

export default {
  AnimationPatternLibrary,
  searchPatterns,
  getPattern
}
