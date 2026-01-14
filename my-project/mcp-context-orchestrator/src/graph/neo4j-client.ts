/**
 * Neo4j Graph Client
 * Handles task relationships, agent assignments, and session tracking
 */

import neo4j, { Driver, Session, QueryResult, Integer } from 'neo4j-driver';

export interface Neo4jConfig {
  uri: string;
  username: string;
  password: string;
}

export interface TaskNode {
  taskId: string;
  name: string;
  status: string;
  phase?: string;
  priority: number;
  score?: number;
}

export interface AgentNode {
  agentId: string;
  type: string;
  capabilities: string[];
}

export interface SessionNode {
  sessionId: string;
  startedAt: string;
  endedAt?: string;
  compacted: boolean;
}

export interface TaskRelationshipInfo {
  sourceTaskId: string;
  targetTaskId: string;
  type: string;
  reason?: string;
}

export interface TaskGraphResult {
  task: TaskNode;
  relationships: {
    blocks: TaskNode[];
    blockedBy: TaskNode[];
    dependsOn: TaskNode[];
    dependencyOf: TaskNode[];
    relatedTo: TaskNode[];
  };
  agents: AgentNode[];
  recentSessions: SessionNode[];
}

export class Neo4jGraph {
  private driver: Driver | null = null;
  private config: Neo4jConfig;

  constructor(config: Neo4jConfig) {
    this.config = config;
  }

  async connect(): Promise<void> {
    this.driver = neo4j.driver(
      this.config.uri,
      neo4j.auth.basic(this.config.username, this.config.password),
      {
        maxConnectionLifetime: 3600000, // 1 hour
        maxConnectionPoolSize: 50,
        connectionAcquisitionTimeout: 30000
      }
    );

    // Verify connectivity
    try {
      await this.driver.verifyConnectivity();
      console.error('Neo4j connected');
    } catch (error) {
      console.error('Neo4j connection failed:', error);
      throw error;
    }

    // Initialize schema constraints
    await this.initializeSchema();
  }

  async disconnect(): Promise<void> {
    if (this.driver) {
      await this.driver.close();
      this.driver = null;
    }
  }

  private getSession(): Session {
    if (!this.driver) throw new Error('Neo4j not connected');
    return this.driver.session();
  }

  private async initializeSchema(): Promise<void> {
    const session = this.getSession();
    try {
      // Create constraints for unique IDs
      await session.run(`
        CREATE CONSTRAINT task_id IF NOT EXISTS
        FOR (t:Task) REQUIRE t.taskId IS UNIQUE
      `);

      await session.run(`
        CREATE CONSTRAINT agent_id IF NOT EXISTS
        FOR (a:Agent) REQUIRE a.agentId IS UNIQUE
      `);

      await session.run(`
        CREATE CONSTRAINT session_id IF NOT EXISTS
        FOR (s:Session) REQUIRE s.sessionId IS UNIQUE
      `);

      console.error('Neo4j schema initialized');
    } catch (error) {
      // Constraints may already exist, that's fine
      console.error('Neo4j schema initialization (may already exist):', error);
    } finally {
      await session.close();
    }
  }

  // ============================================================================
  // Task Operations
  // ============================================================================

  async createOrUpdateTask(task: TaskNode): Promise<void> {
    const session = this.getSession();
    try {
      await session.run(
        `
        MERGE (t:Task {taskId: $taskId})
        SET t.name = $name,
            t.status = $status,
            t.phase = $phase,
            t.priority = $priority,
            t.score = $score,
            t.updatedAt = datetime()
        `,
        {
          taskId: task.taskId,
          name: task.name,
          status: task.status,
          phase: task.phase || null,
          priority: task.priority,
          score: task.score || null
        }
      );
    } finally {
      await session.close();
    }
  }

  async getTask(taskId: string): Promise<TaskNode | null> {
    const session = this.getSession();
    try {
      const result = await session.run(
        `
        MATCH (t:Task {taskId: $taskId})
        RETURN t
        `,
        { taskId }
      );

      if (result.records.length === 0) return null;

      const node = result.records[0].get('t').properties;
      return {
        taskId: node.taskId,
        name: node.name,
        status: node.status,
        phase: node.phase,
        priority: neo4j.integer.toNumber(node.priority),
        score: node.score ? parseFloat(node.score) : undefined
      };
    } finally {
      await session.close();
    }
  }

  async deleteTask(taskId: string): Promise<void> {
    const session = this.getSession();
    try {
      await session.run(
        `
        MATCH (t:Task {taskId: $taskId})
        DETACH DELETE t
        `,
        { taskId }
      );
    } finally {
      await session.close();
    }
  }

  // ============================================================================
  // Relationship Operations
  // ============================================================================

