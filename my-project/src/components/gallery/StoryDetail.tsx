/**
 * StoryDetail Component
 * Full-screen view of a single story with playback
 */

import { useCallback, useEffect, useMemo, useState } from 'react';
import type { StoryRecord } from '../../types';
import { formatDuration, formatRelativeTime } from '../../utils/formatting';
import { AudioPlayer } from './AudioPlayer';
import styles from './gallery.module.css';

interface StoryDetailProps {
  story: StoryRecord;
  onBack: () => void;
  onDelete: (storyId: string) => void;
}

export function StoryDetail({ story, onBack, onDelete }: StoryDetailProps): JSX.Element {
  const [deleteConfirmed, setDeleteConfirmed] = useState(false);

  // Create object URLs for photo
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

  const handleDelete = useCallback(() => {
    if (
      window.confirm(
        'Are you sure you want to delete this story? This action cannot be undone.'
      )
    ) {
      setDeleteConfirmed(true);
      onDelete(story.id);
    }
  }, [story.id, onDelete]);

  // Format the recording date
  const recordingDate = new Date(story.created_at).toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
  });

  return (
    <div className={styles.detailContainer}>
      {/* Header with back button */}
      <div className={styles.detailHeader}>
        <button className={styles.backButton} onClick={onBack} aria-label="Back to gallery">
          ← Back to Gallery
        </button>
      </div>

      {/* Title */}
      <h2 className={styles.detailTitle}>Your Story</h2>

      {/* Prompt section */}
      <div className={styles.promptSection}>
        <label className={styles.promptLabel}>Prompt</label>
        <p className={styles.promptText}>{story.prompt_text}</p>
      </div>

      {/* Metadata section */}
      <div className={styles.metadataSection}>
        <div className={styles.metadataLine}>
          <span className={styles.metadataLineLabel}>Recorded:</span>
          <span>{recordingDate}</span>
        </div>
        <div className={styles.metadataLine}>
          <span className={styles.metadataLineLabel}>Duration:</span>
          <span>{formatDuration(story.audio_duration_seconds)}</span>
        </div>
        {story.consent.email_confirmed && (
          <div className={styles.metadataLine}>
            <span className={styles.metadataLineLabel}>Email:</span>
            <span>Consent given</span>
          </div>
        )}
      </div>

      {/* Photo section (if exists) */}
      {story.photo && photoUrl && (
        <div className={styles.photoSection}>
          <img
            src={photoUrl}
            alt="Story photo"
            className={styles.photoImage}
            loading="lazy"
          />
        </div>
      )}

      {/* Audio player */}
      <AudioPlayer audioBlob={story.audio_blob} duration={story.audio_duration_seconds} />

      {/* Action buttons */}
      <div className={styles.detailActions}>
        <button
          className={`${styles.detailButton} ${styles.detailButtonPrimary}`}
          onClick={onBack}
          disabled={deleteConfirmed}
        >
          ← Back to Gallery
        </button>
        <button
          className={`${styles.detailButton} ${styles.detailButtonDanger}`}
          onClick={handleDelete}
          disabled={deleteConfirmed}
        >
          🗑 Delete Story
        </button>
      </div>
    </div>
  );
}
