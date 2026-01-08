/**
 * FormInput Component
 *
 * Reusable input field with optional error state.
 * Integrates with design tokens from src/tokens/design-tokens.css
 */

import { type InputHTMLAttributes } from 'react'
import styles from '../modal/modal.module.css'

export interface FormInputProps extends InputHTMLAttributes<HTMLInputElement> {
  /** Show error state */
  error?: boolean
  /** Optional error message */
  errorMessage?: string
}

export function FormInput({
  error = false,
  errorMessage,
  className,
  ...inputProps
}: FormInputProps) {
  const inputClasses = [styles.input, error ? styles.error : '', className]
    .filter(Boolean)
    .join(' ')

  return (
    <div>
      <input {...inputProps} className={inputClasses} />
      {error && errorMessage && <div className={styles.inputError}>{errorMessage}</div>}
    </div>
  )
}
