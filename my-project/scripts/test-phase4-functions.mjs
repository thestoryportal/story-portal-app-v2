#!/usr/bin/env node
/**
 * Phase 4 RL Functions Unit Test
 *
 * Tests RL initialization, insights retrieval, and experience recording
 * without running the full orchestrator.
 */

import fs from 'fs/promises'
import path from 'path'
import { fileURLToPath } from 'url'

const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)

// Import RL module
import { RLFeedbackLoop } from './rl-feedback-loop.mjs'

const TEST_DB_PATH = './test-rl-feedback.json'

async function runTests() {
  console.log('╔════════════════════════════════════════════════════════════════╗')
  console.log('║  PHASE 4 RL FUNCTIONS UNIT TEST                                ║')
  console.log('╚════════════════════════════════════════════════════════════════╝\n')

  let allPassed = true

  try {
    // Clean up any existing test database
    try {
      await fs.unlink(TEST_DB_PATH)
      console.log('✓ Cleaned up old test database\n')
    } catch {}

    // Test 1: Initialization
    console.log('[Test 1] RL System Initialization')
    console.log('────────────────────────────────────────────────────────────────')
    const rl = new RLFeedbackLoop(TEST_DB_PATH)
    await rl.load()
    console.log(`✓ RL system initialized`)
    console.log(`✓ Experiences: ${rl.data.experiences.length}`)
    console.log(`✓ Learnings: ${rl.data.learnings.length}`)
    console.log(`✓ Expected: 0 experiences, 0 learnings (first run)\n`)

    if (rl.data.experiences.length !== 0 || rl.data.learnings.length !== 0) {
      console.error('✗ FAILED: Expected empty database on first run')
      allPassed = false
    }

    // Test 2: Record First Experience
    console.log('[Test 2] Record First Experience')
    console.log('────────────────────────────────────────────────────────────────')
    await rl.recordExperience({
      iteration: 1,
      state: { iteration: 1 },
      action: { description: 'Initial implementation', iteration: 1 },
      scoreBefore: 0,
      scoreAfter: 72.5,
      targetReached: false,
      criticalIssueFixed: false
    })
    console.log(`✓ Experience recorded`)
    console.log(`✓ Total experiences: ${rl.data.experiences.length}`)
    console.log(`✓ Last reward: ${rl.data.experiences[0].reward}`)
    console.log(`✓ Expected reward: +72.5 (score delta)\n`)

    if (rl.data.experiences.length !== 1) {
      console.error('✗ FAILED: Expected 1 experience')
      allPassed = false
    }

    // Test 3: Record Multiple Experiences
    console.log('[Test 3] Record Multiple Experiences')
    console.log('────────────────────────────────────────────────────────────────')
    await rl.recordExperience({
      iteration: 2,
      state: { iteration: 2 },
      action: { description: 'Increased boltCount by 2', iteration: 2 },
      scoreBefore: 72.5,
      scoreAfter: 80.3,
      targetReached: false,
      criticalIssueFixed: false
    })
    await rl.recordExperience({
      iteration: 3,
      state: { iteration: 3 },
      action: { description: 'Adjusted glow opacity', iteration: 3 },
      scoreBefore: 80.3,
      scoreAfter: 85.1,
      targetReached: false,
      criticalIssueFixed: false
    })
    console.log(`✓ 2 more experiences recorded`)
    console.log(`✓ Total experiences: ${rl.data.experiences.length}`)
    console.log(`✓ Expected: 3 experiences\n`)

    if (rl.data.experiences.length !== 3) {
      console.error(`✗ FAILED: Expected 3 experiences, got ${rl.data.experiences.length}`)
      allPassed = false
    }

    // Test 4: Record Experience with Target Reached
    console.log('[Test 4] Record Experience with Target Reached (Bonus)')
    console.log('────────────────────────────────────────────────────────────────')
    await rl.recordExperience({
      iteration: 4,
      state: { iteration: 4 },
      action: { description: 'Final refinements', iteration: 4 },
      scoreBefore: 85.1,
      scoreAfter: 95.5,
      targetReached: true,  // Bonus!
      criticalIssueFixed: false
    })
    const lastExperience = rl.data.experiences[rl.data.experiences.length - 1]
    console.log(`✓ Experience with bonus recorded`)
    console.log(`✓ Score delta: ${lastExperience.scoreAfter - lastExperience.scoreBefore}`)
    console.log(`✓ Reward: ${lastExperience.reward}`)
    console.log(`✓ Expected: ~60.4 (delta +10.4 + target bonus +50)\n`)

    if (Math.abs(lastExperience.reward - 60.4) > 0.5) {
      console.error(`✗ FAILED: Expected reward ~60.4, got ${lastExperience.reward}`)
      allPassed = false
    }

    // Test 5: Get Insights (Formatted for Prompts)
    console.log('[Test 5] Get RL Insights')
    console.log('────────────────────────────────────────────────────────────────')
    const insights = rl.formatLessonsForPrompt({ iteration: 5 })
    console.log(`✓ Insights retrieved`)
    console.log(`✓ Insights length: ${insights.length} characters`)
    console.log(`✓ Contains experience count: ${insights.includes('Based on')}`)
    console.log(`✓ Total learnings: ${rl.data.learnings.length}\n`)

    if (!insights || insights.length === 0) {
      console.error('✗ FAILED: Expected non-empty insights')
      allPassed = false
    }

    // Test 6: Statistics
    console.log('[Test 6] Verify Statistics')
    console.log('────────────────────────────────────────────────────────────────')
    console.log(`✓ Total Experiences: ${rl.data.statistics.totalExperiences}`)
    console.log(`✓ Average Reward: ${rl.data.statistics.avgReward.toFixed(2)}`)
    console.log(`✓ Best Action: ${rl.data.statistics.bestAction?.description || 'N/A'}`)
    console.log(`✓ Worst Action: ${rl.data.statistics.worstAction?.description || 'N/A'}\n`)

    if (rl.data.statistics.totalExperiences !== 4) {
      console.error(`✗ FAILED: Expected 4 total experiences, got ${rl.data.statistics.totalExperiences}`)
      allPassed = false
    }

    // Test 7: Database Persistence
    console.log('[Test 7] Database Persistence')
    console.log('────────────────────────────────────────────────────────────────')
    const rl2 = new RLFeedbackLoop(TEST_DB_PATH)
    await rl2.load()
    console.log(`✓ Loaded from disk`)
    console.log(`✓ Experiences: ${rl2.data.experiences.length}`)
    console.log(`✓ Learnings: ${rl2.data.learnings.length}`)
    console.log(`✓ Expected: 4 experiences (persisted)\n`)

    if (rl2.data.experiences.length !== 4) {
      console.error(`✗ FAILED: Expected 4 persisted experiences, got ${rl2.data.experiences.length}`)
      allPassed = false
    }

    // Test 8: Insights Content
    console.log('[Test 8] Insights Content Validation')
    console.log('────────────────────────────────────────────────────────────────')
    console.log('Sample insights:\n')
    console.log(insights.substring(0, 500) + '...\n')

    // Clean up test database
    await fs.unlink(TEST_DB_PATH)
    console.log('✓ Cleaned up test database\n')

    // Final Results
    console.log('╔════════════════════════════════════════════════════════════════╗')
    if (allPassed) {
      console.log('║  ✅ ALL TESTS PASSED                                           ║')
    } else {
      console.log('║  ❌ SOME TESTS FAILED                                          ║')
    }
    console.log('╚════════════════════════════════════════════════════════════════╝')

    process.exit(allPassed ? 0 : 1)

  } catch (err) {
    console.error('\n❌ TEST ERROR:', err.message)
    console.error(err.stack)

    // Clean up on error
    try {
      await fs.unlink(TEST_DB_PATH)
    } catch {}

    process.exit(1)
  }
}

runTests()
