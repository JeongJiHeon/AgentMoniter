/**
 * ErrorBoundary Component Tests
 *
 * ErrorBoundary 컴포넌트의 단위 테스트입니다.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { ErrorBoundary } from '../../errors/ErrorBoundary'

// 에러를 발생시키는 테스트 컴포넌트
function ThrowingComponent({ shouldThrow }: { shouldThrow: boolean }) {
  if (shouldThrow) {
    throw new Error('Test error message')
  }
  return <div>Normal content</div>
}

describe('ErrorBoundary', () => {
  // 콘솔 에러 억제
  beforeEach(() => {
    vi.spyOn(console, 'error').mockImplementation(() => {})
  })

  it('정상적인 children을 렌더링한다', () => {
    render(
      <ErrorBoundary>
        <div>Test content</div>
      </ErrorBoundary>
    )

    expect(screen.getByText('Test content')).toBeInTheDocument()
  })

  it('에러 발생시 기본 폴백 UI를 표시한다', () => {
    render(
      <ErrorBoundary>
        <ThrowingComponent shouldThrow={true} />
      </ErrorBoundary>
    )

    expect(screen.getByText('오류가 발생했습니다')).toBeInTheDocument()
    expect(screen.getByText('Test error message')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: '다시 시도' })).toBeInTheDocument()
  })

  it('커스텀 fallback을 지원한다', () => {
    render(
      <ErrorBoundary fallback={<div>Custom error fallback</div>}>
        <ThrowingComponent shouldThrow={true} />
      </ErrorBoundary>
    )

    expect(screen.getByText('Custom error fallback')).toBeInTheDocument()
  })

  it('함수형 fallback을 지원한다', () => {
    const fallbackFn = vi.fn((error: Error, reset: () => void) => (
      <div>
        <span>Error: {error.message}</span>
        <button onClick={reset}>Reset</button>
      </div>
    ))

    render(
      <ErrorBoundary fallback={fallbackFn}>
        <ThrowingComponent shouldThrow={true} />
      </ErrorBoundary>
    )

    expect(fallbackFn).toHaveBeenCalled()
    expect(screen.getByText('Error: Test error message')).toBeInTheDocument()
  })

  it('onError 콜백을 호출한다', () => {
    const onError = vi.fn()

    render(
      <ErrorBoundary onError={onError}>
        <ThrowingComponent shouldThrow={true} />
      </ErrorBoundary>
    )

    expect(onError).toHaveBeenCalledWith(
      expect.any(Error),
      expect.objectContaining({
        componentStack: expect.any(String),
      })
    )
  })

  it('다시 시도 버튼으로 상태를 초기화한다', () => {
    const { rerender } = render(
      <ErrorBoundary>
        <ThrowingComponent shouldThrow={true} />
      </ErrorBoundary>
    )

    expect(screen.getByText('오류가 발생했습니다')).toBeInTheDocument()

    // 다시 시도 버튼 클릭
    fireEvent.click(screen.getByRole('button', { name: '다시 시도' }))

    // 에러 없이 다시 렌더링
    rerender(
      <ErrorBoundary>
        <ThrowingComponent shouldThrow={false} />
      </ErrorBoundary>
    )

    expect(screen.getByText('Normal content')).toBeInTheDocument()
  })
})
