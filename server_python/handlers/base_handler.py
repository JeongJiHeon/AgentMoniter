"""
BaseHandler - 모든 핸들러의 기본 클래스

공통 의존성과 유틸리티 메서드를 제공합니다.
"""

from typing import Optional, Any
from datetime import datetime


class BaseHandler:
    """WebSocket 메시지 핸들러의 기본 클래스"""

    def __init__(
        self,
        ws_server,
        agent_registry,
        dynamic_orchestration=None,
        orchestration_engine=None,
        workflow_manager=None
    ):
        """
        핸들러 초기화

        Args:
            ws_server: WebSocket 서버 인스턴스
            agent_registry: Agent 레지스트리
            dynamic_orchestration: Dynamic Orchestration 엔진
            orchestration_engine: Orchestration 엔진 (기존)
            workflow_manager: Workflow 매니저
        """
        self.ws_server = ws_server
        self.agent_registry = agent_registry
        self.dynamic_orchestration = dynamic_orchestration
        self.orchestration_engine = orchestration_engine
        self.workflow_manager = workflow_manager

    def log(self, message: str, level: str = "info"):
        """로그 출력"""
        print(f"[{self.__class__.__name__}] {message}")

    def broadcast_notification(self, message: str, notification_type: str = "info"):
        """알림 브로드캐스트"""
        if self.ws_server:
            self.ws_server.broadcast_notification(message, notification_type)

    def broadcast_agent_log(
        self,
        agent_id: str,
        agent_name: str,
        log_type: str,
        message: str,
        details: str = "",
        task_id: Optional[str] = None
    ):
        """Agent 활동 로그 브로드캐스트"""
        if self.ws_server:
            self.ws_server.broadcast_agent_log(
                agent_id=agent_id,
                agent_name=agent_name,
                log_type=log_type,
                message=message,
                details=details,
                task_id=task_id
            )

    def broadcast_agent_update(self, state):
        """Agent 상태 업데이트 브로드캐스트"""
        if self.ws_server:
            self.ws_server.broadcast_agent_update(state)

    def broadcast_task_interaction(
        self,
        task_id: str,
        role: str,
        message: str,
        agent_id: Optional[str] = None,
        agent_name: str = "System"
    ):
        """Task 상호작용 메시지 브로드캐스트"""
        if self.ws_server:
            self.ws_server.broadcast_task_interaction(
                task_id=task_id,
                role=role,
                message=message,
                agent_id=agent_id,
                agent_name=agent_name
            )

    def broadcast_chat_message(
        self,
        role: str,
        content: str,
        agent_id: Optional[str] = None,
        agent_name: str = "System"
    ):
        """Chat 메시지 브로드캐스트"""
        if self.ws_server:
            self.ws_server.broadcast_chat_message(
                role=role,
                content=content,
                agent_id=agent_id,
                agent_name=agent_name
            )

    def broadcast_message(self, message: dict):
        """일반 메시지 브로드캐스트"""
        if self.ws_server:
            self.ws_server.broadcast_message(message)

    def get_agent(self, agent_id: str):
        """Agent 조회"""
        return self.agent_registry.get_agent(agent_id)

    def get_all_agents(self):
        """모든 Agent 조회"""
        return self.agent_registry.get_all_agents()

    def register_agent(self, agent):
        """Agent 등록"""
        self.agent_registry.register_agent(agent)

    def find_orchestration_agent(self):
        """Orchestration Agent 찾기"""
        all_agents = self.get_all_agents()

        for agent in all_agents:
            agent_name_lower = agent.name.lower()
            agent_type_lower = agent.type.lower() if hasattr(agent, 'type') else ''
            state = agent.get_state()

            if ('orchestration' in agent_name_lower or
                'orchestration' in agent_type_lower or
                (hasattr(state, 'description') and state.description and
                 'orchestration' in state.description.lower())):
                return agent

        # 찾지 못한 경우 첫 번째 Agent 반환
        if all_agents:
            return all_agents[0]

        return None

    def get_available_agents_info(self, exclude_agent_id: Optional[str] = None):
        """사용 가능한 Agent 정보 목록 반환"""
        available_agents = []
        for agent in self.get_all_agents():
            if exclude_agent_id and agent.id == exclude_agent_id:
                continue
            agent_state = agent.get_state() if hasattr(agent, 'get_state') else None
            available_agents.append({
                'id': agent.id,
                'name': agent.name,
                'type': agent_state.type if agent_state else 'unknown',
                'description': (agent_state.description
                               if agent_state and hasattr(agent_state, 'description')
                               else agent.name)
            })
        return available_agents
