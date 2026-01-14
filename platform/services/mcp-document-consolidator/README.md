# MCP Document Consolidator - Complete Guide

## Overview

The MCP Document Consolidator is an MCP (Model Context Protocol) server that provides intelligent document knowledge management. It ingests documents, extracts atomic claims, detects conflicts, and consolidates multiple documents into a single authoritative source.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         MCP Server                               │
├─────────────────────────────────────────────────────────────────┤
│  Tools                                                           │
│  ├── ingest_document      - Parse & store documents              │
│  ├── consolidate_documents - Merge with conflict resolution      │
│  ├── find_overlaps        - Detect redundancy/conflicts          │
│  ├── get_source_of_truth  - Query with provenance                │
│  └── deprecate_document   - Mark deprecated with migration       │
├─────────────────────────────────────────────────────────────────┤
│  AI Pipelines                                                    │
│  ├── EmbeddingPipeline    - Vector generation (Python/fallback)  │
│  ├── LLMPipeline          - Ollama for claim extraction          │
│  └── VerificationPipeline - Multi-signal claim validation        │
├─────────────────────────────────────────────────────────────────┤
│  Storage                                                         │
│  ├── PostgreSQL + pgvector - Documents, claims, sections, vectors│
│  └── Neo4j                - Entity graph                         │
└─────────────────────────────────────────────────────────────────┘
```

---

## The Consolidation Pipeline

### Step 1: Document Ingestion (`ingest_document`)

When you ingest a document:

```
Input Document
     │
     ▼
┌─────────────────┐
│ Document Parser │ → Extracts sections, frontmatter, format detection
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Claim Extractor │ → LLM extracts atomic facts (subject-predicate-object)
└────────┬────────┘
         │
         ▼
┌──────────────────┐
│ Embedding Pipeline│ → Generates vectors for semantic search
└────────┬─────────┘
         │
         ▼
┌─────────────────┐
│ Entity Resolver │ → Links entities to Neo4j graph
└────────┬────────┘
         │
         ▼
   Stored in PostgreSQL (with pgvector) + Neo4j
```

**What gets stored:**
- Document metadata (title, path, hash, authority_level, document_type)
- Sections (header, content, line numbers)
- Atomic claims (subject, predicate, object, confidence score)
- Embeddings (vectors stored in PostgreSQL with pgvector)
- Entity relationships (in Neo4j graph)

### Step 2: Find Overlaps (`find_overlaps`)

Before consolidating, identify what overlaps:

```
┌────────────────────┐
│ Scope Resolution   │ → Resolve document IDs or glob patterns
└────────┬───────────┘
         │
         ▼
┌────────────────────┐
│ Embedding Search   │ → Query pgvector for similar sections
└────────┬───────────┘
         │
         ▼
┌────────────────────┐
│ Similarity Cluster │ → Group sections by cosine similarity (threshold: 0.80)
└────────┬───────────┘
         │
         ▼
┌────────────────────┐
│ Conflict Detection │ → Identify contradicting claims
└────────┬───────────┘
         │
         ▼
Output: overlap_clusters, conflict_pairs, redundancy_score, recommendations
```

**Conflict Types Detected:**
- `direct_negation` - "X is true" vs "X is false"
- `value_conflict` - "X = 10" vs "X = 20"
- `temporal_conflict` - Different timestamps for same event
- `scope_conflict` - Different applicability ranges
- `implication_conflict` - Logical contradictions

### Step 3: Consolidation (`consolidate_documents`)

The actual merge process:

```
┌─────────────────────┐
│ Resolve Document IDs │ → From document_ids, scope patterns, or cluster_id
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐
│ Load Documents      │ → Fetch docs, sections, claims from DB
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐
│ Detect Conflicts    │ → Run ConflictDetector on all claims
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐
│ Categorize Conflicts│
│ ├── auto_resolve    │ → strength < 0.3 (auto-resolved)
│ ├── pending_review  │ → 0.3 ≤ strength ≤ 0.9
│ └── require_human   │ → strength > 0.9 (needs manual review)
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐
│ Merge Engine        │ → Combines sections using strategy
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐
│ Generate Output     │ → Markdown, JSON, or YAML format
└─────────┬───────────┘
          │
          ▼
   New Consolidated Document Created
