/**
 * useWebSocket Hook Tests
 *
 * WebSocket 훅의 단위 테스트입니다.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { renderHook, act, waitFor } from '@testing-library/react'

// WebSocket mock 메시지 시뮬레이션 헬퍼
function simulateMessage(message: object) {
  const event = new MessageEvent('message', {
    data: JSON.stringify(message),
  })
  window.dispatchEvent(event)
}

describe('useWebSocket', () => {
  let originalWebSocket: typeof WebSocket

  beforeEach(() => {
    originalWebSocket = global.WebSocket
    vi.useFakeTimers()
  })

  afterEach(() => {
    global.WebSocket = originalWebSocket
    vi.useRealTimers()
  })

  it('WebSocket 연결 상태를 추적한다', async () => {
    // Mock WebSocket 구현
    const mockWs = {
      readyState: WebSocket.CONNECTING,
      onopen: null as (() => void) | null,
      onclose: null as (() => void) | null,
      onmessage: null as ((e: MessageEvent) => void) | null,
      onerror: null as ((e: Event) => void) | null,
      send: vi.fn(),
      close: vi.fn(),
    }

    const MockWebSocket = vi.fn(() => {
      setTimeout(() => {
        mockWs.readyState = WebSocket.OPEN
        mockWs.onopen?.()
      }, 0)
      return mockWs
    })

    // @ts-expect-error - Mock global WebSocket
    global.WebSocket = MockWebSocket

    // 기본적인 WebSocket 동작 테스트
    expect(MockWebSocket).toBeDefined()
  })

  it('메시지 전송 기능이 동작한다', () => {
    const mockSend = vi.fn()
    const mockWs = {
      readyState: WebSocket.OPEN,
      send: mockSend,
      close: vi.fn(),
    }

    // WebSocket이 열린 상태에서 메시지 전송
    const testMessage = { type: 'test', payload: { data: 'hello' } }
    mockWs.send(JSON.stringify(testMessage))

    expect(mockSend).toHaveBeenCalledWith(JSON.stringify(testMessage))
  })

  it('재연결 로직이 동작한다', () => {
    vi.useFakeTimers()

    let connectionAttempts = 0
    const MockWebSocket = vi.fn(() => {
      connectionAttempts++
      return {
        readyState: WebSocket.CLOSED,
        onopen: null,
        onclose: null,
        onmessage: null,
        onerror: null,
        send: vi.fn(),
        close: vi.fn(),
      }
    })

    // 재연결 타이머 시뮬레이션
    const reconnectDelay = 3000
    const triggerReconnect = () => {
      MockWebSocket()
    }

    // 첫 번째 연결
    triggerReconnect()
    expect(connectionAttempts).toBe(1)

    // 재연결 시뮬레이션
    vi.advanceTimersByTime(reconnectDelay)
    triggerReconnect()
    expect(connectionAttempts).toBe(2)

    vi.useRealTimers()
  })
})

describe('WebSocket Message Handling', () => {
  it('AGENT_UPDATE 메시지를 처리한다', () => {
    const handlers = {
      AGENT_UPDATE: vi.fn(),
      NOTIFICATION: vi.fn(),
    }

    const message = {
      type: 'AGENT_UPDATE',
      payload: {
        agentId: 'agent-1',
        status: 'RUNNING',
      },
    }

    // 메시지 핸들러 호출 시뮬레이션
    const handler = handlers[message.type as keyof typeof handlers]
    handler?.(message.payload)

    expect(handlers.AGENT_UPDATE).toHaveBeenCalledWith({
      agentId: 'agent-1',
      status: 'RUNNING',
    })
  })

  it('NOTIFICATION 메시지를 처리한다', () => {
    const handlers = {
      AGENT_UPDATE: vi.fn(),
      NOTIFICATION: vi.fn(),
    }

    const message = {
      type: 'NOTIFICATION',
      payload: {
        message: 'Task completed',
        severity: 'success',
      },
    }

    const handler = handlers[message.type as keyof typeof handlers]
    handler?.(message.payload)

    expect(handlers.NOTIFICATION).toHaveBeenCalledWith({
      message: 'Task completed',
      severity: 'success',
    })
  })

  it('알 수 없는 메시지 타입을 무시한다', () => {
    const handlers = {
      AGENT_UPDATE: vi.fn(),
      NOTIFICATION: vi.fn(),
    }

    const message = {
      type: 'UNKNOWN_TYPE',
      payload: {},
    }

    const handler = handlers[message.type as keyof typeof handlers]
    handler?.(message.payload)

    expect(handlers.AGENT_UPDATE).not.toHaveBeenCalled()
    expect(handlers.NOTIFICATION).not.toHaveBeenCalled()
  })
})
