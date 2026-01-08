/**
 * SpinButton Component
 *
 * Circular spin button that triggers the wheel spin.
 */

import { useState } from 'react';

interface SpinButtonProps {
  onSpin: () => void;
}

export function SpinButton({ onSpin }: SpinButtonProps) {
  const [pressed, setPressed] = useState(false);

  return (
    <div
      className="spin-wheel-button"
      onClick={onSpin}
      onMouseDown={() => setPressed(true)}
      onMouseUp={() => setPressed(false)}
      onMouseLeave={() => setPressed(false)}
      onTouchStart={() => setPressed(true)}
      onTouchEnd={() => setPressed(false)}
      style={{
        position: 'absolute',
        left: '-30px',
        top: '-170px',
        width: '90px',
        height: '90px',
        cursor: 'pointer',
        userSelect: 'none',
        WebkitTapHighlightColor: 'transparent',
        filter: 'drop-shadow(0 4px 6px rgba(0,0,0,0.6)) drop-shadow(0 8px 15px rgba(0,0,0,0.4))',
        borderRadius: '50%',
      }}
    >
      <img
        src={
          pressed
            ? '/assets/images/story-portal-button-spin-click.webp'
            : '/assets/images/story-portal-button-spin-static.webp'
        }
        alt="Spin"
        draggable="false"
        style={{
          width: '100%',
          height: '100%',
          objectFit: 'contain',
          pointerEvents: 'none',
          borderRadius: '50%',
        }}
      />
      <div
        style={{
          position: 'absolute',
          top: '50%',
          left: '50%',
          transform: 'translate(-50%, -50%)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          pointerEvents: 'none',
        }}
      >
        <span
          className={`engraved-material-icon${pressed ? ' pressed' : ''}`}
          style={{
            fontSize: '38px',
            fontVariationSettings: "'FILL' 1, 'wght' 500, 'GRAD' 0, 'opsz' 24",
            transform: 'scaleX(-1)',
          }}
        >
          flip_camera_android
        </span>
      </div>
    </div>
  );
}
