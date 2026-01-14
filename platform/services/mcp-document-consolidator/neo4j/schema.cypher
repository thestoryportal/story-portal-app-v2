// MCP Document Consolidator - Neo4j Schema
// Version: 2.0.0

// Constraints
CREATE CONSTRAINT entity_id IF NOT EXISTS FOR (e:Entity) REQUIRE e.id IS UNIQUE;
CREATE CONSTRAINT claim_id IF NOT EXISTS FOR (c:Claim) REQUIRE c.id IS UNIQUE;
CREATE CONSTRAINT document_id IF NOT EXISTS FOR (d:Document) REQUIRE d.id IS UNIQUE;

// Indexes
CREATE INDEX entity_name IF NOT EXISTS FOR (e:Entity) ON (e.canonical_name);
CREATE INDEX entity_type IF NOT EXISTS FOR (e:Entity) ON (e.type);
CREATE INDEX claim_subject IF NOT EXISTS FOR (c:Claim) ON (c.subject);
CREATE INDEX claim_deprecated IF NOT EXISTS FOR (c:Claim) ON (c.deprecated);

// Node labels and properties
// Entity: { id, canonical_name, type, aliases[], source_file, embedding[], created_at }
// Claim: { id, document_id, section_id, subject, predicate, object, confidence, deprecated }
// Document: { id, path, type, authority_level }

// Relationship types
// (Claim)-[:ABOUT]->(Entity)
// (Claim)-[:CONTRADICTS { strength, type }]->(Claim)
// (Entity)-[:RELATED_TO { relationship_type }]->(Entity)
// (Document)-[:SUPERSEDES]->(Document)
// (Claim)-[:FROM]->(Document)
