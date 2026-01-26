/**
 * Comprehensive DOM and Style Diagnostic for Steam Modal
 *
 * INSTRUCTIONS:
 * 1. Open http://localhost:5173/?test=modal
 * 2. Open DevTools (F12) → Console tab
 * 3. Copy this entire file and paste into console
 * 4. Press Enter to run
 * 5. Copy ALL the output and share it
 */

console.clear();
console.log('%c=== STEAM MODAL COMPREHENSIVE DIAGNOSTIC ===', 'font-size: 16px; font-weight: bold; color: #ff6600;');
console.log('\n');

// Check 1: Find the modal container
console.log('%c1. MODAL CONTAINER CHECK', 'font-weight: bold; color: #00aaff;');
const modal = document.querySelector('[role="dialog"]');
if (!modal) {
  console.error('❌ CRITICAL: No modal with role="dialog" found!');
  console.log('The modal is not rendering at all. Check if SteamModal component is mounted.');
} else {
  console.log('✓ Modal container found');
  console.log('  - classList:', Array.from(modal.classList));
  console.log('  - data-variant:', modal.getAttribute('data-variant'));
  console.log('  - data-closing:', modal.getAttribute('data-closing'));

  const computed = window.getComputedStyle(modal);
  console.log('  - Position:', computed.position);
  console.log('  - Z-index:', computed.zIndex);
  console.log('  - Display:', computed.display);
  console.log('  - Visibility:', computed.visibility);
}
console.log('\n');

// Check 2: Find and inspect Backdrop
console.log('%c2. BACKDROP CHECK', 'font-weight: bold; color: #00aaff;');
const backdrop = document.querySelector('[class*="backdrop"]');
if (!backdrop) {
  console.error('❌ CRITICAL: No backdrop element found!');
} else {
  console.log('✓ Backdrop found');
  console.log('  - className:', backdrop.className);

  const computed = window.getComputedStyle(backdrop);
  console.log('  - Position:', computed.position);
  console.log('  - Z-index:', computed.zIndex);
  console.log('  - Background:', computed.background.substring(0, 100) + '...');
  console.log('  - Opacity:', computed.opacity);
  console.log('  - Display:', computed.display);
  console.log('  - Top:', computed.top, 'Left:', computed.left, 'Width:', computed.width, 'Height:', computed.height);
}
console.log('\n');

// Check 3: Find and inspect SteamField
console.log('%c3. STEAM FIELD CHECK', 'font-weight: bold; color: #00aaff;');
const steamField = document.querySelector('[class*="steamField"]');
if (!steamField) {
  console.error('❌ CRITICAL: No steam field element found!');
} else {
  console.log('✓ Steam field found');
  console.log('  - className:', steamField.className);

  const computed = window.getComputedStyle(steamField);
  console.log('  - Position:', computed.position);
  console.log('  - Z-index:', computed.zIndex);
  console.log('  - Opacity:', computed.opacity);
  console.log('  - Display:', computed.display);
  console.log('  - Overflow:', computed.overflow);

  // Check steam layers
  const baseCloud = steamField.querySelector('[class*="baseCloud"]');
  const wispLeft = steamField.querySelector('[class*="wispLeft"]');
  const wispRight = steamField.querySelector('[class*="wispRight"]');

  console.log('  - Steam layers:');
  console.log('    • baseCloud:', baseCloud ? '✓ found' : '❌ missing');
  console.log('    • wispLeft:', wispLeft ? '✓ found' : '❌ missing');
  console.log('    • wispRight:', wispRight ? '✓ found' : '❌ missing');

  if (baseCloud) {
    const cloudComputed = window.getComputedStyle(baseCloud);
    console.log('    • baseCloud background:', cloudComputed.background.substring(0, 80) + '...');
    console.log('    • baseCloud opacity:', cloudComputed.opacity);
    console.log('    • baseCloud animation:', cloudComputed.animation);
  }
}
console.log('\n');

// Check 4: Find and inspect PanelHeader
console.log('%c4. PANEL HEADER CHECK', 'font-weight: bold; color: #00aaff;');
const header = document.querySelector('[class*="header"][id="modal-title"]') ||
               document.querySelector('[class*="header"]');
if (!header) {
  console.error('❌ CRITICAL: No panel header element found!');
} else {
  console.log('✓ Panel header found');
  console.log('  - className:', header.className);

  const computed = window.getComputedStyle(header);
  console.log('  - Position:', computed.position);
  console.log('  - Z-index:', computed.zIndex);
  console.log('  - Background:', computed.background.substring(0, 100) + '...');
  console.log('  - Border:', computed.border);
  console.log('  - Opacity:', computed.opacity);
  console.log('  - Display:', computed.display);
  console.log('  - Transform:', computed.transform);
  console.log('  - Animation:', computed.animation);
  console.log('  - Top:', computed.top, 'Left:', computed.left);

  // Check title
  const title = header.querySelector('[class*="title"]');
  if (title) {
    const titleComputed = window.getComputedStyle(title);
    console.log('  - Title text:', title.textContent);
    console.log('  - Title font-family:', titleComputed.fontFamily);
    console.log('  - Title color:', titleComputed.color);
    console.log('  - Title font-size:', titleComputed.fontSize);
  }
}
console.log('\n');

