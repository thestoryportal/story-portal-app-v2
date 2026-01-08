/**
 * SteamWisps Component
 *
 * Renders persistent steam effects around the portal.
 */

import type { SteamWisp } from '../types';

interface SteamWispsProps {
  wisps: SteamWisp[];
}

export function SteamWisps({ wisps }: SteamWispsProps) {
  return (
    <div
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        width: '100%',
        height: '100%',
        pointerEvents: 'none',
        zIndex: 10,
      }}
    >
      {wisps.map((wisp) => (
        <div
          key={wisp.id}
          style={{
            position: 'absolute',
            left: wisp.left || 'auto',
            right: wisp.right || 'auto',
            top: wisp.top || 'auto',
            bottom: wisp.bottom || 'auto',
            marginLeft: wisp.offsetX + 'px',
            marginTop: wisp.offsetY + 'px',
            width: wisp.size * 1.2 + 'px',
            height: wisp.size + 'px',
            borderRadius: '50%',
            background:
              'radial-gradient(ellipse at center, rgba(155,148,140,0.6) 0%, rgba(140,133,125,0.35) 40%, transparent 75%)',
            filter: 'blur(8px)',
            animation: `${wisp.animation} ${wisp.duration}ms ease-out forwards`,
          }}
        />
      ))}
    </div>
  );
}
