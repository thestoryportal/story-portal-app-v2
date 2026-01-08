/**
 * MenuPanelItem Component
 *
 * Individual menu panel with rope connectors.
 */

import type { CSSProperties } from 'react';

interface MenuPanelItemProps {
  id: number;
  label: string;
  targetY: string;
  hasTopRope: boolean;
  hasBottomRope: boolean;
  isOpen: boolean;
  index: number;
  swayingFromPanel: number | null;
  swayAnimKey: number;
  onPanelClick: (id: number, label: string) => void;
}

export function MenuPanelItem({
  id,
  label,
  targetY,
  hasTopRope,
  hasBottomRope,
  isOpen,
  index,
  swayingFromPanel,
  swayAnimKey,
  onPanelClick,
}: MenuPanelItemProps) {
  // Opening: reverse order (panel 4 first, panel 1 last)
  // Closing: normal order (panel 1 first, panel 4 last)
  const openDelay = (3 - index) * 0.12;
  const closeDelay = index * 0.12;
  const dealDelay = isOpen ? openDelay : closeDelay;

  // Sway animation - calculate delay based on distance from clicked panel
  const isSwaying = swayingFromPanel !== null && isOpen;
  const clickedIndex = swayingFromPanel ? swayingFromPanel - 1 : 0;
  const distanceFromClicked = Math.abs(index - clickedIndex);
  const swayDelay = distanceFromClicked * 0.12;
  const isClickedPanel = swayingFromPanel === id;

  // Rope styling
  const ropeStyle: CSSProperties = {
    position: 'absolute',
    width: '5px',
    height: '40px',
    background:
      'linear-gradient(90deg, #1a1a1a 0%, #3a3a3a 30%, #4a4a4a 50%, #3a3a3a 70%, #1a1a1a 100%)',
    borderRadius: '2.5px',
    boxShadow: 'inset 0 0 3px rgba(0,0,0,0.6), 0 1px 3px rgba(0,0,0,0.4)',
    transform: 'translateZ(-5px)',
  };

  // Determine animation to apply
  let animationStyle = 'none';
  if (isSwaying) {
    if (isClickedPanel) {
      animationStyle = `menuPanelPush 2.5s ease-out forwards`;
    } else {
      animationStyle = `menuPanelSway 2.5s ease-out ${swayDelay}s forwards`;
    }
  }

  return (
    <div
      key={`${id}-${swayAnimKey}`}
      className="menu-panel-item"
      style={{
        position: 'fixed',
        left: '50%',
        top: isOpen ? targetY : '38%',
        transform: isOpen
          ? 'translate(-50%, -50%) perspective(1000px) rotateX(0deg)'
          : 'translate(-50%, -50%) perspective(1000px) rotateX(-360deg)',
        transformOrigin: 'center center',
        transformStyle: 'preserve-3d',
        width: '250px',
        height: '80px',
        background: 'url("/assets/images/wood-panel.webp") center/cover no-repeat',
        backgroundColor: '#3a2818',
        borderRadius: '4px',
        boxShadow: isOpen
          ? '0 15px 40px rgba(0,0,0,0.5), inset 0 0 12px rgba(0,0,0,0.6)'
          : '0 2px 10px rgba(0,0,0,0.3), inset 0 0 12px rgba(0,0,0,0.6)',
        cursor: 'pointer',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '0 12px',
        fontFamily: "'Carnivalee Freakshow', serif",
        fontSize: '32px',
        textAlign: 'center',
        animation: animationStyle,
        transition: `
          top 0.7s cubic-bezier(0.25, 0.46, 0.45, 0.94) ${dealDelay}s,
          transform 0.7s cubic-bezier(0.25, 0.46, 0.45, 0.94) ${dealDelay}s,
          opacity 0.15s ease ${isOpen ? dealDelay : 0.5 + closeDelay}s,
          visibility 0s linear ${isOpen ? '0s' : 0.7 + closeDelay + 's'},
          box-shadow 0.5s ease ${dealDelay}s
        `,
        opacity: isOpen ? 1 : 0,
        visibility: isOpen ? 'visible' : 'hidden',
        pointerEvents: isOpen ? 'auto' : 'none',
        zIndex: 1004 - index,
      }}
      onClick={(e) => {
        e.stopPropagation();
        onPanelClick(id, label);
      }}
    >
      <span className="carved-text">{label}</span>

      {/* Top rope connectors */}
      {hasTopRope && (
        <>
          <div style={{ ...ropeStyle, left: '15px', top: '-20px' }} />
          <div style={{ ...ropeStyle, right: '15px', top: '-20px' }} />
        </>
      )}

      {/* Bottom rope connectors */}
      {hasBottomRope && (
        <>
          <div style={{ ...ropeStyle, left: '15px', bottom: '-20px' }} />
          <div style={{ ...ropeStyle, right: '15px', bottom: '-20px' }} />
        </>
      )}
    </div>
  );
}
