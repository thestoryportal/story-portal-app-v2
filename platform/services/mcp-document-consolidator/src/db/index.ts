import pg from 'pg';
import type {
  AtomicClaim,
  Entity,
  DocumentType
} from '../types.js';

const { Pool } = pg;

export interface DatabaseConfig {
  host: string;
  port: number;
  database: string;
  user: string;
  password: string;
  ssl?: boolean;
}

interface DocumentRecord {
  id: string;
  source_path: string;
  content_hash: string;
  format: string;
  document_type: DocumentType;
  title: string;
  authority_level: number;
  raw_content: string;
  frontmatter: Record<string, unknown>;
  created_at: Date;
  updated_at: Date;
}

interface SectionRecord {
  id: string;
  document_id: string;
  header: string;
  content: string;
  level: number;
  section_order: number;
  start_line: number;
  end_line: number;
}

interface ClaimRecord extends AtomicClaim {
  deprecated?: boolean;
  deprecated_at?: Date;
  source_document_id?: string;
}

interface ConflictRecord {
  id: string;
  claim_a_id: string;
  claim_b_id: string;
  conflict_type: string;
  strength: number;
  resolution_status: string;
  resolution_details?: Record<string, unknown>;
  created_at: Date;
}

interface SupersessionRecord {
  id: string;
  old_document_id: string;
  new_document_id: string;
  reason: string;
  created_at: Date;
}

interface ConsolidationRecord {
  id: string;
  source_document_ids: string[];
  result_document_id: string;
  strategy: string;
  conflicts_resolved: number;
  conflicts_pending: number;
  created_at: Date;
}

interface ProvenanceRecord {
  id: string;
  document_id: string;
  event_type: string;
  details: Record<string, unknown>;
  timestamp: Date;
}

export class DatabaseService {
  private pool: pg.Pool;

  documents: DocumentRepository;
  sections: SectionRepository;
  claims: ClaimRepository;
  conflicts: ConflictRepository;
  supersessions: SupersessionRepository;
  consolidations: ConsolidationRepository;
  provenance: ProvenanceRepository;
  documentTags: DocumentTagRepository;
  entities: EntityRepository;
  feedback: FeedbackRepository;

  constructor(config: DatabaseConfig) {
    this.pool = new Pool({
      host: config.host,
      port: config.port,
      database: config.database,
      user: config.user,
      password: config.password,
      ssl: config.ssl ? { rejectUnauthorized: false } : undefined,
      max: 20,
      idleTimeoutMillis: 30000,
      connectionTimeoutMillis: 2000
    });

    this.documents = new DocumentRepository(this.pool);
    this.sections = new SectionRepository(this.pool);
    this.claims = new ClaimRepository(this.pool);
    this.conflicts = new ConflictRepository(this.pool);
    this.supersessions = new SupersessionRepository(this.pool);
    this.consolidations = new ConsolidationRepository(this.pool);
    this.provenance = new ProvenanceRepository(this.pool);
    this.documentTags = new DocumentTagRepository(this.pool);
    this.entities = new EntityRepository(this.pool);
    this.feedback = new FeedbackRepository(this.pool);
  }

  async initialize(): Promise<void> {
    // Test connection
    const client = await this.pool.connect();
    try {
      await client.query('SELECT 1');
    } finally {
      client.release();
    }
  }

  async close(): Promise<void> {
    await this.pool.end();
  }

  async transaction<T>(fn: (client: pg.PoolClient) => Promise<T>): Promise<T> {
    const client = await this.pool.connect();
    try {
      await client.query('BEGIN');
      const result = await fn(client);
      await client.query('COMMIT');
      return result;
    } catch (error) {
      await client.query('ROLLBACK');
      throw error;
    } finally {
      client.release();
    }
  }
}

class DocumentRepository {
  constructor(private pool: pg.Pool) {}

