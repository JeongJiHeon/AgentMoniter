import { z } from 'zod';

// 사고 선호도 (Thinking Preference)
export const ThinkingPreferenceSchema = z.object({
  id: z.string().uuid(),
  category: z.enum([
    'decision_style',      // 의사결정 스타일
    'communication',       // 커뮤니케이션 방식
    'priority_rule',       // 우선순위 규칙
    'time_preference',     // 시간 선호도
    'risk_tolerance',      // 위험 허용도
  ]),
  name: z.string(),
  description: z.string(),
  value: z.unknown(),  // 카테고리에 따라 다른 타입
  weight: z.number().min(0).max(1).default(1),  // 중요도 (0~1)
});

export type ThinkingPreference = z.infer<typeof ThinkingPreferenceSchema>;

// 금기 사항 (Taboo)
export const TabooSchema = z.object({
  id: z.string().uuid(),
  type: z.enum([
    'action',           // 행동 금지
    'timing',           // 시간 금지
    'target',           // 대상 금지
    'content',          // 내용 금지
    'method',           // 방법 금지
  ]),
  description: z.string(),
  condition: z.string().optional(),    // 조건식
  severity: z.enum(['warning', 'block', 'critical']).default('block'),
  exceptions: z.array(z.string()).default([]),  // 예외 상황
});

export type Taboo = z.infer<typeof TabooSchema>;

// 실패 패턴 (Failure Pattern)
export const FailurePatternSchema = z.object({
  id: z.string().uuid(),
  name: z.string(),
  description: z.string(),
  triggers: z.array(z.string()),           // 이 패턴을 유발하는 상황
  symptoms: z.array(z.string()),           // 증상/징후
  preventiveMeasures: z.array(z.string()), // 예방 조치
  isActive: z.boolean().default(true),
});

export type FailurePattern = z.infer<typeof FailurePatternSchema>;

// 승인 규칙 (Approval Rule)
export const ApprovalRuleSchema = z.object({
  id: z.string().uuid(),
  name: z.string(),
  description: z.string(),
  condition: z.object({
    type: z.enum([
      'always',           // 항상 승인 필요
      'threshold',        // 임계값 초과 시
      'category',         // 특정 카테고리
      'agent_type',       // 특정 Agent 유형
      'time_based',       // 시간 기반
      'custom',           // 커스텀 조건
    ]),
    value: z.unknown(),
  }),
  approvalType: z.enum([
    'explicit',           // 명시적 승인 필요
    'implicit_timeout',   // 타임아웃 후 자동 승인
    'notify_only',        // 알림만 (승인 불필요)
  ]).default('explicit'),
  timeoutMinutes: z.number().optional(),  // implicit_timeout인 경우
  priority: z.number().default(0),        // 규칙 우선순위
});

export type ApprovalRule = z.infer<typeof ApprovalRuleSchema>;

// 작업 템플릿 (Task Template)
export const TaskTemplateSchema = z.object({
  id: z.string().uuid(),
  name: z.string(),
  description: z.string(),
  triggerKeywords: z.array(z.string()),   // 이 템플릿을 활성화하는 키워드
  defaultPriority: z.enum(['low', 'medium', 'high', 'urgent']).default('medium'),
  requiredFields: z.array(z.string()),    // 필수 입력 필드
  defaultConstraints: z.array(z.string()), // 기본 적용 제약조건
  suggestedAgentType: z.string().optional(),
});

export type TaskTemplate = z.infer<typeof TaskTemplateSchema>;

// 사용자 온톨로지 (User Ontology) - 전체 사고 규칙 집합
export const UserOntologySchema = z.object({
  id: z.string().uuid(),
  userId: z.string(),
  version: z.number().default(1),

  // 사고 선호도
  preferences: z.array(ThinkingPreferenceSchema).default([]),

  // 금기 사항
  taboos: z.array(TabooSchema).default([]),

  // 실패 패턴
  failurePatterns: z.array(FailurePatternSchema).default([]),

  // 승인 규칙
  approvalRules: z.array(ApprovalRuleSchema).default([]),

  // 작업 템플릿
  taskTemplates: z.array(TaskTemplateSchema).default([]),

  // 전역 제약조건
  globalConstraints: z.array(z.object({
    id: z.string().uuid(),
    description: z.string(),
    isActive: z.boolean().default(true),
  })).default([]),

  // 메타데이터
  createdAt: z.date(),
  updatedAt: z.date(),
});

export type UserOntology = z.infer<typeof UserOntologySchema>;

// 온톨로지 컨텍스트 (현재 활성화된 규칙들)
export const OntologyContextSchema = z.object({
  activePreferences: z.array(ThinkingPreferenceSchema),
  activeTaboos: z.array(TabooSchema),
  activeApprovalRules: z.array(ApprovalRuleSchema),
  matchedFailurePatterns: z.array(FailurePatternSchema),
  appliedConstraints: z.array(z.string()),
});

export type OntologyContext = z.infer<typeof OntologyContextSchema>;
