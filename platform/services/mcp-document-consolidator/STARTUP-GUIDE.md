# MCP Document Consolidator - Startup Guide

## Overview
The MCP Document Consolidator is a Model Context Protocol (MCP) server that provides document consolidation, overlap detection, and source-of-truth management capabilities.

## Configuration

### MCP Configuration
The server is configured in `~/.claude/mcp.json`:

```json
{
  "mcpServers": {
    "document-consolidator": {
      "command": "/bin/bash",
      "args": ["/Volumes/Extreme SSD/projects/story-portal-app/platform/services/mcp-document-consolidator/start-mcp.sh"]
    }
  }
}
```

### Environment Configuration
All environment variables are managed in `.env` file in this directory. The startup script (`start-mcp.sh`) automatically loads these variables.

Key configurations:
- **Database**: PostgreSQL connection (agentic_platform)
- **Ollama**: LLM service for document processing
- **Embedding**: Python-based embedding service
- **Neo4j**: Graph database (currently disabled)
- **Redis**: Caching layer

## Prerequisites

1. **Node.js**: Version 20.0.0 or higher
2. **PostgreSQL**: Running on localhost:5432 with database `agentic_platform`
3. **Ollama** (optional): Running on localhost:11434 for LLM features
4. **Python** (optional): For embedding service with venv at `./python/venv`

## Building the Server

```bash
cd /Volumes/Extreme SSD/projects/story-portal-app/platform/services/mcp-document-consolidator
npm install
npm run build
```

## Manual Testing

To test the server manually:

```bash
# Test with timeout (will exit after 3 seconds)
timeout 3 ./start-mcp.sh

# Check if it starts without errors - you should see:
# - Starting MCP Document Consolidator...
# - Node version
# - Database connection info
# - Service status (Ollama, Embedding)
```

## Troubleshooting

### Server Won't Start

1. **Check if built**: Ensure `dist/` directory exists with compiled JavaScript
   ```bash
   ls -la dist/
   ```

2. **Check dependencies**: Ensure node_modules is installed
   ```bash
   npm install
   ```

3. **Check environment**: Verify .env file exists and has correct values
   ```bash
   cat .env
   ```

4. **Check database**: Ensure PostgreSQL is running
   ```bash
   psql -h localhost -U postgres -d agentic_platform -c "SELECT 1;"
   ```

### MCP Connection Failures

1. **Restart Claude Code**: The MCP servers are loaded at startup
2. **Check MCP logs**: Look for error messages in Claude Code
3. **Verify paths**: Ensure all paths in mcp.json are absolute and correct
4. **Test startup script**: Run `./start-mcp.sh` manually to see any errors

### Environment Variable Issues

If you see "not a valid identifier" errors:
- Ensure all paths with spaces are quoted in .env file
- Example: `PYTHON_PATH="/path/with spaces/python3"`

## Available Tools

Once connected, the MCP server provides these tools:

1. **ingest_document**: Add documents with claim extraction
2. **find_overlaps**: Identify redundant/conflicting content
3. **consolidate_documents**: Merge multiple documents
4. **get_source_of_truth**: Query for authoritative answers
5. **deprecate_document**: Mark documents as deprecated

## Stability Features

1. **Automatic environment loading**: Reads from .env file
2. **Default fallbacks**: Uses sensible defaults if env vars missing
3. **Error checking**: Validates Node.js and build artifacts exist
4. **Graceful shutdown**: Handles SIGINT and SIGTERM signals
5. **Logging**: Startup diagnostics to stderr (MCP uses stdout)

## Maintenance

### Updating the Server

```bash
# Pull latest changes
git pull

# Reinstall dependencies
npm install

# Rebuild
npm run build

# Restart Claude Code to reload MCP server
```

### Checking Logs

The server logs to stderr. When run via Claude Code's MCP framework, logs can be viewed in:
- Claude Code debug logs
- System console (if running manually)

### Configuration Changes

After changing `.env`:
1. Restart Claude Code
2. The startup script will reload environment variables

After changing `start-mcp.sh`:
1. Ensure it's still executable: `chmod +x start-mcp.sh`
2. Test manually first: `timeout 3 ./start-mcp.sh`
3. Restart Claude Code

## Production Considerations

For production deployment:

1. **Secure credentials**: Never commit .env with real passwords
2. **Database connection pooling**: Configure POSTGRES_MAX_CONNECTIONS
3. **Enable SSL**: Set POSTGRES_SSL=true for remote databases
4. **Monitoring**: Use LOG_FORMAT=json for structured logging
5. **Resource limits**: Configure MAX_CONCURRENT_DOCUMENTS appropriately
6. **Backup strategy**: Regular backups of PostgreSQL database
7. **High availability**: Consider Redis and Postgres clustering

## Support

For issues:
1. Check this guide first
2. Review server logs for error messages
3. Test components individually (database, Ollama, embeddings)
4. Consult the main platform documentation