```

**Merge Strategies:**

| Strategy | Description |
|----------|-------------|
| `smart` | Choose higher confidence claim (default) |
| `newest_wins` | Prefer claims from most recently updated document |
| `authority_wins` | Prefer claims from higher authority_level document |
| `merge_all` | Include all claims, noting conflicts |

### Step 4: What Happens to Source Documents

**Source documents are NOT deleted.** Instead:

1. **Supersession Record Created** - Links old docs to new consolidated doc
2. **Optional Deprecation** - Use `deprecate_document` to mark sources as deprecated
3. **Reference Migration** - References to old docs can be auto-migrated to new doc
4. **Provenance Tracking** - The consolidated doc tracks which source contributed each section

```
Source Doc A ──┐
               │    ┌──────────────────┐
Source Doc B ──┼───▶│ Consolidated Doc │
               │    └──────────────────┘
Source Doc C ──┘           │
                           ▼
                    provenance_map: {
                      "Section 1": ["doc-a-id", "doc-b-id"],
                      "Section 2": ["doc-c-id"]
                    }
```

**To deprecate source documents after consolidation:**

```typescript
// After consolidation, deprecate each source
await deprecate_document({
  document_id: "source-doc-uuid",
  reason: "Consolidated into new-doc-uuid",
  superseded_by: "new-consolidated-doc-uuid",
  migrate_references: true,  // Update refs in other docs
  archive: false             // or true to move to archive
});
```

---

## Running from a Claude Session

### Prerequisites

1. **Start the infrastructure:**
```bash
cd mcp-document-consolidator
docker-compose up -d  # Starts PostgreSQL, Neo4j, Redis, Ollama
```

2. **Install Ollama and pull model:**
```bash
ollama pull llama3.1:8b
```

3. **Configure MCP in Claude:**

Add to your `.mcp.json` or Claude Code settings:
```json
{
  "mcpServers": {
    "document-consolidator": {
      "command": "node",
      "args": ["dist/server.js"],
      "cwd": "/path/to/mcp-document-consolidator",
      "env": {
        "POSTGRES_URL": "postgresql://user:pass@localhost:5432/docstore",
        "NEO4J_URI": "bolt://localhost:7687",
        "NEO4J_USER": "neo4j",
        "NEO4J_PASSWORD": "password",
        "OLLAMA_BASE_URL": "http://localhost:11434"
      }
    }
  }
}
```

### Using the Tools in Claude

#### 1. Ingest a Document

```
Use the ingest_document tool to add this spec to the knowledge base:
- file_path: /path/to/api-spec.md
- document_type: spec
- authority_level: 8
- tags: ["api", "v2"]
```

**Parameters:**
| Parameter | Required | Default | Description |
|-----------|----------|---------|-------------|
| `file_path` | One of three | - | Path to file |
| `content` | One of three | - | Inline content |
| `url` | One of three | - | URL to fetch |
| `document_type` | Yes | - | spec, guide, handoff, prompt, report, reference, decision, archive |
| `authority_level` | No | 5 | 1-10, higher = more authoritative |
| `tags` | No | [] | Categorization tags |
| `extract_claims` | No | true | Extract atomic claims via LLM |
| `generate_embeddings` | No | true | Generate vectors for search |
| `build_entity_graph` | No | true | Add entities to Neo4j |

#### 2. Find Overlapping Content

```
Use find_overlaps to check for redundant content:
- scope: ["docs/api/**/*.md"]
- similarity_threshold: 0.85
- conflict_types: ["direct_negation", "value_conflict"]
```

**Output includes:**
- `overlap_clusters` - Groups of similar sections with recommended action (merge/keep_newest/review)
- `conflict_pairs` - Specific contradictions between documents
- `redundancy_score` - 0-100 percentage of redundant content
- `recommendations` - Actionable suggestions with priority

#### 3. Consolidate Documents

```
Use consolidate_documents to merge these overlapping docs:
- document_ids: ["uuid-1", "uuid-2", "uuid-3"]
- strategy: smart
- output_format: markdown
- include_provenance: true
```

**Parameters:**
| Parameter | Required | Default | Description |
|-----------|----------|---------|-------------|
| `document_ids` | One of three | - | Specific UUIDs |
| `scope` | One of three | - | Glob patterns |
| `cluster_id` | One of three | - | From find_overlaps output |
| `strategy` | No | smart | smart, newest_wins, authority_wins, merge_all |
| `conflict_threshold` | No | 0.7 | Similarity threshold for conflicts |
| `auto_resolve_below` | No | 0.3 | Auto-resolve conflicts below this strength |
| `require_human_above` | No | 0.9 | Require manual review above this |
| `output_format` | No | markdown | markdown, json, yaml |
| `include_provenance` | No | true | Track which doc contributed each section |
| `dry_run` | No | false | Preview without creating document |

**Output:**
```json
{
  "consolidation_id": "uuid",
  "status": "completed" | "pending_review" | "failed",
  "output_document": {
    "document_id": "new-uuid",
    "title": "Consolidated: Doc A + Doc B",
    "content": "# Consolidated Document\n...",
    "format": "markdown"
  },
  "source_documents": [...],
  "conflicts_resolved": 5,
  "conflicts_pending": [
    {
      "conflict_id": "uuid",
      "description": "direct_negation: 'API uses REST' vs 'API uses GraphQL'",
      "options": [...]
    }
  ],
  "provenance_map": {
    "Authentication": ["doc-a-id"],
    "Error Handling": ["doc-b-id", "doc-c-id"]
  }
}
```

#### 4. Query for Authoritative Answer

```
Use get_source_of_truth to answer:
- query: "What is the authentication method for the API?"
- query_type: factual
- verify_claims: true
- max_sources: 5
```

**Query Types:**
- `factual` - Direct answer with specific values
- `procedural` - Step-by-step instructions
- `conceptual` - Explanation of concepts
- `comparative` - Compare/contrast items

**Output includes:**
- `answer` - Generated answer from sources
- `confidence` - 0-1 confidence score
- `sources` - Documents with relevance scores and excerpts
- `supporting_claims` - Verified claims backing the answer
- `conflicting_claims` - Any contradictions found
- `knowledge_gaps` - What the corpus doesn't cover

#### 5. Deprecate Old Documents

```
Use deprecate_document to retire the old spec:
- document_id: "old-spec-uuid"
- reason: "Consolidated into comprehensive API guide"
- superseded_by: "new-consolidated-uuid"
- migrate_references: true
- archive: false
```

---

## Typical Workflow Example

```
1. INGEST DOCUMENTS
   ├── ingest_document(file_path: "api-v1-spec.md", document_type: "spec")
   ├── ingest_document(file_path: "api-v2-changes.md", document_type: "spec")
   └── ingest_document(file_path: "api-guide.md", document_type: "guide")

