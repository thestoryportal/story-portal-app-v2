/**
 * Test Fixtures
 *
 * Mock data and fixtures for integration tests.
 * Provides realistic test data for all agent types.
 */

import type {
  DesignReview,
  DesignSuggestion,
  GeneratedComponent,
  CodeReview,
  CodeIssue,
  CodeReviewSuggestion,
  TestCoverageInfo,
  AnimationOptimization,
  CurrentPerformanceMetrics,
  Optimization,
  AgentStatus,
  AgentCapability,
  AgentResponse,
  AgentFeedback,
  DesignReviewRequest,
  ComponentGenerationRequest,
  CodeReviewRequest,
  AnimationOptimizationRequest,
} from '@/api/types'

/**
 * Design Review Fixtures
 */
export const designSuggestions: DesignSuggestion[] = [
  {
    id: 'ds-1',
    category: 'accessibility',
    priority: 'high',
    text: 'Add aria-labels to form inputs for better screen reader support',
    code: `<input aria-label="Email address" type="email" />`,
  },
  {
    id: 'ds-2',
    category: 'spacing',
    priority: 'medium',
    text: 'Increase padding on form fields from 8px to 12px for better touch targets',
    cssCode: `.form-input { padding: 12px; }`,
  },
  {
    id: 'ds-3',
    category: 'color-contrast',
    priority: 'high',
    text: 'Increase contrast between button text and background (current: 3:1, target: 4.5:1)',
    code: 'Button: #333 on #0066cc → #fff on #0052a3',
  },
  {
    id: 'ds-4',
    category: 'typography',
    priority: 'low',
    text: 'Consider increasing line-height to 1.6 for better readability',
    cssCode: `body { line-height: 1.6; }`,
  },
]

export const mockDesignReview: DesignReview = {
  suggestions: designSuggestions,
  overallAssessment:
    'Design has good structure but needs improvements in accessibility and spacing. Mobile responsiveness is solid.',
}

export const mockDesignReviewRequest: DesignReviewRequest = {
  componentPath: 'src/components/BookingForm.tsx',
  focusArea: 'accessibility',
  context: 'Reviewing BookingForm component for accessibility compliance',
}

/**
 * Component Generation Fixtures
 */
export const mockGeneratedComponent: GeneratedComponent = {
  code: `import React from 'react'
import styles from './UserCard.module.css'

interface UserCardProps {
  userId: string
  userName: string
  avatar?: string
  onFollow?: () => void
}

export const UserCard: React.FC<UserCardProps> = ({
  userId,
  userName,
  avatar,
  onFollow,
}) => {
  return (
    <div className={styles.card}>
      <img src={avatar} alt={userName} className={styles.avatar} />
      <h3 className={styles.name}>{userName}</h3>
      <button className={styles.followBtn} onClick={onFollow}>
        Follow
      </button>
    </div>
  )
}`,
  types: `export interface UserCardProps {
  userId: string
  userName: string
  avatar?: string
  onFollow?: () => void
}

export interface User {
  id: string
  name: string
  avatar?: string
}`,
  imports: [
    "import React from 'react'",
    "import { useCallback } from 'react'",
    "import styles from './UserCard.module.css'",
  ],
  fileName: 'UserCard.tsx',
  testCode: `import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { UserCard } from './UserCard'

describe('UserCard', () => {
  it('renders user name', () => {
    render(<UserCard userId="1" userName="John Doe" />)
    expect(screen.getByText('John Doe')).toBeDefined()
  })

  it('calls onFollow when button clicked', () => {
    const onFollow = vi.fn()
    render(
      <UserCard userId="1" userName="John Doe" onFollow={onFollow} />
    )
    screen.getByText('Follow').click()
    expect(onFollow).toHaveBeenCalled()
  })
})`,
}

export const mockComponentGenerationRequest: ComponentGenerationRequest = {
  componentName: 'UserCard',
  type: 'component',
  description: 'A card component displaying user profile with follow button',
  basedOn: 'React 18 + TypeScript + CSS Modules',
}

/**
 * Code Review Fixtures
 */
