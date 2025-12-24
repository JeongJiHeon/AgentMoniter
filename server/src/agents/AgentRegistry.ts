import type { IAgent, AgentConfig, IAgentFactory, AgentEventHandler } from './types.js';
import type { Agent, AgentStateUpdate } from '../models/index.js';

/**
 * Agent 레지스트리
 *
 * 모든 Agent 인스턴스를 관리하고 추적합니다.
 * - Agent 등록/해제
 * - Agent 조회
 * - 전역 이벤트 브로드캐스트
 */
export class AgentRegistry {
  private agents: Map<string, IAgent> = new Map();
  private factories: Map<string, IAgentFactory> = new Map();
  private globalEventHandlers: Set<AgentEventHandler> = new Set();

  /**
   * Agent 팩토리 등록
   */
  registerFactory(type: string, factory: IAgentFactory): void {
    this.factories.set(type, factory);
    console.log(`[AgentRegistry] Factory registered for type: ${type}`);
  }

  /**
   * Agent 생성 및 등록
   */
  createAgent(config: AgentConfig): IAgent {
    const factory = this.factories.get(config.type);
    if (!factory) {
      throw new Error(`No factory registered for agent type: ${config.type}`);
    }

    const agent = factory.create(config);

    // 전역 이벤트 핸들러 연결
    this.globalEventHandlers.forEach((handler) => {
      agent.on('state_changed', handler);
      agent.on('ticket_created', handler);
      agent.on('approval_requested', handler);
      agent.on('log', handler);
    });

    this.agents.set(agent.id, agent);
    console.log(`[AgentRegistry] Agent created: ${agent.name} (${agent.id})`);

    return agent;
  }

  /**
   * Agent 직접 등록
   */
  registerAgent(agent: IAgent): void {
    this.globalEventHandlers.forEach((handler) => {
      agent.on('state_changed', handler);
      agent.on('ticket_created', handler);
      agent.on('approval_requested', handler);
      agent.on('log', handler);
    });

    this.agents.set(agent.id, agent);
    console.log(`[AgentRegistry] Agent registered: ${agent.name} (${agent.id})`);
  }

  /**
   * Agent 해제
   */
  async unregisterAgent(agentId: string): Promise<void> {
    const agent = this.agents.get(agentId);
    if (!agent) {
      throw new Error(`Agent not found: ${agentId}`);
    }

    await agent.stop();
    this.agents.delete(agentId);
    console.log(`[AgentRegistry] Agent unregistered: ${agentId}`);
  }

  /**
   * Agent 조회
   */
  getAgent(agentId: string): IAgent | undefined {
    return this.agents.get(agentId);
  }

  /**
   * 모든 Agent 조회
   */
  getAllAgents(): IAgent[] {
    return Array.from(this.agents.values());
  }

  /**
   * 활성 Agent만 조회
   */
  getActiveAgents(): IAgent[] {
    return this.getAllAgents().filter((agent) => agent.isActive());
  }

  /**
   * 타입별 Agent 조회
   */
  getAgentsByType(type: string): IAgent[] {
    return this.getAllAgents().filter((agent) => agent.type === type);
  }

  /**
   * 모든 Agent 상태 조회
   */
  getAllAgentStates(): Agent[] {
    return this.getAllAgents().map((agent) => agent.getState());
  }

  /**
   * 전역 이벤트 핸들러 등록
   */
  onGlobalEvent(handler: AgentEventHandler): void {
    this.globalEventHandlers.add(handler);

    // 기존 Agent들에도 핸들러 연결
    this.agents.forEach((agent) => {
      agent.on('state_changed', handler);
      agent.on('ticket_created', handler);
      agent.on('approval_requested', handler);
      agent.on('log', handler);
    });
  }

  /**
   * Agent 상태 업데이트
   */
  async updateAgentState(agentId: string, update: Partial<AgentStateUpdate>): Promise<void> {
    const agent = this.agents.get(agentId);
    if (!agent) {
      throw new Error(`Agent not found: ${agentId}`);
    }

    await agent.updateState(update);
  }

  /**
   * 모든 Agent 일시정지
   */
  async pauseAll(): Promise<void> {
    const promises = this.getAllAgents().map((agent) => agent.pause());
    await Promise.all(promises);
    console.log(`[AgentRegistry] All agents paused`);
  }

  /**
   * 모든 Agent 재개
   */
  async resumeAll(): Promise<void> {
    const promises = this.getAllAgents().map((agent) => agent.resume());
    await Promise.all(promises);
    console.log(`[AgentRegistry] All agents resumed`);
  }

  /**
   * 등록된 Agent 타입 목록
   */
  getAvailableTypes(): string[] {
    return Array.from(this.factories.keys());
  }

  /**
   * 통계
   */
  getStats(): {
    totalAgents: number;
    activeAgents: number;
    byType: Record<string, number>;
  } {
    const agents = this.getAllAgents();
    const byType: Record<string, number> = {};

    agents.forEach((agent) => {
      byType[agent.type] = (byType[agent.type] || 0) + 1;
    });

    return {
      totalAgents: agents.length,
      activeAgents: agents.filter((a) => a.isActive()).length,
      byType,
    };
  }
}

// 싱글톤 인스턴스
export const agentRegistry = new AgentRegistry();
