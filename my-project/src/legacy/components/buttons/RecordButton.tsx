/**
 * RecordButton Component
 *
 * Button to start recording with disabled tooltip when no prompt is selected.
 */

import { useState } from 'react';

interface RecordButtonProps {
  hasSelectedPrompt: boolean;
  onRecord: () => void;
  onDisabledClick: () => void;
  showTooltip: boolean;
}

export function RecordButton({ hasSelectedPrompt, onRecord, onDisabledClick, showTooltip }: RecordButtonProps) {
  const [pressed, setPressed] = useState(false);

  const handleClick = () => {
    if (hasSelectedPrompt) {
      onRecord();
    } else {
      onDisabledClick();
    }
  };

  const handleMouseDown = () => {
    if (hasSelectedPrompt) {
      setPressed(true);
    }
  };

  return (
    <div
      className="image-button record-btn"
      onClick={handleClick}
      onMouseDown={handleMouseDown}
      onMouseUp={() => setPressed(false)}
      onMouseLeave={() => setPressed(false)}
      onTouchStart={handleMouseDown}
      onTouchEnd={() => setPressed(false)}
      style={{
        cursor: 'pointer',
        position: 'relative',
        userSelect: 'none',
        WebkitTapHighlightColor: 'transparent',
      }}
    >
      {showTooltip && !hasSelectedPrompt && (
        <div className="record-tooltip">Spin the wheel to receive your story prompt to record!</div>
      )}
      <img
        src={
          pressed && hasSelectedPrompt
            ? '/assets/images/story-portal-button-click.webp'
            : '/assets/images/story-portal-button-primary.webp'
        }
        alt="Record"
        draggable="false"
        style={{
          width: '100%',
          height: '100%',
          objectFit: 'contain',
          pointerEvents: 'none',
        }}
      />
      <div className="button-content">
        <span className={`engraved-material-icon${hasSelectedPrompt && pressed ? ' pressed' : ''}`}>
          {hasSelectedPrompt ? 'adaptive_audio_mic' : 'adaptive_audio_mic_off'}
        </span>
        <span
          className={`engraved-button-text${hasSelectedPrompt ? (pressed ? ' pressed' : '') : ''}`}
          style={{ fontSize: 'clamp(12px, 2.8vw, 22px)' }}
        >
          Record
        </span>
      </div>
    </div>
  );
}
