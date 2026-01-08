/**
 * useLocalStorage Hook
 * Wrapper around IndexedDB operations for React components
 */

import { useState, useEffect, useCallback } from 'react';
import type { StoryRecord } from '../types';
import {
  saveStory,
  getAllStories,
  deleteStory,
  updateStory,
  checkStorageQuota,
} from '../utils/storage';

interface UseLocalStorageReturn {
  data: StoryRecord[] | null;
  loading: boolean;
  error: Error | null;
  saveData: (story: StoryRecord) => Promise<void>;
  deleteData: (id: string) => Promise<void>;
  updateData: (id: string, updates: Partial<StoryRecord>) => Promise<void>;
  refetch: () => Promise<void>;
  hasQuota: boolean;
}

export function useLocalStorage(): UseLocalStorageReturn {
  const [data, setData] = useState<StoryRecord[] | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);
  const [hasQuota, setHasQuota] = useState(true);

  /**
   * Fetch all stories from IndexedDB
   */
  const refetch = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);

      const stories = await getAllStories();
      setData(stories);

      // Check storage quota
      const quota = await checkStorageQuota();
      setHasQuota(quota);
    } catch (err) {
      const error = err instanceof Error ? err : new Error('Failed to fetch stories');
      setError(error);
      setData(null);
    } finally {
      setLoading(false);
    }
  }, []);

  /**
   * Save a story
   */
  const saveData = useCallback(
    async (story: StoryRecord) => {
      try {
        await saveStory(story);
        await refetch();
      } catch (err) {
        const error = err instanceof Error ? err : new Error('Failed to save story');
        setError(error);
        throw error;
      }
    },
    [refetch],
  );

  /**
   * Delete a story
   */
  const deleteData = useCallback(
    async (id: string) => {
      try {
        await deleteStory(id);
        await refetch();
      } catch (err) {
        const error = err instanceof Error ? err : new Error('Failed to delete story');
        setError(error);
        throw error;
      }
    },
    [refetch],
  );

  /**
   * Update a story
   */
  const updateData = useCallback(
    async (id: string, updates: Partial<StoryRecord>) => {
      try {
        await updateStory(id, updates);
        await refetch();
      } catch (err) {
        const error = err instanceof Error ? err : new Error('Failed to update story');
        setError(error);
        throw error;
      }
    },
    [refetch],
  );

  // Load stories on mount
  useEffect(() => {
    refetch();
  }, [refetch]);

  return {
    data,
    loading,
    error,
    saveData,
    deleteData,
    updateData,
    refetch,
    hasQuota,
  };
}
