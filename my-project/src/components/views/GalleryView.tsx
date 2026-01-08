/**
 * GalleryView Component
 * Gallery view that displays all saved stories as accordion list
 * Rendered as overlay modal by LegacyApp
 */

import { useState, useCallback } from 'react';
import { useLocalStorage } from '../../hooks/useLocalStorage';
import { StoryAccordion } from '../gallery/StoryAccordion';
import styles from '../gallery/gallery.module.css';

interface GalleryViewProps {
  onBack: () => void;
}

export function GalleryView({ onBack }: GalleryViewProps): JSX.Element {
  const [openAccordionId, setOpenAccordionId] = useState<string | null>(null);
  const { data: stories, loading, error, deleteData, refetch } = useLocalStorage();

  // Auto-refetch after delete
  const handleDelete = useCallback(
    async (storyId: string) => {
      try {
        await deleteData(storyId);
        // Refetch stories
        await refetch();
      } catch (err) {
        console.error('Failed to delete story:', err);
      }
    },
    [deleteData, refetch],
  );

  const handleAccordionToggle = useCallback((storyId: string) => {
    // Only one accordion can be open at a time
    setOpenAccordionId((prev) => (prev === storyId ? null : storyId));
  }, []);

  // Show loading state
  if (loading) {
    return (
      <div className={styles.loadingContainer}>
        <div className={styles.spinner} aria-label="Loading stories..." />
      </div>
    );
  }

  // Show error state
  if (error) {
    return (
      <div className={styles.errorContainer}>
        <h2 className={styles.errorTitle}>Error Loading Stories</h2>
        <p className={styles.errorMessage}>{error.message}</p>
        <button
          onClick={onBack}
          style={{
            marginTop: 'var(--sp-spacing-lg)',
            padding: 'var(--sp-spacing-md) var(--sp-spacing-lg)',
            border: '2px solid #aa4444',
            borderRadius: '8px',
            background: 'transparent',
            color: '#ff9999',
            cursor: 'pointer',
            fontWeight: 'bold',
          }}
        >
          Close Gallery
        </button>
      </div>
    );
  }

  // Show empty state
  if (!stories || stories.length === 0) {
    return (
      <div className={styles.emptyState}>
        <div className={styles.emptyIcon}>🎤</div>
        <h2 className={styles.emptyTitle}>No Stories Yet</h2>
        <p className={styles.emptyMessage}>
          Record your first story by spinning the wheel and clicking the Record button!
        </p>
        <button
          onClick={onBack}
          style={{
            marginTop: 'var(--sp-spacing-lg)',
            padding: 'var(--sp-spacing-md) var(--sp-spacing-lg)',
            border: '2px solid var(--sp-color-border-bronze)',
            borderRadius: '8px',
            background: 'linear-gradient(180deg, #6a4a35, #3d2820)',
            color: 'var(--sp-color-text-button)',
            cursor: 'pointer',
            fontWeight: 'bold',
            fontSize: 'var(--sp-font-size-md, 18px)',
            textTransform: 'uppercase',
          }}
        >
          Close Gallery
        </button>
      </div>
    );
  }

  // Show gallery with accordion list
  return (
    <div className={styles.galleryContainer}>
      <div className={styles.galleryHeader}>
        <button
          onClick={onBack}
          className={styles.closeButton}
          aria-label="Close gallery"
          title="Close gallery"
        >
          ✕
        </button>
        <h2 className={styles.galleryTitle}>My Stories</h2>
        <div style={{ width: '44px' }} />
      </div>

      <div className={styles.storyList}>
        {stories.map((story) => (
          <StoryAccordion
            key={story.id}
            story={story}
            isOpen={openAccordionId === story.id}
            onToggle={() => handleAccordionToggle(story.id)}
            onDelete={handleDelete}
          />
        ))}
      </div>
    </div>
  );
}
