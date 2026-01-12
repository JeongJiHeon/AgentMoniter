/**
 * Vitest Test Setup
 *
 * 테스트 환경 전역 설정 파일입니다.
 */

import '@testing-library/jest-dom'

// Mock WebSocket
class MockWebSocket {
  static CONNECTING = 0
  static OPEN = 1
  static CLOSING = 2
  static CLOSED = 3

  readyState = MockWebSocket.OPEN
  onopen: (() => void) | null = null
  onclose: (() => void) | null = null
  onmessage: ((event: { data: string }) => void) | null = null
  onerror: ((error: Event) => void) | null = null

  constructor(public url: string) {
    setTimeout(() => {
      this.onopen?.()
    }, 0)
  }

  send(data: string): void {
    // Mock send implementation
    console.log('WebSocket send:', data)
  }

  close(): void {
    this.readyState = MockWebSocket.CLOSED
    this.onclose?.()
  }
}

// @ts-expect-error - Mock global WebSocket
global.WebSocket = MockWebSocket

// Mock matchMedia
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: vi.fn().mockImplementation((query: string) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: vi.fn(),
    removeListener: vi.fn(),
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
  })),
})

// Mock IntersectionObserver
class MockIntersectionObserver {
  observe = vi.fn()
  unobserve = vi.fn()
  disconnect = vi.fn()
}

// @ts-expect-error - Mock global IntersectionObserver
global.IntersectionObserver = MockIntersectionObserver

// Mock ResizeObserver
class MockResizeObserver {
  observe = vi.fn()
  unobserve = vi.fn()
  disconnect = vi.fn()
}

// @ts-expect-error - Mock global ResizeObserver
global.ResizeObserver = MockResizeObserver

// Cleanup after each test
afterEach(() => {
  vi.clearAllMocks()
})