  async createRelationship(
    sourceTaskId: string,
    targetTaskId: string,
    type: 'BLOCKS' | 'DEPENDS_ON' | 'RELATED_TO',
    reason?: string
  ): Promise<void> {
    const session = this.getSession();
    try {
      await session.run(
        `
        MATCH (source:Task {taskId: $sourceTaskId})
        MATCH (target:Task {taskId: $targetTaskId})
        MERGE (source)-[r:${type}]->(target)
        SET r.reason = $reason,
            r.createdAt = datetime()
        `,
        { sourceTaskId, targetTaskId, reason: reason || null }
      );
    } finally {
      await session.close();
    }
  }

  async removeRelationship(
    sourceTaskId: string,
    targetTaskId: string,
    type: 'BLOCKS' | 'DEPENDS_ON' | 'RELATED_TO'
  ): Promise<void> {
    const session = this.getSession();
    try {
      await session.run(
        `
        MATCH (source:Task {taskId: $sourceTaskId})-[r:${type}]->(target:Task {taskId: $targetTaskId})
        DELETE r
        `,
        { sourceTaskId, targetTaskId }
      );
    } finally {
      await session.close();
    }
  }

  async getTaskGraph(taskId: string): Promise<TaskGraphResult | null> {
    const session = this.getSession();
    try {
      // Get task and all relationships
      const result = await session.run(
        `
        MATCH (t:Task {taskId: $taskId})
        OPTIONAL MATCH (t)-[:BLOCKS]->(blocked:Task)
        OPTIONAL MATCH (blocker:Task)-[:BLOCKS]->(t)
        OPTIONAL MATCH (t)-[:DEPENDS_ON]->(dependency:Task)
        OPTIONAL MATCH (dependent:Task)-[:DEPENDS_ON]->(t)
        OPTIONAL MATCH (t)-[:RELATED_TO]-(related:Task)
        OPTIONAL MATCH (a:Agent)-[:ASSIGNED_TO]->(t)
        OPTIONAL MATCH (s:Session)-[:WORKED_ON]->(t)
        RETURN t,
               collect(DISTINCT blocked) as blocked,
               collect(DISTINCT blocker) as blockers,
               collect(DISTINCT dependency) as dependencies,
               collect(DISTINCT dependent) as dependents,
               collect(DISTINCT related) as related,
               collect(DISTINCT a) as agents,
               collect(DISTINCT s) as sessions
        `,
        { taskId }
      );

      if (result.records.length === 0) return null;

      const record = result.records[0];
      const taskNode = record.get('t').properties;

      const mapNode = (n: { properties: Record<string, unknown> }): TaskNode => ({
        taskId: n.properties.taskId as string,
        name: n.properties.name as string,
        status: n.properties.status as string,
        phase: n.properties.phase as string | undefined,
        priority: neo4j.integer.toNumber(n.properties.priority as Integer),
        score: n.properties.score ? parseFloat(n.properties.score as string) : undefined
      });

      return {
        task: {
          taskId: taskNode.taskId,
          name: taskNode.name,
          status: taskNode.status,
          phase: taskNode.phase,
          priority: neo4j.integer.toNumber(taskNode.priority),
          score: taskNode.score ? parseFloat(taskNode.score) : undefined
        },
        relationships: {
          blocks: record.get('blocked').filter((n: unknown) => n !== null).map(mapNode),
          blockedBy: record.get('blockers').filter((n: unknown) => n !== null).map(mapNode),
          dependsOn: record.get('dependencies').filter((n: unknown) => n !== null).map(mapNode),
          dependencyOf: record.get('dependents').filter((n: unknown) => n !== null).map(mapNode),
          relatedTo: record.get('related').filter((n: unknown) => n !== null).map(mapNode)
        },
        agents: record.get('agents').filter((n: unknown) => n !== null).map((n: { properties: Record<string, unknown> }) => ({
          agentId: n.properties.agentId as string,
          type: n.properties.type as string,
          capabilities: n.properties.capabilities as string[]
        })),
        recentSessions: record.get('sessions')
          .filter((n: unknown) => n !== null)
          .slice(0, 5)
          .map((n: { properties: Record<string, unknown> }) => ({
            sessionId: n.properties.sessionId as string,
            startedAt: n.properties.startedAt as string,
            endedAt: n.properties.endedAt as string | undefined,
            compacted: n.properties.compacted as boolean || false
          }))
      };
    } finally {
      await session.close();
    }
  }

  // ============================================================================
  // Agent Operations
  // ============================================================================

  async assignAgentToTask(
    agentId: string,
    agentType: string,
    taskId: string,
    capabilities: string[] = []
  ): Promise<void> {
    const session = this.getSession();
    try {
      await session.run(
        `
        MERGE (a:Agent {agentId: $agentId})
        SET a.type = $agentType,
            a.capabilities = $capabilities
        WITH a
        MATCH (t:Task {taskId: $taskId})
        MERGE (a)-[r:ASSIGNED_TO]->(t)
        SET r.since = datetime()
        `,
        { agentId, agentType, taskId, capabilities }
      );
    } finally {
      await session.close();
    }
  }

