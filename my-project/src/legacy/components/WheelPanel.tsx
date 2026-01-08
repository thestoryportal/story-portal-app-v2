/**
 * WheelPanel Component
 *
 * Individual prompt panel on the wheel cylinder.
 */

interface WheelPanelProps {
  prompt: string;
  index: number;
  cylinderRadius: number;
  panelHeight: number;
  fontSize: number;
}

export function WheelPanel({ prompt, index, cylinderRadius, panelHeight, fontSize }: WheelPanelProps) {
  const angle = index * 18;
  const radian = (angle * Math.PI) / 180;
  const y = Math.sin(radian) * cylinderRadius;
  const z = Math.cos(radian) * cylinderRadius;

  return (
    <div
      className="wheel-panel"
      style={{
        height: `${panelHeight}px`,
        marginTop: `${-panelHeight / 2}px`,
        transform: `translate3d(0, ${y}px, ${z}px) rotateX(${-angle}deg)`,
      }}
    >
      <div className="wheel-panel-inner" style={{ fontSize: `${fontSize}px` }}>
        <span className="carved-text">{prompt}</span>
      </div>
    </div>
  );
}
