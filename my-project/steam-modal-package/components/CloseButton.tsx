/**
 * CloseButton Component
 * 
 * Simple brass circular button for closing the modal.
 * Phase 1 uses a simplified design.
 * Phase 3 will upgrade to full valve wheel design.
 * 
 * REFERENCES:
 * - design-tokens-quick-ref.md for brass gradient colors
 * - Button patterns from NavButtons.tsx
 */

import styles from './CloseButton.module.css';

interface CloseButtonProps {
  onClick: () => void;
}

export function CloseButton({ onClick }: CloseButtonProps) {
  return (
    <button
      className={styles.closeButton}
      onClick={onClick}
      aria-label="Close modal"
      type="button"
    >
      <span className={styles.icon} aria-hidden="true">×</span>
    </button>
  );
}
