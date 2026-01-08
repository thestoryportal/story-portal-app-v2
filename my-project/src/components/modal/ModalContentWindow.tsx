/**
 * ModalContentWindow Component
 *
 * Unified steampunk modal container for all content screens.
 * Spec: docs/references/modal-content-window.md
 */

import { useEffect, useCallback, useId, useRef, type ReactNode } from 'react'
import styles from './modal.module.css'

export interface ModalContentWindowProps {
  /** Modal title displayed in header */
  title: string
  /** Called when modal should close */
  onClose: () => void
  /** Modal content */
  children: ReactNode
  /** Width variant: sm (600px), md (700px), lg (800px) */
  maxWidth?: 'sm' | 'md' | 'lg'
  /** Show backdrop blur overlay */
  showBackdrop?: boolean
  /** Close when clicking backdrop */
  closeOnBackdropClick?: boolean
  /** Close when pressing Escape key */
  closeOnEscape?: boolean
  /** Whether modal is open (controls animation) */
  isOpen?: boolean
}

export function ModalContentWindow({
  title,
  onClose,
  children,
  maxWidth = 'lg',
  showBackdrop = true,
  closeOnBackdropClick = true,
  closeOnEscape = true,
  isOpen = true,
}: ModalContentWindowProps) {
  const titleId = useId()
  const triggerRef = useRef<HTMLElement | null>(null)
  const frameRef = useRef<HTMLDivElement>(null)

  // Store reference to element that opened modal (for return focus)
  useEffect(() => {
    if (isOpen) {
      triggerRef.current = document.activeElement as HTMLElement
    }
  }, [isOpen])

  // Return focus to trigger when closing
  const handleClose = useCallback(() => {
    setTimeout(() => {
      if (triggerRef.current && typeof triggerRef.current.focus === 'function') {
        triggerRef.current.focus()
      }
    }, 0)
    onClose()
  }, [onClose])

  // Handle escape key
  const handleKeyDown = useCallback(
    (event: KeyboardEvent) => {
      if (closeOnEscape && event.key === 'Escape') {
        handleClose()
      }
    },
    [closeOnEscape, handleClose]
  )

  // Handle backdrop click
  const handleBackdropClick = useCallback(
    (event: React.MouseEvent<HTMLDivElement>) => {
      if (closeOnBackdropClick && event.target === event.currentTarget) {
        handleClose()
      }
    },
    [closeOnBackdropClick, handleClose]
  )

  // Add/remove escape key listener
  useEffect(() => {
    if (closeOnEscape) {
      document.addEventListener('keydown', handleKeyDown)
      return () => document.removeEventListener('keydown', handleKeyDown)
    }
  }, [closeOnEscape, handleKeyDown])

  // Prevent body scroll when modal is open
  useEffect(() => {
    if (isOpen) {
      document.body.style.overflow = 'hidden'
      return () => {
        document.body.style.overflow = ''
      }
    }
  }, [isOpen])

  if (!showBackdrop && !isOpen) {
    return null
  }

  const backdropClasses = [styles.backdrop, isOpen ? styles.open : ''].filter(Boolean).join(' ')

  const frameClasses = [styles.frame, styles[maxWidth]].filter(Boolean).join(' ')

  return (
    <div
      className={backdropClasses}
      onClick={handleBackdropClick}
      role="dialog"
      aria-modal="true"
      aria-labelledby={titleId}
    >
      <div className={frameClasses} ref={frameRef}>
        {/* Header */}
        <div className={styles.header}>
          <h2 id={titleId} className={styles.title}>
            {title}
          </h2>
          <button
            type="button"
            className={styles.closeBtn}
            onClick={handleClose}
            aria-label="Close modal"
          >
            ✕
          </button>
        </div>

        {/* Content */}
        <div className={styles.content}>{children}</div>
      </div>
    </div>
  )
}
