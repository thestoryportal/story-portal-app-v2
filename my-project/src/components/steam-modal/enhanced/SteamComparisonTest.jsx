import React, { useState, useEffect } from 'react';
import SteamAnimationV35 from './steam-animation-v35';
import SteamAnimationV36 from './steam-animation-v36';

/**
 * Steam Animation Comparison Tool
 *
 * Compare v35 (baseline) vs v36 (AAA enhanced) side-by-side or in toggle mode
 *
 * Modes:
 * - Toggle: Switch between versions with a button
 * - Split: View both versions side-by-side
 * - Solo v35: Only v35 (baseline)
 * - Solo v36: Only v36 (enhanced)
 */
const SteamComparisonTest = () => {
  const [mode, setMode] = useState('toggle'); // 'toggle', 'split', 'solo-v35', 'solo-v36'
  const [activeVersion, setActiveVersion] = useState('v36'); // For toggle mode
  const [showStats, setShowStats] = useState(true);
  const [fps, setFps] = useState({ v35: 0, v36: 0 });

  // FPS monitoring (simplified)
  useEffect(() => {
    let frameCount = 0;
    let lastTime = performance.now();

    const measureFPS = () => {
      frameCount++;
      const currentTime = performance.now();

      if (currentTime >= lastTime + 1000) {
        const currentFPS = Math.round((frameCount * 1000) / (currentTime - lastTime));

        // Update FPS for active version(s)
        if (mode === 'toggle') {
          setFps(prev => ({ ...prev, [activeVersion]: currentFPS }));
        } else if (mode === 'split') {
          // In split mode, FPS applies to both (simplified)
          setFps({ v35: currentFPS, v36: currentFPS });
        } else if (mode === 'solo-v35') {
          setFps(prev => ({ ...prev, v35: currentFPS }));
        } else if (mode === 'solo-v36') {
          setFps(prev => ({ ...prev, v36: currentFPS }));
        }

        frameCount = 0;
        lastTime = currentTime;
      }

      requestAnimationFrame(measureFPS);
    };

    const rafId = requestAnimationFrame(measureFPS);
    return () => cancelAnimationFrame(rafId);
  }, [mode, activeVersion]);

  const versionInfo = {
    v35: {
      name: 'v35 - Baseline',
      quality: '~40% AAA',
      features: [
        'Radial gradient particles',
        'Sine/cosine waft motion',
        'Static particle size',
        'No rotation',
        'Flat depth rendering',
        '4-layer canvas system'
      ],
      color: '#8a6540'
    },
    v36: {
      name: 'v36 - AAA Enhanced',
      quality: '~75-80% AAA',
      features: [
        'Texture-based particles',
        'Perlin noise flow fields',
        'Scale evolution over lifetime',
        'Particle rotation',
        'Multi-layer depth + sorting',
        'Atmospheric glow pass',
        'Object pooling'
      ],
      color: '#c9a87a'
    }
  };

  const toggleVersion = () => {
    setActiveVersion(prev => prev === 'v35' ? 'v36' : 'v35');
  };

  const renderControls = () => (
    <div className="fixed top-4 left-4 z-50 bg-black/80 backdrop-blur-sm rounded-lg p-4 text-white" style={{ maxWidth: '320px' }}>
      <h2 className="text-lg font-bold mb-3 text-amber-400">Steam Animation Comparison</h2>

      {/* Mode Selection */}
      <div className="mb-4">
        <p className="text-xs text-gray-400 mb-2 uppercase tracking-wide">View Mode</p>
        <div className="grid grid-cols-2 gap-2">
          <button
            onClick={() => setMode('toggle')}
            className={`px-3 py-2 text-sm rounded transition-all ${
              mode === 'toggle'
                ? 'bg-amber-600 text-white'
                : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
            }`}
          >
            Toggle
          </button>
          <button
            onClick={() => setMode('split')}
            className={`px-3 py-2 text-sm rounded transition-all ${
              mode === 'split'
                ? 'bg-amber-600 text-white'
                : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
            }`}
          >
            Split
          </button>
          <button
            onClick={() => setMode('solo-v35')}
            className={`px-3 py-2 text-sm rounded transition-all ${
              mode === 'solo-v35'
                ? 'bg-amber-600 text-white'
                : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
            }`}
          >
            v35 Only
          </button>
          <button
            onClick={() => setMode('solo-v36')}
            className={`px-3 py-2 text-sm rounded transition-all ${
              mode === 'solo-v36'
                ? 'bg-amber-600 text-white'
                : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
            }`}
          >
            v36 Only
          </button>
        </div>
      </div>

      {/* Toggle Button (only in toggle mode) */}
      {mode === 'toggle' && (
        <div className="mb-4">
          <button
            onClick={toggleVersion}
            className="w-full px-4 py-3 bg-gradient-to-r from-amber-600 to-amber-700 hover:from-amber-500 hover:to-amber-600 text-white font-semibold rounded-lg transition-all transform hover:scale-105 active:scale-95"
          >
            Switch to {activeVersion === 'v35' ? 'v36' : 'v35'}
          </button>
        </div>
      )}

      {/* Stats Toggle */}
      <div className="mb-4">
        <label className="flex items-center cursor-pointer">
          <input
            type="checkbox"
            checked={showStats}
            onChange={(e) => setShowStats(e.target.checked)}
            className="mr-2"
          />
          <span className="text-sm">Show Version Info</span>
        </label>
      </div>

      {/* Current Version Info */}
      {showStats && (
        <div className="space-y-4">
          {mode === 'toggle' && (
            <VersionCard version={activeVersion} info={versionInfo[activeVersion]} fps={fps[activeVersion]} />
          )}
          {mode === 'split' && (
            <>
              <VersionCard version="v35" info={versionInfo.v35} fps={fps.v35} compact />
              <VersionCard version="v36" info={versionInfo.v36} fps={fps.v36} compact />
            </>
          )}
          {mode === 'solo-v35' && (
            <VersionCard version="v35" info={versionInfo.v35} fps={fps.v35} />
          )}
          {mode === 'solo-v36' && (
            <VersionCard version="v36" info={versionInfo.v36} fps={fps.v36} />
          )}
        </div>
      )}

      {/* Instructions */}
      <div className="mt-4 pt-4 border-t border-gray-700">
        <p className="text-xs text-gray-400 leading-relaxed">
          <strong className="text-amber-400">Tip:</strong> Use Toggle mode to quickly compare.
          Use Split mode to see differences simultaneously.
        </p>
      </div>
    </div>
  );

  const VersionCard = ({ version, info, fps, compact = false }) => (
    <div
      className="rounded-lg p-3 border-2"
      style={{
        borderColor: info.color,
        backgroundColor: 'rgba(0,0,0,0.4)'
      }}
    >
      <div className="flex items-center justify-between mb-2">
        <h3 className="font-bold text-sm" style={{ color: info.color }}>
          {info.name}
        </h3>
        <span className={`text-xs px-2 py-1 rounded ${fps >= 55 ? 'bg-green-600' : fps >= 45 ? 'bg-yellow-600' : 'bg-red-600'}`}>
          {fps} FPS
        </span>
      </div>

      {!compact && (
        <>
          <p className="text-xs text-gray-300 mb-2">
            Quality: <span className="text-amber-400">{info.quality}</span>
          </p>

          <ul className="text-xs text-gray-400 space-y-1">
            {info.features.map((feature, idx) => (
              <li key={idx} className="flex items-start">
                <span className="mr-2">•</span>
                <span>{feature}</span>
              </li>
            ))}
          </ul>
        </>
      )}
    </div>
  );

  const renderVersionLabel = (version, position) => (
    <div
      className="absolute z-40 bg-black/70 backdrop-blur-sm px-4 py-2 rounded-lg"
      style={{
        [position]: '20px',
        top: '20px',
        pointerEvents: 'none'
      }}
    >
      <p className="text-white font-bold text-sm" style={{ color: versionInfo[version].color }}>
        {versionInfo[version].name}
      </p>
      <p className="text-xs text-gray-400">{versionInfo[version].quality}</p>
    </div>
  );

  return (
    <div className="relative w-full h-screen bg-gray-900">
      {renderControls()}

      {/* Toggle Mode */}
      {mode === 'toggle' && (
        <div className="w-full h-full">
          {renderVersionLabel(activeVersion, 'right')}
          {activeVersion === 'v35' ? <SteamAnimationV35 /> : <SteamAnimationV36 />}
        </div>
      )}

      {/* Split Mode */}
      {mode === 'split' && (
        <div className="flex w-full h-full">
          <div className="relative w-1/2 h-full border-r-2 border-amber-500">
            {renderVersionLabel('v35', 'right')}
            <SteamAnimationV35 />
          </div>
          <div className="relative w-1/2 h-full">
            {renderVersionLabel('v36', 'right')}
            <SteamAnimationV36 />
          </div>
        </div>
      )}

      {/* Solo v35 Mode */}
      {mode === 'solo-v35' && (
        <div className="w-full h-full">
          {renderVersionLabel('v35', 'right')}
          <SteamAnimationV35 />
        </div>
      )}

      {/* Solo v36 Mode */}
      {mode === 'solo-v36' && (
        <div className="w-full h-full">
          {renderVersionLabel('v36', 'right')}
          <SteamAnimationV36 />
        </div>
      )}

      {/* Watermark */}
      <div className="fixed bottom-4 right-4 z-50 text-white/30 text-xs">
        Steam Animation v35 → v36 Comparison Tool
      </div>
    </div>
  );
};

export default SteamComparisonTest;
