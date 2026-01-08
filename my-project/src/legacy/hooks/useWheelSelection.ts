/**
 * useWheelSelection - Manages prompt selection and topic loading
 *
 * Handles the prompts displayed on the wheel, selection state, and loading new topics.
 */

import { useState, useRef, useCallback, useEffect } from 'react';
import type { AnimationPhase, Particle } from '../types';
import { ALL_PROMPTS, ELECTRICITY_CONFIG } from '../constants';
import { shuffleArray } from '../utils';

export interface UseWheelSelectionOptions {
  /** Whether test mode is enabled (uses specific test batch) */
  testMode?: boolean;
  /** Callback when electricity effect should start */
  onElectricityStart?: () => void;
  /** Callback when electricity effect should end */
  onElectricityEnd?: () => void;
}

export interface UseWheelSelectionReturn {
  // Prompt state
  prompts: string[];
  selectedPrompt: string | null;
  spinCount: number;

  // Animation state
  animPhase: AnimationPhase;
  particles: Particle[];
  showReassembledPanel: boolean;

  // Refs
  promptsRef: React.MutableRefObject<string[]>;
  usedPromptsRef: React.MutableRefObject<Set<string>>;

  // Actions
  setPrompts: React.Dispatch<React.SetStateAction<string[]>>;
  setSelectedPrompt: React.Dispatch<React.SetStateAction<string | null>>;
  setSpinCount: React.Dispatch<React.SetStateAction<number>>;
  setAnimPhase: React.Dispatch<React.SetStateAction<AnimationPhase>>;
  setParticles: React.Dispatch<React.SetStateAction<Particle[]>>;
  setShowReassembledPanel: React.Dispatch<React.SetStateAction<boolean>>;
  loadNewTopics: () => void;
  selectPrompt: (index: number) => void;
  clearSelection: () => void;
}

// Get all prompts with 24+ characters for testing
const LONG_PROMPTS = ALL_PROMPTS.filter((p) => p.length >= 24);
// TEST BATCH 2: Next 20 long prompts (index 20-39)
const TEST_BATCH_2 = LONG_PROMPTS.slice(20, 40);

/**
 * Wheel selection hook for prompt management
 */
export function useWheelSelection(options: UseWheelSelectionOptions = {}): UseWheelSelectionReturn {
  const { testMode = false, onElectricityStart, onElectricityEnd } = options;

  // Prompt state
  const [prompts, setPrompts] = useState<string[]>(testMode ? TEST_BATCH_2 : shuffleArray(ALL_PROMPTS));
  const [selectedPrompt, setSelectedPrompt] = useState<string | null>(null);
  const [spinCount, setSpinCount] = useState(0);

  // Animation state
  const [animPhase, setAnimPhase] = useState<AnimationPhase>(null);
  const [particles, setParticles] = useState<Particle[]>([]);
  const [showReassembledPanel, setShowReassembledPanel] = useState(false);

  // Refs
  const promptsRef = useRef<string[]>(prompts.slice(0, 20));
  const usedPromptsRef = useRef<Set<string>>(new Set(prompts.slice(0, 20)));
  const recentLandingsRef = useRef<number[]>([]);

  // Keep promptsRef in sync
  useEffect(() => {
    promptsRef.current = prompts.slice(0, 20);
  }, [prompts]);

  // Load new topics - picks 20 unused prompts, resets if all used
  const loadNewTopics = useCallback(() => {
    // Trigger electricity effect
    onElectricityStart?.();

    // Delay the actual topic swap so electricity effect can play
    setTimeout(() => {
      const currentOnWheel = new Set(prompts.slice(0, 20));
      const availablePrompts = ALL_PROMPTS.filter(
        (p) => !currentOnWheel.has(p) && !usedPromptsRef.current.has(p)
      );

      let newPrompts: string[];
      if (availablePrompts.length >= 20) {
        // Shuffle available and take 20
        const shuffled = shuffleArray(availablePrompts);
        newPrompts = shuffled.slice(0, 20);
      } else if (availablePrompts.length > 0) {
        // Use all available + fill from unused in current set
        const shuffledAvailable = shuffleArray(availablePrompts);
        const needed = 20 - shuffledAvailable.length;
        // Reset used tracking and pull from full list
        usedPromptsRef.current = new Set();
        const remaining = ALL_PROMPTS.filter((p) => !new Set(shuffledAvailable).has(p));
        const shuffledRemaining = shuffleArray(remaining);
        newPrompts = [...shuffledAvailable, ...shuffledRemaining.slice(0, needed)];
      } else {
        // All prompts used - reset and shuffle fresh
        usedPromptsRef.current = new Set();
        const shuffled = shuffleArray(ALL_PROMPTS);
        newPrompts = shuffled.slice(0, 20);
      }

      // Track these as used
      newPrompts.forEach((p) => usedPromptsRef.current.add(p));

      // Put remaining prompts after the first 20 for future loading
      const rest = shuffleArray(ALL_PROMPTS.filter((p) => !new Set(newPrompts).has(p)));
      setPrompts([...newPrompts, ...rest]);

      // Clear selection when loading new topics
      setSelectedPrompt(null);
      setAnimPhase(null);
      setShowReassembledPanel(false);
      setParticles([]);

      // Reset tracking for new set
      recentLandingsRef.current = [];
    }, ELECTRICITY_CONFIG.topicSwapDelayMs);

    // End electricity effect after full animation
    setTimeout(() => {
      onElectricityEnd?.();
    }, ELECTRICITY_CONFIG.effectDurationMs);
  }, [prompts, onElectricityStart, onElectricityEnd]);

  // Select a prompt by index
  const selectPrompt = useCallback(
    (index: number) => {
      const prompt = promptsRef.current[index];
      if (prompt) {
        setSelectedPrompt(prompt);
        setSpinCount((c) => c + 1);
      }
    },
    []
  );

  // Clear current selection
  const clearSelection = useCallback(() => {
    setSelectedPrompt(null);
    setAnimPhase(null);
    setShowReassembledPanel(false);
    setParticles([]);
  }, []);

  return {
    // State
    prompts,
    selectedPrompt,
    spinCount,
    animPhase,
    particles,
    showReassembledPanel,

    // Refs
    promptsRef,
    usedPromptsRef,

    // Actions
    setPrompts,
    setSelectedPrompt,
    setSpinCount,
    setAnimPhase,
    setParticles,
    setShowReassembledPanel,
    loadNewTopics,
    selectPrompt,
    clearSelection,
  };
}
