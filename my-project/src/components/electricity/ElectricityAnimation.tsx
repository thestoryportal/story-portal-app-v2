/**
 * ElectricityAnimation Component
 *
 * Clean baseline electricity effect for the Story Portal wheel.
 * Renders procedural lightning bolts with glow effects.
 */

import { useRef, useEffect, useCallback, useMemo } from 'react'

// =============================================================================
// Types
// =============================================================================

export interface ElectricityAnimationProps {
  isActive: boolean
  onPhaseChange?: (phase: 'build' | 'peak' | 'decay' | 'complete') => void
  onComplete?: () => void
  intensity?: number
  lockAtPeak?: boolean
}

type AnimationPhase = 'idle' | 'build' | 'peak' | 'decay'

interface Point {
  x: number
  y: number
}

interface BoltPath {
  points: Point[]
  branches: BoltPath[]
  thickness: number
}

// =============================================================================
// Constants
// =============================================================================

const COLORS = {
  core: '#FFFDE7',
  innerGlow: '#FFA726',
  outerGlow: '#FF6F00',
} as const

const TIMING = {
  buildDuration: 900,
  peakDuration: 1300,
  decayDuration: 800,
  totalDuration: 3000,
  frameInterval: 33,
} as const

const BOLT_CONFIG = {
  count: 8,
  branchesPerBolt: { min: 2, max: 4 },
  coreThickness: { min: 2, max: 4 },
  boltLength: { min: 80, max: 120 },
  segmentLength: { min: 10, max: 20 },
  angleDeviation: 30,
  branchAngle: { min: 25, max: 50 },
  branchLengthRatio: 0.5,
  branchThicknessRatio: 0.7,
} as const

const GLOW_CONFIG = {
  innerBlur: 8,
  outerBlur: 20,
  coreBlur: 2,
} as const

// =============================================================================
// Utility Functions
// =============================================================================

function lerp(a: number, b: number, t: number): number {
  return a + (b - a) * t
}

function randomRange(min: number, max: number): number {
  return Math.random() * (max - min) + min
}

function randomInt(min: number, max: number): number {
  return Math.floor(randomRange(min, max + 1))
}

function clamp(value: number, min: number, max: number): number {
  return Math.max(min, Math.min(max, value))
}

function easeInQuad(t: number): number {
  return t * t
}

function easeOutQuad(t: number): number {
  return 1 - (1 - t) * (1 - t)
}

// =============================================================================
// Bolt Generation
// =============================================================================

function generateBoltPath(
  startPoint: Point,
  angle: number,
  length: number,
  thickness: number,
  depth: number = 0
): BoltPath {
  const points: Point[] = [startPoint]
  let currentPoint = { ...startPoint }
  let currentAngle = angle
  let remainingLength = length

  while (remainingLength > 0) {
    const segmentLen = Math.min(
      remainingLength,
      randomRange(BOLT_CONFIG.segmentLength.min, BOLT_CONFIG.segmentLength.max)
    )

    const deviation = randomRange(-BOLT_CONFIG.angleDeviation, BOLT_CONFIG.angleDeviation)
    currentAngle += (deviation * Math.PI) / 180

    currentPoint = {
      x: currentPoint.x + Math.cos(currentAngle) * segmentLen,
      y: currentPoint.y + Math.sin(currentAngle) * segmentLen,
    }

    points.push(currentPoint)
    remainingLength -= segmentLen
  }

  const branches: BoltPath[] = []
  if (depth === 0 && points.length > 2) {
    const branchCount = randomInt(BOLT_CONFIG.branchesPerBolt.min, BOLT_CONFIG.branchesPerBolt.max)

    for (let i = 0; i < branchCount; i++) {
      const branchPointIndex = randomInt(1, points.length - 2)
      const branchPoint = points[branchPointIndex]
      const branchDirection = Math.random() > 0.5 ? 1 : -1
      const branchAngle = currentAngle + branchDirection * randomRange(
        BOLT_CONFIG.branchAngle.min,
        BOLT_CONFIG.branchAngle.max
      ) * (Math.PI / 180)

      const branchLength = length * BOLT_CONFIG.branchLengthRatio
      const branchThickness = thickness * BOLT_CONFIG.branchThicknessRatio

      branches.push(
        generateBoltPath(branchPoint, branchAngle, branchLength, branchThickness, depth + 1)
      )
    }
  }

  return { points, branches, thickness }
}

function generateAllBolts(intensity: number, canvasSize: number): BoltPath[] {
  const center = canvasSize / 2
  const bolts: BoltPath[] = []
  const angleStep = (Math.PI * 2) / BOLT_CONFIG.count

  for (let i = 0; i < BOLT_CONFIG.count; i++) {
    const angle = angleStep * i + randomRange(-0.2, 0.2)
    const length = randomRange(BOLT_CONFIG.boltLength.min, BOLT_CONFIG.boltLength.max) * Math.max(0.5, intensity)
    const thickness = randomRange(BOLT_CONFIG.coreThickness.min, BOLT_CONFIG.coreThickness.max) * Math.max(0.5, intensity)

    const startPoint: Point = { x: center, y: center }
    bolts.push(generateBoltPath(startPoint, angle, length, thickness, 0))
  }

  return bolts
}

