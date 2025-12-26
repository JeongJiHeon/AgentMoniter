import { create } from 'zustand';

interface WebSocketState {
  // State
  isConnected: boolean;
  reconnectAttempts: number;
  ws: WebSocket | null;

  // Actions
  setConnected: (connected: boolean) => void;
  setWebSocket: (ws: WebSocket | null) => void;
  incrementReconnectAttempts: () => void;
  resetReconnectAttempts: () => void;

  // Helper
  sendMessage: (message: Record<string, unknown>) => void;
}

export const useWebSocketStore = create<WebSocketState>((set, get) => ({
  // Initial State
  isConnected: false,
  reconnectAttempts: 0,
  ws: null,

  // Actions
  setConnected: (connected) => set({ isConnected: connected }),

  setWebSocket: (ws) => set({ ws }),

  incrementReconnectAttempts: () =>
    set((state) => ({ reconnectAttempts: state.reconnectAttempts + 1 })),

  resetReconnectAttempts: () => set({ reconnectAttempts: 0 }),

  // Helper
  sendMessage: (message) => {
    const { ws, isConnected } = get();
    if (ws && isConnected && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify(message));
      console.log('[WebSocketStore] Message sent:', message);
    } else {
      console.warn('[WebSocketStore] Cannot send message: WebSocket not connected');
    }
  },
}));
