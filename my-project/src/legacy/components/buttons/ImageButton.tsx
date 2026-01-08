/**
 * ImageButton Component
 *
 * Reusable button with wood panel background (primary/secondary variants).
 */

import { useState, type ReactNode } from 'react';

interface ImageButtonProps {
  onClick?: () => void;
  onMouseDown?: () => void;
  disabled?: boolean;
  variant?: 'primary' | 'secondary';
  className?: string;
  children: ReactNode;
}

export function ImageButton({
  onClick,
  onMouseDown,
  disabled = false,
  variant = 'primary',
  className = '',
  children,
}: ImageButtonProps) {
  const [pressed, setPressed] = useState(false);

  const handleMouseDown = () => {
    if (!disabled) {
      setPressed(true);
      onMouseDown?.();
    }
  };

  const imageSrc =
    pressed && !disabled
      ? '/assets/images/story-portal-button-click.webp'
      : variant === 'primary'
        ? '/assets/images/story-portal-button-primary.webp'
        : '/assets/images/story-portal-button-secondary.webp';

  return (
    <div
      className={`image-button ${className}`}
      onClick={onClick}
      onMouseDown={handleMouseDown}
      onMouseUp={() => setPressed(false)}
      onMouseLeave={() => setPressed(false)}
      onTouchStart={handleMouseDown}
      onTouchEnd={() => setPressed(false)}
      style={{
        cursor: disabled ? 'default' : 'pointer',
        position: 'relative',
        userSelect: 'none',
        WebkitTapHighlightColor: 'transparent',
      }}
    >
      <img
        src={imageSrc}
        alt=""
        draggable="false"
        style={{
          width: '100%',
          height: '100%',
          objectFit: 'contain',
          pointerEvents: 'none',
        }}
      />
      <div className="button-content">{children}</div>
    </div>
  );
}
