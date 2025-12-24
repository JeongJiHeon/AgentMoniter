import type { ThinkingMode } from '../models/index.js';

// 상태 전환 정의
interface StateTransition {
  from: ThinkingMode;
  to: ThinkingMode;
  event: string;
  guard?: () => boolean;
  action?: () => void | Promise<void>;
}

// 상태 머신 설정
interface StateMachineConfig {
  initialState: ThinkingMode;
  transitions: StateTransition[];
  onStateChange?: (from: ThinkingMode, to: ThinkingMode, event: string) => void;
}

/**
 * Agent 사고 모드 상태 머신
 *
 * 상태 흐름:
 * idle -> exploring -> structuring -> validating -> summarizing -> idle
 *
 * 각 상태에서 가능한 전환:
 * - idle: 새 작업 시작 시 exploring으로
 * - exploring: 정보 수집 완료 시 structuring으로
 * - structuring: 작업 분해 완료 시 validating으로
 * - validating: 검증 완료 시 summarizing으로, 실패 시 exploring으로
 * - summarizing: 완료 시 idle로
 *
 * 모든 상태에서 가능:
 * - pause: 현재 상태 유지하며 일시정지
 * - reset: idle로 초기화
 * - error: 에러 처리 후 idle로
 */
export class ThinkingModeStateMachine {
  private currentState: ThinkingMode;
  private config: StateMachineConfig;
  private history: Array<{ from: ThinkingMode; to: ThinkingMode; event: string; timestamp: Date }> = [];
  private isPaused = false;

  // 기본 전환 규칙
  private static readonly DEFAULT_TRANSITIONS: StateTransition[] = [
    // idle에서 시작
    { from: 'idle', to: 'exploring', event: 'START_TASK' },

    // exploring (탐색)
    { from: 'exploring', to: 'structuring', event: 'INFO_COLLECTED' },
    { from: 'exploring', to: 'idle', event: 'NO_ACTION_NEEDED' },

    // structuring (구조화)
    { from: 'structuring', to: 'validating', event: 'STRUCTURE_COMPLETE' },
    { from: 'structuring', to: 'exploring', event: 'NEED_MORE_INFO' },

    // validating (검증)
    { from: 'validating', to: 'summarizing', event: 'VALIDATION_PASSED' },
    { from: 'validating', to: 'exploring', event: 'VALIDATION_FAILED' },
    { from: 'validating', to: 'structuring', event: 'RESTRUCTURE_NEEDED' },

    // summarizing (요약)
    { from: 'summarizing', to: 'idle', event: 'TASK_COMPLETE' },
    { from: 'summarizing', to: 'validating', event: 'REVIEW_NEEDED' },

    // 공통 전환 (모든 상태에서 가능)
    { from: 'exploring', to: 'idle', event: 'RESET' },
    { from: 'structuring', to: 'idle', event: 'RESET' },
    { from: 'validating', to: 'idle', event: 'RESET' },
    { from: 'summarizing', to: 'idle', event: 'RESET' },
  ];

  constructor(config?: Partial<StateMachineConfig>) {
    this.config = {
      initialState: config?.initialState ?? 'idle',
      transitions: config?.transitions ?? ThinkingModeStateMachine.DEFAULT_TRANSITIONS,
      onStateChange: config?.onStateChange,
    };
    this.currentState = this.config.initialState;
  }

  /**
   * 현재 상태 조회
   */
  getState(): ThinkingMode {
    return this.currentState;
  }

  /**
   * 일시정지 상태 확인
   */
  getIsPaused(): boolean {
    return this.isPaused;
  }

  /**
   * 이벤트 발생으로 상태 전환 시도
   */
  async transition(event: string): Promise<boolean> {
    if (this.isPaused && event !== 'RESUME' && event !== 'RESET') {
      console.log(`[StateMachine] Paused, ignoring event: ${event}`);
      return false;
    }

    const validTransition = this.config.transitions.find(
      (t) => t.from === this.currentState && t.event === event
    );

    if (!validTransition) {
      console.log(`[StateMachine] No valid transition for event '${event}' from state '${this.currentState}'`);
      return false;
    }

    // Guard 조건 확인
    if (validTransition.guard && !validTransition.guard()) {
      console.log(`[StateMachine] Guard condition failed for transition: ${this.currentState} -> ${validTransition.to}`);
      return false;
    }

    const previousState = this.currentState;
    this.currentState = validTransition.to;

    // 히스토리 기록
    this.history.push({
      from: previousState,
      to: this.currentState,
      event,
      timestamp: new Date(),
    });

    // 액션 실행
    if (validTransition.action) {
      await validTransition.action();
    }

    // 상태 변경 콜백
    if (this.config.onStateChange) {
      this.config.onStateChange(previousState, this.currentState, event);
    }

    console.log(`[StateMachine] Transition: ${previousState} -> ${this.currentState} (event: ${event})`);
    return true;
  }

  /**
   * 일시정지
   */
  pause(): void {
    this.isPaused = true;
    console.log(`[StateMachine] Paused at state: ${this.currentState}`);
  }

  /**
   * 재개
   */
  resume(): void {
    this.isPaused = false;
    console.log(`[StateMachine] Resumed at state: ${this.currentState}`);
  }

  /**
   * 초기화
   */
  reset(): void {
    this.currentState = this.config.initialState;
    this.isPaused = false;
    console.log(`[StateMachine] Reset to initial state: ${this.currentState}`);
  }

  /**
   * 현재 상태에서 가능한 이벤트 목록
   */
  getAvailableEvents(): string[] {
    return this.config.transitions
      .filter((t) => t.from === this.currentState)
      .map((t) => t.event);
  }

  /**
   * 특정 이벤트가 현재 상태에서 가능한지 확인
   */
  canTransition(event: string): boolean {
    return this.config.transitions.some(
      (t) => t.from === this.currentState && t.event === event
    );
  }

  /**
   * 상태 전환 히스토리 조회
   */
  getHistory(): Array<{ from: ThinkingMode; to: ThinkingMode; event: string; timestamp: Date }> {
    return [...this.history];
  }

  /**
   * 상태별 설명
   */
  static getStateDescription(state: ThinkingMode): string {
    const descriptions: Record<ThinkingMode, string> = {
      idle: '대기 중 - 새로운 작업을 기다리는 상태',
      exploring: '탐색 중 - 정보를 수집하고 분석하는 상태',
      structuring: '구조화 중 - 작업을 티켓으로 분해하는 상태',
      validating: '검증 중 - 생성된 티켓을 검토하는 상태',
      summarizing: '요약 중 - 결과를 정리하는 상태',
    };
    return descriptions[state];
  }
}
