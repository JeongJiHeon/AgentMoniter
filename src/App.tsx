import { useState, useMemo, useEffect, useRef, useCallback } from 'react';
import { OrchestrationService } from './services/orchestration';
import { DashboardLayout } from './components/layout/DashboardLayout';
import { AgentPanel } from './components/agents/AgentPanel';
import { TicketList } from './components/tickets/TicketList';
import { ApprovalQueue } from './components/approval/ApprovalQueue';
import { SettingsPanel } from './components/settings/SettingsPanel';
import { ChatPanel } from './components/chat/ChatPanel';
import { PersonalizationPanel } from './components/personalization/PersonalizationPanel';
import { CreateAgentModal } from './components/agents/CreateAgentModal';
import type {
  Agent,
  Ticket,
  ApprovalRequest,
  AppSettings,
  MCPService,
  LLMModel,
  PersonalizationItem,
  CustomAgentConfig,
  ThinkingMode,
  Task,
  CreateTaskInput,
  ChatMessage,
  AgentLog,
  Interaction,
  TaskChatMessage,
} from './types';
import { TaskPanel } from './components/tasks/TaskPanel';
import { saveToLocalStorage, loadFromLocalStorage } from './utils/localStorage';

type TabType = 'dashboard' | 'tasks' | 'personalization' | 'settings';

// 초기 MCP 서비스 (Notion, Slack, Confluence)
const initialMCPServices: MCPService[] = [
  {
    id: crypto.randomUUID(),
    type: 'notion',
    name: 'Notion',
    description: 'Notion 워크스페이스와 연동하여 페이지를 관리합니다',
    status: 'disconnected',
    enabled: true,
    config: {},
  },
  {
    id: crypto.randomUUID(),
    type: 'slack',
    name: 'Slack',
    description: 'Slack 워크스페이스와 연동하여 메시지를 관리합니다',
    status: 'disconnected',
    enabled: true,
    config: {},
  },
  {
    id: crypto.randomUUID(),
    type: 'confluence',
    name: 'Confluence',
    description: 'Confluence 페이지와 연동하여 문서를 관리합니다',
    status: 'disconnected',
    enabled: true,
    config: {},
  },
];

// 사용 가능한 LLM 목록
const initialLLMs: LLMModel[] = [
  {
    id: 'claude-3-5-sonnet',
    provider: 'anthropic',
    name: 'Claude 3.5 Sonnet',
    description: '빠른 속도와 높은 성능의 균형',
    maxTokens: 200000,
    isAvailable: true,
    isDefault: true,
  },
  {
    id: 'claude-3-opus',
    provider: 'anthropic',
    name: 'Claude 3 Opus',
    description: '가장 강력한 추론 능력',
    maxTokens: 200000,
    isAvailable: true,
    isDefault: false,
  },
  {
    id: 'claude-3-haiku',
    provider: 'anthropic',
    name: 'Claude 3 Haiku',
    description: '가장 빠른 응답 속도',
    maxTokens: 200000,
    isAvailable: true,
    isDefault: false,
  },
  {
    id: 'gpt-4o',
    provider: 'openai',
    name: 'GPT-4o',
    description: 'OpenAI의 최신 멀티모달 모델',
    maxTokens: 128000,
    isAvailable: true,
    isDefault: false,
  },
  {
    id: 'gpt-4-turbo',
    provider: 'openai',
    name: 'GPT-4 Turbo',
    description: '향상된 지시 따르기 능력',
    maxTokens: 128000,
    isAvailable: true,
    isDefault: false,
  },
  {
    id: 'gpt-3.5-turbo',
    provider: 'openai',
    name: 'GPT-3.5 Turbo',
    description: '빠르고 경제적인 모델',
    maxTokens: 16385,
    isAvailable: true,
    isDefault: false,
  },
  {
    id: 'gemini-1.5-pro',
    provider: 'google',
    name: 'Gemini 1.5 Pro',
    description: 'Google의 최신 대규모 컨텍스트 모델',
    maxTokens: 1000000,
    isAvailable: false,
    isDefault: false,
  },
];

// 초기 설정
const initialSettings: AppSettings = {
  mcpServices: initialMCPServices,
  llmConfig: {
    provider: 'anthropic',
    model: 'claude-3-5-sonnet',
    temperature: 0.7,
    maxTokens: 4096,
  },
  availableLLMs: initialLLMs,
  externalAPIs: [
    {
      id: 'api-1',
      name: 'Agent Monitor Server',
      type: 'WebSocket',
      baseUrl: 'ws://localhost:8080',
      status: 'inactive',
    },
  ],
};

