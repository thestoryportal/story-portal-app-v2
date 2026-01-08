/**
 * BookingModal Component
 *
 * BookingForm integrated with ModalContentWindow.
 * Handles API integration and success/error states.
 */

import { useState, useCallback } from 'react'
import { ModalContentWindow } from '../modal'
import { BookingForm, type BookingFormData } from './BookingForm'
import { bookingClient, BookingApiError } from '../../api'

export interface BookingModalProps {
  isOpen: boolean
  onClose: () => void
  onSuccess?: (data: BookingFormData) => void
}

export function BookingModal({ isOpen, onClose, onSuccess }: BookingModalProps) {
  const [successMessage, setSuccessMessage] = useState<string | null>(null)
  const [confirmationCode, setConfirmationCode] = useState<string | null>(null)

  const handleSubmit = useCallback(
    async (data: BookingFormData) => {
      try {
        // Submit booking to API
        const response = await bookingClient.createBooking(data)

        // Show success message with confirmation code
        setSuccessMessage(`Thank you, ${data.name}! Your booking has been confirmed.`)
        setConfirmationCode(response.confirmationCode)

        // Call optional callback with API response
        onSuccess?.(response as unknown as BookingFormData)

        // Close modal after a delay
        setTimeout(() => {
          setSuccessMessage(null)
          setConfirmationCode(null)
          onClose()
        }, 3000)
      } catch (error) {
        // Re-throw to let BookingForm handle error display
        if (error instanceof BookingApiError) {
          throw new Error(error.message)
        }
        throw error
      }
    },
    [onClose, onSuccess]
  )

  if (!isOpen) {
    return null
  }

  return (
    <ModalContentWindow title="Book Your Experience" onClose={onClose} maxWidth="md">
      {successMessage ? (
        <div
          style={{
            textAlign: 'center',
            padding: '40px 20px',
          }}
        >
          <p
            style={{
              fontSize: '18px',
              marginBottom: '16px',
              color: '#90EE90',
            }}
          >
            ✓ {successMessage}
          </p>
          {confirmationCode && (
            <div
              style={{
                background: 'rgba(139, 111, 71, 0.2)',
                border: '2px solid #8b6f47',
                borderRadius: '8px',
                padding: '16px',
                marginBottom: '16px',
                fontFamily: 'monospace',
              }}
            >
              <p
                style={{
                  margin: '0 0 8px 0',
                  fontSize: '12px',
                  color: 'rgba(245, 222, 179, 0.7)',
                  textTransform: 'uppercase',
                  letterSpacing: '1px',
                }}
              >
                Confirmation Code
              </p>
              <p
                style={{
                  margin: 0,
                  fontSize: '24px',
                  color: '#ffb836',
                  fontWeight: 'bold',
                  letterSpacing: '2px',
                }}
              >
                {confirmationCode}
              </p>
            </div>
          )}
          <p style={{ fontSize: '14px', color: 'rgba(245, 222, 179, 0.7)' }}>
            We'll send a confirmation to your email shortly.
          </p>
        </div>
      ) : (
        <BookingForm onSubmit={handleSubmit} onCancel={onClose} submitText="Confirm Booking" />
      )}
    </ModalContentWindow>
  )
}
