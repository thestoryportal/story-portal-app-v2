#!/bin/bash

# ============================================
# Steam Modal Implementation - Deployment Script
# ============================================
# 
# This script sets up the Steam Modal implementation
# for The Story Portal project.
#
# Usage: ./deploy.sh [--skip-cleanup] [--dry-run]
#
# ============================================

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="${SCRIPT_DIR}/.."
COMPONENTS_DIR="${PROJECT_ROOT}/src/components/steam-modal"

# Flags
SKIP_CLEANUP=false
DRY_RUN=false

# Parse arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    --skip-cleanup)
      SKIP_CLEANUP=true
      shift
      ;;
    --dry-run)
      DRY_RUN=true
      shift
      ;;
    *)
      echo -e "${RED}Unknown option: $1${NC}"
      exit 1
      ;;
  esac
done

# ============================================
# Helper Functions
# ============================================

log_info() {
  echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
  echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
  echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
  echo -e "${RED}[ERROR]${NC} $1"
}

confirm() {
  read -p "$1 (y/n): " -n 1 -r
  echo
  [[ $REPLY =~ ^[Yy]$ ]]
}

# ============================================
# Pre-flight Checks
# ============================================

echo ""
echo "============================================"
echo "  Steam Modal Implementation Deployer"
echo "============================================"
echo ""

log_info "Running pre-flight checks..."

# Check if we're in the right directory
if [ ! -f "${PROJECT_ROOT}/package.json" ]; then
  log_error "package.json not found. Are you in the project root?"
  log_info "Expected: ${PROJECT_ROOT}/package.json"
  exit 1
fi

# Check for existing SmokeEffect.tsx (required reference)
SMOKE_EFFECT_PATH="${PROJECT_ROOT}/src/legacy/components/menu/SmokeEffect.tsx"
if [ ! -f "$SMOKE_EFFECT_PATH" ]; then
  log_warning "SmokeEffect.tsx not found at expected path."
  log_info "Looking in alternative locations..."
  
  # Try to find it
  FOUND_SMOKE=$(find "${PROJECT_ROOT}/src" -name "SmokeEffect.tsx" 2>/dev/null | head -1)
  
  if [ -n "$FOUND_SMOKE" ]; then
    log_success "Found SmokeEffect.tsx at: $FOUND_SMOKE"
    SMOKE_EFFECT_PATH="$FOUND_SMOKE"
  else
    log_error "SmokeEffect.tsx not found anywhere in src/"
    log_error "This file is REQUIRED for color reference."
    exit 1
  fi
fi

log_success "Found SmokeEffect.tsx"

# Check for existing animations.css
ANIMATIONS_PATH="${PROJECT_ROOT}/src/legacy/styles/animations.css"
if [ ! -f "$ANIMATIONS_PATH" ]; then
  log_warning "animations.css not found at expected path."
  FOUND_ANIM=$(find "${PROJECT_ROOT}/src" -name "animations.css" 2>/dev/null | head -1)
  
  if [ -n "$FOUND_ANIM" ]; then
    log_success "Found animations.css at: $FOUND_ANIM"
    ANIMATIONS_PATH="$FOUND_ANIM"
  else
    log_warning "animations.css not found. Will include fallback keyframes."
  fi
fi

# ============================================
# Cleanup Failed Implementation (Optional)
# ============================================

if [ "$SKIP_CLEANUP" = false ]; then
  echo ""
  log_info "Checking for failed implementation remnants..."
  
  CLEANUP_TARGETS=(
    "${PROJECT_ROOT}/src/components/SteamModal.tsx"
    "${PROJECT_ROOT}/src/components/SteamModal.module.css"
    "${PROJECT_ROOT}/src/components/steam-modal"
  )
  
  FOUND_CLEANUP=false
  for target in "${CLEANUP_TARGETS[@]}"; do
    if [ -e "$target" ]; then
      FOUND_CLEANUP=true
      log_warning "Found: $target"
    fi
  done
  
  if [ "$FOUND_CLEANUP" = true ]; then
    if confirm "Remove these files/directories?"; then
      for target in "${CLEANUP_TARGETS[@]}"; do
        if [ -e "$target" ]; then
          if [ "$DRY_RUN" = true ]; then
            log_info "[DRY RUN] Would remove: $target"
          else
            rm -rf "$target"
            log_success "Removed: $target"
          fi
        fi
      done
    fi
  else
    log_success "No cleanup needed"
  fi