  async create(doc: {
    id: string;
    source_path: string;
    content_hash: string;
    format: string;
    document_type: DocumentType;
    title: string;
    authority_level: number;
    raw_content: string;
    frontmatter: Record<string, unknown>;
  }): Promise<string> {
    const result = await this.pool.query(
      `INSERT INTO documents (id, source_path, content_hash, format, document_type, title, authority_level, raw_content, frontmatter)
       VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
       RETURNING id`,
      [doc.id, doc.source_path, doc.content_hash, doc.format, doc.document_type, doc.title, doc.authority_level, doc.raw_content, JSON.stringify(doc.frontmatter)]
    );
    return result.rows[0].id;
  }

  async findById(id: string): Promise<DocumentRecord | null> {
    const result = await this.pool.query(
      'SELECT * FROM documents WHERE id = $1',
      [id]
    );
    if (result.rows.length === 0) return null;
    const row = result.rows[0];
    return {
      ...row,
      frontmatter: typeof row.frontmatter === 'string' ? JSON.parse(row.frontmatter) : row.frontmatter
    };
  }

  async findAll(): Promise<DocumentRecord[]> {
    const result = await this.pool.query('SELECT * FROM documents ORDER BY created_at DESC');
    return result.rows.map(row => ({
      ...row,
      frontmatter: typeof row.frontmatter === 'string' ? JSON.parse(row.frontmatter) : row.frontmatter
    }));
  }

  async findByPathPattern(pattern: string): Promise<DocumentRecord[]> {
    // Convert glob pattern to SQL LIKE pattern
    const sqlPattern = pattern
      .replace(/\*/g, '%')
      .replace(/\?/g, '_');

    const result = await this.pool.query(
      'SELECT * FROM documents WHERE source_path LIKE $1',
      [sqlPattern]
    );
    return result.rows.map(row => ({
      ...row,
      frontmatter: typeof row.frontmatter === 'string' ? JSON.parse(row.frontmatter) : row.frontmatter
    }));
  }

  async findByContentHash(hash: string): Promise<DocumentRecord | null> {
    const result = await this.pool.query(
      'SELECT * FROM documents WHERE content_hash = $1',
      [hash]
    );
    if (result.rows.length === 0) return null;
    const row = result.rows[0];
    return {
      ...row,
      frontmatter: typeof row.frontmatter === 'string' ? JSON.parse(row.frontmatter) : row.frontmatter
    };
  }

  async update(id: string, updates: Partial<{
    document_type: string;
    title: string;
    authority_level: number;
    raw_content: string;
    frontmatter: Record<string, unknown>;
  }>): Promise<void> {
    const setClauses: string[] = [];
    const values: unknown[] = [];
    let paramIndex = 1;

    if (updates.document_type !== undefined) {
      setClauses.push(`document_type = $${paramIndex++}`);
      values.push(updates.document_type);
    }
    if (updates.title !== undefined) {
      setClauses.push(`title = $${paramIndex++}`);
      values.push(updates.title);
    }
    if (updates.authority_level !== undefined) {
      setClauses.push(`authority_level = $${paramIndex++}`);
      values.push(updates.authority_level);
    }
    if (updates.raw_content !== undefined) {
      setClauses.push(`raw_content = $${paramIndex++}`);
      values.push(updates.raw_content);
    }
    if (updates.frontmatter !== undefined) {
      setClauses.push(`frontmatter = $${paramIndex++}`);
      values.push(JSON.stringify(updates.frontmatter));
    }

    if (setClauses.length === 0) return;

    setClauses.push(`updated_at = NOW()`);
    values.push(id);

    await this.pool.query(
      `UPDATE documents SET ${setClauses.join(', ')} WHERE id = $${paramIndex}`,
      values
    );
  }

  async delete(id: string): Promise<void> {
    await this.pool.query('DELETE FROM documents WHERE id = $1', [id]);
  }

  async updateEmbedding(id: string, embedding: number[]): Promise<void> {
    await this.pool.query(
      'UPDATE documents SET embedding = $1 WHERE id = $2',
      [`[${embedding.join(',')}]`, id]
    );
  }

