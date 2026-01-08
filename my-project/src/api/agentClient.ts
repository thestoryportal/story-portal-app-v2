/**
 * Agent API Client
 *
 * Handles all communication with the agentic platform agents.
 * Provides type-safe methods for:
 * - Design reviews (L19 Design Agent)
 * - Component generation (L20 Frontend Agent)
 * - Code reviews (L20 Code Review Agent)
 * - Animation optimization (L20 Animation Agent)
 */

import type {
  DesignReviewRequest,
  DesignReview,
  ComponentGenerationRequest,
  GeneratedComponent,
  CodeReviewRequest,
  CodeReview,
  AnimationOptimizationRequest,
  AnimationOptimization,
  AgentResponse,
  AgentStatus,
  AgentFeedback,
} from './types'

export class AgentApiError extends Error {
  constructor(
    public statusCode: number,
    public agentId?: string,
    message?: string
  ) {
    super(message || `Agent API error: ${statusCode}`)
    this.name = 'AgentApiError'
  }
}

export interface AgentClientConfig {
  baseUrl?: string
  timeout?: number
  retries?: number
  useMock?: boolean
}

class AgentClient {
  private baseUrl: string
  private timeout: number
  private retries: number
  private useMock: boolean

  constructor(config: AgentClientConfig = {}) {
    this.baseUrl = config.baseUrl || this.getBaseUrl()
    this.timeout = config.timeout || 30000 // 30s for agent operations
    this.retries = config.retries || 2
    this.useMock = config.useMock ?? this.shouldUseMock()
  }

  /**
   * Determine if we should use mock API (development environment)
   */
  private shouldUseMock(): boolean {
    return import.meta.env.VITE_USE_AGENT_MOCKS === 'true'
  }

  /**
   * Get base URL from environment or default
   */
  private getBaseUrl(): string {
    return import.meta.env.VITE_AGENT_API_URL || 'http://localhost:8000/api'
  }

  /**
   * Request design review for a component.
   * Uses: L19 Design Agent
   *
   * @param request - Design review request with component path and focus area
   * @returns Design suggestions and overall assessment
   */
  async requestDesignReview(
    request: DesignReviewRequest
  ): Promise<AgentResponse<DesignReview>> {
    if (this.useMock) {
      return this.mockDesignReview(request)
    }

    return this.apiRequest<DesignReview>('/agents/design/review', {
      method: 'POST',
      body: JSON.stringify(request),
    })
  }

  /**
   * Generate a new component based on patterns.
   * Uses: L20 Frontend Agent
   *
   * @param request - Component generation request with name, type, description
   * @returns Generated component code with types and imports
   */
  async generateComponent(
    request: ComponentGenerationRequest
  ): Promise<AgentResponse<GeneratedComponent>> {
    if (this.useMock) {
      return this.mockGenerateComponent(request)
    }

    return this.apiRequest<GeneratedComponent>('/agents/frontend/generate-component', {
      method: 'POST',
      body: JSON.stringify(request),
    })
  }

  /**
   * Request code review and refactoring suggestions.
   * Uses: L20 Code Review Agent
   *
   * @param request - Code review request with file path and focus areas
   * @returns Code issues, suggestions, and test coverage analysis
   */
  async reviewCode(
    request: CodeReviewRequest
  ): Promise<AgentResponse<CodeReview>> {
    if (this.useMock) {
      return this.mockCodeReview(request)
    }

    return this.apiRequest<CodeReview>('/agents/code-review/review', {
      method: 'POST',
      body: JSON.stringify(request),
    })
  }

  /**
   * Request animation optimization or creation.
   * Uses: L20 Animation Agent
   *
   * @param request - Animation optimization request with file path and performance targets
   * @returns Current performance metrics and optimization suggestions
   */
  async optimizeAnimation(
    request: AnimationOptimizationRequest
  ): Promise<AgentResponse<AnimationOptimization>> {
    if (this.useMock) {
      return this.mockAnimationOptimization(request)
    }

    return this.apiRequest<AnimationOptimization>('/agents/animation/optimize', {
      method: 'POST',
      body: JSON.stringify(request),
    })
  }

