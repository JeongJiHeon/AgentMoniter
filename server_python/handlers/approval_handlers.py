"""
ApprovalHandlers - 승인/거부/옵션선택 관련 핸들러

처리하는 메시지 타입:
- APPROVE_REQUEST
- REJECT_REQUEST
- SELECT_OPTION
"""

from datetime import datetime
from typing import Any

from .base_handler import BaseHandler


class ApprovalHandlers(BaseHandler):
    """승인 관련 메시지 핸들러"""

    async def handle_approve_request(self, client_id: str, payload: dict):
        """승인 요청 처리 (APPROVE_REQUEST)"""
        request_id = payload.get('requestId')
        ticket_id = payload.get('ticketId')
        agent_id = payload.get('agentId')

        self.log(f"Processing approval for request {request_id}, ticket {ticket_id}")

        # Agent 조회
        agent = self.get_agent(agent_id)
        if not agent:
            self.log(f"ERROR: Agent {agent_id} not found")
            return

        # ApprovalRequest 생성
        from models.approval import ApprovalRequest, ApprovalStatus, ApprovalResponse
        approval = ApprovalRequest(
            id=request_id,
            ticketId=ticket_id,
            agentId=agent_id,
            type="proceed",
            message="Approval request",
            status=ApprovalStatus.APPROVED,
            response=ApprovalResponse(
                decision="approve",
                respondedAt=datetime.now()
            )
        )

        # Agent 상태를 ACTIVE로 변경
        from models.agent import AgentStatus
        state = agent.get_state()
        state.status = AgentStatus.ACTIVE
        state.currentTaskId = ticket_id
        state.currentTaskDescription = approval.message or "Approved task"
        agent._emit_state_change()

        # Agent 상태 업데이트 브로드캐스트
        self.broadcast_agent_update(state)
        self.log(f"Agent {agent.name} status updated to ACTIVE after approval")

        # Agent에게 승인 알림
        try:
            if hasattr(agent, 'on_approval_received'):
                await agent.on_approval_received(approval)
        except Exception as e:
            self.log(f"ERROR in on_approval_received: {e}")
            import traceback
            traceback.print_exc()

        # WebSocket으로 승인 완료 브로드캐스트
        self.broadcast_notification(
            f"Ticket {ticket_id} approved. Agent will proceed with execution.",
            "success"
        )

        self.log(f"Approval processed for ticket {ticket_id}")

    async def handle_reject_request(self, client_id: str, payload: dict):
        """거부 요청 처리 (REJECT_REQUEST)"""
        request_id = payload.get('requestId')
        ticket_id = payload.get('ticketId')
        agent_id = payload.get('agentId')

        self.log(f"Processing rejection for request {request_id}, ticket {ticket_id}")

        # Agent 조회
        agent = self.get_agent(agent_id)
        if not agent:
            self.log(f"ERROR: Agent {agent_id} not found")
            return

        # ApprovalRequest 생성
        from models.approval import ApprovalRequest, ApprovalStatus, ApprovalResponse
        approval = ApprovalRequest(
            id=request_id,
            ticketId=ticket_id,
            agentId=agent_id,
            type="proceed",
            message="Approval request",
            status=ApprovalStatus.REJECTED,
            response=ApprovalResponse(
                decision="reject",
                respondedAt=datetime.now()
            )
        )

        # Agent에게 거부 알림
        try:
            if hasattr(agent, 'on_approval_received'):
                await agent.on_approval_received(approval)
        except Exception as e:
            self.log(f"ERROR in on_approval_received (reject): {e}")
            import traceback
            traceback.print_exc()

        # WebSocket으로 거부 완료 브로드캐스트
        self.broadcast_notification(f"Ticket {ticket_id} rejected.", "info")

        self.log(f"Rejection processed for ticket {ticket_id}")

    async def handle_select_option(self, client_id: str, payload: dict):
        """옵션 선택 처리 (SELECT_OPTION)"""
        request_id = payload.get('requestId')
        ticket_id = payload.get('ticketId')
        agent_id = payload.get('agentId')
        option_id = payload.get('optionId')

        self.log(f"Processing option selection {option_id} for request {request_id}, ticket {ticket_id}")

        # Agent 조회
        agent = self.get_agent(agent_id)
        if not agent:
            self.log(f"ERROR: Agent {agent_id} not found")
            return

        # ApprovalRequest 생성
        from models.approval import ApprovalRequest, ApprovalStatus, ApprovalResponse
        approval = ApprovalRequest(
            id=request_id,
            ticketId=ticket_id,
            agentId=agent_id,
            type="proceed",
            message="Approval request",
            status=ApprovalStatus.APPROVED,
            response=ApprovalResponse(
                decision="select",
                selectedOptionId=option_id,
                respondedAt=datetime.now()
            )
        )

        # Agent 상태를 ACTIVE로 변경
        from models.agent import AgentStatus
        state = agent.get_state()
        state.status = AgentStatus.ACTIVE
        state.currentTaskId = ticket_id
        state.currentTaskDescription = approval.message or "Option selected"
        agent._emit_state_change()

        # Agent 상태 업데이트 브로드캐스트
        self.broadcast_agent_update(state)
        self.log(f"Agent {agent.name} status updated to ACTIVE after option selection")

        # Agent에게 승인 알림
        try:
            if hasattr(agent, 'on_approval_received'):
                await agent.on_approval_received(approval)
        except Exception as e:
            self.log(f"ERROR in on_approval_received (select_option): {e}")
            import traceback
            traceback.print_exc()

        # WebSocket으로 옵션 선택 완료 브로드캐스트
        self.broadcast_notification(
            f"Option {option_id} selected for ticket {ticket_id}.",
            "success"
        )

        self.log(f"Option selection processed for ticket {ticket_id}")
