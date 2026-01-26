/**
 * Steam Modal Usage Examples
 * 
 * Copy these examples into your application to use the Steam Modal.
 */

import { useState } from 'react';
import { 
  SteamModal, 
  ContentParagraph, 
  ContentDivider,
  ContentSection 
} from './components/steam-modal';

// ============================================
// Example 1: Basic Usage
// ============================================

export function BasicExample() {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <>
      <button onClick={() => setIsOpen(true)}>
        Open Modal
      </button>
      
      <SteamModal
        isOpen={isOpen}
        onClose={() => setIsOpen(false)}
        title="Our Story"
      >
        <ContentParagraph index={0}>
          Welcome to The Story Portal, where tales come alive through 
          the breath of the machine.
        </ContentParagraph>
        
        <ContentDivider />
        
        <ContentParagraph index={1}>
          Every story you share becomes part of our collective memory,
          preserved in steam and brass.
        </ContentParagraph>
      </SteamModal>
    </>
  );
}

// ============================================
// Example 2: Form Variant (Booking)
// ============================================

export function BookingExample() {
  const [isOpen, setIsOpen] = useState(false);
  const [formData, setFormData] = useState({
    name: '',
    email: '',
    date: '',
    message: ''
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    console.log('Booking submitted:', formData);
    setIsOpen(false);
  };

  return (
    <>
      <button onClick={() => setIsOpen(true)}>
        Book Now
      </button>
      
      <SteamModal
        isOpen={isOpen}
        onClose={() => setIsOpen(false)}
        title="Book Your Experience"
        variant="form"
        steamDensity="light"
      >
        <form onSubmit={handleSubmit}>
          <ContentSection title="Your Details">
            <div style={{ marginBottom: '16px' }}>
              <label htmlFor="name" style={{ display: 'block', marginBottom: '8px', color: '#2a1a0a' }}>
                Name
              </label>
              <input
                id="name"
                type="text"
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                style={{
                  width: '100%',
                  padding: '12px',
                  border: '2px solid #8B6F47',
                  borderRadius: '4px',
                  background: '#fff',
                  color: '#2a1a0a',
                  fontSize: '16px'
                }}
                required
              />
            </div>
            
            <div style={{ marginBottom: '16px' }}>
              <label htmlFor="email" style={{ display: 'block', marginBottom: '8px', color: '#2a1a0a' }}>
                Email
              </label>
              <input
                id="email"
                type="email"
                value={formData.email}
                onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                style={{
                  width: '100%',
                  padding: '12px',
                  border: '2px solid #8B6F47',
                  borderRadius: '4px',
                  background: '#fff',
                  color: '#2a1a0a',
                  fontSize: '16px'
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
                onChange={(e) => setFormData({ ...formData, date: e.target.value })}
                style={{
                  width: '100%',
                  padding: '12px',
                  border: '2px solid #8B6F47',
                  borderRadius: '4px',
                  background: '#fff',
                  color: '#2a1a0a',
                  fontSize: '16px'
                }}
                required
              />
            </div>
          </ContentSection>
          
          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '12px', marginTop: '24px' }}>
            <button
              type="button"
              onClick={() => setIsOpen(false)}
              style={{
                padding: '12px 24px',
                background: 'transparent',
                border: '2px solid #8B6F47',
                borderRadius: '4px',
                color: '#2a1a0a',
                cursor: 'pointer',
                fontSize: '14px',
                fontWeight: 'bold',
                textTransform: 'uppercase'
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
                textTransform: 'uppercase'
              }}
            >
              Submit Booking
            </button>
          </div>
        </form>
      </SteamModal>
    </>
  );
}

// ============================================
// Example 3: Legal/Privacy Variant
// ============================================

export function PrivacyPolicyExample() {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <>
      <button onClick={() => setIsOpen(true)}>
        Privacy Policy
      </button>
      
      <SteamModal
        isOpen={isOpen}
        onClose={() => setIsOpen(false)}
        title="Privacy Policy"
        variant="legal"
        steamDensity="light"
      >
        <ContentSection title="Information We Collect">
          <ContentParagraph index={0}>
            We collect information you provide directly to us, such as when you 
            create an account, submit a story, or contact us for support.
          </ContentParagraph>
          <ContentParagraph index={1}>
            This may include your name, email address, and any other information 
            you choose to provide.
          </ContentParagraph>
        </ContentSection>
        
        <ContentDivider />
        
        <ContentSection title="How We Use Your Information">
          <ContentParagraph index={2}>
            We use the information we collect to provide, maintain, and improve 
            our services, including to process transactions and send related 
            information.
          </ContentParagraph>
        </ContentSection>
        
        <ContentDivider />
        
        <ContentSection title="Contact Us">
          <ContentParagraph index={3}>
            If you have any questions about this Privacy Policy, please contact 
            us at privacy@thestoryportal.com.
          </ContentParagraph>
        </ContentSection>
      </SteamModal>
    </>
  );
}

// ============================================
// Example 4: Multiple Modals with State Management
// ============================================

type ModalType = 'story' | 'booking' | 'privacy' | null;

export function MultipleModalsExample() {
  // IMPORTANT: Use a SINGLE state for modal management
  // to prevent stacking issues
  const [activeModal, setActiveModal] = useState<ModalType>(null);

  return (
    <>
      <nav style={{ display: 'flex', gap: '12px' }}>
        <button onClick={() => setActiveModal('story')}>Our Story</button>
        <button onClick={() => setActiveModal('booking')}>Book Now</button>
        <button onClick={() => setActiveModal('privacy')}>Privacy</button>
      </nav>
      
      {/* Only ONE modal renders at a time */}
      {activeModal === 'story' && (
        <SteamModal
          isOpen={true}
          onClose={() => setActiveModal(null)}
          title="Our Story"
          variant="standard"
        >
          <ContentParagraph index={0}>
            The Story Portal began as a dream...
          </ContentParagraph>
        </SteamModal>
      )}
      
      {activeModal === 'booking' && (
        <SteamModal
          isOpen={true}
          onClose={() => setActiveModal(null)}
          title="Book Your Experience"
          variant="form"
        >
          <ContentParagraph index={0}>
            Select your preferred date and time...
          </ContentParagraph>
        </SteamModal>
      )}
      
      {activeModal === 'privacy' && (
        <SteamModal
          isOpen={true}
          onClose={() => setActiveModal(null)}
          title="Privacy Policy"
          variant="legal"
        >
          <ContentParagraph index={0}>
            We respect your privacy...
          </ContentParagraph>
        </SteamModal>
      )}
    </>
  );
}

// ============================================
// Example 5: With Callbacks
// ============================================

export function CallbacksExample() {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <>
      <button onClick={() => setIsOpen(true)}>
        Open Modal
      </button>
      
      <SteamModal
        isOpen={isOpen}
        onClose={() => setIsOpen(false)}
        title="Modal with Callbacks"
        onOpened={() => {
          console.log('Modal fully opened');
          // Track analytics, load data, etc.
        }}
        onClosed={() => {
          console.log('Modal fully closed');
          // Cleanup, reset state, etc.
        }}
      >
        <ContentParagraph index={0}>
          This modal logs to console when it opens and closes.
        </ContentParagraph>
      </SteamModal>
    </>
  );
}
