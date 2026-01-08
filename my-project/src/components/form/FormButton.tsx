/**
 * FormButton Component
 *
 * Steampunk-styled button for forms.
 */

import { type ButtonHTMLAttributes } from 'react'

export interface FormButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  /** Button text */
  children: React.ReactNode
  /** Whether button is in loading state */
  loading?: boolean
  /** Full width button */
  fullWidth?: boolean
}

export function FormButton({
  children,
  loading = false,
  fullWidth = true,
  disabled = false,
  type = 'button',
  ...buttonProps
}: FormButtonProps) {
  return (
    <button
      type={type}
      disabled={disabled || loading}
      style={{
        width: fullWidth ? '100%' : 'auto',
        padding: '16px 32px',
        marginTop: '24px',
        background: 'linear-gradient(180deg, #6a5a4a, #2a1a0a)',
        border: '3px solid #8b6f47',
        borderRadius: '8px',
        color: '#f5deb3',
        fontSize: '18px',
        fontWeight: 'bold',
        textTransform: 'uppercase',
        letterSpacing: '0.5px',
        cursor: disabled || loading ? 'not-allowed' : 'pointer',
        opacity: disabled || loading ? 0.6 : 1,
        transition: 'all 0.15s ease-in-out',
      }}
      onMouseEnter={(e) => {
        if (!disabled && !loading) {
          const btn = e.currentTarget as HTMLButtonElement
          btn.style.transform = 'translateY(-2px)'
          btn.style.boxShadow = '0 4px 12px rgba(0, 0, 0, 0.4)'
        }
      }}
      onMouseLeave={(e) => {
        const btn = e.currentTarget as HTMLButtonElement
        btn.style.transform = 'translateY(0)'
        btn.style.boxShadow = 'none'
      }}
      {...buttonProps}
    >
      {loading ? 'Loading...' : children}
    </button>
  )
}