// Check 5: Find and inspect ContentPanel
console.log('%c5. CONTENT PANEL CHECK', 'font-weight: bold; color: #00aaff;');
const contentPanel = document.querySelector('[class*="contentPanel"]');
if (!contentPanel) {
  console.error('❌ CRITICAL: No content panel element found!');
} else {
  console.log('✓ Content panel found');
  console.log('  - className:', contentPanel.className);

  const computed = window.getComputedStyle(contentPanel);
  console.log('  - Position:', computed.position);
  console.log('  - Z-index:', computed.zIndex);
  console.log('  - Background:', computed.background);
  console.log('  - Opacity:', computed.opacity);
  console.log('  - Display:', computed.display);
  console.log('  - Max-width:', computed.maxWidth);
  console.log('  - Margin:', computed.margin);
  console.log('  - Padding:', computed.padding);
  console.log('  - Transform:', computed.transform);
  console.log('  - Animation:', computed.animation);
}
console.log('\n');

// Check 6: Find and inspect CloseButton
console.log('%c6. CLOSE BUTTON CHECK', 'font-weight: bold; color: #00aaff;');
const closeButton = document.querySelector('[class*="closeButton"]') ||
                    document.querySelector('button[aria-label="Close modal"]');
if (!closeButton) {
  console.error('❌ CRITICAL: No close button element found!');
} else {
  console.log('✓ Close button found');
  console.log('  - className:', closeButton.className);

  const computed = window.getComputedStyle(closeButton);
  console.log('  - Position:', computed.position);
  console.log('  - Z-index:', computed.zIndex);
  console.log('  - Background:', computed.background.substring(0, 100) + '...');
  console.log('  - Border:', computed.border);
  console.log('  - Opacity:', computed.opacity);
  console.log('  - Display:', computed.display);
  console.log('  - Top:', computed.top, 'Right:', computed.right);
  console.log('  - Animation:', computed.animation);
}
console.log('\n');

// Check 7: CSS Animation Status
console.log('%c7. ANIMATION STATUS CHECK', 'font-weight: bold; color: #00aaff;');
if (header) {
  const animations = header.getAnimations();
  console.log('Header animations:', animations.length > 0 ? animations.map(a => ({
    name: a.animationName,
    playState: a.playState,
    currentTime: a.currentTime,
    duration: a.effect?.getTiming().duration
  })) : 'No animations running');
}
console.log('\n');

// Check 8: Visual Bounding Rects
console.log('%c8. VISUAL POSITION CHECK', 'font-weight: bold; color: #00aaff;');
console.log('Element positions on screen:');
if (modal) {
  const rect = modal.getBoundingClientRect();
  console.log('  Modal:', {
    visible: rect.width > 0 && rect.height > 0,
    top: rect.top,
    left: rect.left,
    width: rect.width,
    height: rect.height
  });
}
if (backdrop) {
  const rect = backdrop.getBoundingClientRect();
  console.log('  Backdrop:', {
    visible: rect.width > 0 && rect.height > 0,
    top: rect.top,
    left: rect.left,
    width: rect.width,
    height: rect.height,
    coversViewport: rect.width >= window.innerWidth && rect.height >= window.innerHeight
  });
}
if (header) {
  const rect = header.getBoundingClientRect();
  console.log('  Header:', {
    visible: rect.width > 0 && rect.height > 0,
    top: rect.top,
    left: rect.left,
    width: rect.width,
    height: rect.height,
    inViewport: rect.top >= 0 && rect.top < window.innerHeight
  });
}
if (contentPanel) {
  const rect = contentPanel.getBoundingClientRect();
  console.log('  Content:', {
    visible: rect.width > 0 && rect.height > 0,
    top: rect.top,
    left: rect.left,
    width: rect.width,
    height: rect.height,
    inViewport: rect.top >= 0 && rect.top < window.innerHeight
  });
}
console.log('\n');

// Check 9: Check for elements covering the modal
console.log('%c9. Z-INDEX CONFLICT CHECK', 'font-weight: bold; color: #00aaff;');
const allElements = Array.from(document.querySelectorAll('*'));
const highZIndex = allElements
  .filter(el => {
    const z = parseInt(window.getComputedStyle(el).zIndex);
    return !isNaN(z) && z >= 1000;
  })
  .map(el => ({
    element: el.tagName + (el.className ? '.' + el.className.split(' ')[0] : ''),
    zIndex: window.getComputedStyle(el).zIndex,
    position: window.getComputedStyle(el).position
  }))
  .sort((a, b) => parseInt(b.zIndex) - parseInt(a.zIndex));

console.log('Elements with z-index >= 1000:');
console.table(highZIndex.slice(0, 10));
console.log('\n');

// Final summary
console.log('%c=== DIAGNOSTIC SUMMARY ===', 'font-size: 14px; font-weight: bold; color: #00ff00;');
console.log('Modal found:', modal ? '✓' : '❌');
console.log('Backdrop found:', backdrop ? '✓' : '❌');
console.log('Steam field found:', steamField ? '✓' : '❌');
console.log('Header found:', header ? '✓' : '❌');
console.log('Content panel found:', contentPanel ? '✓' : '❌');
console.log('Close button found:', closeButton ? '✓' : '❌');
console.log('\n');
console.log('%cPlease copy ALL of this output and share it.', 'font-weight: bold; color: #ff6600;');
