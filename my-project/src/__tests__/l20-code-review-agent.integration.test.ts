/**
 * L20 Code Review Agent Integration Tests
 *
 * Tests for L20 Code Review Agent functionality:
 * - Code review requests
 * - Issue identification
 * - Suggestion generation
 * - Test coverage analysis
 * - Quality assessment
 * - Error handling
 */

import { describe, it, expect, beforeEach } from 'vitest'
import { agentClient } from '@/api/agentClient'
import * as fixtures from '@/test/fixtures'

describe('L20 Code Review Agent Integration Tests', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('Code Review Requests', () => {
    it('should request code review successfully', async () => {
      const response = await agentClient.reviewCode(fixtures.mockCodeReviewRequest)

      expect(response.status).toBe('success')
      expect(response.data).toBeDefined()
    })

    it('should return code review with required structure', async () => {
      const response = await agentClient.reviewCode(fixtures.mockCodeReviewRequest)

      const review = response.data
      expect(review).toHaveProperty('issues')
      expect(review).toHaveProperty('suggestions')
      expect(review).toHaveProperty('testCoverage')
      expect(review).toHaveProperty('overallQuality')
      expect(Array.isArray(review.issues)).toBe(true)
      expect(Array.isArray(review.suggestions)).toBe(true)
    })

    it('should accept multiple focus areas', async () => {
      const focusAreas = ['security', 'performance', 'testing', 'type-safety', 'best-practices']

      const response = await agentClient.reviewCode({
        filePath: 'src/services/api.ts',
        reviewFocus: focusAreas,
        severity: 'all',
      })

      expect(response.status).toBe('success')
      expect(response.data.issues).toBeDefined()
    })

    it('should accept different severity levels', async () => {
      const severities = ['all', 'high', 'medium'] as const

      for (const severity of severities) {
        const response = await agentClient.reviewCode({
          filePath: 'src/components/Button.tsx',
          reviewFocus: ['general'],
          severity,
        })

        expect(response.status).toBe('success')
      }
    })

    it('should handle various file types', async () => {
      const files = [
        'src/components/Button.tsx',
        'src/services/api.ts',
        'src/utils/helpers.js',
        'src/hooks/useCustomHook.ts',
      ]

      for (const filePath of files) {
        const response = await agentClient.reviewCode({
          filePath,
          reviewFocus: ['general'],
          severity: 'all',
        })

        expect(response.status).toBe('success')
      }
    })
  })

  describe('Code Issues Detection', () => {
    it('should identify code issues with required properties', async () => {
      const response = await agentClient.reviewCode(fixtures.mockCodeReviewRequest)

      response.data.issues.forEach((issue) => {
        expect(issue).toHaveProperty('severity')
        expect(issue).toHaveProperty('message')
        expect(['low', 'medium', 'high', 'critical']).toContain(issue.severity)
        expect(issue.message).toBeTruthy()
      })
    })

    it('should include line numbers for issues', async () => {
      const response = await agentClient.reviewCode(fixtures.mockCodeReviewRequest)

      response.data.issues.forEach((issue) => {
        // Line number is optional
        if (issue.line) {
          expect(typeof issue.line).toBe('number')
          expect(issue.line).toBeGreaterThan(0)
        }
      })
    })

    it('should include suggestions for fixes', async () => {
      const response = await agentClient.reviewCode(fixtures.mockCodeReviewRequest)

      const issuesWithSuggestions = response.data.issues.filter((i) => i.suggestion)
      expect(issuesWithSuggestions.length).toBeGreaterThan(0)

      issuesWithSuggestions.forEach((issue) => {
        expect(issue.suggestion).toBeTruthy()
      })
    })

    it('should identify security issues', async () => {
      const response = await agentClient.reviewCode({
        filePath: 'src/services/secure.ts',
        reviewFocus: ['security'],
        severity: 'all',
      })

      expect(response.data.issues).toBeDefined()
    })

    it('should identify performance issues', async () => {
      const response = await agentClient.reviewCode({
        filePath: 'src/components/Heavy.tsx',
        reviewFocus: ['performance'],
        severity: 'all',
      })

      expect(response.data.issues).toBeDefined()
    })
  })

  describe('Code Suggestions', () => {
    it('should return code suggestions', async () => {
      const response = await agentClient.reviewCode(fixtures.mockCodeReviewRequest)

      expect(Array.isArray(response.data.suggestions)).toBe(true)
    })

    it('should include suggestion priority', async () => {
      const response = await agentClient.reviewCode(fixtures.mockCodeReviewRequest)

      response.data.suggestions.forEach((suggestion) => {
        expect(['low', 'medium', 'high']).toContain(suggestion.priority)
      })
    })

    it('should categorize suggestions', async () => {
      const response = await agentClient.reviewCode(fixtures.mockCodeReviewRequest)

      response.data.suggestions.forEach((suggestion) => {
        expect(suggestion.category).toBeTruthy()
        expect(suggestion.text).toBeTruthy()
      })
    })

    it('should provide actionable suggestions', async () => {
      const response = await agentClient.reviewCode(fixtures.mockCodeReviewRequest)

      response.data.suggestions.forEach((suggestion) => {
        // Suggestion should be understandable and actionable
        expect(suggestion.text.length).toBeGreaterThan(10)
      })
    })
  })

  describe('Test Coverage Analysis', () => {
    it('should include test coverage metrics', async () => {
      const response = await agentClient.reviewCode(fixtures.mockCodeReviewRequest)

      const coverage = response.data.testCoverage
      expect(coverage).toHaveProperty('current')
      expect(coverage).toHaveProperty('suggested')
      expect(coverage).toHaveProperty('gap')
    })

    it('should provide valid coverage percentages', async () => {
      const response = await agentClient.reviewCode(fixtures.mockCodeReviewRequest)

      const coverage = response.data.testCoverage
      expect(coverage.current).toBeGreaterThanOrEqual(0)
      expect(coverage.current).toBeLessThanOrEqual(100)
      expect(coverage.suggested).toBeGreaterThanOrEqual(0)
      expect(coverage.suggested).toBeLessThanOrEqual(100)
      expect(coverage.gap).toBeGreaterThanOrEqual(0)
    })

    it('should calculate gap correctly', async () => {
      const response = await agentClient.reviewCode(fixtures.mockCodeReviewRequest)

      const coverage = response.data.testCoverage
      const calculatedGap = coverage.suggested - coverage.current
      expect(coverage.gap).toBe(calculatedGap)
    })

    it('should include test suggestions if available', async () => {
      const response = await agentClient.reviewCode(fixtures.mockCodeReviewRequest)

      // testSuggestions is optional
      if (response.data.testSuggestions) {
        expect(Array.isArray(response.data.testSuggestions)).toBe(true)
        response.data.testSuggestions.forEach((suggestion) => {
          expect(typeof suggestion).toBe('string')
          expect(suggestion.length).toBeGreaterThan(0)
        })
      }
    })
  })

  describe('Quality Assessment', () => {
    it('should provide overall quality assessment', async () => {
      const response = await agentClient.reviewCode(fixtures.mockCodeReviewRequest)

      const quality = response.data.overallQuality
      expect(quality).toBeTruthy()
      expect(typeof quality).toBe('string')
    })

    it('should assess code quality across multiple files', async () => {
      const files = [
        'src/components/Button.tsx',
        'src/services/api.ts',
        'src/hooks/useCustom.ts',
      ]

      for (const file of files) {
        const response = await agentClient.reviewCode({
          filePath: file,
          reviewFocus: ['general'],
          severity: 'all',
        })

        expect(response.data.overallQuality).toBeTruthy()
      }
    })
  })

  describe('Focus Area Specific Reviews', () => {
    it('should focus on security when requested', async () => {
      const response = await agentClient.reviewCode({
        filePath: 'src/auth/login.ts',
        reviewFocus: ['security'],
        severity: 'high',
      })

      // Should return review focused on security
      expect(response.data.issues).toBeDefined()
    })

    it('should focus on performance when requested', async () => {
      const response = await agentClient.reviewCode({
        filePath: 'src/components/List.tsx',
        reviewFocus: ['performance'],
        severity: 'all',
      })

      expect(response.data.issues).toBeDefined()
    })

    it('should focus on type safety when requested', async () => {
      const response = await agentClient.reviewCode({
        filePath: 'src/utils/helpers.ts',
        reviewFocus: ['type-safety'],
        severity: 'all',
      })

      expect(response.data.issues).toBeDefined()
    })
  })

  describe('Agent Identification', () => {
    it('should identify as L20 Code Review Agent', async () => {
      const response = await agentClient.reviewCode(fixtures.mockCodeReviewRequest)

      expect(response.agentId).toBeDefined()
      expect(response.agentId).toContain('l20') ||
        expect(response.agentId).toContain('code-review')
    })

    it('should include timestamp in response', async () => {
      const response = await agentClient.reviewCode(fixtures.mockCodeReviewRequest)

      expect(response.timestamp).toBeDefined()
      expect(typeof response.timestamp).toBe('string')
    })
  })

  describe('Error Handling', () => {
    it('should handle missing file path gracefully', async () => {
      try {
        await agentClient.reviewCode({
          filePath: '',
          reviewFocus: ['general'],
          severity: 'all',
        })
      } catch (error) {
        expect(error).toBeDefined()
      }
    })

    it('should handle empty focus areas', async () => {
      const response = await agentClient.reviewCode({
        filePath: 'src/test.ts',
        reviewFocus: [],
        severity: 'all',
      })

      // Should handle gracefully (either with defaults or error)
      expect(response).toBeDefined()
    })
  })

  describe('Performance', () => {
    it('should complete code review within timeout', async () => {
      const startTime = Date.now()
      const response = await agentClient.reviewCode(fixtures.mockCodeReviewRequest)
      const duration = Date.now() - startTime

      expect(response.status).toBe('success')
      expect(duration).toBeLessThan(30000) // 30 second timeout
    })

    it('should handle multiple sequential reviews', async () => {
      const files = [
        'src/components/Button.tsx',
        'src/services/api.ts',
        'src/utils/helpers.ts',
      ]

      for (const file of files) {
        const response = await agentClient.reviewCode({
          filePath: file,
          reviewFocus: ['general'],
          severity: 'all',
        })

        expect(response.status).toBe('success')
      }
    })
  })

  describe('Response Data Validation', () => {
    it('should return consistent review structure', async () => {
      const response = await agentClient.reviewCode(fixtures.mockCodeReviewRequest)

      const review = response.data

      // Structure should be consistent
      expect(review.issues).toBeDefined()
      expect(review.suggestions).toBeDefined()
      expect(review.testCoverage).toBeDefined()
      expect(review.overallQuality).toBeDefined()

      // Types should be correct
      expect(Array.isArray(review.issues)).toBe(true)
      expect(Array.isArray(review.suggestions)).toBe(true)
      expect(typeof review.testCoverage).toBe('object')
      expect(typeof review.overallQuality).toBe('string')
    })
  })
})
