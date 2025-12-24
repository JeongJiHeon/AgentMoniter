#!/usr/bin/env python3
"""
Agent Monitor 서버 메인 엔트리포인트
"""
import asyncio
import json
import os
import signal
import sys
from datetime import datetime
from dotenv import load_dotenv

from agents import agent_registry
from mcp import mcp_registry, NotionService, GmailService, SlackService
from mcp.types import MCPServiceConfig
from websocket import AgentMonitorWebSocketServer
from models.agent import Agent
from models.ticket import Ticket
from models.approval import ApprovalRequest
from models.task import Task
from models.websocket import WebSocketMessageType
from services.slack_webhook import SlackWebhookService
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from typing import Optional

# 환경 변수 로드
load_dotenv()

# FastAPI 앱 생성
app = FastAPI(title="Agent Monitor API")

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 프로덕션에서는 특정 도메인으로 제한
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 전역 변수
ws_server: Optional[AgentMonitorWebSocketServer] = None
slack_webhook_service: Optional[SlackWebhookService] = None


# 간단한 데모 Agent 구현
class DemoAgent:
    """데모용 Agent - 기본적인 작업 처리"""

    def __init__(self, config, agent_id=None):
        from uuid import uuid4
        from models.agent import AgentType, AgentStatus, AgentPermissions, AgentStats, ThinkingMode

        self._id = agent_id or str(uuid4())
        self._config = config
        self._event_handlers: Dict[str, set] = {}  # 이벤트 핸들러 저장
        self.context = None  # AgentExecutionContext

        now = datetime.now()
        self._state = Agent(
            id=self._id,
            name=config.name,
            type=AgentType.CUSTOM,
            description=config.description,
            status=AgentStatus.IDLE,
            thinkingMode=ThinkingMode.IDLE,
            constraints=[],
            permissions=AgentPermissions(),
            stats=AgentStats(),
            lastActivity=now,
            createdAt=now,
            updatedAt=now,
        )

    @property
    def id(self):
        return self._id

    @property
    def name(self):
        return self._config.name

    @property
    def type(self):
        return self._config.type

    def get_state(self):
        return self._state

    def get_thinking_mode(self):
        from models.agent import ThinkingMode
        return ThinkingMode(self._state.thinkingMode)

    def is_active(self):
        from models.agent import AgentStatus
        return self._state.status == AgentStatus.ACTIVE

    def on(self, event_type: str, handler):
        """이벤트 핸들러 등록"""
        if event_type not in self._event_handlers:
            self._event_handlers[event_type] = set()
        self._event_handlers[event_type].add(handler)

    def off(self, event_type: str, handler):
        """이벤트 핸들러 해제"""
        if event_type in self._event_handlers:
            self._event_handlers[event_type].discard(handler)

    def emit(self, event):
        """이벤트 발생"""
        handlers = self._event_handlers.get(event.type, set())
        for handler in handlers:
            try:
                handler(event)
            except Exception as e:
                print(f"[DemoAgent] Event handler error: {e}")

    async def initialize(self, context):
        """초기화"""
        self.context = context
        print(f"[DemoAgent {self.name}] Initialized")

    async def start(self):
        """시작"""
        from models.agent import AgentStatus
        self._state.status = AgentStatus.ACTIVE
        self._state.lastActivity = datetime.now()
        self._emit_state_change()
        print(f"[DemoAgent {self.name}] Started")

    async def pause(self):
        """일시정지"""
        from models.agent import AgentStatus
        self._state.status = AgentStatus.PAUSED
        self._emit_state_change()
        print(f"[DemoAgent {self.name}] Paused")

    async def resume(self):
        """재개"""
        from models.agent import AgentStatus
        self._state.status = AgentStatus.ACTIVE
        self._emit_state_change()
        print(f"[DemoAgent {self.name}] Resumed")

    async def stop(self):
        """중지"""
        from models.agent import AgentStatus, ThinkingMode
        self._state.status = AgentStatus.IDLE
        self._state.thinkingMode = ThinkingMode.IDLE
        self._state.currentTaskId = None
        self._state.currentTaskDescription = None
        self._emit_state_change()
        print(f"[DemoAgent {self.name}] Stopped")

    async def on_approval_received(self, approval):
        """승인 처리"""
        from models.approval import ApprovalStatus
        if approval.status == ApprovalStatus.APPROVED:
            self._state.stats.ticketsCompleted += 1
        elif approval.status == ApprovalStatus.REJECTED:
            self._state.stats.ticketsRejected += 1
        self._emit_state_change()
        print(f"[DemoAgent {self.name}] Approval received: {approval.status}")

    async def update_state(self, update):
        """상태 업데이트"""
        from models.agent import AgentStateUpdate
        if update.status:
            self._state.status = update.status
        if update.thinkingMode:
            self._state.thinkingMode = update.thinkingMode
        if update.currentTaskId is not None:
            self._state.currentTaskId = update.currentTaskId
        if update.currentTaskDescription is not None:
            self._state.currentTaskDescription = update.currentTaskDescription
        self._state.updatedAt = datetime.now()
        self._state.lastActivity = datetime.now()
        self._emit_state_change()

    async def process(self, input_data):
        """Task 처리"""
        from models.ticket import Ticket, TicketStatus, TicketOption, CreateTicketInput
        from models.approval import ApprovalRequest, ApprovalRequestType
        from agents.types import AgentOutput
        from uuid import uuid4
        from datetime import datetime

        # AgentInput에서 task_id 추출 (metadata에서 가져오거나 input_data에서 직접)
        task_id = getattr(input_data, 'task_id', None) or input_data.metadata.get('task_id', '')
        print(f"[DemoAgent {self.name}] Processing task: {task_id}")

        # 1. Thinking mode를 exploring으로 변경
        from models.agent import ThinkingMode, AgentStatus
        self._state.thinkingMode = ThinkingMode.EXPLORING
        self._state.currentTaskId = task_id
        self._state.currentTaskDescription = input_data.metadata.get('title', '')
        self._state.status = AgentStatus.ACTIVE
        self._emit_state_change()
        await asyncio.sleep(1)

        # 2. Ticket 생성
        print(f"[DemoAgent {self.name}] Creating ticket...")
        from models.agent import ThinkingMode
        self._state.thinkingMode = ThinkingMode.STRUCTURING
        self._emit_state_change()

        ticket = Ticket(
            id=str(uuid4()),
            agentId=self._id,
            purpose=f"Process: {input_data.metadata.get('title', 'Task')}",
            content=input_data.content,
            context=json.dumps({
                "what": f"Task processing for {input_data.metadata.get('title')}",
                "why": "User requested task execution",
                "when": datetime.now().isoformat(),
                "where": "Agent Monitor System",
                "who": self.name,
                "how": "Automated processing"
            }),
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
            status=TicketStatus.PENDING_APPROVAL,
            priority=input_data.metadata.get('priority', 'medium'),
            createdAt=datetime.now(),
            updatedAt=datetime.now()
        )

        await asyncio.sleep(1)

        # 3. Approval Request 생성
        print(f"[DemoAgent {self.name}] Requesting approval...")
        from models.agent import ThinkingMode
        self._state.thinkingMode = ThinkingMode.VALIDATING
        self._emit_state_change()

        approval = ApprovalRequest(
            id=str(uuid4()),
            ticketId=ticket.id,
            agentId=self._id,
            type=ApprovalRequestType.PROCEED,
            message=f"Approve task execution: {input_data.metadata.get('title')}?",
            context=input_data.content,
            options=ticket.options,
            status="pending",
            priority=1,
            createdAt=datetime.now()
        )

        await asyncio.sleep(1)

        # 4. 완료
        from models.agent import ThinkingMode
        self._state.thinkingMode = ThinkingMode.SUMMARIZING
        self._emit_state_change()
        await asyncio.sleep(1)

        self._state.thinkingMode = ThinkingMode.IDLE
        self._state.currentTaskId = None
        self._state.currentTaskDescription = None
        self._state.stats.ticketsCreated += 1
        self._emit_state_change()

        print(f"[DemoAgent {self.name}] Task processing complete!")

        # AgentOutput 형식으로 반환
        from agents.types import AgentOutput, CreateTicketInput
        ticket_input = CreateTicketInput(
            purpose=ticket.purpose,
            content=ticket.content,
            context=ticket.context,
            decisionRequired=ticket.decisionRequired,
            options=ticket.options,
            executionPlan=ticket.executionPlan,
            priority=ticket.priority,
            requiresApproval=ticket.requiresApproval,
            estimatedDuration=ticket.estimatedDuration,
            dependencies=ticket.dependencies
        )
        
        approval_dict = {
            "id": approval.id,
            "ticketId": approval.ticketId,
            "agentId": approval.agentId,
            "type": approval.type.value if hasattr(approval.type, 'value') else str(approval.type),
            "message": approval.message,
            "context": approval.context,
            "options": [opt.model_dump(mode="json") if hasattr(opt, 'model_dump') else opt for opt in (approval.options or [])],
            "status": approval.status.value if hasattr(approval.status, 'value') else str(approval.status),
            "priority": approval.priority,
            "createdAt": approval.createdAt.isoformat() if hasattr(approval.createdAt, 'isoformat') else str(approval.createdAt)
        }

        return AgentOutput(
            tickets=[ticket_input],
            approval_requests=[approval_dict],
            logs=[{"level": "info", "message": f"Processed task: {task_id}"}]
        )

    def _emit_state_change(self):
        """상태 변경 이벤트 발송"""
        from agents.types import AgentEvent, AgentEventType
        event = AgentEvent(
            type=AgentEventType.STATE_CHANGED,
            payload=self._state.model_dump(mode="json")
        )
        agent_registry._emit_global_event(event)