  /**
   * Get agent status and capabilities.
   *
   * @param agentId - Agent ID to check (e.g., 'l19-design', 'l20-frontend')
   * @returns Agent status with capabilities and health info
   */
  async getAgentStatus(agentId: string): Promise<AgentResponse<AgentStatus>> {
    if (this.useMock) {
      return this.mockGetAgentStatus(agentId)
    }

    return this.apiRequest<AgentStatus>(`/agents/${agentId}/status`, {
      method: 'GET',
    })
  }

  /**
   * List all available agents.
   *
   * @returns Array of available agents with status
   */
  async listAgents(): Promise<AgentResponse<AgentStatus[]>> {
    if (this.useMock) {
      return this.mockListAgents()
    }

    return this.apiRequest<AgentStatus[]>('/agents', {
      method: 'GET',
    })
  }

  /**
   * Submit feedback about an agent interaction.
   *
   * @param agentId - Agent ID that received feedback
   * @param feedback - User feedback with rating and message
   * @returns Success confirmation
   */
  async submitFeedback(
    agentId: string,
    feedback: AgentFeedback
  ): Promise<AgentResponse<void>> {
    if (this.useMock) {
      return this.mockSubmitFeedback(agentId, feedback)
    }

    return this.apiRequest<void>(`/agents/${agentId}/feedback`, {
      method: 'POST',
      body: JSON.stringify(feedback),
    })
  }

  /**
   * Core API request method with retry logic
   */
  private async apiRequest<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<AgentResponse<T>> {
    let lastError: Error | null = null

    for (let attempt = 0; attempt < this.retries; attempt++) {
      try {
        const controller = new AbortController()
        const timeoutId = setTimeout(() => controller.abort(), this.timeout)

        const response = await fetch(`${this.baseUrl}${endpoint}`, {
          ...options,
          signal: controller.signal,
          headers: {
            'Content-Type': 'application/json',
            'X-Source': 'story-portal-app',
            ...options.headers,
          },
        })

        clearTimeout(timeoutId)

        if (!response.ok) {
          throw new AgentApiError(response.status, undefined, response.statusText)
        }

        const data = await response.json()
        return data as AgentResponse<T>
      } catch (error) {
        lastError = error instanceof Error ? error : new Error(String(error))

        // Don't retry on client errors (4xx)
        if (error instanceof AgentApiError && error.statusCode >= 400 && error.statusCode < 500) {
          throw error
        }

        // Wait before retry
        if (attempt < this.retries - 1) {
          await this.delay(Math.pow(2, attempt) * 1000)
        }
      }
    }

    throw lastError || new Error('Failed to complete agent request')
  }

  /**
   * Simple delay utility for retries
   */
  private delay(ms: number): Promise<void> {
    return new Promise((resolve) => setTimeout(resolve, ms))
  }

  /**
   * ==========================================
   * MOCK IMPLEMENTATIONS (Development)
   * ==========================================
   */

  private mockDesignReview(request: DesignReviewRequest): Promise<AgentResponse<DesignReview>> {
    return new Promise((resolve) => {
      setTimeout(() => {
        const response: AgentResponse<DesignReview> = {
          data: {
            suggestions: [
              {
                id: 'mock-design-1',
                category: 'Button Styling',
                priority: 'medium',
                text: 'Add hover state feedback for buttons',
                cssCode:
                  'button { transition: all 0.2s ease; } button:hover { transform: scale(1.02); }',
              },
              {
                id: 'mock-design-2',
                category: 'Accessibility',
                priority: 'high',
                text: 'Add aria-label to interactive elements',
                htmlCode: '<button aria-label="Submit form">Submit</button>',
              },
              {
                id: 'mock-design-3',
                category: 'Spacing',
                priority: 'low',
                text: 'Increase vertical spacing between form fields for better readability',
                cssCode: '.form-field { margin-bottom: 20px; }',
              },
            ],
            overallAssessment: `Component ${request.componentPath} has good structure. Suggestions focus on improving visual feedback and accessibility.`,
          },
          status: 'success',
          timestamp: new Date().toISOString(),
          agentId: 'l19-design-agent',
        }
        console.log('[Mock] Design review:', response)
        resolve(response)
      }, 2000) // Simulate agent processing time
    })
  }

