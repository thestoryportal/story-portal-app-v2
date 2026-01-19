/**
 * InquiryModal - Contact and inquiry form
 *
 * Modal for users to submit inquiries and contact requests.
 */

import { useEffect, useState } from 'react'

export interface InquiryModalProps {
  isOpen: boolean
  onClose: () => void
  onNext: () => void
  onPrev: () => void
}

export function InquiryModal({ isOpen, onClose, onNext, onPrev }: InquiryModalProps) {
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [message, setMessage] = useState('')
  const [submitted, setSubmitted] = useState(false)

  // Handle escape key
  useEffect(() => {
    if (!isOpen) return

    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    }

    window.addEventListener('keydown', handleEscape)
    return () => window.removeEventListener('keydown', handleEscape)
  }, [isOpen, onClose])

  // Reset form when modal closes
  useEffect(() => {
    if (!isOpen) {
      setSubmitted(false)
    }
  }, [isOpen])

  if (!isOpen) return null

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()

    if (!name.trim() || !email.trim() || !message.trim()) {
      alert('Please fill out all fields.')
      return
    }

    // TODO: Implement actual form submission to backend
    console.log('Inquiry submitted:', { name, email, message })
    setSubmitted(true)

    // Reset form after 2 seconds
    setTimeout(() => {
      setName('')
      setEmail('')
      setMessage('')
    }, 2000)
  }

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
            Get In Touch
          </h2>
        </div>

        {/* Content */}
        <div style={{
          padding: '2rem',
          color: '#f5e6d3',
          overflowY: 'auto',
          maxHeight: 'calc(80vh - 200px)',
        }}>
          {submitted ? (
            <div style={{
              padding: '2rem',
              textAlign: 'center',
              backgroundColor: '#1a0f08',
              borderRadius: '8px',
              border: '2px solid #4CAF50',
            }}>
              <div style={{ fontSize: '3rem', marginBottom: '1rem' }}>✓</div>
              <h3 style={{ color: '#4CAF50', marginTop: 0, marginBottom: '0.5rem' }}>
                Thank You!
              </h3>
              <p style={{ margin: 0 }}>
                Your inquiry has been submitted. We'll get back to you soon!
              </p>
            </div>
          ) : (
            <form onSubmit={handleSubmit}>
              <p style={{ marginTop: 0, marginBottom: '1.5rem', lineHeight: '1.6' }}>
                Have questions about our services or want to discuss your project?
                Fill out the form below and we'll be in touch shortly.
              </p>

              <div style={{ marginBottom: '1.5rem' }}>
                <label style={{
                  display: 'block',
                  color: '#d4af37',
                  marginBottom: '0.5rem',
                  fontWeight: 'bold',
                }}>
                  Name *
                </label>
                <input
                  type="text"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  required
                  style={{
                    width: '100%',
                    padding: '0.75rem',
                    fontSize: '16px',
                    backgroundColor: '#1a0f08',
                    color: '#f5e6d3',
                    border: '2px solid #8b6f47',
                    borderRadius: '8px',
                    fontFamily: 'inherit',
                  }}
                />
              </div>

              <div style={{ marginBottom: '1.5rem' }}>
                <label style={{
                  display: 'block',
                  color: '#d4af37',
                  marginBottom: '0.5rem',
                  fontWeight: 'bold',
                }}>
                  Email *
                </label>
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                  style={{
                    width: '100%',
                    padding: '0.75rem',
                    fontSize: '16px',
                    backgroundColor: '#1a0f08',
                    color: '#f5e6d3',
                    border: '2px solid #8b6f47',
                    borderRadius: '8px',
                    fontFamily: 'inherit',
                  }}
                />
              </div>

              <div style={{ marginBottom: '1.5rem' }}>
                <label style={{
                  display: 'block',
                  color: '#d4af37',
                  marginBottom: '0.5rem',
                  fontWeight: 'bold',
                }}>
                  Message *
                </label>
                <textarea
                  value={message}
                  onChange={(e) => setMessage(e.target.value)}
                  required
                  rows={6}
                  style={{
                    width: '100%',
                    padding: '0.75rem',
                    fontSize: '16px',
                    backgroundColor: '#1a0f08',
                    color: '#f5e6d3',
                    border: '2px solid #8b6f47',
                    borderRadius: '8px',
                    resize: 'vertical',
                    fontFamily: 'inherit',
                  }}
                />
              </div>

              <button
                type="submit"
                style={{
                  width: '100%',
                  padding: '1rem',
                  fontSize: '18px',
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
                Submit Inquiry
              </button>
            </form>
          )}
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
              Next →
            </button>
          </div>
        </div>
      </div>
    </>
  )
}
