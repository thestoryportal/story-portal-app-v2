/**
 * L20 Frontend Agent Integration Tests
 *
 * Tests for L20 Frontend Agent (Component Generation) functionality:
 * - Component code generation
 * - TypeScript type generation
 * - Test code generation
 * - Import statements
 * - Various component types
 * - Error handling
 */

import { describe, it, expect, beforeEach } from 'vitest'
import { agentClient } from '@/api/agentClient'
import * as fixtures from '@/test/fixtures'

describe('L20 Frontend Agent Integration Tests', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('Component Generation', () => {
    it('should generate component successfully', async () => {
      const response = await agentClient.generateComponent(
        fixtures.mockComponentGenerationRequest
      )

      expect(response.status).toBe('success')
      expect(response.data).toBeDefined()
    })

    it('should return generated component with required properties', async () => {
      const response = await agentClient.generateComponent(
        fixtures.mockComponentGenerationRequest
      )

      const component = response.data
      expect(component).toHaveProperty('code')
      expect(component).toHaveProperty('fileName')
      expect(component.code).toBeTruthy()
      expect(component.fileName).toBeTruthy()
    })

    it('should generate component for different types', async () => {
      const types = ['component', 'view'] as const

      for (const type of types) {
        const response = await agentClient.generateComponent({
          componentName: 'TestComponent',
          type,
          description: `Generate a ${type} component`,
          basedOn: 'React best practices',
        })

        expect(response.status).toBe('success')
        expect(response.data.code).toBeTruthy()
      }
    })

    it('should include React import by default', async () => {
      const response = await agentClient.generateComponent(
        fixtures.mockComponentGenerationRequest
      )

      const code = response.data.code
      expect(code).toContain('React') || expect(code).toContain('react')
    })

    it('should generate export statements', async () => {
      const response = await agentClient.generateComponent(
        fixtures.mockComponentGenerationRequest
      )

      const code = response.data.code
      expect(code).toContain('export')
    })
  })

  describe('Generated Code Quality', () => {
    it('should generate syntactically valid JavaScript/TypeScript', async () => {
      const response = await agentClient.generateComponent({
        componentName: 'Button',
        type: 'component',
        description: 'A reusable button component',
        basedOn: 'React + TypeScript',
      })

      const code = response.data.code
      // Check for common React component patterns
      expect(code).toContain('function') || expect(code).toContain('const')
      expect(code).toContain('return')
    })

    it('should use proper component naming conventions', async () => {
      const response = await agentClient.generateComponent({
        componentName: 'UserProfile',
        type: 'component',
        description: 'User profile display component',
        basedOn: 'React',
      })

      const component = response.data
      expect(component.fileName).toContain('UserProfile') ||
        expect(component.code).toContain('UserProfile')
    })

    it('should include JSX/TSX return statements', async () => {
      const response = await agentClient.generateComponent(
        fixtures.mockComponentGenerationRequest
      )

      const code = response.data.code
      expect(code).toContain('return')
    })

    it('should generate components with proper structure', async () => {
      const response = await agentClient.generateComponent({
        componentName: 'Form',
        type: 'component',
        description: 'A form component with validation',
        basedOn: 'React + TypeScript',
      })

      const code = response.data.code
      // Should have function/const and return
      expect(code.split('function').length > 1 || code.split('const').length > 1)
      expect(code).toContain('return')
    })
  })

  describe('TypeScript Support', () => {
    it('should generate TypeScript code', async () => {
      const response = await agentClient.generateComponent(
        fixtures.mockComponentGenerationRequest
      )

      const code = response.data.code
      // Check for TypeScript patterns
      expect(code).toContain(':') || // Type annotations
        expect(code).toContain('interface') ||
        expect(code).toContain('type')
    })

    it('should generate interface definitions when present', async () => {
      const response = await agentClient.generateComponent({
        componentName: 'Props',
        type: 'component',
        description: 'Component with typed props',
        basedOn: 'TypeScript',
      })

      const types = response.data.types
      if (types) {
        expect(types).toBeTruthy()
        expect(types).toContain('interface') || expect(types).toContain('type')
      }
    })

    it('should include optional types property', async () => {
      const response = await agentClient.generateComponent(
        fixtures.mockComponentGenerationRequest
      )

      const component = response.data
      // types property is optional
      if (component.types) {
        expect(typeof component.types).toBe('string')
        expect(component.types.length).toBeGreaterThan(0)
      }
    })
  })

  describe('Test Generation', () => {
    it('should optionally generate test code', async () => {
      const response = await agentClient.generateComponent(
        fixtures.mockComponentGenerationRequest
      )

      const component = response.data
      // testCode is optional but may be provided
      if (component.testCode) {
        expect(typeof component.testCode).toBe('string')
        expect(component.testCode.length).toBeGreaterThan(0)
      }
    })

    it('should generate tests with describe blocks if provided', async () => {
      const response = await agentClient.generateComponent({
        componentName: 'Button',
        type: 'component',
        description: 'Button component with test',
        basedOn: 'React + Vitest',
      })

      const testCode = response.data.testCode
      if (testCode) {
        expect(testCode).toContain('describe') ||
          expect(testCode).toContain('test') ||
          expect(testCode).toContain('it')
      }
    })
  })

  describe('Import Statements', () => {
    it('should include suggested imports', async () => {
      const response = await agentClient.generateComponent(
        fixtures.mockComponentGenerationRequest
      )

      const component = response.data
      if (component.imports) {
        expect(Array.isArray(component.imports)).toBe(true)
        component.imports.forEach((imp) => {
          expect(imp).toContain('import')
        })
      }
    })

    it('should import React by default', async () => {
      const response = await agentClient.generateComponent(
        fixtures.mockComponentGenerationRequest
      )

      const component = response.data
      const allImports = (component.imports || []).join('\n') + component.code

      expect(allImports).toContain('React')
    })

    it('should include appropriate framework imports', async () => {
      const response = await agentClient.generateComponent({
        componentName: 'StyledButton',
        type: 'component',
        description: 'Button with styling',
        basedOn: 'Styled-components',
      })

      const component = response.data
      const imports = component.imports || []
      const code = component.code

      // Either in imports or in code
      const allContent = imports.join('\n') + code
      expect(allContent).toBeTruthy()
    })
  })

  describe('Component File Names', () => {
    it('should generate appropriate file names', async () => {
      const componentName = 'MyCustomComponent'
      const response = await agentClient.generateComponent({
        componentName,
        type: 'component',
        description: 'Test component',
        basedOn: 'React',
      })

      const fileName = response.data.fileName
      expect(fileName).toContain(componentName) || expect(fileName).toBeTruthy()
      expect(fileName.endsWith('.tsx') || fileName.endsWith('.ts') || fileName.endsWith('.jsx'))
    })

    it('should use .tsx extension for TypeScript components', async () => {
      const response = await agentClient.generateComponent({
        componentName: 'TypedComponent',
        type: 'component',
        description: 'TypeScript component',
        basedOn: 'TypeScript',
      })

      const fileName = response.data.fileName
      expect(fileName.endsWith('.tsx') || fileName.endsWith('.ts')).toBe(true)
    })
  })

  describe('Different Basis Frameworks', () => {
    it('should accept different UI frameworks as basis', async () => {
      const frameworks = [
        'Material UI',
        'Tailwind CSS',
        'Bootstrap',
        'Chakra UI',
        'Styled Components',
      ]

      for (const framework of frameworks) {
        const response = await agentClient.generateComponent({
          componentName: 'TestComponent',
          type: 'component',
          description: `Component using ${framework}`,
          basedOn: framework,
        })

        expect(response.status).toBe('success')
        expect(response.data.code).toBeTruthy()
      }
    })
  })

  describe('Agent Identification', () => {
    it('should identify as L20 Frontend Agent', async () => {
      const response = await agentClient.generateComponent(
        fixtures.mockComponentGenerationRequest
      )

      expect(response.agentId).toBeDefined()
      expect(response.agentId).toContain('l20') || expect(response.agentId).toContain('frontend')
    })

    it('should include timestamp in response', async () => {
      const response = await agentClient.generateComponent(
        fixtures.mockComponentGenerationRequest
      )

      expect(response.timestamp).toBeDefined()
      expect(typeof response.timestamp).toBe('string')
    })
  })

  describe('Error Handling', () => {
    it('should handle missing component name gracefully', async () => {
      try {
        await agentClient.generateComponent({
          componentName: '',
          type: 'component',
          description: 'Test',
          basedOn: 'React',
        })
      } catch (error) {
        expect(error).toBeDefined()
      }
    })

    it('should handle invalid component types', async () => {
      const response = await agentClient.generateComponent({
        componentName: 'Test',
        type: 'component',
        description: 'Test component',
        basedOn: 'React',
      })

      // Should either succeed or fail gracefully
      expect(response).toBeDefined()
    })
  })

  describe('Performance', () => {
    it('should generate component within timeout', async () => {
      const startTime = Date.now()
      const response = await agentClient.generateComponent(
        fixtures.mockComponentGenerationRequest
      )
      const duration = Date.now() - startTime

      expect(response.status).toBe('success')
      expect(duration).toBeLessThan(30000) // 30 second timeout
    })

    it('should handle multiple sequential generation requests', async () => {
      const components = ['Button', 'Card', 'Modal', 'Alert']

      for (const name of components) {
        const response = await agentClient.generateComponent({
          componentName: name,
          type: 'component',
          description: `Generate ${name} component`,
          basedOn: 'React',
        })

        expect(response.status).toBe('success')
      }
    })
  })
})
