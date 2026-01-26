/**
 * ContentPanel Component
 *
 * The readable content area with parchment frame and scroll-through-steam effect.
 *
 * FEATURES:
 * - Semi-transparent parchment background creating reading zone
 * - Steam overlays at top and bottom that content scrolls through
 * - Scroll indicators for discoverability
 * - Adaptive visibility based on scroll position
 */

import { ReactNode, useRef, useEffect, useState, useCallback } from 'react';
import styles from './ContentPanel.module.css';

interface ContentPanelProps {
  children: ReactNode;
  title?: string;
}

export function ContentPanel({ children, title }: ContentPanelProps) {
  const scrollContainerRef = useRef<HTMLDivElement>(null);
  const [showScrollIndicator, setShowScrollIndicator] = useState(true);
  const [showTopSteam, setShowTopSteam] = useState(false);

  const handleScroll = useCallback(() => {
    const container = scrollContainerRef.current;
    if (!container) return;

    const { scrollTop, scrollHeight, clientHeight } = container;
    const isScrollable = scrollHeight > clientHeight;

    // Hide scroll indicator after first scroll or if not scrollable
    if (scrollTop > 10 || !isScrollable) {
      setShowScrollIndicator(false);
    }

    // Show top steam overlay when scrolled down
    if (scrollTop > 30) {
      setShowTopSteam(true);
    } else {
      setShowTopSteam(false);
    }
  }, []);

  useEffect(() => {
    const container = scrollContainerRef.current;
    if (!container) return;

    // Initial check
    handleScroll();

    // Add scroll listener
    container.addEventListener('scroll', handleScroll);

    // Check again after content loads (images, etc.)
    const timer = setTimeout(handleScroll, 500);

    return () => {
      container.removeEventListener('scroll', handleScroll);
      clearTimeout(timer);
    };
  }, [handleScroll, children]);

  return (
    <div className={styles.contentPanel}>
      {/* Top steam overlay - appears when scrolling */}
      <div
        className={`${styles.steamOverlayTop} ${showTopSteam ? styles.visible : ''}`}
        aria-hidden="true"
      />

      {/* Scrollable content */}
      <div ref={scrollContainerRef} className={styles.scrollContainer}>
        {title && (
          <h2 className={styles.sectionTitle}>{title}</h2>
        )}
        <div className={styles.bodyContent}>
          {children}
        </div>
      </div>

      {/* Bottom steam overlay - always visible for scrollable content */}
      <div
        className={styles.steamOverlayBottom}
        aria-hidden="true"
      />

      {/* Scroll indicator */}
      <div
        className={`${styles.scrollIndicator} ${showScrollIndicator ? styles.visible : ''}`}
        aria-hidden="true"
      />
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
