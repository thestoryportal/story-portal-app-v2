/**
 * LegacyApp - Main wheel application component
 *
 * Refactored to use extracted modules for maintainability.
 */

import './styles/index.css'
import { useState, useCallback } from 'react'

// Types
import type { Sparkle } from './types'

// Hooks
import { useWheelPhysics } from './hooks/useWheelPhysics'
import { useWheelSelection } from './hooks/useWheelSelection'
import { useMenuState } from './hooks/useMenuState'
import { useSteamEffect } from './hooks/useSteamEffect'


// Effects (R3F component handles its own rendering)

// Components
import {
  WheelPanel,
  PortalRing,
  AnimatedPanel,
  ReassembledPanel,
  SpinButton,
  NewTopicsButton,
  RecordButton,
  NavButtons,
  HamburgerMenu,
  MenuBackdrop,
  MenuPanels,
  MenuLogo,
  SmokeEffect,
  SteamWisps,
} from './components'

// Views
import { AboutView } from './views'
import { GalleryView } from '../components/views/GalleryView'
import { RecordingView } from '../components/views/RecordingView'

// Effects - ElectricityOrtho replaces deprecated Canvas 2D (see .claude/guardrails.md)
import { ElectricityOrtho } from '../components/electricity/ortho'

// Menu Modals
import {
  OurStoryModal,
  OurWorkModal,
  InquiryModal,
  PrivacyTermsModal,
} from '../components/menu-modals'

// Booking (deprecated - kept for NavButtons compatibility)
import { BookingModal } from '../components/form'

// Menu Modal Types
type MenuModalId = 'our-story' | 'our-work' | 'booking' | 'privacy-terms' | null
const MENU_MODAL_ORDER: Exclude<MenuModalId, null>[] = ['our-story', 'our-work', 'booking', 'privacy-terms']

// Constants and utilities
import type { Prompt, StoryRecord } from '../types/story'
import { saveStory } from '../utils/storage'

// Configuration flags
const TEST_MODE = false

// Button shadow configuration
const BUTTON_SHADOW_CONFIG = {
  enabled: true,
  offsetX: -5,
  offsetY: 6,
  blur: 17,
  layers: 4,
  layerMult: 1.5,
  opacity: 0.6,
}

function generateButtonShadowStyle(config: typeof BUTTON_SHADOW_CONFIG) {
  if (!config.enabled) return {}
  return {
    filter: Array.from({ length: config.layers }, (_, i) => {
      const mult = Math.pow(config.layerMult, i)
      const y = config.offsetY * mult
      const blur = config.blur * mult
      const opacity = config.opacity * (1 - i * 0.2)
      return `drop-shadow(${config.offsetX}px ${y}px ${blur}px rgba(0,0,0,${opacity}))`
    }).join(' '),
  }
}

