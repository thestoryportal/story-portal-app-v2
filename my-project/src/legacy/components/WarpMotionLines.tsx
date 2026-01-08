/**
 * WarpMotionLines Component
 *
 * Motion lines displayed during the warp animation phase.
 */

import { useMemo } from 'react';

interface WarpMotionLinesProps {
  visible: boolean;
}

// Pre-calculated opacity values for 12 lines (deterministic pattern)
const LINE_OPACITIES = [0.55, 0.72, 0.48, 0.65, 0.38, 0.78, 0.52, 0.68, 0.42, 0.75, 0.58, 0.45];

export function WarpMotionLines({ visible }: WarpMotionLinesProps) {
  const lines = useMemo(
    () =>
      Array.from({ length: 12 }, (_, i) => ({
        index: i,
        opacity: LINE_OPACITIES[i],
        rotation: i * 30,
        delay: i * 0.03,
      })),
    []
  );

  if (!visible) return null;

  return (
    <div
      style={{
        position: 'absolute',
        left: '50%',
        top: '50%',
        transform: 'translate(-50%, -50%)',
        zIndex: 39,
        pointerEvents: 'none',
        width: '300px',
        height: '200px',
      }}
    >
      {lines.map((line) => (
        <div
          key={line.index}
          style={{
            position: 'absolute',
            left: '50%',
            top: '50%',
            width: '3px',
            height: '40px',
            background: `linear-gradient(to bottom, transparent, rgba(255,215,0,${line.opacity}), rgba(255,140,0,0.8), transparent)`,
            transform: `translate(-50%, -50%) rotate(${line.rotation}deg) translateY(-60px)`,
            animation: `warpStreak 0.6s ease-out forwards`,
            animationDelay: `${line.delay}s`,
          }}
        />
      ))}
    </div>
  );
}