// =============================================================================
// Rendering
// =============================================================================

function renderBolt(
  ctx: CanvasRenderingContext2D,
  bolt: BoltPath,
  intensity: number,
  glowLevel: 'core' | 'inner' | 'outer'
) {
  if (bolt.points.length < 2) return

  ctx.lineCap = 'round'
  ctx.lineJoin = 'round'

  let color: string
  let lineWidth: number
  let blur: number
  let alpha: number

  switch (glowLevel) {
    case 'outer':
      color = COLORS.outerGlow
      lineWidth = bolt.thickness * 4
      blur = GLOW_CONFIG.outerBlur
      alpha = intensity * 0.3
      break
    case 'inner':
      color = COLORS.innerGlow
      lineWidth = bolt.thickness * 2
      blur = GLOW_CONFIG.innerBlur
      alpha = intensity * 0.6
      break
    case 'core':
    default:
      color = COLORS.core
      lineWidth = bolt.thickness
      blur = GLOW_CONFIG.coreBlur
      alpha = intensity * 0.9
      break
  }

  ctx.strokeStyle = color
  ctx.lineWidth = lineWidth
  ctx.shadowBlur = blur
  ctx.shadowColor = color
  ctx.globalAlpha = alpha

  ctx.beginPath()
  ctx.moveTo(bolt.points[0].x, bolt.points[0].y)
  for (let i = 1; i < bolt.points.length; i++) {
    ctx.lineTo(bolt.points[i].x, bolt.points[i].y)
  }
  ctx.stroke()

  for (const branch of bolt.branches) {
    renderBolt(ctx, branch, intensity, glowLevel)
  }
}

function renderAmbientGlow(
  ctx: CanvasRenderingContext2D,
  canvasSize: number,
  intensity: number
) {
  const center = canvasSize / 2
  const radius = canvasSize * 0.35

  const gradient = ctx.createRadialGradient(center, center, 0, center, center, radius)
  gradient.addColorStop(0, 'rgba(255, 111, 0, 0.2)')
  gradient.addColorStop(0.5, 'rgba(255, 111, 0, 0.1)')
  gradient.addColorStop(1, 'transparent')

  ctx.fillStyle = gradient
  ctx.globalAlpha = intensity * 0.5
  ctx.fillRect(0, 0, canvasSize, canvasSize)
}

function renderFrame(
  ctx: CanvasRenderingContext2D,
  bolts: BoltPath[],
  intensity: number,
  canvasSize: number
) {
  ctx.clearRect(0, 0, canvasSize, canvasSize)
  ctx.save()

  renderAmbientGlow(ctx, canvasSize, intensity)

  ctx.globalCompositeOperation = 'lighter'

  for (const bolt of bolts) {
    renderBolt(ctx, bolt, intensity, 'outer')
  }

  for (const bolt of bolts) {
    renderBolt(ctx, bolt, intensity, 'inner')
  }

  for (const bolt of bolts) {
    renderBolt(ctx, bolt, intensity, 'core')
  }

  ctx.restore()
}

function renderReducedMotion(
  ctx: CanvasRenderingContext2D,
  canvasSize: number
) {
  const center = canvasSize / 2
  const gradient = ctx.createRadialGradient(
    center, center, 0,
    center, center, canvasSize * 0.4
  )
  gradient.addColorStop(0, COLORS.innerGlow)
  gradient.addColorStop(0.5, COLORS.outerGlow)
  gradient.addColorStop(1, 'transparent')

  ctx.clearRect(0, 0, canvasSize, canvasSize)
  ctx.fillStyle = gradient
  ctx.globalAlpha = 0.6
  ctx.fillRect(0, 0, canvasSize, canvasSize)
}

// =============================================================================
// Main Component
// =============================================================================

