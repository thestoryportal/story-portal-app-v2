/**
 * useCodeReview Hook
 *
 * Hook for requesting code reviews from L20 Code Review Agent.
 * Manages request state, loading, and error handling.
 *
 * Usage:
 * const { review, loading, error, requestReview } = useCodeReview()
 * await requestReview('src/legacy/hooks/useWheelPhysics.ts',
 *                    ['performance', 'type-safety'])
 */

import { useState, useCallback } from 'react'
import { agentClient, AgentApiError } from '@/api/agentClient'
import type { CodeReview } from '@/api/types'

interface CodeReviewState {
  review: CodeReview | null
  loading: boolean
  error: string | null
}

interface UseCodeReviewReturn {
  review: CodeReview | null
  loading: boolean
  error: string | null
  requestReview: (filePath: string, focusAreas?: string[]) => Promise<CodeReview>
  reset: () => void
}

/**
 * Hook for requesting code reviews from L20 Code Review Agent
 *
 * @returns Object with review data, loading state, error, and request function
 *
 * @example
 * const { review, loading, requestReview } = useCodeReview()
 *
 * // Request a review
 * const result = await requestReview(
 *   'src/legacy/hooks/useWheelPhysics.ts',
 *   ['performance', 'type-safety']
 * )
 *
 * // Check results
 * if (loading) return <div>Reviewing code...</div>
 * if (error) return <div>Error: {error}</div>
 * if (review) {
 *   return (
 *     <div>
 *       <h3>Issues: {review.issues.length}</h3>
 *       <p>Quality: {review.overallQuality}</p>
 *       <p>Test Coverage: {review.testCoverage.current}%</p>
 *     </div>
 *   )
 * }
 */
export function useCodeReview(): UseCodeReviewReturn {
  const [state, setState] = useState<CodeReviewState>({
    review: null,
    loading: false,
    error: null,
  })

  const requestReview = useCallback(
    async (filePath: string, focusAreas: string[] = ['all']): Promise<CodeReview> => {
      setState({ review: null, loading: true, error: null })

      try {
        const response = await agentClient.reviewCode({
          filePath,
          reviewFocus: focusAreas.length > 0 ? focusAreas : ['all'],
          severity: 'all',
        })

        setState({
          review: response.data,
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
              : 'Code review failed'

        setState({
          review: null,
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
      review: null,
      loading: false,
      error: null,
    })
  }, [])

  return {
    ...state,
    requestReview,
    reset,
  }
}
