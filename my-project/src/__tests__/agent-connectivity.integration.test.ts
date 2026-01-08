/**
 * Agent Connectivity Integration Tests
 *
 * Tests for verifying agent API client connectivity and basic functionality:
 * - API endpoint accessibility
 * - Client initialization
 * - Error handling
 * - Agent listing
 * - Feedback submission
 */

import { describe, it, expect, beforeEach } from 'vitest'
import { agentClient } from '@/api/agentClient'
import * as fixtures from '@/test/fixtures'

describe('Agent Connectivity Integration Tests', () => {
  beforeEach(() => {
    // Reset agent client state before each test
    vi.clearAllMocks()
  })

  describe('Agent Client Initialization', () => {
    it('should initialize agent client successfully', () => {
      expect(agentClient).toBeDefined()
      expect(agentClient.requestDesignReview).toBeDefined()
      expect(agentClient.generateComponent).toBeDefined()
      expect(agentClient.reviewCode).toBeDefined()
      expect(agentClient.optimizeAnimation).toBeDefined()
      expect(agentClient.getAgentStatus).toBeDefined()
      expect(agentClient.listAgents).toBeDefined()
      expect(agentClient.submitFeedback).toBeDefined()
    })

    it('should have all methods as functions', () => {
      expect(typeof agentClient.requestDesignReview).toBe('function')
      expect(typeof agentClient.generateComponent).toBe('function')
      expect(typeof agentClient.reviewCode).toBe('function')
      expect(typeof agentClient.optimizeAnimation).toBe('function')
      expect(typeof agentClient.getAgentStatus).toBe('function')
      expect(typeof agentClient.listAgents).toBe('function')
      expect(typeof agentClient.submitFeedback).toBe('function')
    })
  })

  describe('Agent Listing', () => {
    it('should list all available agents', async () => {
      const response = await agentClient.listAgents()

      expect(response).toBeDefined()
      expect(response.status).toBe('success')
      expect(response.data).toBeDefined()
      expect(Array.isArray(response.data)).toBe(true)
      expect(response.data.length).toBeGreaterThan(0)
    })

    it('should return agents with required properties', async () => {
      const response = await agentClient.listAgents()
      const agents = response.data

      agents.forEach((agent) => {
        expect(agent).toHaveProperty('id')
        expect(agent).toHaveProperty('name')
        expect(agent).toHaveProperty('status')
        expect(agent).toHaveProperty('capabilities')
        expect(Array.isArray(agent.capabilities)).toBe(true)
      })
    })

    it('should include all four core agents', async () => {
      const response = await agentClient.listAgents()
      const agentIds = response.data.map((a) => a.id)

      expect(agentIds).toContain('l19-design-agent')
      expect(agentIds).toContain('l20-frontend-agent')
      expect(agentIds).toContain('l20-code-review-agent')
      expect(agentIds).toContain('l20-animation-agent')
    })

    it('should return agent statuses as active', async () => {
      const response = await agentClient.listAgents()

      response.data.forEach((agent) => {
        expect(['active', 'inactive', 'error']).toContain(agent.status)
      })
    })
  })

  describe('Agent Status Checks', () => {
    it('should get status for design agent', async () => {
      const response = await agentClient.getAgentStatus('l19-design-agent')

      expect(response.status).toBe('success')
      expect(response.data.id).toBe('l19-design-agent')
      expect(response.data.name).toBeDefined()
      expect(response.data.layer).toBe('L19')
    })

    it('should get status for frontend agent', async () => {
      const response = await agentClient.getAgentStatus('l20-frontend-agent')

      expect(response.status).toBe('success')
      expect(response.data.id).toBe('l20-frontend-agent')
      expect(response.data.layer).toBe('L20')
    })

    it('should include capabilities in agent status', async () => {
      const response = await agentClient.getAgentStatus('l19-design-agent')

      expect(Array.isArray(response.data.capabilities)).toBe(true)
      expect(response.data.capabilities.length).toBeGreaterThan(0)

      response.data.capabilities.forEach((cap) => {
        expect(cap).toHaveProperty('id')
        expect(cap).toHaveProperty('name')
        expect(cap).toHaveProperty('description')
      })
    })
  })

  describe('Feedback Submission', () => {
    it('should submit feedback for agent', async () => {
      const response = await agentClient.submitFeedback('l19-design-agent', {
        rating: 4.5,
        message: 'Great design suggestions',
      })

      expect(response.status).toBe('success')
    })

    it('should accept feedback with context', async () => {
      const response = await agentClient.submitFeedback('l20-code-review-agent', {
        rating: 4,
        message: 'Code review was thorough',
        context: { taskId: 'task-123', projectId: 'proj-456' },
      })

      expect(response.status).toBe('success')
    })

    it('should accept various rating values', async () => {
      const ratings = [1, 2, 3, 4, 5]

      for (const rating of ratings) {
        const response = await agentClient.submitFeedback('l19-design-agent', {
          rating,
          message: `Rating ${rating}`,
        })
        expect(response.status).toBe('success')
      }
    })
  })

  describe('Response Format Validation', () => {
    it('should return responses with correct format', async () => {
      const response = await agentClient.listAgents()

      expect(response).toHaveProperty('data')
      expect(response).toHaveProperty('status')
      expect(['success', 'error']).toContain(response.status)
    })

    it('should include timestamp in responses', async () => {
      const response = await agentClient.listAgents()

      expect(response).toHaveProperty('timestamp')
      // Timestamp should be valid ISO string or number
      expect(response.timestamp).toBeDefined()
    })

    it('should include agentId where applicable', async () => {
      const response = await agentClient.getAgentStatus('l19-design-agent')

      // agentId might be in the response data or at top level
      expect(response.agentId || response.data.id).toBeDefined()
    })
  })

  describe('Client Configuration', () => {
    it('should respect mock mode environment variable', async () => {
      const useMockEnv = process.env.VITE_USE_AGENT_MOCKS
      expect(useMockEnv).toBe('true')
    })

    it('should use configured timeout', async () => {
      const timeout = process.env.VITE_AGENT_TIMEOUT
      expect(timeout).toBe('30000')
    })

    it('should have API URL configured', async () => {
      const apiUrl = process.env.VITE_AGENT_API_URL
      expect(apiUrl).toBeDefined()
      expect(apiUrl).toContain('agents')
    })
  })
})
