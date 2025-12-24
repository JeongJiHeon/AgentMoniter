import { z } from 'zod';
import { TicketOptionSchema } from './ticket.js';

// 승인 요청 유형
export const ApprovalRequestTypeSchema = z.enum([
  'proceed',          // 진행 여부 확인
  'select_option',    // 옵션 선택
  'prioritize',       // 우선순위 결정
  'provide_input',    // 추가 정보 입력
  'confirm_action',   // 행동 확인
  'review_result',    // 결과 검토
]);

export type ApprovalRequestType = z.infer<typeof ApprovalRequestTypeSchema>;

// 승인 요청 상태
export const ApprovalStatusSchema = z.enum([
  'pending',          // 대기 중
  'approved',         // 승인됨
  'rejected',         // 거부됨
  'expired',          // 만료됨
  'cancelled',        // 취소됨
]);

export type ApprovalStatus = z.infer<typeof ApprovalStatusSchema>;

// 승인 요청 스키마
export const ApprovalRequestSchema = z.object({
  id: z.string().uuid(),
  ticketId: z.string().uuid(),
  agentId: z.string().uuid(),

  // 요청 정보
  type: ApprovalRequestTypeSchema,
  message: z.string(),                    // Agent가 사용자에게 전달하는 메시지
  context: z.string().optional(),         // 추가 맥락 정보

  // 선택지 (select_option, prioritize 등에서 사용)
  options: z.array(TicketOptionSchema).optional(),

  // 필요한 입력 (provide_input에서 사용)
  requiredInputs: z.array(z.object({
    key: z.string(),
    label: z.string(),
    type: z.enum(['text', 'number', 'date', 'select', 'multiselect']),
    required: z.boolean().default(true),
    options: z.array(z.string()).optional(),
  })).optional(),

  // 상태
  status: ApprovalStatusSchema.default('pending'),

  // 응답 (승인/거부 시)
  response: z.object({
    decision: z.enum(['approve', 'reject', 'select', 'input']).optional(),
    selectedOptionId: z.string().uuid().optional(),
    inputValues: z.record(z.unknown()).optional(),
    comment: z.string().optional(),
    respondedAt: z.date().optional(),
  }).optional(),

  // 만료 설정
  expiresAt: z.date().optional(),

  // 우선순위 (UI 정렬용)
  priority: z.number().default(0),

  // 타임스탬프
  createdAt: z.date(),
  updatedAt: z.date(),
});

export type ApprovalRequest = z.infer<typeof ApprovalRequestSchema>;

// 승인 응답 입력
export const ApprovalResponseInputSchema = z.object({
  requestId: z.string().uuid(),
  decision: z.enum(['approve', 'reject', 'select', 'input']),
  selectedOptionId: z.string().uuid().optional(),
  inputValues: z.record(z.unknown()).optional(),
  comment: z.string().optional(),
});

export type ApprovalResponseInput = z.infer<typeof ApprovalResponseInputSchema>;

// 승인 요청 생성 입력
export const CreateApprovalRequestInputSchema = ApprovalRequestSchema.omit({
  id: true,
  status: true,
  response: true,
  createdAt: true,
  updatedAt: true,
}).partial({
  priority: true,
  expiresAt: true,
});

export type CreateApprovalRequestInput = z.infer<typeof CreateApprovalRequestInputSchema>;
