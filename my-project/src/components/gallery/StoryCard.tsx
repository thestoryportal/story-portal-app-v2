/**
 * StoryCard Component
 * Displays a single story in the gallery grid
 */

import { useCallback, useMemo } from 'react';
import type { StoryRecord } from '../../types';
import { formatDuration, formatRelativeTime } from '../../utils/formatting';
import styles from './gallery.module.css';

interface StoryCardProps {
  story: StoryRecord;
  onPlay: (story: StoryRecord) => void;
  onDelete: (storyId: string) => void;
}

export function StoryCard({ story, onPlay, onDelete }: StoryCardProps): JSX.Element {
  const handlePlay = useCallback(() => {
    onPlay(story);
  }, [story, onPlay]);

  const handleDelete = useCallback(() => {
    if (
      window.confirm(
        'Are you sure you want to delete this story? This action cannot be undone.'
      )
    ) {
      onDelete(story.id);
    }
  }, [story.id, onDelete]);

  // Create photo thumbnail URL
  const photoThumbnailUrl = useMemo(() => {
    if (story.photo) {
      return URL.createObjectURL(story.photo.blob);
    }
    return null;
  }, [story.photo]);

  return (
    <div className={styles.storyCard}>
      {/* Thumbnail - photo or microphone icon */}
      <div className={styles.cardThumbnail}>
        {photoThumbnailUrl ? (
          <img
            src={photoThumbnailUrl}
            alt="Story photo thumbnail"
            className={styles.thumbnailImage}
          />
        ) : (
          <span>🎤</span>
        )}
      </div>

      {/* Prompt text */}
      <h3 className={styles.cardPrompt}>{story.prompt_text}</h3>

      {/* Metadata - duration and date */}
      <div className={styles.cardMetadata}>
        <div className={styles.metadataItem}>
          <span className={styles.metadataLabel}>Duration:</span>
          <span>{formatDuration(story.audio_duration_seconds)}</span>
        </div>
        <div className={styles.metadataItem}>
          <span className={styles.metadataLabel}>Created:</span>
          <span>{formatRelativeTime(story.created_at)}</span>
        </div>
      </div>

      {/* Action buttons */}
      <div className={styles.cardActions}>
        <button className={`${styles.cardButton} ${styles.playButton}`} onClick={handlePlay}>
          ▶ Play
        </button>
        <button className={`${styles.cardButton} ${styles.deleteButton}`} onClick={handleDelete}>
          🗑 Delete
        </button>
      </div>
    </div>
  );
}
