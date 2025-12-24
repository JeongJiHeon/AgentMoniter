import { v4 as uuidv4 } from 'uuid';
import type {
  Agent,
  AgentStateUpdate,
  ThinkingMode,
  AgentConstraint,
} from '../models/index.js';
import type {
  IAgent,
  AgentConfig,
  AgentEvent,
  AgentEventType,
  AgentEventHandler,
  AgentExecutionContext,
  AgentInput,
  AgentOutput,
} from './types.js';
import { ThinkingModeStateMachine } from './ThinkingModeStateMachine.js';
import type { ApprovalRequest } from '../models/index.js';

/**
 * 기본 Agent 추상 클래스
 *
 * 모든 Worker Agent는 이 클래스를 상속하여 구현합니다.
 * 핵심 원칙:
 * 1. 임의로 결정하지 않고 사용자에게 승인 요청
 * 2. 온톨로지 규칙 준수
 * 3. 투명한 상태 공개
 */
export abstract class BaseAgent implements IAgent {
  readonly id: string;
  readonly name: string;
  readonly type: string;

  protected state: Agent;
  protected stateMachine: ThinkingModeStateMachine;
  protected context?: AgentExecutionContext;
  protected eventHandlers: Map<AgentEventType, Set<AgentEventHandler>> = new Map();

  constructor(config: AgentConfig) {
    this.id = uuidv4();
    this.name = config.name;
    this.type = config.type;

    const now = new Date();

    // 초기 상태 설정
    this.state = {
      id: this.id,
      name: config.name,
      type: config.type as Agent['type'],
      description: config.description,
      status: 'idle',
      thinkingMode: 'idle',
      constraints: this.buildConstraints(config.constraints ?? []),
      permissions: {
        canCreateTickets: config.permissions?.canCreateTickets ?? true,
        canExecuteApproved: config.permissions?.canExecuteApproved ?? true,
        canAccessMcp: config.permissions?.canAccessMcp ?? [],
      },
      stats: {
        ticketsCreated: 0,
        ticketsCompleted: 0,
        ticketsRejected: 0,
      },
      lastActivity: now,
      createdAt: now,
      updatedAt: now,
    };

    // 상태 머신 초기화
    this.stateMachine = new ThinkingModeStateMachine({
      onStateChange: (from, to, event) => {
        this.onThinkingModeChange(from, to, event);
      },
    });
  }

  // === 상태 조회 ===

  getState(): Agent {
    return { ...this.state };
  }

  getThinkingMode(): ThinkingMode {
    return this.stateMachine.getState();
  }

  isActive(): boolean {
    return this.state.status === 'active';
  }

  // === 라이프사이클 ===

  async initialize(context: AgentExecutionContext): Promise<void> {
    this.context = context;
    this.log('info', `Agent initialized with context`);
    await this.onInitialize(context);
  }

  async start(): Promise<void> {
    this.state.status = 'active';
    this.state.lastActivity = new Date();
    this.log('info', 'Agent started');
    await this.onStart();
    this.emitStateChange();
  }

  async pause(): Promise<void> {
    this.state.status = 'paused';
    this.stateMachine.pause();
    this.log('info', 'Agent paused');
    await this.onPause();
    this.emitStateChange();
  }

  async resume(): Promise<void> {
    this.state.status = 'active';
    this.stateMachine.resume();
    this.log('info', 'Agent resumed');
    await this.onResume();
    this.emitStateChange();
  }

  async stop(): Promise<void> {
    this.state.status = 'idle';
    this.stateMachine.reset();
    this.state.currentTaskId = undefined;
    this.state.currentTaskDescription = undefined;
    this.log('info', 'Agent stopped');
    await this.onStop();
    this.emitStateChange();
  }

  // === 작업 처리 ===

  async process(input: AgentInput): Promise<AgentOutput> {
    this.state.status = 'active';
    this.state.lastActivity = new Date();

    try {
      // 1. 탐색 단계
      await this.stateMachine.transition('START_TASK');
      const explorationResult = await this.explore(input);

      if (!explorationResult.shouldProceed) {
        await this.stateMachine.transition('NO_ACTION_NEEDED');
        return this.createEmptyOutput();
      }

      // 2. 구조화 단계
      await this.stateMachine.transition('INFO_COLLECTED');
      const structuredResult = await this.structure(explorationResult.data);

      // 3. 검증 단계
      await this.stateMachine.transition('STRUCTURE_COMPLETE');
      const validationResult = await this.validate(structuredResult);

      if (!validationResult.isValid) {
        await this.stateMachine.transition('VALIDATION_FAILED');
        // 재탐색 또는 에러 처리
        return this.createEmptyOutput();
      }

      // 4. 요약 단계
      await this.stateMachine.transition('VALIDATION_PASSED');
      const output = await this.summarize(validationResult.data);

      // 5. 완료
      await this.stateMachine.transition('TASK_COMPLETE');

      // 통계 업데이트
      this.state.stats.ticketsCreated += output.tickets.length;

      return output;
    } catch (error) {
      this.log('error', `Processing error: ${error}`);
      this.stateMachine.reset();
      throw error;
    }
  }

