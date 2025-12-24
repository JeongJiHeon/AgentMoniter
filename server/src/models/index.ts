// Ticket models
export {
  TicketStatusSchema,
  PrioritySchema,
  TicketOptionSchema,
  TicketSchema,
  CreateTicketInputSchema,
  type TicketStatus,
  type Priority,
  type TicketOption,
  type Ticket,
  type CreateTicketInput,
} from './ticket.js';

// Agent models
export {
  ThinkingModeSchema,
  AgentTypeSchema,
  AgentStatusSchema,
  AgentConstraintSchema,
  AgentSchema,
  RegisterAgentInputSchema,
  AgentStateUpdateSchema,
  type ThinkingMode,
  type AgentType,
  type AgentStatus,
  type AgentConstraint,
  type Agent,
  type RegisterAgentInput,
  type AgentStateUpdate,
} from './agent.js';

// Ontology models
export {
  ThinkingPreferenceSchema,
  TabooSchema,
  FailurePatternSchema,
  ApprovalRuleSchema,
  TaskTemplateSchema,
  UserOntologySchema,
  OntologyContextSchema,
  type ThinkingPreference,
  type Taboo,
  type FailurePattern,
  type ApprovalRule,
  type TaskTemplate,
  type UserOntology,
  type OntologyContext,
} from './ontology.js';

// Approval models
export {
  ApprovalRequestTypeSchema,
  ApprovalStatusSchema,
  ApprovalRequestSchema,
  ApprovalResponseInputSchema,
  CreateApprovalRequestInputSchema,
  type ApprovalRequestType,
  type ApprovalStatus,
  type ApprovalRequest,
  type ApprovalResponseInput,
  type CreateApprovalRequestInput,
} from './approval.js';

// WebSocket message types
export const WebSocketMessageTypeSchema = {
  // Server -> Client
  AGENT_UPDATE: 'agent_update',
  TICKET_CREATED: 'ticket_created',
  TICKET_UPDATED: 'ticket_updated',
  APPROVAL_REQUEST: 'approval_request',
  APPROVAL_RESOLVED: 'approval_resolved',
  AGENT_QUESTION: 'agent_question',
  SYSTEM_NOTIFICATION: 'system_notification',

  // Client -> Server
  APPROVE_REQUEST: 'approve_request',
  REJECT_REQUEST: 'reject_request',
  SELECT_OPTION: 'select_option',
  PROVIDE_INPUT: 'provide_input',
  CANCEL_TICKET: 'cancel_ticket',
  PAUSE_AGENT: 'pause_agent',
  RESUME_AGENT: 'resume_agent',
} as const;

export type WebSocketMessageType = typeof WebSocketMessageTypeSchema[keyof typeof WebSocketMessageTypeSchema];