  private mockGenerateComponent(
    request: ComponentGenerationRequest
  ): Promise<AgentResponse<GeneratedComponent>> {
    return new Promise((resolve) => {
      setTimeout(() => {
        const response: AgentResponse<GeneratedComponent> = {
          data: {
            code: `import React, { useState, useEffect } from 'react'
import type { Props } from '@/types'
import styles from './${request.componentName}.module.css'

interface ${request.componentName}Props {
  title?: string
  onClose?: () => void
}

export function ${request.componentName}({ title, onClose }: ${request.componentName}Props) {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    // Component initialization logic
  }, [])

  return (
    <div className={styles.container}>
      {title && <h1>{title}</h1>}
      {/* Component content */}
    </div>
  )
}
`,
            types: `export interface ${request.componentName}Props {
  title?: string
  onClose?: () => void
}`,
            imports: [
              "import React, { useState, useEffect } from 'react'",
              `import styles from './${request.componentName}.module.css'`,
            ],
            fileName: `${request.componentName}.tsx`,
            testCode: `import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { ${request.componentName} } from './${request.componentName}'

describe('${request.componentName}', () => {
  it('should render component', () => {
    render(<${request.componentName} />)
    expect(screen.getByRole('region')).toBeInTheDocument()
  })
})`,
          },
          status: 'success',
          timestamp: new Date().toISOString(),
          agentId: 'l20-frontend-agent',
        }
        console.log('[Mock] Component generated:', response)
        resolve(response)
      }, 3000) // Simulate longer generation time
    })
  }

  private mockCodeReview(request: CodeReviewRequest): Promise<AgentResponse<CodeReview>> {
    return new Promise((resolve) => {
      setTimeout(() => {
        const response: AgentResponse<CodeReview> = {
          data: {
            issues: [
              {
                severity: 'medium',
                line: 45,
                message: 'Missing return type annotation',
                suggestion: 'Add explicit return type: `: ReviewResult =>` at function signature',
              },
              {
                severity: 'low',
                line: 78,
                message: 'Unused variable: tempVar',
                suggestion: 'Remove unused variable or use it in the logic',
              },
            ],
            suggestions: [
              {
                priority: 'high',
                category: 'Type Safety',
                text: 'Add strict null checks to all conditional statements',
              },
              {
                priority: 'medium',
                category: 'Performance',
                text: 'Consider memoizing expensive calculations with useMemo',
              },
              {
                priority: 'low',
                category: 'Code Quality',
                text: 'Extract repeated logic into a helper function',
              },
            ],
            testCoverage: {
              current: 45,
              suggested: 75,
              gap: 30,
            },
            testSuggestions: [
              'Test component with null props',
              'Test error boundary handling',
              'Test edge cases in data transformation',
            ],
            overallQuality:
              'Good - with improvements in type safety and test coverage recommended',
          },
          status: 'success',
          timestamp: new Date().toISOString(),
          agentId: 'l20-code-review-agent',
        }
        console.log('[Mock] Code review:', response)
        resolve(response)
      }, 2500) // Simulate code review time
    })
  }

  private mockAnimationOptimization(
    request: AnimationOptimizationRequest
  ): Promise<AgentResponse<AnimationOptimization>> {
    return new Promise((resolve) => {
      setTimeout(() => {
        const response: AgentResponse<AnimationOptimization> = {
          data: {
            currentPerformance: {
              fps: 35,
              avgFrameTime: 28.6,
              gpuMemory: '165MB',
              bottleneck: 'Post-processing effects',
            },
            optimizations: [
              {
                priority: 'high',
                change: 'Reduce bloom post-processing quality',
                impact: '+18 FPS',
                code: 'const bloom = new UnrealBloomPass(resolution, 1.3, 0.4, 0.85);',
              },
              {
                priority: 'medium',
                change: 'Simplify particle geometry',
                impact: '+10 FPS',
                code: 'geometry.setAttribute("position", new THREE.BufferAttribute(positions, 3));',
              },
              {
                priority: 'low',
                change: 'Implement distance-based LOD',
                impact: '+5 FPS',
                code: 'const lod = new THREE.LOD(); lod.addLevel(mesh, 0);',
              },
            ],
            expectedResult: `Achieve ${request.targetPerformance.fps} FPS on modern devices after optimizations`,
          },
          status: 'success',
          timestamp: new Date().toISOString(),
          agentId: 'l20-animation-agent',
        }
        console.log('[Mock] Animation optimization:', response)
        resolve(response)
      }, 2200) // Simulate animation analysis time
    })
  }

