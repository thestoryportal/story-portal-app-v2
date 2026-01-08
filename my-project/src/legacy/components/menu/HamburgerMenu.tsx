/**
 * HamburgerMenu Component
 *
 * Gear button with animated hamburger/X lines.
 */

import type { CSSProperties } from 'react';
import type { HamburgerAnimPhase } from '../../types';

interface HamburgerMenuProps {
  isOpen: boolean;
  animPhase: HamburgerAnimPhase;
  buttonShadowStyle: CSSProperties;
  onToggle: () => void;
}

export function HamburgerMenu({
  isOpen,
  animPhase,
  buttonShadowStyle,
  onToggle,
}: HamburgerMenuProps) {
  // Determine if currently animating (any non-null phase)
  const isAnimating = animPhase !== null;
  // Determine effect states (lifted/floating vs engraved)
  const isLifted = [
    'opening-extrude',
    'opening-collapse',
    'opening-spin-to-x',
    'opening-x-lifted',
    'closing-extrude',
    'closing-spin-to-line',
    'closing-expand',
  ].includes(animPhase as string);

  // During spin phases, use no filter to avoid two-line shading look
  const isSpinning = animPhase === 'opening-spin-to-x' || animPhase === 'closing-spin-to-line';
  const currentFilter = isSpinning
    ? 'none'
    : isLifted
      ? 'url(#hamburger-extruded-filter)'
      : 'url(#hamburger-engraved-filter)';
  const currentGradient = isLifted
    ? 'url(#hamburger-extruded-gradient)'
    : 'url(#hamburger-warm-gradient)';

  // Determine if we're in X shape vs hamburger shape
  const isXRotation =
    (isOpen && !animPhase) ||
    animPhase === 'opening-spin-to-x' ||
    animPhase === 'opening-x-lifted' ||
    animPhase === 'opening-engrave' ||
    animPhase === 'closing-extrude';

  // Determine if lines are collapsed to center vs spread out
  const isCollapsed =
    animPhase === 'opening-collapse' ||
    animPhase === 'opening-spin-to-x' ||
    animPhase === 'opening-x-lifted' ||
    animPhase === 'opening-engrave' ||
    animPhase === 'closing-extrude' ||
    animPhase === 'closing-spin-to-line' ||
    (isOpen && !animPhase);

  // When to show unified X path
  const showXPath =
    (isOpen && !animPhase) ||
    animPhase === 'opening-x-lifted' ||
    animPhase === 'opening-engrave' ||
    animPhase === 'closing-extrude';

  // Transition duration based on phase
  let transitionDuration = '0.25s';
  if (isSpinning) {
    transitionDuration = '0.35s';
  } else if (animPhase === 'opening-collapse' || animPhase === 'closing-expand') {
    transitionDuration = '0.22s';
  } else if (animPhase === 'opening-x-lifted') {
    transitionDuration = '0.15s';
  }

  // Line positions
  const line1TranslateY = isCollapsed ? 0 : -11.5;
  const line3TranslateY = isCollapsed ? 0 : 11.5;

  // Rotations
  const line1Rotation = isXRotation ? 45 : 360;
  const line3Rotation = isXRotation ? -45 : 360;

  // Middle line opacity
  const line2Opacity = isCollapsed ? 0 : 1;

  // Line dimensions
  const lineHeight = 8;
  const lineWidth = 30;

  // Scale for "flying toward viewer" effect
  const liftScale = isLifted ? 1.35 : 1;

  // Shadow offset
  const shadowOffsetX = isLifted ? 3 : 0;
  const shadowOffsetY = isLifted ? 6 : 0;

  // X path
  const xPath =
    'M -7.78,-13.44 L 0,-5.66 L 7.78,-13.44 L 13.44,-7.78 L 5.66,0 L 13.44,7.78 L 7.78,13.44 L 0,5.66 L -7.78,13.44 L -13.44,7.78 L -5.66,0 L -13.44,-7.78 Z';

  return (
    <div
      className="nav-buttons hamburger-menu-button"
      onClick={onToggle}
      style={{
        position: 'absolute',
        right: 'calc(170px)',
        top: 'calc(34% - 195px)',
        cursor: isAnimating ? 'default' : 'pointer',
        userSelect: 'none',
        WebkitTapHighlightColor: 'transparent',
        width: '80px',
        height: '80px',
        ...buttonShadowStyle,
        zIndex: 1000,
      }}
    >
      {/* Gear background with rotation animation */}
      <img
        src="/assets/images/story-portal-app-hamburger-menu-gear.webp"
        alt="Menu"
        draggable="false"
        style={{
          width: '100%',
          height: '100%',
          objectFit: 'contain',
          pointerEvents: 'none',
          animation: [
            'opening-extrude',
            'opening-collapse',
            'opening-spin-to-x',
            'opening-x-lifted',
          ].includes(animPhase as string)
            ? 'gearSpinClockwise 0.75s ease-in-out forwards'
            : ['closing-extrude', 'closing-spin-to-line', 'closing-expand'].includes(
                  animPhase as string
                )
              ? 'gearSpinCounterClockwise 0.75s ease-in-out forwards'
              : 'none',
        }}
      />

      {/* Hamburger/X lines using SVG */}
      <svg
        viewBox="0 0 80 80"
        style={{
          position: 'absolute',
          top: 0,
          left: 0,
          width: '100%',
          height: '100%',
          pointerEvents: 'none',
          overflow: 'visible',
        }}
      >
        <defs>
          {/* Warm gradient for engraved state */}
          <linearGradient id="hamburger-warm-gradient" x1="0%" y1="0%" x2="0%" y2="100%">
            <stop offset="0%" stopColor="#4a3520" />
            <stop offset="15%" stopColor="#6a4a28" />
            <stop offset="30%" stopColor="#8a6535" />
            <stop offset="50%" stopColor="#b8863c" />
            <stop offset="70%" stopColor="#d4a045" />
            <stop offset="85%" stopColor="#c89038" />
            <stop offset="100%" stopColor="#a87030" />
          </linearGradient>

          {/* Brighter gradient for extruded state */}
          <linearGradient id="hamburger-extruded-gradient" x1="0%" y1="0%" x2="0%" y2="100%">
            <stop offset="0%" stopColor="#9a7540" />
            <stop offset="20%" stopColor="#c8964a" />
            <stop offset="50%" stopColor="#e4b050" />
            <stop offset="80%" stopColor="#f0c858" />
            <stop offset="100%" stopColor="#d8a048" />
          </linearGradient>

          {/* Engraved filter */}
          <filter id="hamburger-engraved-filter" x="-50%" y="-50%" width="200%" height="200%">
            <feTurbulence
              type="fractalNoise"
              baseFrequency="1.2"
              numOctaves="4"
              seed="12"
              result="noise"
            />
            <feColorMatrix
              type="matrix"
              in="noise"
              result="metalNoise"
              values="0.3 0 0 0 0
                      0.28 0 0 0 0
                      0.2 0 0 0 0
                      0 0 0 0.5 0"
            />
            <feComposite in="metalNoise" in2="SourceGraphic" operator="in" result="clippedNoise" />
            <feBlend
              in="SourceGraphic"
              in2="clippedNoise"
              mode="multiply"
              result="texturedShape"
            />
            <feOffset dx="0" dy="1.3" in="SourceAlpha" result="shadowOffset" />
            <feGaussianBlur stdDeviation="0.4" in="shadowOffset" result="shadowBlur" />
            <feComposite
              in="shadowBlur"
              in2="SourceAlpha"
              operator="arithmetic"
              k2="-1"
              k3="1"
              result="shadowCutout"
            />
            <feFlood floodColor="rgba(10, 5, 0, 0.9)" result="shadowColor" />
            <feComposite in="shadowColor" in2="shadowCutout" operator="in" result="innerShadow" />
            <feOffset dx="0" dy="-1" in="SourceAlpha" result="highlightOffset" />
            <feGaussianBlur stdDeviation="0.25" in="highlightOffset" result="highlightBlur" />
            <feComposite
              in="highlightBlur"
              in2="SourceAlpha"
              operator="arithmetic"
              k2="-1"
              k3="1"
              result="highlightCutout"
            />
            <feFlood floodColor="rgba(220, 200, 160, 0.7)" result="highlightColor" />
            <feComposite
              in="highlightColor"
              in2="highlightCutout"
              operator="in"
              result="innerHighlight"
            />
            <feMerge>
              <feMergeNode in="texturedShape" />
              <feMergeNode in="innerShadow" />
              <feMergeNode in="innerHighlight" />
            </feMerge>
          </filter>

          {/* Extruded filter */}
          <filter id="hamburger-extruded-filter" x="-50%" y="-50%" width="200%" height="200%">
            <feDropShadow dx="0" dy="0" stdDeviation="0.5" floodColor="rgba(255,220,150,0.3)" />
          </filter>

          {/* Shadow filter */}
          <filter id="hamburger-shadow-filter" x="-100%" y="-100%" width="300%" height="300%">
            <feGaussianBlur stdDeviation="4" result="blur" />
            <feFlood floodColor="rgba(0,0,0,0.6)" result="shadowColor" />
            <feComposite in="shadowColor" in2="blur" operator="in" />
          </filter>
        </defs>

        {/* Animated lines container */}
        <g style={{ transform: 'translate(40px, 40px)' }}>
          {/* SHADOW LAYER */}
          <g
            style={{
              opacity: isLifted && !isSpinning ? 0.5 : 0,
              transition: 'opacity 0.2s ease-out, transform 0.2s ease-out',
              transform: `translate(${shadowOffsetX}px, ${shadowOffsetY}px)`,
            }}
          >
            {showXPath ? (
              <path d={xPath} fill="rgba(0,0,0,0.8)" filter="url(#hamburger-shadow-filter)" />
            ) : (
              <>
                <rect
                  x={-lineWidth / 2}
                  y={-lineHeight / 2}
                  width={lineWidth}
                  height={lineHeight}
                  fill="rgba(0,0,0,0.8)"
                  filter="url(#hamburger-shadow-filter)"
                  style={{
                    transition: `transform ${transitionDuration} ease-in-out`,
                    transform: `translateY(${line1TranslateY}px) rotate(${line1Rotation}deg)`,
                    transformOrigin: 'center center',
                    transformBox: 'fill-box',
                  }}
                />
                <rect
                  x={-lineWidth / 2}
                  y={-lineHeight / 2}
                  width={lineWidth}
                  height={lineHeight}
                  fill="rgba(0,0,0,0.8)"
                  filter="url(#hamburger-shadow-filter)"
                  style={{
                    transition: `opacity ${transitionDuration} ease-in-out`,
                    opacity: line2Opacity,
                  }}
                />
                <rect
                  x={-lineWidth / 2}
                  y={-lineHeight / 2}
                  width={lineWidth}
                  height={lineHeight}
                  fill="rgba(0,0,0,0.8)"
                  filter="url(#hamburger-shadow-filter)"
                  style={{
                    transition: `transform ${transitionDuration} ease-in-out`,
                    transform: `translateY(${line3TranslateY}px) rotate(${line3Rotation}deg)`,
                    transformOrigin: 'center center',
                    transformBox: 'fill-box',
                  }}
                />
              </>
            )}
          </g>

          {/* MAIN LINES */}
          <g
            style={{
              transform: `scale(${liftScale})`,
              transition: 'transform 0.2s ease-out',
            }}
          >
            {/* Unified X path */}
            <path
              d={xPath}
              fill={currentGradient}
              filter={currentFilter}
              style={{
                opacity: showXPath ? 1 : 0,
                transition: 'opacity 0.05s ease-in-out',
              }}
            />

            {/* Rects for hamburger states */}
            <g style={{ opacity: showXPath ? 0 : 1, transition: 'opacity 0.05s ease-in-out' }}>
              <rect
                x={-lineWidth / 2}
                y={-lineHeight / 2}
                width={lineWidth}
                height={lineHeight}
                fill={currentGradient}
                filter={currentFilter}
                style={{
                  transition: `transform ${transitionDuration} ease-in-out`,
                  transform: `translateY(${line1TranslateY}px) rotate(${line1Rotation}deg)`,
                  transformOrigin: 'center center',
                  transformBox: 'fill-box',
                }}
              />
              <rect
                x={-lineWidth / 2}
                y={-lineHeight / 2}
                width={lineWidth}
                height={lineHeight}
                fill={currentGradient}
                filter={currentFilter}
                style={{
                  transition: `opacity ${transitionDuration} ease-in-out`,
                  opacity: line2Opacity,
                }}
              />
              <rect
                x={-lineWidth / 2}
                y={-lineHeight / 2}
                width={lineWidth}
                height={lineHeight}
                fill={currentGradient}
                filter={currentFilter}
                style={{
                  transition: `transform ${transitionDuration} ease-in-out`,
                  transform: `translateY(${line3TranslateY}px) rotate(${line3Rotation}deg)`,
                  transformOrigin: 'center center',
                  transformBox: 'fill-box',
                }}
              />
            </g>
          </g>
        </g>
      </svg>
    </div>
  );
}
