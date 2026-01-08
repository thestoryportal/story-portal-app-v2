/**
 * Integration Test Setup
 *
 * Initializes integration test environment:
 * - Configures mock environment variables
 * - Sets up agent client to use mock mode
 * - Configures timeout settings
 * - Sets up cleanup hooks
 */

import { beforeAll, afterEach, afterAll, vi } from 'vitest'

/**
 * Configure environment for integration tests
 */
beforeAll(() => {
  // Set environment variables for testing
  process.env.VITE_AGENT_API_URL = 'http://localhost:8000/api/agents'
  process.env.VITE_USE_AGENT_MOCKS = 'true'
  process.env.VITE_AGENT_TIMEOUT = '30000'
  process.env.VITE_AGENT_RETRIES = '2'

  // Configure fetch timeout for all tests
  // This allows agents to respond within the 30-second test timeout
  global.fetch = vi.fn()

  console.log('Integration test environment initialized')
})

/**
 * Clean up after each test
 */
afterEach(() => {
  // Reset all mocks
  vi.clearAllMocks()

  // Clear any pending timers
  vi.clearAllTimers()
})

/**
 * Teardown after all tests
 */
afterAll(() => {
  // Final cleanup
  vi.restoreAllMocks()
})

/**
 * Test globals and utilities
 */
declare global {
  // Add any custom globals here if needed
  var testTimeout: number
}

globalThis.testTimeout = 30000
