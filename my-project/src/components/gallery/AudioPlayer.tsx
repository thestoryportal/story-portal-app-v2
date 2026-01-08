/**
 * AudioPlayer Component
 * Simple HTML5 audio player for story playback
 */

import { useEffect, useState } from 'react';
import styles from './gallery.module.css';

interface AudioPlayerProps {
  audioBlob: Blob;
  duration?: number;
}

export function AudioPlayer({ audioBlob }: AudioPlayerProps): JSX.Element {
  const [audioUrl, setAudioUrl] = useState<string>('');

  useEffect(() => {
    const url = URL.createObjectURL(audioBlob);
    setAudioUrl(url);

    return () => {
      URL.revokeObjectURL(url);
    };
  }, [audioBlob]);

  return (
    <div className={styles.audioPlayerContainer}>
      <label className={styles.audioPlayerLabel}>Recording Playback</label>
      <audio
        className={styles.audioElement}
        controls
        src={audioUrl}
        preload="metadata"
        aria-label="Story recording playback"
      />
    </div>
  );
}
