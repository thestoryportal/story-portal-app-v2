/**
 * FormField Component
 *
 * Composite form field with label, input, and error message.
 * Manages layout and accessibility.
 */

import { useId } from 'react'
import { FormInput, type FormInputProps } from './FormInput'
import styles from '../modal/modal.module.css'

export interface FormFieldProps extends Omit<FormInputProps, 'id'> {
  /** Field label text */
  label: string
  /** HTML input type */
  type?: string
  /** Whether field is required */
  required?: boolean
  /** Error message to display */
  errorMessage?: string
  /** Optional helper text below the label */
  helperText?: string
}

export function FormField({
  label,
  type = 'text',
  required = false,
  error = false,
  errorMessage,
  helperText,
  placeholder,
  ...inputProps
}: FormFieldProps) {
  const fieldId = useId()

  return (
    <div className={styles.formGroup}>
      <label htmlFor={fieldId} className={styles.label}>
        {label}
        {required && <span style={{ color: '#ff6b6b' }}> *</span>}
      </label>
      {helperText && (
        <p
          style={{
            fontSize: 'var(--sp-font-size-xs)',
            color: 'rgba(245, 222, 179, 0.7)',
            margin: '4px 0 8px 0',
          }}
        >
          {helperText}
        </p>
      )}
      <FormInput
        id={fieldId}
        type={type}
        required={required}
        error={error}
        errorMessage={errorMessage}
        placeholder={placeholder}
        {...inputProps}
      />
    </div>
  )
}