  async findSimilar(embedding: number[], limit: number = 5, excludeId?: string): Promise<Array<{
    id: string;
    title: string;
    similarity: number;
  }>> {
    const embeddingStr = `[${embedding.join(',')}]`;
    const query = excludeId
      ? `SELECT id, title, 1 - (embedding <=> $1::vector) as similarity
         FROM documents
         WHERE embedding IS NOT NULL AND id != $2
         ORDER BY embedding <=> $1::vector
         LIMIT $3`
      : `SELECT id, title, 1 - (embedding <=> $1::vector) as similarity
         FROM documents
         WHERE embedding IS NOT NULL
         ORDER BY embedding <=> $1::vector
         LIMIT $2`;

    const params = excludeId ? [embeddingStr, excludeId, limit] : [embeddingStr, limit];
    const result = await this.pool.query(query, params);
    return result.rows;
  }
}

class SectionRepository {
  constructor(private pool: pg.Pool) {}

  async create(section: {
    id: string;
    document_id: string;
    header: string;
    content: string;
    level: number;
    section_order: number;
    start_line: number;
    end_line: number;
  }): Promise<string> {
    const result = await this.pool.query(
      `INSERT INTO sections (id, document_id, header, content, level, section_order, start_line, end_line)
       VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
       RETURNING id`,
      [section.id, section.document_id, section.header, section.content, section.level, section.section_order, section.start_line, section.end_line]
    );
    return result.rows[0].id;
  }

  async findByDocumentId(documentId: string): Promise<SectionRecord[]> {
    const result = await this.pool.query(
      'SELECT * FROM sections WHERE document_id = $1 ORDER BY section_order',
      [documentId]
    );
    return result.rows;
  }

  async findByDocumentIds(documentIds: string[]): Promise<SectionRecord[]> {
    if (documentIds.length === 0) return [];
    const result = await this.pool.query(
      'SELECT * FROM sections WHERE document_id = ANY($1) ORDER BY document_id, section_order',
      [documentIds]
    );
    return result.rows;
  }

  async findById(id: string): Promise<SectionRecord | null> {
    const result = await this.pool.query(
      'SELECT * FROM sections WHERE id = $1',
      [id]
    );
    return result.rows[0] || null;
  }

  async updateEmbedding(id: string, embedding: number[]): Promise<void> {
    await this.pool.query(
      'UPDATE sections SET embedding = $1 WHERE id = $2',
      [`[${embedding.join(',')}]`, id]
    );
  }

  async findSimilar(embedding: number[], limit: number = 5, excludeDocumentId?: string): Promise<Array<{
    id: string;
    document_id: string;
    header: string;
    similarity: number;
  }>> {
    const embeddingStr = `[${embedding.join(',')}]`;
    const query = excludeDocumentId
      ? `SELECT id, document_id, header, 1 - (embedding <=> $1::vector) as similarity
         FROM sections
         WHERE embedding IS NOT NULL AND document_id != $2
         ORDER BY embedding <=> $1::vector
         LIMIT $3`
      : `SELECT id, document_id, header, 1 - (embedding <=> $1::vector) as similarity
         FROM sections
         WHERE embedding IS NOT NULL
         ORDER BY embedding <=> $1::vector
         LIMIT $2`;

    const params = excludeDocumentId ? [embeddingStr, excludeDocumentId, limit] : [embeddingStr, limit];
    const result = await this.pool.query(query, params);
    return result.rows;
  }

  async findWithEmbeddingsByDocumentIds(documentIds: string[]): Promise<Array<{
    id: string;
    document_id: string;
    header: string;
    content: string;
    embedding: number[];
  }>> {
    if (documentIds.length === 0) return [];
    const result = await this.pool.query(
      `SELECT id, document_id, header, content, embedding::text
       FROM sections
       WHERE document_id = ANY($1) AND embedding IS NOT NULL
       ORDER BY document_id, section_order`,
      [documentIds]
    );
    // Parse embedding from pgvector text format [x,y,z,...] to number[]
    return result.rows.map(row => ({
      ...row,
      embedding: row.embedding ? JSON.parse(row.embedding) : []
    }));
  }

