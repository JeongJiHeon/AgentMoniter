/**
 * Error Handler - 에러 처리 유틸리티
 *
 * 에러 생성, 변환, 처리를 위한 유틸리티 함수입니다.
 */

import type { AppError, ErrorType, ErrorSeverity } from './types';
import { ErrorCodes } from './types';

/**
 * AppError 클래스
 * 표준화된 에러 객체를 생성합니다.
 */
export class ApplicationError extends Error implements AppError {
  code: string;
  type: ErrorType;
  severity: ErrorSeverity;
  details?: Record<string, unknown>;
  traceId?: string;
  timestamp: string;

  constructor(
    code: string,
    type: ErrorType,
    severity: ErrorSeverity,
    message: string,
    details?: Record<string, unknown>
  ) {
    super(message);
    this.name = 'ApplicationError';
    this.code = code;
    this.type = type;
    this.severity = severity;
    this.message = message;
    this.details = details;
    this.traceId = crypto.randomUUID();
    this.timestamp = new Date().toISOString();
  }

  toJSON(): AppError {
    return {
      code: this.code,
      type: this.type,
      severity: this.severity,
      message: this.message,
      details: this.details,
      traceId: this.traceId,
      timestamp: this.timestamp,
    };
  }
}

/**
 * 에러를 AppError로 변환
 */
export function toAppError(error: unknown): AppError {
  // 이미 AppError인 경우
  if (error instanceof ApplicationError) {
    return error.toJSON();
  }

  // 일반 Error인 경우
  if (error instanceof Error) {
    // TypeError
    if (error instanceof TypeError) {
      return {
        code: ErrorCodes.VALIDATION_ERROR,
        type: 'validation',
        severity: 'error',
        message: error.message,
        timestamp: new Date().toISOString(),
      };
    }

    // 네트워크 에러
    if (error.name === 'NetworkError' || error.message.includes('fetch')) {
      return {
        code: ErrorCodes.NETWORK_ERROR,
        type: 'network',
        severity: 'error',
        message: '네트워크 연결에 문제가 있습니다.',
        timestamp: new Date().toISOString(),
      };
    }

    // 일반 Error
    return {
      code: ErrorCodes.UNKNOWN_ERROR,
      type: 'system',
      severity: 'error',
      message: error.message,
      timestamp: new Date().toISOString(),
    };
  }

  // 문자열인 경우
  if (typeof error === 'string') {
    return {
      code: ErrorCodes.UNKNOWN_ERROR,
      type: 'system',
      severity: 'error',
      message: error,
      timestamp: new Date().toISOString(),
    };
  }

  // 알 수 없는 에러
  return {
    code: ErrorCodes.UNKNOWN_ERROR,
    type: 'system',
    severity: 'error',
    message: 'An unknown error occurred',
    timestamp: new Date().toISOString(),
  };
}

/**
 * 에러 팩토리 함수들
 */
export const ErrorFactory = {
  networkError: (message = '네트워크 연결에 문제가 있습니다.'): ApplicationError =>
    new ApplicationError(
      ErrorCodes.NETWORK_ERROR,
      'network',
      'error',
      message
    ),

  validationError: (message: string, field?: string): ApplicationError =>
    new ApplicationError(
      ErrorCodes.VALIDATION_ERROR,
      'validation',
      'warning',
      message,
      field ? { field } : undefined
    ),

  notFound: (resource: string, id: string): ApplicationError =>
    new ApplicationError(
      `${resource.toUpperCase()}_NOT_FOUND`,
      'business',
      'warning',
      `${resource} '${id}'을(를) 찾을 수 없습니다.`,
      { resource, resourceId: id }
    ),

  webSocketError: (message = 'WebSocket 연결에 문제가 있습니다.'): ApplicationError =>
    new ApplicationError(
      ErrorCodes.WEBSOCKET_ERROR,
      'network',
      'error',
      message
    ),

  llmError: (message: string, details?: Record<string, unknown>): ApplicationError =>
    new ApplicationError(
      ErrorCodes.LLM_ERROR,
      'system',
      'error',
      message,
      details
    ),

  internalError: (message = '내부 오류가 발생했습니다.'): ApplicationError =>
    new ApplicationError(
      ErrorCodes.INTERNAL_ERROR,
      'system',
      'error',
      message
    ),
};

/**
 * 에러 로깅
 */
export function logError(error: AppError, context?: string): void {
  const prefix = context ? `[${context}]` : '[Error]';
  console.error(`${prefix} ${error.code}: ${error.message}`, {
    type: error.type,
    severity: error.severity,
    details: error.details,
    traceId: error.traceId,
  });
}

/**
 * 사용자 친화적 에러 메시지 반환
 */
export function getUserFriendlyMessage(error: AppError): string {
  switch (error.code) {
    case ErrorCodes.NETWORK_ERROR:
    case ErrorCodes.CONNECTION_FAILED:
      return '네트워크 연결을 확인해주세요.';
    case ErrorCodes.WEBSOCKET_DISCONNECTED:
      return '서버와의 연결이 끊어졌습니다. 잠시 후 다시 시도해주세요.';
    case ErrorCodes.AGENT_NOT_FOUND:
      return '요청한 Agent를 찾을 수 없습니다.';
    case ErrorCodes.LLM_RATE_LIMIT:
      return 'API 요청 한도에 도달했습니다. 잠시 후 다시 시도해주세요.';
    case ErrorCodes.VALIDATION_ERROR:
      return error.message || '입력값을 확인해주세요.';
    default:
      return error.message || '오류가 발생했습니다. 다시 시도해주세요.';
  }
}

/**
 * 재시도 가능한 에러인지 확인
 */
export function isRetryable(error: AppError): boolean {
  const retryableCodes = [
    ErrorCodes.NETWORK_ERROR,
    ErrorCodes.TIMEOUT,
    ErrorCodes.WEBSOCKET_DISCONNECTED,
    ErrorCodes.LLM_RATE_LIMIT,
  ];
  return retryableCodes.includes(error.code as typeof retryableCodes[number]);
}
