/**
 * ToastContainer - 접근성이 강화된 토스트 알림 컨테이너
 *
 * Features:
 * - ARIA live region for screen readers
 * - 키보드 접근성
 * - 액션 버튼 지원
 * - 다양한 토스트 타입
 * - 진행률 표시
 */

import { useEffect } from 'react';
import { useNotificationStore } from '../../stores/notificationStore';
import { IconButton } from '../ui/Button';

type ToastType = 'success' | 'error' | 'warning' | 'info';

interface ToastIconProps {
  type: ToastType;
}

function ToastIcon({ type }: ToastIconProps) {
  const iconClass = 'w-5 h-5 flex-shrink-0';

  switch (type) {
    case 'success':
      return (
        <svg className={iconClass} fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
        </svg>
      );
    case 'error':
      return (
        <svg className={iconClass} fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
        </svg>
      );
    case 'warning':
      return (
        <svg className={iconClass} fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
        </svg>
      );
    case 'info':
    default:
      return (
        <svg className={iconClass} fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
      );
  }
}

const toastStyles: Record<ToastType, string> = {
  success: 'bg-green-600 text-white',
  error: 'bg-red-600 text-white',
  warning: 'bg-yellow-500 text-slate-900',
  info: 'bg-blue-600 text-white',
};

const toastLabels: Record<ToastType, string> = {
  success: '성공',
  error: '오류',
  warning: '경고',
  info: '정보',
};

export function ToastContainer() {
  const { toasts, removeToast } = useNotificationStore();

  // ESC 키로 모든 토스트 닫기
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && toasts.length > 0) {
        // 가장 최근 토스트 닫기
        removeToast(toasts[toasts.length - 1].id);
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [toasts, removeToast]);

  if (toasts.length === 0) return null;

  return (
    <div
      className="fixed top-4 right-4 z-50 space-y-2 max-w-md w-full pointer-events-none"
      role="region"
      aria-label="알림"
    >
      {/* ARIA live region for screen readers */}
      <div
        role="status"
        aria-live="polite"
        aria-atomic="true"
        className="sr-only"
      >
        {toasts.map((toast) => (
          <span key={toast.id}>
            {toastLabels[toast.type]}: {toast.message}
          </span>
        ))}
      </div>

      {/* Visual toasts */}
      {toasts.map((toast, index) => (
        <div
          key={toast.id}
          className={`
            pointer-events-auto
            px-4 py-3 rounded-lg shadow-lg
            flex items-start gap-3 min-w-[300px]
            animate-slide-in
            ${toastStyles[toast.type]}
          `}
          role="alert"
          aria-labelledby={`toast-title-${toast.id}`}
          style={{
            animationDelay: `${index * 50}ms`,
          }}
        >
          <ToastIcon type={toast.type} />

          <div className="flex-1 min-w-0">
            <p
              id={`toast-title-${toast.id}`}
              className="text-sm font-medium"
            >
              {toast.message}
            </p>

            {/* 액션 버튼 (있는 경우) */}
            {toast.action && (
              <button
                onClick={() => {
                  toast.action?.onClick();
                  removeToast(toast.id);
                }}
                className={`
                  mt-2 text-sm font-medium underline
                  hover:no-underline focus:outline-none focus:ring-2 focus:ring-white/50 rounded
                  ${toast.type === 'warning' ? 'text-slate-900' : 'text-white'}
                `}
              >
                {toast.action.label}
              </button>
            )}
          </div>

          <IconButton
            icon={
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            }
            aria-label="알림 닫기"
            variant="ghost"
            size="sm"
            onClick={() => removeToast(toast.id)}
            className={`
              flex-shrink-0 -mr-1 -mt-1
              ${toast.type === 'warning' ? 'text-slate-900/70 hover:text-slate-900' : 'text-white/70 hover:text-white'}
            `}
          />
        </div>
      ))}

      {/* 여러 개의 토스트가 있을 때 모두 닫기 버튼 */}
      {toasts.length > 2 && (
        <div className="pointer-events-auto flex justify-end">
          <button
            onClick={() => toasts.forEach((t) => removeToast(t.id))}
            className="text-xs text-slate-400 hover:text-white transition-colors px-2 py-1 rounded hover:bg-slate-700"
          >
            모두 닫기 ({toasts.length})
          </button>
        </div>
      )}
    </div>
  );
}

export default ToastContainer;
