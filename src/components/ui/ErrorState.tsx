/**
 * ErrorState - 에러 상태 표시 컴포넌트
 *
 * Features:
 * - 에러 유형별 표시
 * - 재시도 버튼
 * - 상세 정보 표시
 * - 접근성 지원
 */

import type { ReactNode } from 'react';
import { Button } from './Button';

export type ErrorType = 'network' | 'server' | 'notFound' | 'permission' | 'validation' | 'unknown';

interface ErrorStateProps {
  type?: ErrorType;
  title?: string;
  message?: string;
  details?: string;
  onRetry?: () => void;
  onGoBack?: () => void;
  retryText?: string;
  goBackText?: string;
  isRetrying?: boolean;
  className?: string;
  children?: ReactNode;
}

const errorConfig: Record<ErrorType, { icon: ReactNode; defaultTitle: string; defaultMessage: string }> = {
  network: {
    icon: (
      <svg className="w-12 h-12" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M18.364 5.636a9 9 0 010 12.728m0 0l-2.829-2.829m2.829 2.829L21 21M15.536 8.464a5 5 0 010 7.072m0 0l-2.829-2.829m-4.243 2.829a4.978 4.978 0 01-1.414-2.83m-1.414 5.658a9 9 0 01-2.167-9.238m7.824 2.167a1 1 0 111.414 1.414m-1.414-1.414L3 3m8.293 8.293l1.414 1.414" />
      </svg>
    ),
    defaultTitle: '네트워크 연결 오류',
    defaultMessage: '서버에 연결할 수 없습니다. 인터넷 연결을 확인하고 다시 시도해주세요.',
  },
  server: {
    icon: (
      <svg className="w-12 h-12" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M5 12h14M5 12a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v4a2 2 0 01-2 2M5 12a2 2 0 00-2 2v4a2 2 0 002 2h14a2 2 0 002-2v-4a2 2 0 00-2-2m-2-4h.01M17 16h.01" />
      </svg>
    ),
    defaultTitle: '서버 오류',
    defaultMessage: '서버에서 문제가 발생했습니다. 잠시 후 다시 시도해주세요.',
  },
  notFound: {
    icon: (
      <svg className="w-12 h-12" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9.172 16.172a4 4 0 015.656 0M9 10h.01M15 10h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
    ),
    defaultTitle: '찾을 수 없음',
    defaultMessage: '요청한 리소스를 찾을 수 없습니다.',
  },
  permission: {
    icon: (
      <svg className="w-12 h-12" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
      </svg>
    ),
    defaultTitle: '권한 없음',
    defaultMessage: '이 작업을 수행할 권한이 없습니다.',
  },
  validation: {
    icon: (
      <svg className="w-12 h-12" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
      </svg>
    ),
    defaultTitle: '유효성 검사 오류',
    defaultMessage: '입력한 데이터를 확인해주세요.',
  },
  unknown: {
    icon: (
      <svg className="w-12 h-12" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
    ),
    defaultTitle: '오류 발생',
    defaultMessage: '알 수 없는 오류가 발생했습니다.',
  },
};

export function ErrorState({
  type = 'unknown',
  title,
  message,
  details,
  onRetry,
  onGoBack,
  retryText = '다시 시도',
  goBackText = '뒤로 가기',
  isRetrying = false,
  className = '',
  children,
}: ErrorStateProps) {
  const config = errorConfig[type];

  return (
    <div
      className={`flex flex-col items-center justify-center p-8 text-center ${className}`}
      role="alert"
      aria-live="assertive"
    >
      <div className="text-red-400 mb-4">
        {config.icon}
      </div>

      <h3 className="text-lg font-semibold text-white mb-2">
        {title || config.defaultTitle}
      </h3>

      <p className="text-slate-400 text-sm max-w-md mb-4">
        {message || config.defaultMessage}
      </p>

      {details && (
        <details className="mb-4 w-full max-w-md">
          <summary className="text-sm text-slate-500 cursor-pointer hover:text-slate-400 transition-colors">
            상세 정보 보기
          </summary>
          <pre className="mt-2 p-3 bg-slate-900 rounded-lg text-xs text-slate-400 overflow-auto text-left">
            {details}
          </pre>
        </details>
      )}

      {(onRetry || onGoBack || children) && (
        <div className="flex items-center gap-3 mt-2">
          {onGoBack && (
            <Button variant="ghost" onClick={onGoBack}>
              {goBackText}
            </Button>
          )}
          {onRetry && (
            <Button
              onClick={onRetry}
              isLoading={isRetrying}
              loadingText="재시도 중..."
              leftIcon={
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                </svg>
              }
            >
              {retryText}
            </Button>
          )}
          {children}
        </div>
      )}
    </div>
  );
}

/**
 * EmptyState - 빈 상태 표시 컴포넌트
 */
interface EmptyStateProps {
  icon?: ReactNode;
  title: string;
  message?: string;
  action?: ReactNode;
  className?: string;
}

export function EmptyState({
  icon,
  title,
  message,
  action,
  className = '',
}: EmptyStateProps) {
  return (
    <div className={`flex flex-col items-center justify-center p-8 text-center ${className}`}>
      {icon && (
        <div className="text-slate-500 mb-4">
          {icon}
        </div>
      )}

      <h3 className="text-lg font-medium text-slate-300 mb-2">
        {title}
      </h3>

      {message && (
        <p className="text-slate-400 text-sm max-w-md mb-4">
          {message}
        </p>
      )}

      {action && (
        <div className="mt-2">
          {action}
        </div>
      )}
    </div>
  );
}

/**
 * LoadingState - 로딩 상태 표시 컴포넌트
 */
interface LoadingStateProps {
  message?: string;
  className?: string;
}

export function LoadingState({
  message = '로딩 중...',
  className = '',
}: LoadingStateProps) {
  return (
    <div
      className={`flex flex-col items-center justify-center p-8 ${className}`}
      role="status"
      aria-live="polite"
    >
      <div className="relative w-12 h-12 mb-4">
        <div className="absolute inset-0 border-4 border-slate-700 rounded-full" />
        <div className="absolute inset-0 border-4 border-blue-500 rounded-full border-t-transparent animate-spin" />
      </div>
      <p className="text-slate-400 text-sm">{message}</p>
      <span className="sr-only">로딩 중입니다. 잠시만 기다려주세요.</span>
    </div>
  );
}

export default ErrorState;
