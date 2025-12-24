import { z } from 'zod';

// 티켓 상태
export const TicketStatusSchema = z.enum([
  'draft',              // 초안 - Agent가 작성 중
  'pending_approval',   // 승인 대기 - 사용자 결정 필요
  'approved',           // 승인됨 - 실행 가능
  'in_progress',        // 진행 중 - Agent가 실행 중
  'completed',          // 완료
  'rejected',           // 거부됨
  'blocked',            // 차단됨 - 추가 정보 필요
]);

export type TicketStatus = z.infer<typeof TicketStatusSchema>;

// 우선순위
export const PrioritySchema = z.enum(['low', 'medium', 'high', 'urgent']);
export type Priority = z.infer<typeof PrioritySchema>;

// 티켓 옵션 (사용자 선택지)
export const TicketOptionSchema = z.object({
  id: z.string().uuid(),
  label: z.string().min(1),
  description: z.string(),
  isRecommended: z.boolean().default(false),
  metadata: z.record(z.unknown()).optional(),
});

export type TicketOption = z.infer<typeof TicketOptionSchema>;

// 티켓 스키마 (작업 단위)
export const TicketSchema = z.object({
  id: z.string().uuid(),
  agentId: z.string(),

  // 작업 정의 (5W1H 기반)
  purpose: z.string().min(1),           // Why - 왜 이 작업이 필요한가
  content: z.string().min(1),           // What - 무엇을 할 것인가
  context: z.string().optional(),       // Where/When - 맥락 정보

  // 사용자 결정 요청
  decisionRequired: z.string().optional(),  // 필요한 결정 사항
  options: z.array(TicketOptionSchema).default([]),
  selectedOptionId: z.string().uuid().optional(),

  // 실행 계획
  executionPlan: z.string(),            // 승인 후 수행할 내용
  estimatedImpact: z.string().optional(), // 예상 영향도

  // 메타데이터
  status: TicketStatusSchema.default('draft'),
  priority: PrioritySchema.default('medium'),

  // 연관 정보
  parentTicketId: z.string().uuid().optional(),  // 상위 티켓 (분해된 경우)
  childTicketIds: z.array(z.string().uuid()).default([]),
  relatedTicketIds: z.array(z.string().uuid()).default([]),

  // 추적 정보
  source: z.object({
    type: z.enum(['email', 'document', 'chat', 'calendar', 'manual', 'system']),
    reference: z.string().optional(),
  }).optional(),

  // 제약조건 (온톨로지에서 적용된)
  appliedConstraints: z.array(z.string()).default([]),

  // 타임스탬프
  createdAt: z.date(),
  updatedAt: z.date(),
  approvedAt: z.date().optional(),
  completedAt: z.date().optional(),
});

export type Ticket = z.infer<typeof TicketSchema>;

// 티켓 생성 입력
export const CreateTicketInputSchema = TicketSchema.omit({
  id: true,
  createdAt: true,
  updatedAt: true,
  approvedAt: true,
  completedAt: true,
  status: true,
}).partial({
  childTicketIds: true,
  relatedTicketIds: true,
  appliedConstraints: true,
  options: true,
});

export type CreateTicketInput = z.infer<typeof CreateTicketInputSchema>;
