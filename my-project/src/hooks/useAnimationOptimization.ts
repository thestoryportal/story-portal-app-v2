/**
 * useAnimationOptimization Hook
 *
 * Hook for requesting animation optimization from L20 Animation Agent.
 * Manages request state, loading, and error handling.
 *
 * Usage:
 * const { optimization, loading, error, requestOptimization } = useAnimationOptimization()
 * await requestOptimization('src/components/3DScene.tsx', { fps: 60, targetFrameTime: 16 })
 */

import { useState, useCallback } from 'react'
import { agentClient, AgentApiError } from '@/api/agentClient'
import type { AnimationOptimization } from '@/api/types'

interface AnimationOptimizationState {
  optimization: AnimationOptimization | null
  loading: boolean
  error: string | null
}

interface UseAnimationOptimizationReturn {
  optimization: AnimationOptimization | null
  loading: boolean
  error: string | null
  requestOptimization: (
    filePath: string,
    targetPerformance: { fps: number; targetFrameTime: number },
    constraints?: string[]
  ) => Promise<AnimationOptimization>
  reset: () => void
}

/**
 * Hook for requesting animation optimization from L20 Animation Agent
 *
 * @returns Object with optimization data, loading state, error, and request function
 *
 * @example
 * const { optimization, loading, requestOptimization } = useAnimationOptimization()
 *
 * // Request optimization for 3D animation
 * const result = await requestOptimization(
 *   'src/components/3DScene.tsx',
 *   { fps: 60, targetFrameTime: 16 },
 *   ['reduce-geometry', 'optimize-shaders']
 * )
 *
 * // Check results
 * if (loading) return <div>Optimizing animation...</div>
 * if (error) return <div>Error: {error}</div>
 * if (optimization) {
 *   return (
 *     <div>
 *       <h3>Current FPS: {optimization.currentPerformance.fps}</h3>
 *       <p>Optimizations: {optimization.optimizations.length}</p>
 *       <p>Expected Result: {optimization.expectedResult}</p>
 *     </div>
 *   )
 * }
 */
export function useAnimationOptimization(): UseAnimationOptimizationReturn {
  const [state, setState] = useState<AnimationOptimizationState>({
    optimization: null,
    loading: false,
    error: null,
  })

  const requestOptimization = useCallback(
    async (
      filePath: string,
      targetPerformance: { fps: number; targetFrameTime: number },
      constraints: string[] = []
    ): Promise<AnimationOptimization> => {
      setState({ optimization: null, loading: true, error: null })

      try {
        const response = await agentClient.optimizeAnimation({
          filePath,
          targetPerformance,
          constraints: constraints.length > 0 ? constraints : ['general-optimization'],
        })

        setState({
          optimization: response.data,
          loading: false,
          error: null,
        })

        return response.data
      } catch (err) {
        const errorMessage =
          err instanceof AgentApiError
            ? `Agent error (${err.statusCode}): ${err.message}`
            : err instanceof Error
              ? err.message
              : 'Animation optimization failed'

        setState({
          optimization: null,
          loading: false,
          error: errorMessage,
        })

        throw err
      }
    },
    []
  )

  const reset = useCallback(() => {
    setState({
      optimization: null,
      loading: false,
      error: null,
    })
  }, [])

  return {
    ...state,
    requestOptimization,
    reset,
  }
}
