/**
 * useMenuState - Manages hamburger menu state and animations
 *
 * Handles menu open/close, animation phases, smoke effects, and panel sway.
 */

import { useState, useRef, useCallback } from 'react';
import type { HamburgerAnimPhase, MenuState } from '../types';

export interface UseMenuStateReturn extends MenuState {
  toggleMenu: () => void;
  closeMenu: () => void;
  handlePanelClick: (panelIndex: number) => void;
  setSwayingFromPanel: (panel: number | null) => void;
  hamburgerAnimatingRef: React.MutableRefObject<boolean>;
  smokeTimeoutRef: React.MutableRefObject<ReturnType<typeof setTimeout> | null>;
  smokeDelayTimeoutRef: React.MutableRefObject<ReturnType<typeof setTimeout> | null>;
  logoTimeoutRef: React.MutableRefObject<ReturnType<typeof setTimeout> | null>;
  setMenuOpen: React.Dispatch<React.SetStateAction<boolean>>;
  setMenuHasBeenOpened: React.Dispatch<React.SetStateAction<boolean>>;
  setHamburgerAnimPhase: React.Dispatch<React.SetStateAction<HamburgerAnimPhase>>;
  setShowSmokePoof: React.Dispatch<React.SetStateAction<boolean>>;
  setSmokeAnimKey: React.Dispatch<React.SetStateAction<number>>;
  setSwayAnimKey: React.Dispatch<React.SetStateAction<number>>;
  setShowMenuLogo: React.Dispatch<React.SetStateAction<boolean>>;
}

export function useMenuState(): UseMenuStateReturn {
  // Menu state
  const [menuOpen, setMenuOpen] = useState(false);
  const [menuHasBeenOpened, setMenuHasBeenOpened] = useState(false);
  const [showSmokePoof, setShowSmokePoof] = useState(false);
  const [smokeAnimKey, setSmokeAnimKey] = useState(0);
  const [hamburgerAnimPhase, setHamburgerAnimPhase] = useState<HamburgerAnimPhase>(null);
  const [swayingFromPanel, setSwayingFromPanelState] = useState<number | null>(null);
  const [swayAnimKey, setSwayAnimKey] = useState(0);
  const [showMenuLogo, setShowMenuLogo] = useState(false);

  // Refs for animation control
  const hamburgerAnimatingRef = useRef(false);
  const smokeTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const smokeDelayTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const logoTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Toggle menu with animation sequence
  const toggleMenu = useCallback(() => {
    if (hamburgerAnimatingRef.current) return;

    hamburgerAnimatingRef.current = true;

    // Clear any existing timeouts
    if (smokeTimeoutRef.current) clearTimeout(smokeTimeoutRef.current);
    if (smokeDelayTimeoutRef.current) clearTimeout(smokeDelayTimeoutRef.current);
    if (logoTimeoutRef.current) clearTimeout(logoTimeoutRef.current);

    if (!menuOpen) {
      // Opening sequence
      setMenuHasBeenOpened(true);

      // Phase 1: Extrude (bars grow depth)
      setHamburgerAnimPhase('opening-extrude');

      setTimeout(() => {
        // Phase 2: Collapse to dot
        setHamburgerAnimPhase('opening-collapse');

        setTimeout(() => {
          // Phase 3: Spin and morph to X
          setHamburgerAnimPhase('opening-spin-to-x');

          setTimeout(() => {
            // Phase 4: X lifts
            setHamburgerAnimPhase('opening-x-lifted');

            setTimeout(() => {
              // Phase 5: Engrave
              setHamburgerAnimPhase('opening-engrave');
              setMenuOpen(true);

              // Show logo after menu opens
              logoTimeoutRef.current = setTimeout(() => {
                setShowMenuLogo(true);
              }, 400);

              hamburgerAnimatingRef.current = false;
            }, 150);
          }, 200);
        }, 200);
      }, 150);

      // Trigger smoke poof just before panels start to unfold (~700ms)
      smokeDelayTimeoutRef.current = setTimeout(() => {
        setSmokeAnimKey((k) => k + 1);
        setShowSmokePoof(true);
        smokeTimeoutRef.current = setTimeout(() => {
          setShowSmokePoof(false);
        }, 3500);
      }, 650);
    } else {
      // Closing sequence
      setShowMenuLogo(false);

      // Phase 1: Extrude X
      setHamburgerAnimPhase('closing-extrude');

      setTimeout(() => {
        // Phase 2: Spin back to lines
        setHamburgerAnimPhase('closing-spin-to-line');

        setTimeout(() => {
          // Phase 3: Expand
          setHamburgerAnimPhase('closing-expand');

          setTimeout(() => {
            // Phase 4: Engrave
            setHamburgerAnimPhase('closing-engrave');
            setMenuOpen(false);

            setTimeout(() => {
              setHamburgerAnimPhase(null);
              hamburgerAnimatingRef.current = false;
            }, 150);
          }, 150);
        }, 200);
      }, 150);

      // Trigger smoke poof when menu panels land back down (1150ms delay)
      smokeDelayTimeoutRef.current = setTimeout(() => {
        setSmokeAnimKey((k) => k + 1);
        setShowSmokePoof(true);
        smokeTimeoutRef.current = setTimeout(() => {
          setShowSmokePoof(false);
        }, 3500);
      }, 1150);
    }
  }, [menuOpen]);

  const setSwayingFromPanel = useCallback((panel: number | null) => {
    setSwayingFromPanelState(panel);
    if (panel !== null) {
      setSwayAnimKey((k) => k + 1);
    }
  }, []);

  // Close menu (wrapper around toggleMenu when menu is open)
  const closeMenu = useCallback(() => {
    if (menuOpen && !hamburgerAnimatingRef.current) {
      toggleMenu();
    }
  }, [menuOpen, toggleMenu]);

  // Handle panel click - triggers sway animation
  const handlePanelClick = useCallback((panelIndex: number) => {
    setSwayingFromPanel(panelIndex);
  }, [setSwayingFromPanel]);

  return {
    // State
    menuOpen,
    menuHasBeenOpened,
    hamburgerAnimPhase,
    showSmokePoof,
    smokeAnimKey,
    swayingFromPanel,
    swayAnimKey,
    showMenuLogo,

    // Actions
    toggleMenu,
    closeMenu,
    handlePanelClick,
    setSwayingFromPanel,

    // Refs
    hamburgerAnimatingRef,
    smokeTimeoutRef,
    smokeDelayTimeoutRef,
    logoTimeoutRef,

    // Setters (for external control)
    setMenuOpen,
    setMenuHasBeenOpened,
    setHamburgerAnimPhase,
    setShowSmokePoof,
    setSmokeAnimKey,
    setSwayAnimKey,
    setShowMenuLogo,
  };
}
