import { useEffect, useRef, useState, useCallback } from 'react';
import type { WebSocketMessage, Agent, Ticket, ApprovalRequest } from '../types';

interface WebSocketHookOptions {
  url: string;
  reconnectInterval?: number;
  maxReconnectAttempts?: number;
}

interface WebSocketHookReturn {
  isConnected: boolean;
  agents: Agent[];
  tickets: Ticket[];
  approvalQueue: ApprovalRequest[];
  sendMessage: (message: WebSocketMessage) => void;
  reconnect: () => void;
}

export function useWebSocket({
  url,
  reconnectInterval = 3000,
  maxReconnectAttempts = 5,
}: WebSocketHookOptions): WebSocketHookReturn {
  const [isConnected, setIsConnected] = useState(false);
  const [agents, setAgents] = useState<Agent[]>([]);
  const [tickets, setTickets] = useState<Ticket[]>([]);
  const [approvalQueue, setApprovalQueue] = useState<ApprovalRequest[]>([]);

  const wsRef = useRef<WebSocket | null>(null);
  const reconnectAttemptsRef = useRef(0);
  const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const connect = useCallback(() => {
    try {
      const ws = new WebSocket(url);

      ws.onopen = () => {
        console.log('[WebSocket] Connected');
        setIsConnected(true);
        reconnectAttemptsRef.current = 0;
      };

      ws.onmessage = (event) => {
        try {
          const message: WebSocketMessage = JSON.parse(event.data);
          handleMessage(message);
        } catch (error) {
          console.error('[WebSocket] Failed to parse message:', error);
        }
      };

      ws.onclose = () => {
        console.log('[WebSocket] Disconnected');
        setIsConnected(false);
        scheduleReconnect();
      };

      ws.onerror = (error) => {
        console.error('[WebSocket] Error:', error);
      };

      wsRef.current = ws;
    } catch (error) {
      console.error('[WebSocket] Connection failed:', error);
      scheduleReconnect();
    }
  }, [url]);

  const scheduleReconnect = useCallback(() => {
    if (reconnectAttemptsRef.current >= maxReconnectAttempts) {
      console.log('[WebSocket] Max reconnect attempts reached');
      return;
    }

    reconnectTimeoutRef.current = setTimeout(() => {
      reconnectAttemptsRef.current++;
      console.log(`[WebSocket] Reconnecting... (attempt ${reconnectAttemptsRef.current})`);
      connect();
    }, reconnectInterval);
  }, [connect, reconnectInterval, maxReconnectAttempts]);

  const handleMessage = useCallback((message: WebSocketMessage) => {
    switch (message.type) {
      case 'agent_update':
        setAgents(prev => {
          const agent = message.payload as Agent;
          const index = prev.findIndex(a => a.id === agent.id);
          if (index >= 0) {
            const updated = [...prev];
            updated[index] = agent;
            return updated;
          }
          return [...prev, agent];
        });
        break;

      case 'ticket_created':
        setTickets(prev => [...prev, message.payload as Ticket]);
        break;

      case 'ticket_updated':
        setTickets(prev => {
          const ticket = message.payload as Ticket;
          return prev.map(t => t.id === ticket.id ? ticket : t);
        });
        break;

      case 'approval_request':
        setApprovalQueue(prev => [...prev, message.payload as ApprovalRequest]);
        break;

      default:
        console.log('[WebSocket] Unknown message type:', message.type);
    }
  }, []);

  const sendMessage = useCallback((message: WebSocketMessage) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(message));
    } else {
      console.warn('[WebSocket] Cannot send message: not connected');
    }
  }, []);

  const reconnect = useCallback(() => {
    if (wsRef.current) {
      wsRef.current.close();
    }
    reconnectAttemptsRef.current = 0;
    connect();
  }, [connect]);

  useEffect(() => {
    connect();

    return () => {
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, [connect]);

  return {
    isConnected,
    agents,
    tickets,
    approvalQueue,
    sendMessage,
    reconnect,
  };
}
