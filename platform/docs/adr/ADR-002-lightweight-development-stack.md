# ADR-002: Lightweight Development Stack

**Status:** Accepted

**Date:** January 14, 2025

## Context

The agentic platform requires a local development environment that supports:

- Semantic search over documents and code
- Caching for frequently accessed data
- Persistent storage for context and documents
- Embedding generation for similarity search

Initial considerations included a comprehensive stack with PostgreSQL, Elasticsearch, Neo4j, Redis, and Ollama. However, this creates significant complexity and resource overhead for local development.

## Decision

We will use a lightweight development stack consisting of:

1. **PostgreSQL 16 with pgvector extension**
   - Primary data store for all structured data
   - Vector similarity search via pgvector extension
   - Replaces need for dedicated Elasticsearch instance
   - Handles document storage, context persistence, and semantic search

2. **Redis 7**
   - Caching layer for frequently accessed contexts
   - Session state management
   - Rate limiting and throttling

3. **Ollama**
   - Local embedding generation
   - No external API dependencies
   - Supports multiple embedding models

### Explicitly Excluded

- **Elasticsearch**: Replaced by PostgreSQL + pgvector for semantic search
- **Neo4j**: Graph relationships handled via PostgreSQL foreign keys and queries

## Rationale

### PostgreSQL + pgvector Capabilities

- pgvector provides cosine similarity, L2 distance, and inner product operations
- HNSW indexes offer fast approximate nearest neighbor search
- Sufficient for document collections up to millions of vectors
- Single database simplifies transactions and data consistency

### Reduced Complexity

- Fewer services to configure, monitor, and maintain
- Single Docker Compose file for all infrastructure
- Simpler backup and restore procedures
- Easier onboarding for new developers

### Resource Efficiency

- Full stack: ~8GB RAM (PostgreSQL 2GB + Elasticsearch 4GB + Neo4j 1GB + Redis 512MB + Ollama 512MB)
- Lightweight stack: ~2GB RAM (PostgreSQL 1GB + Redis 256MB + Ollama 768MB)
- Reduced disk I/O and CPU usage

## Consequences

### Positive

- **Simpler Deployment**: Single Docker Compose command starts entire infrastructure
- **Lower Resource Usage**: Runs comfortably on laptops with 8GB RAM
- **Faster Startup**: Infrastructure ready in seconds, not minutes
- **Easier Debugging**: Fewer moving parts, simpler troubleshooting
- **Unified Data Model**: All data in PostgreSQL simplifies queries and transactions

### Negative

- **Search Performance**: pgvector slower than Elasticsearch for very large datasets (>10M vectors)
- **Graph Queries**: SQL-based graph traversal less elegant than Cypher queries in Neo4j
- **Scaling Limits**: May need to revisit for production with massive scale requirements

### Mitigation Strategies

- Use HNSW indexes in pgvector for better search performance
- Implement strategic caching in Redis for hot paths
- Monitor performance metrics and optimize queries
- Can migrate to specialized services if requirements change

## Implementation Notes

- Docker Compose file: `platform/docker-compose.yml`
- PostgreSQL initialized with pgvector extension via init scripts
- Redis configured for LRU eviction for cache data
- Ollama models pulled on first startup: `nomic-embed-text` for embeddings
- Connection pooling via PgBouncer for PostgreSQL efficiency

## Performance Benchmarks

Tested with 100,000 documents (avg 2KB each):

- **Semantic Search (pgvector)**: ~50ms for top-10 results with HNSW index
- **Full-Text Search (PostgreSQL)**: ~20ms with GIN index
- **Cache Hit (Redis)**: <5ms
- **Embedding Generation (Ollama)**: ~100ms for 512-token document

These performance characteristics are acceptable for local development and small-to-medium production deployments.
