/**
 * TypeScript interfaces for the Story Portal Legacy App
 */

// ============ WHEEL PHYSICS ============

export interface WheelPhysicsState {
  rotation: number;
  cylinderRadius: number;
  panelHeight: number;
  fontSize: number;
  wheelTilt: number;
}

export interface WheelPhysicsRefs {
  velocityRef: React.MutableRefObject<number>;
  rotationRef: React.MutableRefObject<number>;
  animationRef: React.MutableRefObject<number | null>;
  isCoastingRef: React.MutableRefObject<boolean>;
  spinFrictionRef: React.MutableRefObject<number>;
  spinDirectionRef: React.MutableRefObject<number>;
  lastInputTimeRef: React.MutableRefObject<number>;
  recentLandingsRef: React.MutableRefObject<number[]>;
  wheelContainerRef: React.MutableRefObject<HTMLDivElement | null>;
  wheelRotationRef: React.MutableRefObject<HTMLDivElement | null>;
  isHoveringRef: React.MutableRefObject<boolean>;
}

export interface WheelPhysicsActions {
  startSpin: (delta: number) => void;
  buttonSpin: () => void;
  resetPhysics: () => void;
  setRotation: React.Dispatch<React.SetStateAction<number>>;
  setCylinderRadius: React.Dispatch<React.SetStateAction<number>>;
  setPanelHeight: React.Dispatch<React.SetStateAction<number>>;
  setFontSize: React.Dispatch<React.SetStateAction<number>>;
  setWheelTilt: React.Dispatch<React.SetStateAction<number>>;
}

// ============ WHEEL SELECTION ============

export interface WheelSelectionState {
  selectedPrompt: string | null;
  prompts: string[];
  spinCount: number;
  selectedPromptForRecording: string | null;
}

export interface WheelSelectionActions {
  loadNewTopics: () => void;
  setSelectedPrompt: (prompt: string | null) => void;
  setPrompts: (prompts: string[]) => void;
}

// ============ ANIMATION PHASES ============

export type AnimationPhase =
  | 'warp'
  | 'hold'
  | 'disintegrate'
  | 'reassemble'
  | 'complete'
  | null;

export interface Particle {
  id: number;
  x: number;
  y: number;
  px: number;
  py: number;
  size: number;
  delay: number;
  duration: number;
}

export interface Sparkle {
  id: number;
  x: number;
  y: number;
  size: number;
  delay: number;
}

export interface AnimationPhaseState {
  animPhase: AnimationPhase;
  particles: Particle[];
  showReassembledPanel: boolean;
  reassembleSparkles: Sparkle[];
  descendY: number;
}

// ============ MENU STATE ============

export type HamburgerAnimPhase =
  | 'opening-extrude'
  | 'opening-collapse'
  | 'opening-spin-to-x'
  | 'opening-x-lifted'
  | 'opening-engrave'
  | 'closing-extrude'
  | 'closing-spin-to-line'
  | 'closing-expand'
  | 'closing-engrave'
  | null;

export interface MenuState {
  menuOpen: boolean;
  menuHasBeenOpened: boolean;
  hamburgerAnimPhase: HamburgerAnimPhase;
  showSmokePoof: boolean;
  smokeAnimKey: number;
  swayingFromPanel: number | null;
  swayAnimKey: number;
  showMenuLogo: boolean;
}

export interface MenuActions {
  toggleMenu: () => void;
  setSwayingFromPanel: (panel: number | null) => void;
}

// ============ STEAM EFFECT ============

export interface SteamLocation {
  id: string;
  left?: string;
  top?: string;
  right?: string;
  bottom?: string;
  type: 'vent';
}

export interface SteamWisp {
  id: number;
  left?: string;
  top?: string;
  right?: string;
  bottom?: string;
  type: 'vent';
  offsetX: number;
  offsetY: number;
  duration: number;
  animation: 'steamStream' | 'steamStreamDrift' | 'steamStreamDriftLeft';
  size: number;
  createdAt: number;
}

// ============ ELECTRICITY EFFECT ============

export interface ElectricityBranch {
  angle: number;
  length: number;
  thickness: number;
  seed: number;
}

export interface ElectricityBolt {
  type: string;
  angle: number;
  length: number;
  seed: number;
  thickness: number;
  speed: number;
  branches: ElectricityBranch[];
  noise: (x: number, y: number) => number;
  opacity: number;
  targetOpacity: number;
  fadeSpeed: number;
  nextToggleTime: number;
  isVisible: boolean;
}

export interface FlashArc {
  id: number;
  angle: number;
  length: number;
  seed: number;
  thickness: number;
  speed: number;
  opacity: number;
  life: number;
  maxLife: number;
  noise: (x: number, y: number) => number;
}

