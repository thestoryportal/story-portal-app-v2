/**
 * ContentPanel Component
 * 
 * The readable content area with HIGH CONTRAST text.
 * 
 * CRITICAL CONTRAST REQUIREMENT:
 * - Background: #f4e4c8 (parchment)
 * - Text: #2a1a0a (dark brown)
 * - Contrast ratio: 14:1 (exceeds WCAG AAA)
 * 
 * This was the CRITICAL failure point in the previous implementation.
 * The spec originally had light text on dark/transparent background.
 * This version MUST use dark text on light parchment.
 * 
 * REFERENCES:
 * - phase-1-foundation-spec.md Section 4
 * - design-tokens-quick-ref.md for colors
 */

import { ReactNode } from 'react';
import styles from './ContentPanel.module.css';

interface ContentPanelProps {
  children: ReactNode;
  title?: string;
}

export function ContentPanel({ children, title }: ContentPanelProps) {
  return (
    <div className={styles.contentPanel}>
      {title && (
        <h2 className={styles.sectionTitle}>{title}</h2>
      )}
      <div className={styles.bodyContent}>
        {children}
      </div>
    </div>
  );
}

/**
 * ContentParagraph - Sub-component for paragraphs with staggered animation
 * 
 * Usage:
 *   <ContentParagraph index={0}>First paragraph</ContentParagraph>
 *   <ContentParagraph index={1}>Second paragraph</ContentParagraph>
 */
export function ContentParagraph({ 
  children, 
  index = 0 
}: { 
  children: ReactNode; 
  index?: number;
}) {
  return (
    <p 
      className={styles.bodyText}
      style={{ animationDelay: `${0.4 + (index * 0.1)}s` }}
    >
      {children}
    </p>
  );
}

/**
 * ContentDivider - Decorative divider between content sections
 */
export function ContentDivider() {
  return <hr className={styles.divider} />;
}

/**
 * ContentSection - Sub-component for titled sections within modal
 */
export function ContentSection({ 
  title, 
  children 
}: { 
  title: string; 
  children: ReactNode;
}) {
  return (
    <section className={styles.section}>
      <h3 className={styles.sectionTitle}>{title}</h3>
      {children}
    </section>
  );
}
