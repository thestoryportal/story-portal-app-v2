/**
 * SteamField Component
 *
 * Creates the atmospheric steam background using layered radial gradients.
 *
 * NEW DESIGN APPROACH:
 * - Multi-layered radial gradients (lightest cream at center, darker brown outward)
 * - Constantly drifting subtle movement
 * - Content floats directly on steam (steam IS the background)
 * - Three-phase entrance: burst → settle → constant drift
 *
 * Color Strategy:
 * - Center: Warm cream/parchment (lightest, where text sits)
 * - Mid: Warm tan transitional tones
 * - Outer: Darker brown atmospheric edges
 *
 * Z-index: 1002-1005 (above backdrop, below content)
 */

import { useMemo } from 'react';
import styles from './SteamField.module.css';

interface SteamFieldProps {
  isOpen: boolean;
  density?: 'light' | 'medium' | 'dense';
}

export function SteamField({ isOpen, density = 'medium' }: SteamFieldProps) {
  // Generate unique animation delays for organic feel
  const delays = useMemo(() => ({
    base: Math.random() * -10,
    mid: Math.random() * -8,
    outer: Math.random() * -6,
    accent: Math.random() * -4,
  }), []);

  if (!isOpen) return null;

  const densityClass = styles[`density_${density}`] || '';

  // No opacity changes based on scroll - steam remains constant
  return (
    <div
      className={`${styles.steamField} ${densityClass}`}
      aria-hidden="true"
    >
      {/* Burst effect - appears on modal open, then fades */}
      <div className={styles.burstEffect} />

      {/* Base Layer - Largest, slowest drift */}
      <div
        className={styles.radialBase}
        style={{ animationDelay: `${delays.base}s` }}
      />

      {/* Mid Layer - Medium size, moderate drift */}
      <div
        className={styles.radialMid}
        style={{ animationDelay: `${delays.mid}s` }}
      />

      {/* Outer Layer - Transparent edge wisps */}
      <div
        className={styles.radialOuter}
        style={{ animationDelay: `${delays.outer}s` }}
      />

      {/* Accent Layer - Chaotic organic wisps */}
      <div
        className={styles.accentWisps}
        style={{ animationDelay: `${delays.accent}s` }}
      />

      {/* Clearing Layer - Dense steam that clears to reveal content */}
      <div className={styles.clearingLayer} />
    </div>
  );
}