  async semanticSearch(
    queryEmbedding: number[],
    limit: number = 10,
    scopeDocumentIds?: string[]
  ): Promise<Array<{
    section_id: string;
    document_id: string;
    header: string;
    content: string;
    similarity: number;
  }>> {
    const embeddingStr = `[${queryEmbedding.join(',')}]`;

    let query: string;
    let params: unknown[];

    if (scopeDocumentIds && scopeDocumentIds.length > 0) {
      query = `
        SELECT
          s.id as section_id,
          s.document_id,
          s.header,
          s.content,
          1 - (s.embedding <=> $1::vector) as similarity
        FROM sections s
        WHERE s.embedding IS NOT NULL
          AND s.document_id = ANY($2)
        ORDER BY s.embedding <=> $1::vector
        LIMIT $3
      `;
      params = [embeddingStr, scopeDocumentIds, limit];
    } else {
      query = `
        SELECT
          s.id as section_id,
          s.document_id,
          s.header,
          s.content,
          1 - (s.embedding <=> $1::vector) as similarity
        FROM sections s
        WHERE s.embedding IS NOT NULL
        ORDER BY s.embedding <=> $1::vector
        LIMIT $2
      `;
      params = [embeddingStr, limit];
    }

    const result = await this.pool.query(query, params);
    return result.rows;
  }
}

class ClaimRepository {
  constructor(private pool: pg.Pool) {}

  async create(claim: AtomicClaim & { document_id: string; section_id: string }): Promise<string> {
    const result = await this.pool.query(
      `INSERT INTO claims (id, document_id, section_id, subject, predicate, object, qualifier, confidence, original_text, claim_type)
       VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10)
       RETURNING id`,
      [claim.id, claim.document_id, claim.section_id, claim.subject, claim.predicate, claim.object, claim.qualifier || null, claim.confidence, claim.original_text, claim.claim_type || 'factual']
    );
    return result.rows[0].id;
  }

  async findByDocumentId(documentId: string): Promise<ClaimRecord[]> {
    const result = await this.pool.query(
      'SELECT * FROM claims WHERE document_id = $1',
      [documentId]
    );
    return result.rows;
  }

  async findByDocumentIds(documentIds: string[]): Promise<ClaimRecord[]> {
    if (documentIds.length === 0) return [];
    const result = await this.pool.query(
      'SELECT * FROM claims WHERE document_id = ANY($1)',
      [documentIds]
    );
    return result.rows;
  }

  async findBySectionId(sectionId: string): Promise<ClaimRecord[]> {
    const result = await this.pool.query(
      'SELECT * FROM claims WHERE section_id = $1',
      [sectionId]
    );
    return result.rows;
  }

  async findBySubject(subject: string): Promise<ClaimRecord[]> {
    const result = await this.pool.query(
      'SELECT * FROM claims WHERE LOWER(subject) = LOWER($1)',
      [subject]
    );
    return result.rows;
  }

  async findById(id: string): Promise<ClaimRecord | null> {
    const result = await this.pool.query(
      'SELECT * FROM claims WHERE id = $1',
      [id]
    );
    return result.rows[0] || null;
  }

  async update(id: string, updates: Partial<{
    deprecated: boolean;
    deprecated_at: Date;
    source_document_id: string;
    confidence: number;
  }>): Promise<void> {
    const setClauses: string[] = [];
    const values: unknown[] = [];
    let paramIndex = 1;

    if (updates.deprecated !== undefined) {
      setClauses.push(`deprecated = $${paramIndex++}`);
      values.push(updates.deprecated);
    }
    if (updates.deprecated_at !== undefined) {
      setClauses.push(`deprecated_at = $${paramIndex++}`);
      values.push(updates.deprecated_at);
    }
    if (updates.source_document_id !== undefined) {
      setClauses.push(`source_document_id = $${paramIndex++}`);
      values.push(updates.source_document_id);
    }
    if (updates.confidence !== undefined) {
      setClauses.push(`confidence = $${paramIndex++}`);
      values.push(updates.confidence);
    }

    if (setClauses.length === 0) return;

    values.push(id);

    await this.pool.query(
      `UPDATE claims SET ${setClauses.join(', ')} WHERE id = $${paramIndex}`,
      values
    );
  }
}

class ConflictRepository {
  constructor(private pool: pg.Pool) {}

