/**
 * ElectricityOverlayTest
 *
 * Renders the full UI with either:
 * - The reference APNG animation (mode=reference)
 * - The live Canvas animation (mode=live)
 *
 * CRITICAL: Both reference and live MUST render in the EXACT same
 * container at the EXACT same size for accurate pixel comparison.
 *
 * This allows full-page screenshot comparison where only the
 * animation area differs between captures.
 *
 * Usage:
 *   http://localhost:5173/?overlay=reference  - Show reference APNG
 *   http://localhost:5173/?overlay=live       - Show live animation
 *   http://localhost:5173/?overlay=live&auto=true - Auto-trigger live
 */

import { useState, useEffect, useCallback } from 'react'
// ElectricityOrtho replaces deprecated Canvas 2D (see .claude/guardrails.md)
import { ElectricityOrtho } from '../components/electricity/ortho'

// Reference APNG path (relative to public folder)
const REFERENCE_APNG = '/reference/electricity_animation_effect_diff_analysis.apng'

// Shared container sizing - must match for both reference and live
// This uses the same sizing as ElectricityAnimation's internal container
const CONTAINER_SIZE = 'calc(min(100%, 100vh - 40px) * 0.78)'

interface OverlayProps {
  mode: 'reference' | 'live'
  autoTrigger?: boolean
}

export function ElectricityOverlay({ mode, autoTrigger = false }: OverlayProps) {
  const [isActive, setIsActive] = useState(false)
  const [phase, setPhase] = useState<string>('idle')

  // Trigger animation
  const trigger = useCallback(() => {
    setIsActive(false)
    setPhase('idle')

    // Reset then start
    requestAnimationFrame(() => {
      setIsActive(true)
      window.dispatchEvent(new CustomEvent('electricity-start'))
    })
  }, [])

  // Handle completion
  const handleComplete = useCallback(() => {
    setPhase('complete')
    // Don't deactivate in overlay mode - keep it running for capture
    // setIsActive(false)
    window.dispatchEvent(new CustomEvent('electricity-complete'))
  }, [])

  // Auto-trigger on mount - CRITICAL: Default to true for live mode
  useEffect(() => {
    if (mode === 'live') {
      // Always auto-trigger for live mode (for diff testing)
      const timer = setTimeout(trigger, 500)
      return () => clearTimeout(timer)
    }
  }, [mode, trigger])

  // Expose trigger globally for Puppeteer
  useEffect(() => {
    (window as any).__triggerElectricity = trigger;
    (window as any).__electricityMode = mode;
    (window as any).__electricityPhase = phase;
    (window as any).__electricityActive = isActive;
  }, [trigger, mode, phase, isActive])

  // SHARED container style - identical for reference and live
  // This ensures both capture the same pixel area
  const containerStyle: React.CSSProperties = {
    position: 'absolute',
    top: '50%',
    left: '50%',
    transform: 'translate(-50%, -50%)',
    width: CONTAINER_SIZE,
    height: CONTAINER_SIZE,
    pointerEvents: 'none',
    zIndex: 27,
    // No overflow:hidden - allow glow effects to show
    overflow: 'visible',
  }

  if (mode === 'reference') {
    // Reference APNG - render in same container, using contain to preserve aspect ratio
    return (
      <div className="electricity-overlay-container" style={containerStyle}>
        <img
          src={REFERENCE_APNG}
          alt="Reference electricity animation"
          style={{
            width: '100%',
            height: '100%',
            objectFit: 'contain', // Preserve aspect ratio
            display: 'block',
          }}
        />
      </div>
    )
  }

  // Live mode - ElectricityOrtho has its own internal positioning
  // ElectricityOrtho replaces deprecated Canvas 2D (see .claude/guardrails.md)
  return (
    <ElectricityOrtho
      isActive={isActive}
      onPhaseChange={(p) => setPhase(p)}
      onComplete={handleComplete}
      lockAtPeak={true}
      intensity={1.0}
    />
  )
}

/**
 * Full page wrapper that includes mode indicator
 */
export function ElectricityOverlayTestPage() {
  const params = new URLSearchParams(window.location.search)
  const mode = (params.get('overlay') as 'reference' | 'live') || 'reference'
  const autoTrigger = params.get('auto') === 'true'

  return (
    <>
      {/* Mode indicator for debugging (hidden during capture) */}
      <div
        id="overlay-mode-indicator"
        style={{
          position: 'fixed',
          top: 10,
          right: 10,
          padding: '4px 8px',
          background: mode === 'reference' ? '#4a4' : '#44a',
          color: '#fff',
          fontSize: 12,
          fontFamily: 'monospace',
          borderRadius: 4,
          zIndex: 9999,
          opacity: 0.8,
        }}
      >
        {mode.toUpperCase()}
      </div>

      {/* The overlay component */}
      <ElectricityOverlay mode={mode} autoTrigger={autoTrigger} />
    </>
  )
}

export default ElectricityOverlayTestPage
