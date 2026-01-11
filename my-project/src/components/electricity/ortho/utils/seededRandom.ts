/**
 * Seeded Random Number Generator
 *
 * Ported from ElectricityAnimation.tsx (lines 127-150)
 * Provides deterministic random number generation for consistent bolt patterns.
 */

// Internal seed state
let randomSeed = 1

/**
 * Generate a seeded random number between 0 and 1
 * Uses linear congruential generator (LCG) algorithm
 */
export function seededRandom(): number {
  randomSeed = (randomSeed * 9301 + 49297) % 233280
  return randomSeed / 233280
}

/**
 * Set the seed for deterministic random generation
 * @param seed - Integer seed value
 */
export function setSeed(seed: number): void {
  randomSeed = seed
}

/**
 * Generate a random number in a range using seeded RNG
 * @param min - Minimum value (inclusive)
 * @param max - Maximum value (exclusive)
 */
export function randomRange(min: number, max: number): number {
  return seededRandom() * (max - min) + min
}

/**
 * Generate a random integer in a range using seeded RNG
 * @param min - Minimum value (inclusive)
 * @param max - Maximum value (inclusive)
 */
export function randomInt(min: number, max: number): number {
  return Math.floor(randomRange(min, max + 1))
}
