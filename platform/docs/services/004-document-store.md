# Service 4/44: DocumentStore

## Overview

| Property | Value |
|----------|-------|
| **Layer** | L01 (Data Layer) |
| **Module** | `L01_data_layer.services.document_store` |
| **Status** | Fully Implemented & Healthy |
| **Dependencies** | PostgreSQL |
| **Category** | Data & Storage |

## Role in Development Environment

The **DocumentStore** is a general-purpose document persistence service. It stores:
- Documents with title and content
- MIME type tracking for content format
- Arbitrary metadata
- Searchable tags
- Version tracking on updates

Use this for storing any text-based content: specifications, prompts, reports, logs, etc.

## Data Model

### Document Fields
- `id: UUID` - Unique identifier
- `title: str` - Document title (max 500 chars)
- `content: str` - Document content (can be large)
- `content_type: str` - MIME type (default: "text/plain")
- `metadata: Dict[str, Any]` - Arbitrary key-value metadata
- `tags: List[str]` - Searchable tags
- `version: int` - Auto-incremented on update
- `created_at: datetime` - Creation timestamp
- `updated_at: datetime` - Last update timestamp

### Supported Content Types
Common MIME types:
- `text/plain` - Plain text
- `text/markdown` - Markdown
- `application/json` - JSON
- `text/html` - HTML
- `application/yaml` - YAML

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/documents/` | Create document |
| `GET` | `/documents/{id}` | Get document by ID |
| `PATCH` | `/documents/{id}` | Update document |
| `DELETE` | `/documents/{id}` | Delete document |
| `GET` | `/documents/` | List documents |

## Use Cases in Your Workflow

### 1. Store Specification Documents
```bash
curl -X POST http://localhost:8011/documents/ \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Steam Modal Component Specification",
    "content": "# Steam Modal\n\n## Overview\n...",
    "content_type": "text/markdown",
    "tags": ["spec", "component", "steam-modal"],
    "metadata": {
      "author": "claude-code",
      "version": "1.0.0"
    }
  }'
```

### 2. Store Prompt Templates
```bash
curl -X POST http://localhost:8011/documents/ \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Code Review Prompt",
    "content": "Review the following code for:\n1. Security issues\n2. Performance\n3. Best practices\n\nCode:\n{{code}}",
    "content_type": "text/plain",
    "tags": ["prompt", "code-review"],
    "metadata": {"prompt_type": "template"}
  }'
```

### 3. Store Session Reports
```bash
curl -X POST http://localhost:8011/documents/ \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Session Report - 2026-01-24",
    "content": "{\"tasks_completed\": 5, \"files_modified\": 12}",
    "content_type": "application/json",
    "tags": ["report", "session"],
    "metadata": {"session_id": "abc123"}
  }'
```

### 4. Store Configuration as Document
```bash
curl -X POST http://localhost:8011/documents/ \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Agent Configuration - Explorer",
    "content": "thoroughness: high\nmax_depth: 10\ntimeout: 300",
    "content_type": "application/yaml",
    "tags": ["config", "agent"],
    "metadata": {"agent_type": "explorer"}
  }'
```

## Service Interactions

```
+------------------+
|  DocumentStore   | <--- L01 Data Layer (PostgreSQL)
|     (L01)        |
+--------+---------+
         |
   Used for:
         |
+------------------+     +-------------------+     +------------------+
|   Specifications |     |  Prompt Templates |     |  Session Reports |
+------------------+     +-------------------+     +------------------+
         |
         v
+------------------+     +-------------------+
|  SemanticCache   |     | DocumentConsolid- |
|     (L04)        |     |     ator (MCP)    |
+------------------+     +-------------------+
```

**Integration Points:**
- **SemanticCache (L04)**: Could index documents for semantic search
- **MCP Document Consolidator**: External tool that may store consolidated docs
- **Any service needing text storage**: Specs, prompts, reports, logs

## Version Tracking

Every update increments the version:
```bash
# Create document (version = 1)
curl -X POST http://localhost:8011/documents/ \
  -d '{"title": "My Doc", "content": "Initial"}'

# Update document (version = 2)
curl -X PATCH http://localhost:8011/documents/{id} \
  -d '{"content": "Updated content"}'

# Response includes: {"version": 2, ...}
```

## Execution Examples

```bash
# Create a document
curl -X POST http://localhost:8011/documents/ \
  -H "Content-Type: application/json" \
  -d '{
    "title": "API Design Guidelines",
    "content": "# REST API Guidelines\n\n1. Use nouns for resources\n2. Use HTTP verbs properly\n...",
    "content_type": "text/markdown",
    "tags": ["guidelines", "api", "rest"],
    "metadata": {"approved_by": "team-lead", "version": "2.0"}
  }'

# Get document by ID
curl http://localhost:8011/documents/550e8400-e29b-41d4-a716-446655440000

# Update document content
curl -X PATCH http://localhost:8011/documents/550e8400-e29b-41d4-a716-446655440000 \
  -H "Content-Type: application/json" \
  -d '{
    "content": "# Updated Guidelines\n...",
    "tags": ["guidelines", "api", "rest", "v2"]
  }'

# List all documents (recent first)
curl http://localhost:8011/documents/

# List with limit
curl "http://localhost:8011/documents/?limit=10"

# Delete document
curl -X DELETE http://localhost:8011/documents/550e8400-e29b-41d4-a716-446655440000
```

## Implementation Status

| Component | Status |
|-----------|--------|
| Create Document | Complete |
| Get Document | Complete |
| Update Document | Complete |
| Delete Document | Complete |
| List Documents | Complete |
| Version Tracking | Complete |
| PostgreSQL Integration | Complete |

## Remaining Work

| Item | Priority | Description |
|------|----------|-------------|
| Tag Search | Medium | Filter documents by tags |
| Full-Text Search | Medium | Search within content |
| Pagination | Medium | Offset-based pagination |
| Version History | Low | Keep old versions |
| Bulk Operations | Low | Create/update multiple documents |
| Redis Events | Low | Publish document lifecycle events |

## Strengths

- **Simple CRUD** - Easy to use for any document
- **Flexible content** - Store any text content with MIME type
- **Version tracking** - Know when documents change
- **Tag-based organization** - Categorize documents
- **Metadata flexibility** - Attach arbitrary key-value data

## Weaknesses

- **No search** - Cannot search by tags or content (yet)
- **No pagination** - Only limit parameter
- **No version history** - Old content is overwritten
- **No events** - Changes not published to Redis
- **No file storage** - Only text content (no binary/files)

## Best Practices

### Content Organization
Use content_type appropriately:
- `text/markdown` for documentation
- `application/json` for structured data
- `text/plain` for simple text
- `application/yaml` for config-like content

### Tag Conventions
Use consistent, hierarchical tags:
- Type: `spec`, `prompt`, `report`, `config`
- Domain: `agent`, `model`, `ui`, `api`
- Status: `draft`, `approved`, `deprecated`

### Metadata Patterns
Include useful tracking info:
```json
{
  "author": "claude-code",
  "created_by": "session-123",
  "approved_by": "human",
  "source": "conversation",
  "version": "1.0.0"
}
```

## Source Files

- Service: `platform/src/L01_data_layer/services/document_store.py`
- Models: `platform/src/L01_data_layer/models/document.py`
- Routes: (likely in `routers/documents.py`)

## Related Services

- ConfigStore (L01) - Structured config (vs. document content)
- EventStore (L01) - Event sourcing (vs. document storage)
- SemanticCache (L04) - Could cache/index documents
- MCP Document Consolidator - External consolidation tool

---
*Generated: 2026-01-24 | Platform Services Documentation*
