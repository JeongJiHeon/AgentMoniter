/**
 * useKeyboardShortcuts - 전역 키보드 단축키 관리 훅
 */

import { useEffect, useCallback, useRef } from 'react'

export interface KeyboardShortcut {
  key: string
  ctrl?: boolean
  meta?: boolean
  shift?: boolean
  alt?: boolean
  action: () => void
  description?: string
  enabled?: boolean
}

interface UseKeyboardShortcutsOptions {
  shortcuts: KeyboardShortcut[]
  enabled?: boolean
  preventDefault?: boolean
}

/**
 * 키보드 단축키를 전역으로 관리하는 훅
 */
export function useKeyboardShortcuts({
  shortcuts,
  enabled = true,
  preventDefault = true,
}: UseKeyboardShortcutsOptions) {
  const shortcutsRef = useRef(shortcuts)
  shortcutsRef.current = shortcuts

  const handleKeyDown = useCallback(
    (event: KeyboardEvent) => {
      if (!enabled) return

      // 입력 요소에서는 단축키 비활성화 (특정 키 제외)
      const target = event.target as HTMLElement
      const isInputElement =
        target.tagName === 'INPUT' ||
        target.tagName === 'TEXTAREA' ||
        target.isContentEditable

      for (const shortcut of shortcutsRef.current) {
        if (shortcut.enabled === false) continue

        const keyMatch = event.key.toLowerCase() === shortcut.key.toLowerCase()
        const ctrlMatch = shortcut.ctrl ? event.ctrlKey || event.metaKey : true
        const metaMatch = shortcut.meta ? event.metaKey : true
        const shiftMatch = shortcut.shift ? event.shiftKey : !event.shiftKey || shortcut.shift === undefined
        const altMatch = shortcut.alt ? event.altKey : !event.altKey

        // Ctrl/Cmd+K는 입력 요소에서도 동작 (Command Palette)
        const isCommandPalette = shortcut.key.toLowerCase() === 'k' && (shortcut.ctrl || shortcut.meta)

        // Escape는 항상 동작
        const isEscape = shortcut.key.toLowerCase() === 'escape'

        // 숫자 키(1-4)는 입력 요소에서 비활성화
        const isNumberKey = /^[1-4]$/.test(shortcut.key)
        if (isNumberKey && isInputElement) continue

        // 입력 요소에서 일반 단축키 무시 (특수 케이스 제외)
        if (isInputElement && !isCommandPalette && !isEscape) continue

        if (keyMatch && ctrlMatch && metaMatch && shiftMatch && altMatch) {
          if (preventDefault) {
            event.preventDefault()
            event.stopPropagation()
          }
          shortcut.action()
          return
        }
      }
    },
    [enabled, preventDefault]
  )

  useEffect(() => {
    window.addEventListener('keydown', handleKeyDown, true)
    return () => {
      window.removeEventListener('keydown', handleKeyDown, true)
    }
  }, [handleKeyDown])
}

/**
 * 단축키 표시용 문자열 생성
 */
export function formatShortcut(shortcut: KeyboardShortcut): string {
  const parts: string[] = []
  const isMac = typeof navigator !== 'undefined' && /Mac|iPod|iPhone|iPad/.test(navigator.platform)

  if (shortcut.ctrl || shortcut.meta) {
    parts.push(isMac ? '⌘' : 'Ctrl')
  }
  if (shortcut.shift) {
    parts.push(isMac ? '⇧' : 'Shift')
  }
  if (shortcut.alt) {
    parts.push(isMac ? '⌥' : 'Alt')
  }

  // 특수 키 이름 변환
  const keyName = shortcut.key.length === 1
    ? shortcut.key.toUpperCase()
    : shortcut.key === 'Escape'
      ? 'Esc'
      : shortcut.key

  parts.push(keyName)

  return parts.join(isMac ? '' : '+')
}

/**
 * 기본 단축키 정의
 */
export const DEFAULT_SHORTCUTS = {
  COMMAND_PALETTE: { key: 'k', ctrl: true, description: 'Open Command Palette' },
  NEW_TASK: { key: 'n', ctrl: true, description: 'Create New Task' },
  NEW_AGENT: { key: 'a', ctrl: true, shift: true, description: 'Create New Agent' },
  TAB_TASKS: { key: '1', description: 'Go to Tasks' },
  TAB_DASHBOARD: { key: '2', description: 'Go to Dashboard' },
  TAB_PERSONALIZATION: { key: '3', description: 'Go to Personalization' },
  TAB_SETTINGS: { key: '4', description: 'Go to Settings' },
  CLOSE: { key: 'Escape', description: 'Close Modal/Palette' },
} as const

export default useKeyboardShortcuts
