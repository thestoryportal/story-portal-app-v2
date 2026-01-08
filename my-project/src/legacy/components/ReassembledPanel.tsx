/**
 * ReassembledPanel Component
 *
 * The panel that appears on the right side after the disintegration animation.
 */

import type { AnimationPhase, Sparkle } from '../types';

interface ReassembledPanelProps {
  selectedPrompt: string | null;
  animPhase: AnimationPhase;
  fontSize: number;
  sparkles: Sparkle[];
  visible: boolean;
}

export function ReassembledPanel({
  selectedPrompt,
  animPhase,
  fontSize,
  sparkles,
  visible,
}: ReassembledPanelProps) {
  if (!visible || !selectedPrompt) return null;

  const isReassemble = animPhase === 'reassemble';
  const isComplete = animPhase === 'complete';

  return (
    <div
      style={{
        position: 'absolute',
        left: 'calc(100% + 45px)',
        top: '50%',
        transform: 'translateY(-50%)',
        zIndex: 25,
        pointerEvents: 'none',
      }}
    >
      {/* Transporter sparkles during reassembly */}
      {isReassemble &&
        sparkles.map((s) => (
          <div
            key={s.id}
            style={{
              position: 'absolute',
              left: `${s.x}%`,
              top: `${s.y}%`,
              width: `${s.size * 2}px`,
              height: `${s.size * 2}px`,
              background: 'radial-gradient(circle, #fff 0%, rgba(100,200,255,0.8) 50%, transparent 100%)',
              borderRadius: '50%',
              animation: 'transporterSparkle 0.3s ease-in-out infinite',
              animationDelay: `${s.delay}s`,
            }}
          />
        ))}

      {/* Scan line during reassembly */}
      {isReassemble && (
        <div
          style={{
            position: 'absolute',
            left: 0,
            right: 0,
            height: '6px',
            background: 'linear-gradient(90deg, transparent, rgba(100,200,255,0.9), transparent)',
            animation: 'scanlineMove 0.75s ease-in-out infinite',
            zIndex: 5,
          }}
        />
      )}

      {/* The reassembled panel - landscape rectangle with larger text */}
      <div
        className="prompt-text"
        style={{
          width: '440px',
          height: '198px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          boxSizing: 'border-box',
          background: 'url("/assets/images/wood-panel.webp") center/cover no-repeat',
          backgroundColor: '#3a2818',
          border: 'none',
          fontWeight: 'normal',
          fontFamily: "'Carnivalee Freakshow', serif",
          fontSize: `${fontSize * 2.42}px`,
          textAlign: 'center',
          padding: '22px 31px',
          lineHeight: '1.1',
          margin: 0,
          borderRadius: '8px',
          boxShadow: isReassemble
            ? '0 0 50px rgba(100,200,255,0.7), 0 0 100px rgba(100,200,255,0.4)'
            : '0 0 30px rgba(255,215,0,0.5), 0 0 60px rgba(255,140,0,0.3)',
          animation: isReassemble ? 'reassembleReveal 1.5s ease-out forwards' : 'none',
          opacity: isComplete ? 1 : undefined,
        }}
      >
        <span className="carved-text">{selectedPrompt}</span>
      </div>
    </div>
  );
}