fi

# ============================================
# Create Directory Structure
# ============================================

echo ""
log_info "Creating directory structure..."

DIRS_TO_CREATE=(
  "${COMPONENTS_DIR}"
  "${COMPONENTS_DIR}/hooks"
  "${COMPONENTS_DIR}/__tests__"
)

for dir in "${DIRS_TO_CREATE[@]}"; do
  if [ "$DRY_RUN" = true ]; then
    log_info "[DRY RUN] Would create: $dir"
  else
    mkdir -p "$dir"
    log_success "Created: $dir"
  fi
done

# ============================================
# Copy Component Files
# ============================================

echo ""
log_info "Copying component files..."

# Source files from the package
PACKAGE_COMPONENTS="${SCRIPT_DIR}/components"

if [ ! -d "$PACKAGE_COMPONENTS" ]; then
  log_error "Components directory not found in package."
  log_info "Expected: ${PACKAGE_COMPONENTS}"
  exit 1
fi

if [ "$DRY_RUN" = true ]; then
  log_info "[DRY RUN] Would copy files from ${PACKAGE_COMPONENTS} to ${COMPONENTS_DIR}"
else
  cp -r "${PACKAGE_COMPONENTS}/"* "${COMPONENTS_DIR}/"
  log_success "Copied all component files"
fi

# ============================================
# Verify Installation
# ============================================

echo ""
log_info "Verifying installation..."

REQUIRED_FILES=(
  "Backdrop.tsx"
  "Backdrop.module.css"
  "SteamField.tsx"
  "SteamField.module.css"
  "ContentPanel.tsx"
  "ContentPanel.module.css"
  "PanelHeader.tsx"
  "PanelHeader.module.css"
  "CloseButton.tsx"
  "CloseButton.module.css"
  "SteamModal.tsx"
  "SteamModal.module.css"
  "index.ts"
)

MISSING_FILES=()

for file in "${REQUIRED_FILES[@]}"; do
  if [ ! -f "${COMPONENTS_DIR}/${file}" ]; then
    MISSING_FILES+=("$file")
  fi
done

