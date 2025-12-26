/**
 * localStorage 유틸리티
 * 애플리케이션 상태를 로컬 스토리지에 저장하고 불러오는 기능 제공
 */

const STORAGE_KEYS = {
  SETTINGS: 'agent-monitor-settings',
  TASKS: 'agent-monitor-tasks',
  AGENTS: 'agent-monitor-agents',
  TICKETS: 'agent-monitor-tickets',
  APPROVALS: 'agent-monitor-approvals',
  AUTO_ASSIGN_MODE: 'agent-monitor-auto-assign-mode',
  CUSTOM_AGENTS: 'agent-monitor-custom-agents',
  PERSONALIZATION: 'agent-monitor-personalization',
  THEME: 'agent-monitor-theme',
} as const;

/**
 * localStorage에 데이터 저장
 */
export function saveToLocalStorage<T>(key: keyof typeof STORAGE_KEYS, data: T): boolean {
  try {
    const serialized = JSON.stringify(data);
    localStorage.setItem(STORAGE_KEYS[key], serialized);
    return true;
  } catch (error) {
    console.error(`[localStorage] Failed to save ${key}:`, error);
    return false;
  }
}

/**
 * localStorage에서 데이터 불러오기
 */
export function loadFromLocalStorage<T>(key: keyof typeof STORAGE_KEYS): T | null {
  try {
    const serialized = localStorage.getItem(STORAGE_KEYS[key]);
    if (serialized === null) {
      return null;
    }
    return JSON.parse(serialized) as T;
  } catch (error) {
    console.error(`[localStorage] Failed to load ${key}:`, error);
    return null;
  }
}

/**
 * localStorage에서 데이터 삭제
 */
export function removeFromLocalStorage(key: keyof typeof STORAGE_KEYS): boolean {
  try {
    localStorage.removeItem(STORAGE_KEYS[key]);
    return true;
  } catch (error) {
    console.error(`[localStorage] Failed to remove ${key}:`, error);
    return false;
  }
}

/**
 * 모든 저장된 데이터 삭제
 */
export function clearAllStorage(): boolean {
  try {
    Object.values(STORAGE_KEYS).forEach(key => {
      localStorage.removeItem(key);
    });
    return true;
  } catch (error) {
    console.error('[localStorage] Failed to clear all storage:', error);
    return false;
  }
}

/**
 * Date 객체를 포함한 데이터의 직렬화/역직렬화 헬퍼
 */
export function serializeWithDates<T>(data: T): string {
  return JSON.stringify(data, (_key, value) => {
    if (value instanceof Date) {
      return { __type: 'Date', value: value.toISOString() };
    }
    return value;
  });
}

export function deserializeWithDates<T>(json: string): T {
  return JSON.parse(json, (_key, value) => {
    if (value && typeof value === 'object' && value.__type === 'Date') {
      return new Date(value.value);
    }
    return value;
  });
}
