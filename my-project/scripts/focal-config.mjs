/**
 * Focal Area Configuration
 *
 * Defines the CIRCULAR mask matching the inner portal ring area.
 * Both reference and live captures will be cropped to this same circle.
 *
 * CALIBRATION INSTRUCTIONS:
 * 1. Open http://localhost:5173/?align=blend
 * 2. Adjust the yellow circle to match the inner edge of the portal ring
 * 3. Click "Copy Config" to get the values
 * 4. Paste them here and restart the capture script
 *
 * The inner portal ring uses: calc(min(100%, 100vh - 40px) * 0.68)
 * For 1280x900 viewport: min(1280, 860) * 0.68 = 584.8px diameter
 */

// Viewport dimensions (must match capture settings)
export const VIEWPORT = {
  width: 1280,
  height: 900,
}

// Circular mask matching inner portal ring
// Calibrate using http://localhost:5173/?align=blend
export const FOCAL_AREA = {
  // Center of the circular mask
  centerX: 640,
  centerY: 450,

  // Radius of the circular mask (half the inner portal diameter)
  // Inner portal = calc(min(100%, 100vh - 40px) * 0.68) = 584.8px for 1280x900
  radius: 292, // 584px diameter

  // No padding - mask exactly to inner ring edge
  padding: 0,
}

// Get the bounding box for the circular mask
// Screenshots are rectangular, so we crop to the square bounding the circle
export function getCropBounds() {
  const { centerX, centerY, radius, padding } = FOCAL_AREA
  const size = (radius + padding) * 2

  return {
    x: Math.round(centerX - radius - padding),
    y: Math.round(centerY - radius - padding),
    width: Math.round(size),
    height: Math.round(size),
    // Include circle info for masking during comparison
    isCircular: true,
    circleRadius: radius,
  }
}

// Get circular mask parameters for pixel comparison
export function getCircularMask() {
  const { centerX, centerY, radius } = FOCAL_AREA
  return {
    centerX,
    centerY,
    radius,
    // For cropped images, the center is at (radius, radius)
    croppedCenterX: radius,
    croppedCenterY: radius,
  }
}

// Reference animation dimensions (from the source APNG)
export const REFERENCE = {
  width: 465,
  height: 465,
}

// Export for use in scripts
export default {
  VIEWPORT,
  FOCAL_AREA,
  REFERENCE,
  getCropBounds,
  getCircularMask,
}
