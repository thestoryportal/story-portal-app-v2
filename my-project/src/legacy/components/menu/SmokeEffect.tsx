/**
 * SmokeEffect Component
 *
 * Smoke poof effect when menu opens/closes.
 */

import { Fragment } from 'react';

interface SmokeEffectProps {
  visible: boolean;
  animKey: number;
}

export function SmokeEffect({ visible, animKey }: SmokeEffectProps) {
  if (!visible) return null;

  return (
    <Fragment key={animKey}>
      {/* Main smoke cloud - larger for wider coverage */}
      <div
        style={{
          position: 'fixed',
          left: '50%',
          top: '38%',
          width: '350px',
          height: '350px',
          borderRadius: '50%',
          background:
            'radial-gradient(ellipse at center, rgba(140,120,100,0.95) 0%, rgba(120,100,80,0.8) 25%, rgba(100,80,60,0.5) 50%, rgba(80,60,40,0.2) 75%, transparent 90%)',
          animation: 'smokePoof 1.0s ease-out forwards',
          pointerEvents: 'none',
          zIndex: 1005,
          filter: 'blur(12px)',
        }}
      />

      {/* Smoke wisp 1 - drifts up-left */}
      <div
        style={{
          position: 'fixed',
          left: '50%',
          top: '38%',
          width: '120px',
          height: '90px',
          borderRadius: '50%',
          background:
            'radial-gradient(ellipse at center, rgba(130,110,90,0.9) 0%, rgba(110,90,70,0.6) 50%, transparent 85%)',
          animation: 'smokeWisp1 1.4s ease-out forwards',
          animationDelay: '0.05s',
          pointerEvents: 'none',
          zIndex: 1006,
          filter: 'blur(8px)',
        }}
      />

      {/* Smoke wisp 2 - drifts up-right */}
      <div
        style={{
          position: 'fixed',
          left: '50%',
          top: '38%',
          width: '100px',
          height: '75px',
          borderRadius: '50%',
          background:
            'radial-gradient(ellipse at center, rgba(120,100,80,0.9) 0%, rgba(100,80,60,0.6) 50%, transparent 85%)',
          animation: 'smokeWisp2 1.3s ease-out forwards',
          animationDelay: '0.1s',
          pointerEvents: 'none',
          zIndex: 1006,
          filter: 'blur(7px)',
        }}
      />

      {/* Smoke wisp 3 - drifts up-center */}
      <div
        style={{
          position: 'fixed',
          left: '50%',
          top: '38%',
          width: '140px',
          height: '100px',
          borderRadius: '50%',
          background:
            'radial-gradient(ellipse at center, rgba(150,130,110,0.85) 0%, rgba(130,110,90,0.5) 50%, transparent 85%)',
          animation: 'smokeWisp3 1.5s ease-out forwards',
          animationDelay: '0.02s',
          pointerEvents: 'none',
          zIndex: 1006,
          filter: 'blur(10px)',
        }}
      />

      {/* Inner bright flash */}
      <div
        style={{
          position: 'fixed',
          left: '50%',
          top: '38%',
          width: '180px',
          height: '180px',
          borderRadius: '50%',
          background:
            'radial-gradient(ellipse at center, rgba(255,240,200,0.7) 0%, rgba(220,200,160,0.4) 40%, transparent 70%)',
          animation: 'smokePoof 0.5s ease-out forwards',
          pointerEvents: 'none',
          zIndex: 1004,
          filter: 'blur(6px)',
        }}
      />

      {/* Lingering smoke - drifts left */}
      <div
        style={{
          position: 'fixed',
          left: '50%',
          top: '38%',
          width: '200px',
          height: '150px',
          borderRadius: '50%',
          background:
            'radial-gradient(ellipse at center, rgba(130,115,95,0.7) 0%, rgba(110,95,75,0.4) 50%, transparent 85%)',
          animation: 'smokeLingerLeft 3.0s ease-out forwards',
          animationDelay: '0.2s',
          pointerEvents: 'none',
          zIndex: 1003,
          filter: 'blur(15px)',
        }}
      />

      {/* Lingering smoke - drifts right */}
      <div
        style={{
          position: 'fixed',
          left: '50%',
          top: '38%',
          width: '180px',
          height: '140px',
          borderRadius: '50%',
          background:
            'radial-gradient(ellipse at center, rgba(125,110,90,0.7) 0%, rgba(105,90,70,0.4) 50%, transparent 85%)',
          animation: 'smokeLingerRight 3.2s ease-out forwards',
          animationDelay: '0.15s',
          pointerEvents: 'none',
          zIndex: 1003,
          filter: 'blur(14px)',
        }}
      />

      {/* Lingering smoke - drifts up */}
      <div
        style={{
          position: 'fixed',
          left: '50%',
          top: '38%',
          width: '250px',
          height: '180px',
          borderRadius: '50%',
          background:
            'radial-gradient(ellipse at center, rgba(140,120,100,0.65) 0%, rgba(120,100,80,0.35) 50%, transparent 85%)',
          animation: 'smokeLingerUp 3.5s ease-out forwards',
          animationDelay: '0.1s',
          pointerEvents: 'none',
          zIndex: 1003,
          filter: 'blur(18px)',
        }}
      />
    </Fragment>
  );
}
