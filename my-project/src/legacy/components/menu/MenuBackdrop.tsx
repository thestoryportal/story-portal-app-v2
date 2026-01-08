/**
 * MenuBackdrop Component
 *
 * Blur overlay when menu is open.
 */

interface MenuBackdropProps {
  isOpen: boolean;
  onClose: () => void;
}

export function MenuBackdrop({ isOpen, onClose }: MenuBackdropProps) {
  return (
    <div
      className="menu-backdrop"
      onClick={onClose}
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        width: '100vw',
        height: '100vh',
        backgroundColor: 'rgba(0, 0, 0, 0.3)',
        backdropFilter: isOpen ? 'blur(8px)' : 'blur(0px)',
        WebkitBackdropFilter: isOpen ? 'blur(8px)' : 'blur(0px)',
        opacity: isOpen ? 1 : 0,
        pointerEvents: isOpen ? 'auto' : 'none',
        transition:
          'opacity 1s ease-out, backdrop-filter 1s ease-out, -webkit-backdrop-filter 1s ease-out',
        zIndex: 998,
      }}
    />
  );
}
