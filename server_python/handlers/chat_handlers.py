"""
ChatHandlers - 채팅 관련 핸들러

처리하는 메시지 타입:
- CHAT_MESSAGE
"""

from .base_handler import BaseHandler


class ChatHandlers(BaseHandler):
    """채팅 관련 메시지 핸들러"""

    async def handle_chat_message(self, client_id: str, payload: dict):
        """채팅 메시지 처리 (CHAT_MESSAGE)"""
        user_message = payload.get('message')

        self.log(f"Processing chat_message: {user_message[:50]}...")

        # Orchestration Agent 찾기
        orchestration_agent = self.find_orchestration_agent()

        if not orchestration_agent:
            self.log("ERROR: No agents available for chat")
            self.broadcast_chat_message(
                role='assistant',
                content='사용 가능한 Agent가 없습니다. 먼저 Agent를 생성해주세요.',
                agent_id=None,
                agent_name="System"
            )
            return

        self.log(f"Using Orchestration Agent for LLM chat: {orchestration_agent.name}")

        try:
            # Agent 정보를 프론트엔드로 전달
            available_agents = self.get_available_agents_info(
                exclude_agent_id=orchestration_agent.id
            )

            # 프론트엔드에 LLM 호출 요청
            self.broadcast_message({
                'type': 'request_llm_response',
                'payload': {
                    'user_message': user_message,
                    'available_agents': available_agents,
                    'context': 'chat'
                }
            })
            self.log("Sent LLM request to frontend for chat")

        except Exception as e:
            self.log(f"ERROR processing chat_message: {e}")
            import traceback
            traceback.print_exc()

            self.broadcast_chat_message(
                role='assistant',
                content=f"메시지 처리 중 오류가 발생했습니다: {str(e)}",
                agent_id=None,
                agent_name="System"
            )
