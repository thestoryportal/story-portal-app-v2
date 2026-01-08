/**
 * Test Mocks
 *
 * Mock implementations and utilities for testing agent client.
 * Provides vi.fn() mocks for all agentClient methods.
 */

import { vi } from 'vitest'
import type {
  DesignReviewRequest,
  DesignReview,
  ComponentGenerationRequest,
  GeneratedComponent,
  CodeReviewRequest,
  CodeReview,
  AnimationOptimizationRequest,
  AnimationOptimization,
  AgentStatus,
  AgentResponse,
  AgentFeedback,
} from '@/api/types'
import * as fixtures from './fixtures'

/**
 * Mock agentClient for testing
 */
export const createMockAgentClient = () => ({
  requestDesignReview: vi.fn<
    [DesignReviewRequest],
    Promise<AgentResponse<DesignReview>>
  >((request) =>
    Promise.resolve({
      data: fixtures.createMockDesignReview(),
      status: 'success' as const,
      timestamp: new Date().toISOString(),
      agentId: 'l19-design-agent',
    })
  ),

  generateComponent: vi.fn<
    [ComponentGenerationRequest],
    Promise<AgentResponse<GeneratedComponent>>
  >((request) =>
    Promise.resolve({
      data: fixtures.createMockGeneratedComponent({
        fileName: `${request.componentName}.tsx`,
      }),
      status: 'success' as const,
      timestamp: new Date().toISOString(),
      agentId: 'l20-frontend-agent',
    })
  ),

  reviewCode: vi.fn<
    [CodeReviewRequest],
    Promise<AgentResponse<CodeReview>>
  >((request) =>
    Promise.resolve({
      data: fixtures.createMockCodeReview(),
      status: 'success' as const,
      timestamp: new Date().toISOString(),
      agentId: 'l20-code-review-agent',
    })
  ),

  optimizeAnimation: vi.fn<
    [AnimationOptimizationRequest],
    Promise<AgentResponse<AnimationOptimization>>
  >((request) =>
    Promise.resolve({
      data: fixtures.createMockAnimationOptimization(),
      status: 'success' as const,
      timestamp: new Date().toISOString(),
      agentId: 'l20-animation-agent',
    })
  ),

  getAgentStatus: vi.fn<
    [string],
    Promise<AgentResponse<AgentStatus>>
  >((agentId) =>
    Promise.resolve({
      data: fixtures.getAgentStatusByLayerId(agentId),
      status: 'success' as const,
      timestamp: new Date().toISOString(),
    })
  ),

  listAgents: vi.fn<
    [],
    Promise<AgentResponse<AgentStatus[]>>
  >(() =>
    Promise.resolve({
      data: [
        fixtures.mockL19DesignAgentStatus,
        fixtures.mockL20FrontendAgentStatus,
        fixtures.mockL20CodeReviewAgentStatus,
        fixtures.mockL20AnimationAgentStatus,
      ],
      status: 'success' as const,
      timestamp: new Date().toISOString(),
    })
  ),

  submitFeedback: vi.fn<
    [string, AgentFeedback],
    Promise<AgentResponse<void>>
  >((agentId, feedback) =>
    Promise.resolve({
      data: undefined,
      status: 'success' as const,
      timestamp: new Date().toISOString(),
    })
  ),
})

/**
 * Create a mock agentClient that returns errors
 */
export const createErrorAgentClient = (errorMessage: string = 'Agent error') => ({
  requestDesignReview: vi.fn(() =>
    Promise.reject(new Error(errorMessage))
  ),

  generateComponent: vi.fn(() =>
    Promise.reject(new Error(errorMessage))
  ),

  reviewCode: vi.fn(() =>
    Promise.reject(new Error(errorMessage))
  ),

  optimizeAnimation: vi.fn(() =>
    Promise.reject(new Error(errorMessage))
  ),

  getAgentStatus: vi.fn(() =>
    Promise.reject(new Error(errorMessage))
  ),

  listAgents: vi.fn(() =>
    Promise.reject(new Error(errorMessage))
  ),

  submitFeedback: vi.fn(() =>
    Promise.reject(new Error(errorMessage))
  ),
})

