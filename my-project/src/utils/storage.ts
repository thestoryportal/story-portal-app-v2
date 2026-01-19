/**
 * Storage Utility - IndexedDB Operations
 *
 * Handles persistent storage of story records using IndexedDB.
 * Provides CRUD operations and storage quota management.
 */

import type { StoryRecord } from '../types/story'

const DB_NAME = 'StoryPortalDB'
const DB_VERSION = 1
const STORE_NAME = 'stories'

/**
 * Initialize and open IndexedDB connection
 */
function openDB(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open(DB_NAME, DB_VERSION)

    request.onerror = () => {
      reject(new Error('Failed to open database'))
    }

    request.onsuccess = () => {
      resolve(request.result)
    }

    request.onupgradeneeded = (event) => {
      const db = (event.target as IDBOpenDBRequest).result

      // Create object store if it doesn't exist
      if (!db.objectStoreNames.contains(STORE_NAME)) {
        const objectStore = db.createObjectStore(STORE_NAME, { keyPath: 'id' })

        // Create indexes for efficient querying
        objectStore.createIndex('created_at', 'created_at', { unique: false })
        objectStore.createIndex('prompt_id', 'prompt_id', { unique: false })
        objectStore.createIndex('sharing_status', 'sharing_status', { unique: false })
      }
    }
  })
}

/**
 * Save a story record to IndexedDB
 */
export async function saveStory(story: StoryRecord): Promise<void> {
  const db = await openDB()

  return new Promise((resolve, reject) => {
    const transaction = db.transaction([STORE_NAME], 'readwrite')
    const store = transaction.objectStore(STORE_NAME)
    const request = store.put(story)

    request.onsuccess = () => {
      resolve()
    }

    request.onerror = () => {
      reject(new Error(`Failed to save story: ${request.error?.message}`))
    }

    transaction.oncomplete = () => {
      db.close()
    }
  })
}

/**
 * Get all story records from IndexedDB
 * Returns stories sorted by creation date (newest first)
 */
export async function getAllStories(): Promise<StoryRecord[]> {
  const db = await openDB()

  return new Promise((resolve, reject) => {
    const transaction = db.transaction([STORE_NAME], 'readonly')
    const store = transaction.objectStore(STORE_NAME)
    const request = store.getAll()

    request.onsuccess = () => {
      const stories = request.result as StoryRecord[]

      // Sort by created_at descending (newest first)
      const sorted = stories.sort((a, b) => {
        return new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
      })

      resolve(sorted)
    }

    request.onerror = () => {
      reject(new Error('Failed to retrieve stories'))
    }

    transaction.oncomplete = () => {
      db.close()
    }
  })
}

/**
 * Get a single story by ID
 */
export async function getStoryById(id: string): Promise<StoryRecord | undefined> {
  const db = await openDB()

  return new Promise((resolve, reject) => {
    const transaction = db.transaction([STORE_NAME], 'readonly')
    const store = transaction.objectStore(STORE_NAME)
    const request = store.get(id)

    request.onsuccess = () => {
      resolve(request.result as StoryRecord | undefined)
    }

    request.onerror = () => {
      reject(new Error(`Failed to retrieve story: ${id}`))
    }

    transaction.oncomplete = () => {
      db.close()
    }
  })
}

/**
 * Update an existing story record
 */
export async function updateStory(
  id: string,
  updates: Partial<StoryRecord>
): Promise<void> {
  const db = await openDB()

  return new Promise((resolve, reject) => {
    const transaction = db.transaction([STORE_NAME], 'readwrite')
    const store = transaction.objectStore(STORE_NAME)
    const getRequest = store.get(id)

    getRequest.onsuccess = () => {
      const existingStory = getRequest.result as StoryRecord | undefined

      if (!existingStory) {
        reject(new Error(`Story not found: ${id}`))
        return
      }

      // Merge updates with existing story
      const updatedStory: StoryRecord = {
        ...existingStory,
        ...updates,
        id, // Ensure ID doesn't change
        updated_at: new Date().toISOString(),
      }

      const putRequest = store.put(updatedStory)

      putRequest.onsuccess = () => {
        resolve()
      }

      putRequest.onerror = () => {
        reject(new Error(`Failed to update story: ${putRequest.error?.message}`))
      }
    }

    getRequest.onerror = () => {
      reject(new Error(`Failed to retrieve story for update: ${id}`))
    }

    transaction.oncomplete = () => {
      db.close()
    }
  })
}

