import { useState } from 'react';
import LegacyApp from "./legacy/LegacyApp";
import { TestSteamModal } from './TestSteamModal';
import { TestSteamV36 } from './TestSteamV36';
import { TestSteamV37 } from './TestSteamV37';
import { TestSteamV35vsV37 } from './TestSteamV35vsV37';
import { TestSteamSideBySide } from './TestSteamSideBySide';
import {
  SteamModal,
  ContentParagraph,
  ContentDivider,
  ContentSection,
} from './components/steam-modal';

type ModalType = 'story' | 'booking' | 'privacy' | null;

export default function App() {
  // Check URL for test modes
  const isTestMode = window.location.search.includes('test=modal');
  const isComparisonMode = window.location.search.includes('test=comparison');
  const isV36Test = window.location.search.includes('test=v36');
  const isV37Test = window.location.search.includes('test=v37');
  const isCompare37 = window.location.search.includes('test=compare37');

  // Show test pages if requested
  if (isCompare37) {
    return <TestSteamV35vsV37 />;
  }

  if (isV37Test) {
    return <TestSteamV37 />;
  }

  if (isV36Test) {
    return <TestSteamV36 />;
  }

  if (isComparisonMode) {
    return <TestSteamSideBySide />;
  }

  if (isTestMode) {
    return <TestSteamModal />;
  }

  const [showDemoButtons, setShowDemoButtons] = useState(false);
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
    <>
      <LegacyApp />

      {/* Demo Toggle Button - Bottom Right Corner */}
      <button
        onClick={() => setShowDemoButtons(!showDemoButtons)}
        style={{
          position: 'fixed',
          bottom: '20px',
          right: '20px',
          zIndex: 9999,
          padding: '10px 18px',
          background: showDemoButtons ? '#8B6F47' : 'linear-gradient(180deg, #6a5a4a, #2a1a0a)',
          border: '2px solid #8B6F47',
          borderRadius: '8px',
          color: '#f5deb3',
          cursor: 'pointer',
          fontSize: '13px',
          fontWeight: 'bold',
          textTransform: 'uppercase',
          boxShadow: '0 4px 12px rgba(0,0,0,0.4)',
        }}
      >
        {showDemoButtons ? '✕' : '🎭 Steam Modal Demo'}
      </button>

      {/* Demo Modal Buttons - Floating Panel */}
      {showDemoButtons && (
        <div
          style={{
            position: 'fixed',
            bottom: '80px',
            right: '20px',
            zIndex: 9999,
            display: 'flex',
            flexDirection: 'column',
            gap: '10px',
            padding: '16px',
            background: 'rgba(42, 26, 10, 0.95)',
            border: '2px solid #8B6F47',
            borderRadius: '8px',
            boxShadow: '0 8px 24px rgba(0,0,0,0.6)',
          }}
        >
          <div
            style={{
              color: '#f5deb3',
              fontSize: '12px',
              marginBottom: '8px',
              textAlign: 'center',
              fontWeight: 'bold',
            }}
          >
            Try These Modals:
          </div>

          <button
            onClick={() => setActiveModal('story')}
            style={{
              padding: '10px 16px',
              background: 'linear-gradient(180deg, #6a5a4a, #2a1a0a)',
              border: '2px solid #8B6F47',
              borderRadius: '6px',
              color: '#f5deb3',
              cursor: 'pointer',
              fontSize: '12px',
              fontWeight: 'bold',
              whiteSpace: 'nowrap',
            }}
          >
            📖 Our Story
          </button>

          <button
            onClick={() => setActiveModal('booking')}
            style={{
              padding: '10px 16px',
              background: 'linear-gradient(180deg, #6a5a4a, #2a1a0a)',
              border: '2px solid #8B6F47',
              borderRadius: '6px',
              color: '#f5deb3',
              cursor: 'pointer',
              fontSize: '12px',
              fontWeight: 'bold',
              whiteSpace: 'nowrap',
            }}
          >
            📅 Book Now
          </button>

          <button
            onClick={() => setActiveModal('privacy')}
            style={{
              padding: '10px 16px',
              background: 'linear-gradient(180deg, #6a5a4a, #2a1a0a)',
              border: '2px solid #8B6F47',
              borderRadius: '6px',
              color: '#f5deb3',
              cursor: 'pointer',
              fontSize: '12px',
              fontWeight: 'bold',
              whiteSpace: 'nowrap',
            }}
          >
            🔒 Privacy Policy
          </button>
        </div>
      )}

      {/* Our Story Modal */}
      {activeModal === 'story' && (
        <SteamModal
          isOpen={true}
          onClose={() => setActiveModal(null)}
          title="Our Story"
          variant="standard"
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
                  htmlFor="demo-name"
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
                  id="demo-name"
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
                  htmlFor="demo-email"
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
                  id="demo-email"
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
                  id="demo-date"
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
    </>
  );
}