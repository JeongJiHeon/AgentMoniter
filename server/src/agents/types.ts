import type {
  Agent,
  AgentStateUpdate,
  Ticket,
  CreateTicketInput,
  ApprovalRequest,
  OntologyContext,
  ThinkingMode,
} from '../models/index.js';

// Agent 이벤트 타입
export type AgentEventType =
  | 'state_changed'
  | 'ticket_created'
  | 'ticket_updated'
  | 'approval_requested'
  | 'approval_received'
  | 'error'
  | 'warning'
  | 'log';

// Agent 이벤트
export interface AgentEvent {
  type: AgentEventType;
  agentId: string;
  timestamp: Date;
  payload: unknown;
}

// Agent 이벤트 핸들러
export type AgentEventHandler = (event: AgentEvent) => void | Promise<void>;

// Agent 실행 컨텍스트
export interface AgentExecutionContext {
  agentId: string;
  ontologyContext: OntologyContext;
  currentTicket?: Ticket;
  previousDecisions: Array<{
    ticketId: string;
    decision: string;
    timestamp: Date;
  }>;
}

// Agent 입력 (처리할 작업)
export interface AgentInput {
  type: 'email' | 'document' | 'message' | 'task' | 'event';
  content: string;
  metadata?: Record<string, unknown>;
  source?: {
    type: string;
    reference: string;
  };
}

// Agent 출력 (처리 결과)
export interface AgentOutput {
  tickets: CreateTicketInput[];
  approvalRequests: Array<Omit<ApprovalRequest, 'id' | 'createdAt' | 'updatedAt' | 'status'>>;
  logs: Array<{
    level: 'info' | 'warning' | 'error';
    message: string;
    timestamp: Date;
  }>;
}

// 사고 모드 전환 규칙
export interface ThinkingModeTransition {
  from: ThinkingMode;
  to: ThinkingMode;
  condition: string;
  action?: () => void | Promise<void>;
}

// Agent 인터페이스
export interface IAgent {
  readonly id: string;
  readonly name: string;
  readonly type: string;

  // 상태 조회
  getState(): Agent;
  getThinkingMode(): ThinkingMode;
  isActive(): boolean;

  // 라이프사이클
  initialize(context: AgentExecutionContext): Promise<void>;
  start(): Promise<void>;
  pause(): Promise<void>;
  resume(): Promise<void>;
  stop(): Promise<void>;

  // 작업 처리
  process(input: AgentInput): Promise<AgentOutput>;

  // 승인 처리
  onApprovalReceived(approval: ApprovalRequest): Promise<void>;

  // 상태 업데이트
  updateState(update: Partial<AgentStateUpdate>): Promise<void>;

  // 이벤트
  on(event: AgentEventType, handler: AgentEventHandler): void;
  off(event: AgentEventType, handler: AgentEventHandler): void;
  emit(event: AgentEvent): void;
}

// Agent 팩토리 인터페이스
export interface IAgentFactory {
  create(config: AgentConfig): IAgent;
  getAvailableTypes(): string[];
}

// Agent 설정
export interface AgentConfig {
  name: string;
  type: string;
  description?: string;
  permissions?: {
    canCreateTickets?: boolean;
    canExecuteApproved?: boolean;
    canAccessMcp?: string[];
  };
  constraints?: Array<{
    type: string;
    description: string;
    condition?: string;
  }>;
  customConfig?: Record<string, unknown>;
}
