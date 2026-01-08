/**
 * API Type Definitions
 *
 * Shared types for API requests and responses.
 */

export interface BookingRequest {
  email: string
  name: string
  date: string
  message?: string
}

export interface BookingResponse {
  id: string
  email: string
  name: string
  date: string
  message?: string
  createdAt: string
  confirmationCode: string
}

export interface ApiError {
  code: string
  message: string
  field?: string
}

export interface ApiResponse<T> {
  success: boolean
  data?: T
  error?: ApiError
}
