/**
 * SteamField Component
 * 
 * Creates the atmospheric steam background using CSS layers.
 * 
 * CRITICAL: Uses colors from SmokeEffect.tsx (warm brown/tan), NOT amber.
 * The original spec incorrectly specified amber colors - this was corrected.
 * 
 * REFERENCES:
 * - SmokeEffect.tsx for color palette
 * - animations.css for keyframes
 * - Z-index: 1002-1003 (above backdrop, below content)
 * 
 * Color palette (from SmokeEffect.tsx):
 * - Main: rgba(140, 120, 100, X) - warm brown
 * - Secondary: rgba(130, 110, 90, X) - tan
 * - Tertiary: rgba(120, 100, 80, X) - darker brown
 */

import { useMemo } from 'react';
import styles from './SteamField.module.css';

interface SteamFieldProps {
  isOpen: boolean;
  density?: 'light' | 'medium' | 'dense';
}

export function SteamField({ isOpen, density = 'medium' }: SteamFieldProps) {
  // Generate unique animation delays for organic feel
  // Memoized to prevent re-randomization on re-renders
  const delays = useMemo(() => ({
    baseCloud: Math.random() * -4,
    wispLeft: Math.random() * -6,
    wispRight: Math.random() * -8,
    risingUpper: Math.random() * -3,
    puffA: Math.random() * -2,
    puffB: Math.random() * -4,
  }), []);

  if (!isOpen) return null;

  const densityClass = styles[`density_${density}`] || '';

  return (
    <div 
      className={`${styles.steamField} ${densityClass}`}
      aria-hidden="true"
    >
      {/* Layer 1: Base Cloud (center) */}
      <div 
        className={styles.baseCloud}
        style={{ animationDelay: `${delays.baseCloud}s` }}
      />
      
      {/* Layer 2: Wisp Left */}
      <div 
        className={styles.wispLeft}
        style={{ animationDelay: `${delays.wispLeft}s` }}
      />
      
      {/* Layer 3: Wisp Right */}
      <div 
        className={styles.wispRight}
        style={{ animationDelay: `${delays.wispRight}s` }}
      />
      
      {/* Layer 4: Rising Steam */}
      <div 
        className={styles.risingUpper}
        style={{ animationDelay: `${delays.risingUpper}s` }}
      />
      
      {/* Layer 5-6: Accent Puffs */}
      <div 
        className={styles.puffA}
        style={{ animationDelay: `${delays.puffA}s` }}
      />
      <div 
        className={styles.puffB}
        style={{ animationDelay: `${delays.puffB}s` }}
      />
    </div>
  );
}
