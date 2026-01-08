/**
 * StoriesView Component
 *
 * View for displaying saved stories.
 * Uses ModalContentWindow for consistent steampunk styling.
 */

import { ModalContentWindow } from '../../components/modal'
import styles from './views.module.css'

interface StoriesViewProps {
  onBack: () => void
}

export function StoriesView({ onBack }: StoriesViewProps) {
  return (
    <ModalContentWindow title="My Stories" onClose={onBack} maxWidth="lg">
      <div className={styles.emptyState}>
        <p className={styles.emptyText}>Your recorded stories will appear here...</p>
      </div>
    </ModalContentWindow>
  )
}
