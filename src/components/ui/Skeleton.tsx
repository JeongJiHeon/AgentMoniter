/**
 * Skeleton - 로딩 상태 스켈레톤 컴포넌트
 *
 * Features:
 * - 다양한 형태 지원 (텍스트, 원형, 카드 등)
 * - 애니메이션 효과
 * - 접근성 지원
 */

import type { ReactNode } from 'react';

interface SkeletonProps {
  className?: string;
  width?: string | number;
  height?: string | number;
  variant?: 'text' | 'circular' | 'rectangular' | 'rounded';
  animation?: 'pulse' | 'wave' | 'none';
}

export function Skeleton({
  className = '',
  width,
  height,
  variant = 'text',
  animation = 'pulse',
}: SkeletonProps) {
  const variantStyles = {
    text: 'rounded',
    circular: 'rounded-full',
    rectangular: 'rounded-none',
    rounded: 'rounded-lg',
  };

  const animationStyles = {
    pulse: 'animate-pulse',
    wave: 'animate-shimmer bg-gradient-to-r from-slate-700 via-slate-600 to-slate-700 bg-[length:200%_100%]',
    none: '',
  };

  const style = {
    width: typeof width === 'number' ? `${width}px` : width,
    height: typeof height === 'number' ? `${height}px` : height,
  };

  return (
    <div
      className={`
        bg-slate-700
        ${variantStyles[variant]}
        ${animationStyles[animation]}
        ${className}
      `}
      style={style}
      aria-hidden="true"
      role="presentation"
    />
  );
}

/**
 * SkeletonText - 텍스트 라인 스켈레톤
 */
interface SkeletonTextProps {
  lines?: number;
  className?: string;
}

export function SkeletonText({ lines = 3, className = '' }: SkeletonTextProps) {
  return (
    <div className={`space-y-2 ${className}`} aria-hidden="true">
      {Array.from({ length: lines }).map((_, i) => (
        <Skeleton
          key={i}
          height={16}
          width={i === lines - 1 ? '60%' : '100%'}
          variant="text"
        />
      ))}
    </div>
  );
}

/**
 * SkeletonCard - 카드 형태 스켈레톤
 */
interface SkeletonCardProps {
  hasImage?: boolean;
  imageHeight?: number;
  lines?: number;
  className?: string;
}

export function SkeletonCard({
  hasImage = true,
  imageHeight = 120,
  lines = 2,
  className = '',
}: SkeletonCardProps) {
  return (
    <div
      className={`bg-slate-800 rounded-lg border border-slate-700 overflow-hidden ${className}`}
      aria-hidden="true"
    >
      {hasImage && (
        <Skeleton height={imageHeight} variant="rectangular" />
      )}
      <div className="p-4 space-y-3">
        <Skeleton height={20} width="70%" variant="text" />
        <SkeletonText lines={lines} />
      </div>
    </div>
  );
}

/**
 * SkeletonTaskCard - 태스크 카드 스켈레톤
 */
export function SkeletonTaskCard({ className = '' }: { className?: string }) {
  return (
    <div
      className={`bg-slate-800/50 rounded-xl p-4 border border-slate-700 ${className}`}
      aria-hidden="true"
    >
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center gap-3">
          <Skeleton width={24} height={24} variant="circular" />
          <Skeleton width={120} height={20} variant="text" />
        </div>
        <Skeleton width={60} height={24} variant="rounded" />
      </div>
      <SkeletonText lines={2} />
      <div className="flex items-center gap-2 mt-3">
        <Skeleton width={60} height={20} variant="rounded" />
        <Skeleton width={80} height={20} variant="rounded" />
      </div>
    </div>
  );
}

/**
 * SkeletonAgentCard - 에이전트 카드 스켈레톤
 */
export function SkeletonAgentCard({ className = '' }: { className?: string }) {
  return (
    <div
      className={`bg-slate-800/50 rounded-xl p-4 border border-slate-700 ${className}`}
      aria-hidden="true"
    >
      <div className="flex items-center gap-3 mb-4">
        <Skeleton width={40} height={40} variant="circular" />
        <div className="flex-1">
          <Skeleton width={100} height={18} variant="text" className="mb-2" />
          <Skeleton width={60} height={14} variant="text" />
        </div>
        <Skeleton width={8} height={8} variant="circular" />
      </div>
      <Skeleton width="100%" height={12} variant="text" className="mb-2" />
      <Skeleton width="80%" height={12} variant="text" />
    </div>
  );
}

/**
 * SkeletonList - 리스트 스켈레톤 래퍼
 */
interface SkeletonListProps {
  count?: number;
  children: ReactNode;
  className?: string;
}

export function SkeletonList({ count = 3, children, className = '' }: SkeletonListProps) {
  return (
    <div className={className} role="status" aria-label="로딩 중...">
      <span className="sr-only">콘텐츠를 불러오는 중입니다...</span>
      {Array.from({ length: count }).map((_, i) => (
        <div key={i}>{children}</div>
      ))}
    </div>
  );
}

export default Skeleton;
