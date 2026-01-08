# Form Components Usage Guide

Complete guide to using the Story Portal form components.

## Overview

The form component suite provides reusable, accessible, steampunk-styled form inputs integrated with the design token system.

**Components:**

- `FormInput` — Single input field with error state
- `FormField` — Labeled input with validation
- `FormButton` — Steampunk-styled button
- `BookingForm` — Complete booking form with all fields
- `BookingModal` — BookingForm wrapped in ModalContentWindow

---

## FormInput

Basic input field with optional error state.

```tsx
import { FormInput } from './components/form'

;<FormInput
  type="email"
  placeholder="your@email.com"
  error={hasError}
  errorMessage="Invalid email address"
/>
```

**Props:**

```typescript
interface FormInputProps extends InputHTMLAttributes<HTMLInputElement> {
  error?: boolean
  errorMessage?: string
}
```

---

## FormField

Labeled input field with automatic ID management and error handling.

```tsx
import { FormField } from './components/form'

;<FormField
  label="Email Address"
  type="email"
  name="email"
  value={email}
  onChange={(e) => setEmail(e.target.value)}
  error={!!errors.email}
  errorMessage={errors.email}
  placeholder="your@email.com"
  required
  helperText="We'll never share your email"
/>
```

**Props:**

```typescript
interface FormFieldProps extends Omit<FormInputProps, 'id'> {
  label: string
  type?: string
  required?: boolean
  errorMessage?: string
  helperText?: string
}
```

---

## FormButton

Steampunk-styled button for forms.

```tsx
import { FormButton } from './components/form'

;<FormButton type="submit" fullWidth={true} loading={isSubmitting}>
  Submit Form
</FormButton>
```

**Props:**

```typescript
interface FormButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  children: React.ReactNode
  loading?: boolean
  fullWidth?: boolean
}
```

---

## BookingForm

Complete booking form with email, name, date, and optional message fields.

```tsx
import { BookingForm } from './components/form'

const [bookingData, setBookingData] = useState(null)

<BookingForm
  onSubmit={async (data) => {
    // Send to API
    await api.createBooking(data)
  }}
  onCancel={() => setOpen(false)}
  submitText="Confirm Booking"
/>
```

**Props:**

```typescript
interface BookingFormProps {
  onSubmit: (data: BookingFormData) => Promise<void> | void
  onCancel?: () => void
  initialValues?: Partial<BookingFormData>
  submitText?: string
}

interface BookingFormData {
  email: string
  name: string
  date: string
  message?: string
}
```

**Features:**

- ✅ Email validation (RFC-compliant)
- ✅ Name validation (2+ characters)
- ✅ Date field with native picker
- ✅ Optional message textarea
- ✅ Loading state during submission
- ✅ Error messages with inline clearing
- ✅ Submit and cancel buttons

---

## BookingModal

BookingForm integrated with ModalContentWindow for complete booking experience.

```tsx
import { BookingModal } from './components/form'
import { useState } from 'react'

export function MyComponent() {
  const [isBookingOpen, setIsBookingOpen] = useState(false)

  return (
    <>
      <button onClick={() => setIsBookingOpen(true)}>Book Now</button>

      <BookingModal
        isOpen={isBookingOpen}
        onClose={() => setIsBookingOpen(false)}
        onSuccess={(data) => {
          console.log('Booking confirmed:', data)
        }}
      />
    </>
  )
}
```

**Props:**

```typescript
interface BookingModalProps {
  isOpen: boolean
  onClose: () => void
  onSuccess?: (data: BookingFormData) => void
}
```

**Features:**

- ✅ Modal wrapper with steampunk styling
- ✅ Success message display
- ✅ Auto-close on successful submission
- ✅ Integrated with ModalContentWindow

---

## Styling & Design Tokens

All components use CSS modules and design tokens from `src/tokens/design-tokens.css`:

**Colors:**