/**
 * Create a mock agentClient with delayed responses
 * (simulates network latency)
 */
export const createDelayedAgentClient = (delayMs: number = 500) => ({
  requestDesignReview: vi.fn<
    [DesignReviewRequest],
    Promise<AgentResponse<DesignReview>>
  >((request) =>
    new Promise((resolve) =>
      setTimeout(
        () =>
          resolve({
            data: fixtures.createMockDesignReview(),
            status: 'success' as const,
            timestamp: new Date().toISOString(),
            agentId: 'l19-design-agent',
          }),
        delayMs
      )
    )
  ),

  generateComponent: vi.fn<
    [ComponentGenerationRequest],
    Promise<AgentResponse<GeneratedComponent>>
  >((request) =>
    new Promise((resolve) =>
      setTimeout(
        () =>
          resolve({
            data: fixtures.createMockGeneratedComponent({
              fileName: `${request.componentName}.tsx`,
            }),
            status: 'success' as const,
            timestamp: new Date().toISOString(),
            agentId: 'l20-frontend-agent',
          }),
        delayMs
      )
    )
  ),

  reviewCode: vi.fn<
    [CodeReviewRequest],
    Promise<AgentResponse<CodeReview>>
  >((request) =>
    new Promise((resolve) =>
      setTimeout(
        () =>
          resolve({
            data: fixtures.createMockCodeReview(),
            status: 'success' as const,
            timestamp: new Date().toISOString(),
            agentId: 'l20-code-review-agent',
          }),
        delayMs
      )
    )
  ),

  optimizeAnimation: vi.fn<
    [AnimationOptimizationRequest],
    Promise<AgentResponse<AnimationOptimization>>
  >((request) =>
    new Promise((resolve) =>
      setTimeout(
        () =>
          resolve({
            data: fixtures.createMockAnimationOptimization(),
            status: 'success' as const,
            timestamp: new Date().toISOString(),
            agentId: 'l20-animation-agent',
          }),
        delayMs
      )
    )
  ),

  getAgentStatus: vi.fn<
    [string],
    Promise<AgentResponse<AgentStatus>>
  >((agentId) =>
    new Promise((resolve) =>
      setTimeout(
        () =>
          resolve({
            data: fixtures.getAgentStatusByLayerId(agentId),
            status: 'success' as const,
            timestamp: new Date().toISOString(),
          }),
        delayMs
      )
    )
  ),

  listAgents: vi.fn<
    [],
    Promise<AgentResponse<AgentStatus[]>>
  >(() =>
    new Promise((resolve) =>
      setTimeout(
        () =>
          resolve({
            data: [
              fixtures.mockL19DesignAgentStatus,
              fixtures.mockL20FrontendAgentStatus,
              fixtures.mockL20CodeReviewAgentStatus,
              fixtures.mockL20AnimationAgentStatus,
            ],
            status: 'success' as const,
            timestamp: new Date().toISOString(),
          }),
        delayMs
      )
    )
  ),

  submitFeedback: vi.fn<
    [string, AgentFeedback],
    Promise<AgentResponse<void>>
  >((agentId, feedback) =>
    new Promise((resolve) =>
      setTimeout(
        () =>
          resolve({
            data: undefined,
            status: 'success' as const,
            timestamp: new Date().toISOString(),
          }),
        delayMs
      )
    )
  ),
})

/**
 * Mock fetch for testing API calls
 */
export const createMockFetch = (response: any) =>
  vi.fn(() =>
    Promise.resolve({
      ok: true,
      status: 200,
      json: () => Promise.resolve(response),
      text: () => Promise.resolve(JSON.stringify(response)),
    } as Response)
  )

/**
 * Mock fetch that returns errors
 */
export const createErrorMockFetch = (status: number = 500, statusText: string = 'Error') =>
  vi.fn(() =>
    Promise.resolve({
      ok: false,
      status,
      statusText,
      json: () => Promise.reject(new Error(`HTTP ${status}: ${statusText}`)),
      text: () => Promise.resolve(`HTTP ${status}: ${statusText}`),
    } as Response)
  )
