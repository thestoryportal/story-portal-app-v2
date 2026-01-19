/**
 * OurWorkModal - Portfolio and services showcase
 *
 * Modal displaying the company's work, services, and portfolio.
 */

import { useEffect } from 'react'

export interface OurWorkModalProps {
  isOpen: boolean
  onClose: () => void
  onNext: () => void
  onPrev: () => void
}

export function OurWorkModal({ isOpen, onClose, onNext, onPrev }: OurWorkModalProps) {
  // Handle escape key
  useEffect(() => {
    if (!isOpen) return

    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    }

    window.addEventListener('keydown', handleEscape)
    return () => window.removeEventListener('keydown', handleEscape)
  }, [isOpen, onClose])

  if (!isOpen) return null

  return (
    <>
      {/* Backdrop */}
      <div
        onClick={onClose}
        style={{
          position: 'fixed',
          inset: 0,
          backgroundColor: 'rgba(0, 0, 0, 0.8)',
          zIndex: 9998,
          backdropFilter: 'blur(4px)',
        }}
      />

      {/* Modal */}
      <div style={{
        position: 'fixed',
        top: '50%',
        left: '50%',
        transform: 'translate(-50%, -50%)',
        maxWidth: '700px',
        width: '90%',
        maxHeight: '80vh',
        backgroundColor: '#2a1810',
        borderRadius: '16px',
        boxShadow: '0 16px 64px rgba(0, 0, 0, 0.9)',
        zIndex: 9999,
        overflow: 'hidden',
        border: '2px solid #d4af37',
      }}>
        {/* Header */}
        <div style={{
          padding: '2rem',
          background: 'linear-gradient(180deg, #1a0f08 0%, #2a1810 100%)',
          borderBottom: '2px solid #d4af37',
        }}>
          <h2 style={{
            margin: 0,
            color: '#d4af37',
            fontSize: '2rem',
            fontWeight: 'bold',
          }}>
            Our Work
          </h2>
        </div>

        {/* Content */}
        <div style={{
          padding: '2rem',
          color: '#f5e6d3',
          overflowY: 'auto',
          maxHeight: 'calc(80vh - 200px)',
        }}>
          <h3 style={{ color: '#d4af37', marginTop: 0, marginBottom: '1rem' }}>
            Services & Solutions
          </h3>

          <div style={{ marginBottom: '2rem' }}>
            <h4 style={{ color: '#d4af37', marginBottom: '0.5rem' }}>
              Story Capture & Preservation
            </h4>
            <p style={{ margin: 0, marginBottom: '1rem', lineHeight: '1.6' }}>
              Professional-grade audio and video recording with intuitive prompts
              to guide storytellers through their narrative journey.
            </p>

            <h4 style={{ color: '#d4af37', marginBottom: '0.5rem', marginTop: '1.5rem' }}>
              Digital Legacy Creation
            </h4>
            <p style={{ margin: 0, marginBottom: '1rem', lineHeight: '1.6' }}>
              Transform recorded stories into beautifully curated digital collections
              that can be shared across generations.
            </p>

            <h4 style={{ color: '#d4af37', marginBottom: '0.5rem', marginTop: '1.5rem' }}>
              Community Story Archives
            </h4>
            <p style={{ margin: 0, marginBottom: '1rem', lineHeight: '1.6' }}>
              Build collective narratives by bringing together stories from families,
              communities, and organizations.
            </p>
          </div>

          <div style={{
            padding: '1.5rem',
            backgroundColor: '#1a0f08',
            borderRadius: '8px',
            borderLeft: '4px solid #d4af37',
          }}>
            <h3 style={{ color: '#d4af37', marginTop: 0, marginBottom: '0.5rem' }}>
              Featured Projects
            </h3>
            <p style={{ margin: 0, lineHeight: '1.6' }}>
              From family reunions to corporate heritage projects, we've helped preserve
              thousands of stories across diverse communities and contexts.
            </p>
          </div>
        </div>

        {/* Footer with navigation */}
        <div style={{
          padding: '1.5rem 2rem',
          background: 'linear-gradient(180deg, #2a1810 0%, #1a0f08 100%)',
          borderTop: '2px solid #8b6f47',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
        }}>
          <button
            onClick={onClose}
            style={{
              padding: '0.75rem 2rem',
              fontSize: '16px',
              backgroundColor: 'transparent',
              color: '#d4af37',
              border: '2px solid #8b6f47',
              borderRadius: '8px',
              cursor: 'pointer',
              transition: 'all 0.2s',
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.borderColor = '#d4af37'
              e.currentTarget.style.backgroundColor = 'rgba(212, 175, 55, 0.1)'
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.borderColor = '#8b6f47'
              e.currentTarget.style.backgroundColor = 'transparent'
            }}
          >
            Close
          </button>

          <div style={{ display: 'flex', gap: '1rem' }}>
            <button
              onClick={onPrev}
              style={{
                padding: '0.75rem 2rem',
                fontSize: '16px',
                backgroundColor: 'transparent',
                color: '#d4af37',
                border: '2px solid #d4af37',
                borderRadius: '8px',
                cursor: 'pointer',
                transition: 'all 0.2s',
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.backgroundColor = 'rgba(212, 175, 55, 0.1)'
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.backgroundColor = 'transparent'
              }}
            >
              ← Prev
            </button>

            <button
              onClick={onNext}
              style={{
                padding: '0.75rem 2rem',
                fontSize: '16px',
                backgroundColor: '#d4af37',
                color: '#1a0f08',
                border: 'none',
                borderRadius: '8px',
                cursor: 'pointer',
                fontWeight: 'bold',
                transition: 'all 0.2s',
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.backgroundColor = '#c4942e'
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.backgroundColor = '#d4af37'
              }}
            >
              Next →
            </button>
          </div>
        </div>
      </div>
    </>
  )
}
