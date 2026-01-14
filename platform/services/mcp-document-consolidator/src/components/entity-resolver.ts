import neo4j, { Driver, Session } from 'neo4j-driver';
import { v4 as uuidv4 } from 'uuid';
import type { Entity, EntityMention, EntityType } from '../types.js';
import { DatabaseError } from '../errors.js';

export interface EmbeddingService {
  embed(texts: string[]): Promise<number[][]>;
}

export class EntityResolver {
  private driver: Driver;
  private embeddingService: EmbeddingService;

  constructor(
    embeddingServiceOrUri: EmbeddingService | string,
    neo4jUriOrAuth: string | { username: string; password: string },
    neo4jAuthOrEmbedding?: { username: string; password: string } | EmbeddingService
  ) {
    // Support both orderings:
    // (neo4jUri, neo4jAuth, embeddingService) or (embeddingService, neo4jUri, neo4jAuth)
    let neo4jUri: string;
    let neo4jAuth: { username: string; password: string };
    let embeddingService: EmbeddingService;

    if (typeof embeddingServiceOrUri === 'string') {
      // Old order: (neo4jUri, neo4jAuth, embeddingService)
      neo4jUri = embeddingServiceOrUri;
      neo4jAuth = neo4jUriOrAuth as { username: string; password: string };
      embeddingService = neo4jAuthOrEmbedding as EmbeddingService;
    } else {
      // New order: (embeddingService, neo4jUri, neo4jAuth)
      embeddingService = embeddingServiceOrUri;
      neo4jUri = neo4jUriOrAuth as string;
      neo4jAuth = neo4jAuthOrEmbedding as { username: string; password: string };
    }

    this.driver = neo4j.driver(
      neo4jUri,
      neo4j.auth.basic(neo4jAuth.username, neo4jAuth.password)
    );
    this.embeddingService = embeddingService;
  }

  async resolve(mentions: EntityMention[]): Promise<Map<string, Entity>> {
    const resolved = new Map<string, Entity>();
    const session = this.driver.session();

    try {
      for (const mention of mentions) {
        // Check for existing entity by exact match
        let entity = await this.findByExactMatch(session, mention.text);

        // Check for existing entity by semantic similarity
        if (!entity) {
          entity = await this.findBySimilarity(session, mention.text);
        }

        // Create new entity if not found
        if (!entity) {
          entity = await this.createEntity(session, mention);
        } else {
          // Add alias if new mention text
          await this.addAlias(session, entity.canonical_id, mention.text);
        }

        resolved.set(mention.text, entity);
      }
    } catch (error) {
      throw new DatabaseError(
        'entity_resolution',
        error instanceof Error ? error.message : 'Unknown error'
      );
    } finally {
      await session.close();
    }

    return resolved;
  }

  private async findByExactMatch(session: Session, text: string): Promise<Entity | null> {
    const result = await session.run(`
      MATCH (e:Entity)
      WHERE e.canonical_name = $text OR $text IN e.aliases
      RETURN e
      LIMIT 1
    `, { text: text.toLowerCase() });

    if (result.records.length === 0) return null;

    const node = result.records[0].get('e');
    return {
      canonical_id: node.properties.id,
      canonical_name: node.properties.canonical_name,
      name: node.properties.canonical_name,
      type: node.properties.type as EntityType,
      aliases: node.properties.aliases || [],
      source_file: node.properties.source_file,
      attributes: node.properties.attributes || {}
    };
  }

  private async findBySimilarity(session: Session, text: string): Promise<Entity | null> {
    try {
      // Get embedding for the mention
      const embeddings = await this.embeddingService.embed([text]);
      const embedding = embeddings[0];

      // Search for similar entities using cosine similarity
      // Note: This requires Neo4j GDS library to be installed
      const result = await session.run(`
        MATCH (e:Entity)
        WHERE e.embedding IS NOT NULL
        WITH e, gds.similarity.cosine(e.embedding, $embedding) AS similarity
        WHERE similarity > 0.85
        RETURN e, similarity
        ORDER BY similarity DESC
        LIMIT 1
      `, { embedding });

      if (result.records.length === 0) return null;

      const node = result.records[0].get('e');
      return {
        canonical_id: node.properties.id,
        canonical_name: node.properties.canonical_name,
        name: node.properties.canonical_name,
        type: node.properties.type as EntityType,
        aliases: node.properties.aliases || [],
        source_file: node.properties.source_file,
        attributes: node.properties.attributes || {}
      };
    } catch {
      // If GDS is not installed, fall back to exact match only
      return null;
    }
  }

