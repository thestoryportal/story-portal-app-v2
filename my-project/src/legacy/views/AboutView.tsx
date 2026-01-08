/**
 * AboutView Component
 *
 * About/How to Play view.
 * Uses ModalContentWindow for consistent steampunk styling.
 */

import { ModalContentWindow } from '../../components/modal'

interface AboutViewProps {
  onBack: () => void
}

export function AboutView({ onBack }: AboutViewProps) {
  return (
    <ModalContentWindow title="How to Play" onClose={onBack} maxWidth="sm">
      <div>
        <p>
          The Story Portal is a Love Burn festival experience where you can spin the wheel, select a
          prompt, and record your stories to share with the community.
        </p>
        <h3 style={{ marginTop: '24px', color: '#f5deb3' }}>Steps:</h3>
        <ol style={{ color: '#f5deb3' }}>
          <li>Spin the wheel to reveal story prompts</li>
          <li>Select a prompt that speaks to you</li>
          <li>Record your story in your own words</li>
          <li>Share with the community or keep it private</li>
        </ol>
      </div>
    </ModalContentWindow>
  )
}
