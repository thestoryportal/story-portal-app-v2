import { io, Socket } from 'socket.io-client'
import type { PlatformEvent } from '../types'

const WS_URL = import.meta.env.VITE_WS_URL || 'http://localhost:8010'

type EventCallback = (data: PlatformEvent) => void

class WebSocketManager {
  private socket: Socket | null = null
  private listeners: Map<string, Set<EventCallback>> = new Map()
  private reconnectAttempts = 0
  private maxReconnectAttempts = 5

  connect() {
    if (this.socket?.connected) {
      console.log('WebSocket already connected')
      return
    }

    this.socket = io(WS_URL, {
      transports: ['websocket', 'polling'],
      reconnection: true,
      reconnectionAttempts: this.maxReconnectAttempts,
      reconnectionDelay: 1000,
      reconnectionDelayMax: 5000,
    })

    this.socket.on('connect', () => {
      console.log('WebSocket connected')
      this.reconnectAttempts = 0
    })

    this.socket.on('disconnect', (reason) => {
      console.log('WebSocket disconnected:', reason)
    })

    this.socket.on('connect_error', (error) => {
      console.error('WebSocket connection error:', error)
      this.reconnectAttempts++

      if (this.reconnectAttempts >= this.maxReconnectAttempts) {
        console.error('Max reconnection attempts reached')
      }
    })

    // Forward events to listeners
    this.socket.on('event', (data: PlatformEvent) => {
      const eventType = data.event_type
      const listeners = this.listeners.get(eventType)

      if (listeners) {
        listeners.forEach((callback) => {
          try {
            callback(data)
          } catch (error) {
            console.error('Error in event listener:', error)
          }
        })
      }

      // Also notify wildcard listeners
      const wildcardListeners = this.listeners.get('*')
      if (wildcardListeners) {
        wildcardListeners.forEach((callback) => {
          try {
            callback(data)
          } catch (error) {
            console.error('Error in wildcard listener:', error)
          }
        })
      }
    })

    // Handle specific event types
    this.socket.on('agent.spawned', (data) => this.handleEvent('agent.spawned', data))
    this.socket.on('agent.terminated', (data) => this.handleEvent('agent.terminated', data))
    this.socket.on('agent.paused', (data) => this.handleEvent('agent.paused', data))
    this.socket.on('agent.resumed', (data) => this.handleEvent('agent.resumed', data))
    this.socket.on('task.started', (data) => this.handleEvent('task.started', data))
    this.socket.on('task.completed', (data) => this.handleEvent('task.completed', data))
    this.socket.on('task.failed', (data) => this.handleEvent('task.failed', data))
    this.socket.on('workflow.started', (data) => this.handleEvent('workflow.started', data))
    this.socket.on('workflow.completed', (data) => this.handleEvent('workflow.completed', data))
  }

  private handleEvent(eventType: string, data: any) {
    const event: PlatformEvent = {
      event_id: data.event_id || `${eventType}-${Date.now()}`,
      event_type: eventType,
      payload: data,
      timestamp: data.timestamp || new Date().toISOString(),
      source: data.source || 'websocket',
    }

    const listeners = this.listeners.get(eventType)
    if (listeners) {
      listeners.forEach((callback) => callback(event))
    }
  }

  disconnect() {
    if (this.socket) {
      this.socket.disconnect()
      this.socket = null
      this.reconnectAttempts = 0
      console.log('WebSocket disconnected manually')
    }
  }

  subscribe(eventType: string, callback: EventCallback): () => void {
    if (!this.listeners.has(eventType)) {
      this.listeners.set(eventType, new Set())
    }
    this.listeners.get(eventType)!.add(callback)

    // Subscribe to event on server if connected
    if (this.socket?.connected) {
      this.socket.emit('subscribe', { topics: [eventType] })
    }

    // Return unsubscribe function
    return () => {
      const listeners = this.listeners.get(eventType)
      if (listeners) {
        listeners.delete(callback)
        if (listeners.size === 0) {
          this.listeners.delete(eventType)
          // Unsubscribe from server
          if (this.socket?.connected) {
            this.socket.emit('unsubscribe', { topics: [eventType] })
          }
        }
      }
    }
  }

  subscribeToAll(callback: EventCallback): () => void {
    return this.subscribe('*', callback)
  }

  isConnected(): boolean {
    return this.socket?.connected || false
  }

  getConnectionStatus(): 'connected' | 'disconnected' | 'connecting' {
    if (!this.socket) return 'disconnected'
    if (this.socket.connected) return 'connected'
    return 'connecting'
  }
}

// Singleton instance
export const wsManager = new WebSocketManager()
export default wsManager
