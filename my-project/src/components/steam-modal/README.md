# Steam Modal Component

A theatrical steam/smoke modal system where content materializes from atmospheric steam effects.

## Features

- **Atmospheric Steam Effects**: Warm brown/tan steam that matches the existing app aesthetic
- **High Contrast Content**: Parchment background (#f4e4c8) with dark brown text (#2a1a0a) for 14:1 contrast ratio
- **Animated Wooden Header**: Panel header that tumbles in from above
- **Proper Lifecycle Management**: No stacking issues, clean mount/unmount
- **Accessibility**: Focus management, keyboard support (Escape key)
- **Multiple Variants**: Standard, form, gallery, and legal variants with different steam densities

## Quick Start

```tsx
import { useState } from 'react';
import { SteamModal, ContentParagraph, ContentDivider } from './components/steam-modal';

function App() {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <>
      <button onClick={() => setIsOpen(true)}>
        Open Modal
      </button>

      <SteamModal
        isOpen={isOpen}
        onClose={() => setIsOpen(false)}
        title="Our Story"
      >
        <ContentParagraph index={0}>
          Welcome to The Story Portal, where tales come alive through
          the breath of the machine.
        </ContentParagraph>

        <ContentDivider />

        <ContentParagraph index={1}>
          Every story you share becomes part of our collective memory,
          preserved in steam and brass.
        </ContentParagraph>
      </SteamModal>
    </>
  );
}
```

## Props

### SteamModal

| Prop | Type | Default | Required | Description |
|------|------|---------|----------|-------------|
| `isOpen` | `boolean` | - | Yes | Whether modal is visible |
| `onClose` | `() => void` | - | Yes | Called when modal should close |
| `title` | `string` | - | Yes | Header title |
| `children` | `ReactNode` | - | Yes | Modal content |
| `variant` | `'standard' \| 'form' \| 'gallery' \| 'legal'` | `'standard'` | No | Content variant |
| `steamDensity` | `'light' \| 'medium' \| 'dense'` | varies | No | Steam opacity |
| `onOpened` | `() => void` | - | No | Called after open animation |
| `onClosed` | `() => void` | - | No | Called after close animation |

### ContentParagraph

| Prop | Type | Default | Required | Description |
|------|------|---------|----------|-------------|
| `children` | `ReactNode` | - | Yes | Paragraph text |
| `index` | `number` | `0` | No | Animation stagger index |

### ContentDivider

No props. Creates a decorative divider between content sections.

### ContentSection

| Prop | Type | Default | Required | Description |
|------|------|---------|----------|-------------|
| `title` | `string` | - | Yes | Section title |
| `children` | `ReactNode` | - | Yes | Section content |

## Variants

### Standard
Default variant with medium steam density. Best for general content.

```tsx
<SteamModal variant="standard" title="Our Story">
  {/* content */}
</SteamModal>
```

### Form
Light steam density for better visibility of form elements.

```tsx
<SteamModal variant="form" title="Book Your Experience">
  <form>{/* form fields */}</form>
</SteamModal>
```

### Legal
Light steam density for better readability of legal text.

```tsx
<SteamModal variant="legal" title="Privacy Policy">
  {/* legal content */}
</SteamModal>
```

### Gallery
Medium steam density for viewing images or media.

```tsx
<SteamModal variant="gallery" title="Photo Gallery">
  {/* gallery content */}
</SteamModal>
```

## Multiple Modals

When using multiple modals, use a single state variable to prevent stacking issues:

```tsx
type ModalType = 'story' | 'booking' | 'privacy' | null;

function App() {
  const [activeModal, setActiveModal] = useState<ModalType>(null);

  return (
    <>
      <button onClick={() => setActiveModal('story')}>Our Story</button>
      <button onClick={() => setActiveModal('booking')}>Book Now</button>

      {activeModal === 'story' && (
        <SteamModal
          isOpen={true}
          onClose={() => setActiveModal(null)}
          title="Our Story"
        >
          {/* content */}
        </SteamModal>
      )}

      {activeModal === 'booking' && (
        <SteamModal
          isOpen={true}
          onClose={() => setActiveModal(null)}
          title="Book Now"
          variant="form"
        >
          {/* booking form */}
        </SteamModal>
      )}
    </>
  );
}
```

## Closing Methods

The modal can be closed in three ways:

1. **Click the X button** (top-right)
2. **Press Escape key**
3. **Click the backdrop** (outside the content area)

## Color Palette

The steam effects use colors from the existing `SmokeEffect.tsx`:

- Main cloud: `rgba(140, 120, 100, 0.12)`
- Wisps: `rgba(130, 110, 90, 0.08)`
- Rising steam: `rgba(140, 120, 100, 0.07)`

Content panel uses high contrast colors:

- Background: `#f4e4c8` (parchment)
- Text: `#2a1a0a` (dark brown)
- Contrast ratio: 14:1 (WCAG AAA compliant)

## Examples

See `USAGE_EXAMPLES.tsx` for more detailed examples including:

- Basic usage
- Form variant with booking
- Legal variant with privacy policy
- Multiple modal state management
- Callbacks for tracking

## Accessibility

- Focus is trapped within the modal when open
- Escape key closes the modal
- Focus is restored to the previous element when closed
- ARIA attributes for screen readers
- High contrast text (14:1 ratio) exceeds WCAG AAA standards
- Keyboard navigation supported

## Browser Support

Requires:
- CSS Modules support (Vite, CRA, Next.js all work out of the box)
- React 16.8+ (hooks)
- Modern browsers with CSS animation support

## License

Part of The Story Portal project.
