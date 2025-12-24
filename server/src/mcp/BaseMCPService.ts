import type {
  IMCPService,
  MCPServiceType,
  MCPServiceConfig,
  MCPOperationRequest,
  MCPOperationResult,
  MCPValidationResult,
  MCPEvent,
  MCPEventType,
  MCPEventHandler,
  MCPOperationType,
} from './types.js';

/**
 * MCP 서비스 기본 추상 클래스
 *
 * 핵심 원칙:
 * 1. 읽기 작업은 자유롭게 수행
 * 2. 쓰기 작업은 초안 생성까지만, 최종 저장은 승인 후
 * 3. 전송 작업(메일 발송, 공유 등)은 반드시 승인 필요
 */
export abstract class BaseMCPService implements IMCPService {
  readonly type: MCPServiceType;
  readonly name: string;

  protected config: MCPServiceConfig;
  protected connected = false;
  protected eventHandlers: Map<MCPEventType, Set<MCPEventHandler>> = new Map();

  // 승인 필요 여부 판단 기준
  protected static readonly APPROVAL_REQUIRED_OPERATIONS: MCPOperationType[] = [
    'send',
    'publish',
    'share',
    'delete',
  ];

  protected static readonly APPROVAL_OPTIONAL_OPERATIONS: MCPOperationType[] = [
    'create',
    'update',
  ];

  protected static readonly NO_APPROVAL_OPERATIONS: MCPOperationType[] = [
    'read',
    'search',
    'list',
  ];

  constructor(config: MCPServiceConfig) {
    this.type = config.type;
    this.name = config.name;
    this.config = config;
  }

  // === 연결 상태 ===

  isConnected(): boolean {
    return this.connected;
  }

  async connect(): Promise<void> {
    if (this.connected) {
      return;
    }

    await this.doConnect();
    this.connected = true;
    this.emit({
      type: 'service_connected',
      service: this.type,
      timestamp: new Date(),
      payload: { name: this.name },
    });
  }

  async disconnect(): Promise<void> {
    if (!this.connected) {
      return;
    }

    await this.doDisconnect();
    this.connected = false;
    this.emit({
      type: 'service_disconnected',
      service: this.type,
      timestamp: new Date(),
      payload: { name: this.name },
    });
  }

  // === 작업 실행 ===

  async execute(request: MCPOperationRequest): Promise<MCPOperationResult> {
    if (!this.connected) {
      return {
        success: false,
        error: 'Service not connected',
      };
    }

    // 승인 확인
    if (request.requiresApproval && request.status !== 'approved') {
      return {
        success: false,
        error: 'Operation requires approval',
      };
    }

    this.emit({
      type: 'operation_started',
      service: this.type,
      operationId: request.id,
      timestamp: new Date(),
      payload: { operation: request.operation, target: request.target },
    });

    try {
      const result = await this.doExecute(request);

      this.emit({
        type: result.success ? 'operation_completed' : 'operation_failed',
        service: this.type,
        operationId: request.id,
        timestamp: new Date(),
        payload: result,
      });

      return result;
    } catch (error) {
      const errorResult: MCPOperationResult = {
        success: false,
        error: error instanceof Error ? error.message : String(error),
      };

      this.emit({
        type: 'operation_failed',
        service: this.type,
        operationId: request.id,
        timestamp: new Date(),
        payload: errorResult,
      });

      return errorResult;
    }
  }

  // === 작업 검증 ===

  async validate(request: MCPOperationRequest): Promise<MCPValidationResult> {
    const errors: string[] = [];
    const warnings: string[] = [];

    // 기본 검증
    if (!request.target?.type) {
      errors.push('Target type is required');
    }

    // 승인 필요 여부 판단
    const requiresApproval = this.determineApprovalRequirement(request);
    let approvalReason: string | undefined;

    if (requiresApproval) {
      approvalReason = this.getApprovalReason(request);
    }

    // 서비스별 추가 검증
    const serviceValidation = await this.doValidate(request);
    errors.push(...serviceValidation.errors);
    warnings.push(...serviceValidation.warnings);

    return {
      isValid: errors.length === 0,
      errors,
      warnings,
      requiresApproval,
      approvalReason,
    };
  }

  // === 롤백 ===

  async rollback(operationId: string): Promise<boolean> {
    // 기본 구현: 롤백 불가
    console.log(`[${this.name}] Rollback not supported for operation: ${operationId}`);
    return false;
  }

  // === 이벤트 ===

  on(eventType: MCPEventType, handler: MCPEventHandler): void {
    if (!this.eventHandlers.has(eventType)) {
      this.eventHandlers.set(eventType, new Set());
    }
    this.eventHandlers.get(eventType)!.add(handler);
  }

  off(eventType: MCPEventType, handler: MCPEventHandler): void {
    this.eventHandlers.get(eventType)?.delete(handler);
  }

  protected emit(event: MCPEvent): void {
    const handlers = this.eventHandlers.get(event.type);
    if (handlers) {
      handlers.forEach((handler) => {
        try {
          handler(event);
        } catch (error) {
          console.error(`[${this.name}] Event handler error:`, error);
        }
      });
    }
  }

  // === Protected 헬퍼 ===

  protected determineApprovalRequirement(request: MCPOperationRequest): boolean {
    // 필수 승인 작업
    if (BaseMCPService.APPROVAL_REQUIRED_OPERATIONS.includes(request.operation)) {
      return true;
    }

    // 승인 불필요 작업
    if (BaseMCPService.NO_APPROVAL_OPERATIONS.includes(request.operation)) {
      return false;
    }

    // 선택적 승인 작업 - 서비스별 정책 적용
    return this.shouldRequireApproval(request);
  }

  protected getApprovalReason(request: MCPOperationRequest): string {
    const reasons: Record<MCPOperationType, string> = {
      send: '외부로 메시지/이메일을 발송하려고 합니다',
      publish: '콘텐츠를 공개하려고 합니다',
      share: '다른 사용자와 공유하려고 합니다',
      delete: '데이터를 삭제하려고 합니다',
      create: '새 콘텐츠를 생성하려고 합니다',
      update: '기존 콘텐츠를 수정하려고 합니다',
      read: '',
      search: '',
      list: '',
    };

    return reasons[request.operation] || '작업을 수행하려고 합니다';
  }

  // === Abstract 메서드 (하위 클래스에서 구현) ===

  protected abstract doConnect(): Promise<void>;
  protected abstract doDisconnect(): Promise<void>;
  protected abstract doExecute(request: MCPOperationRequest): Promise<MCPOperationResult>;
  protected abstract doValidate(request: MCPOperationRequest): Promise<{
    errors: string[];
    warnings: string[];
  }>;

  /**
   * 서비스별 승인 필요 여부 추가 판단
   * 기본값: create/update는 승인 필요
   */
  protected shouldRequireApproval(_request: MCPOperationRequest): boolean {
    return true;
  }
}