export function ElectricityAnimation({
  isActive,
  onPhaseChange,
  onComplete,
  intensity: externalIntensity,
  lockAtPeak = false,
}: ElectricityAnimationProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const animationRef = useRef<number | null>(null)
  const startTimeRef = useRef<number | null>(null)
  const phaseRef = useRef<AnimationPhase>('idle')
  const boltsRef = useRef<BoltPath[]>([])
  const lastBoltUpdateRef = useRef<number>(0)

  const onPhaseChangeRef = useRef(onPhaseChange)
  const onCompleteRef = useRef(onComplete)

  useEffect(() => {
    onPhaseChangeRef.current = onPhaseChange
    onCompleteRef.current = onComplete
  }, [onPhaseChange, onComplete])

  const prefersReducedMotion = useMemo(() => {
    if (typeof window === 'undefined') return false
    return window.matchMedia('(prefers-reduced-motion: reduce)').matches
  }, [])

  const canvasSize = 465

  const regenerateBolts = useCallback((intensity: number) => {
    boltsRef.current = generateAllBolts(intensity, canvasSize)
  }, [canvasSize])

  const getPhaseAndIntensity = useCallback((elapsed: number): { phase: AnimationPhase; intensity: number } => {
    if (elapsed < TIMING.buildDuration) {
      const t = elapsed / TIMING.buildDuration
      return { phase: 'build', intensity: easeInQuad(t) }
    } else if (lockAtPeak || elapsed < TIMING.buildDuration + TIMING.peakDuration) {
      return { phase: 'peak', intensity: 1.0 }
    } else if (elapsed < TIMING.totalDuration) {
      const decayStart = TIMING.buildDuration + TIMING.peakDuration
      const t = (elapsed - decayStart) / TIMING.decayDuration
      return { phase: 'decay', intensity: 1 - easeOutQuad(t) }
    }
    return { phase: 'idle', intensity: 0 }
  }, [lockAtPeak])

  const animate = useCallback((timestamp: number) => {
    if (!canvasRef.current) return

    const ctx = canvasRef.current.getContext('2d')
    if (!ctx) return

    if (startTimeRef.current === null) {
      startTimeRef.current = timestamp
      regenerateBolts(0.1)
    }

    const elapsed = timestamp - (startTimeRef.current ?? timestamp)

    if (!lockAtPeak && elapsed >= TIMING.totalDuration) {
      ctx.clearRect(0, 0, canvasSize, canvasSize)
      phaseRef.current = 'idle'
      startTimeRef.current = null
      onPhaseChangeRef.current?.('complete')
      onCompleteRef.current?.()
      return
    }

    const { phase, intensity } = getPhaseAndIntensity(elapsed)
    const effectiveIntensity = externalIntensity ?? intensity

    if (phase !== phaseRef.current && phase !== 'idle') {
      phaseRef.current = phase
      onPhaseChangeRef.current?.(phase)
    }

    const timeSinceLastUpdate = timestamp - lastBoltUpdateRef.current
    if (timeSinceLastUpdate > TIMING.frameInterval * 3) {
      regenerateBolts(effectiveIntensity)
      lastBoltUpdateRef.current = timestamp
    }

    renderFrame(ctx, boltsRef.current, effectiveIntensity, canvasSize)

    animationRef.current = requestAnimationFrame(animate)
  }, [canvasSize, externalIntensity, getPhaseAndIntensity, regenerateBolts, lockAtPeak])

  const animateReduced = useCallback(() => {
    if (!canvasRef.current) return

    const ctx = canvasRef.current.getContext('2d')
    if (!ctx) return

    renderReducedMotion(ctx, canvasSize)

    setTimeout(() => {
      ctx.clearRect(0, 0, canvasSize, canvasSize)
      onPhaseChangeRef.current?.('complete')
      onCompleteRef.current?.()
    }, 200)
  }, [canvasSize])

  useEffect(() => {
    if (isActive) {
      startTimeRef.current = null
      phaseRef.current = 'idle'
      lastBoltUpdateRef.current = 0
      boltsRef.current = []

      if (prefersReducedMotion) {
        animateReduced()
      } else {
        onPhaseChangeRef.current?.('build')
        animationRef.current = requestAnimationFrame(animate)
      }
    } else {
      if (animationRef.current) {
        cancelAnimationFrame(animationRef.current)
        animationRef.current = null
      }

      if (canvasRef.current) {
        const ctx = canvasRef.current.getContext('2d')
        if (ctx) {
          ctx.clearRect(0, 0, canvasSize, canvasSize)
        }
      }
    }

    return () => {
      if (animationRef.current) {
        cancelAnimationFrame(animationRef.current)
        animationRef.current = null
      }
    }
  }, [isActive, animate, animateReduced, canvasSize, prefersReducedMotion])

  const responsiveSize = 'calc(min(100%, 100vh - 40px) * 0.78)'

  return (
    <div
      className="electricity-effect-container"
      style={{
        position: 'absolute',
        top: '50%',
        left: '50%',
        transform: 'translate(-50%, -50%)',
        width: responsiveSize,
        height: responsiveSize,
        pointerEvents: 'none',
        zIndex: 27,
        borderRadius: '50%',
      }}
      aria-hidden="true"
    >
      <canvas
        ref={canvasRef}
        width={canvasSize}
        height={canvasSize}
        style={{
          width: '100%',
          height: '100%',
          borderRadius: '50%',
        }}
      />
    </div>
  )
}

export default ElectricityAnimation
