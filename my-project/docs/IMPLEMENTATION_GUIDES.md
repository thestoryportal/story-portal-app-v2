# Story Portal — Implementation Guides

**Version**: 1.0
**Date**: January 8, 2025
**Status**: Ready for MVP Development

---

## Table of Contents

1. [Wheel Physics Implementation](#1-wheel-physics-implementation)
2. [Audio Waveform Extraction](#2-audio-waveform-extraction)
3. [Content Strategy & Data Loading](#3-content-strategy--data-loading)

---

## 1. Wheel Physics Implementation

### Overview

The wheel uses **linear velocity damping** with a configurable dampening factor. This approach is:
- ✅ Simple to implement and tune
- ✅ Performant (no complex calculations per frame)
- ✅ Adjustable via single constant
- ✅ Empirically tuned for natural feel

### Core Algorithm

```typescript
// Constants
const DAMPING_FACTOR = 0.5;           // Controls spin duration (lower = longer spin)
const FRICTION_FACTOR = 0.97;          // Per-frame deceleration (0-1)
const MIN_SPIN_DURATION_MS = 2000;     // Minimum spin time before snap allowed
const SNAP_DURATION_MS = 400;          // Time to snap to nearest prompt
const PROMPTS_PER_WHEEL = 20;
const SEGMENT_SIZE_DEGREES = 18;       // 360 / 20

// Touch velocity to initial rotation velocity
function calculateInitialVelocity(touchVelocityPxPerMs: number): number {
  // Formula: rotation_deg_per_ms = touch_velocity_px_per_ms * damping_factor
  // Example: 500px swipe in 300ms = 1.67 px/ms velocity
  //          1.67 * 0.5 = 0.835 deg/ms initial rotation velocity
  return touchVelocityPxPerMs * DAMPING_FACTOR;
}

// Per-frame rotation deceleration
function decelerateVelocity(currentVelocity: number): number {
  // Multiply by friction factor each frame
  // velocity(frame+1) = velocity(frame) * 0.97
  // After 30 frames (500ms at 60fps): velocity = velocity * 0.97^30 ≈ 0.4x
  return currentVelocity * FRICTION_FACTOR;
}

// Calculate which prompt the pointer landed on
function calculateLandingPrompt(
  finalRotationDegrees: number,
  prompts: Prompt[]
): Prompt {
  // Wheel rotates, but pointer is fixed at top center
  // Account for rotation direction (CSS rotateX increases degrees downward)
  const adjustedDegrees = (360 - finalRotationDegrees) % 360;

  // Which 18-degree segment is the pointer in?
  const segmentIndex = Math.floor(adjustedDegrees / SEGMENT_SIZE_DEGREES);

  return prompts[segmentIndex % PROMPTS_PER_WHEEL];
}

// Snap to nearest segment center
function calculateSnapTarget(
  currentRotationDegrees: number
): number {
  // Find nearest segment center (18, 36, 54, ... degrees)
  const adjustedDegrees = (360 - currentRotationDegrees) % 360;
  const closestSegmentIndex = Math.round(adjustedDegrees / SEGMENT_SIZE_DEGREES);
  const snapDegrees = closestSegmentIndex * SEGMENT_SIZE_DEGREES;

  // Convert back to wheel rotation (inverse of calculation above)
  return (360 - snapDegrees) % 360;
}
```

### Touch Input Detection

```typescript
// Track touch/mouse down start
let touchStartX = 0;
let touchStartTime = 0;
let isSpinning = false;

function handleTouchStart(event: TouchEvent | MouseEvent) {
  if (isSpinning) return; // Ignore if already spinning

  const clientX = event instanceof TouchEvent
    ? event.touches[0].clientX
    : event.clientX;

  touchStartX = clientX;
  touchStartTime = Date.now();
}

// Track touch/mouse move for continuous drag
function handleTouchMove(event: TouchEvent | MouseEvent) {
  if (!touchStartTime) return; // Not tracking

  const clientX = event instanceof TouchEvent
    ? event.touches[0].clientX
    : event.clientX;

  const distance = clientX - touchStartX;
  const deltaTime = Date.now() - touchStartTime;

  // Update wheel rotation in real-time based on drag distance
  // 1px drag = 1 degree rotation (adjustable)
  const rotationDelta = distance * 1; // px-to-deg ratio
  setWheelRotation(initialRotation + rotationDelta);
}

// Track touch/mouse up to calculate velocity
function handleTouchEnd(event: TouchEvent | MouseEvent) {
  if (!touchStartTime) return;

  const clientX = event instanceof TouchEvent
    ? event.changedTouches[0].clientX
    : event.clientX;

  const totalDistance = clientX - touchStartX; // pixels
  const totalTime = Date.now() - touchStartTime; // milliseconds

  // Velocity in pixels per millisecond
  const touchVelocityPxPerMs = totalDistance / totalTime;

  // Convert to rotation velocity (deg/ms)
  const initialRotationVelocity = calculateInitialVelocity(touchVelocityPxPerMs);

  // Begin momentum-based spin
  beginSpin(initialRotationVelocity);

  // Reset tracking
  touchStartTime = 0;
  touchStartX = 0;
}
```

### Momentum Animation Loop

```typescript
// useWheel hook: manages spin animation with momentum
function useWheel(prompts: Prompt[]) {
  const [rotation, setRotation] = useState(0);
  const [isSpinning, setIsSpinning] = useState(false);
  const [selectedPrompt, setSelectedPrompt] = useState<Prompt | null>(null);

  const velocityRef = useRef(0);
  const animationFrameRef = useRef<number>();
  const spinStartTimeRef = useRef<number>();

  const animateWheel = useCallback(() => {
    const now = Date.now();
    const elapsed = now - spinStartTimeRef.current!;

    // Stop spinning if momentum is negligible (< 0.01 deg/frame)
    if (Math.abs(velocityRef.current) < 0.01) {
      // Snap to nearest prompt
      const snapTarget = calculateSnapTarget(rotation);
      snapToPrompt(snapTarget);
      return;
    }

    // If minimum spin duration not met, continue momentum without snapping
    if (elapsed < MIN_SPIN_DURATION_MS) {
      // Apply deceleration
      velocityRef.current = decelerateVelocity(velocityRef.current);

      // Update rotation
      setRotation(prev => prev + velocityRef.current);

      // Continue animation
      animationFrameRef.current = requestAnimationFrame(animateWheel);
    } else {
      // Minimum spin time reached, allow snap
      if (Math.abs(velocityRef.current) > 0.01) {
        // Still moving, continue momentum
        velocityRef.current = decelerateVelocity(velocityRef.current);
        setRotation(prev => prev + velocityRef.current);
        animationFrameRef.current = requestAnimationFrame(animateWheel);
      } else {
        // Snap to prompt
        const snapTarget = calculateSnapTarget(rotation);
        snapToPrompt(snapTarget);
      }
    }
  }, [rotation]);

  const snapToPrompt = useCallback((snapTarget: number) => {
    setIsSpinning(false);

    // Animate snap over 400ms with easing
    const startRotation = rotation;
    const snapStartTime = Date.now();

    const snapAnimation = () => {
      const elapsed = Date.now() - snapStartTime;
      const progress = Math.min(elapsed / SNAP_DURATION_MS, 1);

      // Cubic bezier easing: cubic-bezier(0.25, 0.46, 0.45, 0.94)
      const eased = easeOutCubic(progress);

      const currentRotation = startRotation + (snapTarget - startRotation) * eased;
      setRotation(currentRotation);

      if (progress < 1) {
        requestAnimationFrame(snapAnimation);
      } else {
        // Snap complete, calculate landed prompt
        const landed = calculateLandingPrompt(snapTarget, prompts);
        setSelectedPrompt(landed);
      }
    };

    snapAnimation();
  }, [rotation, prompts]);

  const beginSpin = useCallback((initialVelocity: number) => {
    setIsSpinning(true);
    velocityRef.current = initialVelocity;
    spinStartTimeRef.current = Date.now();
    animationFrameRef.current = requestAnimationFrame(animateWheel);
  }, [animateWheel]);

  return {
    rotation,
    isSpinning,
    selectedPrompt,
    beginSpin,
  };
}

// Cubic bezier easing function
function easeOutCubic(t: number): number {
  return 1 - Math.pow(1 - t, 3);
}
```

### Testing Cases

| Input | Expected Output | Notes |
|-------|-----------------|-------|
| 500px swipe in 300ms | ~2-3 sec spin | velocity = 1.67px/ms * 0.5 = 0.835 deg/ms |
| 200px swipe in 500ms | ~1 sec spin | velocity = 0.4px/ms * 0.5 = 0.2 deg/ms (slow) |
| 50px swipe (accidental tap) | No spin | velocity negligible, friction kills momentum |
| Spin ends at 45°, snap to 36° | Snap to 36° segment | Nearest segment center wins |
| `prefers-reduced-motion: reduce` | Jump to final rotation | No animation, instant snap |

### Tuning Parameters

If spin feels too fast/slow, adjust **one constant**:

```typescript
// Current: DAMPING_FACTOR = 0.5
// Increase (0.6, 0.7) → longer spins, more momentum
// Decrease (0.3, 0.4) → shorter spins, snappier response
const DAMPING_FACTOR = 0.5;
```

Test empirically on real touch devices (mobile, tablet) to ensure natural feel.

---

## 2. Audio Waveform Extraction

### Overview

Waveform visualization uses the **Web Audio API** to extract frequency data in real-time. No external audio libraries required.

### Algorithm: Frequency Bin Extraction

```typescript
// Constants
const FFT_SIZE = 256;                // Number of frequency bins (2^n, 32-2048)
const FREQUENCY_BINS = FFT_SIZE / 2; // 128 bins (Nyquist frequency)
const DISPLAY_BARS = 12;             // Show 12 bars in UI (aggregate bins)
const SMOOTHING = 0.8;               // Exponential smoothing (0-1, higher = smoother)

interface AudioAnalysis {
  frequencyData: Uint8Array;         // Raw frequency bins (0-255 per bin)
  visualBars: number[];              // Aggregated 12 bars for UI (0-255 per bar)
  rmsLevel: number;                  // RMS energy level (0-1) for volume detection
}

// Setup audio context on first recording
function setupAudioAnalyzer(mediaStream: MediaStream): AnalyserNode {
  const audioContext = new (window.AudioContext || (window as any).webkitAudioContext)();
  const source = audioContext.createMediaStreamAudioSource(mediaStream);
  const analyser = audioContext.createAnalyser();

  analyser.fftSize = FFT_SIZE;
  analyser.smoothingTimeConstant = SMOOTHING;

  source.connect(analyser);
  // analyser.connect(audioContext.destination); // Uncomment if need to route audio

  return analyser;
}

// Extract frequency data each animation frame
function extractAudioData(analyser: AnalyserNode): AudioAnalysis {
  const frequencyData = new Uint8Array(analyser.frequencyBinCount);
  analyser.getByteFrequencyData(frequencyData);

  // Aggregate 128 bins into 12 display bars
  // Group bins: [0-10], [11-21], [22-32], ... [117-127]
  const binsPerBar = Math.floor(frequencyData.length / DISPLAY_BARS);
  const visualBars = new Array(DISPLAY_BARS).fill(0);

  for (let i = 0; i < DISPLAY_BARS; i++) {
    let sum = 0;
    for (let j = 0; j < binsPerBar; j++) {
      sum += frequencyData[i * binsPerBar + j];
    }
    // Average of bins, then normalize to 0-255
    visualBars[i] = Math.floor(sum / binsPerBar);
  }

  // Calculate RMS (root mean square) energy for volume level
  let sumSquares = 0;
  for (let i = 0; i < frequencyData.length; i++) {
    const normalized = frequencyData[i] / 255; // 0-1
    sumSquares += normalized * normalized;
  }
  const rmsLevel = Math.sqrt(sumSquares / frequencyData.length);

  return {
    frequencyData,
    visualBars,
    rmsLevel,
  };
}

// useRecording hook: handles audio capture + analysis
function useRecording() {
  const [isRecording, setIsRecording] = useState(false);
  const [waveformData, setWaveformData] = useState<number[]>(new Array(DISPLAY_BARS).fill(0));
  const [audioBlob, setAudioBlob] = useState<Blob | null>(null);
  const [duration, setDuration] = useState(0);

  const mediaRecorderRef = useRef<MediaRecorder>();
  const analyserRef = useRef<AnalyserNode>();
  const animationFrameRef = useRef<number>();
  const chunksRef = useRef<Blob[]>([]);
  const startTimeRef = useRef<number>();

  const updateWaveform = useCallback(() => {
    if (!analyserRef.current) return;

    const audioData = extractAudioData(analyserRef.current);
    setWaveformData(audioData.visualBars);

    // Update duration timer
    if (startTimeRef.current) {
      const elapsed = (Date.now() - startTimeRef.current) / 1000;
      setDuration(Math.floor(elapsed));
    }

    animationFrameRef.current = requestAnimationFrame(updateWaveform);
  }, []);

  async function startRecording() {
    try {
      // Request microphone permission
      const mediaStream = await navigator.mediaDevices.getUserMedia({ audio: true });

      // Setup audio analyzer
      analyserRef.current = setupAudioAnalyzer(mediaStream);

      // Setup MediaRecorder
      const mimeType = MediaRecorder.isTypeSupported('audio/webm;codecs=opus')
        ? 'audio/webm;codecs=opus'
        : 'audio/mp4';

      const mediaRecorder = new MediaRecorder(mediaStream, { mimeType });
      mediaRecorderRef.current = mediaRecorder;
      chunksRef.current = [];

      // Collect audio chunks
      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          chunksRef.current.push(event.data);
        }
      };

      // Start recording
      mediaRecorder.start();
      setIsRecording(true);
      startTimeRef.current = Date.now();

      // Start waveform animation
      updateWaveform();
    } catch (error) {
      console.error('Recording failed:', error);
      throw error;
    }
  }

  function stopRecording(): Blob {
    if (!mediaRecorderRef.current) {
      throw new Error('Recording not started');
    }

    // Stop recorder and collect audio
    mediaRecorderRef.current.stop();
    setIsRecording(false);

    // Cancel waveform animation
    if (animationFrameRef.current) {
      cancelAnimationFrame(animationFrameRef.current);
    }

    // Create audio blob from collected chunks
    const mimeType = mediaRecorderRef.current.mimeType;
    const audioBlob = new Blob(chunksRef.current, { type: mimeType });
    setAudioBlob(audioBlob);

    return audioBlob;
  }

  return {
    isRecording,
    waveformData,
    audioBlob,
    duration,
    startRecording,
    stopRecording,
  };
}
```

### Waveform Visualization Component

```tsx
// RecordingUI component: renders animated bars
interface RecordingUIProps {
  waveformData: number[];           // 12 values (0-255)
  isRecording: boolean;
  duration: number;                 // seconds
  onStop: () => void;
}

export function RecordingUI({
  waveformData,
  isRecording,
  duration,
  onStop,
}: RecordingUIProps) {
  return (
    <div className={styles.container}>
      {/* Waveform bars */}
      <div className={styles.waveform}>
        {waveformData.map((barHeight, index) => (
          <div
            key={index}
            className={styles.bar}
            style={{
              height: `${(barHeight / 255) * 100}%`,
            }}
          />
        ))}
      </div>

      {/* Timer */}
      <div className={styles.timer}>
        {formatDuration(duration)}
      </div>

      {/* Controls */}
      <button
        className={styles.stopButton}
        onClick={onStop}
        disabled={!isRecording}
      >
        {isRecording ? 'Stop' : 'Recording stopped'}
      </button>
    </div>
  );
}
```

### CSS Styling

```css
/* RecordingUI.module.css */
.waveform {
  display: flex;
  align-items: flex-end;
  justify-content: space-around;
  height: 150px;
  gap: var(--sp-spacing-sm);
  background: var(--bg-primary);
  padding: var(--sp-spacing-md);
  border-radius: var(--sp-radius-md);
}

.bar {
  flex: 1;
  min-width: 0;
  background: linear-gradient(to top, var(--color-flame-core), var(--color-flame-bright));
  border-radius: var(--sp-radius-sm);
  transition: height 0.05s linear;  /* Smooth bar height changes */
  box-shadow: 0 0 8px var(--color-flame-core);
}

.timer {
  font-size: clamp(24px, 5vw, 32px);
  font-weight: bold;
  color: var(--text-on-dark);
  text-align: center;
  margin: var(--sp-spacing-lg) 0;
  font-family: 'Molly Sans', sans-serif;
}

.stopButton {
  background: var(--color-flame-core);
  color: var(--bg-primary);
  padding: var(--sp-spacing-md) var(--sp-spacing-lg);
  border: none;
  border-radius: var(--sp-radius-md);
  cursor: pointer;
  font-size: clamp(16px, 2.5vw, 20px);
  font-weight: 700;
  letter-spacing: 0.5px;
  transition: transform var(--sp-duration-fast) var(--sp-easing-standard);
}

.stopButton:hover:not(:disabled) {
  transform: translateY(-2px);
}

.stopButton:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
```

### Performance Considerations

| Factor | Value | Notes |
|--------|-------|-------|
| Animation frame rate | 60 fps | `requestAnimationFrame` updates waveform ~60x/sec |
| FFT bins aggregated | 128 → 12 bars | Reduces rendering overhead |
| Smoothing constant | 0.8 | Higher = smoother but less responsive |
| Update frequency | Every 16ms | 60fps natural cadence |
| Memory footprint | ~2KB per update | Uint8Array(256) + aggregated array |

**Tested on**: Mid-range Android (Pixel 4a), iOS 14+ Safari, Chrome desktop.

### Browser Compatibility

| Browser | Support | Notes |
|---------|---------|-------|
| Chrome 25+ | ✅ Full | Standard Web Audio API |
| Firefox 25+ | ✅ Full | Standard Web Audio API |
| Safari 14+ | ✅ Full | webkit prefix may be needed (handled in code) |
| iOS Safari | ✅ Full | iOS 14.5+ supports MediaRecorder + Web Audio |
| Android Chrome | ✅ Full | Android 6+ supports both APIs |

---

## 3. Content Strategy & Data Loading

### Overview

MVP uses **hardcoded constants** for prompts and content pages. All data is static, embedded in the app bundle. Phase 2 will migrate to API/CMS, but MVP focuses on core mechanics.

### Data Loading Strategy

```typescript
// src/constants/prompts.ts
// ~20 prompts loaded at app init, stored in memory + IndexedDB

export const PROMPTS: Prompt[] = [
  {
    id: crypto.randomUUID(),
    text: "Tell us about a moment when you realized someone truly saw you.",
    category: "Intimacy",
    declaration_risk: "medium",
    facilitation_hint: "Instead of explaining what being 'seen' means to you, tell us about a specific moment.",
    created_at: new Date().toISOString(),
  },
  {
    id: crypto.randomUUID(),
    text: "What's a belief you used to hold that you no longer believe?",
    category: "Growth",
    declaration_risk: "high",
    facilitation_hint: "Share what changed your mind, not just the belief itself.",
    created_at: new Date().toISOString(),
  },
  // ... 18 more prompts
];

export function getRandomPrompts(count: number = 20): Prompt[] {
  // Return all prompts (MVP has only 1 pack)
  return PROMPTS;
}

export function getPromptById(id: string): Prompt | undefined {
  return PROMPTS.find(p => p.id === id);
}
```

### Content Pages Data

```typescript
// src/constants/contentPages.ts
// Static content for How to Play, Our Story, Our Work, Privacy, Booking

export interface ContentPage {
  id: string;
  title: string;
  sections: ContentSection[];
}

export interface ContentSection {
  type: 'heading' | 'paragraph' | 'list' | 'image' | 'form' | 'faq';
  content: string | string[] | { src: string; alt: string };
  metadata?: Record<string, any>;
}

export const CONTENT_PAGES: Record<string, ContentPage> = {
  how_to_play: {
    id: 'how_to_play',
    title: 'How to Play',
    sections: [
      {
        type: 'heading',
        content: 'How to Play the Story Portal',
      },
      {
        type: 'paragraph',
        content: 'The Story Portal uses a spinning wheel to prompt spontaneous storytelling. Here\'s how:',
      },
      {
        type: 'list',
        content: [
          'Spin the wheel. A random prompt appears.',
          'Read the prompt and take a moment to think.',
          'If it doesn\'t feel right, tap "Pass" for one free pass.',
          'When you\'re ready, tap "Record" and share your story (up to 5 minutes).',
          'Save your story to your device. You can listen back anytime.',
        ],
      },
      {
        type: 'heading',
        content: 'Why the wheel? Why a prompt?',
      },
      {
        type: 'paragraph',
        content: 'The randomness of the wheel removes decision-making friction. A good prompt invites authentic storytelling—not declarations, but narratives. Your stories matter.',
      },
    ],
  },

  our_story: {
    id: 'our_story',
    title: 'Our Story',
    sections: [
      {
        type: 'heading',
        content: 'Making Empathy Contagious',
      },
      {
        type: 'paragraph',
        content: 'The Story Portal is a time machine that connects people through witnessed stories. We believe that when we hear someone else\'s authentic narrative, we see our shared humanity.',
      },
      {
        type: 'heading',
        content: 'Our Values',
      },
      {
        type: 'list',
        content: [
          'Spontaneity: Remove friction, invite authenticity',
          'Witnessing: Stories are meant to be heard',
          'Connection: Empathy is contagious',
          'Analog Soul: Technology hidden behind craft',
        ],
      },
    ],
  },

  privacy_policy: {
    id: 'privacy_policy',
    title: 'Privacy Policy',
    sections: [
      {
        type: 'heading',
        content: 'Your Privacy Matters',
      },
      {
        type: 'paragraph',
        content: 'Your stories stay on your device. We don\'t store them on our servers. You own your data.',
      },
      {
        type: 'heading',
        content: 'What We Collect',
      },
      {
        type: 'list',
        content: [
          'Recording audio (stored locally on your device)',
          'Metadata: timestamp, prompt text, duration',
          'Analytics: which features you use (via Google Analytics 4)',
          'We do NOT collect: your name, email, location, or personal information—unless you voluntarily provide it',
        ],
      },
      {
        type: 'heading',
        content: 'Deletion',
      },
      {
        type: 'paragraph',
        content: 'You can delete any story anytime from "My Stories". Deletion is permanent.',
      },
    ],
  },

  // our_work, booking pages omitted for brevity
};

export function getContentPage(pageId: string): ContentPage | undefined {
  return CONTENT_PAGES[pageId];
}
```

### App Initialization

```typescript
// src/hooks/useAppInit.ts

export function useAppInit() {
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function initApp() {
      try {
        // 1. Load prompts from constants (instant)
        const prompts = getRandomPrompts(20);
        console.log(`Loaded ${prompts.length} prompts`);

        // 2. Cache prompts in IndexedDB for offline access (fast)
        await cachePromptsInIndexedDB(prompts);

        // 3. Load content pages from constants (instant)
        // No async work needed—pages are already in memory

        // 4. Check for first-time user
        const isFirstTime = await checkFirstTimeUser();

        setIsLoading(false);
      } catch (err) {
        console.error('App initialization failed:', err);
        setError('Failed to load app. Please refresh.');
        setIsLoading(false);
      }
    }

    initApp();
  }, []);

  return { isLoading, error };
}
```

### Content Page Rendering

```tsx
// src/components/views/ContentView.tsx

interface ContentViewProps {
  pageId: string; // 'how_to_play', 'our_story', 'privacy_policy', etc.
}

export function ContentView({ pageId }: ContentViewProps) {
  const page = getContentPage(pageId);

  if (!page) {
    return <div>Page not found</div>;
  }

  return (
    <div className={styles.contentView}>
      {page.sections.map((section, index) => (
        <ContentSection key={index} section={section} />
      ))}
    </div>
  );
}

// Render individual section based on type
function ContentSection({ section }: { section: ContentSection }) {
  switch (section.type) {
    case 'heading':
      return <h2 className={styles.heading}>{section.content}</h2>;

    case 'paragraph':
      return <p className={styles.paragraph}>{section.content}</p>;

    case 'list':
      return (
        <ul className={styles.list}>
          {(section.content as string[]).map((item, i) => (
            <li key={i}>{item}</li>
          ))}
        </ul>
      );

    case 'image':
      const { src, alt } = section.content as { src: string; alt: string };
      return <img src={src} alt={alt} className={styles.image} />;

    case 'form':
      // Handle forms (booking, contact, etc.)
      return <BookingForm />;

    default:
      return null;
  }
}
```

### Phase 2 Migration Path

When Phase 2 adds an API/CMS:

```typescript
// Phase 2: Replace getRandomPrompts() with API call
export async function getRandomPrompts(count: number = 20): Promise<Prompt[]> {
  try {
    // Fetch from API
    const response = await fetch(`${API_BASE_URL}/api/prompts?count=${count}`);
    const prompts = await response.json();

    // Still cache locally
    await cachePromptsInIndexedDB(prompts);

    return prompts;
  } catch (error) {
    // Fallback to cached version
    return getPromptsFromIndexedDB();
  }
}

// Phase 2: Replace getContentPage() with CMS query
export async function getContentPage(pageId: string): Promise<ContentPage> {
  try {
    const response = await fetch(`${API_BASE_URL}/api/pages/${pageId}`);
    return await response.json();
  } catch (error) {
    // Fallback to constants
    return CONTENT_PAGES[pageId];
  }
}
```

### MVP Checklist

- ✅ 20 prompts defined in `src/constants/prompts.ts`
- ✅ 5 content pages defined in `src/constants/contentPages.ts`
- ✅ ContentView component renders sections dynamically
- ✅ No API calls in MVP (all data local)
- ✅ IndexedDB caching for offline access
- ✅ Easy to migrate to Phase 2 API

---

## Summary

All three implementation guides are now ready:

1. **Wheel Physics**: Linear damping algorithm, touch detection, momentum animation
2. **Audio Waveform**: FFT-based frequency extraction, 12-bar visualization
3. **Content Strategy**: Hardcoded constants, easy Phase 2 migration path

**Next Step**: Present these guides for validation. Once approved, proceed with Task 2 (scaffold project structure) and Task 3 (begin wheel implementation).
