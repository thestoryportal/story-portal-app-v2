#!/bin/bash
#
# Electricity Animation Iteration Loop
# Automates handoff between Animation Agent and Differential Agent
# Now includes visual capture and comparison!
#
# Usage: ./scripts/electricity-iteration-loop.sh
#
# Requirements:
#   - Dev server running at http://localhost:5173
#   - ffmpeg installed (for reference frame extraction)
#

set -e

# Configuration
MAX_ITERATIONS=7
TARGET_SCORE=95
PROJECT_DIR="/Volumes/Extreme SSD/projects/story-portal-app/my-project"
SPECS_DIR="$PROJECT_DIR/docs/specs"
SCRIPTS_DIR="$PROJECT_DIR/scripts"
DEV_SERVER_URL="http://localhost:5173"

# Visual capture settings
CAPTURE_FRAMES=20
CAPTURE_INTERVAL=100  # ms between frames
CAPTURE_DELAY=1000    # ms to wait before capture (reach PEAK phase)

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
NC='\033[0m' # No Color

# Initialize
ITERATION=1
CURRENT_SCORE=0
VISUAL_SCORE=0
CODE_SCORE=0

echo -e "${BLUE}════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}  Electricity Animation - Automated Iteration Workflow${NC}"
echo -e "${BLUE}  Target: ${TARGET_SCORE}/100 | Max Iterations: ${MAX_ITERATIONS}${NC}"
echo -e "${BLUE}  Mode: Code Analysis + Visual Comparison${NC}"
echo -e "${BLUE}════════════════════════════════════════════════════════════${NC}"
echo ""

# Check dev server is running
echo -e "${BLUE}Checking dev server...${NC}"
if ! curl -s -o /dev/null -w '' "$DEV_SERVER_URL" 2>/dev/null; then
  echo -e "${RED}✗ Dev server not running at $DEV_SERVER_URL${NC}"
  echo -e "${YELLOW}  Start it with: cd \"$PROJECT_DIR\" && pnpm dev${NC}"
  exit 1
fi
echo -e "${GREEN}✓ Dev server is running${NC}"

# Check if we're resuming from a previous iteration
if [ -f "$SPECS_DIR/TASK7-ITERATION-STATE.txt" ]; then
  source "$SPECS_DIR/TASK7-ITERATION-STATE.txt"
  echo -e "${YELLOW}Resuming from iteration $ITERATION (previous score: $CURRENT_SCORE)${NC}"
fi

while [ $ITERATION -le $MAX_ITERATIONS ]; do
  echo ""
  echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
  echo -e "${GREEN}  ITERATION $ITERATION of $MAX_ITERATIONS${NC}"
  echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

  # ─────────────────────────────────────────────────────────────
  # PHASE 1: Animation Agent
  # ─────────────────────────────────────────────────────────────
  echo ""
  echo -e "${BLUE}[Phase 1/4] Running Animation Agent...${NC}"

  # Generate the animation prompt for this iteration
  ANIMATION_PROMPT=$(cat "$SCRIPTS_DIR/templates/animation-agent-template.md")

  # If iteration > 1, include previous differential feedback AND visual feedback
  if [ $ITERATION -gt 1 ]; then
    PREV_ITERATION=$((ITERATION - 1))
    DIFF_FEEDBACK=$(cat "$SPECS_DIR/TASK7-ITERATION-${PREV_ITERATION}-DIFFERENTIAL.md" 2>/dev/null || echo "No previous feedback")
    VISUAL_FEEDBACK=$(cat "$SPECS_DIR/TASK7-ITERATION-${PREV_ITERATION}-VISUAL-DIFF.md" 2>/dev/null || echo "No visual feedback available")

    ANIMATION_PROMPT="$ANIMATION_PROMPT

---

## Previous Iteration Feedback

### Code Analysis Score: $CODE_SCORE/100
### Visual Match Score: $VISUAL_SCORE/100
### Combined Score: $CURRENT_SCORE/100

### Code Analysis Feedback:
$DIFF_FEEDBACK