  private mockGetAgentStatus(agentId: string): Promise<AgentResponse<AgentStatus>> {
    return new Promise((resolve) => {
      setTimeout(() => {
        const agentMap: Record<string, Omit<AgentStatus, 'id'>> = {
          'l19-design-agent': {
            name: 'Design Agent',
            layer: 'L19',
            status: 'active',
            capabilities: [
              { id: 'design-review', name: 'Design Review', description: 'Review component styling' },
              { id: 'a11y-audit', name: 'Accessibility Audit', description: 'Check accessibility' },
            ],
            lastHeartbeat: new Date().toISOString(),
          },
          'l20-frontend-agent': {
            name: 'Frontend Agent',
            layer: 'L20',
            status: 'active',
            capabilities: [
              {
                id: 'component-gen',
                name: 'Component Generation',
                description: 'Generate React components',
              },
              {
                id: 'type-gen',
                name: 'Type Generation',
                description: 'Generate TypeScript types',
              },
            ],
            lastHeartbeat: new Date().toISOString(),
          },
          'l20-animation-agent': {
            name: 'Animation Agent',
            layer: 'L20',
            status: 'active',
            capabilities: [
              {
                id: 'animation-opt',
                name: 'Animation Optimization',
                description: 'Optimize animations',
              },
              {
                id: 'perf-analysis',
                name: 'Performance Analysis',
                description: 'Analyze animation performance',
              },
            ],
            lastHeartbeat: new Date().toISOString(),
          },
          'l20-code-review-agent': {
            name: 'Code Review Agent',
            layer: 'L20',
            status: 'active',
            capabilities: [
              {
                id: 'code-review',
                name: 'Code Review',
                description: 'Review code quality',
              },
              {
                id: 'type-check',
                name: 'Type Checking',
                description: 'Check TypeScript types',
              },
            ],
            lastHeartbeat: new Date().toISOString(),
          },
        }

        const agentData = agentMap[agentId] || agentMap['l19-design-agent']

        const response: AgentResponse<AgentStatus> = {
          data: {
            id: agentId,
            ...agentData,
          },
          status: 'success',
          timestamp: new Date().toISOString(),
        }
        resolve(response)
      }, 500)
    })
  }

  private mockListAgents(): Promise<AgentResponse<AgentStatus[]>> {
    return new Promise((resolve) => {
      setTimeout(() => {
        const response: AgentResponse<AgentStatus[]> = {
          data: [
            {
              id: 'l19-design-agent',
              name: 'Design Agent',
              layer: 'L19',
              status: 'active',
              capabilities: [
                { id: 'design-review', name: 'Design Review', description: 'Review styling' },
              ],
              lastHeartbeat: new Date().toISOString(),
            },
            {
              id: 'l20-frontend-agent',
              name: 'Frontend Agent',
              layer: 'L20',
              status: 'active',
              capabilities: [
                {
                  id: 'component-gen',
                  name: 'Component Generation',
                  description: 'Generate components',
                },
              ],
              lastHeartbeat: new Date().toISOString(),
            },
            {
              id: 'l20-animation-agent',
              name: 'Animation Agent',
              layer: 'L20',
              status: 'active',
              capabilities: [
                {
                  id: 'animation-opt',
                  name: 'Animation Optimization',
                  description: 'Optimize animations',
                },
              ],
              lastHeartbeat: new Date().toISOString(),
            },
            {
              id: 'l20-code-review-agent',
              name: 'Code Review Agent',
              layer: 'L20',
              status: 'active',
              capabilities: [
                {
                  id: 'code-review',
                  name: 'Code Review',
                  description: 'Review code',
                },
              ],
              lastHeartbeat: new Date().toISOString(),
            },
          ],
          status: 'success',
          timestamp: new Date().toISOString(),
        }
        resolve(response)
      }, 600)
    })
  }

  private mockSubmitFeedback(
    agentId: string,
    _feedback: AgentFeedback
  ): Promise<AgentResponse<void>> {
    return new Promise((resolve) => {
      setTimeout(() => {
        const response: AgentResponse<void> = {
          data: undefined,
          status: 'success',
          timestamp: new Date().toISOString(),
          agentId,
        }
        console.log(`[Mock] Feedback submitted for ${agentId}`)
        resolve(response)
      }, 300)
    })
  }
}

// Export singleton instance
export const agentClient = new AgentClient({
  useMock: true, // Use mock by default in development
})

export default agentClient
