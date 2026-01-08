/**
 * DevToolsView Component
 *
 * Developer tools view placeholder.
 * Previous experimental animation/component tools have been archived.
 * This view is reserved for future developer tool implementations.
 *
 * Usage:
 * <DevToolsView onBack={() => setView('wheel')} />
 */

import { ModalContentWindow } from '../../components/modal'

interface DevToolsViewProps {
  onBack: () => void
}

export function DevToolsView({ onBack }: DevToolsViewProps) {
  return (
    <ModalContentWindow title="Developer Tools" onClose={onBack} maxWidth="md">
      <div style={{ padding: '2rem', textAlign: 'center' }}>
        <p style={{ fontSize: '1.1rem', color: '#888' }}>
          Developer tools are being rebuilt with the new agent platform.
        </p>
        <p style={{ fontSize: '0.95rem', color: '#aaa', marginTop: '1rem' }}>
          Check back soon for animation controls, design review, and code analysis tools.
        </p>
      </div>
    </ModalContentWindow>
  )
}
