/**
 * Test page for Steam Animation v37
 * Navigate to ?test=v37 to see this version
 *
 * v37 = v35 baseline with ADDITIVE enhancements:
 * - Preserved: 7-stop gradients, alphaMultiplier, getWaft(), movement multipliers
 * - Added: Perlin noise overlay, texture overlay, rotation, scale, depth
 */

import SteamAnimationV37 from './components/steam-modal/enhanced/steam-animation-v37';

export function TestSteamV37() {
  return (
    <div style={{
      position: 'fixed',
      inset: 0,
      overflow: 'hidden',
      background: '#1c1814'
    }}>
      <SteamAnimationV37 />

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
        maxWidth: '320px'
      }}>
        <h3 style={{ margin: '0 0 10px 0', color: '#c9a87a' }}>v37 - Enhanced v35</h3>
        <p style={{ margin: '0 0 8px 0', fontSize: '11px', color: '#9a8a6a' }}>
          Built on v35 baseline with additive enhancements
        </p>
        <div style={{ fontSize: '11px', marginBottom: '8px', color: '#7a9a6a' }}>
          <strong>Preserved from v35:</strong>
        </div>
        <ul style={{ margin: '0 0 8px 0', paddingLeft: '18px', fontSize: '11px', lineHeight: '1.5', color: '#b5a58a' }}>
          <li>7-stop gradient rendering</li>
          <li>alphaMultiplier layer system</li>
          <li>getWaft() deterministic movement</li>
          <li>Full movement multipliers</li>
        </ul>
        <div style={{ fontSize: '11px', marginBottom: '8px', color: '#6a8aba' }}>
          <strong>Added in v37:</strong>
        </div>
        <ul style={{ margin: 0, paddingLeft: '18px', fontSize: '11px', lineHeight: '1.5', color: '#b5a58a' }}>
          <li>Built-in Perlin noise (no deps)</li>
          <li>Noise flow ON TOP of waft</li>
          <li>Texture overlay (optional)</li>
          <li>Particle rotation/scale/depth</li>
          <li>Debug border removed</li>
        </ul>
      </div>

      {/* Compare links */}
      <div style={{
        position: 'fixed',
        bottom: '20px',
        left: '20px',
        display: 'flex',
        gap: '10px',
        zIndex: 10000
      }}>
        <a
          href="?test=compare37"
          style={{
            background: 'linear-gradient(145deg, #6a9a5a, #4a7a3a)',
            color: '#fff',
            padding: '10px 16px',
            borderRadius: '6px',
            fontSize: '13px',
            fontWeight: 'bold',
            textDecoration: 'none',
            border: '2px solid #8aba7a'
          }}
        >
          Compare v35 vs v37
        </a>
        <span
          style={{
            background: 'rgba(100,80,60,0.9)',
            color: '#f5deb3',
            padding: '10px 16px',
            borderRadius: '6px',
            fontSize: '13px',
            fontWeight: 'bold'
          }}
        >
          v37 (current)
        </span>
      </div>
    </div>
  );
}
