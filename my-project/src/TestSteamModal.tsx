/**
 * Standalone test page for Steam Modal
 * Navigate to this route to test the modal in isolation
 */

import { useState } from 'react';
import { SteamModal, ContentParagraph } from './components/steam-modal';
import { DiagnosticModal } from './components/steam-modal/DiagnosticModal';

export function TestSteamModal() {
  const [isOpen, setIsOpen] = useState(true); // Start with modal open
  const [showDiagnostic, setShowDiagnostic] = useState(false);

  return (
    <div style={{
      minHeight: '100vh',
      background: '#1a0f0a',
      padding: '40px',
      color: '#f5deb3',
    }}>
      <h1>Steam Modal Test Page</h1>
      <p>The modal should be visible when this page loads.</p>

      <div style={{ display: 'flex', gap: '12px', marginTop: '20px' }}>
        <button
          onClick={() => setIsOpen(true)}
          style={{
            padding: '12px 24px',
            background: 'linear-gradient(180deg, #6a5a4a, #2a1a0a)',
            border: '2px solid #8B6F47',
            borderRadius: '4px',
            color: '#f5deb3',
            cursor: 'pointer',
            fontSize: '14px',
            fontWeight: 'bold',
          }}
        >
          Open Modal
        </button>

        <button
          onClick={() => setShowDiagnostic(true)}
          style={{
            padding: '12px 24px',
            background: '#c44',
            border: '2px solid #f88',
            borderRadius: '4px',
            color: 'white',
            cursor: 'pointer',
            fontSize: '14px',
            fontWeight: 'bold',
          }}
        >
          🔍 Run Diagnostic
        </button>
      </div>

      <div style={{ marginTop: '20px', background: 'rgba(255,255,255,0.1)', padding: '20px', borderRadius: '8px' }}>
        <h3>Expected to see:</h3>
        <ul>
          <li>✓ Dark warm backdrop (vignette effect)</li>
          <li>✓ Warm brown/tan steam wisps (animated)</li>
          <li>✓ Wooden panel header at top with "Test Modal" title</li>
          <li>✓ Parchment-colored content panel in center</li>
          <li>✓ Dark brown text on parchment (high contrast)</li>
          <li>✓ Brass circular X button (top-right)</li>
        </ul>

        <h3 style={{ marginTop: '20px' }}>Debug Info:</h3>
        <p>Modal state: <strong>{isOpen ? 'OPEN' : 'CLOSED'}</strong></p>
        <p>Check browser console for any errors.</p>
        <p>Press F12 and look at Elements tab - search for 'role="dialog"'</p>
      </div>

      <SteamModal
        isOpen={isOpen}
        onClose={() => {
          console.log('[TestPage] Modal closed');
          setIsOpen(false);
        }}
        title="Test Modal"
        variant="standard"
        onOpened={() => console.log('[TestPage] Modal opened')}
        onClosed={() => console.log('[TestPage] Modal closed animation complete')}
      >
        <ContentParagraph index={0}>
          This is test content in the Steam Modal. You should see this text
          in DARK BROWN on a PARCHMENT background.
        </ContentParagraph>

        <ContentParagraph index={1}>
          Behind this content panel, you should see warm brown/tan steam effects
          animating gently.
        </ContentParagraph>

        <ContentParagraph index={2}>
          Above this content, there should be a wooden panel with bronze borders
          displaying "Test Modal" as the title.
        </ContentParagraph>
      </SteamModal>

      {showDiagnostic && <DiagnosticModal />}
    </div>
  );
}
