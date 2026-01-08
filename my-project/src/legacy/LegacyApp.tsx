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
  SteamWisps,
  WheelPanel,
  PortalRing,
  WarpMotionLines,
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
} from './components'

// Views
import { RecordView, StoriesView, AboutView } from './views'

// Booking
import { BookingModal } from '../components/form'

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
  const [view, setView] = useState<'wheel' | 'record' | 'stories' | 'about'>('wheel')
  const [selectedPromptForRecording, setSelectedPromptForRecording] = useState<string | null>(null)

  // Booking modal state
  const [bookingOpen, setBookingOpen] = useState(false)

  // Record button tooltip
  const [showRecordTooltip, setShowRecordTooltip] = useState(false)

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

  // Steam effect hook
  const { steamWisps } = useSteamEffect()

  // Record button handlers
  const handleRecordClick = useCallback(() => {
    if (selectedPrompt) {
      setSelectedPromptForRecording(selectedPrompt)
      setView('record')
    }
  }, [selectedPrompt])

  const handleDisabledRecordClick = useCallback(() => {
    setShowRecordTooltip(true)
    setTimeout(() => setShowRecordTooltip(false), 3000)
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
  if (view === 'record') {
    return (
      <RecordView selectedPrompt={selectedPromptForRecording} onBack={() => setView('wheel')} />
    )
  }

  if (view === 'stories') {
    return <StoriesView onBack={() => setView('wheel')} />
  }

  if (view === 'about') {
    return <AboutView onBack={() => setView('wheel')} />
  }

  // Main wheel view
  return (
    <div className="wheel-view-wrapper">
      <div className="wheel-content">
        {/* Steam Effects */}
        <SteamWisps wisps={steamWisps} />

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
          {/* Warp Motion Lines */}
          <WarpMotionLines visible={!!selectedPrompt && animPhase === 'warp'} />

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
          <NewTopicsButton onLoadNewTopics={loadNewTopics} />
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
          onPanelClick={handlePanelClick}
        />

        {/* Smoke Effect */}
        <SmokeEffect visible={showSmokePoof} animKey={smokeAnimKey} />

        {/* Menu Logo */}
        <MenuLogo visible={showMenuLogo} hasBeenOpened={menuHasBeenOpened} />

        {/* Nav Buttons (How to Play, Book Now, My Stories) */}
        <NavButtons
          onHowToPlay={() => setView('about')}
          onBook={() => setBookingOpen(true)}
          onMyStories={() => setView('stories')}
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
      </div>
    </div>
  )
}
