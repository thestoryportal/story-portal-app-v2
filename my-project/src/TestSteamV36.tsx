/**
 * Test page for Steam Animation v36 (AAA Enhanced)
 * Navigate to ?test=v36 to see the enhanced version
 */

import SteamAnimationV36 from './components/steam-modal/enhanced/steam-animation-v36';

export function TestSteamV36() {
  return (
    <div style={{
      position: 'fixed',
      inset: 0,
      overflow: 'hidden',
      background: '#1c1814'
    }}>
      <SteamAnimationV36 />

      {/* Info overlay */}
      <div style={{
        position: 'fixed',
        top: '20px',
        left: '20px',
        background: 'rgba(0,0,0,0.8)',
        color: '#f5deb3',
        padding: '15px',
        borderRadius: '8px',
        fontSize: '14px',
        zIndex: 10000,
        maxWidth: '300px'
      }}>
        <h3 style={{ margin: '0 0 10px 0', color: '#c9a87a' }}>v36 - AAA Enhanced</h3>
        <ul style={{ margin: 0, paddingLeft: '20px', fontSize: '12px', lineHeight: '1.6' }}>
          <li>Texture-based particles</li>
          <li>Perlin noise flow</li>
          <li>Particle rotation</li>
          <li>Scale evolution</li>
          <li>Depth sorting + blur</li>
          <li>Atmospheric glow</li>
        </ul>
      </div>
    </div>
  );
}
