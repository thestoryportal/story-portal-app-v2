/**
 * NewTopicsButton Component
 *
 * Button to load new topics into the wheel.
 */

import { useState } from 'react';

interface NewTopicsButtonProps {
  onLoadNewTopics: () => void;
}

export function NewTopicsButton({ onLoadNewTopics }: NewTopicsButtonProps) {
  const [pressed, setPressed] = useState(false);

  const handleMouseDown = () => {
    setPressed(true);
    onLoadNewTopics();
  };

  return (
    <div
      className="image-button new-topics-btn"
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
      <img
        src={
          pressed
            ? '/assets/images/story-portal-button-click.webp'
            : '/assets/images/story-portal-button-primary.webp'
        }
        alt="New Topics"
        draggable="false"
        style={{
          width: '100%',
          height: '100%',
          objectFit: 'contain',
          pointerEvents: 'none',
        }}
      />
      <div className="button-content">
        <svg
          className={`engraved-icon${pressed ? ' pressed' : ''}`}
          viewBox="0 0 24 24"
          style={{ width: 'clamp(18px, 4vw, 32px)', height: 'clamp(18px, 4vw, 32px)' }}
        >
          <defs>
            <linearGradient id="icon-gradient" x1="0%" y1="0%" x2="0%" y2="100%">
              <stop offset="0%" style={{ stopColor: '#f5e6d3', stopOpacity: 1 }} />
              <stop offset="35%" style={{ stopColor: '#d4af37', stopOpacity: 1 }} />
              <stop offset="65%" style={{ stopColor: '#c4942e', stopOpacity: 1 }} />
              <stop offset="100%" style={{ stopColor: '#8b6f47', stopOpacity: 1 }} />
            </linearGradient>
          </defs>
          <path d="M14 3H21V10L18.5 7.5L14.5 11.5L12.5 9.5L16.5 5.5L14 3ZM14 21H21V14L18.5 16.5L5.5 3.5L3.5 5.5L16.5 18.5L14 21ZM3.5 18.5L5.5 20.5L9.5 16.5L7.5 14.5L3.5 18.5Z" fill="url(#icon-gradient)" />
        </svg>
        <span
          className={`engraved-button-text${pressed ? ' pressed' : ''}`}
          style={{ fontSize: 'clamp(12px, 2.8vw, 22px)' }}
        >
          New Topics
        </span>
      </div>
    </div>
  );
}
