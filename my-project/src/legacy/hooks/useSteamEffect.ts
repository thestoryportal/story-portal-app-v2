/**
 * useSteamEffect - Manages persistent steam wisp particles
 *
 * Spawns steam wisps at configured vent locations that animate and disappear.
 */

import { useState, useEffect, useRef } from 'react';
import type { SteamWisp } from '../types';
import { STEAM_LOCATIONS } from '../constants';

export interface UseSteamEffectReturn {
  steamWisps: SteamWisp[];
}

export function useSteamEffect(): UseSteamEffectReturn {
  const [steamWisps, setSteamWisps] = useState<SteamWisp[]>([]);
  const steamIdRef = useRef(0);

  useEffect(() => {
    const spawnSteam = () => {
      // Pick a random location
      const loc = STEAM_LOCATIONS[Math.floor(Math.random() * STEAM_LOCATIONS.length)];
      // Destructure to exclude the string id from SteamLocation
      // eslint-disable-next-line @typescript-eslint/no-unused-vars
      const { id: _locationId, ...locPosition } = loc;
      const id = steamIdRef.current++;
      const duration = 3800 + Math.random() * 2000;
      const animOptions: SteamWisp['animation'][] = [
        'steamStream',
        'steamStreamDrift',
        'steamStreamDriftLeft',
      ];
      const animation = animOptions[Math.floor(Math.random() * animOptions.length)];

      // Add slight position variation
      const offsetX = (Math.random() - 0.5) * 14;
      const offsetY = (Math.random() - 0.5) * 8;

      const newWisp: SteamWisp = {
        id,
        ...locPosition,
        offsetX,
        offsetY,
        duration,
        animation,
        size: 70 + Math.random() * 50,
        createdAt: Date.now(),
      };

      setSteamWisps((prev) => [...prev, newWisp]);

      // Remove wisp after animation completes
      setTimeout(() => {
        setSteamWisps((prev) => prev.filter((w) => w.id !== id));
      }, duration + 100);
    };

    // Spawn initial batch - thick coverage across all vents
    for (let i = 0; i < 40; i++) {
      setTimeout(() => spawnSteam(), i * 100 + Math.random() * 120);
    }

    // Continue spawning very frequently for persistent thick steam
    let continueSpawning = true;
    const spawnWithRandomDelay = () => {
      if (!continueSpawning) return;
      spawnSteam();
      const nextDelay = 120 + Math.random() * 230; // 120-350ms between spawns
      setTimeout(spawnWithRandomDelay, nextDelay);
    };

    // Start the random spawning after initial batch
    const startTimeout = setTimeout(spawnWithRandomDelay, 3000);

    return () => {
      continueSpawning = false;
      clearTimeout(startTimeout);
    };
  }, []);

  return { steamWisps };
}
