/**
 * BookingForm Component
 *
 * Complete booking form with email, name, date, and optional message fields.
 * Includes validation and error handling.
 */

import { useState, useCallback, type FormEvent } from 'react'
import { FormField } from './FormField'
import { FormButton } from './FormButton'

export interface BookingFormData {
  email: string
  name: string
  date: string
  message?: string
}

export interface BookingFormProps {
  /** Called when form is submitted with valid data */
  onSubmit: (data: BookingFormData) => Promise<void> | void
  /** Called when user cancels/closes form */
  onCancel?: () => void
  /** Optional initial values */
  initialValues?: Partial<BookingFormData>
  /** Custom submit button text */
  submitText?: string
}

interface FormErrors {
  email?: string
  name?: string
  date?: string
}

export function BookingForm({
  onSubmit,
  onCancel,
  initialValues = {},
  submitText = 'Complete Booking',
}: BookingFormProps) {
  const [formData, setFormData] = useState<BookingFormData>({
    email: initialValues.email || '',
    name: initialValues.name || '',
    date: initialValues.date || '',
    message: initialValues.message || '',
  })

  const [errors, setErrors] = useState<FormErrors>({})
  const [isLoading, setIsLoading] = useState(false)
  const [submitError, setSubmitError] = useState<string | null>(null)

  // Validation
  const validateForm = useCallback((): boolean => {
    const newErrors: FormErrors = {}

    // Email validation
    if (!formData.email.trim()) {
      newErrors.email = 'Email is required'
    } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(formData.email)) {
      newErrors.email = 'Please enter a valid email address'
    }

    // Name validation
    if (!formData.name.trim()) {
      newErrors.name = 'Name is required'
    } else if (formData.name.length < 2) {
      newErrors.name = 'Name must be at least 2 characters'
    }

    // Date validation
    if (!formData.date) {
      newErrors.date = 'Date is required'
    }

    setErrors(newErrors)
    return Object.keys(newErrors).length === 0
  }, [formData])

  // Handle form submission
  const handleSubmit = useCallback(
    async (e: FormEvent<HTMLFormElement>) => {
      e.preventDefault()
      setSubmitError(null)

      if (!validateForm()) {
        return
      }

      setIsLoading(true)
      try {
        await onSubmit(formData)
      } catch (error) {
        setSubmitError(
          error instanceof Error ? error.message : 'An error occurred while submitting the form'
        )
      } finally {
        setIsLoading(false)
      }
    },
    [formData, onSubmit, validateForm]
  )

  // Handle input change
  const handleChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
      const { name, value } = e.target
      setFormData((prev) => ({
        ...prev,
        [name]: value,
      }))
      // Clear error for this field when user starts typing
      if (errors[name as keyof FormErrors]) {
        setErrors((prev) => ({
          ...prev,
          [name]: undefined,
        }))
      }
    },
    [errors]
  )

  return (
    <form onSubmit={handleSubmit}>
      {submitError && (
        <div
          style={{
            background: 'rgba(204, 68, 68, 0.2)',
            border: '2px solid #cc4444',
            borderRadius: '8px',
            padding: '16px',
            marginBottom: '24px',
            color: '#ff6b6b',
            fontSize: '14px',
          }}
        >
          {submitError}
        </div>
      )}

      <FormField
        label="Full Name"
        name="name"
        type="text"
        value={formData.name}
        onChange={handleChange}
        error={!!errors.name}
        errorMessage={errors.name}
        placeholder="Your full name"
        required
      />

      <FormField
        label="Email Address"
        name="email"
        type="email"
        value={formData.email}
        onChange={handleChange}
        error={!!errors.email}
        errorMessage={errors.email}
        placeholder="your@email.com"
        required
      />

      <FormField
        label="Preferred Date"
        name="date"
        type="date"
        value={formData.date}
        onChange={handleChange}
        error={!!errors.date}
        errorMessage={errors.date}
        required
      />

      <div style={{ marginBottom: 'var(--sp-spacing-xl)' }}>
        <label
          style={{ display: 'block', color: '#f5deb3', fontSize: '14px', marginBottom: '8px' }}
        >
          Message (optional)
        </label>
        <textarea
          name="message"
          value={formData.message}
          onChange={handleChange}
          placeholder="Any special requests or notes..."
          style={{
            width: '100%',
            minHeight: '120px',
            padding: 'var(--sp-spacing-md)',
            fontFamily: 'var(--sp-font-ui)',
            fontSize: 'var(--sp-font-size-sm)',
            color: 'var(--sp-color-text-primary)',
            background: 'rgba(0, 0, 0, 0.4)',
            border: 'var(--sp-border-medium)',
            borderRadius: 'var(--sp-radius-md)',
            boxShadow: 'inset 0 2px 6px rgba(0, 0, 0, 0.4)',
            resize: 'vertical',
          }}
        />
      </div>

      <div
        style={{
          display: 'flex',
          gap: '12px',
          marginTop: '32px',
        }}
      >
        <FormButton type="submit" fullWidth loading={isLoading}>
          {submitText}
        </FormButton>
        {onCancel && (
          <button
            type="button"
            onClick={onCancel}
            style={{
              flex: 1,
              padding: '16px 32px',
              background: 'transparent',
              border: '2px solid #8b6f47',
              borderRadius: '8px',
              color: '#f5deb3',
              fontSize: '16px',
              fontWeight: 'bold',
              cursor: 'pointer',
              transition: 'all 0.15s ease-in-out',
            }}
            onMouseEnter={(e) => {
              const btn = e.currentTarget as HTMLButtonElement
              btn.style.background = 'rgba(139, 111, 71, 0.2)'
            }}
            onMouseLeave={(e) => {
              const btn = e.currentTarget as HTMLButtonElement
              btn.style.background = 'transparent'
            }}
          >
            Cancel
          </button>
        )}
      </div>
    </form>
  )
}
