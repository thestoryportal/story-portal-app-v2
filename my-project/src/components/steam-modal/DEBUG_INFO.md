# Debug Information for Steam Modal

## What to Check in Browser DevTools

### 1. Check if components are rendering:
Open browser DevTools (F12) and:
1. Go to Elements/Inspector tab
2. Look for these elements at the END of `<body>`:
   - A `<div>` with `role="dialog"`
   - Inside it should be:
     - A div with class starting with `backdrop_`
     - A div with class starting with `steamField_`
     - A div with class starting with `header_` (wood panel)
     - A div with class starting with `contentPanel_` (parchment)
     - A button with class starting with `closeButton_`

### 2. Check CSS Modules are loading:
In DevTools:
1. Go to Sources tab
2. Look for files under `src/components/steam-modal/`
3. Check if `.module.css` files are there
4. Click on one and verify styles are present

### 3. Check for console errors:
1. Go to Console tab
2. Look for any errors related to:
   - "Cannot read property" or "undefined"
   - CSS module imports
   - React errors

### 4. Check computed styles:
1. Inspect the dialog element
2. Check Computed styles tab
3. Verify z-index is 1000+
4. Check if position is fixed
5. Check if inset is 0

### 5. Check if portal is working:
The modal should render at the END of `<body>`, not inside your app's root div.
If it's inside the app root, the portal isn't working.

## Common Issues

### Issue: Modal div exists but nothing visible
- **Cause**: Z-index conflict with existing app elements
- **Fix**: Check if something else has z-index > 9999

### Issue: No backdrop/steam/header visible
- **Cause**: CSS modules not loading or class names not matching
- **Fix**: Check if class names in DOM match pattern `[filename]_[className]_[hash]`

### Issue: Modal completely missing from DOM
- **Cause**: Component not rendering at all
- **Fix**: Check console for React errors

### Issue: Styles not applied
- **Cause**: CSS module import path wrong or Vite not processing
- **Fix**: Restart dev server, check import paths

## Quick Test

Add this to your browser console when modal is open:

```javascript
// Check if modal container exists
const modal = document.querySelector('[role="dialog"]');
console.log('Modal exists:', !!modal);

// Check computed styles
if (modal) {
  const styles = window.getComputedStyle(modal);
  console.log('Z-index:', styles.zIndex);
  console.log('Position:', styles.position);
  console.log('Display:', styles.display);
}

// Check for backdrop
const backdrop = document.querySelector('[class*="backdrop"]');
console.log('Backdrop exists:', !!backdrop);

// Check for header
const header = document.querySelector('[class*="header"]');
console.log('Header exists:', !!header);
if (header) {
  const headerStyles = window.getComputedStyle(header);
  console.log('Header background:', headerStyles.background);
  console.log('Header z-index:', headerStyles.zIndex);
}
```