  private async createEntity(session: Session, mention: EntityMention): Promise<Entity> {
    const id = uuidv4();
    const embeddings = await this.embeddingService.embed([mention.text]);
    const embedding = embeddings[0];
    const entityType = mention.type || this.inferEntityType(mention.text);

    await session.run(`
      CREATE (e:Entity {
        id: $id,
        canonical_name: $name,
        type: $type,
        aliases: [],
        embedding: $embedding,
        created_at: datetime()
      })
    `, {
      id,
      name: mention.text.toLowerCase(),
      type: entityType,
      embedding
    });

    return {
      canonical_id: id,
      canonical_name: mention.text.toLowerCase(),
      name: mention.text.toLowerCase(),
      type: entityType,
      aliases: [],
      attributes: {}
    };
  }

  private async addAlias(session: Session, entityId: string, alias: string): Promise<void> {
    await session.run(`
      MATCH (e:Entity {id: $entityId})
      WHERE NOT $alias IN e.aliases
      SET e.aliases = e.aliases + $alias
    `, { entityId, alias: alias.toLowerCase() });
  }

  /**
   * Infer entity type from mention text using heuristics
   */
  private inferEntityType(text: string): EntityType {
    const lowerText = text.toLowerCase();

    // Function patterns
    if (lowerText.match(/^(get|set|create|update|delete|fetch|handle|process|validate|parse)/)) {
      return 'function';
    }

    // Config patterns
    if (lowerText.match(/(config|setting|option|param|env)/)) {
      return 'config';
    }

    // File patterns
    if (lowerText.match(/\.(ts|js|json|yaml|yml|md|css|html|tsx|jsx)$/)) {
      return 'file';
    }

    // Component patterns (PascalCase or ends with Component/View/Page)
    if (lowerText.match(/^[A-Z][a-z]+([A-Z][a-z]+)*$/) ||
        lowerText.match(/(component|view|page|modal|dialog|widget)$/i)) {
      return 'component';
    }

    // Person patterns
    if (lowerText.match(/@|\.com|author|maintainer|owner/)) {
      return 'person';
    }

    return 'unknown';
  }

  /**
   * Create relationship between entities
   */
  async createRelationship(
    session: Session,
    fromEntityId: string,
    toEntityId: string,
    relationshipType: string
  ): Promise<void> {
    await session.run(`
      MATCH (a:Entity {id: $fromId})
      MATCH (b:Entity {id: $toId})
      MERGE (a)-[r:RELATED_TO {type: $relType}]->(b)
    `, {
      fromId: fromEntityId,
      toId: toEntityId,
      relType: relationshipType
    });
  }

  /**
   * Link claim to entity in the graph
   */
  async linkClaimToEntity(
    claimId: string,
    entityId: string,
    documentId: string
  ): Promise<void> {
    const session = this.driver.session();
    try {
      await session.run(`
        MERGE (c:Claim {id: $claimId})
        SET c.document_id = $documentId
        WITH c
        MATCH (e:Entity {id: $entityId})
        MERGE (c)-[:ABOUT]->(e)
      `, { claimId, entityId, documentId });
    } finally {
      await session.close();
    }
  }

  /**
   * Find related entities through graph traversal
   */
  async findRelatedEntities(entityId: string, maxDepth: number = 2): Promise<Entity[]> {
    const session = this.driver.session();
    try {
      const result = await session.run(`
        MATCH (start:Entity {id: $entityId})
        MATCH path = (start)-[:RELATED_TO*1..${maxDepth}]-(related:Entity)
        WHERE related.id <> $entityId
        RETURN DISTINCT related
      `, { entityId });

      return result.records.map(record => {
        const node = record.get('related');
        return {
          canonical_id: node.properties.id,
          canonical_name: node.properties.canonical_name,
          name: node.properties.canonical_name,
          type: node.properties.type as EntityType,
          aliases: node.properties.aliases || [],
          source_file: node.properties.source_file,
          attributes: node.properties.attributes || {}
        };
      });
    } finally {
      await session.close();
    }
  }

  /**
   * Get all entities from the graph
   */
  async getAllEntities(): Promise<Entity[]> {
    const session = this.driver.session();
    try {
      const result = await session.run(`
        MATCH (e:Entity)
        RETURN e
      `);

      return result.records.map(record => {
        const node = record.get('e');
        return {
          canonical_id: node.properties.id,
          canonical_name: node.properties.canonical_name,
          name: node.properties.canonical_name,
          type: node.properties.type as EntityType,
          aliases: node.properties.aliases || [],
          source_file: node.properties.source_file,
          attributes: node.properties.attributes || {}
        };
      });
    } finally {
      await session.close();
    }
  }

  /**
   * Close the driver connection
   */
  async close(): Promise<void> {
    await this.driver.close();
  }
}
