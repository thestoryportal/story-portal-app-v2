/**
 * PanelHeader Component
 *
 * Wooden panel that animates in from above.
 * Features dynamic title sizing based on length.
 *
 * REFERENCES:
 * - MenuPanelItem.tsx for wooden panel styling
 * - wood-panel.webp texture (if available)
 * - design-tokens-quick-ref.md for colors
 */

import { useMemo } from 'react';
import styles from './PanelHeader.module.css';

interface PanelHeaderProps {
  title: string;
}

export function PanelHeader({ title }: PanelHeaderProps) {
  // Dynamic sizing based on title length
  const titleClass = useMemo(() => {
    const length = title.length;
    if (length <= 20) return styles.titleLarge;
    if (length <= 40) return styles.titleMedium;
    return styles.titleSmall;
  }, [title]);

  // Truncate extremely long titles
  const displayTitle = title.length > 60
    ? `${title.substring(0, 57)}...`
    : title;

  return (
    <header className={styles.header} id="modal-title">
      {/* Title text with dynamic sizing */}
      <h1 className={`${styles.title} ${titleClass}`} title={title}>
        {displayTitle}
      </h1>
    </header>
  );
}
