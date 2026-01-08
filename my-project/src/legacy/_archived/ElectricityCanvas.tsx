/**
 * @deprecated Use ElectricityR3F instead.
 * This canvas wrapper for the raw WebGL effect is superseded by R3F.
 *
 * ElectricityCanvas Component
 *
 * Canvas wrapper for the WebGL electricity effect.
 */

import { forwardRef } from 'react';

interface ElectricityCanvasProps {
  visible: boolean;
  debug?: boolean;
}

export const ElectricityCanvas = forwardRef<HTMLCanvasElement, ElectricityCanvasProps>(
  function ElectricityCanvas({ visible, debug = false }, ref) {
    if (!visible) return null;

    return (
      <canvas
        ref={ref}
        style={{
          position: 'absolute',
          left: '50%',
          top: '50%',
          transform: 'translate(-50%, -50%)',
          width: 'calc(min(100%, 100vh - 40px) * 0.78)',
          height: 'calc(min(100%, 100vh - 40px) * 0.78)',
          borderRadius: '50%',
          zIndex: 27, // Below PortalRing (30), above wheel (25)
          pointerEvents: 'none',
          backgroundColor: debug ? 'rgba(255, 0, 255, 0.3)' : 'transparent',
          border: debug ? '4px solid magenta' : 'none',
        }}
        width={400}
        height={400}
      />
    );
  }
);