- Text: `--sp-color-text-primary` (#f5deb3)
- Border: `--sp-color-border-bronze` (#8b6f47)
- Accent: `--sp-color-accent-core` (#ffb836)
- Error: #ff6b6b

**Typography:**

- Font family: `--sp-font-ui` (Molly Sans)
- Font size: `--sp-font-size-sm` (16px)
- Line height: `--sp-line-height-body` (1.6)

**Spacing:**

- Form groups: `--sp-spacing-xl` (24px)
- Input padding: `--sp-spacing-md` (16px)
- Button padding: `--sp-spacing-md` + `--sp-spacing-2xl`

---

## Examples

### Complete Registration Form

```tsx
import { useState } from 'react'
import { ModalContentWindow } from '../modal'
import { FormField, FormButton } from '../form'

export function RegistrationModal({ isOpen, onClose }) {
  const [formData, setFormData] = useState({
    email: '',
    name: '',
  })
  const [errors, setErrors] = useState({})

  const handleSubmit = async (e) => {
    e.preventDefault()
    // Validate and submit
  }

  return (
    <ModalContentWindow title="Create Account" onClose={onClose} isOpen={isOpen} maxWidth="sm">
      <form onSubmit={handleSubmit}>
        <FormField
          label="Full Name"
          value={formData.name}
          onChange={(e) => setFormData({ ...formData, name: e.target.value })}
          error={!!errors.name}
          errorMessage={errors.name}
          required
        />

        <FormField
          label="Email"
          type="email"
          value={formData.email}
          onChange={(e) => setFormData({ ...formData, email: e.target.value })}
          error={!!errors.email}
          errorMessage={errors.email}
          required
        />

        <FormButton type="submit" fullWidth>
          Create Account
        </FormButton>
      </form>
    </ModalContentWindow>
  )
}
```

### Custom Form with Multi-Step

```tsx
import { useState } from 'react'
import { ModalContentWindow } from '../modal'
import { FormField, FormButton } from '../form'

export function MultiStepForm() {
  const [step, setStep] = useState(1)
  const [data, setData] = useState({})

  return (
    <ModalContentWindow title={`Step ${step}`} onClose={() => {}}>
      {step === 1 && (
        <FormField
          label="Name"
          value={data.name || ''}
          onChange={(e) => setData({ ...data, name: e.target.value })}
          required
        />
      )}

      {step === 2 && (
        <FormField
          label="Email"
          type="email"
          value={data.email || ''}
          onChange={(e) => setData({ ...data, email: e.target.value })}
          required
        />
      )}

      <div style={{ display: 'flex', gap: '12px', marginTop: '32px' }}>
        {step > 1 && (
          <FormButton type="button" onClick={() => setStep(step - 1)}>
            Previous
          </FormButton>
        )}

        <FormButton type="button" fullWidth={step === 1} onClick={() => setStep(step + 1)}>
          {step === 2 ? 'Submit' : 'Next'}
        </FormButton>
      </div>
    </ModalContentWindow>
  )
}
```

---

## Accessibility

All components follow WCAG 2.1 AA standards:

- ✅ Semantic HTML (`<label>`, `<input>`, `<button>`)
- ✅ Proper label associations via `htmlFor` and `id`
- ✅ Error messages linked to inputs
- ✅ Focus management
- ✅ Keyboard navigation
- ✅ Error announcements (screen readers)
- ✅ Form validation feedback
- ✅ Required field indicators

---

## Testing

Example test setup:

```tsx
import { render, screen, fireEvent } from '@testing-library/react'
import { BookingForm } from './BookingForm'

test('displays validation errors', async () => {
  const onSubmit = vi.fn()
  render(<BookingForm onSubmit={onSubmit} />)

  // Submit empty form
  fireEvent.click(screen.getByText('Complete Booking'))

  // Check for error messages
  expect(screen.getByText('Email is required')).toBeInTheDocument()
  expect(screen.getByText('Name is required')).toBeInTheDocument()
})

test('submits valid form data', async () => {
  const onSubmit = vi.fn()
  render(<BookingForm onSubmit={onSubmit} />)

  fireEvent.change(screen.getByPlaceholderText('your@email.com'), {
    target: { value: 'test@example.com' },
  })
  fireEvent.change(screen.getByPlaceholderText('Your full name'), {
    target: { value: 'John Doe' },
  })

  fireEvent.click(screen.getByDisplayValue('2024-01-15'))
  fireEvent.click(screen.getByText('Complete Booking'))

  expect(onSubmit).toHaveBeenCalled()
})
```

---

## File Structure

```
src/components/form/
├── FormInput.tsx           # Basic input with error
├── FormField.tsx           # Labeled input with validation
├── FormButton.tsx          # Steampunk button
├── BookingForm.tsx         # Complete booking form
├── BookingModal.tsx        # Booking form in modal
├── index.ts                # Barrel export
└── USAGE.md                # This file
```

---

**Status:** ✅ Complete and production-ready
**TypeScript:** ✅ Fully typed
**Accessibility:** ✅ WCAG 2.1 AA
**Testing:** Ready for unit/integration tests
