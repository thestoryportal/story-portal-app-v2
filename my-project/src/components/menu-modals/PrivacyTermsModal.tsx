/**
 * PrivacyTermsModal - Privacy Policy and Terms of Service
 *
 * Modal displaying privacy policy and terms of service information.
 */

import { useEffect } from 'react'

export interface PrivacyTermsModalProps {
  isOpen: boolean
  onClose: () => void
  onPrev: () => void
}

export function PrivacyTermsModal({ isOpen, onClose, onPrev }: PrivacyTermsModalProps) {
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
            Privacy & Terms
          </h2>
        </div>

        {/* Content */}
        <div style={{
          padding: '2rem',
          color: '#f5e6d3',
          overflowY: 'auto',
          maxHeight: 'calc(80vh - 200px)',
          lineHeight: '1.6',
        }}>
          {/* Privacy Policy Section */}
          <div style={{ marginBottom: '2rem' }}>
            <h3 style={{ color: '#d4af37', marginTop: 0, marginBottom: '1rem' }}>
              Privacy Policy
            </h3>

            <p style={{ marginBottom: '1rem' }}>
              <strong>Last Updated:</strong> January 2026
            </p>

            <h4 style={{ color: '#d4af37', marginBottom: '0.5rem', marginTop: '1.5rem' }}>
              Information We Collect
            </h4>
            <p style={{ margin: 0, marginBottom: '1rem' }}>
              We collect information you provide directly to us, including when you
              create an account, record stories, or communicate with us. This may
              include your name, email address, and story content.
            </p>

            <h4 style={{ color: '#d4af37', marginBottom: '0.5rem', marginTop: '1.5rem' }}>
              How We Use Your Information
            </h4>
            <p style={{ margin: 0, marginBottom: '1rem' }}>
              Your information is used to provide and improve our services, communicate
              with you, and ensure the security of your account and stories.
            </p>

            <h4 style={{ color: '#d4af37', marginBottom: '0.5rem', marginTop: '1.5rem' }}>
              Data Security
            </h4>
            <p style={{ margin: 0, marginBottom: '1rem' }}>
              We implement industry-standard security measures to protect your personal
              information and story content. Your stories are encrypted and stored securely.
            </p>

            <div style={{
              padding: '1rem',
              backgroundColor: '#1a0f08',
              borderRadius: '8px',
              borderLeft: '4px solid #d4af37',
              marginTop: '1rem',
            }}>
              <strong>Your Rights:</strong> You have the right to access, modify, or
              delete your personal information and stories at any time.
            </div>
          </div>

          {/* Terms of Service Section */}
          <div>
            <h3 style={{ color: '#d4af37', marginBottom: '1rem' }}>
              Terms of Service
            </h3>

            <p style={{ marginBottom: '1rem' }}>
              <strong>Last Updated:</strong> January 2026
            </p>

            <h4 style={{ color: '#d4af37', marginBottom: '0.5rem', marginTop: '1.5rem' }}>
              Account Responsibilities
            </h4>
            <p style={{ margin: 0, marginBottom: '1rem' }}>
              You are responsible for maintaining the security of your account and
              for all activities that occur under your account.
            </p>

            <h4 style={{ color: '#d4af37', marginBottom: '0.5rem', marginTop: '1.5rem' }}>
              Content Ownership
            </h4>
            <p style={{ margin: 0, marginBottom: '1rem' }}>
              You retain all rights to your stories and content. We only use your
              content to provide and improve our services to you.
            </p>

            <h4 style={{ color: '#d4af37', marginBottom: '0.5rem', marginTop: '1.5rem' }}>
              Acceptable Use
            </h4>
            <p style={{ margin: 0, marginBottom: '1rem' }}>
              You agree to use our service in compliance with all applicable laws
              and regulations. Prohibited activities include harassment, spam, or
              any illegal content.
            </p>

            <div style={{
              padding: '1rem',
              backgroundColor: '#1a0f08',
              borderRadius: '8px',
              borderLeft: '4px solid #d4af37',
              marginTop: '1rem',
            }}>
              <strong>Note:</strong> By using our service, you agree to these terms.
              We may update these terms from time to time, and continued use
              constitutes acceptance of any changes.
            </div>
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
        </div>
      </div>
    </>
  )
}
