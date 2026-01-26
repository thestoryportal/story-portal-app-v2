/**
 * Simple test to verify components render
 */

import { SteamModal, ContentParagraph } from './index';

export function SimpleTest() {
  return (
    <div style={{ padding: '40px', background: '#000', minHeight: '100vh' }}>
      <h1 style={{ color: 'white' }}>Testing Steam Modal</h1>

      <SteamModal
        isOpen={true}
        onClose={() => console.log('close clicked')}
        title="Test Modal"
      >
        <ContentParagraph index={0}>
          This is a test paragraph to see if the modal renders at all.
        </ContentParagraph>
      </SteamModal>
    </div>
  );
}
