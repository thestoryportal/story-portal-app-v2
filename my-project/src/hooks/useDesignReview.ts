/**
 * useDesignReview Hook
 *
 * Hook for requesting design reviews from L19 Design Agent.
 * Manages request state, loading, and error handling.
 *
 * Usage:
 * const { review, loading, error, requestReview } = useDesignReview()
 * await requestReview('src/components/BookingForm.tsx', 'form-styling')
 */

import { useState, useCallback } from 'react'
import { agentClient, AgentApiError } from '@/api/agentClient'
import type { DesignReview } from '@/api/types'

interface DesignReviewState {
  review: DesignReview | null
  loading: boolean
  error: string | null
}

interface UseDesignReviewReturn {
  review: DesignReview | null
  loading: boolean
  error: string | null
  requestReview: (componentPath: string, focusArea: string) => Promise<DesignReview>
  reset: () => void
}

/**
 * Hook for requesting design reviews from L19 Design Agent
 *
 * @returns Object with review data, loading state, error, and request function
 *
 * @example
 * const { review, loading, requestReview } = useDesignReview()
 *
 * // Request a review
 * const result = await requestReview(
 *   'src/components/BookingForm.tsx',
 *   'form-styling'
 * )
 *
 * // Check results
 * if (loading) return <div>Analyzing design...</div>
 * if (error) return <div>Error: {error}</div>
 * if (review) {
 *   return review.suggestions.map(suggestion => (
 *     <div key={suggestion.id}>{suggestion.text}</div>
 *   ))
 * }
 */
export function useDesignReview(): UseDesignReviewReturn {
  const [state, setState] = useState<DesignReviewState>({
    review: null,
    loading: false,
    error: null,
  })

  const requestReview = useCallback(
    async (componentPath: string, focusArea: string): Promise<DesignReview> => {
      setState({ review: null, loading: true, error: null })

      try {
        const response = await agentClient.requestDesignReview({
          componentPath,
          focusArea,
          context: `Please review ${componentPath} focusing on ${focusArea}`,
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
              : 'Failed to get design review'

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