/**
 * Delete a story record from IndexedDB
 */
export async function deleteStory(id: string): Promise<void> {
  const db = await openDB()

  return new Promise((resolve, reject) => {
    const transaction = db.transaction([STORE_NAME], 'readwrite')
    const store = transaction.objectStore(STORE_NAME)
    const request = store.delete(id)

    request.onsuccess = () => {
      resolve()
    }

    request.onerror = () => {
      reject(new Error(`Failed to delete story: ${request.error?.message}`))
    }

    transaction.oncomplete = () => {
      db.close()
    }
  })
}

/**
 * Check storage quota and usage
 * Returns true if sufficient storage is available
 */
export async function checkStorageQuota(): Promise<boolean> {
  if (!navigator.storage || !navigator.storage.estimate) {
    // Storage API not available, assume quota is available
    return true
  }

  try {
    const estimate = await navigator.storage.estimate()
    const usage = estimate.usage || 0
    const quota = estimate.quota || 0

    // Consider quota available if less than 80% used
    const percentageUsed = quota > 0 ? (usage / quota) * 100 : 0
    return percentageUsed < 80
  } catch (error) {
    console.error('Failed to check storage quota:', error)
    return true // Assume available on error
  }
}

/**
 * Get storage usage information
 */
export async function getStorageInfo(): Promise<{
  usage: number
  quota: number
  percentageUsed: number
}> {
  if (!navigator.storage || !navigator.storage.estimate) {
    return { usage: 0, quota: 0, percentageUsed: 0 }
  }

  try {
    const estimate = await navigator.storage.estimate()
    const usage = estimate.usage || 0
    const quota = estimate.quota || 0
    const percentageUsed = quota > 0 ? (usage / quota) * 100 : 0

    return { usage, quota, percentageUsed }
  } catch (error) {
    console.error('Failed to get storage info:', error)
    return { usage: 0, quota: 0, percentageUsed: 0 }
  }
}

/**
 * Clear all stories from IndexedDB (use with caution)
 */
export async function clearAllStories(): Promise<void> {
  const db = await openDB()

  return new Promise((resolve, reject) => {
    const transaction = db.transaction([STORE_NAME], 'readwrite')
    const store = transaction.objectStore(STORE_NAME)
    const request = store.clear()

    request.onsuccess = () => {
      resolve()
    }

    request.onerror = () => {
      reject(new Error('Failed to clear all stories'))
    }

    transaction.oncomplete = () => {
      db.close()
    }
  })
}

/**
 * Export stories as JSON (for backup/export functionality)
 */
export async function exportStories(): Promise<string> {
  const stories = await getAllStories()

  // Convert Blobs to base64 for JSON serialization
  const exportData = await Promise.all(
    stories.map(async (story) => {
      const audioBase64 = await blobToBase64(story.audio_blob)
      const photoBase64 = story.photo?.blob
        ? await blobToBase64(story.photo.blob)
        : undefined

      return {
        ...story,
        audio_blob: audioBase64,
        photo: story.photo
          ? { ...story.photo, blob: photoBase64 }
          : undefined,
      }
    })
  )

  return JSON.stringify(exportData, null, 2)
}

/**
 * Helper: Convert Blob to base64 string
 */
function blobToBase64(blob: Blob): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onloadend = () => {
      const result = reader.result as string
      // Remove data URL prefix (e.g., "data:audio/webm;base64,")
      const base64 = result.split(',')[1] || result
      resolve(base64)
    }
    reader.onerror = () => {
      reject(new Error('Failed to convert blob to base64'))
    }
    reader.readAsDataURL(blob)
  })
}
