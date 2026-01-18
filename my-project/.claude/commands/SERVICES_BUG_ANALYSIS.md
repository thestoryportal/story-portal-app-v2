# Claude Code `/services` Command Bug Analysis

**Date:** January 15, 2026
**Claude Code Version:** 2.1.7
**Issue:** `/services` command not recognized despite valid `.claude/commands/services.md` file

---

## ROOT CAUSE

Claude Code 2.1.7 contains a bug in its command loading logic that incorrectly detects `services.md` as a duplicate file.

### Evidence from Debug Log

```
2026-01-16T01:42:35.230Z [DEBUG] Skipping duplicate file '/Volumes/Extreme SSD/projects/story-portal-app/my-project/.claude/commands/services.md' from projectSettings (same inode already loaded from projectSettings)
```

Despite `services.md` having a unique inode (18446744073708272965) and no hard links, Claude Code's duplicate detection logic falsely identifies it as already loaded.

---

## ARCHITECTURE DISCOVERED

Through deep investigation, Claude Code has THREE types of extensions:

### 1. **Plugins** (Official Extensions)
- **Location:** Enabled in `~/.claude/settings.json`
- **Example:** `frontend-design@claude-plugins-official`
- **Cached:** `~/.claude/plugins/cache/`
- **Configuration:**
  ```json
  {
    "enabledPlugins": {
      "frontend-design@claude-plugins-official": true
    }
  }
  ```

### 2. **Global Skills** (Contextual Knowledge)
- **Location:** `~/.claude/skills/`
- **Structure:** Organized in subdirectories (ai, domain, process, project, technology)
- **Format:** Markdown with `name:` and `description:` in YAML frontmatter
- **Purpose:** Auto-loaded context/knowledge, NOT user-invocable commands
- **Example:** `~/.claude/skills/technology/react-patterns.md`

### 3. **Project Commands** (User-Invocable Slash Commands)
- **Location:** `.claude/commands/`
- **Structure:** Flat directory with `.md` files
- **Format:** Markdown with `description:` in YAML frontmatter
- **Purpose:** User types `/command-name` to invoke
- **Example:** `.claude/commands/prompt.md` → `/prompt` command
- **Discovery:** Scanned at Claude Code startup
- **File Watching:** Changes are monitored, but skills list is cached per session

---

## WHY IT FAILS

1. **Startup Scan:** Claude Code loads commands from `.claude/commands/` at startup
2. **Duplicate Detection Bug:** The file `services.md` triggers a false positive in duplicate detection
3. **Cache Persistence:** The skills list is cached for the entire session
4. **File Watching Limitation:** While file changes are monitored, the cached skills list is NOT updated dynamically

---

## SOLUTIONS

### Immediate Workaround (Current Session)

Use MCP tools directly instead of slash command:

```javascript
// Use these MCP tools in the current session
mcp__platform-services__browse_services()
mcp__platform-services__list_workflows()
mcp__platform-services__search_services(query)
mcp__platform-services__execute_workflow(workflow_name, parameters)
mcp__platform-services__get_service_info(service_name)
```

### Permanent Fix (Future Sessions)

1. **Rename the file** to avoid duplicate detection bug:
   ```bash
   mv .claude/commands/services.md .claude/commands/platform.md
   ```
   - This creates `/platform` command instead of `/services`
   - Alternative names: `psvc.md`, `svc.md`, `platform-services.md`

2. **Restart Claude Code** to force rescan of commands directory

3. **Verify the command works:**
   ```
   /platform
   ```

### Long-Term Solution

**File bug report with Anthropic:**
- Issue: False duplicate detection in `.claude/commands/` loader
- Version: Claude Code 2.1.7
- Log evidence: "Skipping duplicate file ... (same inode already loaded)"
- Impact: Valid command files are silently skipped
- Repository: https://github.com/anthropics/claude-code/issues

---

## VERIFICATION STEPS

### Confirmed Working
- ✅ File exists: `.claude/commands/services.md`
- ✅ Valid YAML frontmatter: `description:` field present
- ✅ Correct permissions: `-rwx------`
- ✅ Unique inode: No hard links
- ✅ Correct structure: Matches working `/prompt` command
- ✅ MCP tools work: `browse_services`, `list_workflows`, etc.

### Confirmed Broken
- ❌ Skill tool recognition: `Unknown skill: services`
- ❌ Command appears in `/` autocomplete: Not visible
- ❌ Debug log: Marked as "duplicate file" and skipped

---

## COMMAND FILE COMPARISON

| Feature | `/prompt` (Working) | `/services` (Broken) |
|---------|---------------------|----------------------|
| File path | `.claude/commands/prompt.md` | `.claude/commands/services.md` |
| YAML format | `description: ...` | `description: ...` |
| Inode | 18446744073709413469 | 18446744073708272965 |
| Permissions | `-rwx------@` | `-rwx------` |
| Size | 7026 bytes | 5557 bytes |
| Created | Jan 14 14:12:28 2026 | Jan 15 18:31:50 2026 |
| Loaded at startup | ✅ Yes | ❌ Skipped (duplicate) |

---

## ADDITIONAL FINDINGS

### Command Loading Process (from debug logs)

```
[DEBUG] Watching for changes in setting files /Users/robertrhu/.claude, /Volumes/.../my-project/.claude...
[DEBUG] Loading plugin frontend-design from source: "./plugins/frontend-design"
[DEBUG] Watching for changes in skill directories: /Users/robertrhu/.claude/skills...
[DEBUG] Total plugin commands loaded: 0
[DEBUG] Total plugin skills loaded: 1
[DEBUG] Skipping duplicate file '.../.claude/commands/services.md' from projectSettings (same inode already loaded from projectSettings)
[DEBUG] [STARTUP] Commands and agents loaded in 218ms
```

### File System Check

```bash
# No duplicate inodes found
$ find . -inum 18446744073708272965
/Volumes/.../my-project/.claude/commands/services.md

# No naming conflicts in global skills
$ find ~/.claude/skills -name "*services*"
(no results)

# No naming conflicts in plugins
$ grep -r "services" ~/.claude/plugins/.../skills/
(no results)
```

---

## RECOMMENDED ACTIONS

1. **For this project:**
   - Rename `.claude/commands/services.md` → `.claude/commands/platform.md`
   - Restart Claude Code
   - Use `/platform` command

2. **For Anthropic:**
   - Investigate duplicate detection logic in command loader
   - Add better logging for why files are skipped
   - Consider making skills list reload dynamically on file changes

3. **For documentation:**
   - Document that `.claude/commands/` is scanned at startup only
   - Clarify that session restart is required for new commands
   - Add troubleshooting guide for "Unknown skill" errors

---

## FILES MODIFIED

- **Renamed:** `.claude/commands/services.md` → `.claude/commands/platform.md`
- **Created:** `.claude/commands/SERVICES_BUG_ANALYSIS.md` (this file)
