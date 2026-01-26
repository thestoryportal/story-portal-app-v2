/**
 * Steam Modal Demo Component
 *
 * Copy this component into your app to test the Steam Modal.
 * You can integrate this into your main App.tsx or any other component.
 */

import { useState } from 'react';
import {
  SteamModal,
  ContentParagraph,
  ContentDivider,
  ContentSection,
} from './index';

type ModalType = 'story' | 'booking' | 'privacy' | null;

export function SteamModalDemo() {
  const [activeModal, setActiveModal] = useState<ModalType>(null);
  const [formData, setFormData] = useState({
    name: '',
    email: '',
    date: '',
  });

  const handleBookingSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    console.log('Booking submitted:', formData);
    alert('Booking request submitted! Check console for details.');
    setActiveModal(null);
  };

  return (
    <div
      style={{
        padding: '40px',
        fontFamily: 'sans-serif',
        maxWidth: '1200px',
        margin: '0 auto',
      }}
    >
      <h1 style={{ marginBottom: '24px', color: '#2a1a0a' }}>
        Steam Modal Demo
      </h1>

      <p style={{ marginBottom: '24px', color: '#4a3a2a', lineHeight: 1.6 }}>
        Click any button below to see the Steam Modal in action. Each variant
        demonstrates different use cases and steam densities.
      </p>

      {/* Demo Buttons */}
      <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap' }}>
        <button
          onClick={() => setActiveModal('story')}
          style={{
            padding: '12px 24px',
            background: 'linear-gradient(180deg, #6a5a4a, #2a1a0a)',
            border: '2px solid #8B6F47',
            borderRadius: '4px',
            color: '#f5deb3',
            cursor: 'pointer',
            fontSize: '14px',
            fontWeight: 'bold',
            textTransform: 'uppercase',
          }}
        >
          Our Story (Standard)
        </button>

        <button
          onClick={() => setActiveModal('booking')}
          style={{
            padding: '12px 24px',
            background: 'linear-gradient(180deg, #6a5a4a, #2a1a0a)',
            border: '2px solid #8B6F47',
            borderRadius: '4px',
            color: '#f5deb3',
            cursor: 'pointer',
            fontSize: '14px',
            fontWeight: 'bold',
            textTransform: 'uppercase',
          }}
        >
          Book Now (Form Variant)
        </button>

        <button
          onClick={() => setActiveModal('privacy')}
          style={{
            padding: '12px 24px',
            background: 'linear-gradient(180deg, #6a5a4a, #2a1a0a)',
            border: '2px solid #8B6F47',
            borderRadius: '4px',
            color: '#f5deb3',
            cursor: 'pointer',
            fontSize: '14px',
            fontWeight: 'bold',
            textTransform: 'uppercase',
          }}
        >
          Privacy Policy (Legal)
        </button>
      </div>

      {/* Features List */}
      <div style={{ marginTop: '48px' }}>
        <h2 style={{ marginBottom: '16px', color: '#2a1a0a' }}>Features</h2>
        <ul style={{ color: '#4a3a2a', lineHeight: 1.8 }}>
          <li>Warm brown/tan steam effects matching existing app aesthetic</li>
          <li>High contrast parchment content panel (14:1 contrast ratio)</li>
          <li>Animated wooden header that tumbles in</li>
          <li>Brass circular close button</li>
          <li>Close via X button, Escape key, or click outside</li>
          <li>Proper focus management and accessibility</li>
          <li>No modal stacking issues</li>
          <li>Multiple variants for different use cases</li>
        </ul>
      </div>

      {/* Our Story Modal */}
      {activeModal === 'story' && (
        <SteamModal
          isOpen={true}
          onClose={() => setActiveModal(null)}
          title="Our Story"
          variant="standard"
          onOpened={() => console.log('Story modal opened')}
          onClosed={() => console.log('Story modal closed')}
        >
          <ContentParagraph index={0}>
            Welcome to The Story Portal, where tales come alive through the
            breath of the machine. In this realm of steam and brass, your words
            transcend mere text to become living, breathing narratives.
          </ContentParagraph>

          <ContentDivider />

          <ContentParagraph index={1}>
            Every story you share becomes part of our collective memory,
            preserved in the eternal dance of steam and cogwork. Here, in this
            intersection of art and machinery, your imagination finds its voice.
          </ContentParagraph>

          <ContentDivider />

          <ContentParagraph index={2}>
            Step inside. Tell your tale. Let the steam carry your words into
            eternity.
          </ContentParagraph>
        </SteamModal>
      )}

      {/* Booking Modal */}
      {activeModal === 'booking' && (
        <SteamModal
          isOpen={true}
          onClose={() => setActiveModal(null)}
          title="Book Your Experience"
          variant="form"
          steamDensity="light"
        >
          <form onSubmit={handleBookingSubmit}>
            <ContentSection title="Your Details">
              <div style={{ marginBottom: '16px' }}>
                <label
                  htmlFor="name"
                  style={{
                    display: 'block',
                    marginBottom: '8px',
                    color: '#2a1a0a',
                    fontWeight: 'bold',
                  }}
                >
                  Name
                </label>
                <input
                  id="name"
                  type="text"
                  value={formData.name}
                  onChange={(e) =>
                    setFormData({ ...formData, name: e.target.value })
                  }
                  style={{
                    width: '100%',
                    padding: '12px',
                    border: '2px solid #8B6F47',
                    borderRadius: '4px',
                    background: '#fff',
                    color: '#2a1a0a',
                    fontSize: '16px',
                    boxSizing: 'border-box',
                  }}
                  required
                />
              </div>

              <div style={{ marginBottom: '16px' }}>
                <label
                  htmlFor="email"
                  style={{
                    display: 'block',
                    marginBottom: '8px',
                    color: '#2a1a0a',
                    fontWeight: 'bold',
                  }}
                >
                  Email
                </label>
                <input
                  id="email"
                  type="email"
                  value={formData.email}
                  onChange={(e) =>
                    setFormData({ ...formData, email: e.target.value })
                  }
                  style={{
                    width: '100%',
                    padding: '12px',
                    border: '2px solid #8B6F47',
                    borderRadius: '4px',
                    background: '#fff',
                    color: '#2a1a0a',
                    fontSize: '16px',
                    boxSizing: 'border-box',
                  }}
                  required
                />
              </div>
            </ContentSection>

            <ContentDivider />

            <ContentSection title="Preferred Date">
              <div style={{ marginBottom: '16px' }}>
                <input
                  id="date"
                  type="date"
                  value={formData.date}
                  onChange={(e) =>
                    setFormData({ ...formData, date: e.target.value })
                  }
                  style={{
                    width: '100%',
                    padding: '12px',
                    border: '2px solid #8B6F47',
                    borderRadius: '4px',
                    background: '#fff',
                    color: '#2a1a0a',
                    fontSize: '16px',
                    boxSizing: 'border-box',
                  }}
                  required
                />
              </div>
            </ContentSection>

            <div
              style={{
                display: 'flex',
                justifyContent: 'flex-end',
                gap: '12px',
                marginTop: '24px',
              }}
            >
              <button
                type="button"
                onClick={() => setActiveModal(null)}
                style={{
                  padding: '12px 24px',
                  background: 'transparent',
                  border: '2px solid #8B6F47',
                  borderRadius: '4px',
                  color: '#2a1a0a',
                  cursor: 'pointer',
                  fontSize: '14px',
                  fontWeight: 'bold',
                  textTransform: 'uppercase',
                }}
              >
                Cancel
              </button>
              <button
                type="submit"
                style={{
                  padding: '12px 24px',
                  background: 'linear-gradient(180deg, #6a5a4a, #2a1a0a)',
                  border: '2px solid #8B6F47',
                  borderRadius: '4px',
                  color: '#f5deb3',
                  cursor: 'pointer',
                  fontSize: '14px',
                  fontWeight: 'bold',
                  textTransform: 'uppercase',
                }}
              >
                Submit Booking
              </button>
            </div>
          </form>
        </SteamModal>
      )}

      {/* Privacy Policy Modal */}
      {activeModal === 'privacy' && (
        <SteamModal
          isOpen={true}
          onClose={() => setActiveModal(null)}
          title="Privacy Policy"
          variant="legal"
          steamDensity="light"
        >
          <ContentSection title="Information We Collect">
            <ContentParagraph index={0}>
              We collect information you provide directly to us, such as when
              you create an account, submit a story, or contact us for support.
            </ContentParagraph>
            <ContentParagraph index={1}>
              This may include your name, email address, and any other
              information you choose to provide.
            </ContentParagraph>
          </ContentSection>

          <ContentDivider />

          <ContentSection title="How We Use Your Information">
            <ContentParagraph index={2}>
              We use the information we collect to provide, maintain, and
              improve our services, including to process transactions and send
              related information.
            </ContentParagraph>
            <ContentParagraph index={3}>
              We may also use the information to communicate with you about
              products, services, offers, and events offered by The Story Portal
              and others.
            </ContentParagraph>
          </ContentSection>

          <ContentDivider />

          <ContentSection title="Information Sharing">
            <ContentParagraph index={4}>
              We do not share your personal information with third parties
              except as described in this policy or with your consent.
            </ContentParagraph>
          </ContentSection>

          <ContentDivider />

          <ContentSection title="Contact Us">
            <ContentParagraph index={5}>
              If you have any questions about this Privacy Policy, please
              contact us at privacy@thestoryportal.com.
            </ContentParagraph>
          </ContentSection>
        </SteamModal>
      )}
    </div>
  );
}
