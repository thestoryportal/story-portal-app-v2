import { describe, it, expect, vi, beforeEach } from 'vitest';
import { createCreateCheckpointTool, CreateCheckpointInputSchema } from '../../src/tools/create-checkpoint.js';
import type { ToolDependencies } from '../../src/tools/index.js';

// Mock dependencies
const mockDeps: ToolDependencies = {
  projectId: 'test-project',
  redis: {
    getTaskContext: vi.fn(),
    setTaskContext: vi.fn(),
    deleteTaskContext: vi.fn(),
    getHotContext: vi.fn(),
    setHotContext: vi.fn(),
  } as any,
};

vi.mock('../../src/db/client.js', () => ({
  getGlobalContext: vi.fn(),
  getTaskContext: vi.fn(),
  createCheckpoint: vi.fn(),
}));

describe('Tool Input Schemas', () => {
  describe('CreateCheckpointInputSchema', () => {
    it('should validate correct input', () => {
      const input = {
        label: 'Test Checkpoint',
        description: 'A test checkpoint',
        taskId: 'task-123',
        checkpointType: 'manual' as const,
      };

      const result = CreateCheckpointInputSchema.safeParse(input);
      expect(result.success).toBe(true);
    });

    it('should reject invalid checkpoint type', () => {
      const input = {
        label: 'Test Checkpoint',
        checkpointType: 'invalid',
      };

      const result = CreateCheckpointInputSchema.safeParse(input);
      expect(result.success).toBe(false);
    });

    it('should apply default checkpoint type', () => {
      const input = {
        label: 'Test Checkpoint',
      };

      const result = CreateCheckpointInputSchema.parse(input);
      expect(result.checkpointType).toBe('manual');
    });

    it('should validate optional fields', () => {
      const input = {
        label: 'Test Checkpoint',
        description: 'Optional description',
        taskId: 'task-123',
        includeTasks: ['task-456', 'task-789'],
        sessionId: 'session-abc',
      };

      const result = CreateCheckpointInputSchema.safeParse(input);
      expect(result.success).toBe(true);
      if (result.success) {
        expect(result.data.includeTasks).toHaveLength(2);
        expect(result.data.sessionId).toBe('session-abc');
      }
    });
  });
});

describe('Tools', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('create_checkpoint', () => {
    it('should create a task-scoped checkpoint', async () => {
      const { getGlobalContext, getTaskContext, createCheckpoint } = await import('../../src/db/client.js');

      vi.mocked(getGlobalContext).mockResolvedValue({
        hardRules: [],
        techStack: {},
        keyPaths: [],
        services: [],
        activeTaskId: 'task-123',
      } as any);

      vi.mocked(getTaskContext).mockResolvedValue({
        taskId: 'task-123',
        name: 'Test Task',
        status: 'active',
        currentPhase: 'planning',
        iteration: 1,
        score: 0,
        lockedElements: [],
        immediateContext: {},
        keyFiles: [],
        technicalDecisions: [],
        resumePrompt: '',
        version: 1,
      } as any);

      vi.mocked(createCheckpoint).mockResolvedValue(undefined);
      vi.mocked(mockDeps.redis.setTaskContext).mockResolvedValue(undefined);

      const tool = createCreateCheckpointTool(mockDeps);
      const result = await tool.execute({
        label: 'Test Checkpoint',
        taskId: 'task-123',
      });

      expect(result.success).toBe(true);
      expect(result.scope).toBe('task');
      expect(result.includedTasks).toEqual(['task-123']);
      expect(result.label).toBe('Test Checkpoint');
      expect(createCheckpoint).toHaveBeenCalledTimes(1);
    });

    it('should create a global checkpoint when no taskId provided', async () => {
      const { getGlobalContext, createCheckpoint } = await import('../../src/db/client.js');

      vi.mocked(getGlobalContext).mockResolvedValue({
        hardRules: [],
        techStack: {},
        keyPaths: [],
        services: [],
        activeTaskId: null,
      } as any);

      vi.mocked(createCheckpoint).mockResolvedValue(undefined);
      vi.mocked(mockDeps.redis.setTaskContext).mockResolvedValue(undefined);

      const tool = createCreateCheckpointTool(mockDeps);
      const result = await tool.execute({
        label: 'Global Checkpoint',
      });

      expect(result.success).toBe(true);
      expect(result.scope).toBe('global');
      expect(result.includedTasks).toEqual([]);
    });

    it('should create a multi-task checkpoint', async () => {
      const { getGlobalContext, getTaskContext, createCheckpoint } = await import('../../src/db/client.js');

      vi.mocked(getGlobalContext).mockResolvedValue({
        hardRules: [],
        techStack: {},
        keyPaths: [],
        services: [],
        activeTaskId: 'task-123',
      } as any);

      vi.mocked(getTaskContext).mockImplementation((taskId: string) =>
        Promise.resolve({
          taskId,
          name: `Task ${taskId}`,
          status: 'active',
          currentPhase: 'planning',
          iteration: 1,
          score: 0,
          lockedElements: [],
          immediateContext: {},
          keyFiles: [],
          technicalDecisions: [],
          resumePrompt: '',
          version: 1,
        } as any)
      );

      vi.mocked(createCheckpoint).mockResolvedValue(undefined);
      vi.mocked(mockDeps.redis.setTaskContext).mockResolvedValue(undefined);

      const tool = createCreateCheckpointTool(mockDeps);
      const result = await tool.execute({
        label: 'Multi-task Checkpoint',
        taskId: 'task-123',
        includeTasks: ['task-456', 'task-789'],
      });

      expect(result.success).toBe(true);
      expect(result.scope).toBe('multi_task');
      expect(result.includedTasks).toEqual(['task-123', 'task-456', 'task-789']);
      expect(getTaskContext).toHaveBeenCalledTimes(3);
    });

    it('should generate unique checkpoint ID', async () => {
      const { getGlobalContext, createCheckpoint } = await import('../../src/db/client.js');

      vi.mocked(getGlobalContext).mockResolvedValue({
        hardRules: [],
        techStack: {},
        keyPaths: [],
        services: [],
        activeTaskId: null,
      } as any);

      vi.mocked(createCheckpoint).mockResolvedValue(undefined);
      vi.mocked(mockDeps.redis.setTaskContext).mockResolvedValue(undefined);

      const tool = createCreateCheckpointTool(mockDeps);
      const result1 = await tool.execute({ label: 'Checkpoint 1' });
      const result2 = await tool.execute({ label: 'Checkpoint 2' });

      expect(result1.checkpointId).not.toBe(result2.checkpointId);
      expect(result1.checkpointId).toMatch(/^cp-\d+-[a-f0-9]{8}$/);
      expect(result2.checkpointId).toMatch(/^cp-\d+-[a-f0-9]{8}$/);
    });
  });
});
