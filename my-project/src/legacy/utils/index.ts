/**
 * Utility functions for the Story Portal
 */

/**
 * Fisher-Yates shuffle algorithm
 * Returns a new shuffled array without mutating the original
 */
export function shuffleArray<T>(arr: T[]): T[] {
  const result = [...arr];
  for (let i = result.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [result[i], result[j]] = [result[j], result[i]];
  }
  return result;
}

/**
 * Convert hex color to RGB object
 */
export function hexToRgb(hex: string): { r: number; g: number; b: number } | null {
  const result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
  return result
    ? {
        r: parseInt(result[1], 16),
        g: parseInt(result[2], 16),
        b: parseInt(result[3], 16),
      }
    : null;
}

/**
 * Convert RGB values to hex string
 */
export function rgbToHex(r: number, g: number, b: number): string {
  return '#' + [r, g, b].map((x) => x.toString(16).padStart(2, '0')).join('');
}

/**
 * Clamp a value between min and max
 */
export function clamp(value: number, min: number, max: number): number {
  return Math.min(Math.max(value, min), max);
}

/**
 * Linear interpolation between two values
 */
export function lerp(a: number, b: number, t: number): number {
  return a + (b - a) * t;
}

/**
 * Generate a random number between min and max
 */
export function randomRange(min: number, max: number): number {
  return min + Math.random() * (max - min);
}

/**
 * Generate a random integer between min and max (inclusive)
 */
export function randomInt(min: number, max: number): number {
  return Math.floor(Math.random() * (max - min + 1)) + min;
}

/**
 * Debounce a function
 */
export function debounce<T extends (...args: unknown[]) => void>(
  func: T,
  wait: number
): (...args: Parameters<T>) => void {
  let timeout: ReturnType<typeof setTimeout> | null = null;
  return (...args: Parameters<T>) => {
    if (timeout) clearTimeout(timeout);
    timeout = setTimeout(() => func(...args), wait);
  };
}

/**
 * Generate button shadow CSS filter string
 */
export function generateButtonShadow(config: {
  enabled: boolean;
  offsetX: number;
  offsetY: number;
  blur: number;
  opacity: number;
  layers: number;
  layerMult: number;
}): string {
  if (!config.enabled) return 'none';

  return Array.from({ length: config.layers }, (_, i) => {
    const mult = Math.pow(config.layerMult, i);
    const y = config.offsetY * mult;
    const blur = config.blur * mult;
    const opacity = config.opacity * (1 - i * 0.2);
    return `drop-shadow(${config.offsetX}px ${y}px ${blur}px rgba(0,0,0,${opacity}))`;
  }).join(' ');
}

/**
 * Generate extrusion layer offsets for 3D text effect
 */
export function generateExtrusionLayers(config: {
  extrudeDepth: number;
  extrudeOffsetX: number;
  extrudeOffsetY: number;
  extrudeMaxOffset: number;
  extrudeBaseR: number;
  extrudeBaseG: number;
  extrudeBaseB: number;
  extrudeStepR: number;
  extrudeStepG: number;
  extrudeStepB: number;
}): Array<{ offsetX: number; offsetY: number; r: number; g: number; b: number }> {
  return Array.from({ length: config.extrudeDepth }, (_, i) => {
    const t = (config.extrudeDepth - 1 - i) / (config.extrudeDepth - 1); // 1 at back, 0 at front
    return {
      offsetX: config.extrudeMaxOffset * config.extrudeOffsetX * t,
      offsetY: config.extrudeMaxOffset * config.extrudeOffsetY * t,
      r: Math.min(255, config.extrudeBaseR + config.extrudeStepR * i),
      g: Math.min(255, config.extrudeBaseG + config.extrudeStepG * i),
      b: Math.min(255, config.extrudeBaseB + config.extrudeStepB * i),
    };
  });
}
