import { z } from 'zod';

// Agent 사고 모드
export const ThinkingModeSchema = z.enum([
  'idle',         // 대기 - 작업 없음
  'exploring',    // 탐색 - 정보 수집 중
  'structuring',  // 구조화 - 작업 분해/정리 중
  'validating',   // 검증 - 결과 확인 중
  'summarizing',  // 요약 - 결과 정리 중
]);

export type ThinkingMode = z.infer<typeof ThinkingModeSchema>;

// Agent 유형
export const AgentTypeSchema = z.enum([
  'document-processor',   // 문서 처리
  'email-handler',        // 이메일 처리
  'research-assistant',   // 리서치
  'schedule-manager',     // 일정 관리
  'task-coordinator',     // 작업 조율
  'custom',               // 커스텀
]);

export type AgentType = z.infer<typeof AgentTypeSchema>;

// Agent 상태
export const AgentStatusSchema = z.enum([
  'active',       // 활성 - 작업 수행 중
  'idle',         // 대기 - 작업 없음
  'paused',       // 일시정지 - 사용자 입력 대기
  'error',        // 오류 상태
  'disabled',     // 비활성화
]);

export type AgentStatus = z.infer<typeof AgentStatusSchema>;

// Agent 제약조건
export const AgentConstraintSchema = z.object({
  id: z.string().uuid(),
  type: z.enum([
    'action_forbidden',     // 금지된 행동
    'approval_required',    // 승인 필수
    'notify_required',      // 알림 필수
    'limit_scope',          // 범위 제한
    'time_restriction',     // 시간 제한
  ]),
  description: z.string(),
  condition: z.string().optional(),  // 조건식 (선택적)
  isActive: z.boolean().default(true),
  source: z.enum(['ontology', 'user', 'system']).default('system'),
});

export type AgentConstraint = z.infer<typeof AgentConstraintSchema>;

// Agent 스키마
export const AgentSchema = z.object({
  id: z.string().uuid(),
  name: z.string().min(1),
  type: AgentTypeSchema,
  description: z.string().optional(),

  // 상태 정보
  status: AgentStatusSchema.default('idle'),
  thinkingMode: ThinkingModeSchema.default('idle'),

  // 현재 작업
  currentTaskId: z.string().uuid().optional(),
  currentTaskDescription: z.string().optional(),

  // 제약조건
  constraints: z.array(AgentConstraintSchema).default([]),

  // 권한
  permissions: z.object({
    canCreateTickets: z.boolean().default(true),
    canExecuteApproved: z.boolean().default(true),
    canAccessMcp: z.array(z.string()).default([]),  // 접근 가능한 MCP 서비스
  }).default({}),

  // 통계
  stats: z.object({
    ticketsCreated: z.number().default(0),
    ticketsCompleted: z.number().default(0),
    ticketsRejected: z.number().default(0),
    averageApprovalTime: z.number().optional(),  // ms
  }).default({}),

  // 메타데이터
  lastActivity: z.date(),
  createdAt: z.date(),
  updatedAt: z.date(),
});

export type Agent = z.infer<typeof AgentSchema>;

// Agent 등록 입력
export const RegisterAgentInputSchema = AgentSchema.omit({
  id: true,
  status: true,
  thinkingMode: true,
  currentTaskId: true,
  currentTaskDescription: true,
  stats: true,
  lastActivity: true,
  createdAt: true,
  updatedAt: true,
}).partial({
  constraints: true,
  permissions: true,
});

export type RegisterAgentInput = z.infer<typeof RegisterAgentInputSchema>;

// Agent 상태 업데이트
export const AgentStateUpdateSchema = z.object({
  agentId: z.string().uuid(),
  status: AgentStatusSchema.optional(),
  thinkingMode: ThinkingModeSchema.optional(),
  currentTaskId: z.string().uuid().optional().nullable(),
  currentTaskDescription: z.string().optional().nullable(),
});

export type AgentStateUpdate = z.infer<typeof AgentStateUpdateSchema>;
