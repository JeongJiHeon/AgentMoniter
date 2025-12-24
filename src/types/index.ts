// Agent 사고 모드
export type ThinkingMode = 'idle' | 'exploring' | 'structuring' | 'validating' | 'summarizing';

// Agent 상태
export interface Agent {
  id: string;
  name: string;
  type: string;
  thinkingMode: ThinkingMode;
  currentTask: string | null;
  constraints: string[];
  lastActivity: Date;
  isActive: boolean;
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

// WebSocket 메시지 타입
export type WebSocketMessageType =
  | 'agent_update'
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