  async create(conflict: {
    id: string;
    claim_a_id: string;
    claim_b_id: string;
    conflict_type: string;
    strength: number;
  }): Promise<string> {
    const result = await this.pool.query(
      `INSERT INTO conflicts (id, claim_a_id, claim_b_id, conflict_type, strength)
       VALUES ($1, $2, $3, $4, $5)
       RETURNING id`,
      [conflict.id, conflict.claim_a_id, conflict.claim_b_id, conflict.conflict_type, conflict.strength]
    );
    return result.rows[0].id;
  }

  async findByClaimIds(claimIds: string[]): Promise<ConflictRecord[]> {
    if (claimIds.length === 0) return [];
    const result = await this.pool.query(
      'SELECT * FROM conflicts WHERE claim_a_id = ANY($1) OR claim_b_id = ANY($1)',
      [claimIds]
    );
    return result.rows;
  }

  async findUnresolved(): Promise<ConflictRecord[]> {
    const result = await this.pool.query(
      "SELECT * FROM conflicts WHERE resolution_status = 'pending'"
    );
    return result.rows;
  }

  async resolve(id: string, details: Record<string, unknown>): Promise<void> {
    await this.pool.query(
      `UPDATE conflicts SET resolution_status = 'resolved', resolution_details = $1 WHERE id = $2`,
      [JSON.stringify(details), id]
    );
  }
}

class SupersessionRepository {
  constructor(private pool: pg.Pool) {}

  async create(supersession: {
    old_document_id: string;
    new_document_id: string;
    reason: string;
  }): Promise<string> {
    const result = await this.pool.query(
      `INSERT INTO supersessions (old_document_id, new_document_id, reason)
       VALUES ($1, $2, $3)
       RETURNING id`,
      [supersession.old_document_id, supersession.new_document_id, supersession.reason]
    );
    return result.rows[0].id;
  }

  async findByOldDocumentId(oldDocId: string): Promise<SupersessionRecord[]> {
    const result = await this.pool.query(
      'SELECT * FROM supersessions WHERE old_document_id = $1',
      [oldDocId]
    );
    return result.rows;
  }

  async findByNewDocumentId(newDocId: string): Promise<SupersessionRecord[]> {
    const result = await this.pool.query(
      'SELECT * FROM supersessions WHERE new_document_id = $1',
      [newDocId]
    );
    return result.rows;
  }
}

class ConsolidationRepository {
  constructor(private pool: pg.Pool) {}

  async create(consolidation: {
    id: string;
    source_document_ids: string[];
    result_document_id: string;
    strategy: string;
    conflicts_resolved: number;
    conflicts_pending: number;
  }): Promise<string> {
    const result = await this.pool.query(
      `INSERT INTO consolidations (id, source_document_ids, result_document_id, strategy, conflicts_resolved, conflicts_pending)
       VALUES ($1, $2, $3, $4, $5, $6)
       RETURNING id`,
      [consolidation.id, consolidation.source_document_ids, consolidation.result_document_id, consolidation.strategy, consolidation.conflicts_resolved, consolidation.conflicts_pending]
    );
    return result.rows[0].id;
  }

  async findByClusterId(clusterId: string): Promise<ConsolidationRecord | null> {
    // Cluster IDs are stored in frontmatter or as consolidation IDs
    const result = await this.pool.query(
      'SELECT * FROM consolidations WHERE id = $1',
      [clusterId]
    );
    return result.rows[0] || null;
  }

  async findByResultDocumentId(docId: string): Promise<ConsolidationRecord | null> {
    const result = await this.pool.query(
      'SELECT * FROM consolidations WHERE result_document_id = $1',
      [docId]
    );
    return result.rows[0] || null;
  }
}

class ProvenanceRepository {
  constructor(private pool: pg.Pool) {}

  async create(provenance: {
    id: string;
    document_id: string;
    event_type: string;
    details: Record<string, unknown>;
    timestamp: Date;
  }): Promise<string> {
    const result = await this.pool.query(
      `INSERT INTO provenance (id, document_id, event_type, details, timestamp)
       VALUES ($1, $2, $3, $4, $5)
       RETURNING id`,
      [provenance.id, provenance.document_id, provenance.event_type, JSON.stringify(provenance.details), provenance.timestamp]
    );
    return result.rows[0].id;
  }

