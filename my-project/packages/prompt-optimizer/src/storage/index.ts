/**
 * Storage exports.
 */

export {
  FileAdapter,
  createFileAdapter,
  getStorageDir,
  ensureStorageDir,
  DEFAULT_STORAGE_DIR,
  type FileAdapterOptions,
} from './file-adapter.js';

export {
  ProfileStore,
  createProfileStore,
} from './profile-store.js';

export {
  MetricsStore,
  createMetricsStore,
} from './metrics-store.js';

export {
  CacheStore,
  createCacheStore,
  type CacheEntry,
  type CacheStats,
  type CacheStoreOptions,
} from './cache-store.js';
