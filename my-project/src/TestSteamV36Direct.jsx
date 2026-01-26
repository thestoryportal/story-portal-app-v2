import React from 'react';
import SteamAnimationV35 from './components/steam-modal/enhanced/steam-animation-v35';

/**
 * Direct test for Steam Animation v35 (baseline)
 * Simple wrapper to verify routing works
 */
function TestSteamV36Direct() {
  return (
    <div style={{ width: '100vw', height: '100vh', overflow: 'hidden', background: '#1c1814' }}>
      <SteamAnimationV35 />
    </div>
  );
}

export default TestSteamV36Direct;
