from typing import Dict, List, Optional
from .types import IAgent, AgentConfig, IAgentFactory, AgentEventHandler
from models.agent import Agent, AgentStateUpdate


class AgentRegistry:
    """
    Agent 레지스트리
    
    모든 Agent 인스턴스를 관리하고 추적합니다.
    - Agent 등록/해제
    - Agent 조회
    - 전역 이벤트 브로드캐스트
    """
    
    def __init__(self):
        self.agents: Dict[str, IAgent] = {}
        self.factories: Dict[str, IAgentFactory] = {}
        self.global_event_handlers: set = set()
    
    def register_factory(self, type: str, factory: IAgentFactory) -> None:
        """Agent 팩토리 등록"""
        self.factories[type] = factory
        print(f"[AgentRegistry] Factory registered for type: {type}")
    
    def create_agent(self, config: AgentConfig) -> IAgent:
        """Agent 생성 및 등록"""
        factory = self.factories.get(config.type)
        if not factory:
            raise ValueError(f"No factory registered for agent type: {config.type}")
        
        agent = factory.create(config)
        
        # 전역 이벤트 핸들러 연결
        for handler in self.global_event_handlers:
            agent.on("state_changed", handler)
            agent.on("ticket_created", handler)
            agent.on("approval_requested", handler)
            agent.on("log", handler)
        
        self.agents[agent.id] = agent
        print(f"[AgentRegistry] Agent created: {agent.name} ({agent.id})")
        
        return agent
    
    def register_agent(self, agent: IAgent) -> None:
        """Agent 직접 등록"""
        for handler in self.global_event_handlers:
            agent.on("state_changed", handler)
            agent.on("ticket_created", handler)
            agent.on("approval_requested", handler)
            agent.on("log", handler)
        
        self.agents[agent.id] = agent
        print(f"[AgentRegistry] Agent registered: {agent.name} ({agent.id})")
    
    async def unregister_agent(self, agent_id: str) -> None:
        """Agent 해제"""
        agent = self.agents.get(agent_id)
        if not agent:
            raise ValueError(f"Agent not found: {agent_id}")
        
        await agent.stop()
        del self.agents[agent_id]
        print(f"[AgentRegistry] Agent unregistered: {agent_id}")
    
    def get_agent(self, agent_id: str) -> Optional[IAgent]:
        """Agent 조회"""
        return self.agents.get(agent_id)
    
    def get_all_agents(self) -> List[IAgent]:
        """모든 Agent 조회"""
        return list(self.agents.values())
    
    def get_active_agents(self) -> List[IAgent]:
        """활성 Agent만 조회"""
        return [agent for agent in self.agents.values() if agent.is_active()]
    
    def get_agents_by_type(self, type: str) -> List[IAgent]:
        """타입별 Agent 조회"""
        return [agent for agent in self.agents.values() if agent.type == type]
    
    def get_all_agent_states(self) -> List[Agent]:
        """모든 Agent 상태 조회"""
        return [agent.get_state() for agent in self.agents.values()]
    
    def on_global_event(self, handler: AgentEventHandler) -> None:
        """전역 이벤트 핸들러 등록"""
        self.global_event_handlers.add(handler)
        
        # 기존 Agent들에도 핸들러 연결
        for agent in self.agents.values():
            agent.on("state_changed", handler)
            agent.on("ticket_created", handler)
            agent.on("approval_requested", handler)
            agent.on("log", handler)
    
    async def update_agent_state(self, agent_id: str, update: AgentStateUpdate) -> None:
        """Agent 상태 업데이트"""
        agent = self.agents.get(agent_id)
        if not agent:
            raise ValueError(f"Agent not found: {agent_id}")
        
        await agent.update_state(update)
    
    async def pause_all(self) -> None:
        """모든 Agent 일시정지"""
        import asyncio
        await asyncio.gather(*[agent.pause() for agent in self.agents.values()])
        print("[AgentRegistry] All agents paused")
    
    async def resume_all(self) -> None:
        """모든 Agent 재개"""
        import asyncio
        await asyncio.gather(*[agent.resume() for agent in self.agents.values()])
        print("[AgentRegistry] All agents resumed")
    
    def get_available_types(self) -> List[str]:
        """등록된 Agent 타입 목록"""
        return list(self.factories.keys())
    
    def get_stats(self) -> Dict[str, any]:
        """통계"""
        agents = self.get_all_agents()
        by_type: Dict[str, int] = {}
        
        for agent in agents:
            by_type[agent.type] = by_type.get(agent.type, 0) + 1
        
        return {
            "totalAgents": len(agents),
            "activeAgents": len([a for a in agents if a.is_active()]),
            "byType": by_type,
        }


# 싱글톤 인스턴스
agent_registry = AgentRegistry()