async def create_demo_agent(config, agent_id=None):
    """데모 Agent 생성"""
    agent = DemoAgent(config, agent_id)
    agent_registry.register_agent(agent)
    return agent


async def process_agent_task(agent, agent_input):
    """Agent Task 처리"""
    try:
        print(f"[Server] Starting task processing for agent {agent.name}")
        
        # Agent 상태 업데이트: currentTaskId 설정
        task_id = agent_input.metadata.get('task_id', '')
        if hasattr(agent, 'get_state'):
            state = agent.get_state()
            state.currentTaskId = task_id
            state.currentTaskDescription = agent_input.metadata.get('title', '')
            if hasattr(agent, '_emit_state_change'):
                agent._emit_state_change()
        
        # Task 처리 실행
        result = await agent.process(agent_input)
        
        print(f"[Server] Agent {agent.name} completed task processing")
        
        # 결과에서 tickets와 approvals 추출하여 이벤트 발생
        # AgentOutput 형식으로 반환되므로 tickets와 approval_requests 속성 사용
        from agents.types import AgentOutput
        if isinstance(result, AgentOutput):
            tickets = result.tickets or []
            approvals = result.approval_requests or []
            print(f"[Server] Result: {len(tickets)} tickets, {len(approvals)} approvals")
        else:
            # 이전 형식 호환성
            tickets = result.get('tickets', []) if isinstance(result, dict) else []
            approvals = result.get('approvals', []) if isinstance(result, dict) else []
            print(f"[Server] Result: {len(tickets)} tickets, {len(approvals)} approvals")
        
        # Tickets와 Approvals 브로드캐스트
        from models.approval import ApprovalRequest, ApprovalRequestType, ApprovalStatus
        from models.ticket import Ticket, TicketStatus
        from uuid import uuid4
        
        # 먼저 approvals를 처리하고, 각 approval에 대응하는 ticket을 찾아서 처리
        processed_ticket_ids = set()  # 이미 처리된 ticket 추적
        broadcasted_approval = False  # 승인 대기 브로드캐스트 여부
        broadcasted_ticket = False  # 티켓 목록 브로드캐스트 여부
        
        # 승인 요청별로 처리
        for idx, approval_dict in enumerate(approvals):
            # ticketId가 비어있으면 새로 생성
            ticket_id = approval_dict.get('ticketId', '')
            if not ticket_id or ticket_id == '':
                ticket_id = str(uuid4())
            
            approval = ApprovalRequest(
                id=approval_dict.get('id', str(uuid4())),
                ticketId=ticket_id,
                agentId=approval_dict.get('agentId', agent.id),
                type=ApprovalRequestType(approval_dict.get('type', 'proceed')),
                message=approval_dict.get('message', ''),
                context=approval_dict.get('context'),
                options=approval_dict.get('options'),
                status=ApprovalStatus(approval_dict.get('status', 'pending')),
                priority=approval_dict.get('priority', 1),
                createdAt=datetime.fromisoformat(approval_dict.get('createdAt')) if isinstance(approval_dict.get('createdAt'), str) else datetime.now()
            )
            
            # 해당하는 ticket_input 찾기 (인덱스로 매칭 또는 purpose/message로 매칭)
            ticket_input = None
            if idx < len(tickets):
                ticket_input = tickets[idx]
            else:
                # 인덱스로 찾지 못한 경우 purpose나 message로 매칭
                for t in tickets:
                    # approval의 message나 purpose와 ticket의 purpose를 비교
                    if (approval.message and t.purpose and approval.message.find(t.purpose) != -1) or \
                       (not approval.message and not t.purpose):
                        ticket_input = t
                        break
            
            # ticket_input을 찾지 못한 경우 첫 번째 ticket 사용
            if not ticket_input and len(tickets) > 0:
                ticket_input = tickets[0]
            
            # 티켓 생성 (ticket_input이 있는 경우)
            if ticket_input:
                ticket = Ticket(
                    id=ticket_id,
                    agentId=agent.id,
                    purpose=ticket_input.purpose,
                    content=ticket_input.content,
                    context=json.dumps(ticket_input.context) if isinstance(ticket_input.context, dict) else (ticket_input.context if isinstance(ticket_input.context, str) else None),
                    decisionRequired=ticket_input.decisionRequired,
                    options=ticket_input.options or [],
                    executionPlan=ticket_input.executionPlan,
                    status=TicketStatus.PENDING_APPROVAL,
                    priority=ticket_input.priority,
                    createdAt=datetime.now(),
                    updatedAt=datetime.now()
                )
                processed_ticket_ids.add(ticket.id)
                
                # 옵션이 있는지 확인 (approval.options 또는 ticket.options)
                has_options = False
                if approval.type == ApprovalRequestType.SELECT_OPTION:
                    has_options = (approval.options and len(approval.options) > 0) or (ticket.options and len(ticket.options) > 0)
                else:
                    has_options = (ticket.options and len(ticket.options) > 0)
                
                print(f"[Server] DEBUG: approval.type={approval.type}, approval.options={approval.options}, ticket.options={ticket.options}, has_options={has_options}")
                
                # 옵션이 있는 경우: 승인 대기에 추가
                if has_options:
                    # approval이 select_option 타입이 아니면 수정
                    if approval.type != ApprovalRequestType.SELECT_OPTION:
                        # approval을 select_option으로 변경
                        approval.type = ApprovalRequestType.SELECT_OPTION
                        if not approval.options or len(approval.options) == 0:
                            # ticket.options를 approval.options로 복사
                            approval.options = [{"id": opt.id, "label": opt.label, "description": opt.description, "isRecommended": opt.isRecommended} for opt in ticket.options] if ticket.options else []
                    
                    print(f"[Server] Broadcasting approval_request (with options): {approval.id}, ticketId: {ticket.id}, options count: {len(approval.options) if approval.options else 0}")
                    ws_server.broadcast_approval_request(approval)
                    broadcasted_approval = True
                    # 티켓은 생성하되, 티켓 목록에는 추가하지 않음 (승인 대기에서만 표시)
                else:
                    # 옵션이 없는 경우: 티켓 목록에 추가
                    print(f"[Server] Broadcasting ticket_created (no options): {ticket.id}")
                    ws_server.broadcast_ticket_created(ticket)
                    broadcasted_ticket = True
            else:
                # ticket_input을 찾지 못한 경우에도 approval_request는 브로드캐스트
                print(f"[Server] Broadcasting approval_request (no matching ticket): {approval.id}")
                ws_server.broadcast_approval_request(approval)
                broadcasted_approval = True
        
        # approvals가 없고 tickets만 있는 경우 처리
        if len(approvals) == 0 and len(tickets) > 0:
            print(f"[Server] No approvals, processing {len(tickets)} tickets directly")
            for ticket_input in tickets:
                ticket = Ticket(
                    id=str(uuid4()),
                    agentId=agent.id,
                    purpose=ticket_input.purpose,
                    content=ticket_input.content,
                    context=json.dumps(ticket_input.context) if isinstance(ticket_input.context, dict) else (ticket_input.context if isinstance(ticket_input.context, str) else None),
                    decisionRequired=ticket_input.decisionRequired,
                    options=ticket_input.options or [],
                    executionPlan=ticket_input.executionPlan,
                    status=TicketStatus.PENDING_APPROVAL,
                    priority=ticket_input.priority,
                    createdAt=datetime.now(),
                    updatedAt=datetime.now()
                )
                # 옵션이 없는 티켓만 티켓 목록에 추가
                if not ticket.options or len(ticket.options) == 0:
                    print(f"[Server] Broadcasting ticket_created (no options, no approvals): {ticket.id}")
                    ws_server.broadcast_ticket_created(ticket)
                    broadcasted_ticket = True
                else:
                    # 옵션이 있는 티켓은 승인 대기에 추가해야 함
                    approval = ApprovalRequest(
                        id=str(uuid4()),
                        ticketId=ticket.id,
                        agentId=agent.id,
                        type=ApprovalRequestType.SELECT_OPTION,
                        message=ticket_input.decisionRequired or "Please select an option",
                        context=ticket_input.content,
                        options=[{"id": opt.id, "label": opt.label, "description": opt.description, "isRecommended": opt.isRecommended} for opt in ticket_input.options] if ticket_input.options else [],
                        status=ApprovalStatus.PENDING,
                        priority=1,
                        createdAt=datetime.now()
                    )
                    print(f"[Server] Broadcasting approval_request (ticket with options, no approvals): {approval.id}, ticketId: {ticket.id}")
                    ws_server.broadcast_approval_request(approval)
                    broadcasted_approval = True
        
        # 둘 중 하나는 반드시 브로드캐스트되었는지 확인
        if not broadcasted_approval and not broadcasted_ticket:
            print(f"[Server] WARNING: No approval or ticket was broadcasted! tickets: {len(tickets)}, approvals: {len(approvals)}")
            # 최소한 티켓이나 승인 요청 중 하나는 브로드캐스트
            if len(tickets) > 0:
                ticket_input = tickets[0]
                ticket = Ticket(
                    id=str(uuid4()),
                    agentId=agent.id,
                    purpose=ticket_input.purpose,
                    content=ticket_input.content,
                    context=json.dumps(ticket_input.context) if isinstance(ticket_input.context, dict) else (ticket_input.context if isinstance(ticket_input.context, str) else None),
                    decisionRequired=ticket_input.decisionRequired,
                    options=ticket_input.options or [],
                    executionPlan=ticket_input.executionPlan,
                    status=TicketStatus.PENDING_APPROVAL,
                    priority=ticket_input.priority,
                    createdAt=datetime.now(),
                    updatedAt=datetime.now()
                )
                if ticket.options and len(ticket.options) > 0:
                    approval = ApprovalRequest(
                        id=str(uuid4()),
                        ticketId=ticket.id,
                        agentId=agent.id,
                        type=ApprovalRequestType.SELECT_OPTION,
                        message=ticket_input.decisionRequired or "Please select an option",
                        context=ticket_input.content,
                        options=[{"id": opt.id, "label": opt.label, "description": opt.description, "isRecommended": opt.isRecommended} for opt in ticket_input.options],
                        status=ApprovalStatus.PENDING,
                        priority=1,
                        createdAt=datetime.now()
                    )
                    print(f"[Server] FALLBACK: Broadcasting approval_request: {approval.id}, ticketId: {ticket.id}")
                    ws_server.broadcast_approval_request(approval)
                else:
                    print(f"[Server] FALLBACK: Broadcasting ticket_created: {ticket.id}")
                    ws_server.broadcast_ticket_created(ticket)
        
        # Agent 상태 업데이트: 작업 완료 후에도 ACTIVE 유지 (다음 작업 대기)
        if hasattr(agent, 'get_state'):
            state = agent.get_state()
            state.currentTaskId = None
            state.currentTaskDescription = None
            # state.status = AgentStatus.IDLE  # 주석 처리: 작업 완료 후에도 ACTIVE 유지
            if hasattr(agent, '_emit_state_change'):
                agent._emit_state_change()
                # Agent 상태 업데이트 브로드캐스트
                if ws_server:
                    ws_server.broadcast_agent_update(state)
        
    except Exception as e:
        print(f"[Server] Error processing agent task: {e}")
        import traceback
        traceback.print_exc()
        
        # 에러 발생 시 Agent 상태 리셋
        if hasattr(agent, 'get_state'):
            state = agent.get_state()
            state.currentTaskId = None
            state.currentTaskDescription = None
            if hasattr(agent, '_emit_state_change'):
                agent._emit_state_change()


