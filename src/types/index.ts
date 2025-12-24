// Agent 사고 모드
export type ThinkingMode = 'idle' | 'exploring' | 'structuring' | 'validating' | 'summarizing';

// Agent 역할 (Orchestration vs Specialist)
export type AgentRole = 'orchestration' | 'specialist';

// Agent Log 타입 (사용자가 이해할 수 있는 로그만)
export type AgentLogType = 'info' | 'decision' | 'warning' | 'error' | 'a2a_call' | 'a2a_response';

// A2A (Agent-to-Agent) 호출
export interface A2ACall {
  id: string;
  fromAgentId: string;
  fromAgentName: string;
  toAgentId: string;
  toAgentName: string;
  purpose: string; // "Analyze documents", "Execute action"
  input: unknown;
  timestamp: Date;
}

// A2A 응답
export interface A2AResponse {
  id: string;
  callId: string;
  agentId: string;
  agentName: string;
  summary: string;
  artifacts?: Array<{ type: string; data: unknown }>;
  decisions?: string[];
  recommendation?: string;
  timestamp: Date;
}

// Agent Activity Log
export interface AgentLog {
  id: string;
  agentId: string;
  agentName: string;
  type: AgentLogType;
  message: string; // 사람이 읽을 수 있는 문장
  details?: string; // 선택적 세부 정보
  relatedTicketId?: string;
  relatedApprovalId?: string;
  relatedA2ACallId?: string; // A2A 호출 연결
  timestamp: Date;
}

// Agent 상태
export interface Agent {
  id: string;
  name: string;
  type: string;
  role?: AgentRole; // orchestration or specialist
  thinkingMode: ThinkingMode;
  currentTask: string | null;
  constraints: string[];
  lastActivity: Date;
  isActive: boolean;
  // Orchestration Agent 전용
  subAgents?: string[]; // Sub Agent IDs
  orchestratorId?: string; // 이 Agent를 호출한 Orchestrator
}

// 티켓 상태
export type TicketStatus = 'pending_approval' | 'approved' | 'in_progress' | 'completed' | 'rejected';

// 티켓 (작업 단위)
export interface Ticket {
  id: string;
  agentId: string;
  purpose: string;
  content: string;
  decisionRequired: string;
  options: TicketOption[];
  executionPlan: string;
  status: TicketStatus;
  priority: 'low' | 'medium' | 'high' | 'urgent';
  createdAt: Date;
  updatedAt: Date;
}

// 티켓 옵션
export interface TicketOption {
  id: string;
  label: string;
  description: string;
  isRecommended: boolean;
}

// 승인 요청
export interface ApprovalRequest {
  id: string;
  ticketId: string;
  agentId: string;
  type: 'proceed' | 'select_option' | 'prioritize';
  message: string;
  options?: TicketOption[];
  createdAt: Date;
}

// Interaction 타입 (Approval보다 유연한 양방향 상호작용)
export type InteractionType = 'clarify' | 'adjust' | 'guide';

// Interaction
export interface Interaction {
  id: string;
  taskId: string;
  agentId: string;
  agentName: string;
  type: InteractionType;
  question: string; // Agent가 묻는 질문 또는 제안
  options?: Array<{ id: string; label: string; description?: string }>; // clarify용
  userResponse?: string; // User의 응답
  status: 'pending' | 'responded' | 'cancelled';
  createdAt: Date;
  respondedAt?: Date;
}

// WebSocket 메시지 타입
export type WebSocketMessageType =
  | 'agent_update'
  | 'agent_log'
  | 'a2a_call'
  | 'a2a_response'
  | 'interaction_created'
  | 'interaction_responded'
  | 'ticket_created'
  | 'ticket_updated'
  | 'approval_request'
  | 'approval_resolved'
  | 'agent_question'
  | 'system_notification'
  | 'mcp_status_update'
  | 'settings_update'
  | 'task_created'
  | 'task_updated'
  | 'assign_task'
  | 'create_agent'
  | 'agent_response';

export interface WebSocketMessage {
  type: WebSocketMessageType;
  payload: unknown;
  timestamp: Date;
}

// ===== MCP 설정 =====

export type MCPServiceType =
  | 'notion'
  | 'slack'
  | 'confluence'
  | 'gmail'
  | 'google-docs'
  | 'google-calendar'
  | 'jira'
  | 'github'
  | 'custom';

export type MCPConnectionStatus = 'connected' | 'disconnected' | 'connecting' | 'error';

export interface MCPService {
  id: string;
  type: MCPServiceType;
  name: string;
  description: string;
  status: MCPConnectionStatus;
  enabled: boolean;
  config: MCPServiceConfig;
  lastConnected?: Date;
  errorMessage?: string;
}

export interface MCPServiceConfig {
  apiKey?: string;
  accessToken?: string;
  workspaceId?: string;
  baseUrl?: string;
  webhookUrl?: string;
  [key: string]: string | undefined;
}

// ===== LLM 설정 =====

export type LLMProvider = 'anthropic' | 'openai' | 'google' | 'azure' | 'local';

export interface LLMModel {
  id: string;
  provider: LLMProvider;
  name: string;
  description: string;
  maxTokens: number;
  isAvailable: boolean;
  isDefault: boolean;
}

export interface LLMConfig {
  provider: LLMProvider;
  model: string;
  apiKey?: string;
  baseUrl?: string;
  temperature: number;
  maxTokens: number;
}

// ===== 외부 API 설정 =====

export interface ExternalAPI {
  id: string;
  name: string;
  type: string;
  baseUrl: string;
  status: 'active' | 'inactive' | 'error';
  lastHealthCheck?: Date;
}

// ===== 전체 설정 =====

export interface AppSettings {
  mcpServices: MCPService[];
  llmConfig: LLMConfig;
  availableLLMs: LLMModel[];
  externalAPIs: ExternalAPI[];
}

// ===== 챗봇 =====

export type ChatMessageRole = 'user' | 'assistant' | 'system';

export interface ChatMessage {
  id: string;
  role: ChatMessageRole;
  content: string;
  timestamp: Date;
  isStreaming?: boolean;
}

export interface ChatSession {
  id: string;
  messages: ChatMessage[];
  createdAt: Date;
  title?: string;
}

// ===== 개인화 정보 =====

export interface PersonalizationItem {
  id: string;
  content: string;
  category: 'preference' | 'fact' | 'rule' | 'insight' | 'other';
  source: 'chat' | 'manual' | 'agent';
  createdAt: Date;
  updatedAt: Date;
}

// ===== 커스텀 Agent 설정 =====

export interface CustomAgentConfig {
  id: string;
  name: string;
  description: string;
  type: string;
  systemPrompt: string;
  constraints: string[];
  allowedMCPs: string[];
  isActive: boolean;
  createdAt: Date;
  updatedAt: Date;
}

// 대시보드 전체 상태
export interface DashboardState {
  agents: Agent[];
  tickets: Ticket[];
  approvalQueue: ApprovalRequest[];
  interactions: Interaction[];
  a2aCalls: A2ACall[];
  a2aResponses: A2AResponse[];
  isConnected: boolean;
  settings: AppSettings;
}

// Task 타입 재export
export type {
  Task,
  CreateTaskInput,
  TaskStatus,
  TaskPriority,
  TaskSource,
} from './task';
