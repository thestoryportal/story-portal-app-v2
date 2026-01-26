/**
 * Side-by-side comparison: v35 (Baseline) vs v37 (Enhanced)
 * Navigate to ?test=compare37 to see this comparison
 */

import SteamAnimationV35 from './components/steam-modal/enhanced/steam-animation-v35';
import SteamAnimationV37 from './components/steam-modal/enhanced/steam-animation-v37';

export function TestSteamV35vsV37() {
  return (
    <div style={{
      position: 'fixed',
      inset: 0,
      display: 'flex',
      overflow: 'hidden',
      background: '#000'
    }}>
      {/* v35 - Left Side */}
      <div style={{
        position: 'relative',
        width: '50%',
        height: '100%',
        borderRight: '2px solid #c9a87a',
        zIndex: 10003
      }}>
        <SteamAnimationV35 />

        {/* v35 Label */}
        <div style={{
          position: 'absolute',
          top: '20px',
          right: '20px',
          background: 'rgba(0,0,0,0.85)',
          color: '#8a6540',
          padding: '10px 20px',
          borderRadius: '8px',
          border: '2px solid #8a6540',
          fontWeight: 'bold',
          fontSize: '16px',
          zIndex: 10000
        }}>
          v35 - Baseline
        </div>

        {/* v35 Features */}
        <div style={{
          position: 'absolute',
          bottom: '20px',
          left: '20px',
          background: 'rgba(0,0,0,0.85)',
          color: '#f5deb3',
          padding: '12px',
          borderRadius: '8px',
          fontSize: '11px',
          zIndex: 10000,
          maxWidth: '220px'
        }}>
          <div style={{ fontWeight: 'bold', marginBottom: '5px', color: '#8a6540' }}>v35 Features:</div>
          <ul style={{ margin: 0, paddingLeft: '15px', lineHeight: '1.4' }}>
            <li>7-stop radial gradients</li>
            <li>Sine/cosine waft motion</li>
            <li>alphaMultiplier layers</li>
            <li>Static particle size</li>
            <li>No rotation</li>
            <li>Debug red border</li>
          </ul>
        </div>
      </div>

      {/* v37 - Right Side */}
      <div style={{
        position: 'relative',
        width: '50%',
        height: '100%',
        zIndex: 10003
      }}>
        <SteamAnimationV37 />

        {/* v37 Label */}
        <div style={{
          position: 'absolute',
          top: '20px',
          left: '20px',
          background: 'rgba(0,0,0,0.85)',
          color: '#6a9a5a',
          padding: '10px 20px',
          borderRadius: '8px',
          border: '2px solid #6a9a5a',
          fontWeight: 'bold',
          fontSize: '16px',
          zIndex: 10000
        }}>
          v37 - Enhanced
        </div>

        {/* v37 Features */}
        <div style={{
          position: 'absolute',
          bottom: '20px',
          right: '20px',
          background: 'rgba(0,0,0,0.85)',
          color: '#f5deb3',
          padding: '12px',
          borderRadius: '8px',
          fontSize: '11px',
          zIndex: 10000,
          maxWidth: '220px'
        }}>
          <div style={{ fontWeight: 'bold', marginBottom: '5px', color: '#6a9a5a' }}>v37 Additions:</div>
          <ul style={{ margin: 0, paddingLeft: '15px', lineHeight: '1.4' }}>
            <li>+ Perlin noise flow</li>
            <li>+ Texture overlay</li>
            <li>+ Particle rotation</li>
            <li>+ Scale evolution</li>
            <li>+ Depth property</li>
            <li>- Debug border removed</li>
          </ul>
          <div style={{ marginTop: '8px', fontSize: '10px', color: '#aaa', fontStyle: 'italic' }}>
            All v35 features preserved
          </div>
        </div>
      </div>

      {/* Center instruction */}
      <div style={{
        position: 'absolute',
        top: '50%',
        left: '50%',
        transform: 'translate(-50%, -50%)',
        background: 'rgba(0,0,0,0.95)',
        color: '#f5deb3',
        padding: '20px',
        borderRadius: '12px',
        border: '2px solid #c9a87a',
        textAlign: 'center',
        zIndex: 10001,
        fontSize: '14px'
      }}>
        <div style={{ fontSize: '18px', fontWeight: 'bold', marginBottom: '10px' }}>
          Click "☰ Open Menu" on each side
        </div>
        <div style={{ fontSize: '12px', color: '#aaa', marginBottom: '10px' }}>
          Watch the full 5-phase animation on both
        </div>
        <div style={{ fontSize: '11px', color: '#7a9a6a' }}>
          v37 should look identical to v35 with subtle enhancements
        </div>
      </div>

      {/* Back link */}
      <a
        href="?test=v37"
        style={{
          position: 'absolute',
          top: '20px',
          left: '50%',
          transform: 'translateX(-50%)',
          background: 'rgba(0,0,0,0.8)',
          color: '#c9a87a',
          padding: '8px 16px',
          borderRadius: '6px',
          fontSize: '12px',
          textDecoration: 'none',
          zIndex: 10002
        }}
      >
        ← Back to v37 solo
      </a>
    </div>
  );
}