export const codeReviewIssues: CodeIssue[] = [
  {
    severity: 'critical',
    line: 45,
    message: 'API key exposed in source code',
    suggestion: 'Move to environment variable: const apiKey = process.env.API_KEY',
  },
  {
    severity: 'high',
    line: 78,
    message: 'Missing error handling for async operation',
    suggestion: 'Add try/catch block around fetch call',
  },
  {
    severity: 'medium',
    line: 120,
    message: 'Unused variable: tempData',
    suggestion: 'Remove unused variable or use it',
  },
  {
    severity: 'low',
    line: 5,
    message: 'Import not used: lodash.debounce',
    suggestion: 'Remove unused import',
  },
]

export const codeReviewSuggestions: CodeReviewSuggestion[] = [
  {
    priority: 'high',
    category: 'performance',
    text: 'Consider memoizing expensive calculations using useMemo',
  },
  {
    priority: 'medium',
    category: 'best-practices',
    text: 'Use const instead of let where values are not reassigned',
  },
  {
    priority: 'low',
    category: 'style',
    text: 'Function names should use camelCase (getCurrentUser vs get_current_user)',
  },
]

export const testCoverage: TestCoverageInfo = {
  current: 65,
  suggested: 85,
  gap: 20,
}

export const mockCodeReview: CodeReview = {
  issues: codeReviewIssues,
  suggestions: codeReviewSuggestions,
  testCoverage,
  testSuggestions: [
    'Add unit tests for getCurrentUser function',
    'Add integration tests for API communication',
    'Add E2E tests for user authentication flow',
  ],
  overallQuality: 'Good structure, needs better error handling and security review',
}

export const mockCodeReviewRequest: CodeReviewRequest = {
  filePath: 'src/services/userService.ts',
  reviewFocus: ['security', 'performance', 'testing'],
  severity: 'all',
}

/**
 * Animation Optimization Fixtures
 */
export const mockCurrentPerformance: CurrentPerformanceMetrics = {
  fps: 35,
  avgFrameTime: 28.5,
  gpuMemory: '512MB',
  bottleneck: 'shader-complexity',
}

export const mockOptimizations: Optimization[] = [
  {
    priority: 'high',
    change: 'Reduce polygon count from 100k to 50k',
    impact: 'Expected 20-25 FPS increase',
    code: 'geometry.simplify({ target: 0.5 })',
  },
  {
    priority: 'high',
    change: 'Use simpler shader for ambient occlusion',
    impact: 'Expected 10-15 FPS increase',
    code: 'material.aoMap = simpleAOTexture',
  },
  {
    priority: 'medium',
    change: 'Enable frustum culling',
    impact: 'Expected 3-5 FPS increase',
    code: 'camera.updateMatrix(); frustumCulling.update(camera)',
  },
  {
    priority: 'low',
    change: 'Use instancing for repeated objects',
    impact: 'Expected 2-3 FPS increase',
    code: 'THREE.InstancedMesh usage',
  },
]

export const mockAnimationOptimization: AnimationOptimization = {
  currentPerformance: mockCurrentPerformance,
  optimizations: mockOptimizations,
  expectedResult: 'Achieve 55-60 FPS with optimizations applied',
}

export const mockAnimationOptimizationRequest: AnimationOptimizationRequest = {
  filePath: 'src/components/3DScene.tsx',
  targetPerformance: { fps: 60, targetFrameTime: 16.67 },
  constraints: ['maintain-visual-quality', 'support-mobile'],
}

/**
 * Agent Status Fixtures
 */
export const designAgentCapabilities: AgentCapability[] = [
  { id: 'ac-1', name: 'UI Analysis', description: 'Analyze UI components for design issues' },
  { id: 'ac-2', name: 'Accessibility Review', description: 'Review accessibility compliance' },
  { id: 'ac-3', name: 'Design Suggestions', description: 'Provide design improvement suggestions' },
]

export const frontendAgentCapabilities: AgentCapability[] = [
  { id: 'fc-1', name: 'Component Generation', description: 'Generate React components' },
  { id: 'fc-2', name: 'TypeScript Support', description: 'Generate typed components' },
  { id: 'fc-3', name: 'Test Generation', description: 'Generate component tests' },
]