async def main():
    print("=" * 50)
    print("Agent Monitor Server Starting...")
    print("=" * 50)
    
    # 0. 저장된 Agent 로드
    print("\n[0/4] Loading saved agents...")
    from utils.agent_storage import load_agents
    from agents.types import AgentConfig, AgentExecutionContext
    from models.ontology import OntologyContext
    
    saved_agents = load_agents()
    if saved_agents:
        print(f"[Server] Found {len(saved_agents)} saved agents, restoring...")
        
        # TaskProcessorAgent 클래스 정의 (나중에 재사용)
        from agents.base_agent import BaseAgent
        from agents.types import AgentInput, AgentOutput
        from models.ticket import CreateTicketInput, TicketOption
        from uuid import uuid4
        from typing import Dict, Any
        
        class TaskProcessorAgent(BaseAgent):
            """Task 처리용 Agent - BaseAgent를 상속받아 구현"""
            
            def __init__(self, config: AgentConfig, agent_id: str = None):
                super().__init__(config)
                if agent_id:
                    self._id = agent_id
                    self._state.id = agent_id

            async def explore(self, input: AgentInput) -> Dict[str, Any]:
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
                self.log("info", "Structuring task into tickets")
                return {
                    "tickets": [{
                        "purpose": f"Process: {data.get('title', 'Task')}",
                        "content": data.get('content', ''),
                        "priority": data.get('priority', 'medium')
                    }]
                }

            async def validate(self, data: Any) -> Dict[str, Any]:
                self.log("info", "Validating structured data")
                return {
                    "is_valid": True,
                    "data": data,
                    "errors": []
                }

            async def summarize(self, data: Any) -> AgentOutput:
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
                    
                    approval_dict = {
                        "id": str(uuid4()),
                        "ticketId": "",
                        "agentId": self.id,
                        "type": "proceed",
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
                
                # 승인된 작업 실행
                # TODO: 실제 작업 로직 구현 (예: LLM 호출, API 호출 등)
                # 현재는 간단한 응답 생성
                task_content = approval.context or "Task"
                result_message = f"""점심 메뉴 추천 결과:

🍽️ 추천 메뉴:
1. 한식: 비빔밥, 김치찌개, 된장찌개
2. 중식: 짜장면, 짬뽕, 탕수육
3. 일식: 초밥, 우동, 돈까스
4. 양식: 파스타, 피자, 스테이크

💡 오늘의 특별 추천: 비빔밥 (건강하고 든든한 한식)

위 메뉴 중에서 선택해주시면 더 자세한 정보를 제공해드리겠습니다!"""
                
                # 결과를 WebSocket으로 브로드캐스트 (챗봇 메시지로)
                # ws_server는 main 함수의 로컬 변수로 클로저로 캡처됨
                try:
                    if ws_server:
                        from websocket.websocket_server import WebSocketMessage
                        from models.websocket import WebSocketMessageType
                        ws_server._broadcast(WebSocketMessage(
                            type=WebSocketMessageType.AGENT_RESPONSE,
                            payload={
                                "agentId": self.id,
                                "agentName": self.name,
                                "ticketId": approval.ticketId,
                                "message": result_message,
                                "timestamp": datetime.now().isoformat()
                            }
                        ))
                except NameError:
                    # ws_server가 아직 초기화되지 않은 경우
                    pass
                
                # Agent 상태 리셋: 작업 완료 후 IDLE 상태로 변경
                # 주의: 작업이 완료되어도 다른 작업이 대기 중일 수 있으므로
                # 즉시 IDLE로 변경하지 않고, 다음 작업이 없을 때만 IDLE로 변경
                from models.agent import AgentStatus, ThinkingMode
                state = self.get_state()
                
                # 현재 작업 완료 처리
                state.currentTaskId = None
                state.currentTaskDescription = None
                state.thinkingMode = ThinkingMode.IDLE
                
                # 다른 대기 중인 작업이 있는지 확인
                # TODO: 대기 중인 작업이 있으면 ACTIVE 유지, 없으면 IDLE로 변경
                # 현재는 작업 완료 후 IDLE로 변경하지 않고 ACTIVE 유지
                # (다음 작업이 바로 할당될 수 있으므로)
                # state.status = AgentStatus.IDLE  # 주석 처리: 작업 완료 후에도 ACTIVE 유지
                
                self._emit_state_change()
                
                # WebSocket으로 Agent 상태 업데이트 브로드캐스트
                try:
                    if ws_server:
                        ws_server.broadcast_agent_update(state)
                except NameError:
                    pass
                
                self.log("info", f"Task execution completed for ticket {approval.ticketId}, agent status maintained")
            
            async def on_rejected(self, approval):
                """거부 처리"""
                self.log("info", f"Task rejected for ticket {approval.ticketId}")
                
                # ws_server는 main 함수의 로컬 변수로 클로저로 캡처됨
                try:
                    if ws_server:
                        from websocket.websocket_server import WebSocketMessage
                        from models.websocket import WebSocketMessageType
                        ws_server._broadcast(WebSocketMessage(
                            type=WebSocketMessageType.AGENT_RESPONSE,
                            payload={
                                "agentId": self.id,
                                "agentName": self.name,
                                "ticketId": approval.ticketId,
                                "message": f"작업이 거부되었습니다. Ticket {approval.ticketId}의 실행이 취소되었습니다.",
                                "timestamp": datetime.now().isoformat()
                            }
                        ))
                except (NameError, Exception) as e:
                    # ws_server가 아직 초기화되지 않은 경우 또는 기타 에러
                    print(f"[Server] ERROR broadcasting rejection response: {e}")
                
                # Agent 상태 리셋: 거부 후에도 ACTIVE 유지 (다음 작업 대기)
                try:
                    from models.agent import AgentStatus, ThinkingMode
                    state = self.get_state()
                    state.currentTaskId = None
                    state.currentTaskDescription = None
                    state.thinkingMode = ThinkingMode.IDLE
                    # state.status = AgentStatus.IDLE  # 주석 처리: 거부 후에도 ACTIVE 유지
                    self._emit_state_change()
                    
                    # WebSocket으로 Agent 상태 업데이트 브로드캐스트
                    try:
                        if ws_server:
                            ws_server.broadcast_agent_update(state)
                    except (NameError, Exception) as e:
                        print(f"[Server] ERROR broadcasting agent update (reject): {e}")
                except Exception as e:
                    print(f"[Server] ERROR resetting agent state (reject): {e}")
                    import traceback
                    traceback.print_exc()
        
        # 저장된 Agent 복원
        restored_count = 0
        for agent_data in saved_agents:
            try:
                agent_id = agent_data.get("id")
                config = AgentConfig(
                    name=agent_data.get("name"),
                    type=agent_data.get("type", "custom"),
                    description=agent_data.get("description", ""),
                    constraints=agent_data.get("constraints", []),
                    permissions=agent_data.get("permissions", {}),
                    custom_config=agent_data.get("customConfig", {})
                )
                
                agent = TaskProcessorAgent(config, agent_id)
                agent_registry.register_agent(agent)
                
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
                
                restored_count += 1
                print(f"[Server] Restored agent: {agent.name} ({agent.id})")
            except Exception as e:
                print(f"[Server] Error restoring agent {agent_data.get('id', 'unknown')}: {e}")
                import traceback
                traceback.print_exc()
        
        print(f"[Server] Restored {restored_count}/{len(saved_agents)} agents successfully")
    else:
        print("[Server] No saved agents found")
    
    # 1. MCP 서비스 등록
    print("\n[1/4] Registering MCP Services...")
    
    notion_service = NotionService(MCPServiceConfig(
        type="notion",
        name="Notion Workspace",
        enabled=True,
        credentials={"apiKey": os.getenv("NOTION_API_KEY", "demo-key")}
    ))
    
    gmail_service = GmailService(MCPServiceConfig(
        type="gmail",
        name="Gmail Account",
        enabled=True
    ))
    
    slack_service = SlackService(MCPServiceConfig(
        type="slack",
        name="Slack Workspace",
        enabled=True,
        credentials={
            "accessToken": os.getenv("SLACK_BOT_TOKEN", ""),
            "webhookUrl": os.getenv("SLACK_WEBHOOK_URL", "")
        }
    ))
    
    mcp_registry.register(notion_service, MCPServiceConfig(
        type="notion",
        name="Notion Workspace",
        enabled=True
    ))
    
    mcp_registry.register(gmail_service, MCPServiceConfig(
        type="gmail",
        name="Gmail Account",
        enabled=True
    ))
    
    mcp_registry.register(slack_service, MCPServiceConfig(
        type="slack",
        name="Slack Workspace",
        enabled=True
    ))
    
    status = mcp_registry.get_status()
    print(f"  - Registered: {status['total']} services")
    
    # 2. WebSocket 서버 시작
    print("\n[2/4] Starting WebSocket Server...")
    
    ws_port = int(os.getenv("WS_PORT", "8080"))
    global ws_server
    ws_server = AgentMonitorWebSocketServer(ws_port)
    
    # Slack 웹훅 서비스 초기화
    global slack_webhook_service
    slack_webhook_service = SlackWebhookService(
        signing_secret=os.getenv("SLACK_SIGNING_SECRET")
    )
    
    # Task 생성 핸들러 등록
    def handle_task_created(task: Task):
        """Task 생성 시 WebSocket으로 브로드캐스트"""
        print(f"[Server] Task created from Slack: {task.title}")
        ws_server.broadcast_task_created(task)
    
    slack_webhook_service.on_task_created(handle_task_created)
    
    # FastAPI 라우터 등록
    from api.slack_webhook import router as slack_router, set_slack_webhook_service
    set_slack_webhook_service(slack_webhook_service)
    app.include_router(slack_router)
    
    # Agent 이벤트를 WebSocket으로 브로드캐스트
    def handle_agent_event(event):
        """Agent 이벤트 핸들러"""
        if event.type == "state_changed":
            if event.payload and isinstance(event.payload, dict) and "id" in event.payload:
                # Agent 상태 업데이트
                try:
                    agent = Agent(**event.payload)
                    ws_server.broadcast_agent_update(agent)
                except Exception as e:
                    print(f"[Server] Failed to broadcast agent update: {e}")
        elif event.type == "ticket_created":
            if event.payload:
                try:
                    ticket = Ticket(**event.payload) if isinstance(event.payload, dict) else event.payload
                    ws_server.broadcast_ticket_created(ticket)
                except Exception as e:
                    print(f"[Server] Failed to broadcast ticket created: {e}")
        elif event.type == "approval_requested":
            if event.payload:
                try:
                    approval = ApprovalRequest(**event.payload) if isinstance(event.payload, dict) else event.payload
                    ws_server.broadcast_approval_request(approval)
                except Exception as e:
                    print(f"[Server] Failed to broadcast approval request: {e}")
        elif event.type == "log":
            # 로그는 브로드캐스트하지 않음 (필요시 추가)
            pass
    
    agent_registry.on_global_event(handle_agent_event)

    # 클라이언트 액션 처리
    async def handle_client_action(client_id: str, message):
        """클라이언트 액션 핸들러"""
        print(f"[Server] Client action from {client_id}: {message.type}")

        if message.type == WebSocketMessageType.ASSIGN_TASK:
            # Task를 Agent에게 할당하고 처리 시작
            payload = message.payload
            task_id = payload.get('taskId')
            agent_id = payload.get('agentId')
            task_data = payload.get('task', {})

            print(f"[Server] Assigning task {task_id} to agent {agent_id}")

            # Agent 조회 - 실제 등록된 Agent만 사용
            agent = agent_registry.get_agent(agent_id)
            if not agent:
                print(f"[Server] ERROR: Agent {agent_id} not found in registry")
                print(f"[Server] Available agents: {[a.id for a in agent_registry.get_all_agents()]}")
                # WebSocket으로 에러 메시지 전송
                if ws_server:
                    ws_server.broadcast_notification(
                        f"Agent {agent_id} not found. Please create the agent first.",
                        "error"
                    )
                return

            print(f"[Server] Found agent: {agent.name} ({agent.id})")

            # Agent 초기화 및 시작 (아직 안 된 경우)
            if not hasattr(agent, 'context') or (hasattr(agent, 'context') and agent.context is None):
                print(f"[Server] Initializing agent {agent_id}")
                from agents.types import AgentExecutionContext
                from models.ontology import OntologyContext
                
                # OntologyContext 생성 (기본값 - 빈 리스트들)
                ontology_context = OntologyContext(
                    activePreferences=[],
                    activeTaboos=[],
                    activeApprovalRules=[],
                    matchedFailurePatterns=[],
                    appliedConstraints=[]
                )
                
                context = AgentExecutionContext(
                    agent_id=agent_id,
                    ontology_context=ontology_context,
                    current_ticket=None,
                    previous_decisions=[]
                )
                try:
                    if hasattr(agent, 'initialize'):
                        await agent.initialize(context)
                    if hasattr(agent, 'start'):
                        await agent.start()
                    print(f"[Server] Agent {agent_id} initialized and started")
                except Exception as e:
                    print(f"[Server] Error initializing agent: {e}")
                    import traceback
                    traceback.print_exc()
                    return

            # Agent에게 Task 할당 및 처리 시작
            try:
                from agents.types import AgentInput
                agent_input = AgentInput(
                    type='task',
                    content=task_data.get('description', task_data.get('title', '')),
                    metadata={
                        'task_id': task_id,
                        'title': task_data.get('title'),
                        'priority': task_data.get('priority'),
                        'source': task_data.get('source'),
                        'tags': task_data.get('tags', [])
                    }
                )

                # 비동기로 Agent 처리 시작
                asyncio.create_task(process_agent_task(agent, agent_input))
                print(f"[Server] Started agent task processing for task {task_id}")

            except Exception as e:
                print(f"[Server] Error starting agent task: {e}")
                import traceback
                traceback.print_exc()

        elif message.type == WebSocketMessageType.CREATE_AGENT:
            # Agent 생성 요청 처리
            print(f"[Server] Received CREATE_AGENT message from {client_id}")
            print(f"[Server] Message payload: {message.payload}")
            
            payload = message.payload
            agent_id = payload.get('id')
            agent_name = payload.get('name')
            agent_type = payload.get('type', 'custom')
            description = payload.get('description', '')
            constraints = payload.get('constraints', [])
            permissions = payload.get('permissions', {})
            custom_config = payload.get('customConfig', {})

            if not agent_id or not agent_name:
                print(f"[Server] ERROR: Missing required fields (id or name)")
                if ws_server:
                    ws_server.broadcast_notification(
                        "Agent creation failed: Missing required fields",
                        "error"
                    )
                return

            print(f"[Server] Creating agent: {agent_name} ({agent_id})")

            try:
                from agents.types import AgentConfig
                config = AgentConfig(
                    name=agent_name,
                    type=agent_type,
                    description=description,
                    constraints=constraints,
                    permissions=permissions,
                    custom_config=custom_config
                )

                # BaseAgent를 상속받는 간단한 TaskProcessorAgent 생성
                from agents.base_agent import BaseAgent
                from agents.types import AgentInput, AgentOutput
                from models.ticket import CreateTicketInput, TicketOption
                from uuid import uuid4
                from typing import Dict, Any

                class TaskProcessorAgent(BaseAgent):
                    """Task 처리용 Agent - BaseAgent를 상속받아 구현"""
                    
                    def __init__(self, config: AgentConfig, agent_id: str = None):
                        # BaseAgent 초기화
                        super().__init__(config)
                        # 지정된 ID가 있으면 덮어쓰기
                        if agent_id:
                            self._id = agent_id
                            self._state.id = agent_id

                    async def explore(self, input: AgentInput) -> Dict[str, Any]:
                        """탐색 단계"""
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
                        """구조화 단계"""
                        self.log("info", "Structuring task into tickets")
                        return {
                            "tickets": [{
                                "purpose": f"Process: {data.get('title', 'Task')}",
                                "content": data.get('content', ''),
                                "priority": data.get('priority', 'medium')
                            }]
                        }

                    async def validate(self, data: Any) -> Dict[str, Any]:
                        """검증 단계"""
                        self.log("info", "Validating structured data")
                        return {
                            "is_valid": True,
                            "data": data,
                            "errors": []
                        }

                    async def on_approved(self, approval):
                        """승인 후 실제 작업 수행"""
                        self.log("info", f"Approval received, executing task for ticket {approval.ticketId}")
                        
                        # 승인된 작업 실행
                        # TODO: 실제 작업 로직 구현 (예: LLM 호출, API 호출 등)
                        # 현재는 간단한 응답 생성
                        task_content = approval.context or "Task"
                        result_message = f"""점심 메뉴 추천 결과:

🍽️ 추천 메뉴:
1. 한식: 비빔밥, 김치찌개, 된장찌개
2. 중식: 짜장면, 짬뽕, 탕수육
3. 일식: 초밥, 우동, 돈까스
4. 양식: 파스타, 피자, 스테이크

💡 오늘의 특별 추천: 비빔밥 (건강하고 든든한 한식)

위 메뉴 중에서 선택해주시면 더 자세한 정보를 제공해드리겠습니다!"""
                        
                        # 결과를 WebSocket으로 브로드캐스트 (챗봇 메시지로)
                        # ws_server는 main 함수의 로컬 변수로 클로저로 캡처됨
                        try:
                            if ws_server:
                                from websocket.websocket_server import WebSocketMessage
                                from models.websocket import WebSocketMessageType
                                ws_server._broadcast(WebSocketMessage(
                                    type=WebSocketMessageType.AGENT_RESPONSE,
                                    payload={
                                        "agentId": self.id,
                                        "agentName": self.name,
                                        "ticketId": approval.ticketId,
                                        "message": result_message,
                                        "timestamp": datetime.now().isoformat()
                                    }
                                ))
                        except (NameError, Exception) as e:
                            # ws_server가 아직 초기화되지 않은 경우 또는 기타 에러
                            print(f"[Server] ERROR broadcasting agent response (CREATE_AGENT): {e}")
                        
                        # Agent 상태 리셋: 작업 완료 후에도 ACTIVE 유지 (다음 작업 대기)
                        try:
                            from models.agent import AgentStatus, ThinkingMode
                            state = self.get_state()
                            state.currentTaskId = None
                            state.currentTaskDescription = None
                            state.thinkingMode = ThinkingMode.IDLE
                            # state.status = AgentStatus.IDLE  # 주석 처리: 작업 완료 후에도 ACTIVE 유지
                            self._emit_state_change()
                            
                            # WebSocket으로 Agent 상태 업데이트 브로드캐스트
                            try:
                                if ws_server:
                                    ws_server.broadcast_agent_update(state)
                            except (NameError, Exception) as e:
                                print(f"[Server] ERROR broadcasting agent update (CREATE_AGENT): {e}")
                        except Exception as e:
                            print(f"[Server] ERROR resetting agent state (CREATE_AGENT): {e}")
                            import traceback
                            traceback.print_exc()
                        
                        self.log("info", f"Task execution completed for ticket {approval.ticketId}, agent status maintained")
                    
                    async def on_rejected(self, approval):
                        """거부 처리"""
                        self.log("info", f"Task rejected for ticket {approval.ticketId}")
                        
                        # ws_server는 main 함수의 로컬 변수로 클로저로 캡처됨
                        try:
                            if ws_server:
                                from websocket.websocket_server import WebSocketMessage
                                from models.websocket import WebSocketMessageType
                                ws_server._broadcast(WebSocketMessage(
                                    type=WebSocketMessageType.AGENT_RESPONSE,
                                    payload={
                                        "agentId": self.id,
                                        "agentName": self.name,
                                        "ticketId": approval.ticketId,
                                        "message": f"작업이 거부되었습니다. Ticket {approval.ticketId}의 실행이 취소되었습니다.",
                                        "timestamp": datetime.now().isoformat()
                                    }
                                ))
                        except (NameError, Exception) as e:
                            # ws_server가 아직 초기화되지 않은 경우 또는 기타 에러
                            print(f"[Server] ERROR broadcasting rejection response (CREATE_AGENT): {e}")
                        
                        # Agent 상태 리셋: 거부 후에도 ACTIVE 유지 (다음 작업 대기)
                        try:
                            from models.agent import AgentStatus, ThinkingMode
                            state = self.get_state()
                            state.currentTaskId = None
                            state.currentTaskDescription = None
                            state.thinkingMode = ThinkingMode.IDLE
                            # state.status = AgentStatus.IDLE  # 주석 처리: 거부 후에도 ACTIVE 유지
                            self._emit_state_change()
                            
                            # WebSocket으로 Agent 상태 업데이트 브로드캐스트
                            try:
                                if ws_server:
                                    ws_server.broadcast_agent_update(state)
                            except (NameError, Exception) as e:
                                print(f"[Server] ERROR broadcasting agent update (CREATE_AGENT reject): {e}")
                        except Exception as e:
                            print(f"[Server] ERROR resetting agent state (CREATE_AGENT reject): {e}")
                            import traceback
                            traceback.print_exc()
                    
                    async def summarize(self, data: Any) -> AgentOutput:
                        """요약 단계"""
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
                            # 옵션이 있는 티켓이므로 select_option 타입으로 생성
                            # ticketId를 미리 생성하여 approval과 ticket이 같은 ID를 공유하도록 함
                            shared_ticket_id = str(uuid4())
                            approval_dict = {
                                "id": str(uuid4()),
                                "ticketId": shared_ticket_id,  # Ticket ID를 미리 생성하여 공유
                                "agentId": self.id,
                                "type": "select_option",  # 옵션이 있으므로 select_option 타입
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

                # Agent 생성
                agent = TaskProcessorAgent(config, agent_id)
                
                # Agent 등록
                agent_registry.register_agent(agent)
                
                # Agent 초기화 및 시작
                from agents.types import AgentExecutionContext
                from models.ontology import OntologyContext
                
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
                
                # Agent 등록 확인
                registered_agent = agent_registry.get_agent(agent.id)
                if registered_agent:
                    print(f"[Server] Agent successfully registered: {agent.name} ({agent.id})")
                    print(f"[Server] Total agents in registry: {len(agent_registry.get_all_agents())}")
                else:
                    print(f"[Server] WARNING: Agent registered but not found in registry!")
                
                # Agent 저장
                from utils.agent_storage import save_agent_config
                try:
                    save_agent_config(agent.id, config, agent.get_state().model_dump(mode="json") if hasattr(agent.get_state(), 'model_dump') else None)
                except Exception as e:
                    print(f"[Server] Warning: Failed to save agent to storage: {e}")
                
                # WebSocket으로 Agent 업데이트 브로드캐스트
                ws_server.broadcast_agent_update(agent.get_state())
                
                print(f"[Server] Agent created and registered: {agent.name} ({agent.id})")
                
            except Exception as e:
                print(f"[Server] Error creating agent: {e}")
                import traceback
                traceback.print_exc()
                if ws_server:
                    ws_server.broadcast_notification(
                        f"Failed to create agent: {str(e)}",
                        "error"
                    )

        elif message.type == WebSocketMessageType.APPROVE_REQUEST:
            # 승인 요청 처리
            payload = message.payload
            request_id = payload.get('requestId')
            ticket_id = payload.get('ticketId')
            agent_id = payload.get('agentId')
            
            print(f"[Server] Processing approval for request {request_id}, ticket {ticket_id}")
            
            # Agent 조회
            agent = agent_registry.get_agent(agent_id)
            if not agent:
                print(f"[Server] ERROR: Agent {agent_id} not found")
                return
            
            # ApprovalRequest 찾기 (임시로 생성 - 실제로는 저장소에서 조회해야 함)
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
            
            # Agent 상태를 ACTIVE로 변경 (승인 후 작업 시작)
            from models.agent import AgentStatus
            state = agent.get_state()
            state.status = AgentStatus.ACTIVE
            state.currentTaskId = ticket_id
            state.currentTaskDescription = approval.message or "Approved task"
            agent._emit_state_change()
            
            # Agent 상태 업데이트 브로드캐스트
            if ws_server:
                ws_server.broadcast_agent_update(state)
                print(f"[Server] Agent {agent.name} status updated to ACTIVE after approval")
            
            # Agent에게 승인 알림
            try:
                if hasattr(agent, 'on_approval_received'):
                    await agent.on_approval_received(approval)
            except Exception as e:
                print(f"[Server] ERROR in on_approval_received: {e}")
                import traceback
                traceback.print_exc()
            
            # Ticket 상태 업데이트
            # TODO: Ticket 저장소에서 조회하여 상태 업데이트
            
            # WebSocket으로 승인 완료 브로드캐스트
            try:
                if ws_server:
                    ws_server.broadcast_notification(
                        f"Ticket {ticket_id} approved. Agent will proceed with execution.",
                        "success"
                    )
            except Exception as e:
                print(f"[Server] ERROR broadcasting approval notification: {e}")
            
            print(f"[Server] Approval processed for ticket {ticket_id}")
        
        elif message.type == WebSocketMessageType.REJECT_REQUEST:
            # 거부 요청 처리
            payload = message.payload
            request_id = payload.get('requestId')
            ticket_id = payload.get('ticketId')
            agent_id = payload.get('agentId')
            
            print(f"[Server] Processing rejection for request {request_id}, ticket {ticket_id}")
            
            # Agent 조회
            agent = agent_registry.get_agent(agent_id)
            if not agent:
                print(f"[Server] ERROR: Agent {agent_id} not found")
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
                print(f"[Server] ERROR in on_approval_received (reject): {e}")
                import traceback
                traceback.print_exc()
            
            # WebSocket으로 거부 완료 브로드캐스트
            try:
                if ws_server:
                    ws_server.broadcast_notification(
                        f"Ticket {ticket_id} rejected.",
                        "info"
                    )
            except Exception as e:
                print(f"[Server] ERROR broadcasting rejection notification: {e}")
            
            print(f"[Server] Rejection processed for ticket {ticket_id}")
        
        elif message.type == WebSocketMessageType.SELECT_OPTION:
            # 옵션 선택 처리
            payload = message.payload
            request_id = payload.get('requestId')
            ticket_id = payload.get('ticketId')
            agent_id = payload.get('agentId')
            option_id = payload.get('optionId')
            
            print(f"[Server] Processing option selection {option_id} for request {request_id}, ticket {ticket_id}")
            
            # Agent 조회
            agent = agent_registry.get_agent(agent_id)
            if not agent:
                print(f"[Server] ERROR: Agent {agent_id} not found")
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
            
            # Agent 상태를 ACTIVE로 변경 (옵션 선택 후 작업 시작)
            from models.agent import AgentStatus
            state = agent.get_state()
            state.status = AgentStatus.ACTIVE
            state.currentTaskId = ticket_id
            state.currentTaskDescription = approval.message or "Option selected"
            agent._emit_state_change()
            
            # Agent 상태 업데이트 브로드캐스트
            if ws_server:
                ws_server.broadcast_agent_update(state)
                print(f"[Server] Agent {agent.name} status updated to ACTIVE after option selection")
            
            # Agent에게 승인 알림
            try:
                if hasattr(agent, 'on_approval_received'):
                    await agent.on_approval_received(approval)
            except Exception as e:
                print(f"[Server] ERROR in on_approval_received (select_option): {e}")
                import traceback
                traceback.print_exc()
            
            # WebSocket으로 옵션 선택 완료 브로드캐스트
            try:
                if ws_server:
                    ws_server.broadcast_notification(
                        f"Option {option_id} selected for ticket {ticket_id}.",
                        "success"
                    )
            except Exception as e:
                print(f"[Server] ERROR broadcasting option selection notification: {e}")
            
            print(f"[Server] Option selection processed for ticket {ticket_id}")

        # TODO: 다른 액션 처리 구현
        # - pause_agent -> agent_registry.update_agent_state()

    ws_server.on_client_action = handle_client_action
    
    await ws_server.start()
    print(f"  - WebSocket server running on port {ws_port}")
    
    # HTTP 서버 시작 (별도 태스크로 실행)
    http_port = int(os.getenv("HTTP_PORT", "8000"))
    config = uvicorn.Config(app, host="0.0.0.0", port=http_port, log_level="info")
    server = uvicorn.Server(config)
    asyncio.create_task(server.serve())
    print(f"  - HTTP server running on port {http_port}")
    print(f"  - Slack webhook: http://localhost:{http_port}/api/slack/webhook")
    
    # 3. 초기화 완료
    print("\n[3/3] Server Ready!")
    print("=" * 50)
    print("Agent Monitor Server is running")
    print(f"WebSocket: ws://localhost:{ws_port}")
    print(f"HTTP API: http://localhost:{http_port}")
    print(f"Slack Webhook: http://localhost:{http_port}/api/slack/webhook")
    print("=" * 50)
    
    # Graceful shutdown
    def signal_handler(sig, frame):
        print("\nShutting down...")
        asyncio.create_task(ws_server.stop())
        asyncio.create_task(mcp_registry.disconnect_all())
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # 서버 실행 유지
    try:
        await asyncio.Future()  # 무한 대기
    except KeyboardInterrupt:
        print("\nShutting down...")
        await ws_server.stop()
        await mcp_registry.disconnect_all()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nServer stopped")
    except Exception as error:
        print(f"Failed to start server: {error}")
        sys.exit(1)

