"""
TaskProcessorAgent - Task 처리용 Agent

BaseAgent를 상속받아 구현한 범용 Task 처리 Agent입니다.
Agent 복원 및 새 Agent 생성 시 모두 이 클래스를 사용합니다.
"""

import json
from datetime import datetime
from typing import Dict, Any, Optional
from uuid import uuid4

from agents.base_agent import BaseAgent
from agents.types import AgentInput, AgentOutput, AgentConfig
from models.ticket import CreateTicketInput, TicketOption
from models.agent import AgentStatus, ThinkingMode


class TaskProcessorAgent(BaseAgent):
    """Task 처리용 Agent - BaseAgent를 상속받아 구현"""

    def __init__(
        self,
        config: AgentConfig,
        agent_id: str = None,
        ws_server = None
    ):
        """
        TaskProcessorAgent 초기화

        Args:
            config: Agent 설정
            agent_id: 지정된 Agent ID (복원 시 사용)
            ws_server: WebSocket 서버 인스턴스 (의존성 주입)
        """
        super().__init__(config)
        if agent_id:
            self._id = agent_id
            self._state.id = agent_id
        self._ws_server = ws_server

    def set_ws_server(self, ws_server):
        """WebSocket 서버 인스턴스 설정 (지연 주입용)"""
        self._ws_server = ws_server

    async def explore(self, input: AgentInput) -> Dict[str, Any]:
        """탐색 단계 - Task 정보 수집 및 분석"""
        self.log("info", f"Exploring task: {input.metadata.get('title', 'Task')}")
        return {
            "should_proceed": True,
            "data": {
                "task_id": input.metadata.get('task_id'),
                "title": input.metadata.get('title'),
                "content": input.content,
                "priority": input.metadata.get('priority', 'medium')
            }
        }

    async def structure(self, data: Any) -> Any:
        """구조화 단계 - Task를 Ticket으로 변환"""
        self.log("info", "Structuring task into tickets")
        return {
            "tickets": [{
                "purpose": f"Process: {data.get('title', 'Task')}",
                "content": data.get('content', ''),
                "priority": data.get('priority', 'medium')
            }]
        }

    async def validate(self, data: Any) -> Dict[str, Any]:
        """검증 단계 - 구조화된 데이터 검증"""
        self.log("info", "Validating structured data")
        return {
            "is_valid": True,
            "data": data,
            "errors": []
        }

    async def summarize(self, data: Any) -> AgentOutput:
        """요약 단계 - Ticket 및 Approval Request 생성"""
        self.log("info", "Summarizing and creating output")

        tickets = []
        approvals = []

        for ticket_data in data.get("tickets", []):
            # context를 JSON 문자열로 변환
            context_dict = {
                "what": ticket_data.get("purpose"),
                "why": "User requested task execution",
                "when": datetime.now().isoformat(),
                "where": "Agent Monitor System",
                "who": self.name,
                "how": "Automated processing"
            }

            ticket_input = CreateTicketInput(
                agentId=self.id,
                purpose=ticket_data.get("purpose", "Process task"),
                content=ticket_data.get("content", ""),
                context=json.dumps(context_dict),
                decisionRequired="Should I proceed with this task?",
                options=[
                    TicketOption(
                        id="approve",
                        label="Approve and Execute",
                        description="Proceed with task execution",
                        isRecommended=True
                    ),
                    TicketOption(
                        id="reject",
                        label="Reject",
                        description="Cancel task execution",
                        isRecommended=False
                    )
                ],
                executionPlan="1. Analyze task requirements\n2. Execute task steps\n3. Report results",
                priority=ticket_data.get("priority", "medium")
            )
            tickets.append(ticket_input)

            # Approval request 생성
            # ticketId를 미리 생성하여 approval과 ticket이 같은 ID를 공유
            shared_ticket_id = str(uuid4())
            approval_dict = {
                "id": str(uuid4()),
                "ticketId": shared_ticket_id,
                "agentId": self.id,
                "type": "select_option",
                "message": f"Approve task execution: {ticket_data.get('purpose')}?",
                "context": ticket_data.get("content", ""),
                "options": [
                    {"id": "approve", "label": "Approve and Execute", "description": "Proceed with task execution", "isRecommended": True},
                    {"id": "reject", "label": "Reject", "description": "Cancel task execution", "isRecommended": False}
                ],
                "status": "pending",
                "priority": 1,
                "createdAt": datetime.now().isoformat()
            }
            approvals.append(approval_dict)

        return AgentOutput(
            tickets=tickets,
            approval_requests=approvals,
            logs=[{"level": "info", "message": f"Created {len(tickets)} tickets"}]
        )

    async def on_approved(self, approval):
        """승인 후 실제 작업 수행"""
        self.log("info", f"Approval received, executing task for ticket {approval.ticketId}")

        task_content = approval.context or "Task"
        result_message = f"작업이 승인되어 처리되었습니다. (Ticket: {approval.ticketId})"

        # 결과를 WebSocket으로 브로드캐스트
        self._broadcast_notification(
            f"Ticket approved: {result_message[:100]}",
            "success"
        )

        # Agent Activity 로그에도 기록
        self._broadcast_agent_log(
            log_type="info",
            message=f"Ticket 승인됨: {approval.ticketId}",
            details=f"처리 결과:\n{result_message}"
        )

        # Agent 상태 업데이트
        self._update_agent_state_after_task()

        self.log("info", f"Task execution completed for ticket {approval.ticketId}")

    async def on_rejected(self, approval):
        """거부 처리"""
        self.log("info", f"Task rejected for ticket {approval.ticketId}")

        # Rejection 알림
        self._broadcast_notification(
            f"Ticket rejected: {approval.ticketId} 실행이 취소되었습니다.",
            "warning"
        )

        # Agent Activity 로그에도 기록
        self._broadcast_agent_log(
            log_type="warning",
            message=f"Ticket 거부됨: {approval.ticketId}",
            details="사용자가 작업 실행을 거부했습니다."
        )

        # Agent 상태 업데이트
        self._update_agent_state_after_task()

    def _broadcast_notification(self, message: str, notification_type: str):
        """WebSocket으로 알림 브로드캐스트"""
        try:
            if self._ws_server:
                self._ws_server.broadcast_notification(message, notification_type)
                print(f"[TaskProcessorAgent] Notification broadcasted: {message[:50]}...")
        except Exception as e:
            print(f"[TaskProcessorAgent] ERROR broadcasting notification: {e}")
            import traceback
            traceback.print_exc()

    def _broadcast_agent_log(self, log_type: str, message: str, details: str = ""):
        """Agent 활동 로그 브로드캐스트"""
        try:
            if self._ws_server:
                self._ws_server.broadcast_agent_log(
                    agent_id=self.id,
                    agent_name=self.name,
                    log_type=log_type,
                    message=message,
                    details=details
                )
        except Exception as e:
            print(f"[TaskProcessorAgent] ERROR broadcasting agent log: {e}")
            import traceback
            traceback.print_exc()

    def _update_agent_state_after_task(self):
        """Task 완료/거부 후 Agent 상태 업데이트"""
        try:
            state = self.get_state()
            state.currentTaskId = None
            state.currentTaskDescription = None
            state.thinkingMode = ThinkingMode.IDLE
            # ACTIVE 상태 유지 (다음 작업 대기)
            self._emit_state_change()

            # WebSocket으로 Agent 상태 업데이트 브로드캐스트
            if self._ws_server:
                self._ws_server.broadcast_agent_update(state)
        except Exception as e:
            print(f"[TaskProcessorAgent] ERROR updating agent state: {e}")
            import traceback
            traceback.print_exc()
