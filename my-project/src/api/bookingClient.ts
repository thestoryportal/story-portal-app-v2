/**
 * Booking API Client
 *
 * Handles all booking-related API calls.
 * Supports both real and mock backends.
 */

import type { BookingRequest, BookingResponse, ApiError } from './types'

export class BookingApiError extends Error {
  constructor(
    public code: string,
    public field?: string,
    message?: string
  ) {
    super(message || code)
    this.name = 'BookingApiError'
  }
}

export interface BookingClientConfig {
  baseUrl?: string
  timeout?: number
  retries?: number
  useMock?: boolean
}

class BookingClient {
  private baseUrl: string
  private timeout: number
  private retries: number
  private useMock: boolean

  constructor(config: BookingClientConfig = {}) {
    this.baseUrl = config.baseUrl || this.getBaseUrl()
    this.timeout = config.timeout || 10000
    this.retries = config.retries || 3
    this.useMock = config.useMock ?? this.shouldUseMock()
  }

  /**
   * Determine if we should use mock API (development environment)
   */
  private shouldUseMock(): boolean {
    return import.meta.env.DEV || import.meta.env.VITE_USE_MOCK_API === 'true'
  }

  /**
   * Get base URL from environment or default
   */
  private getBaseUrl(): string {
    return import.meta.env.VITE_API_BASE_URL || 'http://localhost:3000/api'
  }

  /**
   * Create a booking
   */
  async createBooking(data: BookingRequest): Promise<BookingResponse> {
    if (this.useMock) {
      return this.mockCreateBooking(data)
    }

    return this.apiRequest<BookingResponse>('/bookings', {
      method: 'POST',
      body: JSON.stringify(data),
    })
  }

  /**
   * Get booking by ID
   */
  async getBooking(id: string): Promise<BookingResponse> {
    if (this.useMock) {
      return this.mockGetBooking(id)
    }

    return this.apiRequest<BookingResponse>(`/bookings/${id}`, {
      method: 'GET',
    })
  }

  /**
   * Cancel booking by ID
   */
  async cancelBooking(id: string, reason?: string): Promise<{ success: boolean }> {
    if (this.useMock) {
      return this.mockCancelBooking(id, reason)
    }

    return this.apiRequest<{ success: boolean }>(`/bookings/${id}/cancel`, {
      method: 'POST',
      body: JSON.stringify({ reason }),
    })
  }

  /**
   * Core API request method with retry logic
   */
  private async apiRequest<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
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
            ...options.headers,
          },
        })

        clearTimeout(timeoutId)

        if (!response.ok) {
          const error = await this.parseError(response)
          throw new BookingApiError(error.code, error.field, error.message)
        }

        const data = await response.json()
        return data as T
      } catch (error) {
        lastError = error instanceof Error ? error : new Error(String(error))

        // Don't retry on client errors (4xx)
        if (error instanceof BookingApiError && error.code.startsWith('400')) {
          throw error
        }

        // Wait before retry
        if (attempt < this.retries - 1) {
          await this.delay(Math.pow(2, attempt) * 1000)
        }
      }
    }

    throw lastError || new Error('Failed to complete booking request')
  }

  /**
   * Parse error response from API
   */
  private async parseError(response: Response): Promise<ApiError> {
    try {
      const data = await response.json()
      return (
        data.error || {
          code: `${response.status}`,
          message: response.statusText,
        }
      )
    } catch {
      return {
        code: `${response.status}`,
        message: response.statusText || 'Unknown error',
      }
    }
  }

  /**
   * Simple delay utility for retries
   */
  private delay(ms: number): Promise<void> {
    return new Promise((resolve) => setTimeout(resolve, ms))
  }

  /**
   * ==========================================
   * MOCK API IMPLEMENTATIONS (Development)
   * ==========================================
   */

  private mockCreateBooking(data: BookingRequest): Promise<BookingResponse> {
    return new Promise((resolve) => {
      // Simulate network delay
      setTimeout(() => {
        const bookingId = this.generateId('BOOK')
        const confirmationCode = this.generateConfirmationCode()

        const booking: BookingResponse = {
          id: bookingId,
          email: data.email,
          name: data.name,
          date: data.date,
          message: data.message,
          createdAt: new Date().toISOString(),
          confirmationCode,
        }

        // Log booking for debugging
        console.log('✓ Mock booking created:', booking)

        // Store in localStorage for persistence
        this.storeBooking(booking)

        resolve(booking)
      }, 800) // Simulate 800ms network latency
    })
  }

  private mockGetBooking(id: string): Promise<BookingResponse> {
    return new Promise((resolve, reject) => {
      setTimeout(() => {
        const booking = this.retrieveBooking(id)
        if (booking) {
          resolve(booking)
        } else {
          reject(new BookingApiError('BOOKING_NOT_FOUND', undefined, `Booking ${id} not found`))
        }
      }, 300)
    })
  }

  private mockCancelBooking(id: string, reason?: string): Promise<{ success: boolean }> {
    return new Promise((resolve, reject) => {
      setTimeout(() => {
        const booking = this.retrieveBooking(id)
        if (!booking) {
          reject(new BookingApiError('BOOKING_NOT_FOUND', undefined, `Booking ${id} not found`))
          return
        }

        this.deleteBooking(id)
        console.log(`✓ Mock booking cancelled: ${id}${reason ? ` - ${reason}` : ''}`)

        resolve({ success: true })
      }, 300)
    })
  }

  /**
   * Local storage helpers for mock API
   */

  private storeBooking(booking: BookingResponse): void {
    const key = `booking_${booking.id}`
    localStorage.setItem(key, JSON.stringify(booking))

    // Also maintain a list of all booking IDs
    const ids = JSON.parse(localStorage.getItem('booking_ids') || '[]') as string[]
    if (!ids.includes(booking.id)) {
      ids.push(booking.id)
      localStorage.setItem('booking_ids', JSON.stringify(ids))
    }
  }

  private retrieveBooking(id: string): BookingResponse | null {
    const key = `booking_${id}`
    const data = localStorage.getItem(key)
    return data ? JSON.parse(data) : null
  }

  private deleteBooking(id: string): void {
    const key = `booking_${id}`
    localStorage.removeItem(key)

    const ids = JSON.parse(localStorage.getItem('booking_ids') || '[]') as string[]
    const filtered = ids.filter((bid) => bid !== id)
    localStorage.setItem('booking_ids', JSON.stringify(filtered))
  }

  /**
   * Utilities
   */

  private generateId(prefix: string): string {
    return `${prefix}_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
  }

  private generateConfirmationCode(): string {
    return Math.random().toString(36).substr(2, 8).toUpperCase()
  }
}

// Export singleton instance
export const bookingClient = new BookingClient({
  useMock: true, // Use mock API by default in development
})

export default bookingClient
