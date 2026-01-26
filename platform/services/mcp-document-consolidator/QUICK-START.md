# Document Consolidator MCP - Quick Start

## ✅ Setup Complete

The document-consolidator MCP server has been successfully configured and is ready to use.

## Quick Commands

### Verify Health
```bash
cd "/Volumes/Extreme SSD/projects/story-portal-app/platform/services/mcp-document-consolidator"
./health-check.sh
```

### Test Startup
```bash
timeout 3 ./start-mcp.sh
```

### Rebuild After Changes
```bash
npm run build
```

## Using the Server

### 1. Restart Claude Code
The MCP server loads at startup. Simply restart Claude Code.

### 2. Check Connection
Look for "document-consolidator" in the MCP servers list.

### 3. Use the Tools
Available tools in Claude Code:
- **ingest_document** - Add documents with claim extraction
- **find_overlaps** - Find redundant/conflicting content
- **consolidate_documents** - Merge multiple documents
- **get_source_of_truth** - Query for authoritative answers
- **deprecate_document** - Mark documents as deprecated

## Troubleshooting

### Connection Failed?
```bash
# 1. Run health check
./health-check.sh

# 2. Check PostgreSQL
docker ps | grep postgres

# 3. View startup logs
timeout 3 ./start-mcp.sh
```

### Build Issues?
```bash
# Clean and rebuild
rm -rf dist/
npm install
npm run build
```

## Configuration Files

- `~/.claude/mcp.json` - MCP registration
- `.env` - Environment variables
- `start-mcp.sh` - Startup script
- `health-check.sh` - System validation

## Documentation

- `STARTUP-GUIDE.md` - Comprehensive guide
- `README-MCP-SETUP.md` - Setup details
- `FIX-SUMMARY.md` - What was fixed

## Status: Production Ready ✅

All systems operational. Server is stable and well-documented.
