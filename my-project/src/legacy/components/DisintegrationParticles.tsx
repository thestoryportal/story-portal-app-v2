/**
 * DisintegrationParticles Component
 *
 * Particle effects during the disintegration animation phase.
 */

import type { Particle } from '../types';

interface DisintegrationParticlesProps {
  particles: Particle[];
  visible: boolean;
}

export function DisintegrationParticles({ particles, visible }: DisintegrationParticlesProps) {
  if (!visible) return null;

  return (
    <>
      {particles.map((p) => (
        <div
          key={p.id}
          style={{
            position: 'absolute',
            left: `calc(50% + ${p.x * 2.25}px)`,
            top: `calc(50% + ${p.y * 2.25}px)`,
            width: `${p.size * 1.5}px`,
            height: `${p.size * 1.5}px`,
            background: `radial-gradient(circle, rgba(255,215,0,1) 0%, rgba(255,140,0,0.8) 50%, transparent 100%)`,
            borderRadius: '50%',
            '--px': `${p.px * 1.5}px`,
            '--py': `${p.py * 1.5}px`,
            animation: `particleFly ${p.duration}s ease-out forwards`,
            animationDelay: `${p.delay}s`,
            pointerEvents: 'none',
          } as React.CSSProperties}
        />
      ))}
    </>
  );
}
