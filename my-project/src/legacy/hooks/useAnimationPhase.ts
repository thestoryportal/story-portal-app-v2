/**
 * useAnimationPhase - Manages the prompt selection animation sequence
 *
 * Handles the warp → hold → disintegrate → reassemble → complete animation flow.
 */

import { useState, useEffect, useCallback } from 'react';
import type { AnimationPhase, Particle, Sparkle } from '../types';

export interface UseAnimationPhaseReturn {
  animPhase: AnimationPhase;
  particles: Particle[];
  showReassembledPanel: boolean;
  reassembleSparkles: Sparkle[];
  descendY: number;
  setAnimPhase: React.Dispatch<React.SetStateAction<AnimationPhase>>;
  setShowReassembledPanel: React.Dispatch<React.SetStateAction<boolean>>;
  setParticles: React.Dispatch<React.SetStateAction<Particle[]>>;
  setReassembleSparkles: React.Dispatch<React.SetStateAction<Sparkle[]>>;
  setDescendY: React.Dispatch<React.SetStateAction<number>>;
  resetAnimation: () => void;
}

/**
 * Generate particles for disintegration effect
 */
function generateParticles(): Particle[] {
  const particles: Particle[] = [];
  const numParticles = 60;

  for (let i = 0; i < numParticles; i++) {
    const angle = Math.random() * Math.PI * 2;
    const distance = 100 + Math.random() * 200;
    const size = 3 + Math.random() * 8;
    const delay = Math.random() * 1.5;

    particles.push({
      id: i,
      x: (Math.random() - 0.5) * 200,
      y: (Math.random() - 0.5) * 60,
      px: Math.cos(angle) * distance,
      py: Math.sin(angle) * distance - 50,
      size,
      delay,
      duration: 1.5 + Math.random() * 1.5,
    });
  }

  return particles;
}

/**
 * Generate sparkles for reassembly effect
 */
function generateSparkles(): Sparkle[] {
  const sparkles: Sparkle[] = [];

  for (let i = 0; i < 30; i++) {
    sparkles.push({
      id: i,
      x: Math.random() * 100,
      y: Math.random() * 100,
      delay: Math.random() * 1.5,
      size: 2 + Math.random() * 4,
    });
  }

  return sparkles;
}

export function useAnimationPhase(): UseAnimationPhaseReturn {
  const [animPhase, setAnimPhase] = useState<AnimationPhase>(null);
  const [particles, setParticles] = useState<Particle[]>([]);
  const [showReassembledPanel, setShowReassembledPanel] = useState(false);
  const [reassembleSparkles, setReassembleSparkles] = useState<Sparkle[]>([]);
  const [descendY, setDescendY] = useState(0);

  // Animation phase state machine
  useEffect(() => {
    if (animPhase === 'warp') {
      // Warp phase - 600ms
      const timer = setTimeout(() => setAnimPhase('hold'), 600);
      return () => clearTimeout(timer);
    } else if (animPhase === 'hold') {
      // Hold for 3 seconds
      const timer = setTimeout(() => {
        setParticles(generateParticles());
        setAnimPhase('disintegrate');
      }, 3000);
      return () => clearTimeout(timer);
    } else if (animPhase === 'disintegrate') {
      // Disintegrate for 3 seconds, then start reassembly
      const timer = setTimeout(() => {
        setReassembleSparkles(generateSparkles());
        setShowReassembledPanel(true);
        setAnimPhase('reassemble');
      }, 3000);
      return () => clearTimeout(timer);
    } else if (animPhase === 'reassemble') {
      // Reassembly takes 1.5 seconds, then done
      const timer = setTimeout(() => {
        setAnimPhase('complete');
        setParticles([]);
        setReassembleSparkles([]);
      }, 1500);
      return () => clearTimeout(timer);
    }
  }, [animPhase]);

  // Reset all animation state
  const resetAnimation = useCallback(() => {
    setAnimPhase(null);
    setParticles([]);
    setShowReassembledPanel(false);
    setReassembleSparkles([]);
    setDescendY(0);
  }, []);

  return {
    animPhase,
    particles,
    showReassembledPanel,
    reassembleSparkles,
    descendY,
    setAnimPhase,
    setShowReassembledPanel,
    setParticles,
    setReassembleSparkles,
    setDescendY,
    resetAnimation,
  };
}
