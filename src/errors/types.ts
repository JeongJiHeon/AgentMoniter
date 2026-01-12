/**
 * Error Types - 에러 타입 정의
 *
 * 프론트엔드 전체에서 사용하는 에러 관련 타입 정의입니다.
 */

export type ErrorType = 'network' | 'auth' | 'validation' | 'business' | 'system';

export type ErrorSeverity = 'info' | 'warning' | 'error' | 'critical';

export interface AppErrorDetails {
  field?: string;
  resource?: string;
  resourceId?: string;
  [key: string]: unknown;
}

export interface AppError {
  code: string;
  type: ErrorType;
  severity: ErrorSeverity;
  message: string;
  details?: AppErrorDetails;
  traceId?: string;
  timestamp?: string;
}

export interface ErrorState {
  hasError: boolean;
  error: AppError | null;
}

export interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
  errorInfo: React.ErrorInfo | null;
}

// 에러 코드 상수
export const ErrorCodes = {
  // Network
  NETWORK_ERROR: 'NETWORK_ERROR',
  TIMEOUT: 'TIMEOUT',
  CONNECTION_FAILED: 'CONNECTION_FAILED',

  // WebSocket
  WEBSOCKET_ERROR: 'WEBSOCKET_ERROR',
  WEBSOCKET_DISCONNECTED: 'WEBSOCKET_DISCONNECTED',

  // Agent
  AGENT_NOT_FOUND: 'AGENT_NOT_FOUND',
  AGENT_INITIALIZATION_FAILED: 'AGENT_INITIALIZATION_FAILED',

  // Task
  TASK_NOT_FOUND: 'TASK_NOT_FOUND',
  TASK_PROCESSING_FAILED: 'TASK_PROCESSING_FAILED',

  // LLM
  LLM_ERROR: 'LLM_ERROR',
  LLM_RATE_LIMIT: 'LLM_RATE_LIMIT',

  // Validation
  VALIDATION_ERROR: 'VALIDATION_ERROR',
  INVALID_INPUT: 'INVALID_INPUT',

  // System
  INTERNAL_ERROR: 'INTERNAL_ERROR',
  UNKNOWN_ERROR: 'UNKNOWN_ERROR',
} as const;

export type ErrorCode = typeof ErrorCodes[keyof typeof ErrorCodes];
