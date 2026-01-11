/**
 * AlignmentTest
 *
 * Visual tool to verify the reference APNG is perfectly aligned
 * with the live animation position before running the diff pipeline.
 *
 * KEY INSIGHT: Both reference and live MUST render in the EXACT same
 * container to ensure identical pixel crops for diff comparison.
 *
 * Modes:
 *   - blend: Shows reference semi-transparent over live
 *   - toggle: Rapidly switches between reference and live
 *   - sideBySide: Shows both next to each other
 *   - guides: Shows alignment guides and bounds
 *
 * Usage:
 *   http://localhost:5173/?align=blend
 *   http://localhost:5173/?align=toggle
 *   http://localhost:5173/?align=guides
 */

import { useState, useEffect, useRef, useCallback } from 'react'
// ElectricityOrtho replaces deprecated Canvas 2D (see .claude/guardrails.md)
import { ElectricityOrtho } from '../components/electricity/ortho'
import { PortalRing } from '../legacy/components'

// Import legacy styles for portal ring
import '../legacy/styles/index.css'

// Reference APNG path
const REFERENCE_APNG = '/reference/electricity_animation_effect_diff_analysis.apng'

// Default focal area - circular mask matching inner portal ring
// The inner portal area uses: calc(min(100%, 100vh - 40px) * 0.68)
// For 1280x900: min(1280, 860) * 0.68 = 584.8px diameter
const DEFAULT_FOCAL = {
  centerX: 640,
  centerY: 450,
  diameter: 584, // Inner portal ring diameter (circular mask)
}

type AlignMode = 'blend' | 'toggle' | 'sideBySide' | 'guides' | 'reference' | 'live'