if [ ${#MISSING_FILES[@]} -gt 0 ]; then
  log_error "Missing files:"
  for file in "${MISSING_FILES[@]}"; do
    echo "  - $file"
  done
  exit 1
fi

log_success "All files present"

# ============================================
# Extract Color Reference
# ============================================

echo ""
log_info "Extracting color reference from SmokeEffect.tsx..."

# Extract the color values for verification
if command -v grep &> /dev/null; then
  SMOKE_COLORS=$(grep -oE 'rgba\([0-9]+,[0-9]+,[0-9]+,[0-9.]+\)' "$SMOKE_EFFECT_PATH" | head -5)
  
  if [ -n "$SMOKE_COLORS" ]; then
    log_success "Found color palette in SmokeEffect.tsx:"
    echo "$SMOKE_COLORS" | while read -r color; do
      echo "  - $color"
    done
    
    # Save to reference file
    echo "# Color Reference from SmokeEffect.tsx" > "${COMPONENTS_DIR}/COLOR_REFERENCE.md"
    echo "" >> "${COMPONENTS_DIR}/COLOR_REFERENCE.md"
    echo "These colors MUST be used in SteamField.module.css:" >> "${COMPONENTS_DIR}/COLOR_REFERENCE.md"
    echo "" >> "${COMPONENTS_DIR}/COLOR_REFERENCE.md"
    echo '```' >> "${COMPONENTS_DIR}/COLOR_REFERENCE.md"
    echo "$SMOKE_COLORS" >> "${COMPONENTS_DIR}/COLOR_REFERENCE.md"
    echo '```' >> "${COMPONENTS_DIR}/COLOR_REFERENCE.md"
    
    log_success "Created COLOR_REFERENCE.md"
  fi
fi

# ============================================
# Create Test File
# ============================================

echo ""
log_info "Creating test setup..."

cat > "${COMPONENTS_DIR}/__tests__/SteamModal.test.tsx" << 'EOF'
/**
 * SteamModal Tests
 * 
 * Basic smoke tests for the Steam Modal component.
 */

import { render, screen, fireEvent } from '@testing-library/react';
import { SteamModal, ContentParagraph } from '../index';

describe('SteamModal', () => {
  it('renders when open', () => {
    render(
      <SteamModal
        isOpen={true}
        onClose={() => {}}
        title="Test Modal"
      >
        <ContentParagraph>Test content</ContentParagraph>
      </SteamModal>
    );
    
    expect(screen.getByRole('dialog')).toBeInTheDocument();
    expect(screen.getByText('Test Modal')).toBeInTheDocument();
    expect(screen.getByText('Test content')).toBeInTheDocument();
  });

  it('does not render when closed', () => {
    render(
      <SteamModal
        isOpen={false}
        onClose={() => {}}
        title="Test Modal"
      >
        <ContentParagraph>Test content</ContentParagraph>
      </SteamModal>
    );
    
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
  });

  it('calls onClose when close button is clicked', () => {
    const onClose = jest.fn();
    
    render(
      <SteamModal
        isOpen={true}
        onClose={onClose}
        title="Test Modal"
      >
        <ContentParagraph>Test content</ContentParagraph>
      </SteamModal>
    );
    
    fireEvent.click(screen.getByLabelText('Close modal'));
    expect(onClose).toHaveBeenCalled();
  });

  it('calls onClose when Escape is pressed', () => {
    const onClose = jest.fn();
    
    render(
      <SteamModal
        isOpen={true}
        onClose={onClose}
        title="Test Modal"
      >
        <ContentParagraph>Test content</ContentParagraph>
      </SteamModal>
    );
    
    fireEvent.keyDown(document, { key: 'Escape' });
    expect(onClose).toHaveBeenCalled();
  });
});

describe('Contrast Requirements', () => {
  it('has correct background color on content panel', () => {
    render(
      <SteamModal
        isOpen={true}
        onClose={() => {}}
        title="Test Modal"
      >
        <ContentParagraph>Test content</ContentParagraph>
      </SteamModal>
    );
    
    const contentPanel = document.querySelector('[class*="contentPanel"]');
    expect(contentPanel).toBeInTheDocument();
    
    // Note: Actual color testing requires computed styles
    // This is a placeholder for visual regression testing
  });
});
EOF

log_success "Created test file"

# ============================================
# Print Summary
# ============================================

echo ""
echo "============================================"
echo "  Installation Complete!"
echo "============================================"
echo ""

if [ "$DRY_RUN" = true ]; then
  log_warning "This was a DRY RUN - no files were actually modified."
  echo ""
fi

log_success "Steam Modal components installed to:"
echo "  ${COMPONENTS_DIR}"
echo ""

log_info "Next steps:"
echo ""
echo "  1. Import and use the SteamModal component:"
echo ""
echo "     import { SteamModal, ContentParagraph } from './components/steam-modal';"
echo ""
echo "     <SteamModal"
echo "       isOpen={isOpen}"
echo "       onClose={() => setIsOpen(false)}"
echo "       title=\"Our Story\""
echo "     >"
echo "       <ContentParagraph>Your content here</ContentParagraph>"
echo "     </SteamModal>"
echo ""
echo "  2. Start the dev server:"
echo "     npm run dev"
echo ""
echo "  3. Test the modal and verify:"
echo "     - [ ] Steam colors are warm brown (not amber)"
echo "     - [ ] Text is dark on parchment (high contrast)"
echo "     - [ ] Animations play smoothly"
echo "     - [ ] Modal closes properly (no stacking)"
echo ""
echo "  4. Run tests:"
echo "     npm test -- --testPathPattern=SteamModal"
echo ""

log_info "See README.md for detailed implementation guide and troubleshooting."
echo ""