export const codeReviewAgentCapabilities: AgentCapability[] = [
  { id: 'cc-1', name: 'Code Quality', description: 'Review code quality' },
  { id: 'cc-2', name: 'Security Review', description: 'Identify security issues' },
  { id: 'cc-3', name: 'Performance Analysis', description: 'Analyze performance issues' },
]

export const animationAgentCapabilities: AgentCapability[] = [
  { id: 'ac-1', name: 'Performance Analysis', description: 'Analyze animation performance' },
  { id: 'ac-2', name: 'Optimization', description: 'Suggest animation optimizations' },
  { id: 'ac-3', name: '3D Graphics', description: 'Optimize 3D graphics performance' },
]

export const mockL19DesignAgentStatus: AgentStatus = {
  id: 'l19-design-agent',
  name: 'Design Agent',
  layer: 'L19',
  status: 'active',
  capabilities: designAgentCapabilities,
  lastHeartbeat: new Date().toISOString(),
}

export const mockL20FrontendAgentStatus: AgentStatus = {
  id: 'l20-frontend-agent',
  name: 'Frontend Agent',
  layer: 'L20',
  status: 'active',
  capabilities: frontendAgentCapabilities,
  lastHeartbeat: new Date().toISOString(),
}

export const mockL20CodeReviewAgentStatus: AgentStatus = {
  id: 'l20-code-review-agent',
  name: 'Code Review Agent',
  layer: 'L20',
  status: 'active',
  capabilities: codeReviewAgentCapabilities,
  lastHeartbeat: new Date().toISOString(),
}

export const mockL20AnimationAgentStatus: AgentStatus = {
  id: 'l20-animation-agent',
  name: 'Animation Agent',
  layer: 'L20',
  status: 'active',
  capabilities: animationAgentCapabilities,
  lastHeartbeat: new Date().toISOString(),
}

/**
 * Helper function to create agent status with proper layer mapping
 */
export const getAgentStatusByLayerId = (agentId: string): AgentStatus => {
  const statusMap: Record<string, AgentStatus> = {
    'l19-design-agent': mockL19DesignAgentStatus,
    'l20-frontend-agent': mockL20FrontendAgentStatus,
    'l20-code-review-agent': mockL20CodeReviewAgentStatus,
    'l20-animation-agent': mockL20AnimationAgentStatus,
  }
  return statusMap[agentId] || mockL19DesignAgentStatus
}

/**
 * Generic Response Wrappers
 */
export const createSuccessResponse = <T,>(data: T): AgentResponse<T> => ({
  data,
  status: 'success',
  timestamp: new Date().toISOString(),
})

export const createErrorResponse = (message: string): AgentResponse<any> => ({
  data: null,
  status: 'error',
  timestamp: new Date().toISOString(),
})

/**
 * Feedback Fixtures
 */
export const mockAgentFeedback: AgentFeedback = {
  rating: 4.5,
  message: 'Great suggestions for design improvements',
  context: {
    agentId: 'l19-design-agent',
    taskId: 'design-review-001',
  },
}

/**
 * Helper Functions for Tests
 */
export const createMockDesignReview = (overrides?: Partial<DesignReview>): DesignReview => ({
  ...mockDesignReview,
  ...overrides,
})

export const createMockGeneratedComponent = (
  overrides?: Partial<GeneratedComponent>
): GeneratedComponent => ({
  ...mockGeneratedComponent,
  ...overrides,
})

export const createMockCodeReview = (overrides?: Partial<CodeReview>): CodeReview => ({
  ...mockCodeReview,
  ...overrides,
})

export const createMockAnimationOptimization = (
  overrides?: Partial<AnimationOptimization>
): AnimationOptimization => ({
  ...mockAnimationOptimization,
  ...overrides,
})

export const createMockAgentStatus = (overrides?: Partial<AgentStatus>): AgentStatus => ({
  ...mockL19DesignAgentStatus,
  ...overrides,
})
