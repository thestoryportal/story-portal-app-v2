# Troubleshooting: Steam Modal CSS Not Loading

## Problem Description
User reports seeing the modal but without proper styling:
- ❌ No wood panel heading
- ❌ No smoke/steam background
- ❌ No animations

This indicates **components are rendering but CSS modules are not being applied**.

## Quick Diagnosis Steps

### Step 1: Check Dev Server Port
Your dev server is running. Open your browser to:
```
http://localhost:5173/?test=modal
```

### Step 2: Run the COMPREHENSIVE Diagnostic
1. Open DevTools (F12) → Console tab
2. Open the file `DIAGNOSTIC-SCRIPT.js` in your project root
3. Copy the ENTIRE contents of that file
4. Paste into the browser console and press Enter
5. The script will output a comprehensive analysis of what's happening

### Step 3 (Alternative): Run the Quick CSS Diagnostic
On the test page, click the red **"🔍 Run Diagnostic"** button.

Then check the browser console for output starting with:
```
=== CSS Module Diagnostic ===
```

### What To Look For:

#### ✅ CSS Modules Working:
```javascript
Backdrop styles: { backdrop: "Backdrop_backdrop_a1b2c3" }
Header styles: { header: "PanelHeader_header_d4e5f6", title: "PanelHeader_title_g7h8i9" }
```
Classes have the pattern: `[filename]_[className]_[hash]`

#### ❌ CSS Modules NOT Working:
```javascript
Backdrop styles: {}
// or
Backdrop styles: { backdrop: "backdrop" }  // No hash!
```

## If CSS Modules Are NOT Loading:

### Fix 1: Clear Vite Cache
```bash
cd /Volumes/Extreme\ SSD/projects/story-portal-app/my-project
rm -rf node_modules/.vite
npm run dev
```

### Fix 2: Check Vite Config
Open `vite.config.ts` and ensure CSS modules are enabled (should be default):

```typescript
export default defineConfig({
  css: {
    modules: {
      localsConvention: 'camelCase', // or 'dashes'
    }
  }
})
```

### Fix 3: Verify File Extensions
All CSS files should be named `*.module.css` (not just `.css`)

Check:
```bash
ls -la src/components/steam-modal/*.module.css
```

You should see 6 files:
- Backdrop.module.css
- CloseButton.module.css
- ContentPanel.module.css
- PanelHeader.module.css
- SteamField.module.css
- SteamModal.module.css

### Fix 4: Check Import Statements
In each component file, imports should look like:
```typescript
import styles from './ComponentName.module.css';
```

NOT:
```typescript
import './ComponentName.module.css';  // ❌ Wrong!
```

## If CSS Modules ARE Loading But Styles Don't Apply:

### Check for Z-Index Conflicts
Run in browser console:
```javascript
const modal = document.querySelector('[role="dialog"]');
if (modal) {
  console.log('Z-index:', window.getComputedStyle(modal).zIndex);
  console.log('Position:', window.getComputedStyle(modal).position);
}
```

Z-index should be `1000` or higher.

### Check for CSS Specificity Issues
Inspect an element (like the backdrop) in DevTools → Styles tab.
Look for crossed-out styles indicating they're being overridden.

## Visual Tests on Diagnostic Page

When you click "Run Diagnostic", you should see:

1. **Backdrop Test**: Dark gradient background with vignette
2. **Header Test**: Brown wooden panel with bronze border and title
3. **Content Panel Test**: Parchment background (#f4e4c8) with dark brown text
4. **Steam Field Test**: Animated layers (may be subtle)

## Expected Final Appearance

When working correctly:
- **Layer 1 (Backdrop)**: Dark screen with warm vignette (not pure black)
- **Layer 2 (Steam)**: Warm brown/tan wisps floating and animating
- **Layer 3 (Header)**: Wooden panel at top with "Test Modal" in stylized font
- **Layer 4 (Content)**: Parchment-colored box in center with dark text
- **Layer 5 (Close Button)**: Brass circular X button in top-right

## Need More Help?

Share these diagnostic results:
1. Screenshot of the test page
2. Console output from diagnostic
3. Output of: `npm list vite react`
4. Browser and version you're using

## Quick Sanity Check

Run this in your project root:
```bash
# Check if CSS module files exist
find src/components/steam-modal -name "*.module.css" -type f

# Check if TypeScript is configured for CSS modules
grep -r "module.css" tsconfig.json vite.config.ts 2>/dev/null || echo "No CSS module config found"
```
