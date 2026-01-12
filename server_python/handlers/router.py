"""
MessageRouter - WebSocket 메시지 라우팅

메시지 타입에 따라 적절한 핸들러로 라우팅합니다.
"""

from typing import Callable, Optional

from models.websocket import WebSocketMessageType
from .agent_handlers import AgentHandlers
from .approval_handlers import ApprovalHandlers
from .task_handlers import TaskHandlers
from .chat_handlers import ChatHandlers
from .config_handlers import ConfigHandlers


class MessageRouter:
    """WebSocket 메시지 라우터"""

    def __init__(
        self,
        ws_server,
        agent_registry,
        dynamic_orchestration=None,
        orchestration_engine=None,
        workflow_manager=None,
        process_agent_task: Callable = None
    ):
        """
        MessageRouter 초기화

        Args:
            ws_server: WebSocket 서버 인스턴스
            agent_registry: Agent 레지스트리
            dynamic_orchestration: Dynamic Orchestration 엔진
            orchestration_engine: Orchestration 엔진 (기존)
            workflow_manager: Workflow 매니저
            process_agent_task: Agent Task 처리 함수
        """
        # 핸들러 인스턴스 생성
        self.agent_handlers = AgentHandlers(
            ws_server=ws_server,
            agent_registry=agent_registry,
            dynamic_orchestration=dynamic_orchestration,
            orchestration_engine=orchestration_engine,
            workflow_manager=workflow_manager,
            process_agent_task=process_agent_task
        )

        self.approval_handlers = ApprovalHandlers(
            ws_server=ws_server,
            agent_registry=agent_registry
        )

        self.task_handlers = TaskHandlers(
            ws_server=ws_server,
            agent_registry=agent_registry,
            dynamic_orchestration=dynamic_orchestration,
            orchestration_engine=orchestration_engine,
            workflow_manager=workflow_manager
        )

        self.chat_handlers = ChatHandlers(
            ws_server=ws_server,
            agent_registry=agent_registry
        )

        self.config_handlers = ConfigHandlers(
            ws_server=ws_server,
            agent_registry=agent_registry
        )

    async def handle(self, client_id: str, message):
        """
        클라이언트 메시지 처리 (메인 라우팅)

        Args:
            client_id: 클라이언트 ID
            message: WebSocket 메시지
        """
        print(f"[MessageRouter] Client action from {client_id}: {message.type}")

        try:
            if message.type == WebSocketMessageType.ASSIGN_TASK:
                await self.agent_handlers.handle_assign_task(client_id, message.payload)

            elif message.type == WebSocketMessageType.CREATE_AGENT:
                await self.agent_handlers.handle_create_agent(client_id, message.payload)

            elif message.type == WebSocketMessageType.APPROVE_REQUEST:
                await self.approval_handlers.handle_approve_request(client_id, message.payload)

            elif message.type == WebSocketMessageType.REJECT_REQUEST:
                await self.approval_handlers.handle_reject_request(client_id, message.payload)

            elif message.type == WebSocketMessageType.SELECT_OPTION:
                await self.approval_handlers.handle_select_option(client_id, message.payload)

            elif message.type == WebSocketMessageType.TASK_INTERACTION_CLIENT:
                await self.task_handlers.handle_task_interaction(client_id, message.payload)

            elif message.type == WebSocketMessageType.UPDATE_LLM_CONFIG:
                await self.config_handlers.handle_update_llm_config(client_id, message.payload)

            elif message.type == WebSocketMessageType.CHAT_MESSAGE:
                await self.chat_handlers.handle_chat_message(client_id, message.payload)

            else:
                print(f"[MessageRouter] Unknown message type: {message.type}")

        except Exception as e:
            print(f"[MessageRouter] Error handling message: {e}")
            import traceback
            traceback.print_exc()