  // === 승인 처리 ===

  async onApprovalReceived(approval: ApprovalRequest): Promise<void> {
    this.log('info', `Approval received: ${approval.id} - ${approval.status}`);

    if (approval.status === 'approved') {
      this.state.stats.ticketsCompleted++;
      await this.onApproved(approval);
    } else if (approval.status === 'rejected') {
      this.state.stats.ticketsRejected++;
      await this.onRejected(approval);
    }

    this.emitStateChange();
  }

  // === 상태 업데이트 ===

  async updateState(update: Partial<AgentStateUpdate>): Promise<void> {
    if (update.status) {
      this.state.status = update.status;
    }
    if (update.thinkingMode) {
      // 상태 머신을 통한 전환은 별도로 처리
      this.state.thinkingMode = update.thinkingMode;
    }
    if (update.currentTaskId !== undefined) {
      this.state.currentTaskId = update.currentTaskId ?? undefined;
    }
    if (update.currentTaskDescription !== undefined) {
      this.state.currentTaskDescription = update.currentTaskDescription ?? undefined;
    }

    this.state.updatedAt = new Date();
    this.state.lastActivity = new Date();
    this.emitStateChange();
  }

  // === 이벤트 시스템 ===

  on(eventType: AgentEventType, handler: AgentEventHandler): void {
    if (!this.eventHandlers.has(eventType)) {
      this.eventHandlers.set(eventType, new Set());
    }
    this.eventHandlers.get(eventType)!.add(handler);
  }

  off(eventType: AgentEventType, handler: AgentEventHandler): void {
    this.eventHandlers.get(eventType)?.delete(handler);
  }

  emit(event: AgentEvent): void {
    const handlers = this.eventHandlers.get(event.type);
    if (handlers) {
      handlers.forEach((handler) => {
        try {
          handler(event);
        } catch (error) {
          console.error(`Event handler error:`, error);
        }
      });
    }
  }

  // === Protected 메서드 (하위 클래스에서 구현) ===

  /**
   * 탐색 단계 - 입력 분석 및 정보 수집
   */
  protected abstract explore(input: AgentInput): Promise<{
    shouldProceed: boolean;
    data: unknown;
  }>;

  /**
   * 구조화 단계 - 작업 분해 및 티켓 생성
   */
  protected abstract structure(data: unknown): Promise<unknown>;

  /**
   * 검증 단계 - 생성된 구조 검증
   */
  protected abstract validate(data: unknown): Promise<{
    isValid: boolean;
    data: unknown;
    errors?: string[];
  }>;

  /**
   * 요약 단계 - 최종 출력 생성
   */
  protected abstract summarize(data: unknown): Promise<AgentOutput>;

  // === 라이프사이클 훅 (선택적 오버라이드) ===

  protected async onInitialize(_context: AgentExecutionContext): Promise<void> {}
  protected async onStart(): Promise<void> {}
  protected async onPause(): Promise<void> {}
  protected async onResume(): Promise<void> {}
  protected async onStop(): Promise<void> {}
  protected async onApproved(_approval: ApprovalRequest): Promise<void> {}
  protected async onRejected(_approval: ApprovalRequest): Promise<void> {}

  // === Private 헬퍼 ===

  private buildConstraints(
    constraints: Array<{ type: string; description: string; condition?: string }>
  ): AgentConstraint[] {
    return constraints.map((c) => ({
      id: uuidv4(),
      type: c.type as AgentConstraint['type'],
      description: c.description,
      condition: c.condition,
      isActive: true,
      source: 'system' as const,
    }));
  }

  private onThinkingModeChange(from: ThinkingMode, to: ThinkingMode, event: string): void {
    this.state.thinkingMode = to;
    this.state.updatedAt = new Date();

    this.emit({
      type: 'state_changed',
      agentId: this.id,
      timestamp: new Date(),
      payload: { from, to, event },
    });
  }

  private emitStateChange(): void {
    this.emit({
      type: 'state_changed',
      agentId: this.id,
      timestamp: new Date(),
      payload: this.getState(),
    });
  }

  protected log(level: 'info' | 'warning' | 'error', message: string): void {
    this.emit({
      type: 'log',
      agentId: this.id,
      timestamp: new Date(),
      payload: { level, message },
    });
  }

  private createEmptyOutput(): AgentOutput {
    return {
      tickets: [],
      approvalRequests: [],
      logs: [],
    };
  }
}
