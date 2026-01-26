/**
 * Backdrop Component
 * 
 * Creates the darkened, warm-tinted background for the steam modal.
 * Clicking anywhere on the backdrop closes the modal.
 * 
 * REFERENCES:
 * - Colors from design-tokens-quick-ref.md
 * - Z-index: 1001 (below smoke layers)
 */

import { useEffect } from 'react';
import styles from './Backdrop.module.css';

interface BackdropProps {
  isOpen: boolean;
  onClose: () => void;
}

export function Backdrop({ isOpen, onClose }: BackdropProps) {
  // Prevent body scroll when modal is open
  useEffect(() => {
    if (isOpen) {
      const originalOverflow = document.body.style.overflow;
      document.body.style.overflow = 'hidden';
      return () => {
        document.body.style.overflow = originalOverflow;
      };
    }
  }, [isOpen]);

  if (!isOpen) return null;

  return (
    <div
      className={styles.backdrop}
      onClick={onClose}
      role="button"
      tabIndex={0}
      aria-label="Close modal"
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          onClose();
        }
      }}
    />
  );
}