  async unassignAgentFromTask(agentId: string, taskId: string): Promise<void> {
    const session = this.getSession();
    try {
      await session.run(
        `
        MATCH (a:Agent {agentId: $agentId})-[r:ASSIGNED_TO]->(t:Task {taskId: $taskId})
        DELETE r
        `,
        { agentId, taskId }
      );
    } finally {
      await session.close();
    }
  }

  // ============================================================================
  // Session Operations
  // ============================================================================

  async recordSession(
    sessionId: string,
    taskId: string,
    duration?: number
  ): Promise<void> {
    const session = this.getSession();
    try {
      await session.run(
        `
        MERGE (s:Session {sessionId: $sessionId})
        SET s.startedAt = coalesce(s.startedAt, datetime()),
            s.compacted = false
        WITH s
        MATCH (t:Task {taskId: $taskId})
        MERGE (s)-[r:WORKED_ON]->(t)
        SET r.duration = coalesce(r.duration, 0) + coalesce($duration, 0)
        `,
        { sessionId, taskId, duration: duration || 0 }
      );
    } finally {
      await session.close();
    }
  }

  async markSessionEnded(sessionId: string): Promise<void> {
    const session = this.getSession();
    try {
      await session.run(
        `
        MATCH (s:Session {sessionId: $sessionId})
        SET s.endedAt = datetime()
        `,
        { sessionId }
      );
    } finally {
      await session.close();
    }
  }

  async markSessionCompacted(sessionId: string): Promise<void> {
    const session = this.getSession();
    try {
      await session.run(
        `
        MATCH (s:Session {sessionId: $sessionId})
        SET s.compacted = true,
            s.endedAt = datetime()
        `,
        { sessionId }
      );
    } finally {
      await session.close();
    }
  }

  // ============================================================================
  // Query Operations
  // ============================================================================

  async getBlockingTasks(taskId: string): Promise<TaskNode[]> {
    const session = this.getSession();
    try {
      const result = await session.run(
        `
        MATCH (blocker:Task)-[:BLOCKS]->(t:Task {taskId: $taskId})
        WHERE blocker.status <> 'completed'
        RETURN blocker
        `,
        { taskId }
      );

      return result.records.map((record) => {
        const node = record.get('blocker').properties;
        return {
          taskId: node.taskId,
          name: node.name,
          status: node.status,
          phase: node.phase,
          priority: neo4j.integer.toNumber(node.priority),
          score: node.score ? parseFloat(node.score) : undefined
        };
      });
    } finally {
      await session.close();
    }
  }

  async getReadyTasks(): Promise<TaskNode[]> {
    const session = this.getSession();
    try {
      // Tasks that have no uncompleted blockers
      const result = await session.run(
        `
        MATCH (t:Task)
        WHERE t.status IN ['pending', 'in_progress']
        AND NOT EXISTS {
          MATCH (blocker:Task)-[:BLOCKS]->(t)
          WHERE blocker.status <> 'completed'
        }
        RETURN t
        ORDER BY t.priority ASC
        `
      );

      return result.records.map((record) => {
        const node = record.get('t').properties;
        return {
          taskId: node.taskId,
          name: node.name,
          status: node.status,
          phase: node.phase,
          priority: neo4j.integer.toNumber(node.priority),
          score: node.score ? parseFloat(node.score) : undefined
        };
      });
    } finally {
      await session.close();
    }
  }

  async getTaskPath(fromTaskId: string, toTaskId: string): Promise<TaskNode[]> {
    const session = this.getSession();
    try {
      const result = await session.run(
        `
        MATCH path = shortestPath(
          (from:Task {taskId: $fromTaskId})-[*]-(to:Task {taskId: $toTaskId})
        )
        RETURN [node in nodes(path) | node] as pathNodes
        `,
        { fromTaskId, toTaskId }
      );

      if (result.records.length === 0) return [];

      return result.records[0].get('pathNodes').map((node: { properties: Record<string, unknown> }) => ({
        taskId: node.properties.taskId as string,
        name: node.properties.name as string,
        status: node.properties.status as string,
        phase: node.properties.phase as string | undefined,
        priority: neo4j.integer.toNumber(node.properties.priority as Integer),
        score: node.properties.score ? parseFloat(node.properties.score as string) : undefined
      }));
    } finally {
      await session.close();
    }
  }

  // ============================================================================
  // Utility Operations
  // ============================================================================

  async ping(): Promise<boolean> {
    if (!this.driver) return false;

    try {
      await this.driver.verifyConnectivity();
      return true;
    } catch {
      return false;
    }
  }

  async runQuery(cypher: string, params: Record<string, unknown> = {}): Promise<QueryResult> {
    const session = this.getSession();
    try {
      return await session.run(cypher, params);
    } finally {
      await session.close();
    }
  }
}