export function AlignmentTest() {
  const params = new URLSearchParams(window.location.search)
  const initialMode = (params.get('align') as AlignMode) || 'blend'

  const [mode, setMode] = useState<AlignMode>(initialMode)
  const [blendOpacity, setBlendOpacity] = useState(0.5)
  const [toggleState, setToggleState] = useState(false)
  const [isLiveActive, setIsLiveActive] = useState(true)
  const [showGuides, setShowGuides] = useState(true)
  const [showBounds, setShowBounds] = useState(true)
  const [showPortalRing, setShowPortalRing] = useState(true)

  // Adjustable focal area
  const [focal, setFocal] = useState(DEFAULT_FOCAL)

  // Track actual rendered bounds
  const containerRef = useRef<HTMLDivElement>(null)
  const [actualBounds, setActualBounds] = useState({ x: 0, y: 0, width: 0, height: 0 })

  // Measure actual container bounds on mount and resize
  useEffect(() => {
    const measureBounds = () => {
      if (containerRef.current) {
        const rect = containerRef.current.getBoundingClientRect()
        setActualBounds({
          x: Math.round(rect.left),
          y: Math.round(rect.top),
          width: Math.round(rect.width),
          height: Math.round(rect.height),
        })
      }
    }

    measureBounds()
    window.addEventListener('resize', measureBounds)
    return () => window.removeEventListener('resize', measureBounds)
  }, [])

  // Toggle animation for toggle mode
  useEffect(() => {
    if (mode !== 'toggle') return

    const interval = setInterval(() => {
      setToggleState(prev => !prev)
    }, 500)

    return () => clearInterval(interval)
  }, [mode])

  // Keyboard shortcuts
  useEffect(() => {
    const handleKey = (e: KeyboardEvent) => {
      switch (e.key) {
        case '1': setMode('blend'); break
        case '2': setMode('toggle'); break
        case '3': setMode('sideBySide'); break
        case '4': setMode('guides'); break
        case 'r': setMode('reference'); break
        case 'l': setMode('live'); break
        case 'g': setShowGuides(prev => !prev); break
        case 'b': setShowBounds(prev => !prev); break
        case 'p': setShowPortalRing(prev => !prev); break
        case ' ':
          e.preventDefault()
          setIsLiveActive(prev => !prev)
          break
        case 'ArrowUp':
          if (e.shiftKey) setFocal(f => ({ ...f, centerY: f.centerY - 5 }))
          else setBlendOpacity(prev => Math.min(1, prev + 0.1))
          break
        case 'ArrowDown':
          if (e.shiftKey) setFocal(f => ({ ...f, centerY: f.centerY + 5 }))
          else setBlendOpacity(prev => Math.max(0, prev - 0.1))
          break
        case 'ArrowLeft':
          if (e.shiftKey) setFocal(f => ({ ...f, centerX: f.centerX - 5 }))
          break
        case 'ArrowRight':
          if (e.shiftKey) setFocal(f => ({ ...f, centerX: f.centerX + 5 }))
          break
        case '+':
        case '=':
          setFocal(f => ({ ...f, diameter: f.diameter + 10 }))
          break
        case '-':
          setFocal(f => ({ ...f, diameter: Math.max(100, f.diameter - 10) }))
          break
        case 'c':
          // Copy focal config to clipboard
          navigator.clipboard.writeText(`centerX: ${focal.centerX}, centerY: ${focal.centerY}, diameter: ${focal.diameter}`)
          break
      }
    }

    window.addEventListener('keydown', handleKey)
    return () => window.removeEventListener('keydown', handleKey)
  }, [focal])

  // Copy config to clipboard
  const copyConfig = useCallback(() => {
    const radius = Math.round(focal.diameter / 2)
    const cropX = Math.round(focal.centerX - radius)
    const cropY = Math.round(focal.centerY - radius)
    const config = `// Update scripts/focal-config.mjs:
export const FOCAL_AREA = {
  centerX: ${focal.centerX},
  centerY: ${focal.centerY},
  radius: ${radius},
  padding: 0,
}

// Circular mask: center=(${focal.centerX}, ${focal.centerY}), diameter=${focal.diameter}
// Bounding box: x=${cropX}, y=${cropY}, size=${focal.diameter}x${focal.diameter}`
    navigator.clipboard.writeText(config)
    alert('Config copied to clipboard!')
  }, [focal])

  // The animation container - SHARED between reference and live
  // This ensures both render at the EXACT same position/size
  const animationContainerStyle: React.CSSProperties = {
    position: 'absolute',
    top: '50%',
    left: '50%',
    transform: 'translate(-50%, -50%)',
    width: 'calc(min(100%, 100vh - 40px) * 0.78)',
    height: 'calc(min(100%, 100vh - 40px) * 0.78)',
    borderRadius: '50%',
    overflow: 'visible', // Allow glow to show outside bounds
  }

  // Render reference APNG - fills the shared container
  const renderReference = (opacity: number = 1) => (
    <img
      src={REFERENCE_APNG}
      alt="Reference"
      style={{
        position: 'absolute',
        top: 0,
        left: 0,
        width: '100%',
        height: '100%',
        objectFit: 'contain', // Use contain to preserve aspect ratio
        opacity,
        pointerEvents: 'none',
      }}
    />
  )

  // Render live animation - uses ElectricityOrtho's internal positioning
  // ElectricityOrtho replaces deprecated Canvas 2D (see .claude/guardrails.md)
  const renderLive = (opacity: number = 1) => (
    <div style={{ opacity, width: '100%', height: '100%', position: 'relative' }}>
      <ElectricityOrtho
        isActive={isLiveActive}
        onComplete={() => setIsLiveActive(false)}
      />
    </div>
  )

  // Crop area guides - CIRCULAR mask matching inner portal ring
  const renderCropGuides = () => {
    const radius = focal.diameter / 2

    return (
      <div
        style={{
          position: 'fixed',
          inset: 0,
          pointerEvents: 'none',
          zIndex: 100,
        }}
      >
        {/* Center crosshair */}
        <div
          style={{
            position: 'absolute',
            left: focal.centerX - 1,
            top: 0,
            bottom: 0,
            width: 2,
            background: 'rgba(255, 0, 0, 0.5)',
          }}
        />
        <div
          style={{
            position: 'absolute',
            top: focal.centerY - 1,
            left: 0,
            right: 0,
            height: 2,
            background: 'rgba(255, 0, 0, 0.5)',
          }}
        />

        {/* Circular mask outline (yellow) - this is the crop area */}
        <div
          style={{
            position: 'absolute',
            left: focal.centerX - radius,
            top: focal.centerY - radius,
            width: focal.diameter,
            height: focal.diameter,
            border: '3px solid rgba(255, 255, 0, 0.9)',
            borderRadius: '50%',
            background: 'rgba(255, 255, 0, 0.03)',
            boxShadow: '0 0 0 2000px rgba(0, 0, 0, 0.5)', // Darken outside the circle
          }}
        />

        {/* Center marker */}
        <div
          style={{
            position: 'absolute',
            left: focal.centerX - 6,
            top: focal.centerY - 6,
            width: 12,
            height: 12,
            background: '#ff0',
            borderRadius: '50%',
            border: '2px solid #000',
          }}
        />

        {/* Label */}
        <div
          style={{
            position: 'absolute',
            left: focal.centerX - radius,
            top: focal.centerY - radius - 28,
            color: '#ff0',
            fontSize: 12,
            fontFamily: 'monospace',
            background: 'rgba(0,0,0,0.8)',
            padding: '2px 6px',
            borderRadius: 3,
          }}
        >
          Mask: {focal.diameter}px circle @ ({focal.centerX}, {focal.centerY})
        </div>
      </div>
    )
  }

  // Actual bounds indicator
  const renderBoundsIndicator = () => (
    <div
      style={{
        position: 'fixed',
        left: actualBounds.x,
        top: actualBounds.y,
        width: actualBounds.width,
        height: actualBounds.height,
        border: '2px dashed rgba(0, 255, 255, 0.7)',
        borderRadius: '50%',
        pointerEvents: 'none',
        zIndex: 99,
      }}
    >
      <div
        style={{
          position: 'absolute',
          bottom: -25,
          left: '50%',
          transform: 'translateX(-50%)',
          color: '#0ff',
          fontSize: 11,
          fontFamily: 'monospace',
          background: 'rgba(0,0,0,0.8)',
          padding: '2px 6px',
          whiteSpace: 'nowrap',
        }}
      >
        Actual: {actualBounds.width}x{actualBounds.height} @ ({actualBounds.x}, {actualBounds.y})
      </div>
    </div>
  )

  return (
    <div style={{ position: 'relative', width: '100vw', height: '100vh', background: '#0a0a0a', overflow: 'hidden' }}>
      {/* Control Panel */}
      <div
        style={{
          position: 'fixed',
          top: 10,
          left: 10,
          zIndex: 1000,
          background: 'rgba(0,0,0,0.95)',
          padding: 15,
          borderRadius: 8,
          color: '#fff',
          fontFamily: 'monospace',
          fontSize: 11,
          minWidth: 280,
          maxHeight: 'calc(100vh - 40px)',
          overflowY: 'auto',
        }}
      >
        <div style={{ fontWeight: 'bold', marginBottom: 10, fontSize: 14, color: '#DAA041' }}>
          Alignment Test
        </div>

        <div style={{ marginBottom: 10 }}>
          <strong>Mode:</strong>
          <div style={{ display: 'flex', gap: 4, marginTop: 5, flexWrap: 'wrap' }}>
            {(['blend', 'toggle', 'sideBySide', 'guides', 'reference', 'live'] as AlignMode[]).map(m => (
              <button
                key={m}
                onClick={() => setMode(m)}
                style={{
                  padding: '3px 6px',
                  background: mode === m ? '#DAA041' : '#333',
                  color: mode === m ? '#000' : '#fff',
                  border: 'none',
                  borderRadius: 3,
                  cursor: 'pointer',
                  fontSize: 10,
                }}
              >
                {m}
              </button>
            ))}
          </div>
        </div>

        {mode === 'blend' && (
          <div style={{ marginBottom: 10 }}>
            <strong>Blend: {Math.round(blendOpacity * 100)}%</strong>
            <input
              type="range"
              min="0"
              max="100"
              value={blendOpacity * 100}
              onChange={(e) => setBlendOpacity(Number(e.target.value) / 100)}
              style={{ width: '100%', marginTop: 5 }}
            />
            <div style={{ fontSize: 9, opacity: 0.7 }}>
              0% = Reference only, 100% = Live only
            </div>
          </div>
        )}

        <div style={{ marginBottom: 8 }}>
          <label style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            <input
              type="checkbox"
              checked={showGuides}
              onChange={(e) => setShowGuides(e.target.checked)}
            />
            Show circular mask (yellow)
          </label>
        </div>

        <div style={{ marginBottom: 8 }}>
          <label style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            <input
              type="checkbox"
              checked={showBounds}
              onChange={(e) => setShowBounds(e.target.checked)}
            />
            Show actual bounds (cyan)
          </label>
        </div>

        <div style={{ marginBottom: 8 }}>
          <label style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            <input
              type="checkbox"
              checked={showPortalRing}
              onChange={(e) => setShowPortalRing(e.target.checked)}
            />
            Show portal ring
          </label>
        </div>

        <div style={{ marginBottom: 10 }}>
          <button
            onClick={() => setIsLiveActive(prev => !prev)}
            style={{
              padding: '5px 10px',
              background: isLiveActive ? '#4a4' : '#a44',
              color: '#fff',
              border: 'none',
              borderRadius: 4,
              cursor: 'pointer',
              fontSize: 11,
            }}
          >
            Live: {isLiveActive ? 'ON' : 'OFF'}
          </button>
        </div>

        <div style={{ borderTop: '1px solid #333', paddingTop: 10, marginTop: 10 }}>
          <strong style={{ color: '#ff0' }}>Circular Mask (inner ring):</strong>
          <div style={{ marginTop: 5 }}>
            <label style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
              <span style={{ width: 50 }}>X:</span>
              <input
                type="number"
                value={focal.centerX}
                onChange={(e) => setFocal(f => ({ ...f, centerX: Number(e.target.value) }))}
                style={{ width: 60, background: '#222', color: '#fff', border: '1px solid #444', padding: 2 }}
              />
            </label>
            <label style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
              <span style={{ width: 50 }}>Y:</span>
              <input
                type="number"
                value={focal.centerY}
                onChange={(e) => setFocal(f => ({ ...f, centerY: Number(e.target.value) }))}
                style={{ width: 60, background: '#222', color: '#fff', border: '1px solid #444', padding: 2 }}
              />
            </label>
            <label style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
              <span style={{ width: 50 }}>Dia:</span>
              <input
                type="number"
                value={focal.diameter}
                onChange={(e) => setFocal(f => ({ ...f, diameter: Number(e.target.value) }))}
                style={{ width: 60, background: '#222', color: '#fff', border: '1px solid #444', padding: 2 }}
              />
            </label>
          </div>
          <button
            onClick={copyConfig}
            style={{
              marginTop: 8,
              padding: '5px 10px',
              background: '#DAA041',
              color: '#000',
              border: 'none',
              borderRadius: 4,
              cursor: 'pointer',
              fontSize: 11,
              fontWeight: 'bold',
            }}
          >
            Copy Config
          </button>
        </div>

        <div style={{ fontSize: 9, opacity: 0.7, borderTop: '1px solid #333', paddingTop: 8, marginTop: 10 }}>
          <strong>Keyboard:</strong><br />
          1-4: Switch modes | R/L: Ref/Live<br />
          G: Guides | B: Bounds | P: Portal ring<br />
          Space: Toggle animation<br />
          Arrows: Adjust blend<br />
          Shift+Arrows: Move mask center<br />
          +/-: Resize mask diameter
        </div>

        <div style={{ fontSize: 9, opacity: 0.6, borderTop: '1px solid #333', paddingTop: 8, marginTop: 8 }}>
          <strong>Actual Bounds:</strong><br />
          {actualBounds.width}x{actualBounds.height}<br />
          @ ({actualBounds.x}, {actualBounds.y})
        </div>
      </div>

      {/* Mode indicator */}
      <div
        style={{
          position: 'fixed',
          top: 10,
          right: 10,
          padding: '6px 12px',
          background: mode === 'reference' ? '#4a4' : mode === 'live' ? '#44a' : '#a84',
          color: '#fff',
          fontFamily: 'monospace',
          fontWeight: 'bold',
          borderRadius: 4,
          zIndex: 1000,
          fontSize: 12,
        }}
      >
        {mode.toUpperCase()}
        {mode === 'toggle' && ` (${toggleState ? 'REF' : 'LIVE'})`}
      </div>

      {/* Main animation container - shared positioning */}
      <div style={{ position: 'relative', width: '100%', height: '100%' }}>
        {/* Portal ring - the UI element that frames the animation */}
        {showPortalRing && (
          <div style={{
            position: 'absolute',
            top: '50%',
            left: '50%',
            transform: 'translate(-50%, -50%)',
            width: 'calc(min(100%, 100vh - 40px))',
            height: 'calc(min(100%, 100vh - 40px))',
            pointerEvents: 'none',
            zIndex: 30,
          }}>
            <PortalRing />
          </div>
        )}

        {/* The shared container for both reference and live */}
        <div ref={containerRef} style={animationContainerStyle}>
          {mode === 'blend' && (
            <>
              {renderReference(1 - blendOpacity)}
              {renderLive(blendOpacity)}
            </>
          )}

          {mode === 'toggle' && (
            toggleState ? renderReference() : renderLive()
          )}

          {mode === 'guides' && (
            <>
              {renderReference(0.5)}
              {renderLive(0.5)}
            </>
          )}

          {mode === 'reference' && renderReference()}
          {mode === 'live' && renderLive()}
        </div>

        {/* Side by side mode - separate containers */}
        {mode === 'sideBySide' && (
          <div style={{ display: 'flex', width: '100%', height: '100%', position: 'absolute', top: 0, left: 0 }}>
            <div style={{ flex: 1, position: 'relative', borderRight: '2px solid #333', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <div style={{ position: 'absolute', top: 10, left: '50%', transform: 'translateX(-50%)', color: '#4a4', fontFamily: 'monospace', zIndex: 50 }}>REFERENCE</div>
              <div style={{ ...animationContainerStyle, position: 'relative', transform: 'none' }}>
                {renderReference()}
              </div>
            </div>
            <div style={{ flex: 1, position: 'relative', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <div style={{ position: 'absolute', top: 10, left: '50%', transform: 'translateX(-50%)', color: '#44a', fontFamily: 'monospace', zIndex: 50 }}>LIVE</div>
              <div style={{ ...animationContainerStyle, position: 'relative', transform: 'none' }}>
                {renderLive()}
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Alignment guides overlay */}
      {showGuides && renderCropGuides()}

      {/* Actual bounds indicator */}
      {showBounds && renderBoundsIndicator()}
    </div>
  )
}

export default AlignmentTest
