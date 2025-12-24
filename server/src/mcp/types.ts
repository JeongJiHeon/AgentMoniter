import { z } from 'zod';

// MCP 서비스 타입
export const MCPServiceTypeSchema = z.enum([
  'notion',
  'confluence',
  'gmail',
  'google-docs',
  'google-calendar',
  'slack',
  'jira',
  'github',
  'custom',
]);

export type MCPServiceType = z.infer<typeof MCPServiceTypeSchema>;

// MCP 작업 타입
export const MCPOperationTypeSchema = z.enum([
  // 읽기 작업 (승인 불필요)
  'read',
  'search',
  'list',

  // 쓰기 작업 (승인 필요)
  'create',
  'update',
  'delete',

  // 전송 작업 (승인 필수)
  'send',
  'publish',
  'share',
]);

export type MCPOperationType = z.infer<typeof MCPOperationTypeSchema>;

// MCP 작업 상태
export const MCPOperationStatusSchema = z.enum([
  'pending',          // 대기 중
  'pending_approval', // 승인 대기
  'approved',         // 승인됨
  'executing',        // 실행 중
  'completed',        // 완료
  'failed',           // 실패
  'cancelled',        // 취소됨
]);

export type MCPOperationStatus = z.infer<typeof MCPOperationStatusSchema>;

// MCP 작업 요청
export const MCPOperationRequestSchema = z.object({
  id: z.string().uuid(),
  agentId: z.string().uuid(),
  ticketId: z.string().uuid().optional(),

  // 서비스 정보
  service: MCPServiceTypeSchema,
  operation: MCPOperationTypeSchema,

  // 작업 상세
  target: z.object({
    type: z.string(),          // 예: 'page', 'email', 'document'
    id: z.string().optional(), // 기존 리소스 ID (update/delete 시)
    path: z.string().optional(), // 경로 (생성 위치 등)
  }),

  // 작업 데이터
  payload: z.record(z.unknown()),

  // 상태
  status: MCPOperationStatusSchema.default('pending'),

  // 승인 요구 여부
  requiresApproval: z.boolean(),
  approvalRequestId: z.string().uuid().optional(),

  // 결과
  result: z.object({
    success: z.boolean(),
    data: z.unknown().optional(),
    error: z.string().optional(),
    executedAt: z.date().optional(),
  }).optional(),

  // 메타데이터
  metadata: z.object({
    description: z.string(),
    estimatedImpact: z.string().optional(),
    rollbackPossible: z.boolean().default(false),
  }),

  // 타임스탬프
  createdAt: z.date(),
  updatedAt: z.date(),
});

export type MCPOperationRequest = z.infer<typeof MCPOperationRequestSchema>;

// MCP 서비스 설정
export interface MCPServiceConfig {
  type: MCPServiceType;
  name: string;
  enabled: boolean;
  credentials?: Record<string, string>;
  baseUrl?: string;
  options?: Record<string, unknown>;
}

// MCP 서비스 인터페이스
export interface IMCPService {
  readonly type: MCPServiceType;
  readonly name: string;

  // 연결 상태
  isConnected(): boolean;
  connect(): Promise<void>;
  disconnect(): Promise<void>;

  // 작업 실행
  execute(request: MCPOperationRequest): Promise<MCPOperationResult>;

  // 작업 검증
  validate(request: MCPOperationRequest): Promise<MCPValidationResult>;

  // 롤백 (가능한 경우)
  rollback(operationId: string): Promise<boolean>;
}

// MCP 작업 결과
export interface MCPOperationResult {
  success: boolean;
  data?: unknown;
  error?: string;
  metadata?: Record<string, unknown>;
}

// MCP 검증 결과
export interface MCPValidationResult {
  isValid: boolean;
  errors: string[];
  warnings: string[];
  requiresApproval: boolean;
  approvalReason?: string;
}

// MCP 이벤트
export type MCPEventType =
  | 'operation_started'
  | 'operation_completed'
  | 'operation_failed'
  | 'approval_required'
  | 'service_connected'
  | 'service_disconnected';

export interface MCPEvent {
  type: MCPEventType;
  service: MCPServiceType;
  operationId?: string;
  timestamp: Date;
  payload: unknown;
}

export type MCPEventHandler = (event: MCPEvent) => void | Promise<void>;