export interface ElectricityState {
  time: number;
  bolts: ElectricityBolt[];
  initialized: boolean;
}

export interface ElectricityConfig {
  NUM_TENDRILS: number;
  MIN_TENDRIL_LENGTH: number;
  MAX_TENDRIL_LENGTH: number;
  TENDRIL_THICKNESS: number;
  BRANCH_PROBABILITY: number;
  MAX_BRANCHES: number;
  ANIMATION_SPEED: number;
  NOISE_SCALE: number;
  CORE_COLOR: string;
  GLOW_COLOR: string;
  FLICKER_MIN_OPACITY: number;
  FLICKER_MAX_OPACITY: number;
  FLICKER_SPEED: number;
}

// ============ TEXT EFFECTS ============

export interface ExtrusionLayer {
  offsetX: number;
  offsetY: number;
  r: number;
  g: number;
  b: number;
}

export interface TextEffectConfig {
  // Extrusion geometry
  extrudeDepth: number;
  extrudeOffsetX: number;
  extrudeOffsetY: number;
  extrudeMaxOffset: number;

  // Extrusion colors
  extrudeBaseR: number;
  extrudeBaseG: number;
  extrudeBaseB: number;
  extrudeStepR: number;
  extrudeStepG: number;
  extrudeStepB: number;

  // Face gradient
  faceTopColor: string;
  faceMidColor: string;
  faceBottomColor: string;
  faceGradientMidStop: number;

  // Highlight/bevel
  highlightEnabled: boolean;
  highlightTopColor: string;
  highlightTopOpacity: number;
  highlightMidColor: string;
  highlightMidOpacity: number;
  highlightMidStop: number;
  highlightBottomColor: string;
  highlightBottomOpacity: number;

  // Text shadow
  textShadowEnabled: boolean;
  textShadowOffsetX: number;
  textShadowOffsetY: number;
  textShadowBlur: number;
  textShadowColor: string;
  textShadowOpacity: number;

  // Outer stroke
  outerStrokeEnabled: boolean;
  outerStrokeColor: string;
  outerStrokeWidth: number;

  // Texture overlay
  textureOverlayEnabled: boolean;
  textureOverlayOpacity: number;
  textureBlendMode: string;
  textureGradientEnabled: boolean;
  textureGradientType: 'vertical' | 'horizontal' | 'radial';
  textureGradientTopOpacity: number;
  textureGradientMidOpacity: number;
  textureGradientBottomOpacity: number;
  textureGradientMidStop: number;
}

export interface ButtonShadowConfig {
  enabled: boolean;
  offsetX: number;
  offsetY: number;
  blur: number;
  spread: number;
  color: string;
  opacity: number;
  layers: number;
  layerMult: number;
}

// ============ BUTTON STATES ============

export interface ButtonStates {
  recordPressed: boolean;
  spinPressed: boolean;
  myStoriesPressed: boolean;
  howToPlayPressed: boolean;
  hamburgerPressed: boolean;
  newTopicsPressed: boolean;
  showRecordTooltip: boolean;
}

// ============ TESTING/DEBUG ============

export interface TestResults {
  totalSpins: number;
  uniquePrompts: number;
  mostCommon: { prompt: string; count: number };
  leastCommon: { prompt: string; count: number };
  distribution: Record<string, number>;
  chiSquare: number;
  isRandom: boolean;
}

export interface TestState {
  testMode: boolean;
  showTestPanel: boolean;
  testResults: TestResults | null;
  realTimeTest: boolean;
  realTimeProgress: number;
  realTimeTarget: number;
  manualTracking: boolean;
  manualLandings: string[];
  promptLandingCounts: Record<string, number>;
}

// ============ VIEW TYPES ============

export type ViewType = 'wheel' | 'record' | 'stories' | 'about';

// ============ COMPONENT PROPS ============

export interface WheelContainerProps {
  rotation: number;
  prompts: string[];
  panelHeight: number;
  fontSize: number;
  wheelTilt: number;
  cylinderRadius: number;
  onStartSpin: (delta: number) => void;
}

export interface WheelPanelProps {
  prompt: string;
  index: number;
  panelHeight: number;
  fontSize: number;
  cylinderRadius: number;
}

export interface AnimatedPanelProps {
  prompt: string;
  animPhase: AnimationPhase;
  panelHeight: number;
  fontSize: number;
  textEffects: TextEffectConfig;
}

export interface ImageButtonProps {
  label: string;
  icon?: string;
  pressed: boolean;
  disabled?: boolean;
  variant?: 'primary' | 'secondary';
  onClick: () => void;
  onMouseDown?: () => void;
  onMouseUp?: () => void;
  onMouseLeave?: () => void;
  style?: React.CSSProperties;
}

export interface MenuPanelItem {
  id: string;
  label: string;
  icon: string;
  onClick: () => void;
}
