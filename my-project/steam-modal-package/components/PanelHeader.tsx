/**
 * PanelHeader Component
 * 
 * Wooden panel that animates in from above.
 * Uses the same style as hamburger menu panels for visual consistency.
 * 
 * REFERENCES:
 * - MenuPanelItem.tsx for wooden panel styling
 * - wood-panel.webp texture (if available)
 * - design-tokens-quick-ref.md for colors
 */

import styles from './PanelHeader.module.css';

interface PanelHeaderProps {
  title: string;
}

export function PanelHeader({ title }: PanelHeaderProps) {
  return (
    <header className={styles.header} id="modal-title">
      {/* Corner rivets for mechanical feel */}
      <div className={`${styles.rivet} ${styles.rivetTL}`} aria-hidden="true" />
      <div className={`${styles.rivet} ${styles.rivetTR}`} aria-hidden="true" />
      <div className={`${styles.rivet} ${styles.rivetBL}`} aria-hidden="true" />
      <div className={`${styles.rivet} ${styles.rivetBR}`} aria-hidden="true" />
      
      {/* Title text */}
      <h1 className={styles.title}>{title}</h1>
    </header>
  );
}
