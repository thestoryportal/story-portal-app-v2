/**
 * MenuLogo Component
 *
 * Story Portal logo displayed below the menu panels.
 */

interface MenuLogoProps {
  visible: boolean;
  hasBeenOpened: boolean;
}

export function MenuLogo({ visible, hasBeenOpened }: MenuLogoProps) {
  if (!hasBeenOpened) return null;

  return (
    <div
      style={{
        position: 'fixed',
        left: '50%',
        top: 'calc(38% + 205px)',
        transform: 'translateX(-50%)',
        width: '240px',
        height: 'auto',
        opacity: visible ? 1 : 0,
        // When visible is false, we're about to fade IN (use 1s)
        // When visible is true, we're about to fade OUT (use 2.9s)
        transition: visible ? 'opacity 2.9s ease-in-out' : 'opacity 1s ease-in-out',
        pointerEvents: 'none',
        zIndex: 1002,
      }}
    >
      <img
        src="/assets/images/story-portal-logo.svg"
        alt="The Story Portal"
        style={{
          width: '100%',
          height: 'auto',
          objectFit: 'contain',
        }}
      />
    </div>
  );
}
