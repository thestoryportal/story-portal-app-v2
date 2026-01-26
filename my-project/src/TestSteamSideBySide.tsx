/**
 * Side-by-side comparison: v35 (Baseline) vs v36 (AAA Enhanced)
 */

import SteamAnimationV35 from './components/steam-modal/enhanced/steam-animation-v35';
import SteamAnimationV36 from './components/steam-modal/enhanced/steam-animation-v36';

export function TestSteamSideBySide() {
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
          background: 'rgba(0,0,0,0.8)',
          color: '#8a6540',
          padding: '10px 20px',
          borderRadius: '8px',
          border: '2px solid #8a6540',
          fontWeight: 'bold',
          fontSize: '16px',
          zIndex: 10000
        }}>
          v35 - Baseline (~40% AAA)
        </div>

        {/* v35 Features */}
        <div style={{
          position: 'absolute',
          bottom: '20px',
          left: '20px',
          background: 'rgba(0,0,0,0.8)',
          color: '#f5deb3',
          padding: '12px',
          borderRadius: '8px',
          fontSize: '11px',
          zIndex: 10000,
          maxWidth: '250px'
        }}>
          <div style={{ fontWeight: 'bold', marginBottom: '5px', color: '#8a6540' }}>Features:</div>
          <ul style={{ margin: 0, paddingLeft: '15px', lineHeight: '1.4' }}>
            <li>Radial gradients</li>
            <li>Sine/cosine motion</li>
            <li>Static size</li>
            <li>No rotation</li>
            <li>Flat depth</li>
          </ul>
        </div>
      </div>

      {/* v36 - Right Side */}
      <div style={{
        position: 'relative',
        width: '50%',
        height: '100%',
        zIndex: 10003
      }}>
        <SteamAnimationV36 />

        {/* v36 Label */}
        <div style={{
          position: 'absolute',
          top: '20px',
          left: '20px',
          background: 'rgba(0,0,0,0.8)',
          color: '#c9a87a',
          padding: '10px 20px',
          borderRadius: '8px',
          border: '2px solid #c9a87a',
          fontWeight: 'bold',
          fontSize: '16px',
          zIndex: 10000
        }}>
          v36 - AAA Enhanced (~75-80% AAA)
        </div>

        {/* v36 Features */}
        <div style={{
          position: 'absolute',
          bottom: '20px',
          right: '20px',
          background: 'rgba(0,0,0,0.8)',
          color: '#f5deb3',
          padding: '12px',
          borderRadius: '8px',
          fontSize: '11px',
          zIndex: 10000,
          maxWidth: '250px'
        }}>
          <div style={{ fontWeight: 'bold', marginBottom: '5px', color: '#c9a87a' }}>Features:</div>
          <ul style={{ margin: 0, paddingLeft: '15px', lineHeight: '1.4' }}>
            <li>Texture sprites</li>
            <li>Perlin noise flow</li>
            <li>Scale evolution</li>
            <li>Particle rotation</li>
            <li>Depth + blur</li>
            <li>Glow pass</li>
            <li>Object pooling</li>
          </ul>
        </div>
      </div>

      {/* Center instruction */}
      <div style={{
        position: 'absolute',
        top: '50%',
        left: '50%',
        transform: 'translate(-50%, -50%)',
        background: 'rgba(0,0,0,0.9)',
        color: '#f5deb3',
        padding: '20px',
        borderRadius: '12px',
        border: '2px solid #c9a87a',
        textAlign: 'center',
        zIndex: 10001,
        fontSize: '14px'
      }}>
        <div style={{ fontSize: '18px', fontWeight: 'bold', marginBottom: '10px' }}>
          Click "☰ Open Menu" on each side to start
        </div>
        <div style={{ fontSize: '12px', color: '#aaa' }}>
          Compare particle shapes, movement, rotation, and depth
        </div>
      </div>
    </div>
  );
}