export default function LegacyApp() {
  // View state
  const [view, setView] = useState<'wheel' | 'record' | 'about'>('wheel')
  const [galleryOpen, setGalleryOpen] = useState(false)
  const [selectedPromptForRecording, setSelectedPromptForRecording] = useState<Prompt | null>(null)

  // Booking modal state (deprecated - kept for NavButtons compatibility)
  const [bookingOpen, setBookingOpen] = useState(false)

  // Menu modal state
  const [activeMenuModal, setActiveMenuModal] = useState<MenuModalId>(null)

  // Record button tooltip
  const [showRecordTooltip, setShowRecordTooltip] = useState(false)

  // Electricity animation state
  const [electricityActive, setElectricityActive] = useState(false)

  // Reassemble sparkles state (managed locally since useWheelSelection doesn't export it yet)
  const [reassembleSparkles] = useState<Sparkle[]>([])

  // Button shadow style
  const buttonShadowStyle = generateButtonShadowStyle(BUTTON_SHADOW_CONFIG)

  // Wheel selection hook
  const wheelSelection = useWheelSelection({
    testMode: TEST_MODE,
  })

  const {
    prompts,
    selectedPrompt,
    animPhase,
    particles,
    showReassembledPanel,
    loadNewTopics,
    selectPrompt,
  } = wheelSelection

  // Wheel physics hook
  const {
    state: physicsState,
    actions: physicsActions,
    refs: physicsRefs,
  } = useWheelPhysics({
    testMode: TEST_MODE,
    onWheelStop: (selectedIndex: number) => {
      selectPrompt(selectedIndex)
    },
  })

  const { cylinderRadius, panelHeight, fontSize, wheelTilt } = physicsState
  const { startSpin, buttonSpin } = physicsActions
  const { wheelContainerRef, wheelRotationRef, isHoveringRef } = physicsRefs

  // Menu state hook
  const menuState = useMenuState()

  // Steam effect hook - persistent vent steam
  const { steamWisps } = useSteamEffect()
  const {
    menuOpen,
    menuHasBeenOpened,
    hamburgerAnimPhase,
    showSmokePoof,
    smokeAnimKey,
    swayingFromPanel,
    swayAnimKey,
    showMenuLogo,
    toggleMenu,
    closeMenu,
    handlePanelClick,
  } = menuState

  // Menu modal navigation
  const navigateMenuModal = useCallback((direction: 'next' | 'prev') => {
    if (!activeMenuModal) return
    const currentIndex = MENU_MODAL_ORDER.indexOf(activeMenuModal)
    const newIndex = direction === 'next' ? currentIndex + 1 : currentIndex - 1
    if (newIndex >= 0 && newIndex < MENU_MODAL_ORDER.length) {
      setActiveMenuModal(MENU_MODAL_ORDER[newIndex])
    }
  }, [activeMenuModal])

  // Handle menu panel click - trigger sway animation, then open modal
  const handleMenuItemClick = useCallback((id: number, _label: string) => {
    // Trigger sway animation (existing behavior)
    handlePanelClick(id)

    // Open modal after sway animation completes (menu stays open)
    setTimeout(() => {
      const modalMap: Record<number, MenuModalId> = {
        1: 'our-story',
        2: 'our-work',
        3: 'booking',
        4: 'privacy-terms',
      }
      setActiveMenuModal(modalMap[id] || null)
    }, 700)
  }, [handlePanelClick])

  // Close menu modal
  const closeMenuModal = useCallback(() => {
    setActiveMenuModal(null)
  }, [])

  // Record button handlers
  const handleRecordClick = useCallback(() => {
    if (selectedPrompt) {
      // Create a Prompt object from the selected text
      const promptObj: Prompt = {
        id: `prompt_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
        text: selectedPrompt,
        category: 'Story',
        declaration_risk: 'medium',
        facilitation_hint: 'Share your story in your own words.',
        created_at: new Date().toISOString(),
      }
      setSelectedPromptForRecording(promptObj)
      setView('record')
    }
  }, [selectedPrompt])

  const handleDisabledRecordClick = useCallback(() => {
    setShowRecordTooltip(true)
    setTimeout(() => setShowRecordTooltip(false), 3000)
  }, [])

  // Handle New Topics with electricity animation
  const handleNewTopicsClick = useCallback(() => {
    setElectricityActive(true)
    loadNewTopics()
  }, [loadNewTopics])

  // Handle electricity animation complete
  const handleElectricityComplete = useCallback(() => {
    setElectricityActive(false)
  }, [])

  // Save story handler
  const handleSaveStory = useCallback(async (story: StoryRecord) => {
    try {
      await saveStory(story)
      console.log('Story saved successfully:', story.id)

      // Return to wheel view
      setSelectedPromptForRecording(null)
      setView('wheel')
    } catch (error) {
      console.error('Failed to save story:', error)
      // Error is already displayed in RecordingView
    }
  }, [])

  // Mouse/touch handlers for wheel
  const handleMouseDown = useCallback(
    (e: React.MouseEvent) => {
      e.preventDefault()
      e.stopPropagation()
      let lastY = e.clientY
      let lastTime = Date.now()

      const move = (me: MouseEvent) => {
        me.preventDefault()
        me.stopPropagation()
        const currentY = me.clientY
        const currentTime = Date.now()
        const deltaY = currentY - lastY
        const deltaTime = currentTime - lastTime
        if (deltaTime > 5) {
          startSpin(-deltaY * 1.0)
          lastY = currentY
          lastTime = currentTime
        }
      }

      const up = () => {
        document.removeEventListener('mousemove', move)
        document.removeEventListener('mouseup', up)
      }

      document.addEventListener('mousemove', move)
      document.addEventListener('mouseup', up)
    },
    [startSpin]
  )

  const handleTouchStart = useCallback(
    (e: React.TouchEvent) => {
      e.stopPropagation()
      let lastY = e.touches[0].clientY
      let lastTime = Date.now()

      const move = (te: TouchEvent) => {
        te.preventDefault()
        te.stopPropagation()
        const currentY = te.touches[0].clientY
        const currentTime = Date.now()
        const deltaY = currentY - lastY
        const deltaTime = currentTime - lastTime
        if (deltaTime > 5) {
          startSpin(-deltaY * 1.2)
          lastY = currentY
          lastTime = currentTime
        }
      }

      const end = () => {
        document.removeEventListener('touchmove', move)
        document.removeEventListener('touchend', end)
      }

      document.addEventListener('touchmove', move, { passive: false })
      document.addEventListener('touchend', end)
    },
    [startSpin]
  )

  const handleWheel = useCallback(
    (e: React.WheelEvent) => {
      const rect = e.currentTarget.getBoundingClientRect()
      const centerX = rect.left + rect.width / 2
      const centerY = rect.top + rect.height / 2
      const distanceFromCenter = Math.sqrt(
        Math.pow(e.clientX - centerX, 2) + Math.pow(e.clientY - centerY, 2)
      )
      const maxRadius = (rect.width / 2) * 0.8
      if (distanceFromCenter > maxRadius) return

      e.preventDefault()
      e.stopPropagation()
      startSpin(e.deltaY * 0.6)
    },
    [startSpin]
  )

  // Render based on view
  if (view === 'record' && selectedPromptForRecording) {
    return (
      <RecordingView
        prompt={selectedPromptForRecording}
        onSaveStory={handleSaveStory}
        onCancel={() => {
          setSelectedPromptForRecording(null)
          setView('wheel')
        }}
      />
    )
  }

  if (view === 'about') {
    return <AboutView onBack={() => setView('wheel')} />
  }

  // Main wheel view
  return (
    <div className="wheel-view-wrapper">
      {/* Persistent Vent Steam Effect */}
      <SteamWisps wisps={steamWisps} />

      <div className="wheel-content">
        {/* Wheel Container */}
        <div
          ref={wheelContainerRef}
          className="wheel-container"
          onMouseEnter={() => {
            isHoveringRef.current = true
          }}
          onMouseLeave={() => {
            isHoveringRef.current = false
          }}
          onMouseDown={handleMouseDown}
          onTouchStart={handleTouchStart}
          onWheel={handleWheel}
        >

          {/* Animated Panel */}
          <AnimatedPanel
            selectedPrompt={selectedPrompt}
            animPhase={animPhase}
            panelHeight={panelHeight}
            fontSize={fontSize}
            particles={particles}
          />

          {/* Portal Ring */}
          <PortalRing />

          {/* Electricity Animation (triggers on New Topics) - Ortho R3F */}
          <ElectricityOrtho
            isActive={electricityActive}
            onComplete={handleElectricityComplete}
            onPhaseChange={(phase) => console.log('[Electricity]', phase)}
          />

          {/* Reassembled Panel */}
          <ReassembledPanel
            selectedPrompt={selectedPrompt}
            animPhase={animPhase}
            fontSize={fontSize}
            sparkles={reassembleSparkles}
            visible={showReassembledPanel}
          />

          {/* Portal shadows */}
          <div className="portal-inner-shadow" />
          <div className="wheel-inner-depth" />

          {/* Wheel Viewport */}
          <div className="wheel-viewport">
            <div
              style={{
                transform: `rotateX(${wheelTilt}deg)`,
                transformStyle: 'preserve-3d',
                width: '100%',
                height: '100%',
                position: 'relative',
              }}
            >
              <div ref={wheelRotationRef} className="wheel-cylinder">
                {prompts.slice(0, 20).map((prompt, i) => (
                  <WheelPanel
                    key={i}
                    prompt={prompt}
                    index={i}
                    cylinderRadius={cylinderRadius}
                    panelHeight={panelHeight}
                    fontSize={fontSize}
                  />
                ))}
              </div>
            </div>
          </div>

          <div className="wheel-depth-overlay" />
        </div>

        {/* Selected prompt container */}
        <div className="selected-prompt-container" />

        {/* Buttons Container */}
        <div className="buttons-container">
          <SpinButton onSpin={buttonSpin} />
          <NewTopicsButton onLoadNewTopics={handleNewTopicsClick} />
          <RecordButton
            hasSelectedPrompt={!!selectedPrompt}
            onRecord={handleRecordClick}
            onDisabledClick={handleDisabledRecordClick}
            showTooltip={showRecordTooltip}
          />
        </div>

        {/* Hamburger Menu */}
        <HamburgerMenu
          isOpen={menuOpen}
          animPhase={hamburgerAnimPhase}
          buttonShadowStyle={buttonShadowStyle}
          onToggle={toggleMenu}
        />

        {/* Menu Backdrop */}
        <MenuBackdrop isOpen={menuOpen} onClose={closeMenu} />

        {/* Menu Panels */}
        <MenuPanels
          isOpen={menuOpen}
          hasBeenOpened={menuHasBeenOpened}
          swayingFromPanel={swayingFromPanel}
          swayAnimKey={swayAnimKey}
          onPanelClick={handleMenuItemClick}
        />

        {/* Smoke Effect */}
        <SmokeEffect visible={showSmokePoof} animKey={smokeAnimKey} />

        {/* Menu Logo */}
        <MenuLogo visible={showMenuLogo} hasBeenOpened={menuHasBeenOpened} />

        {/* Nav Buttons (How to Play, Book Now, My Stories) */}
        <NavButtons
          onHowToPlay={() => setView('about')}
          onBook={() => setBookingOpen(true)}
          onMyStories={() => setGalleryOpen(true)}
          buttonShadowStyle={buttonShadowStyle}
        />

        {/* Booking Modal */}
        <BookingModal
          isOpen={bookingOpen}
          onClose={() => setBookingOpen(false)}
          onSuccess={(booking) => {
            console.log('Booking confirmed:', booking)
          }}
        />

        {/* Gallery Modal Overlay */}
        {galleryOpen && (
          <div
            style={{
              position: 'fixed',
              inset: 0,
              background: 'rgba(0, 0, 0, 0.3)',
              backdropFilter: 'blur(6px)',
              zIndex: 2000,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              padding: 'var(--sp-spacing-lg)',
              overflow: 'auto',
            }}
            onClick={() => setGalleryOpen(false)}
          >
            <div
              onClick={(e) => e.stopPropagation()}
              style={{
                maxWidth: '90vw',
                maxHeight: '90vh',
                width: '100%',
                borderRadius: '12px',
              }}
            >
              <GalleryView onBack={() => setGalleryOpen(false)} />
            </div>
          </div>
        )}

        {/* Menu Modals - overlay on top of menu (menu stays open) */}
        <OurStoryModal
          isOpen={activeMenuModal === 'our-story'}
          onClose={closeMenuModal}
          onNext={() => navigateMenuModal('next')}
        />
        <OurWorkModal
          isOpen={activeMenuModal === 'our-work'}
          onClose={closeMenuModal}
          onNext={() => navigateMenuModal('next')}
          onPrev={() => navigateMenuModal('prev')}
        />
        <InquiryModal
          isOpen={activeMenuModal === 'booking'}
          onClose={closeMenuModal}
          onNext={() => navigateMenuModal('next')}
          onPrev={() => navigateMenuModal('prev')}
        />
        <PrivacyTermsModal
          isOpen={activeMenuModal === 'privacy-terms'}
          onClose={closeMenuModal}
          onPrev={() => navigateMenuModal('prev')}
        />
      </div>
    </div>
  )
}
