import { useEffect, useRef, useCallback } from 'react';
import {
  useAgentStore,
  useTaskStore,
  useTicketStore,
  useChatStore,
  useWebSocketStore,
} from '../stores';
import type { Agent, Task, AgentLog, Interaction, TaskChatMessage, ChatMessage } from '../types';

interface UseWebSocketOptions {
  url: string;
  reconnectInterval?: number;
  maxReconnectAttempts?: number;
}

export function useWebSocket({
  url,
  reconnectInterval = 3000,
  maxReconnectAttempts = 10,
}: UseWebSocketOptions) {
  const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const lastEventTimestampRef = useRef<number | null>(null); // Track last event timestamp for cursor

  // Store actions
  const { setConnected, setWebSocket, incrementReconnectAttempts, resetReconnectAttempts } =
    useWebSocketStore();
  const { addAgent } = useAgentStore();
  const { addTask, updateTask, addInteraction, updateInteraction, addTaskChatMessage, addAgentLog } =
    useTaskStore();
  const { addTicket, updateTicket, addApprovalRequest } = useTicketStore();
  const { addChatMessage } = useChatStore();

  // Message handler
  const handleMessage = useCallback(
    (event: MessageEvent) => {
      try {
        const message = JSON.parse(event.data);

        // Track last event timestamp for reconnection cursor
        if (message.timestamp) {
          const timestamp = new Date(message.timestamp).getTime();
          lastEventTimestampRef.current = timestamp;
        }

        console.log('[WebSocket] Received message:', message.type);

        switch (message.type) {
          case 'task_created': {
            const payload = message.payload;
            const task: Task = {
              id: payload.id,
              title: payload.title,
              description: payload.description,
              status: payload.status,
              priority: payload.priority,
              source: payload.source,
              sourceReference: payload.sourceReference,
              tags: payload.tags || [],
              autoAssign: payload.autoAssign,
              createdAt: new Date(payload.createdAt),
              updatedAt: new Date(payload.updatedAt),
              completedAt: payload.completedAt ? new Date(payload.completedAt) : undefined,
            };
            addTask(task);
            console.log(`[WebSocket] Task created from ${task.source}: ${task.title}`);
            break;
          }

          case 'task_updated': {
            const payload = message.payload;
            updateTask(payload.id, {
              ...payload,
              updatedAt: new Date(payload.updatedAt),
              completedAt: payload.completedAt ? new Date(payload.completedAt) : undefined,
            });
            break;
          }

          case 'ticket_created': {
            const payload = message.payload;
            // Only add tickets without options to ticket list
            // Tickets with options are shown only in approval queue
            if (!payload.options || payload.options.length === 0) {
              addTicket(payload);
              console.log(`[WebSocket] Ticket created by agent ${payload.agentId}: ${payload.purpose}`);
            } else {
              console.log(`[WebSocket] Ticket with options created (approval queue only): ${payload.purpose}`);
            }
            break;
          }

          case 'ticket_updated': {
            const payload = message.payload;
            updateTicket(payload.id, payload);
            break;
          }

          case 'approval_request': {
            const payload = message.payload;
            // Only add approval requests with options
            if (payload.type === 'select_option' && payload.options && payload.options.length > 0) {
              addApprovalRequest(payload);
              console.log(`[WebSocket] Approval request from agent ${payload.agentId}: ${payload.message}`);
            } else {
              console.log(`[WebSocket] Approval request (no options) - ticket list only: ${payload.message}`);
            }
            break;
          }

          case 'agent_log': {
            const payload = message.payload;
            const agentLog: AgentLog = {
              id: payload.id || crypto.randomUUID(),
              agentId: payload.agentId,
              agentName: payload.agentName,
              type: payload.type,
              message: payload.message,
              details: payload.details,
              relatedTaskId: payload.relatedTaskId,
              timestamp: typeof payload.timestamp === 'string' ? new Date(payload.timestamp) : new Date(),
            };
            addAgentLog(agentLog);
            console.log(`[WebSocket] Agent log: ${agentLog.type} - ${agentLog.message}`);
            break;
          }

          case 'interaction_created': {
            const payload = message.payload as Interaction;
            addInteraction({
              ...payload,
              createdAt: new Date(payload.createdAt),
              respondedAt: payload.respondedAt ? new Date(payload.respondedAt) : undefined,
            });
            console.log(`[WebSocket] Interaction created: ${payload.question}`);
            break;
          }

          case 'interaction_responded': {
            const payload = message.payload as Interaction;
            updateInteraction(payload.id, {
              ...payload,
              createdAt: new Date(payload.createdAt),
              respondedAt: payload.respondedAt ? new Date(payload.respondedAt) : undefined,
            });
            console.log(`[WebSocket] Interaction responded: ${payload.id}`);
            break;
          }

          case 'chat_message_response': {
            const payload = message.payload;
            const chatMessage: ChatMessage = {
              id: payload.id || crypto.randomUUID(),
              role: payload.role || 'assistant',
              content: payload.content || '',
              timestamp: typeof payload.timestamp === 'string' ? new Date(payload.timestamp) : new Date(),
            };
            addChatMessage(chatMessage);
            console.log(`[WebSocket] Chat message added: ${chatMessage.role}`);
            break;
          }

          case 'task_interaction': {
            const payload = message.payload;
            const timestamp =
              typeof payload.timestamp === 'string'
                ? new Date(payload.timestamp)
                : payload.timestamp instanceof Date
                ? payload.timestamp
                : new Date();

            const chatMessage: TaskChatMessage = {
              id: payload.id || crypto.randomUUID(),
              taskId: payload.taskId || payload.task_id,
              role: payload.role || 'agent',
              message: payload.message || '',
              agentId: payload.agentId || payload.agent_id,
              agentName: payload.agentName || payload.agent_name,
              timestamp,
            };

            addTaskChatMessage(chatMessage);
            console.log(`[WebSocket] Task interaction: ${chatMessage.role} - ${chatMessage.message}`);
            break;
          }

          case 'agent_update': {
            const payload = message.payload;
            const isActive = payload.status === 'active' || payload.status === 'ACTIVE';
            const agent: Agent = {
              id: payload.id,
              name: payload.name,
              type: payload.type,
              thinkingMode: payload.thinkingMode || 'idle',
              currentTask: payload.currentTaskId || payload.currentTaskDescription || null,
              constraints: payload.constraints?.map((c: any) => c.description || c) || [],
              lastActivity: new Date(payload.lastActivity || payload.updatedAt || Date.now()),
              isActive,
            };
            addAgent(agent);
            console.log(`[WebSocket] Agent updated: ${agent.name} (${agent.id}), isActive: ${agent.isActive}`);
            break;
          }

          case 'system_notification': {
            const payload = message.payload;
            console.log(`[WebSocket] System notification: ${payload.message}`);
            // Could add toast notification here in the future
            break;
          }

          case 'agent_response': {
            const payload = message.payload;
            console.log(`[WebSocket] Agent response from ${payload.agentName}: ${payload.message}`);

            // Route to Agent Activity Log
            const agentLog: AgentLog = {
              id: crypto.randomUUID(),
              agentId: payload.agentId || 'unknown',
              agentName: payload.agentName,
              type: 'info',
              message: payload.message,
              timestamp: new Date(payload.timestamp || Date.now()),
            };
            addAgentLog(agentLog);
            break;
          }

          case 'task_events_response': {
            const payload = message.payload;
            const taskId = payload.taskId;
            const events = payload.events || [];
            console.log(`[WebSocket] Received ${events.length} task events for task ${taskId}`);

            // Process each event and add to agent logs
            for (const event of events) {
              if (event.type === 'agent_log' && event.payload) {
                const eventPayload = event.payload;
                const agentLog: AgentLog = {
                  id: eventPayload.id || crypto.randomUUID(),
                  agentId: eventPayload.agentId,
                  agentName: eventPayload.agentName,
                  type: eventPayload.type,
                  message: eventPayload.message,
                  details: eventPayload.details,
                  relatedTaskId: taskId,
                  timestamp: typeof eventPayload.timestamp === 'string'
                    ? new Date(eventPayload.timestamp)
                    : new Date(),
                };
                addAgentLog(agentLog);
              }
            }
            break;
          }

          default:
            console.log('[WebSocket] Unknown message type:', message.type);
        }
      } catch (error) {
        console.error('[WebSocket] Failed to parse message:', error);
      }
    },
    [addAgent, addTask, updateTask, addTicket, updateTicket, addApprovalRequest, addInteraction, updateInteraction, addTaskChatMessage, addAgentLog, addChatMessage]
  );

  // Connection handler
  const connect = useCallback(() => {
    const currentAttempts = useWebSocketStore.getState().reconnectAttempts;
    if (currentAttempts >= maxReconnectAttempts) {
      console.error('[WebSocket] Max reconnect attempts reached');
      return;
    }

    try {
      const ws = new WebSocket(url);

      ws.onopen = () => {
        console.log('[WebSocket] Connected');
        setConnected(true);
        setWebSocket(ws);
        resetReconnectAttempts();

        // Send cursor for event replay on reconnection
        if (lastEventTimestampRef.current) {
          console.log('[WebSocket] Sending cursor for event replay:', lastEventTimestampRef.current);
          ws.send(JSON.stringify({
            type: 'replay_events',
            payload: { since: lastEventTimestampRef.current }
          }));
        }

        // Clear reconnect timeout
        if (reconnectTimeoutRef.current) {
          clearTimeout(reconnectTimeoutRef.current);
          reconnectTimeoutRef.current = null;
        }
      };

      ws.onmessage = handleMessage;

      ws.onerror = (error) => {
        console.error('[WebSocket] Error:', error);
        setConnected(false);
      };

      ws.onclose = (event) => {
        console.log('[WebSocket] Connection closed', event.code, event.reason);
        setConnected(false);
        setWebSocket(null);

        // 컴포넌트 언마운트 시 재연결하지 않음 (reason이 'Component unmounting'인 경우)
        if (event.reason === 'Component unmounting') {
          console.log('[WebSocket] Normal closure, not reconnecting');
          return;
        }

        // 서버에서 종료된 경우나 연결이 끊어진 경우 재연결 시도
        console.log(`[WebSocket] Attempting to reconnect in ${reconnectInterval}ms...`);
        reconnectTimeoutRef.current = setTimeout(() => {
          incrementReconnectAttempts();
          connect();
        }, reconnectInterval);
      };
    } catch (error) {
      console.error('[WebSocket] Connection failed:', error);
      setConnected(false);

      // Schedule reconnect
      reconnectTimeoutRef.current = setTimeout(() => {
        incrementReconnectAttempts();
        connect();
      }, reconnectInterval);
    }
  }, [url, handleMessage, setConnected, setWebSocket, resetReconnectAttempts, incrementReconnectAttempts, maxReconnectAttempts, reconnectInterval]);

  // Initialize connection
  useEffect(() => {
    connect();

    // 브라우저가 온라인 상태로 돌아오면 재연결
    const handleOnline = () => {
      console.log('[WebSocket] Browser online - attempting to reconnect');
      const currentWs = useWebSocketStore.getState().ws;
      if (!currentWs || currentWs.readyState !== WebSocket.OPEN) {
        resetReconnectAttempts();
        connect();
      }
    };

    // 페이지가 다시 보이면 연결 상태 확인
    const handleVisibilityChange = () => {
      if (document.visibilityState === 'visible') {
        console.log('[WebSocket] Page visible - checking connection');
        const currentWs = useWebSocketStore.getState().ws;
        if (!currentWs || currentWs.readyState !== WebSocket.OPEN) {
          console.log('[WebSocket] Connection lost - reconnecting');
          resetReconnectAttempts();
          connect();
        }
      }
    };

    window.addEventListener('online', handleOnline);
    document.addEventListener('visibilitychange', handleVisibilityChange);

    // 주기적으로 연결 상태 확인 (30초마다)
    const heartbeatInterval = setInterval(() => {
      const currentWs = useWebSocketStore.getState().ws;
      if (!currentWs || currentWs.readyState !== WebSocket.OPEN) {
        console.log('[WebSocket] Heartbeat check - connection lost, reconnecting');
        resetReconnectAttempts();
        connect();
      }
    }, 30000);

    return () => {
      // Cleanup
      window.removeEventListener('online', handleOnline);
      document.removeEventListener('visibilitychange', handleVisibilityChange);
      clearInterval(heartbeatInterval);

      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
        reconnectTimeoutRef.current = null;
      }

      const currentWs = useWebSocketStore.getState().ws;
      if (currentWs && (currentWs.readyState === WebSocket.OPEN || currentWs.readyState === WebSocket.CONNECTING)) {
        currentWs.close(1000, 'Component unmounting');
      }
      setConnected(false);
      setWebSocket(null);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return {
    connect,
  };
}
