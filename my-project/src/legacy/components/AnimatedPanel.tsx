/**
 * AnimatedPanel Component
 *
 * The main animated panel that appears during warp, hold, and disintegrate phases.
 */

import type { AnimationPhase, Particle } from '../types';
import { DisintegrationParticles } from './DisintegrationParticles';

interface AnimatedPanelProps {
  selectedPrompt: string | null;
  animPhase: AnimationPhase;
  panelHeight: number;
  fontSize: number;
  particles: Particle[];
}

export function AnimatedPanel({
  selectedPrompt,
  animPhase,
  panelHeight,
  fontSize,
  particles,
}: AnimatedPanelProps) {
  if (!selectedPrompt || !animPhase) return null;
  if (!['warp', 'hold', 'disintegrate'].includes(animPhase)) return null;

  const isDisintegrate = animPhase === 'disintegrate';
  const isHoldOrDisintegrate = animPhase === 'hold' || animPhase === 'disintegrate';

  return (
    <div
      style={{
        position: 'absolute',
        left: '50%',
        top: '50%',
        transform: 'translate(-50%, -50%)',
        zIndex: 40,
        perspective: '1000px',
        pointerEvents: 'none',
      }}
    >
      <div
        className="prompt-text"
        style={{
          width: '250px',
          height: `${panelHeight}px`,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          boxSizing: 'border-box',
          background: 'url("/assets/images/wood-panel.webp") center/cover no-repeat',
          backgroundColor: '#3a2818',
          border: 'none',
          fontWeight: 'normal',
          fontFamily: "'Carnivalee Freakshow', serif",
          fontSize: `${fontSize}px`,
          textAlign: 'center',
          padding: '0 12px',
          lineHeight: '1',
          margin: 0,
          boxShadow: isDisintegrate
            ? '0 0 50px rgba(255,215,0,0.9), 0 0 100px rgba(255,140,0,0.6)'
            : '0 0 30px rgba(255,215,0,0.6), 0 0 60px rgba(255,140,0,0.4)',
          transformStyle: 'preserve-3d',
          animation:
            animPhase === 'warp'
              ? 'warpSpeed 0.6s cubic-bezier(0.25, 0.46, 0.45, 0.94) forwards'
              : animPhase === 'disintegrate'
                ? 'disintegrateGlow 3s ease-out forwards'
                : 'none',
          transform: isHoldOrDisintegrate ? 'scale(2.25)' : undefined,
        }}
      >
        <span className="carved-text">{selectedPrompt}</span>
      </div>

      <DisintegrationParticles particles={particles} visible={isDisintegrate} />
    </div>
  );
}
