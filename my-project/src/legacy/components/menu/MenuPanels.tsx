/**
 * MenuPanels Component
 *
 * Container for all menu panel items.
 */

import { MenuPanelItem } from './MenuPanelItem';

interface MenuItem {
  id: number;
  label: string;
  targetY: string;
  hasTopRope: boolean;
  hasBottomRope: boolean;
}

const MENU_ITEMS: MenuItem[] = [
  { id: 1, label: 'Our Story', targetY: 'calc(38% - 165px)', hasTopRope: false, hasBottomRope: true },
  { id: 2, label: 'Our Work', targetY: 'calc(38% - 65px)', hasTopRope: true, hasBottomRope: true },
  { id: 3, label: 'Booking', targetY: 'calc(38% + 35px)', hasTopRope: true, hasBottomRope: true },
  { id: 4, label: 'Privacy & Terms', targetY: 'calc(38% + 135px)', hasTopRope: true, hasBottomRope: false },
];

interface MenuPanelsProps {
  isOpen: boolean;
  hasBeenOpened: boolean;
  swayingFromPanel: number | null;
  swayAnimKey: number;
  onPanelClick: (id: number, label: string) => void;
}

export function MenuPanels({
  isOpen,
  hasBeenOpened,
  swayingFromPanel,
  swayAnimKey,
  onPanelClick,
}: MenuPanelsProps) {
  if (!hasBeenOpened) return null;

  return (
    <>
      {MENU_ITEMS.map((item, index) => (
        <MenuPanelItem
          key={`${item.id}-${swayAnimKey}`}
          id={item.id}
          label={item.label}
          targetY={item.targetY}
          hasTopRope={item.hasTopRope}
          hasBottomRope={item.hasBottomRope}
          isOpen={isOpen}
          index={index}
          swayingFromPanel={swayingFromPanel}
          swayAnimKey={swayAnimKey}
          onPanelClick={onPanelClick}
        />
      ))}
    </>
  );
}
