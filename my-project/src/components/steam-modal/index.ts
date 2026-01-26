/**
 * Steam Modal Exports
 * 
 * Main entry point for the Steam Modal component system.
 * 
 * Usage:
 *   import { SteamModal, ContentParagraph, ContentDivider } from './components/steam-modal';
 * 
 *   <SteamModal
 *     isOpen={isOpen}
 *     onClose={() => setIsOpen(false)}
 *     title="Our Story"
 *     variant="standard"
 *   >
 *     <ContentParagraph index={0}>
 *       First paragraph content...
 *     </ContentParagraph>
 *     <ContentDivider />
 *     <ContentParagraph index={1}>
 *       Second paragraph content...
 *     </ContentParagraph>
 *   </SteamModal>
 */

// Main component
export { SteamModal } from './SteamModal';
export type { SteamModalProps } from './SteamModal';

// Content sub-components
export { 
  ContentParagraph, 
  ContentDivider, 
  ContentSection 
} from './ContentPanel';

// Individual components (for advanced usage)
export { Backdrop } from './Backdrop';
export { SteamField } from './SteamField';
export { PanelHeader } from './PanelHeader';
export { ContentPanel } from './ContentPanel';