  async findByDocumentId(documentId: string): Promise<ProvenanceRecord[]> {
    const result = await this.pool.query(
      'SELECT * FROM provenance WHERE document_id = $1 ORDER BY timestamp DESC',
      [documentId]
    );
    return result.rows.map(row => ({
      ...row,
      details: typeof row.details === 'string' ? JSON.parse(row.details) : row.details
    }));
  }
}

class DocumentTagRepository {
  constructor(private pool: pg.Pool) {}

  async add(documentId: string, tag: string): Promise<void> {
    await this.pool.query(
      `INSERT INTO document_tags (document_id, tag)
       VALUES ($1, $2)
       ON CONFLICT (document_id, tag) DO NOTHING`,
      [documentId, tag]
    );
  }

  async remove(documentId: string, tag: string): Promise<void> {
    await this.pool.query(
      'DELETE FROM document_tags WHERE document_id = $1 AND tag = $2',
      [documentId, tag]
    );
  }

  async findByDocumentId(documentId: string): Promise<string[]> {
    const result = await this.pool.query(
      'SELECT tag FROM document_tags WHERE document_id = $1',
      [documentId]
    );
    return result.rows.map(row => row.tag);
  }

  async findDocumentsByTag(tag: string): Promise<string[]> {
    const result = await this.pool.query(
      'SELECT document_id FROM document_tags WHERE tag = $1',
      [tag]
    );
    return result.rows.map(row => row.document_id);
  }
}

class EntityRepository {
  constructor(private pool: pg.Pool) {}

  async create(entity: Entity): Promise<string> {
    const result = await this.pool.query(
      `INSERT INTO entities (id, canonical_id, name, type, aliases, properties)
       VALUES ($1, $2, $3, $4, $5, $6)
       RETURNING id`,
      [entity.id, entity.canonical_id, entity.name, entity.type, entity.aliases, JSON.stringify(entity.properties || {})]
    );
    return result.rows[0].id;
  }

  async findByCanonicalId(canonicalId: string): Promise<Entity | null> {
    const result = await this.pool.query(
      'SELECT * FROM entities WHERE canonical_id = $1',
      [canonicalId]
    );
    if (result.rows.length === 0) return null;
    const row = result.rows[0];
    return {
      ...row,
      properties: typeof row.properties === 'string' ? JSON.parse(row.properties) : row.properties
    };
  }

  async findByName(name: string): Promise<Entity[]> {
    const result = await this.pool.query(
      'SELECT * FROM entities WHERE LOWER(name) = LOWER($1) OR $1 = ANY(aliases)',
      [name]
    );
    return result.rows.map(row => ({
      ...row,
      properties: typeof row.properties === 'string' ? JSON.parse(row.properties) : row.properties
    }));
  }
}

class FeedbackRepository {
  constructor(private pool: pg.Pool) {}

  async create(feedback: {
    id: string;
    claim_id?: string;
    conflict_id?: string;
    document_id?: string;
    feedback_type: string;
    content: string;
    user_id?: string;
  }): Promise<string> {
    const result = await this.pool.query(
      `INSERT INTO feedback (id, claim_id, conflict_id, document_id, feedback_type, content, user_id)
       VALUES ($1, $2, $3, $4, $5, $6, $7)
       RETURNING id`,
      [feedback.id, feedback.claim_id, feedback.conflict_id, feedback.document_id, feedback.feedback_type, feedback.content, feedback.user_id]
    );
    return result.rows[0].id;
  }

  async findByDocumentId(documentId: string): Promise<Array<{
    id: string;
    feedback_type: string;
    content: string;
    created_at: Date;
  }>> {
    const result = await this.pool.query(
      'SELECT * FROM feedback WHERE document_id = $1 ORDER BY created_at DESC',
      [documentId]
    );
    return result.rows;
  }
}

export function createDatabaseService(config: DatabaseConfig): DatabaseService {
  return new DatabaseService(config);
}
