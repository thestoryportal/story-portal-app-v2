/**
 * RecordView Component
 *
 * Recording interface for story prompts.
 * Uses ModalContentWindow for consistent steampunk styling.
 */

import { ModalContentWindow } from '../../components/modal'

interface RecordViewProps {
  selectedPrompt: string | null
  onBack: () => void
}

export function RecordView({ selectedPrompt, onBack }: RecordViewProps) {
  return (
    <ModalContentWindow title="Record Your Story" onClose={onBack} maxWidth="sm">
      <div>
        {selectedPrompt && (
          <div
            style={{
              background: 'rgba(139,69,19,0.3)',
              padding: '20px',
              borderRadius: '8px',
              marginBottom: '32px',
              border: '2px solid #8B6F47',
            }}
          >
            <p
              style={{
                color: '#f5deb3',
                fontSize: '20px',
                fontWeight: 'bold',
                margin: 0,
                textAlign: 'center',
              }}
            >
              {selectedPrompt}
            </p>
          </div>
        )}
        <p style={{ textAlign: 'center' }}>Recording functionality coming soon...</p>
      </div>
    </ModalContentWindow>
  )
}