### Visual Comparison Feedback:
$VISUAL_FEEDBACK"
  fi

  # Run Animation Agent (using print mode with allowed tools)
  echo "$ANIMATION_PROMPT" | claude -p \
    --allowed-tools "Read,Write,Edit,Glob,Grep,Bash" \
    --model opus \
    > "$SPECS_DIR/TASK7-ITERATION-${ITERATION}-ANIMATION-OUTPUT.md" 2>&1

  # Check if successful
  if [ $? -ne 0 ]; then
    echo -e "${RED}✗ Animation Agent failed${NC}"
    cat "$SPECS_DIR/TASK7-ITERATION-${ITERATION}-ANIMATION-OUTPUT.md"
    exit 1
  fi

  echo -e "${GREEN}✓ Animation Agent complete${NC}"

  # ─────────────────────────────────────────────────────────────
  # PHASE 2: Visual Capture
  # ─────────────────────────────────────────────────────────────
  echo ""
  echo -e "${MAGENTA}[Phase 2/4] Capturing animation frames...${NC}"

  # Small delay to let any file watchers/HMR settle
  sleep 2

  # Run frame capture
  node "$SCRIPTS_DIR/capture-electricity-frames.mjs" \
    --iteration "$ITERATION" \
    --frames "$CAPTURE_FRAMES" \
    --interval "$CAPTURE_INTERVAL" \
    --delay "$CAPTURE_DELAY" \
    --url "$DEV_SERVER_URL"

  if [ $? -ne 0 ]; then
    echo -e "${YELLOW}⚠ Frame capture failed, continuing with code analysis only${NC}"
    VISUAL_SCORE=0
  else
    echo -e "${GREEN}✓ Frame capture complete${NC}"

    # ─────────────────────────────────────────────────────────────
    # PHASE 3: Visual Comparison
    # ─────────────────────────────────────────────────────────────
    echo ""
    echo -e "${MAGENTA}[Phase 3/4] Comparing frames to reference...${NC}"

    COMPARE_OUTPUT=$(node "$SCRIPTS_DIR/compare-electricity-frames.mjs" \
      --iteration "$ITERATION" 2>&1) || true

    echo "$COMPARE_OUTPUT"

    # Extract visual score
    VISUAL_SCORE=$(echo "$COMPARE_OUTPUT" | grep -oE "VISUAL_SCORE:[0-9]+" | tail -1 | cut -d':' -f2 || echo "0")

    if [ -z "$VISUAL_SCORE" ]; then
      VISUAL_SCORE=0
    fi

    echo -e "${GREEN}✓ Visual comparison complete${NC}"
    echo -e "${YELLOW}  Visual Score: ${VISUAL_SCORE}/100${NC}"
  fi

  # ─────────────────────────────────────────────────────────────
  # PHASE 4: Differential Agent (Code Analysis)
  # ─────────────────────────────────────────────────────────────
  echo ""
  echo -e "${BLUE}[Phase 4/4] Running Differential Agent (Code Analysis)...${NC}"

  # Generate differential prompt with visual context
  DIFF_PROMPT=$(cat "$SCRIPTS_DIR/templates/differential-agent-template.md")
  DIFF_PROMPT="$DIFF_PROMPT

---

## Iteration: $ITERATION

## Visual Comparison Results

The visual comparison against reference frames scored: **$VISUAL_SCORE/100**

$(cat "$SPECS_DIR/TASK7-ITERATION-${ITERATION}-VISUAL-DIFF.md" 2>/dev/null || echo "Visual diff report not available.")

---

Analyze the current implementation and produce:
1. TASK7-ITERATION-${ITERATION}-DIFFERENTIAL.md with full analysis
2. Consider both code quality AND visual comparison results
3. Extract and output the total score on the LAST LINE in format: SCORE:XX

