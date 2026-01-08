/// <reference types="vitest" />
import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'
import path from 'path'

/**
 * Vitest Configuration for Integration Tests
 *
 * Extends the main Vite config with integration test specific settings:
 * - Longer timeouts for agent operations (30s)
 * - jsdom environment for DOM testing
 * - Includes test files matching *.integration.test.ts pattern
 * - Isolates tests to prevent state pollution
 * - Hooks into test/setup.integration.ts for initialization
 */
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: ['./src/test/setup.ts', './src/test/setup.integration.ts'],
    include: ['src/**/*.integration.test.{ts,tsx}'],
    exclude: ['node_modules', 'servers/**', 'dist'],

    // Integration test specific settings
    testTimeout: 30000, // Agent operations can take up to 30 seconds
    hookTimeout: 30000,
    teardownTimeout: 10000,
    isolate: true, // Each test runs in isolation to prevent state pollution
    threads: true,
    maxThreads: 4, // Limit parallel test threads for API rate limiting
    minThreads: 1,

    // Coverage settings for integration tests
    coverage: {
      provider: 'v8',
      reporter: ['text', 'json', 'html'],
      exclude: [
        'node_modules/',
        'src/test/',
        '**/*.d.ts',
        '**/*.config.*',
        '**/mockData.ts',
      ],
    },

    // Reporters
    reporters: ['default'],
  },
})
