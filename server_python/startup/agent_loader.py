"""
AgentLoader - 저장된 Agent 로드

저장소에서 Agent를 로드하고 복원하는 기능을 담당합니다.
"""

from typing import List, Optional
from datetime import datetime


class AgentLoader:
    """Agent 로드 및 복원 클래스"""

    def __init__(self, agent_registry, ws_server=None):
        """
        AgentLoader 초기화

        Args:
            agent_registry: Agent 레지스트리
            ws_server: WebSocket 서버 (Agent에 주입용)
        """
        self.agent_registry = agent_registry
        self.ws_server = ws_server

    async def load_all_agents(self) -> int:
        """
        저장된 모든 Agent 로드

        Returns:
            복원된 Agent 수
        """
        print("\n[AgentLoader] Loading saved agents...")

        # 저장소에서 Agent 로드
        try:
            from utils.agent_storage import load_agents
        except ImportError:
            print("[AgentLoader] agent_storage.py not found (may be migrated to Redis)")
            return 0

        saved_agents = load_agents()
        if not saved_agents:
            print("[AgentLoader] No saved agents found")
            return 0

        print(f"[AgentLoader] Found {len(saved_agents)} saved agents, restoring...")

        restored_count = 0
        for agent_data in saved_agents:
            try:
                agent = await self._restore_agent(agent_data)
                if agent:
                    restored_count += 1
            except Exception as e:
                print(f"[AgentLoader] Error restoring agent {agent_data.get('id')}: {e}")
                import traceback
                traceback.print_exc()

        print(f"[AgentLoader] Restored {restored_count}/{len(saved_agents)} agents successfully")
        return restored_count

    async def _restore_agent(self, agent_data: dict):
        """
        단일 Agent 복원

        Args:
            agent_data: Agent 설정 데이터

        Returns:
            복원된 Agent 인스턴스
        """
        from agents.types import AgentConfig, AgentExecutionContext
        from agents import TaskProcessorAgent
        from models.ontology import OntologyContext

        agent_id = agent_data.get("id")
        config = AgentConfig(
            name=agent_data.get("name"),
            type=agent_data.get("type", "custom"),
            description=agent_data.get("description", ""),
            constraints=agent_data.get("constraints", []),
            permissions=agent_data.get("permissions", {}),
            custom_config=agent_data.get("customConfig", {})
        )

        agent = TaskProcessorAgent(config, agent_id, ws_server=self.ws_server)
        self.agent_registry.register_agent(agent)

        # Agent 초기화
        ontology_context = OntologyContext(
            activePreferences=[],
            activeTaboos=[],
            activeApprovalRules=[],
            matchedFailurePatterns=[],
            appliedConstraints=[]
        )

        context = AgentExecutionContext(
            agent_id=agent.id,
            ontology_context=ontology_context,
            current_ticket=None,
            previous_decisions=[]
        )

        await agent.initialize(context)
        await agent.start()

        print(f"[AgentLoader] Restored agent: {agent.name} ({agent.id})")
        return agent


async def load_saved_agents(agent_registry, ws_server=None) -> int:
    """
    저장된 Agent 로드 (헬퍼 함수)

    Args:
        agent_registry: Agent 레지스트리
        ws_server: WebSocket 서버

    Returns:
        복원된 Agent 수
    """
    loader = AgentLoader(agent_registry, ws_server)
    return await loader.load_all_agents()
