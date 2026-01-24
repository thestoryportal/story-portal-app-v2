# MCP Document Consolidator Debug Session - 2026-01-23

## Problem
MCP document consolidator server fails to connect at session start and Python embedding subprocess doesn't terminate cleanly on shutdown.

## Root Cause Analysis

### Issue 1: Slow Startup (Primary Issue)
The Python embedding service takes ~2-3 seconds to load the sentence-transformers model. This causes:
1. Claude Code may timeout waiting for the MCP server to respond
2. If stdin closes before the model is loaded, the server can't respond

**Solution Applied**: Disabled `EMBEDDING_ENABLED=false` in `.env` for fast startup. The simple fallback embedding is used instead.

### Issue 2: Python Process Shutdown Hang
When the Node.js server shuts down:
1. Closes stdin to the Python process
2. Waits for Python to exit
3. Python may be stuck in `readline()` if EOF arrives during model loading

**Root Cause**: The Python `readline()` is blocking. If EOF is delivered while the model is loading (before the first readline), it may not be detected.

### Issue 3: Ollama Model Configuration
The `.env` specified `llama3.2:3b` but only `llama3.2:latest` was installed.

**Solution Applied**: Pulled `llama3.2:3b` model with Ollama (`ollama pull llama3.2:3b`).

## Current State (After Fixes)

✅ **Working Configuration**:
- `EMBEDDING_ENABLED=false` - Uses simple fallback embeddings
- `OLLAMA_ENABLED=true` - LLM features available
- `NEO4J_ENABLED=false` - Entity resolution unavailable
- Server starts quickly (~1 second)
- MCP protocol works correctly
- Clean shutdown

## Ollama Models Available
```
llama3.2:3b (3.2B) ← Configured in .env
llama3.2:latest (3.2B)
llama3.2:1b (1.2B)
llama3.1:8b (8.0B)
mistral:7b (7.2B)
llava-llama3:latest (8B)
nomic-embed-text:latest (137M)
```

## Future Improvements

### Priority 1: Lazy-Load Embedding Model
Instead of loading at startup, load on first use:
```typescript
async embed(texts: string[]): Promise<number[][]> {
  if (!this.isInitialized) {
    await this.initialize();  // Load model here
  }
  // ... rest of implementation
}
```

### Priority 2: Fix Python EOF Handling
Add a select/poll before readline to detect EOF:
```python
import select

def run(self):
    while self.running:
        # Check if stdin has data or closed
        ready, _, _ = select.select([sys.stdin], [], [], 1.0)
        if not ready:
            continue
        line = sys.stdin.readline()
        if not line:  # EOF
            break
        # ... process request
```

### Priority 3: Add Startup Timeout in .mcp.json
Claude Code may support startup timeouts:
```json
{
  "mcpServers": {
    "document-consolidator": {
      "command": "/bin/bash",
      "args": ["..."],
      "startupTimeout": 30000
    }
  }
}
```

## Files Modified This Session
1. `.env` - Disabled embedding for fast startup
2. `DEBUG-SESSION-2026-01-23.md` - This file

## Test Commands

### Quick Test (Fast Startup)
```bash
echo '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"test","version":"1.0"}}}' | timeout 10 /bin/bash "/Volumes/Extreme SSD/projects/story-portal-app/platform/services/mcp-document-consolidator/start-mcp.sh" 2>&1
```

### Full Protocol Test
```bash
(
  echo '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"claude-code","version":"1.0"}}}'
  sleep 0.5
  echo '{"jsonrpc":"2.0","method":"notifications/initialized"}'
  echo '{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}'
  sleep 1
) | timeout 15 /bin/bash "/Volumes/Extreme SSD/projects/story-portal-app/platform/services/mcp-document-consolidator/start-mcp.sh" 2>&1
```

### Kill Orphan Processes
```bash
pkill -9 -f "embedding_service.py"
pkill -9 -f "dist/server.js"
```
