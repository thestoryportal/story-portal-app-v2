/**
 * NavButtons Component
 *
 * How to Play and My Stories navigation buttons with extruded text effect.
 */

import { useState, type CSSProperties } from 'react'

// Default text effect configuration
const TEXT_EFFECT_CONFIG = {
  extrudeDepth: 8,
  extrudeMaxOffset: 3,
  extrudeOffsetX: 0.25,
  extrudeOffsetY: 1,
  extrudeBaseR: 40,
  extrudeBaseG: 25,
  extrudeBaseB: 8,
  extrudeStepR: 17,
  extrudeStepG: 4,
  extrudeStepB: 0,
  faceTopColor: '#f2dfc0',
  faceMidColor: '#e3bf7d',
  faceBottomColor: '#f18741',
  faceGradientMidStop: 45,
  highlightEnabled: true,
  highlightTopColor: '#e8d4b8',
  highlightTopOpacity: 0.8,
  highlightMidColor: '#d4b892',
  highlightMidOpacity: 0.25,
  highlightMidStop: 30,
  highlightBottomColor: '#8b7355',
  highlightBottomOpacity: 0.25,
  textShadowEnabled: true,
  textShadowOffsetX: 0,
  textShadowOffsetY: 2,
  textShadowBlur: 1.5,
  textShadowColor: '#1a1008',
  textShadowOpacity: 1,
  outerStrokeEnabled: true,
  outerStrokeColor: '#523e21',
  outerStrokeWidth: 2,
  textureOverlayEnabled: true,
  textureOverlayOpacity: 0.85,
  textureBlendMode: 'hard-light' as const,
  textureGradientEnabled: true,
  textureGradientType: 'horizontal' as const,
  textureGradientTopOpacity: 1,
  textureGradientMidOpacity: 0.7,
  textureGradientBottomOpacity: 0.25,
  textureGradientMidStop: 50,
}

// Generate extrusion layers
function generateExtrudeLayers() {
  const cfg = TEXT_EFFECT_CONFIG
  return Array.from({ length: cfg.extrudeDepth }, (_, i) => {
    const t = (cfg.extrudeDepth - 1 - i) / (cfg.extrudeDepth - 1)
    return {
      offsetX: cfg.extrudeMaxOffset * cfg.extrudeOffsetX * t,
      offsetY: cfg.extrudeMaxOffset * cfg.extrudeOffsetY * t,
      r: Math.min(255, cfg.extrudeBaseR + cfg.extrudeStepR * i),
      g: Math.min(255, cfg.extrudeBaseG + cfg.extrudeStepG * i),
      b: Math.min(255, cfg.extrudeBaseB + cfg.extrudeStepB * i),
    }
  })
}

const extrudeLayers = generateExtrudeLayers()

// Convert opacity to luminance grayscale for SVG masks
function opacityToGray(opacity: number): string {
  const val = Math.round(opacity * 255)
  return `rgb(${val}, ${val}, ${val})`
}

interface NavButtonProps {
  id: string
  label: string
  icon: string
  iconX: number
  textX: number
  textY: number
  onClick: () => void
  buttonShadowStyle: CSSProperties
}

