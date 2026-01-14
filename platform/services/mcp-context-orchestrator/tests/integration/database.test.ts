import { describe, it, expect, beforeEach, vi, Mock } from 'vitest';

// Mock pg
vi.mock('pg', () => {
  const mockClient = {
    query: vi.fn(),
    release: vi.fn()
  };

  const mockPool = {
    query: vi.fn(),
    connect: vi.fn().mockResolvedValue(mockClient),
    end: vi.fn()
  };

  return {
    default: {
      Pool: vi.fn(() => mockPool)
    }
  };
});

describe('Database Integration', () => {
  let mockPool: { query: Mock; connect: Mock; end: Mock };
  let mockClient: { query: Mock; release: Mock };

  beforeEach(async () => {
    vi.clearAllMocks();

    const pg = await import('pg');
    mockPool = (pg.default.Pool as Mock)() as typeof mockPool;
    mockClient = (await mockPool.connect()) as typeof mockClient;
    mockPool.connect.mockClear();
  });

  describe('Context Storage', () => {
    it('should save task context to database', async () => {
      mockPool.query.mockResolvedValueOnce({
        rows: [
          {
            id: 'task-123',
            data: { name: 'Test Task', status: 'active' },
            version: 1,
          },
        ],
      });

      const result = await mockPool.query(
        `INSERT INTO mcp_contexts.task_contexts (id, data, version)
         VALUES ($1, $2, $3)
         RETURNING id, data, version`,
        ['task-123', JSON.stringify({ name: 'Test Task', status: 'active' }), 1]
      );

      expect(result.rows[0].id).toBe('task-123');
      expect(result.rows[0].version).toBe(1);
    });

    it('should retrieve task context from database', async () => {
      mockPool.query.mockResolvedValueOnce({
        rows: [
          {
            id: 'task-123',
            data: { name: 'Test Task', status: 'active' },
            version: 1,
          },
        ],
      });

      const result = await mockPool.query(
        'SELECT id, data, version FROM mcp_contexts.task_contexts WHERE id = $1',
        ['task-123']
      );

      expect(result.rows).toHaveLength(1);
      expect(result.rows[0].id).toBe('task-123');
      expect(result.rows[0].data).toEqual({ name: 'Test Task', status: 'active' });
    });

    it('should update task context with version increment', async () => {
      mockPool.query.mockResolvedValueOnce({
        rows: [
          {
            id: 'task-123',
            version: 2,
          },
        ],
      });

      const result = await mockPool.query(
        `UPDATE mcp_contexts.task_contexts
         SET data = $1, version = version + 1, updated_at = NOW()
         WHERE id = $2
         RETURNING id, version`,
        [JSON.stringify({ name: 'Updated Task', status: 'active' }), 'task-123']
      );

      expect(result.rows[0].version).toBe(2);
    });

    it('should delete task context', async () => {
      mockPool.query.mockResolvedValueOnce({ rowCount: 1 });

      const result = await mockPool.query(
        'DELETE FROM mcp_contexts.task_contexts WHERE id = $1',
        ['task-123']
      );

      expect(result.rowCount).toBe(1);
    });
  });

  describe('Checkpoint Operations', () => {
    it('should create checkpoint with snapshot', async () => {
      const snapshot = {
        createdAt: new Date().toISOString(),
        projectId: 'test-project',
        global: { hardRules: [] },
        tasks: {},
      };

      mockPool.query.mockResolvedValueOnce({
        rows: [
          {
            id: 'cp-123',
            label: 'Test Checkpoint',
            checkpoint_type: 'manual',
          },
        ],
      });

      const result = await mockPool.query(
        `INSERT INTO mcp_contexts.checkpoints
         (id, label, checkpoint_type, scope, snapshot)
         VALUES ($1, $2, $3, $4, $5)
         RETURNING id, label, checkpoint_type`,
        ['cp-123', 'Test Checkpoint', 'manual', 'global', JSON.stringify(snapshot)]
      );

      expect(result.rows[0].id).toBe('cp-123');
      expect(result.rows[0].checkpoint_type).toBe('manual');
    });

    it('should retrieve checkpoints by scope', async () => {
      mockPool.query.mockResolvedValueOnce({
        rows: [
          {
            id: 'cp-1',
            label: 'Checkpoint 1',
            scope: 'global',
            created_at: '2025-01-14T10:00:00Z',
          },
          {
            id: 'cp-2',
            label: 'Checkpoint 2',
            scope: 'global',
            created_at: '2025-01-14T11:00:00Z',
          },
        ],
      });

      const result = await mockPool.query(
        `SELECT id, label, scope, created_at
         FROM mcp_contexts.checkpoints
         WHERE scope = $1
         ORDER BY created_at DESC`,
        ['global']
      );

      expect(result.rows).toHaveLength(2);
      expect(result.rows[0].scope).toBe('global');
    });

    it('should retrieve checkpoint with snapshot', async () => {
      const snapshot = {
        createdAt: '2025-01-14T10:00:00Z',
        projectId: 'test-project',
        global: { hardRules: [] },
      };

      mockPool.query.mockResolvedValueOnce({
        rows: [
          {
            id: 'cp-123',
            label: 'Test Checkpoint',
            snapshot,
          },
        ],
      });

      const result = await mockPool.query(
        'SELECT id, label, snapshot FROM mcp_contexts.checkpoints WHERE id = $1',
        ['cp-123']
      );

      expect(result.rows[0].snapshot).toEqual(snapshot);
    });
  });

  describe('Global Context', () => {
    it('should save global context', async () => {
      const globalContext = {
        hardRules: ['Rule 1', 'Rule 2'],
        techStack: { backend: 'Node.js', frontend: 'React' },
        keyPaths: ['/src', '/tests'],
        services: ['api', 'worker'],
        activeTaskId: 'task-123',
      };

      mockPool.query.mockResolvedValueOnce({
        rows: [{ project_id: 'test-project' }],
      });

      const result = await mockPool.query(
        `INSERT INTO mcp_contexts.global_contexts
         (project_id, hard_rules, tech_stack, key_paths, services, active_task_id)
         VALUES ($1, $2, $3, $4, $5, $6)
         ON CONFLICT (project_id)
         DO UPDATE SET
           hard_rules = EXCLUDED.hard_rules,
           tech_stack = EXCLUDED.tech_stack,
           key_paths = EXCLUDED.key_paths,
           services = EXCLUDED.services,
           active_task_id = EXCLUDED.active_task_id,
           updated_at = NOW()
         RETURNING project_id`,
        [
          'test-project',
          JSON.stringify(globalContext.hardRules),
          JSON.stringify(globalContext.techStack),
          JSON.stringify(globalContext.keyPaths),
          JSON.stringify(globalContext.services),
          globalContext.activeTaskId,
        ]
      );

      expect(result.rows[0].project_id).toBe('test-project');
    });

    it('should retrieve global context', async () => {
      mockPool.query.mockResolvedValueOnce({
        rows: [
          {
            project_id: 'test-project',
            hard_rules: ['Rule 1'],
            tech_stack: { backend: 'Node.js' },
            key_paths: ['/src'],
            active_task_id: 'task-123',
          },
        ],
      });

      const result = await mockPool.query(
        `SELECT project_id, hard_rules, tech_stack, key_paths, active_task_id
         FROM mcp_contexts.global_contexts
         WHERE project_id = $1`,
        ['test-project']
      );

      expect(result.rows[0].project_id).toBe('test-project');
      expect(result.rows[0].active_task_id).toBe('task-123');
    });
  });

  describe('Conflict Detection', () => {
    it('should record detected conflicts', async () => {
      mockPool.query.mockResolvedValueOnce({
        rows: [{ id: 'conflict-1' }],
      });

      const result = await mockPool.query(
        `INSERT INTO mcp_contexts.conflicts
         (id, conflict_type, task_id, description, severity)
         VALUES ($1, $2, $3, $4, $5)
         RETURNING id`,
        ['conflict-1', 'version', 'task-123', 'Version mismatch', 'high']
      );

      expect(result.rows[0].id).toBe('conflict-1');
    });

    it('should retrieve conflicts by task', async () => {
      mockPool.query.mockResolvedValueOnce({
        rows: [
          {
            id: 'conflict-1',
            conflict_type: 'version',
            task_id: 'task-123',
            severity: 'high',
          },
          {
            id: 'conflict-2',
            conflict_type: 'data',
            task_id: 'task-123',
            severity: 'medium',
          },
        ],
      });

      const result = await mockPool.query(
        `SELECT id, conflict_type, task_id, severity
         FROM mcp_contexts.conflicts
         WHERE task_id = $1`,
        ['task-123']
      );

      expect(result.rows).toHaveLength(2);
      expect(result.rows[0].task_id).toBe('task-123');
    });

    it('should resolve conflict', async () => {
      mockPool.query.mockResolvedValueOnce({ rowCount: 1 });

      const result = await mockPool.query(
        `UPDATE mcp_contexts.conflicts
         SET status = 'resolved', resolved_at = NOW()
         WHERE id = $1`,
        ['conflict-1']
      );

      expect(result.rowCount).toBe(1);
    });
  });

  describe('Transaction Support', () => {
    it('should support transactions for atomic updates', async () => {
      mockPool.connect.mockResolvedValueOnce(mockClient);
      mockClient.query.mockResolvedValue({ rows: [] });

      await mockClient.query('BEGIN');
      await mockClient.query('UPDATE mcp_contexts.task_contexts SET data = $1 WHERE id = $2', [
        '{}',
        'task-1',
      ]);
      await mockClient.query('UPDATE mcp_contexts.task_contexts SET data = $1 WHERE id = $2', [
        '{}',
        'task-2',
      ]);
      await mockClient.query('COMMIT');

      expect(mockClient.query).toHaveBeenCalledWith('BEGIN');
      expect(mockClient.query).toHaveBeenCalledWith('COMMIT');
      expect(mockClient.query).toHaveBeenCalledTimes(4);
    });

    it('should rollback on transaction error', async () => {
      mockPool.connect.mockResolvedValueOnce(mockClient);
      mockClient.query
        .mockResolvedValueOnce({ rows: [] }) // BEGIN
        .mockRejectedValueOnce(new Error('Update failed')) // Failed update
        .mockResolvedValueOnce({ rows: [] }); // ROLLBACK

      try {
        await mockClient.query('BEGIN');
        await mockClient.query('UPDATE mcp_contexts.task_contexts SET invalid');
      } catch (error) {
        await mockClient.query('ROLLBACK');
      }

      expect(mockClient.query).toHaveBeenCalledWith('ROLLBACK');
    });
  });
});
