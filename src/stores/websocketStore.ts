import { create } from 'zustand';

export type ConnectionState = 'connected' | 'connecting' | 'reconnecting' | 'disconnected';

interface PendingMessage {
  id: string;
  message: Record<string, unknown>;
  timestamp: number;
  retries: number;
}

interface WebSocketState {
  // State
  isConnected: boolean;
  connectionState: ConnectionState;
  reconnectAttempts: number;
  maxReconnectAttempts: number;
  lastError: string | null;
  lastConnectedAt: Date | null;
  lastDisconnectedAt: Date | null;
  ws: WebSocket | null;

  // Offline queue
  pendingMessages: PendingMessage[];

  // Actions
  setConnected: (connected: boolean) => void;
  setConnectionState: (state: ConnectionState) => void;
  setWebSocket: (ws: WebSocket | null) => void;
  incrementReconnectAttempts: () => void;
  resetReconnectAttempts: () => void;
  setLastError: (error: string | null) => void;
  setLastConnectedAt: (date: Date | null) => void;
  setLastDisconnectedAt: (date: Date | null) => void;

  // Offline queue actions
  addPendingMessage: (message: Record<string, unknown>) => void;
  removePendingMessage: (id: string) => void;
  clearPendingMessages: () => void;
  processPendingMessages: () => void;

  // Helper
  sendMessage: (message: Record<string, unknown>) => void;

  // Task-specific event requests
  requestTaskEvents: (taskId: string) => void;
  requestTaskGraph: (taskId: string) => void;
  requestAgentMemory: (agentId: string, taskId?: string) => void;

  // Exponential backoff helper
  getBackoffDelay: () => number;
}

// Exponential backoff configuration
const BACKOFF_BASE = 1000; // 1 second
const BACKOFF_MAX = 30000; // 30 seconds
const MAX_RECONNECT_ATTEMPTS = 10;

export const useWebSocketStore = create<WebSocketState>((set, get) => ({
  // Initial State
  isConnected: false,
  connectionState: 'disconnected',
  reconnectAttempts: 0,
  maxReconnectAttempts: MAX_RECONNECT_ATTEMPTS,
  lastError: null,
  lastConnectedAt: null,
  lastDisconnectedAt: null,
  ws: null,
  pendingMessages: [],

  // Actions
  setConnected: (connected) => {
    set({ isConnected: connected });
    if (connected) {
      set({
        connectionState: 'connected',
        lastConnectedAt: new Date(),
        lastError: null
      });
    }
  },

  setConnectionState: (state) => set({ connectionState: state }),

  setWebSocket: (ws) => set({ ws }),

  incrementReconnectAttempts: () =>
    set((state) => ({ reconnectAttempts: state.reconnectAttempts + 1 })),

  resetReconnectAttempts: () => set({ reconnectAttempts: 0 }),

  setLastError: (error) => set({ lastError: error }),

  setLastConnectedAt: (date) => set({ lastConnectedAt: date }),

  setLastDisconnectedAt: (date) => set({ lastDisconnectedAt: date }),

  // Offline queue actions
  addPendingMessage: (message) => {
    const pendingMessage: PendingMessage = {
      id: crypto.randomUUID(),
      message,
      timestamp: Date.now(),
      retries: 0,
    };
    set((state) => ({
      pendingMessages: [...state.pendingMessages, pendingMessage],
    }));
    console.log('[WebSocketStore] Message queued for later:', message);
  },

  removePendingMessage: (id) => {
    set((state) => ({
      pendingMessages: state.pendingMessages.filter((m) => m.id !== id),
    }));
  },

  clearPendingMessages: () => set({ pendingMessages: [] }),

  processPendingMessages: () => {
    const { ws, isConnected, pendingMessages, removePendingMessage } = get();
    if (!ws || !isConnected || ws.readyState !== WebSocket.OPEN) {
      return;
    }

    console.log(`[WebSocketStore] Processing ${pendingMessages.length} pending messages`);

    for (const pending of pendingMessages) {
      try {
        ws.send(JSON.stringify(pending.message));
        console.log('[WebSocketStore] Sent queued message:', pending.message);
        removePendingMessage(pending.id);
      } catch (error) {
        console.error('[WebSocketStore] Failed to send queued message:', error);
        // Keep in queue for retry
      }
    }
  },

  // Helper
  sendMessage: (message) => {
    const { ws, isConnected, addPendingMessage } = get();
    if (ws && isConnected && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify(message));
      console.log('[WebSocketStore] Message sent:', message);
    } else {
      // Queue message for later
      addPendingMessage(message);
    }
  },

  // Request task-specific events
  requestTaskEvents: (taskId: string) => {
    const { ws, isConnected } = get();
    if (ws && isConnected && ws.readyState === WebSocket.OPEN) {
      const message = {
        type: 'request_task_events',
        payload: { taskId }
      };
      ws.send(JSON.stringify(message));
      console.log('[WebSocketStore] Requested task events for:', taskId);
    } else {
      console.warn('[WebSocketStore] Cannot request task events: WebSocket not connected');
    }
  },

  // Request task graph
  requestTaskGraph: (taskId: string) => {
    const { sendMessage } = get();
    sendMessage({
      type: 'request_task_graph',
      payload: { taskId },
      timestamp: new Date().toISOString()
    });
    console.log('[WebSocketStore] Requested task graph for:', taskId);
  },

  // Request agent memory
  requestAgentMemory: (agentId: string, taskId?: string) => {
    const { sendMessage } = get();
    sendMessage({
      type: 'request_agent_memory',
      payload: { agentId, taskId },
      timestamp: new Date().toISOString()
    });
    console.log('[WebSocketStore] Requested agent memory for:', agentId);
  },

  // Exponential backoff helper
  getBackoffDelay: () => {
    const { reconnectAttempts } = get();
    const delay = Math.min(BACKOFF_BASE * Math.pow(2, reconnectAttempts), BACKOFF_MAX);
    // Add jitter (±10%)
    const jitter = delay * 0.1 * (Math.random() * 2 - 1);
    return Math.round(delay + jitter);
  },
}));
