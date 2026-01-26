/**
 * SteamModal Component
 * 
 * Main modal assembly combining all sub-components.
 * Uses React Portal for proper DOM rendering.
 * 
 * CRITICAL LIFECYCLE MANAGEMENT:
 * - Proper mounting/unmounting to prevent stacking
 * - Event listener cleanup
 * - Focus management for accessibility
 * 
 * This was a CRITICAL failure point in the previous implementation
 * where modals would stack behind each other.
 */

import { useEffect, useCallback, useRef, ReactNode, useState } from 'react';
import { createPortal } from 'react-dom';
import { Backdrop } from './Backdrop';
import { SteamField } from './SteamField';
import { PanelHeader } from './PanelHeader';
import { ContentPanel } from './ContentPanel';
import { CloseButton } from './CloseButton';
import styles from './SteamModal.module.css';

export interface SteamModalProps {
  /** Whether the modal is currently open */
  isOpen: boolean;
  /** Callback when modal should close */
  onClose: () => void;
  /** Modal title displayed in the panel header */
  title: string;
  /** Modal content */
  children: ReactNode;
  /** Content variant affecting steam density and styling */
  variant?: 'standard' | 'form' | 'gallery' | 'legal';
  /** Steam density level (overrides variant default) */
  steamDensity?: 'light' | 'medium' | 'dense';
  /** Optional callback when modal has fully opened */
  onOpened?: () => void;
  /** Optional callback when modal has fully closed */
  onClosed?: () => void;
}

export function SteamModal({
  isOpen,
  onClose,
  title,
  children,
  variant = 'standard',
  steamDensity,
  onOpened,
  onClosed,
}: SteamModalProps) {
  const modalRef = useRef<HTMLDivElement>(null);
  const previousActiveElement = useRef<HTMLElement | null>(null);
  const [isClosing, setIsClosing] = useState(false);
  const [shouldRender, setShouldRender] = useState(false);

  // Handle mount/unmount with animation
  useEffect(() => {
    if (isOpen) {
      setShouldRender(true);
      setIsClosing(false);
      
      // Notify when opened (after animations)
      const openTimer = setTimeout(() => {
        onOpened?.();
      }, 900); // Match entry animation duration
      
      return () => clearTimeout(openTimer);
    } else if (shouldRender) {
      // Start closing animation
      setIsClosing(true);
      
      // Wait for exit animations then unmount
      const closeTimer = setTimeout(() => {
        setShouldRender(false);
        setIsClosing(false);
        onClosed?.();
      }, 600); // Match exit animation duration
      
      return () => clearTimeout(closeTimer);
    }
  }, [isOpen, shouldRender, onOpened, onClosed]);

  // Handle escape key
  const handleKeyDown = useCallback((event: KeyboardEvent) => {
    if (event.key === 'Escape' && !isClosing) {
      onClose();
    }
  }, [onClose, isClosing]);

  // Setup and cleanup
  useEffect(() => {
    if (shouldRender && !isClosing) {
      // Store current focus to restore later
      previousActiveElement.current = document.activeElement as HTMLElement;
      
      // Add escape listener
      document.addEventListener('keydown', handleKeyDown);
      
      // Focus the modal container
      // Small delay to ensure render is complete
      const focusTimer = setTimeout(() => {
        modalRef.current?.focus();
      }, 100);
      
      return () => {
        document.removeEventListener('keydown', handleKeyDown);
        clearTimeout(focusTimer);
        
        // Restore focus to previous element
        if (previousActiveElement.current) {
          previousActiveElement.current.focus();
        }
      };
    }
  }, [shouldRender, isClosing, handleKeyDown]);

  // Don't render if not needed
  if (!shouldRender) return null;

  // Determine steam density based on variant
  const actualDensity = steamDensity ?? (
    variant === 'legal' ? 'light' : 
    variant === 'form' ? 'light' :
    variant === 'gallery' ? 'medium' :
    'medium'
  );

  // Handle backdrop click (don't close if clicking content)
  const handleBackdropClose = () => {
    if (!isClosing) {
      onClose();
    }
  };

  // Render via portal to ensure proper stacking context
  return createPortal(
    <div 
      ref={modalRef}
      className={`${styles.modalContainer} ${isClosing ? styles.closing : ''}`}
      role="dialog"
      aria-modal="true"
      aria-labelledby="modal-title"
      tabIndex={-1}
      data-variant={variant}
      data-closing={isClosing}
    >
      {/* Layer 1: Backdrop (z-index: 1001) */}
      <Backdrop 
        isOpen={!isClosing} 
        onClose={handleBackdropClose} 
      />
      
      {/* Layer 2: Steam Field (z-index: 1002) */}
      <SteamField 
        isOpen={!isClosing} 
        density={actualDensity} 
      />
      
      {/* Layer 3: Panel Header (z-index: 1003) */}
      <PanelHeader title={title} />
      
      {/* Layer 4: Content Panel (z-index: 1004) */}
      <ContentPanel>
        {children}
      </ContentPanel>
      
      {/* Layer 6: Close Button (z-index: 1006) */}
      <CloseButton onClick={onClose} />
    </div>,
    document.body
  );
}

// Re-export sub-components for convenience
export { ContentParagraph, ContentDivider, ContentSection } from './ContentPanel';
