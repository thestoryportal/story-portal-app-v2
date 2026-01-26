---
description: Comprehensive automated debugging workflow - thorough, precise, systematic
---

# Debug Command

**Invoke with**: `/debug` or `/debug [issue description]`

A full-featured, systematic debugging workflow that deploys multiple diagnostic techniques to identify, isolate, and resolve issues.

## Debugging Philosophy

```
REPRODUCE → ISOLATE → ANALYZE → RESOLVE → VERIFY
```

Every debugging session follows this proven methodology with parallel diagnostic gathering and systematic root cause analysis.

---

## Phase 0: Initial Triage

When user invokes `/debug`, IMMEDIATELY use AskUserQuestion:

- header: "Debug Type"
- question: "What type of issue are you debugging?"
- options:
  1. label: "UI/Visual Bug", description: "Component rendering, styling, layout, animations"
  2. label: "Runtime Error", description: "JavaScript errors, crashes, exceptions"
  3. label: "API/Network Issue", description: "Backend calls, data fetching, responses"
  4. label: "Performance Problem", description: "Slow rendering, memory leaks, lag"
  5. label: "State/Data Bug", description: "Incorrect data, state management issues"
  6. label: "Build/Compile Error", description: "TypeScript, webpack, vite errors"

Then ask for specifics:
- header: "Details"
- question: "Describe the issue (or say 'unknown' to start diagnostic scan)"
- Allow free text response

---

## Phase 1: Symptom Collection (Parallel Execution)

Run these diagnostic tools IN PARALLEL using multiple tool calls in a single message:

### 1.1 Browser Diagnostics (if UI/Runtime/Performance)
```
- tabs_context_mcp → get available tabs
- If app not open: tabs_create_mcp → navigate to app URL
- computer action=screenshot → capture current visual state
- read_console_messages pattern="error|warn|exception" → collect JS errors
- read_network_requests urlPattern="/api" → check failed API calls
```

### 1.2 Code Diagnostics (always run)
```
- Task tool with subagent_type=Explore:
  "Search for error patterns, recent changes, and related code paths for: [issue description]"
```

### 1.3 Test Diagnostics (if applicable)
```
- Bash: npm test -- --reporter=verbose 2>&1 | head -100
- Or: npm run test:related [file] if specific file known
```

### 1.4 Log Diagnostics (if backend/API)
```
- Bash: Check dev server output, docker logs, or application logs
- Look for stack traces, error codes, timing issues
```

### 1.5 Git Diagnostics (for regression detection)
```
- Bash: git log --oneline -10 (recent commits)
- Bash: git diff HEAD~3 --stat (recent changes summary)
```

---

## Phase 2: Hypothesis Formation

Based on collected symptoms, form hypotheses ranked by likelihood:

1. **Pattern Match**: Match error messages to known issue patterns
2. **Stack Trace Analysis**: Trace errors back to source files
3. **Timeline Correlation**: Connect issue to recent code changes
4. **Dependency Check**: Identify external dependency issues

Present findings to user:
```
## Diagnostic Summary

**Symptoms Found:**
- [List each error, warning, or anomaly discovered]

**Likely Causes (ranked):**
1. [Most likely cause] - Evidence: [what points to this]
2. [Second possibility] - Evidence: [supporting data]
3. [Third possibility] - Evidence: [supporting data]

**Recommended Investigation Path:**
[Specific files/functions to examine]
```

---

## Phase 3: Isolation

Use AskUserQuestion to confirm investigation direction:
- header: "Investigate"
- question: "Which hypothesis should we investigate first?"
- options: [Generated from Phase 2 findings]

### Isolation Techniques by Issue Type:

**UI/Visual Issues:**
- Use browser javascript_tool to inspect component state
- Read component source files
- Check CSS/styling rules
- Invoke smoke-modal-ux-designer agent if modal/dialog related

**Runtime Errors:**
- Add targeted console.log statements
- Read error source file with context (-B 10 -A 10)
- Check for null/undefined handling

**API/Network Issues:**
- Inspect request/response payloads
- Check backend service logs
- Verify API endpoint implementations

**Performance Issues:**
- Browser Performance profiling via javascript_tool
- Check for unnecessary re-renders
- Analyze bundle size and lazy loading

**State/Data Issues:**
- Inspect Redux/Zustand/Context state via browser
- Trace data flow through components
- Check data transformation logic

**Build Errors:**
- Read full error output
- Check tsconfig.json, vite.config.ts, package.json
- Verify dependency versions

---

## Phase 4: Resolution

Once root cause is identified:

1. **Propose Fix**: Show the specific code change needed
2. **Explain Why**: Describe why this fixes the issue
3. **Consider Side Effects**: Note any potential impacts

Use AskUserQuestion:
- header: "Apply Fix"
- question: "Should I apply this fix?"
- options:
  1. label: "Yes, apply fix", description: "Make the code change"
  2. label: "Show me more context", description: "Read more related code first"
  3. label: "Let me review first", description: "I'll make the change manually"
  4. label: "Try different approach", description: "Investigate another hypothesis"

---

## Phase 5: Verification

After applying fix:

### 5.1 Automated Verification
```
- Run relevant tests: npm test -- --testPathPattern=[affected]
- Type check: npx tsc --noEmit
- Lint check: npm run lint [file]
```

### 5.2 Browser Verification (if UI-related)
```
- Refresh page / navigate to affected area
- Take screenshot
- Verify console is clean of related errors
- Check network requests succeed
```

### 5.3 Regression Check
```
- Run broader test suite if available
- Manual verification of related features
```

Present verification results:
```
## Verification Results

**Tests**: [PASS/FAIL with details]
**Type Check**: [PASS/FAIL]
**Browser Check**: [Clean/Issues found]
**Regression Risk**: [Low/Medium/High]

[Screenshot of fixed state if applicable]
```

---

## Specialized Agent Integration

Based on the debugging domain, spawn specialized agents using Task tool:

### Animation/Visual Effects Issues
```
Task tool with subagent_type=smoke-modal-ux-designer:
"Analyze the animation/visual issue: [description].
Review timing, easing, performance, and visual consistency."
```

### Complex Code Architecture Issues
```
Task tool with subagent_type=Explore:
"Thoroughly map the code architecture related to [issue].
Identify all dependencies, data flows, and potential failure points."
```

### Backend Integration Issues
```
Task tool with subagent_type=Explore:
"Investigate the backend integration for [feature].
Check API contracts, error handling, and data transformations."
```

### State Management Issues
```
Task tool with subagent_type=Explore:
"Trace the state management flow for [feature].
Map state updates, selectors, and component subscriptions."
```

---

## Quick Debug Shortcuts

For common issues, use these accelerated paths:

### `/debug console` - Console Error Focus
Skip to browser console analysis, read errors, trace to source.

### `/debug network` - Network Issue Focus
Skip to network request analysis, check API responses.

### `/debug test [file]` - Test Failure Focus
Run specific test file, analyze failures, trace to source.

### `/debug visual` - Visual Regression Focus
Take screenshot, compare to expected, analyze differences.

### `/debug perf` - Performance Focus
Run performance analysis via browser, identify bottlenecks.

---

## Error Handling

If debugging hits a dead end:

1. **Expand Search**: Look at broader code context
2. **Check Dependencies**: Verify package versions, compatibility
3. **Review Recent Changes**: git bisect to find regression
4. **Ask for Help**: Request more context from user

Use AskUserQuestion:
- header: "Need More Info"
- question: "I need additional information to proceed. What can you provide?"
- options:
  1. label: "Steps to reproduce", description: "Exact steps that trigger the issue"
  2. label: "When it started", description: "What changed before the issue appeared"
  3. label: "Expected behavior", description: "What should happen instead"
  4. label: "Environment details", description: "Browser, OS, Node version, etc."

---

## Session Persistence

At end of debugging session, offer to save context:

```
## Debug Session Summary

**Issue**: [Original description]
**Root Cause**: [What was found]
**Resolution**: [What was done]
**Files Changed**: [List]
**Verification**: [Status]

Would you like me to save this to .claude/contexts/ for future reference?
```

---

## Best Practices

1. **Always gather symptoms before forming hypotheses**
2. **Use parallel tool calls to speed up diagnostics**
3. **Verify fixes don't introduce new issues**
4. **Document complex debugging sessions for future reference**
5. **Spawn specialized agents for domain-specific issues**
6. **Keep the user informed at each phase**

---

## Tool Integration Reference

| Tool | Purpose |
|------|---------|
| `computer action=screenshot` | Capture visual state |
| `read_console_messages` | JavaScript errors/warnings |
| `read_network_requests` | API call analysis |
| `javascript_tool` | Runtime state inspection |
| `Read` | Source code examination |
| `Grep` | Pattern search across codebase |
| `Bash` | Run tests, check logs, git operations |
| `Task` | Spawn specialized agents |
| `Edit` | Apply fixes |

This workflow ensures thorough, systematic debugging that leaves no stone unturned while remaining efficient through parallel execution and targeted investigation.