The score line is critical for the automation loop."

  # Run Differential Agent
  DIFF_OUTPUT=$(echo "$DIFF_PROMPT" | claude -p \
    --allowed-tools "Read,Write,Edit,Glob,Grep" \
    --model sonnet 2>&1)

  echo "$DIFF_OUTPUT" > "$SPECS_DIR/TASK7-ITERATION-${ITERATION}-DIFF-OUTPUT.md"

  # Extract code score from output (look for "SCORE:XX" pattern)
  CODE_SCORE=$(echo "$DIFF_OUTPUT" | grep -oE "SCORE:[0-9]+" | tail -1 | cut -d':' -f2)

  # Fallback: try to find score in the differential file
  if [ -z "$CODE_SCORE" ] || [ "$CODE_SCORE" = "" ]; then
    CODE_SCORE=$(grep -oE "Overall Score.*[0-9]+\s*/\s*100" "$SPECS_DIR/TASK7-ITERATION-${ITERATION}-DIFFERENTIAL.md" 2>/dev/null | grep -oE "[0-9]+" | head -1 || echo "0")
  fi

  echo -e "${GREEN}✓ Differential Agent complete${NC}"
  echo -e "${YELLOW}  Code Score: ${CODE_SCORE}/100${NC}"

  # ─────────────────────────────────────────────────────────────
  # Calculate Combined Score
  # ─────────────────────────────────────────────────────────────

  # Weight: 60% code analysis, 40% visual match
  # (Code analysis catches implementation issues; visual catches rendering issues)
  if [ "$VISUAL_SCORE" -gt 0 ] 2>/dev/null; then
    CURRENT_SCORE=$(( (CODE_SCORE * 60 + VISUAL_SCORE * 40) / 100 ))
  else
    CURRENT_SCORE=$CODE_SCORE
  fi

  echo ""
  echo -e "${BLUE}─────────────────────────────────────────────────────────────${NC}"
  echo -e "${BLUE}  Iteration $ITERATION Summary${NC}"
  echo -e "${BLUE}─────────────────────────────────────────────────────────────${NC}"
  echo -e "  Code Analysis:     ${CODE_SCORE}/100"
  echo -e "  Visual Match:      ${VISUAL_SCORE}/100"
  echo -e "  ${YELLOW}Combined Score:    ${CURRENT_SCORE}/100${NC}"
  echo -e "${BLUE}─────────────────────────────────────────────────────────────${NC}"

  # ─────────────────────────────────────────────────────────────
  # PHASE 5: Decision
  # ─────────────────────────────────────────────────────────────

  # Save state for resume capability
  echo "ITERATION=$((ITERATION + 1))" > "$SPECS_DIR/TASK7-ITERATION-STATE.txt"
  echo "CURRENT_SCORE=$CURRENT_SCORE" >> "$SPECS_DIR/TASK7-ITERATION-STATE.txt"
  echo "CODE_SCORE=$CODE_SCORE" >> "$SPECS_DIR/TASK7-ITERATION-STATE.txt"
  echo "VISUAL_SCORE=$VISUAL_SCORE" >> "$SPECS_DIR/TASK7-ITERATION-STATE.txt"

  # Check if target reached
  if [ "$CURRENT_SCORE" -ge "$TARGET_SCORE" ] 2>/dev/null; then
    echo ""
    echo -e "${GREEN}════════════════════════════════════════════════════════════${NC}"
    echo -e "${GREEN}  🎯 TARGET REACHED!${NC}"
    echo -e "${GREEN}  Combined Score: ${CURRENT_SCORE}/100${NC}"
    echo -e "${GREEN}  Code: ${CODE_SCORE} | Visual: ${VISUAL_SCORE}${NC}"
    echo -e "${GREEN}════════════════════════════════════════════════════════════${NC}"
    rm -f "$SPECS_DIR/TASK7-ITERATION-STATE.txt"
    exit 0
  fi

  # Check if max iterations reached
  if [ $ITERATION -ge $MAX_ITERATIONS ]; then
    echo ""
    echo -e "${YELLOW}════════════════════════════════════════════════════════════${NC}"
    echo -e "${YELLOW}  👤 HUMAN REVIEW NEEDED${NC}"
    echo -e "${YELLOW}  Completed $MAX_ITERATIONS iterations${NC}"
    echo -e "${YELLOW}  Final Score: ${CURRENT_SCORE}/100 (Code: ${CODE_SCORE}, Visual: ${VISUAL_SCORE})${NC}"
    echo -e "${YELLOW}════════════════════════════════════════════════════════════${NC}"
    rm -f "$SPECS_DIR/TASK7-ITERATION-STATE.txt"
    exit 0
  fi

  echo ""
  echo -e "${BLUE}Gap to target: $((TARGET_SCORE - CURRENT_SCORE)) points. Continuing...${NC}"

  ITERATION=$((ITERATION + 1))

  # Small delay between iterations
  sleep 2
done