function NavButton({
  id,
  label,
  icon,
  iconX,
  textX,
  textY,
  onClick,
  buttonShadowStyle,
}: NavButtonProps) {
  const [pressed, setPressed] = useState(false)
  const cfg = TEXT_EFFECT_CONFIG

  const pressedShadowStyle: CSSProperties = {
    filter: 'drop-shadow(-5px 4px 12px rgba(0,0,0,0.4))',
  }

  return (
    <div
      className="secondary-button"
      onClick={onClick}
      onMouseDown={() => setPressed(true)}
      onMouseUp={() => setPressed(false)}
      onMouseLeave={() => setPressed(false)}
      onTouchStart={() => setPressed(true)}
      onTouchEnd={() => setPressed(false)}
      style={{
        cursor: 'pointer',
        position: 'relative',
        userSelect: 'none',
        WebkitTapHighlightColor: 'transparent',
        width: '280px',
        height: '56px',
        transform: pressed ? 'translateY(2px)' : 'translateY(0)',
        ...(pressed ? pressedShadowStyle : buttonShadowStyle),
      }}
    >
      <div
        style={{
          position: 'absolute',
          top: 0,
          left: 0,
          width: '280px',
          height: '56px',
          zIndex: 3,
        }}
      >
        <svg
          viewBox="0 0 280 56"
          style={{
            width: '280px',
            height: '56px',
            display: 'block',
            overflow: 'visible',
          }}
        >
          <defs>
            {/* Texture pattern */}
            <pattern
              id={`metal-texture-${id}`}
              patternUnits="userSpaceOnUse"
              width="280"
              height="56"
            >
              <image
                href="/assets/images/story-portal-button-secondary.webp"
                width="280"
                height="56"
              />
            </pattern>

            {/* Face gradient */}
            <linearGradient id={`face-gradient-${id}`} x1="0%" y1="0%" x2="0%" y2="100%">
              <stop offset="0%" stopColor={cfg.faceTopColor} />
              <stop offset={`${cfg.faceGradientMidStop}%`} stopColor={cfg.faceMidColor} />
              <stop offset="100%" stopColor={cfg.faceBottomColor} />
            </linearGradient>

            {/* Bevel highlight */}
            <linearGradient id={`bevel-highlight-${id}`} x1="0%" y1="0%" x2="0%" y2="100%">
              <stop
                offset="0%"
                stopColor={cfg.highlightTopColor}
                stopOpacity={cfg.highlightTopOpacity}
              />
              <stop
                offset={`${cfg.highlightMidStop}%`}
                stopColor={cfg.highlightMidColor}
                stopOpacity={cfg.highlightMidOpacity}
              />
              <stop
                offset="100%"
                stopColor={cfg.highlightBottomColor}
                stopOpacity={cfg.highlightBottomOpacity}
              />
            </linearGradient>

            {/* Texture opacity gradient */}
            <linearGradient
              id={`texture-opacity-gradient-${id}`}
              gradientUnits="userSpaceOnUse"
              x1="0"
              y1="28"
              x2="280"
              y2="28"
            >
              <stop offset="0%" stopColor={opacityToGray(cfg.textureGradientTopOpacity)} />
              <stop
                offset={`${cfg.textureGradientMidStop}%`}
                stopColor={opacityToGray(cfg.textureGradientMidOpacity)}
              />
              <stop offset="100%" stopColor={opacityToGray(cfg.textureGradientBottomOpacity)} />
            </linearGradient>

            {/* Texture mask */}
            <mask
              id={`texture-mask-${id}`}
              maskUnits="userSpaceOnUse"
              x="0"
              y="0"
              width="280"
              height="56"
            >
              <rect
                x="0"
                y="0"
                width="280"
                height="56"
                fill={`url(#texture-opacity-gradient-${id})`}
              />
            </mask>

            {/* Shadow filter */}
            <filter id={`extrude-shadow-${id}`} x="-50%" y="-50%" width="200%" height="200%">
              <feDropShadow
                dx={cfg.textShadowOffsetX}
                dy={cfg.textShadowOffsetY}
                stdDeviation={cfg.textShadowBlur}
                floodColor={cfg.textShadowColor}
                floodOpacity={cfg.textShadowOpacity}
              />
            </filter>
          </defs>

          {/* Button base */}
          <image href="/assets/images/story-portal-button-secondary.webp" width="280" height="56" />

          {/* Extruded text layers */}
          <g transform="translate(140, 28)">
            {/* Extrusion layers - back to front */}
            {extrudeLayers.map((layer, i) => (
              <g
                key={`extrude-${id}-${i}`}
                transform={`translate(${layer.offsetX}, ${layer.offsetY})`}
              >
                <text
                  x={iconX}
                  y="0"
                  fill={`rgb(${layer.r}, ${layer.g}, ${layer.b})`}
                  stroke={cfg.outerStrokeEnabled && i === 0 ? cfg.outerStrokeColor : 'none'}
                  strokeWidth={cfg.outerStrokeEnabled && i === 0 ? cfg.outerStrokeWidth : 0}
                  fontFamily="Material Symbols Outlined"
                  fontSize="26"
                  dominantBaseline="central"
                  style={{ fontVariationSettings: "'FILL' 1, 'wght' 700" }}
                >
                  {icon}
                </text>
                <text
                  x={textX}
                  y={textY}
                  fill={`rgb(${layer.r}, ${layer.g}, ${layer.b})`}
                  stroke={cfg.outerStrokeEnabled && i === 0 ? cfg.outerStrokeColor : 'none'}
                  strokeWidth={cfg.outerStrokeEnabled && i === 0 ? cfg.outerStrokeWidth : 0}
                  fontFamily="Molly Sans, sans-serif"
                  fontSize="22"
                  dominantBaseline="central"
                  letterSpacing="1"
                >
                  {label}
                </text>
              </g>
            ))}

            {/* Front face with gradient */}
            <g filter={`url(#extrude-shadow-${id})`}>
              <text
                x={iconX}
                y="0"
                fill={`url(#face-gradient-${id})`}
                fontFamily="Material Symbols Outlined"
                fontSize="26"
                dominantBaseline="central"
                style={{ fontVariationSettings: "'FILL' 1, 'wght' 700" }}
              >
                {icon}
              </text>
              <text
                x={textX}
                y={textY}
                fill={`url(#face-gradient-${id})`}
                fontFamily="Molly Sans, sans-serif"
                fontSize="22"
                dominantBaseline="central"
                letterSpacing="1"
              >
                {label}
              </text>
            </g>

            {/* Highlight */}
            {cfg.highlightEnabled && (
              <g>
                <text
                  x={iconX}
                  y="0"
                  fill={`url(#bevel-highlight-${id})`}
                  fontFamily="Material Symbols Outlined"
                  fontSize="26"
                  dominantBaseline="central"
                  style={{ fontVariationSettings: "'FILL' 1, 'wght' 700" }}
                >
                  {icon}
                </text>
                <text
                  x={textX}
                  y={textY}
                  fill={`url(#bevel-highlight-${id})`}
                  fontFamily="Molly Sans, sans-serif"
                  fontSize="22"
                  dominantBaseline="central"
                  letterSpacing="1"
                >
                  {label}
                </text>
              </g>
            )}
          </g>

          {/* Texture overlay */}
          {cfg.textureOverlayEnabled && (
            <g
              opacity={cfg.textureOverlayOpacity}
              style={{ mixBlendMode: cfg.textureBlendMode }}
              mask={`url(#texture-mask-${id})`}
            >
              <text
                x={140 + iconX}
                y="28"
                fill={`url(#metal-texture-${id})`}
                fontFamily="Material Symbols Outlined"
                fontSize="26"
                dominantBaseline="central"
                style={{ fontVariationSettings: "'FILL' 1, 'wght' 700" }}
              >
                {icon}
              </text>
              <text
                x={140 + textX}
                y={28 + textY}
                fill={`url(#metal-texture-${id})`}
                fontFamily="Molly Sans, sans-serif"
                fontSize="22"
                dominantBaseline="central"
                letterSpacing="1"
              >
                {label}
              </text>
            </g>
          )}
        </svg>
      </div>
    </div>
  )
}

interface NavButtonsProps {
  onHowToPlay: () => void
  onMyStories: () => void
  onBook: () => void
  buttonShadowStyle: CSSProperties
}

export function NavButtons({
  onHowToPlay,
  onMyStories,
  onBook,
  buttonShadowStyle,
}: NavButtonsProps) {
  return (
    <div
      className="nav-buttons"
      style={{
        position: 'absolute',
        right: '140px',
        top: '34%',
        transform: 'translateY(-50%)',
        display: 'flex',
        flexDirection: 'column',
        gap: '15px',
      }}
    >
      <NavButton
        id="htp"
        label="HOW TO PLAY"
        icon="person_play"
        iconX={-91}
        textX={-58}
        textY={2}
        onClick={onHowToPlay}
        buttonShadowStyle={buttonShadowStyle}
      />
      <NavButton
        id="mys"
        label="MY STORIES"
        icon="web_stories"
        iconX={-84}
        textX={-49}
        textY={3}
        onClick={onMyStories}
        buttonShadowStyle={buttonShadowStyle}
      />
    </div>
  )
}
