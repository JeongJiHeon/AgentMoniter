import type {
  IMCPService,
  MCPServiceType,
  MCPServiceConfig,
  MCPOperationRequest,
  MCPOperationResult,
  MCPValidationResult,
  MCPEventHandler,
} from './types.js';

/**
 * MCP 서비스 레지스트리
 *
 * 모든 MCP 서비스 인스턴스를 관리합니다.
 */
export class MCPServiceRegistry {
  private services: Map<MCPServiceType, IMCPService> = new Map();
  private configs: Map<MCPServiceType, MCPServiceConfig> = new Map();
  private globalEventHandlers: Set<MCPEventHandler> = new Set();

  /**
   * 서비스 등록
   */
  register(service: IMCPService, config: MCPServiceConfig): void {
    this.services.set(service.type, service);
    this.configs.set(service.type, config);
    console.log(`[MCPRegistry] Service registered: ${service.name} (${service.type})`);
  }

  /**
   * 서비스 해제
   */
  async unregister(type: MCPServiceType): Promise<void> {
    const service = this.services.get(type);
    if (service?.isConnected()) {
      await service.disconnect();
    }
    this.services.delete(type);
    this.configs.delete(type);
    console.log(`[MCPRegistry] Service unregistered: ${type}`);
  }

  /**
   * 서비스 조회
   */
  getService(type: MCPServiceType): IMCPService | undefined {
    return this.services.get(type);
  }

  /**
   * 모든 서비스 조회
   */
  getAllServices(): IMCPService[] {
    return Array.from(this.services.values());
  }

  /**
   * 연결된 서비스만 조회
   */
  getConnectedServices(): IMCPService[] {
    return this.getAllServices().filter((s) => s.isConnected());
  }

  /**
   * 서비스 연결
   */
  async connectService(type: MCPServiceType): Promise<void> {
    const service = this.services.get(type);
    if (!service) {
      throw new Error(`Service not found: ${type}`);
    }
    await service.connect();
  }

  /**
   * 모든 서비스 연결
   */
  async connectAll(): Promise<void> {
    const enabledServices = Array.from(this.configs.entries())
      .filter(([, config]) => config.enabled)
      .map(([type]) => type);

    await Promise.all(
      enabledServices.map((type) => this.connectService(type).catch((err) => {
        console.error(`[MCPRegistry] Failed to connect ${type}:`, err);
      }))
    );
  }

  /**
   * 모든 서비스 연결 해제
   */
  async disconnectAll(): Promise<void> {
    await Promise.all(
      this.getAllServices().map((s) => s.disconnect().catch((err) => {
        console.error(`[MCPRegistry] Failed to disconnect ${s.type}:`, err);
      }))
    );
  }

  /**
   * 작업 실행
   */
  async execute(request: MCPOperationRequest): Promise<MCPOperationResult> {
    const service = this.services.get(request.service);
    if (!service) {
      return {
        success: false,
        error: `Service not found: ${request.service}`,
      };
    }

    if (!service.isConnected()) {
      return {
        success: false,
        error: `Service not connected: ${request.service}`,
      };
    }

    return service.execute(request);
  }

  /**
   * 작업 검증
   */
  async validate(request: MCPOperationRequest): Promise<MCPValidationResult> {
    const service = this.services.get(request.service);
    if (!service) {
      return {
        isValid: false,
        errors: [`Service not found: ${request.service}`],
        warnings: [],
        requiresApproval: true,
      };
    }

    return service.validate(request);
  }

  /**
   * 전역 이벤트 핸들러 등록
   */
  onGlobalEvent(handler: MCPEventHandler): void {
    this.globalEventHandlers.add(handler);
  }

  /**
   * 서비스 상태 요약
   */
  getStatus(): {
    total: number;
    connected: number;
    services: Array<{
      type: MCPServiceType;
      name: string;
      connected: boolean;
      enabled: boolean;
    }>;
  } {
    const services = Array.from(this.services.entries()).map(([type, service]) => ({
      type,
      name: service.name,
      connected: service.isConnected(),
      enabled: this.configs.get(type)?.enabled ?? false,
    }));

    return {
      total: services.length,
      connected: services.filter((s) => s.connected).length,
      services,
    };
  }
}

// 싱글톤 인스턴스
export const mcpRegistry = new MCPServiceRegistry();