2. ANALYZE OVERLAPS
   └── find_overlaps(scope: ["api-*.md"])
       → Returns: 3 overlap clusters, 2 conflicts, redundancy: 45%

3. CONSOLIDATE
   └── consolidate_documents(
         cluster_id: "overlap-cluster-uuid",
         strategy: "smart",
         output_format: "markdown"
       )
       → Creates: "Consolidated API Documentation" (new-doc-uuid)
       → Resolves: 2 conflicts automatically
       → Pending: 0 conflicts for human review

4. DEPRECATE SOURCES
   ├── deprecate_document(document_id: "api-v1-spec-uuid", superseded_by: "new-doc-uuid")
   ├── deprecate_document(document_id: "api-v2-changes-uuid", superseded_by: "new-doc-uuid")
   └── deprecate_document(document_id: "api-guide-uuid", superseded_by: "new-doc-uuid")

5. QUERY CONSOLIDATED KNOWLEDGE
   └── get_source_of_truth(query: "How do I authenticate API requests?")
       → Returns answer from consolidated doc with full provenance
```

---

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `POSTGRES_URL` | Yes | - | PostgreSQL connection string (with pgvector extension) |
| `NEO4J_URI` | Yes | - | Neo4j bolt URI |
| `NEO4J_USER` | Yes | - | Neo4j username |
| `NEO4J_PASSWORD` | Yes | - | Neo4j password |
| `OLLAMA_BASE_URL` | No | `http://localhost:11434` | Ollama API URL |
| `OLLAMA_MODEL` | No | `llama3.1:8b` | Model for claim extraction |
| `EMBEDDING_MODEL` | No | `all-MiniLM-L6-v2` | Sentence transformer model |

---

## Document Types

| Type | Purpose | Typical Authority |
|------|---------|-------------------|
| `spec` | Technical specifications | 8-10 |
| `guide` | How-to guides | 6-8 |
| `handoff` | Session handoff notes | 5-7 |
| `prompt` | Prompt templates | 5-7 |
| `report` | Analysis reports | 6-8 |
| `reference` | Reference material | 7-9 |
| `decision` | Decision records | 8-10 |
| `archive` | Deprecated/archived | 1-3 |