function App() {
  const [activeTab, setActiveTab] = useState<TabType>('tasks');
  const [agents, setAgents] = useState<Agent[]>([]);
  const [tickets, setTickets] = useState<Ticket[]>(() => {
    const saved = loadFromLocalStorage<Ticket[]>('TICKETS');
    if (saved) {
      // Date 객체 복원
      return saved.map(t => ({
        ...t,
        createdAt: new Date(t.createdAt),
        updatedAt: new Date(t.updatedAt),
      }));
    }
    return [];
  });
  const [approvalQueue, setApprovalQueue] = useState<ApprovalRequest[]>(() => {
    const saved = loadFromLocalStorage<ApprovalRequest[]>('APPROVALS');
    if (saved) {
      // Date 객체 복원
      return saved.map(a => ({
        ...a,
        createdAt: new Date(a.createdAt),
      }));
    }
    return [];
  });
  const [settings, setSettings] = useState<AppSettings>(() => {
    const saved = loadFromLocalStorage<AppSettings>('SETTINGS');
    return saved || initialSettings;
  });
  const [selectedAgent, setSelectedAgent] = useState<Agent | null>(null);
  const [personalizationItems, setPersonalizationItems] = useState<PersonalizationItem[]>(() => {
    const saved = loadFromLocalStorage<PersonalizationItem[]>('PERSONALIZATION');
    return saved || [];
  });
  const [customAgents, setCustomAgents] = useState<CustomAgentConfig[]>(() => {
    const saved = loadFromLocalStorage<CustomAgentConfig[]>('CUSTOM_AGENTS');
    return saved || [];
  });
  const [isCreateAgentModalOpen, setIsCreateAgentModalOpen] = useState(false);
  const [agentLogs, setAgentLogs] = useState<AgentLog[]>([]);
  const [interactions, setInteractions] = useState<Interaction[]>([]);
  const [taskChatMessages, setTaskChatMessages] = useState<TaskChatMessage[]>([]);
  const [tasks, setTasks] = useState<Task[]>(() => {
    const saved = loadFromLocalStorage<Task[]>('TASKS');
    if (saved) {
      // Date 객체 복원
      return saved.map(t => ({
        ...t,
        createdAt: new Date(t.createdAt),
        updatedAt: new Date(t.updatedAt),
        completedAt: t.completedAt ? new Date(t.completedAt) : undefined,
      }));
    }
    return [];
  });
  const [autoAssignMode, setAutoAssignMode] = useState<'global' | 'manual'>(() => {
    const saved = loadFromLocalStorage<'global' | 'manual'>('AUTO_ASSIGN_MODE');
    return saved || 'manual';
  });
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([]);
  const orchestrationServiceRef = useRef<OrchestrationService | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const [wsConnected, setWsConnected] = useState(false);
  const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const processingTasksRef = useRef<Set<string>>(new Set()); // 현재 처리 중인 Task ID 추적

  // Orchestration Service 초기화
  useEffect(() => {
    orchestrationServiceRef.current = new OrchestrationService(settings.llmConfig);
  }, [settings.llmConfig]);

  // localStorage 저장 - settings
  useEffect(() => {
    saveToLocalStorage('SETTINGS', settings);
  }, [settings]);

  // localStorage 저장 - autoAssignMode
  useEffect(() => {
    saveToLocalStorage('AUTO_ASSIGN_MODE', autoAssignMode);
  }, [autoAssignMode]);

  // localStorage 저장 - customAgents
  useEffect(() => {
    saveToLocalStorage('CUSTOM_AGENTS', customAgents);
  }, [customAgents]);

  // localStorage 저장 - personalizationItems
  useEffect(() => {
    saveToLocalStorage('PERSONALIZATION', personalizationItems);
  }, [personalizationItems]);

  // WebSocket 메시지 핸들러 설정
  const setupWebSocketHandlers = useCallback((ws: WebSocket) => {
    ws.onmessage = (event) => {
      try {
        const message = JSON.parse(event.data);

        if (message.type === 'task_created') {
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
            autoAssign: payload.autoAssign !== undefined ? payload.autoAssign : undefined,
            createdAt: new Date(payload.createdAt),
            updatedAt: new Date(payload.updatedAt),
            completedAt: payload.completedAt ? new Date(payload.completedAt) : undefined,
          };
          setTasks(prev => {
            // 중복 체크
            if (prev.find(t => t.id === task.id)) {
              return prev;
            }
            return [...prev, task];
          });

          // 알림 표시
          console.log(`[WebSocket] Task created from ${task.source}: ${task.title}`);

          // 자동 할당은 별도 useEffect에서 처리
        } else if (message.type === 'task_updated') {
          const payload = message.payload;
          setTasks(prev =>
            prev.map(t =>
              t.id === payload.id
                ? {
                    ...t,
                    ...payload,
                    updatedAt: new Date(payload.updatedAt),
                    completedAt: payload.completedAt ? new Date(payload.completedAt) : undefined,
                  }
                : t
            )
          );
        } else if (message.type === 'ticket_created') {
          const payload = message.payload;
          // 옵션이 없는 티켓만 티켓 목록에 추가 (옵션이 있는 티켓은 승인 대기에서만 처리)
          if (!payload.options || payload.options.length === 0) {
            setTickets(prev => {
              // 중복 체크
              if (prev.find(t => t.id === payload.id)) {
                return prev;
              }
              return [...prev, payload];
            });
            console.log(`[WebSocket] Ticket created by agent ${payload.agentId}: ${payload.purpose}`);
          } else {
            console.log(`[WebSocket] Ticket with options created (will be shown in approval queue only): ${payload.purpose}`);
          }
        } else if (message.type === 'ticket_updated') {
          const payload = message.payload;
          setTickets(prev =>
            prev.map(t => (t.id === payload.id ? payload : t))
          );
        } else if (message.type === 'approval_request') {
          const payload = message.payload;
          // 옵션이 있는 승인 요청만 승인 대기에 추가
          if (payload.type === 'select_option' && payload.options && payload.options.length > 0) {
            setApprovalQueue(prev => {
              // 중복 체크
              if (prev.find(r => r.id === payload.id)) {
                return prev;
              }
              return [...prev, payload];
            });
            console.log(`[WebSocket] Approval request (with options) from agent ${payload.agentId}: ${payload.message}`);
          } else {
            // 옵션이 없는 승인 요청은 티켓 목록에서 처리되므로 승인 대기에 추가하지 않음
            console.log(`[WebSocket] Approval request (no options) - will be shown in ticket list only: ${payload.message}`);
          }
        } else if (message.type === 'agent_log') {
          const payload = message.payload as any;
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
          setAgentLogs(prev => [...prev, agentLog]);
          console.log(`[WebSocket] Agent log: ${agentLog.type} - ${agentLog.message} (${agentLog.agentName}) - Task: ${agentLog.relatedTaskId}`);
        } else if (message.type === 'interaction_created') {
          const payload = message.payload as Interaction;
          setInteractions(prev => [...prev, {
            ...payload,
            createdAt: new Date(payload.createdAt),
            respondedAt: payload.respondedAt ? new Date(payload.respondedAt) : undefined,
          }]);
          console.log(`[WebSocket] Interaction created: ${payload.question}`);
        } else if (message.type === 'interaction_responded') {
          const payload = message.payload as Interaction;
          setInteractions(prev =>
            prev.map(i => i.id === payload.id ? {
              ...payload,
              createdAt: new Date(payload.createdAt),
              respondedAt: payload.respondedAt ? new Date(payload.respondedAt) : undefined,
            } : i)
          );
          console.log(`[WebSocket] Interaction responded: ${payload.id}`);
        } else if (message.type === 'chat_message_response') {
          // Orchestration Agent의 Chat 응답
          const payload = message.payload as any;
          console.log(`[WebSocket] Received chat_message_response:`, payload);
          
          const chatMessage: ChatMessage = {
            id: payload.id || crypto.randomUUID(),
            role: payload.role || 'assistant',
            content: payload.content || '',
            timestamp: typeof payload.timestamp === 'string' ? new Date(payload.timestamp) : new Date(),
          };
          
          setChatMessages(prev => [...prev, chatMessage]);
          console.log(`[WebSocket] Chat message added: ${chatMessage.role} - ${chatMessage.content}`);
        } else if (message.type === 'task_interaction') {
          const payload = message.payload as any;
          console.log(`[WebSocket] Received task_interaction:`, payload);
          
          // timestamp가 문자열이면 Date로 변환, 이미 Date면 그대로 사용
          const timestamp = typeof payload.timestamp === 'string' 
            ? new Date(payload.timestamp) 
            : (payload.timestamp instanceof Date ? payload.timestamp : new Date());
          
          const chatMessage: TaskChatMessage = {
            id: payload.id || crypto.randomUUID(),
            taskId: payload.taskId || payload.task_id, // 서버에서 taskId 또는 task_id로 올 수 있음
            role: payload.role || 'agent',
            message: payload.message || '',
            agentId: payload.agentId || payload.agent_id,
            agentName: payload.agentName || payload.agent_name,
            timestamp: timestamp,
          };
          
          console.log(`[WebSocket] Parsed chat message:`, chatMessage);
          setTaskChatMessages(prev => {
            // 중복 메시지 방지 (같은 id가 있으면 업데이트, 없으면 추가)
            const existingIndex = prev.findIndex(msg => msg.id === chatMessage.id);
            if (existingIndex >= 0) {
              const updated = [...prev];
              updated[existingIndex] = chatMessage;
              return updated;
            }
            return [...prev, chatMessage];
          });
          console.log(`[WebSocket] Task interaction added: ${chatMessage.role} - ${chatMessage.message} (taskId: ${chatMessage.taskId})`);
        } else if (message.type === 'agent_update') {
          const payload = message.payload;
          // status를 isActive로 변환 (active면 true)
          const isActive = payload.status === 'active' || payload.status === 'ACTIVE';
          const agent: Agent = {
            id: payload.id,
            name: payload.name,
            type: payload.type,
            thinkingMode: payload.thinkingMode || 'idle',
            currentTask: payload.currentTaskId || payload.currentTaskDescription || null,
            constraints: payload.constraints?.map((c: any) => c.description || c) || [],
            lastActivity: new Date(payload.lastActivity || payload.updatedAt || Date.now()),
            isActive: isActive,
          };
          setAgents(prev => {
            // 기존 Agent 업데이트 또는 새로 추가
            const existingIndex = prev.findIndex(a => a.id === agent.id);
            if (existingIndex >= 0) {
              const updated = [...prev];
              updated[existingIndex] = agent;
              return updated;
            }
            return [...prev, agent];
          });
          console.log(`[WebSocket] Agent updated: ${agent.name} (${agent.id}), isActive: ${agent.isActive}`);
        } else if (message.type === 'system_notification') {
          const payload = message.payload;
          console.log(`[WebSocket] System notification: ${payload.message}`);
          // 필요시 알림 UI에 표시
        } else if (message.type === 'agent_response') {
          const payload = message.payload;
          console.log(`[WebSocket] Agent response from ${payload.agentName}: ${payload.message}`);

          // Route to Agent Activity Log instead of Chat
          // This keeps agent responses within Task context, not in Chat
          const agentLog: AgentLog = {
            id: crypto.randomUUID(),
            agentId: payload.agentId || 'unknown',
            agentName: payload.agentName,
            type: 'info', // Agent responses are informational logs
            message: payload.message,
            timestamp: new Date(payload.timestamp || Date.now()),
          };
          setAgentLogs(prev => [...prev, agentLog]);
          console.log(`[WebSocket] Agent response routed to Activity Log (not Chat)`);
        }
      } catch (error) {
        console.error('[WebSocket] Failed to parse message:', error);
      }
    };
  }, []);

  // WebSocket 연결 함수 (외부에서도 사용 가능하도록)
  const connectWebSocket = useCallback((): Promise<WebSocket | null> => {
    return new Promise((resolve) => {
      try {
        const ws = new WebSocket('ws://localhost:8080');
        wsRef.current = ws;

        ws.onopen = () => {
          console.log('[WebSocket] Connected');
          setWsConnected(true);
          // 재연결 타임아웃 클리어
          if (reconnectTimeoutRef.current) {
            clearTimeout(reconnectTimeoutRef.current);
            reconnectTimeoutRef.current = null;
          }
          // 메시지 핸들러 설정
          setupWebSocketHandlers(ws);
          resolve(ws);
        };
    
        ws.onerror = (error) => {
          console.error('[WebSocket] Error:', error);
          setWsConnected(false);
          resolve(null);
        };
        
        ws.onclose = (event) => {
          console.log('[WebSocket] Connection closed', event.code, event.reason);
          setWsConnected(false);
          
          // 정상 종료가 아닌 경우에만 재연결 시도
          if (event.code !== 1000) {
            console.log('[WebSocket] Attempting to reconnect in 3 seconds...');
            reconnectTimeoutRef.current = setTimeout(() => {
              if (!wsRef.current || wsRef.current.readyState === WebSocket.CLOSED) {
                console.log('[WebSocket] Reconnecting...');
                connectWebSocket();
              }
            }, 3000);
          }
        };
      } catch (error) {
        console.error('[WebSocket] Connection failed:', error);
        setWsConnected(false);
        // 재연결 시도
        reconnectTimeoutRef.current = setTimeout(() => {
          console.log('[WebSocket] Retrying connection...');
          connectWebSocket();
        }, 3000);
        resolve(null);
      }
    });
  }, [setupWebSocketHandlers]);

  // WebSocket 연결 및 Task 수신
  useEffect(() => {
    let ws: WebSocket | null = null;
    
    connectWebSocket().then((connectedWs) => {
      ws = connectedWs;
    });
    
    return () => {
      // 재연결 타임아웃 클리어
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
        reconnectTimeoutRef.current = null;
      }
      
      if (ws && (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING)) {
        ws.close(1000, 'Component unmounting');
      }
      if (wsRef.current && (wsRef.current.readyState === WebSocket.OPEN || wsRef.current.readyState === WebSocket.CONNECTING)) {
        wsRef.current.close(1000, 'Component unmounting');
      }
      wsRef.current = null;
      setWsConnected(false);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []); // WebSocket 연결은 한 번만 설정

  // customAgents를 Agent 타입으로 변환하여 병합
  // agents (백엔드에서 받은 Agent)와 customAgents (로컬 Agent)를 병합
  // 중복 제거: agents에 이미 있으면 customAgents는 제외
  const allAgents: Agent[] = useMemo(() => {
    const agentIds = new Set(agents.map(a => a.id));
    const customAgentsFiltered = customAgents
      .filter(ca => ca.isActive && !agentIds.has(ca.id)) // agents에 없는 것만 추가
      .map(ca => ({
        id: ca.id,
        name: ca.name,
        type: ca.type,
        thinkingMode: 'idle' as ThinkingMode,
        currentTask: null,
        constraints: ca.constraints || [],
        lastActivity: ca.updatedAt,
        isActive: ca.isActive,
      }));
    
    return [...agents, ...customAgentsFiltered];
  }, [agents, customAgents]);

  // Task 자동 할당 처리 (Task가 추가될 때마다 실행)
  useEffect(() => {
    const pendingTasks = tasks.filter(t => !t.assignedAgentId && t.status === 'pending');
    if (pendingTasks.length === 0 || !orchestrationServiceRef.current || allAgents.length === 0) return;

    pendingTasks.forEach(task => {
      // 🆕 이미 처리 중인 Task는 건너뛰기
      if (processingTasksRef.current.has(task.id)) {
        console.log(`[App] Task ${task.id} is already being processed, skipping...`);
        return;
      }
      
      // 자동 할당 조건:
      // 1. autoAssignMode가 'global'이고 autoAssign이 false가 아닌 경우
      // 2. autoAssignMode가 'manual'이고 autoAssign이 true인 경우
      // 3. autoAssign이 undefined이고 긴급/높은 우선순위이거나 Slack에서 온 경우 (기본 규칙)
      let shouldAutoAssign = false;
      
      if (autoAssignMode === 'global') {
        // 글로벌 자동 모드: autoAssign이 false가 아닌 모든 Task 자동 할당
        shouldAutoAssign = task.autoAssign !== false;
      } else {
        // 수동 모드: autoAssign이 true인 Task만 자동 할당
        // 또는 autoAssign이 undefined이고 기본 규칙에 해당하는 경우
        if (task.autoAssign === true) {
          shouldAutoAssign = true;
        } else if (task.autoAssign === undefined) {
          // 기본 규칙: 긴급/높은 우선순위이거나 Slack에서 온 경우
          shouldAutoAssign = orchestrationServiceRef.current ? orchestrationServiceRef.current.shouldAutoAssign(task) : false;
        }
      }
      
      if (shouldAutoAssign && orchestrationServiceRef.current) {
        // 중복 할당 방지: 이미 할당 중이거나 할당된 Task는 건너뛰기
        if (task.assignedAgentId) {
          return;
        }
        
        // 🆕 처리 시작 표시
        processingTasksRef.current.add(task.id);
        console.log(`[App] Starting to process task ${task.id}...`);
        
        // 🆕 멀티-에이전트 Planning
        orchestrationServiceRef.current.selectAgentsForTask(task, allAgents)
          .then(plan => {
            if (plan.agents.length > 0) {
              const primaryAgentId = plan.agents[0].agentId;
              
              // Task 상태 업데이트
              setTasks(prevTasks => {
                const existingTask = prevTasks.find(t => t.id === task.id);
                if (!existingTask || existingTask.assignedAgentId || existingTask.status !== 'pending') {
                  console.log(`[App] Task ${task.id} already processed or not pending, skipping state update`);
                  return prevTasks;
                }
                
                return prevTasks.map(t =>
                  t.id === task.id
                    ? { ...t, assignedAgentId: primaryAgentId, status: 'in_progress', updatedAt: new Date() }
                    : t
                );
              });
              
              // WebSocket 메시지 전송 - 멀티-에이전트 플랜 포함
              if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
                const message = {
                  type: 'assign_task',
                  payload: {
                    taskId: task.id,
                    agentId: primaryAgentId,
                    // 🆕 멀티-에이전트 플랜 정보
                    orchestrationPlan: {
                      agents: plan.agents,
                      needsUserInput: plan.needsUserInput,
                      inputPrompt: plan.inputPrompt,
                    },
                    task: {
                      id: task.id,
                      title: task.title,
                      description: task.description,
                      priority: task.priority,
                      source: task.source,
                      tags: task.tags,
                    }
                  },
                  timestamp: new Date().toISOString(),
                };
                wsRef.current.send(JSON.stringify(message));
                console.log(`[App] Auto-assigned with multi-agent plan:`, message);
              } else {
                console.warn(`[App] WebSocket not connected. Cannot send task assignment for task ${task.id}`);
              }
              
              console.log(`[Orchestration] Multi-agent plan for task ${task.id}:`, plan.agents.map(a => a.agentName));
            } else {
              console.warn(`[App] No agents selected for task ${task.id}`);
            }
          })
          .catch(error => {
            console.error('[Orchestration] Error in auto-assignment:', error);
          })
          .finally(() => {
            // 🆕 처리 완료 - ref에서 제거
            processingTasksRef.current.delete(task.id);
            console.log(`[App] Finished processing task ${task.id}`);
          });
      }
    });
  }, [tasks, allAgents, autoAssignMode]);

  const handleApprove = (ticketId: string) => {
    console.log(`[App] handleApprove called for ticket ${ticketId}`);
    
    // 먼저 approvalRequest를 찾기
    const approvalRequest = approvalQueue.find(r => r.ticketId === ticketId);
    
    if (!approvalRequest) {
      console.warn(`[App] Approval request not found for ticket ${ticketId}`);
      // approvalRequest가 없어도 티켓 상태는 업데이트
      setTickets(prev =>
        prev.map(t =>
          t.id === ticketId ? { ...t, status: 'approved' as const, updatedAt: new Date() } : t
        )
      );
      return;
    }
    
    // 티켓 상태 업데이트 (TicketList 반영)
    setTickets(prev =>
      prev.map(t =>
        t.id === ticketId ? { ...t, status: 'approved' as const, updatedAt: new Date() } : t
      )
    );
    
    // 승인 대기에서 제거 (ApprovalQueue 반영)
    setApprovalQueue(prev => prev.filter(r => r.ticketId !== ticketId));
    
    // Agent 상태를 활성으로 업데이트 (프론트엔드에서 즉시 반영)
    setAgents(prev =>
      prev.map(a =>
        a.id === approvalRequest.agentId
          ? { ...a, isActive: true, currentTask: ticketId }
          : a
      )
    );
    
    // 백엔드로 승인 메시지 전송
    const sendMessage = () => {
      const message = {
        type: 'approve_request',
        payload: {
          requestId: approvalRequest.id,
          ticketId: ticketId,
          agentId: approvalRequest.agentId,
          decision: 'approve',
        },
        timestamp: new Date().toISOString(),
      };
      
      if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
        wsRef.current.send(JSON.stringify(message));
        console.log(`[App] Sent approve_request message:`, message);
      } else {
        console.warn(`[App] WebSocket not connected. Attempting to reconnect...`);
        // WebSocket 재연결 시도
        if (!wsRef.current || wsRef.current.readyState === WebSocket.CLOSED || wsRef.current.readyState === WebSocket.CONNECTING) {
          // 재연결 시도
          try {
            const ws = new WebSocket('ws://localhost:8080');
            wsRef.current = ws;
            
            ws.onopen = () => {
              console.log('[App] WebSocket reconnected');
              setWsConnected(true);
              ws.send(JSON.stringify(message));
              console.log(`[App] Sent approve_request message after reconnect:`, message);
            };
            
            ws.onerror = () => {
              console.error('[App] WebSocket reconnection failed');
              alert('WebSocket 연결에 실패했습니다. 페이지를 새로고침하거나 서버가 실행 중인지 확인하세요.');
            };
            
            // 5초 타임아웃
            setTimeout(() => {
              if (ws.readyState !== WebSocket.OPEN) {
                alert('WebSocket 연결 시간이 초과되었습니다. 페이지를 새로고침하거나 서버가 실행 중인지 확인하세요.');
              }
            }, 5000);
          } catch (error) {
            console.error('[App] Failed to reconnect WebSocket:', error);
            alert('WebSocket 연결에 실패했습니다. 페이지를 새로고침하거나 서버가 실행 중인지 확인하세요.');
          }
        } else {
          alert('WebSocket이 연결되지 않았습니다. 잠시 후 다시 시도해주세요.');
        }
      }
    };
    
    sendMessage();
  };

  const handleReject = (ticketId: string) => {
    console.log(`[App] handleReject called for ticket ${ticketId}`);
    
    // 먼저 approvalRequest를 찾기
    const approvalRequest = approvalQueue.find(r => r.ticketId === ticketId);
    
    if (!approvalRequest) {
      console.warn(`[App] Approval request not found for ticket ${ticketId}`);
      // approvalRequest가 없어도 티켓 상태는 업데이트
      setTickets(prev =>
        prev.map(t =>
          t.id === ticketId ? { ...t, status: 'rejected' as const, updatedAt: new Date() } : t
        )
      );
      return;
    }
    
    // 티켓 상태 업데이트 (TicketList 반영)
    setTickets(prev =>
      prev.map(t =>
        t.id === ticketId ? { ...t, status: 'rejected' as const, updatedAt: new Date() } : t
      )
    );
    
    // 승인 대기에서 제거 (ApprovalQueue 반영)
    setApprovalQueue(prev => prev.filter(r => r.ticketId !== ticketId));
    
    // 백엔드로 거부 메시지 전송
    const sendMessage = () => {
      const message = {
        type: 'reject_request',
        payload: {
          requestId: approvalRequest.id,
          ticketId: ticketId,
          agentId: approvalRequest.agentId,
          decision: 'reject',
        },
        timestamp: new Date().toISOString(),
      };
      
      if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
        wsRef.current.send(JSON.stringify(message));
        console.log(`[App] Sent reject_request message:`, message);
      } else {
        console.warn(`[App] WebSocket not connected. Attempting to reconnect...`);
        // WebSocket 재연결 시도
        connectWebSocket().then((ws) => {
          if (ws && ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify(message));
            console.log(`[App] Sent reject_request message after reconnect:`, message);
          } else {
            alert('WebSocket 연결에 실패했습니다. 페이지를 새로고침하거나 서버가 실행 중인지 확인하세요.');
          }
        }).catch((error) => {
          console.error('[App] Failed to reconnect WebSocket:', error);
          alert('WebSocket 연결에 실패했습니다. 페이지를 새로고침하거나 서버가 실행 중인지 확인하세요.');
        });
      }
    };
    
    sendMessage();
  };

  const handleSelectOption = (ticketId: string, optionId: string) => {
    console.log(`[App] handleSelectOption called: ticketId=${ticketId}, optionId=${optionId}`);
    console.log(`[App] Current approvalQueue:`, approvalQueue.map(r => ({ id: r.id, ticketId: r.ticketId })));
    console.log(`[App] Current tickets:`, tickets.map(t => ({ id: t.id, agentId: t.agentId })));
    
    // 먼저 approvalRequest를 찾기
    let approvalRequest = approvalQueue.find(r => r.ticketId === ticketId);
    
    // approvalRequest를 찾지 못한 경우, ticket에서 직접 agentId를 가져오기
    if (!approvalRequest) {
      console.warn(`[App] Approval request not found for ticket ${ticketId}, trying to find from ticket...`);
      const ticket = tickets.find(t => t.id === ticketId);
      if (ticket && ticket.agentId) {
        // ticket에서 agentId를 찾았으면 임시 approvalRequest 생성
        approvalRequest = {
          id: `temp-${ticketId}`, // 임시 ID
          ticketId: ticketId,
          agentId: ticket.agentId,
          type: 'select_option',
          message: 'Option selected',
          createdAt: new Date(),
        };
        console.log(`[App] Created temporary approval request from ticket:`, approvalRequest);
      } else {
        console.error(`[App] Cannot find approval request or ticket for ticketId ${ticketId}`);
        alert(`티켓 ${ticketId}에 대한 승인 요청을 찾을 수 없습니다.`);
        return;
      }
    }
    
    console.log(`[App] Using approval request:`, approvalRequest);
    
    // 티켓 상태 업데이트 (TicketList 반영)
    setTickets(prev =>
      prev.map(t =>
        t.id === ticketId ? { ...t, status: 'approved' as const, updatedAt: new Date() } : t
      )
    );
    
    // 승인 대기에서 제거 (ApprovalQueue 반영)
    setApprovalQueue(prev => prev.filter(r => r.ticketId !== ticketId));
    
    // 옵션 선택 후 티켓 목록에 추가 (승인 대기에서 승인된 경우)
    // 옵션이 있는 티켓은 승인 대기에서만 표시되었으므로, 승인 후 티켓 목록에 추가
    const ticket = tickets.find(t => t.id === ticketId);
    if (!ticket && approvalRequest) {
      // 티켓이 없으면 생성 (옵션이 있는 티켓은 승인 대기에서만 표시되었으므로)
      const newTicket: Ticket = {
        id: ticketId,
        agentId: approvalRequest.agentId,
        purpose: approvalRequest.message,
        content: approvalRequest.context || '',
        decisionRequired: approvalRequest.message,
        options: approvalRequest.options || [],
        executionPlan: '',
        status: 'approved',
        priority: 'medium',
        createdAt: approvalRequest.createdAt,
        updatedAt: new Date(),
      };
      setTickets(prev => [...prev, newTicket]);
    }
    
    // Agent 상태를 활성으로 업데이트 (프론트엔드에서 즉시 반영)
    setAgents(prev =>
      prev.map(a =>
        a.id === approvalRequest.agentId
          ? { ...a, isActive: true, currentTask: ticketId }
          : a
      )
    );
    
    // 백엔드로 옵션 선택 메시지 전송
    const sendMessage = () => {
      const message = {
        type: 'select_option',
        payload: {
          requestId: approvalRequest.id,
          ticketId: ticketId,
          agentId: approvalRequest.agentId,
          optionId: optionId,
        },
        timestamp: new Date().toISOString(),
      };
      
      console.log(`[App] Preparing to send select_option message:`, message);
      
      if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
        wsRef.current.send(JSON.stringify(message));
        console.log(`[App] Sent select_option message:`, message);
      } else {
        console.warn(`[App] WebSocket not connected. Current state:`, wsRef.current?.readyState);
        console.warn(`[App] Attempting to reconnect...`);
        // WebSocket 재연결 시도
        connectWebSocket().then((ws) => {
          if (ws && ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify(message));
            console.log(`[App] Sent select_option message after reconnect:`, message);
          } else {
            console.error(`[App] WebSocket reconnection failed. State:`, ws?.readyState);
            alert('WebSocket 연결에 실패했습니다. 페이지를 새로고침하거나 서버가 실행 중인지 확인하세요.');
          }
        }).catch((error) => {
          console.error('[App] Failed to reconnect WebSocket:', error);
          alert('WebSocket 연결에 실패했습니다. 페이지를 새로고침하거나 서버가 실행 중인지 확인하세요.');
        });
      }
    };
    
    sendMessage();
  };

  const handleApprovalRespond = (requestId: string, response: string) => {
    console.log(`[App] handleApprovalRespond called: requestId=${requestId}, response=${response}`);
    const request = approvalQueue.find(r => r.id === requestId);
    if (!request) {
      console.warn(`[App] Approval request not found: ${requestId}`);
      console.log(`[App] Available requests:`, approvalQueue.map(r => ({ id: r.id, ticketId: r.ticketId })));
      return;
    }

    console.log(`[App] Found approval request:`, { id: request.id, ticketId: request.ticketId, agentId: request.agentId });

    if (response === 'approve') {
      handleApprove(request.ticketId);
    } else if (response === 'reject') {
      handleReject(request.ticketId);
    } else {
      handleSelectOption(request.ticketId, response);
    }
  };

  const handleUpdateSettings = (updates: Partial<AppSettings>) => {
    setSettings(prev => ({ ...prev, ...updates }));
  };

  // Personalization handlers
  const handleAddPersonalizationItem = (
    item: Omit<PersonalizationItem, 'id' | 'createdAt' | 'updatedAt'>
  ) => {
    const newItem: PersonalizationItem = {
      ...item,
      id: crypto.randomUUID(),
      createdAt: new Date(),
      updatedAt: new Date(),
    };
    setPersonalizationItems(prev => [...prev, newItem]);
  };

  const handleUpdatePersonalizationItem = (id: string, content: string) => {
    setPersonalizationItems(prev =>
      prev.map(item =>
        item.id === id ? { ...item, content, updatedAt: new Date() } : item
      )
    );
  };

  const handleDeletePersonalizationItem = (id: string) => {
    setPersonalizationItems(prev => prev.filter(item => item.id !== id));
  };

  const handleSaveInsightFromChat = (content: string) => {
    handleAddPersonalizationItem({
      content,
      category: 'insight',
      source: 'chat',
    });
  };

  const handleAutoSavePersonalization = (
    items: Omit<PersonalizationItem, 'id' | 'createdAt' | 'updatedAt' | 'source'>[]
  ) => {
    items.forEach(item => {
      handleAddPersonalizationItem({
        ...item,
        source: 'chat',
      });
    });
  };

  // Custom agent handlers
  const handleCreateAgent = (
    config: Omit<CustomAgentConfig, 'id' | 'createdAt' | 'updatedAt'>
  ) => {
    const newAgent: CustomAgentConfig = {
      ...config,
      id: crypto.randomUUID(),
      createdAt: new Date(),
      updatedAt: new Date(),
    };
    
    // 로컬 상태에 추가
    setCustomAgents(prev => [...prev, newAgent]);
    
    // 백엔드로 Agent 생성 요청 전송
    console.log(`[App] Creating agent: ${newAgent.name} (${newAgent.id})`);
    console.log(`[App] WebSocket state: ${wsRef.current ? wsRef.current.readyState : 'null'} (OPEN=1)`);
    
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      const message = {
        type: 'create_agent',
        payload: {
          id: newAgent.id,
          name: newAgent.name,
          type: newAgent.type,
          description: newAgent.description,
          constraints: newAgent.constraints || [],
          permissions: newAgent.permissions || {},
          customConfig: newAgent.customConfig || {},
        },
        timestamp: new Date().toISOString(),
      };
      wsRef.current.send(JSON.stringify(message));
      console.log(`[App] Sent create_agent message:`, message);
    } else {
      console.error(`[App] WebSocket not connected. Cannot send create_agent message`);
      console.error(`[App] wsRef.current: ${wsRef.current}`);
      console.error(`[App] readyState: ${wsRef.current ? wsRef.current.readyState : 'N/A'}`);
      
      // WebSocket 재연결 시도
      if (!wsRef.current || wsRef.current.readyState === WebSocket.CLOSED) {
        console.log('[App] Attempting to reconnect WebSocket...');
        const ws = new WebSocket('ws://localhost:8080');
        wsRef.current = ws;
        
        ws.onopen = () => {
          console.log('[App] WebSocket reconnected');
          setWsConnected(true);
          // 재연결 후 메시지 재전송
          const message = {
            type: 'create_agent',
            payload: {
              id: newAgent.id,
              name: newAgent.name,
              type: newAgent.type,
              description: newAgent.description,
              constraints: newAgent.constraints || [],
              permissions: newAgent.permissions || {},
              customConfig: newAgent.customConfig || {},
            },
            timestamp: new Date().toISOString(),
          };
          ws.send(JSON.stringify(message));
          console.log(`[App] Sent create_agent message after reconnect:`, message);
        };
        
        ws.onerror = () => {
          console.error('[App] WebSocket reconnection failed');
          // 사용자에게 알림 (한 번만)
          if (!wsConnected) {
            alert('WebSocket이 연결되지 않았습니다. 서버가 실행 중인지 확인하세요.\n\n서버 시작 방법:\n1. cd agent-monitor_v2/server_python\n2. python main.py');
          }
        };
      } else {
        // 연결 중이거나 다른 상태인 경우 잠시 후 재시도
        setTimeout(() => {
          if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
            const message = {
              type: 'create_agent',
              payload: {
                id: newAgent.id,
                name: newAgent.name,
                type: newAgent.type,
                description: newAgent.description,
                constraints: newAgent.constraints || [],
                permissions: newAgent.permissions || {},
                customConfig: newAgent.customConfig || {},
              },
              timestamp: new Date().toISOString(),
            };
            wsRef.current.send(JSON.stringify(message));
            console.log(`[App] Sent create_agent message after wait:`, message);
          }
        }, 1000);
      }
    }
  };

  const handleUpdateAgent = (id: string, updates: Partial<CustomAgentConfig>) => {
    setCustomAgents(prev =>
      prev.map(agent =>
        agent.id === id ? { ...agent, ...updates, updatedAt: new Date() } : agent
      )
    );
  };

  const handleDeleteAgent = (id: string) => {
    setCustomAgents(prev => prev.filter(agent => agent.id !== id));
  };

  // Task handlers
  const handleCreateTask = (input: CreateTaskInput) => {
    const newTask: Task = {
      id: crypto.randomUUID(),
      title: input.title,
      description: input.description,
      status: 'pending',
      priority: input.priority || 'medium',
      source: input.source || 'manual',
      sourceReference: input.sourceReference,
      tags: input.tags || [],
      dueDate: input.dueDate,
      createdAt: new Date(),
      updatedAt: new Date(),
    };
    
    setTasks(prev => {
      const updatedTasks = [...prev, newTask];
      
      // 자동 할당 시도 (높은 우선순위이거나 Slack에서 온 경우)
      if (orchestrationServiceRef.current) {
        const shouldAutoAssign = orchestrationServiceRef.current.shouldAutoAssign(newTask);
        if (shouldAutoAssign && allAgents.length > 0) {
          orchestrationServiceRef.current.selectAgentForTask(newTask, allAgents)
            .then(agentId => {
              if (agentId) {
                handleAssignAgent(newTask.id, agentId);
                console.log(`[Orchestration] Auto-assigned task ${newTask.id} to agent ${agentId}`);
              }
            })
            .catch(error => {
              console.error('[Orchestration] Error in auto-assignment:', error);
            });
        }
      }
      
      return updatedTasks;
    });
  };

  const handleUpdateTask = (id: string, updates: Partial<Task>) => {
    setTasks(prev =>
      prev.map(task =>
        task.id === id ? { ...task, ...updates, updatedAt: new Date() } : task
      )
    );
  };

  const handleDeleteTask = (id: string) => {
    setTasks(prev => prev.filter(task => task.id !== id));
  };

  const handleAssignAgent = useCallback((taskId: string, agentId: string) => {
    const task = tasks.find(t => t.id === taskId);
    if (!task) {
      console.error(`[App] Task ${taskId} not found`);
      return;
    }

    // Task에 Agent 할당 및 상태 업데이트
    setTasks(prev =>
      prev.map(t =>
        t.id === taskId
          ? { ...t, assignedAgentId: agentId, status: 'in_progress', updatedAt: new Date() }
          : t
      )
    );

    // WebSocket으로 백엔드에 Agent 할당 및 Task 시작 요청 전송
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      const message = {
        type: 'assign_task',
        payload: {
          taskId,
          agentId,
          task: {
            id: task.id,
            title: task.title,
            description: task.description,
            priority: task.priority,
            source: task.source,
            tags: task.tags,
          }
        },
        timestamp: new Date().toISOString(),
      };

      wsRef.current.send(JSON.stringify(message));
      console.log(`[App] Sent assign_task message to backend:`, message);
    } else {
      console.warn(`[App] WebSocket not connected. Cannot send task assignment for task ${taskId}`);
    }
  }, [tasks]);

  const handleRespondInteraction = useCallback((interactionId: string, response: string) => {
    // Update local state
    setInteractions(prev =>
      prev.map(i =>
        i.id === interactionId
          ? { ...i, userResponse: response, status: 'responded', respondedAt: new Date() }
          : i
      )
    );

    // Send to backend via WebSocket
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      const message = {
        type: 'respond_interaction',
        payload: {
          interactionId,
          response,
        },
        timestamp: new Date().toISOString(),
      };

      wsRef.current.send(JSON.stringify(message));
      console.log(`[App] Sent respond_interaction message to backend:`, message);
    } else {
      console.warn(`[App] WebSocket not connected. Cannot respond to interaction ${interactionId}`);
    }
  }, []);

  const handleSendTaskMessage = useCallback((taskId: string, message: string) => {
    // Create user message locally first for immediate UI feedback
    const userMessage: TaskChatMessage = {
      id: crypto.randomUUID(),
      taskId,
      role: 'user',
      message,
      timestamp: new Date(),
    };

    setTaskChatMessages(prev => [...prev, userMessage]);

    // Send to backend via WebSocket
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      const wsMessage = {
        type: 'task_interaction',
        payload: {
          taskId,
          role: 'user',
          message,
        },
        timestamp: new Date().toISOString(),
      };

      wsRef.current.send(JSON.stringify(wsMessage));
      console.log(`[App] Sent task_interaction message to backend:`, wsMessage);
    } else {
      console.warn(`[App] WebSocket not connected. Cannot send task message for task ${taskId}`);
    }
  }, []);

  // Chat Panel용 Orchestration Agent 메시지 전송
  const handleSendChatMessage = useCallback((message: string) => {
    console.log(`[App] Sending chat message to Orchestration Agent: ${message}`);
    
    // WebSocket을 통해 Orchestration Agent에게 메시지 전송
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      const wsMessage = {
        type: 'chat_message',
        payload: {
          message,
          timestamp: new Date().toISOString(),
        },
        timestamp: new Date().toISOString(),
      };

      wsRef.current.send(JSON.stringify(wsMessage));
      console.log(`[App] Sent chat_message to backend:`, wsMessage);
    } else {
      console.warn(`[App] WebSocket not connected. Cannot send chat message`);
      // WebSocket 연결이 안 된 경우 에러 메시지 표시
      setChatMessages(prev => [...prev, {
        id: crypto.randomUUID(),
        role: 'assistant',
        content: '서버에 연결되지 않았습니다. 잠시 후 다시 시도해주세요.',
        timestamp: new Date(),
      }]);
    }
  }, []);

  return (
    <DashboardLayout 
      activeTab={activeTab} 
      onTabChange={setActiveTab}
      rightPanel={
        <ChatPanel
          llmConfig={settings.llmConfig}
          agentCount={allAgents.length}
          mcpCount={settings.mcpServices.filter(s => s.status === 'connected').length}
          personalizationCount={personalizationItems.length}
          onSaveInsight={handleSaveInsightFromChat}
          onAutoSavePersonalization={handleAutoSavePersonalization}
          externalMessages={chatMessages}
          onMessagesRead={() => setChatMessages([])}
          onSendMessage={handleSendChatMessage}
          useOrchestration={true}
        />
      }
    >
      {activeTab === 'dashboard' && (
        <div className="grid grid-cols-12 gap-6">
          {/* Left Column - Agent Panel */}
          <div className="col-span-3">
            <AgentPanel
              agents={allAgents}
              onAgentSelect={setSelectedAgent}
            />
            {/* Create Agent Button */}
            <button
              onClick={() => setIsCreateAgentModalOpen(true)}
              className="w-full mt-4 px-4 py-3 bg-blue-600 hover:bg-blue-500 text-white rounded-xl flex items-center justify-center gap-2 transition-colors"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
              </svg>
              새 Agent 생성
            </button>
          </div>

          {/* Center Column - Ticket List */}
          <div className="col-span-5">
            <TicketList
              tickets={selectedAgent
                ? tickets.filter(t => t.agentId === selectedAgent.id)
                : tickets
              }
              onApprove={handleApprove}
              onReject={handleReject}
              onSelectOption={handleSelectOption}
            />
          </div>

          {/* Right Column - Approval Queue */}
          <div className="col-span-4">
            <ApprovalQueue
              requests={approvalQueue}
              onRespond={handleApprovalRespond}
            />

            {/* Selected Agent Detail */}
            {selectedAgent && (
              <div className="mt-6 bg-slate-800/50 rounded-xl p-4 border border-slate-700">
                <div className="flex items-center justify-between mb-4">
                  <h2 className="text-lg font-semibold text-white">Agent 상세</h2>
                  <button
                    onClick={() => setSelectedAgent(null)}
                    className="text-slate-400 hover:text-white"
                  >
                    닫기
                  </button>
                </div>
                <div className="space-y-3">
                  <div>
                    <p className="text-xs text-slate-500">이름</p>
                    <p className="text-white">{selectedAgent.name}</p>
                  </div>
                  <div>
                    <p className="text-xs text-slate-500">유형</p>
                    <p className="text-slate-300">{selectedAgent.type}</p>
                  </div>
                  <div>
                    <p className="text-xs text-slate-500">현재 모드</p>
                    <p className="text-slate-300">{selectedAgent.thinkingMode}</p>
                  </div>
                  {selectedAgent.currentTask && (
                    <div>
                      <p className="text-xs text-slate-500">현재 작업</p>
                      <p className="text-slate-300">{selectedAgent.currentTask}</p>
                    </div>
                  )}
                  {selectedAgent.constraints.length > 0 && (
                    <div>
                      <p className="text-xs text-slate-500 mb-2">제약조건</p>
                      <div className="space-y-1">
                        {selectedAgent.constraints.map((c, i) => (
                          <div key={i} className="px-2 py-1 bg-red-500/10 border border-red-500/30 rounded text-sm text-red-400">
                            {c}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {activeTab === 'tasks' && (
        <div className="max-w-7xl mx-auto">
          <TaskPanel
            tasks={tasks}
            agents={allAgents}
            tickets={tickets}
            approvalRequests={approvalQueue}
            agentLogs={agentLogs}
            interactions={interactions}
            taskChatMessages={taskChatMessages}
            onCreateTask={handleCreateTask}
            onUpdateTask={handleUpdateTask}
            onDeleteTask={handleDeleteTask}
            onAssignAgent={handleAssignAgent}
            onRespondInteraction={handleRespondInteraction}
            onSendTaskMessage={handleSendTaskMessage}
            availableMCPs={settings.mcpServices}
            llmConfig={settings.llmConfig}
            autoAssignMode={autoAssignMode}
            onAutoAssignModeChange={setAutoAssignMode}
          />
        </div>
      )}

      {activeTab === 'personalization' && (
        <PersonalizationPanel
          items={personalizationItems}
          onAddItem={handleAddPersonalizationItem}
          onUpdateItem={handleUpdatePersonalizationItem}
          onDeleteItem={handleDeletePersonalizationItem}
        />
      )}

      {activeTab === 'settings' && (
        <SettingsPanel
          settings={settings}
          customAgents={customAgents}
          onUpdateSettings={handleUpdateSettings}
          onUpdateAgent={handleUpdateAgent}
          onDeleteAgent={handleDeleteAgent}
        />
      )}

      {/* Create Agent Modal */}
      <CreateAgentModal
        isOpen={isCreateAgentModalOpen}
        onClose={() => setIsCreateAgentModalOpen(false)}
        onCreateAgent={handleCreateAgent}
        availableMCPs={settings.mcpServices}
        llmConfig={settings.llmConfig}
      />
    </DashboardLayout>
  );
}

export default App;
