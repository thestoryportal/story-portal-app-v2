/**
 * StoryAccordion Component
 * Displays a single story as an accordion tab
 * Shows play button, thumbnail, prompt, duration, and date in collapsed state
 * Shows full-size photo when expanded (only if photo exists)
 */

import { useCallback, useEffect, useMemo, useState } from 'react';
import type { StoryRecord } from '../../types';
import { formatDuration } from '../../utils/formatting';
import styles from './gallery.module.css';

interface StoryAccordionProps {
  story: StoryRecord;
  isOpen: boolean;
  onToggle: () => void;
  onDelete: (storyId: string) => void;
}

export function StoryAccordion({
  story,
  isOpen,
  onToggle,
  onDelete,
}: StoryAccordionProps): JSX.Element {
  const [isPlaying, setIsPlaying] = useState(false);

  // Create object URL for photo
  const photoUrl = useMemo(() => {
    if (story.photo) {
      return URL.createObjectURL(story.photo.blob);
    }
    return null;
  }, [story.photo]);

  // Cleanup photo URL on unmount
  useEffect(() => {
    return () => {
      if (photoUrl) {
        URL.revokeObjectURL(photoUrl);
      }
    };
  }, [photoUrl]);

  const handleHeaderClick = useCallback(() => {
    // Only allow opening if photo exists
    if (photoUrl) {
      onToggle();
    }
  }, [onToggle, photoUrl]);

  const handlePlayClick = useCallback((e: React.MouseEvent) => {
    e.stopPropagation();
    setIsPlaying(!isPlaying);
  }, [isPlaying]);

  const handleDeleteClick = useCallback(
    (e: React.MouseEvent) => {
      // Prevent accordion toggle when clicking delete
      e.stopPropagation();

      if (
        window.confirm(
          'Are you sure you want to delete this story? This action cannot be undone.'
        )
      ) {
        onDelete(story.id);
      }
    },
    [story.id, onDelete],
  );

  // Format the recording date
  const recordingDate = new Date(story.created_at).toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  });

  return (
    <div className={styles.accordion}>
      <button
        className={`${styles.accordionHeader} ${photoUrl && isOpen ? styles.open : ''}`}
        onClick={handleHeaderClick}
        aria-expanded={photoUrl ? isOpen : false}
        aria-controls={`accordion-content-${story.id}`}
        disabled={!photoUrl}
      >
        {/* Arrow indicator */}
        <span className={styles.accordionArrow}>
          {photoUrl ? '▶' : ''}
        </span>

        {/* Play button */}
        <button
          className={styles.playButtonCompact}
          onClick={handlePlayClick}
          aria-label={isPlaying ? 'Pause audio' : 'Play audio'}
          title={isPlaying ? 'Pause audio' : 'Play audio'}
        >
          {isPlaying ? '⏸' : '▶'}
        </button>

        {/* Thumbnail */}
        <div className={styles.thumbnailSection}>
          {photoUrl ? (
            <img
              src={photoUrl}
              alt="Story thumbnail"
              className={styles.thumbnailCompact}
            />
          ) : (
            <div className={styles.thumbnailCompact}>📖</div>
          )}
        </div>

        {/* Center section: Prompt + Duration + Date */}
        <div className={styles.accordionCenter}>
          <h3 className={styles.promptCompact}>{story.prompt_text}</h3>

          <div className={styles.metadataLine}>
            <span className={styles.durationValue}>{formatDuration(story.audio_duration_seconds)}</span>
            <span className={styles.metadataSeparator}>•</span>
            <span className={styles.recordingDateValue}>{recordingDate}</span>
          </div>
        </div>

        {/* Delete button */}
        <button
          className={styles.deleteButtonCompact}
          onClick={handleDeleteClick}
          aria-label="Delete this story"
          title="Delete this story"
        >
          🗑
        </button>
      </button>

      {/* Expanded content - full-size photo */}
      {photoUrl && (
        <div
          id={`accordion-content-${story.id}`}
          className={`${styles.accordionContent} ${isOpen ? styles.open : ''}`}
        >
          <div className={styles.accordionContentInner}>
            <img
              src={photoUrl}
              alt="Story photo"
              className={styles.photoExpanded}
            />
          </div>
        </div>
      )}
    </div>
  );
}
