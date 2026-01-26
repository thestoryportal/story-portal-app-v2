# Steam Modal - Quick Start Guide

## 5-Minute Setup

### Step 1: Copy the Components

Copy the entire `components/` folder to your project:

```bash
cp -r steam-modal-package/components/ your-project/src/components/steam-modal/
```

### Step 2: Import and Use

```tsx
import { useState } from 'react';
import { SteamModal, ContentParagraph } from './components/steam-modal';

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
          Your content here...
        </ContentParagraph>
      </SteamModal>
    </>
  );
}
```

### Step 3: Verify

1. Start your dev server: `npm run dev`
2. Click the button to open the modal
3. Check that:
   - [ ] Steam is warm brown (not amber/orange)
   - [ ] Text is dark on parchment (readable)
   - [ ] Modal closes when clicking X, Escape, or backdrop
   - [ ] No stacking when opening/closing multiple times

---

## Common Issues

### "Module not found"

Make sure the path matches where you copied the files:

```tsx
// If you copied to src/components/steam-modal/
import { SteamModal } from './components/steam-modal';

// If you copied to src/ui/steam-modal/
import { SteamModal } from './ui/steam-modal';
```

### "CSS not loading"

Ensure your bundler supports CSS Modules (`.module.css` files).

For Vite, this works out of the box.

For Create React App, this works out of the box.

For Next.js, this works out of the box.

### "Fonts not showing"

The modal expects these fonts to be available:
- `Carnivalee Freakshow` (display)
- `Molly Sans` (body)

If you don't have these fonts, update the CSS files to use your project's fonts:

```css
/* In ContentPanel.module.css */
.sectionTitle {
  font-family: 'Your Display Font', serif;
}

.bodyText {
  font-family: 'Your Body Font', sans-serif;
}
```

---

## Props Reference

### SteamModal

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| `isOpen` | `boolean` | required | Whether modal is visible |
| `onClose` | `() => void` | required | Called when modal should close |
| `title` | `string` | required | Header title |
| `children` | `ReactNode` | required | Modal content |
| `variant` | `'standard' \| 'form' \| 'gallery' \| 'legal'` | `'standard'` | Content variant |
| `steamDensity` | `'light' \| 'medium' \| 'dense'` | varies by variant | Steam opacity |
| `onOpened` | `() => void` | - | Called after open animation |
| `onClosed` | `() => void` | - | Called after close animation |

### ContentParagraph

| Prop | Type | Default | Description |
|------|------|---------|-------------|
| `children` | `ReactNode` | required | Paragraph text |
| `index` | `number` | `0` | Animation stagger index |

---

## That's It!

The modal should now be working. If you need more customization, see the full README.md.
