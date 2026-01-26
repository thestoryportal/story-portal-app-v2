# Context Management Skill

Manual context loading, saving, and management for long-running tasks.

## Usage

```
/context                      # Show current context status
/context load <task-id>       # Load specific task context
/context save                 # Save current context snapshot
/context checkpoint <name>    # Create named checkpoint
/context rollback <target>    # Rollback to checkpoint or version
/context recover              # Check for and recover interrupted sessions
/context list                 # List all available tasks
/context switch <task-id>     # Switch to different task
/context conflicts            # Detect cross-system conflicts
/context sync                 # Sync built-in tasks with MCP context
```

## Instructions

When this skill is invoked, perform the appropriate action based on the arguments:

### No arguments or "status"
Show current context status by calling these tools IN PARALLEL:
1. `mcp__context-orchestrator__get_unified_context()` - Get global context
2. `mcp__context-orchestrator__get_task_graph()` - Get task overview
3. `mcp__context-orchestrator__check_recovery()` - Check for recovery needs
4. `mcp__context-orchestrator__detect_conflicts()` - Check for conflicts

Display a summary showing:
- Current project and active task
- Task list with statuses (from both MCP and built-in TaskList)
- Any blockers or recovery needs
- Any detected conflicts
- Last checkpoint info

### "load <task-id>"
Load full context for a specific task:
1. Call `mcp__context-orchestrator__get_unified_context({ taskId: "<task-id>", includeVersionHistory: true })`
2. Display the task's:
   - Name and description
   - Current phase and status
   - Immediate context (working on, last action, next step, blockers)
   - Key files
   - Technical decisions
   - Resume prompt
   - Recent version history (if any)

### "save"
Save current context snapshot:
1. Ask user what they're currently working on (if not clear from conversation)
2. Call `mcp__context-orchestrator__save_context_snapshot()` with:
   - taskId (from active task or ask user)
   - updates with immediateContext (workingOn, lastAction, nextStep, blockers)
   - changeSummary describing what was accomplished
3. Confirm save was successful
4. Also update corresponding built-in task via TaskUpdate if one exists with same ID

### "checkpoint <name>"
Create a named checkpoint for rollback:
1. Call `mcp__context-orchestrator__create_checkpoint()` with:
   - taskId (current active task)
   - label (the provided name)
   - checkpointType: "manual"
   - description (brief summary of current state)
2. Confirm checkpoint was created with its ID
3. Remind user they can rollback with `/context rollback checkpoint:<id>`

### "rollback <target>"
Rollback to a previous state. Target can be:
- `checkpoint:<id>` - Rollback to a named checkpoint
- `version:<number>` - Rollback to a specific version number

Steps:
1. Parse the target to determine type (checkpoint or version)
2. Call `mcp__context-orchestrator__rollback_to()` with:
   - taskId (current active task)
   - target: { type: "checkpoint", checkpointId: "<id>" } OR { type: "version", version: <number> }
   - createBackup: true (always backup before rollback)
3. Display what was restored
4. Warn user that this replaced current state

### "recover"
Check for and recover interrupted sessions:
1. Call `mcp__context-orchestrator__check_recovery({ includeHistory: true })`
2. If recovery needed:
   - Show what was interrupted
   - Display recovery prompt
   - Offer to load the context
   - Mark as recovered after handling
3. If no recovery needed:
   - Confirm all sessions are clean

### "list"
List all available tasks from BOTH sources:
1. Call `mcp__context-orchestrator__get_task_graph()` for MCP tasks
2. Call `TaskList` for built-in tasks
3. Merge and display all tasks with:
   - Task ID
   - Name
   - Status (pending/in_progress/completed)
   - Source (MCP or Built-in)
   - Priority
   - Whether blocked

### "switch <task-id>"
Switch to a different task:
1. If currently working on a task, save its context first
2. Call `mcp__context-orchestrator__switch_task()` with:
   - fromTaskId (current task, if any)
   - toTaskId (the target task)
   - currentTaskUpdates (if switching from active work)
3. Display the new task's context
4. Update built-in task status if applicable

### "conflicts"
Detect and display cross-system conflicts:
1. Call `mcp__context-orchestrator__detect_conflicts()` with all conflict types
2. Display any conflicts found:
   - state_mismatch: Different state in different systems
   - file_conflict: Same file modified in multiple contexts
   - spec_contradiction: Conflicting specifications
   - version_divergence: Version history diverged
3. For each conflict, offer resolution options:
   - use_a: Use value from system A
   - use_b: Use value from system B
   - merge: Attempt to merge
   - ignore: Mark as ignored
4. If user selects a resolution, call `mcp__context-orchestrator__resolve_conflict()`

### "sync"
Sync built-in Task tools with MCP context:
1. Call `TaskList` to get built-in tasks
2. Call `mcp__context-orchestrator__get_task_graph()` for MCP tasks
3. For tasks that exist in both:
   - Compare status, update if different
   - Sync descriptions and metadata
4. For tasks only in built-in:
   - Offer to create in MCP context
5. For tasks only in MCP:
   - Offer to create in built-in tasks
6. Call `mcp__context-orchestrator__sync_hot_context()` to update file cache

## Best Practices

- Use `/context save` before taking breaks or ending sessions
- Use `/context checkpoint <name>` before risky operations (refactors, migrations)
- Use `/context recover` at the start of sessions to check for interrupted work
- Use `/context switch` when changing focus between tasks
- Use `/context conflicts` periodically to catch state mismatches
- Use `/context sync` to keep MCP and built-in tasks aligned
- Use `/context rollback` to undo mistakes (always creates backup first)

## Tool Integration

This skill integrates:
- **Context Orchestrator MCP**: Primary context storage (PostgreSQL, Redis, Neo4j)
- **Built-in Task Tools**: TaskCreate, TaskUpdate, TaskList, TaskGet
- **File Cache**: .claude/contexts/ for fast local access
- **Hooks**: Automatic context injection on session start and prompt submit

## Examples

```
User: /context
Claude: [Shows status from both MCP and built-in tasks, any conflicts]

User: /context load steam-modal-refinement
Claude: [Loads full context with version history]

User: /context save
Claude: What are you currently working on?
User: Implementing the close animation
Claude: [Saves to MCP and updates built-in task if exists]

User: /context checkpoint pre-refactor
Claude: [Creates checkpoint, shows ID for rollback]

User: /context rollback checkpoint:abc123
Claude: [Rolls back to checkpoint, shows what changed]

User: /context conflicts
Claude: [Shows any state mismatches, offers resolution]

User: /context sync
Claude: [Syncs MCP and built-in tasks, shows what changed]
```
