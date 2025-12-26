#!/usr/bin/env python3
"""
Agent Monitor 서버 메인 엔트리포인트
"""
import os
import sys

# 🔴 출력 버퍼링 비활성화 (nohup에서 로그 즉시 출력)
sys.stdout.reconfigure(line_buffering=True)
sys.stderr.reconfigure(line_buffering=True)

# 🔴 환경 변수는 반드시 다른 import 전에 로드해야 함!
from dotenv import load_dotenv
load_dotenv()

import asyncio
import json
import signal
from datetime import datetime
from typing import Dict, Optional, List

from agents import agent_registry
from mcp import mcp_registry, NotionService, GmailService, SlackService
from mcp.types import MCPServiceConfig
from websocket import AgentMonitorWebSocketServer
from models.agent import Agent
from models.ticket import Ticket
from models.approval import ApprovalRequest
from models.task import Task
from models.websocket import WebSocketMessageType
from agents.orchestration import (
    call_llm,
    WorkflowStep,
    WorkflowState,
    WorkflowManager,
    OrchestrationEngine,
    build_workflow_steps,
    workflow_manager,
    orchestration_engine
)
from agents.dynamic_orchestration import dynamic_orchestration
from services.slack_webhook import SlackWebhookService
from services.redis_service import redis_service
from services.event_store import event_store
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

# 환경 변수는 파일 상단에서 이미 로드됨

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
        """Task 처리 - LLM 기반 실제 작업 수행"""
        from models.ticket import Ticket, TicketStatus, TicketOption, CreateTicketInput
        from models.approval import ApprovalRequest, ApprovalRequestType
        from agents.types import AgentOutput
        from uuid import uuid4
        from datetime import datetime
        from models.agent import ThinkingMode, AgentStatus

        # AgentInput에서 정보 추출
        task_id = getattr(input_data, 'task_id', None) or input_data.metadata.get('task_id', '')
        task_content = input_data.content
        task_title = input_data.metadata.get('title', '')
        
        print(f"[Agent {self.name}] Processing task: {task_id}")

        # 상태 업데이트: 작업 중
        self._state.thinkingMode = ThinkingMode.EXPLORING
        self._state.currentTaskId = task_id
        self._state.currentTaskDescription = task_title
        self._state.status = AgentStatus.ACTIVE
        self._emit_state_change()

        # LLM을 통한 실제 작업 수행
        agent_description = self._state.description or self.name
        
        messages = [
            {
                "role": "system",
                "content": f"당신은 '{self.name}' Agent입니다. 설명: {agent_description}. 주어진 작업을 수행하고 결과를 보고해주세요."
            },
            {
                "role": "user",
                "content": f"다음 작업을 수행해주세요:\n\n**요청**: {task_content}\n\n이 작업에 대한 결과를 작성해주세요."
            }
        ]
        
        result = await call_llm(messages, max_tokens=500)
        
        print(f"[Agent {self.name}] LLM result: {result[:100]}...")

        # 상태 업데이트: 완료
        self._state.thinkingMode = ThinkingMode.IDLE
        self._state.currentTaskId = None
        self._state.currentTaskDescription = None
        self._state.stats.ticketsCreated += 1
        self._emit_state_change()

        print(f"[Agent {self.name}] Task processing complete!")

        # 승인은 멀티-에이전트 워크플로우에서 관리하므로 여기서는 빈 리스트 반환
        return AgentOutput(
            tickets=[],
            approval_requests=[],
            logs=[{"level": "info", "message": f"Task completed: {task_id}", "result": result}]
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
    """Agent Task 처리 - Dynamic Orchestration 사용"""
    try:
        print(f"[Server] Starting task processing for agent {agent.name}")
        
        # Dynamic Orchestration Engine 초기화
        dynamic_orchestration.set_ws_server(ws_server)
        
        # Agent 상태 업데이트: currentTaskId 설정
        task_id = agent_input.metadata.get('task_id', '')
        task_title = agent_input.metadata.get('title', '')
        task_content = agent_input.content or task_title
        
        # 프론트엔드에서 받은 멀티-에이전트 플랜
        planned_agents = agent_input.metadata.get('planned_agents', [])
        
        # Slack 정보 추출 (있는 경우)
        slack_channel = agent_input.metadata.get('slack_channel')
        slack_ts = agent_input.metadata.get('slack_ts')
        
        # 사용 가능한 Agent 목록 구성
        all_agents = agent_registry.get_all_agents()
        available_agents = [
            {
                "id": ag.id,
                "name": ag.name,
                "type": ag.type if hasattr(ag, 'type') else 'custom'
            }
            for ag in all_agents
        ]
        
        # 프론트엔드에서 받은 planned_agents도 포함
        for pa in planned_agents:
            agent_id = pa.get('agentId')
            if not any(a['id'] == agent_id for a in available_agents):
                available_agents.append({
                    "id": agent_id,
                    "name": pa.get('agentName', f'Agent-{agent_id[:8]}'),
                    "type": "custom"
                })
        
        print(f"[Server] Available agents for orchestration: {[a['name'] for a in available_agents]}")
        
        # =====================================================
        # Dynamic Orchestration으로 요청 처리
        # =====================================================
        print(f"[Server] Starting Dynamic Orchestration for task: {task_title}")
        
        result = await dynamic_orchestration.process_request(
            task_id=task_id,
            request=task_content,
            available_agents=available_agents,
            slack_channel=slack_channel,
            slack_ts=slack_ts
        )
        
        if result is None:
            # 사용자 입력 대기 중
            print(f"[Server] Workflow paused for user input: {task_id}")
            return
        
        print(f"[Server] Dynamic Orchestration completed for task {task_id}")
        return  # 여기서 종료
        
        # =====================================================
        # 단일 Agent 처리 (기존 로직)
        # =====================================================
        
        # 📝 로그: Task 처리 시작
        ws_server.broadcast_agent_log(
            agent_id=agent.id,
            agent_name=agent.name,
            log_type="info",
            message=f"Task 처리 시작: {task_title[:50]}{'...' if len(task_title) > 50 else ''}",
            details=f"Agent: {agent.name}, Task ID: {task_id}",
            task_id=task_id
        )
        
        if hasattr(agent, 'get_state'):
            state = agent.get_state()
            state.currentTaskId = task_id
            state.currentTaskDescription = task_title
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
                
                # 📝 로그: Ticket 생성
                ws_server.broadcast_agent_log(
                    agent_id=agent.id,
                    agent_name=agent.name,
                    log_type="info",
                    message=f"Ticket 생성: {ticket.purpose[:50]}{'...' if len(ticket.purpose) > 50 else ''}",
                    details=f"Ticket ID: {ticket.id}, Priority: {ticket.priority}",
                    task_id=task_id
                )
                
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
                    
                    # 📝 로그: Approval 요청 (옵션 있음)
                    ws_server.broadcast_agent_log(
                        agent_id=agent.id,
                        agent_name=agent.name,
                        log_type="decision",
                        message=f"승인 요청: {approval.message[:50]}{'...' if len(approval.message) > 50 else ''}",
                        details=f"Type: {approval.type}, Options: {len(approval.options) if approval.options else 0}개",
                        task_id=task_id
                    )
                    
                    ws_server.broadcast_approval_request(approval)
                    broadcasted_approval = True
                    # 티켓은 생성하되, 티켓 목록에는 추가하지 않음 (승인 대기에서만 표시)
                else:
                    # 옵션이 없는 경우: 티켓 목록에 추가
                    print(f"[Server] Broadcasting ticket_created (no options): {ticket.id}")
                    
                    # 📝 로그: Ticket 브로드캐스트
                    ws_server.broadcast_agent_log(
                        agent_id=agent.id,
                        agent_name=agent.name,
                        log_type="info",
                        message=f"Ticket 대기 중: {ticket.purpose[:50]}{'...' if len(ticket.purpose) > 50 else ''}",
                        details=f"승인 대기 상태로 전환됨",
                        task_id=task_id
                    )
                    
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
        
        # 📝 로그: Task 처리 완료
        ws_server.broadcast_agent_log(
            agent_id=agent.id,
            agent_name=agent.name,
            log_type="info",
            message=f"Task 처리 완료: {task_title[:50]}{'...' if len(task_title) > 50 else ''}",
            details=f"Tickets: {len(tickets)}, Approvals: {len(approvals)}",
            task_id=task_id
        )
        
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
        
        # 📝 로그: Task 처리 에러
        ws_server.broadcast_agent_log(
            agent_id=agent.id,
            agent_name=agent.name,
            log_type="error",
            message=f"Task 처리 중 오류 발생: {str(e)[:50]}{'...' if len(str(e)) > 50 else ''}",
            details=traceback.format_exc(),
            task_id=task_id if 'task_id' in locals() else None
        )
        
        # 에러 발생 시 Agent 상태 리셋
        if hasattr(agent, 'get_state'):
            state = agent.get_state()
            state.currentTaskId = None
            state.currentTaskDescription = None
            if hasattr(agent, '_emit_state_change'):
                agent._emit_state_change()


async def main():
    global answer_agent, question_agent

    print("=" * 50)
    print("Agent Monitor Server Starting...")
    print("=" * 50)

    # 0. Initialize Redis
    print("\n[0/5] Initializing Redis...")
    try:
        await redis_service.connect()
        is_healthy = await redis_service.health_check()
        if is_healthy:
            print("✅ Redis connected and healthy")
        else:
            print("⚠️  Redis connection established but health check failed")
    except Exception as e:
        print(f"❌ Redis connection failed: {e}")
        print("⚠️  Server will continue without Redis (limited functionality)")

    # 1. 저장된 Agent 로드 (Legacy - will be migrated to Redis)
    print("\n[1/5] Loading saved agents...")
    try:
        from utils.agent_storage import load_agents
    except ImportError:
        print("⚠️  agent_storage.py not found (already migrated to Redis)")
        load_agents = lambda: []

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
                task_content = approval.context or "Task"
                result_message = f"작업이 승인되어 처리되었습니다. (Ticket: {approval.ticketId})"
                
                # 결과를 WebSocket으로 브로드캐스트 (task_interaction 타입으로)
                # Approval 응답은 System Notification으로 전송 (Task Chat 혼동 방지)
                try:
                    if ws_server:
                        ws_server.broadcast_notification(
                            f"Ticket approved: {result_message[:100]}",
                            "success"
                        )
                        # Agent Activity 로그에도 기록
                        ws_server.broadcast_agent_log(
                            agent_id=self.id,
                            agent_name=self.name,
                            log_type="info",
                            message=f"Ticket 승인됨: {approval.ticketId}",
                            details=f"처리 결과:\n{result_message}"
                        )
                        print(f"[Server] Approval result broadcasted as notification and logged")
                except (NameError, Exception) as e:
                    print(f"[Server] ERROR broadcasting approval notification: {e}")
                    import traceback
                    traceback.print_exc()
                
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
                
                # Rejection 응답도 System Notification으로 전송
                try:
                    if ws_server:
                        ws_server.broadcast_notification(
                            f"Ticket rejected: {approval.ticketId} 실행이 취소되었습니다.",
                            "warning"
                        )
                        # Agent Activity 로그에도 기록
                        ws_server.broadcast_agent_log(
                            agent_id=self.id,
                            agent_name=self.name,
                            log_type="warning",
                            message=f"Ticket 거부됨: {approval.ticketId}",
                            details="사용자가 작업 실행을 거부했습니다."
                        )
                        print(f"[Server] Rejection broadcasted as notification and logged")
                except (NameError, Exception) as e:
                    print(f"[Server] ERROR broadcasting rejection notification: {e}")
                    import traceback
                    traceback.print_exc()
                
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
    
    # Orchestration Engine에 WebSocket 서버 참조 설정 (서버 시작 후 설정됨)
    print("\n[0.5/4] Orchestration Engine initialized (Question/Answer Agents are virtual)")
    
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
            
            # 🆕 멀티-에이전트 플랜 (프론트엔드 OrchestrationService에서 생성)
            orchestration_plan = payload.get('orchestrationPlan', {})
            planned_agents = orchestration_plan.get('agents', [])
            needs_user_input = orchestration_plan.get('needsUserInput', False)
            input_prompt = orchestration_plan.get('inputPrompt', '')

            print(f"[Server] Assigning task {task_id} to agent {agent_id}")
            if planned_agents:
                print(f"[Server] Multi-agent plan: {[a.get('agentName') for a in planned_agents]}")

            # Agent 조회 - 실제 등록된 Agent만 사용
            agent = agent_registry.get_agent(agent_id)
            if not agent:
                print(f"[Server] Agent {agent_id} not found in registry, auto-creating...")
                
                # planned_agents에서 해당 Agent 정보 찾기
                agent_info = None
                for pa in planned_agents:
                    if pa.get('agentId') == agent_id:
                        agent_info = pa
                        break
                
                if agent_info:
                    agent_name = agent_info.get('agentName', f'Agent-{agent_id[:8]}')
                    print(f"[Server] Auto-creating agent: {agent_name} ({agent_id})")
                    
                    # Agent 자동 생성 (GenericAgent 사용)
                    from agents.generic_agent import GenericAgent
                    from agents.types import AgentConfig
                    
                    config = AgentConfig(
                        name=agent_name,
                        type='custom',
                        description=f'Auto-created agent for task: {task_data.get("title", "Unknown")}',
                        constraints=[],
                        capabilities=['general'],
                    )
                    
                    agent = GenericAgent(config)
                    # Agent ID를 프론트엔드에서 보낸 ID로 설정
                    agent._id = agent_id
                    agent._state.id = agent_id
                    agent_registry.register_agent(agent)
                    
                    # WebSocket으로 Agent 업데이트 브로드캐스트
                    if ws_server:
                        ws_server.broadcast_agent_update(agent.get_state())
                    
                    print(f"[Server] Agent {agent_name} auto-created and registered")
                else:
                    print(f"[Server] ERROR: Agent {agent_id} not found in planned_agents either")
                    print(f"[Server] Available agents: {[a.id for a in agent_registry.get_all_agents()]}")
                    # WebSocket으로 에러 메시지 전송
                    if ws_server:
                        ws_server.broadcast_notification(
                            f"Agent {agent_id} not found. Please create the agent first.",
                            "error"
                        )
                    return

            print(f"[Server] Found/Created agent: {agent.name} ({agent.id})")

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
                        'tags': task_data.get('tags', []),
                        # 🆕 멀티-에이전트 플랜 정보
                        'orchestration_plan': orchestration_plan,
                        'planned_agents': planned_agents,
                        'needs_user_input': needs_user_input,
                        'input_prompt': input_prompt,
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
                        task_content = approval.context or "Task"
                        result_message = f"작업이 승인되어 처리되었습니다. (Ticket: {approval.ticketId})"
                        
                        # 결과를 WebSocket으로 브로드캐스트 (챗봇 메시지로)
                        # Approval 응답은 System Notification으로 전송
                        try:
                            if ws_server:
                                ws_server.broadcast_notification(
                                    f"Agent created and approved: {result_message[:100]}",
                                    "success"
                                )
                                # Agent Activity 로그에도 기록
                                ws_server.broadcast_agent_log(
                                    agent_id=self.id,
                                    agent_name=self.name,
                                    log_type="info",
                                    message=f"Agent 생성 승인됨: {approval.ticketId}",
                                    details=f"처리 결과:\n{result_message}"
                                )
                                print(f"[Server] Agent creation approval broadcasted as notification and logged")
                        except (NameError, Exception) as e:
                            print(f"[Server] ERROR broadcasting agent creation notification: {e}")
                            import traceback
                            traceback.print_exc()
                        
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
                        
                        # Rejection 응답도 System Notification으로 전송
                        try:
                            if ws_server:
                                ws_server.broadcast_notification(
                                    f"Agent creation rejected: Ticket {approval.ticketId} 실행이 취소되었습니다.",
                                    "warning"
                                )
                                # Agent Activity 로그에도 기록
                                ws_server.broadcast_agent_log(
                                    agent_id=self.id,
                                    agent_name=self.name,
                                    log_type="warning",
                                    message=f"Agent 생성 거부됨: {approval.ticketId}",
                                    details="사용자가 Agent 생성을 거부했습니다."
                                )
                                print(f"[Server] Agent creation rejection broadcasted as notification and logged")
                        except (NameError, Exception) as e:
                            print(f"[Server] ERROR broadcasting rejection notification: {e}")
                            import traceback
                            traceback.print_exc()
                        
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
        
        elif message.type == WebSocketMessageType.TASK_INTERACTION_CLIENT:
            # Task 상호작용 메시지 처리 (사용자가 Chat에서 메시지 전송)
            payload = message.payload
            task_id = payload.get('taskId')
            user_message = payload.get('message')
            role = payload.get('role', 'user')
            
            print(f"[Server] Processing task_interaction: taskId={task_id}, role={role}, message={user_message[:50]}...")
            
            # =====================================================
            # Dynamic Orchestration에서 대기 중인 워크플로우 확인
            # =====================================================
            if dynamic_orchestration.has_pending_workflow(task_id):
                print(f"[Server] Found pending dynamic workflow for task {task_id}, resuming...")
                
                # Dynamic Orchestration 초기화
                dynamic_orchestration.set_ws_server(ws_server)
                
                # 사용자 입력으로 워크플로우 재개
                result = await dynamic_orchestration.resume_with_user_input(task_id, user_message)
                
                if result is None:
                    # 또 다른 사용자 입력 대기 중
                    print(f"[Server] Workflow paused again for user input: {task_id}")
                    return
                
                # 워크플로우 완료
                workflow = dynamic_orchestration.get_workflow(task_id)
                if workflow:
                    ws_server.broadcast_agent_log(
                        agent_id="orchestrator-system",
                        agent_name="Orchestration Agent",
                        log_type="info",
                        message="🎉 워크플로우 완료",
                        details=f"사용자 입력: {user_message}",
                        task_id=task_id
                    )
                
                # 완료된 워크플로우 정리
                dynamic_orchestration.remove_workflow(task_id)
                
                print(f"[Server] Dynamic workflow completed for task {task_id}")
                return  # 워크플로우 처리 완료
            
            # 기존 workflow_manager 확인 (하위 호환성)
            if await workflow_manager.has_pending_workflow(task_id):
                print(f"[Server] Found pending workflow for task {task_id}, resuming...")
                
                # Orchestration Engine 초기화
                orchestration_engine.set_ws_server(ws_server)
                
                # resume_workflow로 중앙 실행 루프 재개
                result = await orchestration_engine.resume_workflow(task_id, user_message)
                
                if result is None:
                    # 또 다른 사용자 입력 대기 중
                    print(f"[Server] Workflow paused again for user input: {task_id}")
                    return
                
                # 워크플로우 완료
                workflow = await workflow_manager.get_workflow(task_id)
                if workflow:
                    ws_server.broadcast_agent_log(
                        agent_id=workflow.steps[-1].agent_id if workflow.steps else "system",
                        agent_name=workflow.steps[-1].agent_name if workflow.steps else "System",
                        log_type="info",
                        message="🎉 워크플로우 완료",
                        details=f"사용자 입력: {user_message}",
                        task_id=task_id
                    )
                
                # 완료된 워크플로우 정리
                await workflow_manager.remove_workflow(task_id)
                
                print(f"[Server] Workflow completed for task {task_id}")
                return  # 워크플로우 처리 완료
            
            # =====================================================
            # 일반 메시지 처리 (워크플로우 없음)
            # =====================================================
            
            # Orchestration Agent 찾기
            orchestration_agent = None
            all_agents = agent_registry.get_all_agents()
            
            # Orchestration Agent 찾기: name이나 type에 "orchestration"이 포함된 경우
            for agent in all_agents:
                agent_name_lower = agent.name.lower()
                agent_type_lower = agent.type.lower() if hasattr(agent, 'type') else ''
                state = agent.get_state()
                
                # name이나 type에 "orchestration"이 포함되어 있거나, description에 포함된 경우
                if ('orchestration' in agent_name_lower or 
                    'orchestration' in agent_type_lower or
                    (hasattr(state, 'description') and state.description and 'orchestration' in state.description.lower())):
                    orchestration_agent = agent
                    break
            
            # Orchestration Agent를 찾지 못한 경우, 첫 번째 활성 Agent를 사용하거나 새로 생성
            if not orchestration_agent:
                print(f"[Server] WARNING: Orchestration Agent not found, using first available agent")
                if len(all_agents) > 0:
                    orchestration_agent = all_agents[0]
                    print(f"[Server] Using first available agent: {orchestration_agent.name} ({orchestration_agent.id})")
                else:
                    print(f"[Server] ERROR: No agents available")
                    if ws_server:
                        ws_server.broadcast_task_interaction(
                            task_id=task_id,
                            role='system',
                            message=f"사용 가능한 Agent가 없습니다. 먼저 Agent를 생성해주세요.",
                            agent_id=None,
                            agent_name="System"
                        )
                    return
            
            print(f"[Server] Using Orchestration Agent: {orchestration_agent.name} ({orchestration_agent.id})")
            
            # Agent 로그: Task 처리 시작
            if ws_server:
                ws_server.broadcast_agent_log(
                    agent_id=orchestration_agent.id,
                    agent_name=orchestration_agent.name,
                    log_type='info',
                    message=f"Task 처리 시작: {user_message[:50]}...",
                    details=f"Task ID: {task_id}\n전체 메시지: {user_message}",
                    task_id=task_id
                )
            
            # 🆕 MULTI-AGENT ORCHESTRATION: Step-by-Step 순차 실행
            try:
                user_message_lower = user_message.lower()
                
                # Agent 로그: Planning 시작
                if ws_server:
                    ws_server.broadcast_agent_log(
                        agent_id=orchestration_agent.id,
                        agent_name=orchestration_agent.name,
                        log_type='info',
                        message="🔍 Planning: 요청 분석 및 실행 계획 수립 중...",
                        details=f"요청: {user_message}",
                        task_id=task_id
                    )
                
                # =====================================================
                # STEP 1: 프론트엔드에 Agent 선택 요청
                # 프론트엔드의 OrchestrationService가 LLM을 사용하여 Agent 선택
                # =====================================================
                available_agents = []
                for ag in all_agents:
                    if ag.id == orchestration_agent.id:
                        continue
                    agent_state = ag.get_state() if hasattr(ag, 'get_state') else None
                    available_agents.append({
                        'id': ag.id,
                        'name': ag.name,
                        'type': agent_state.type if agent_state else 'unknown',
                        'description': agent_state.description if agent_state and hasattr(agent_state, 'description') else ag.name
                    })
                
                # 프론트엔드에 Agent 선택 요청 (비동기)
                if ws_server:
                    ws_server.broadcast_message({
                        'type': 'request_agent_selection',
                        'payload': {
                            'task_id': task_id,
                            'user_message': user_message,
                            'available_agents': available_agents
                        }
                    })
                
                # 현재는 빈 execution_plan (프론트엔드에서 재호출 시 처리)
                execution_plan = []
                
                # =====================================================
                # STEP 2: 실행 계획 로그
                # =====================================================
                if execution_plan:
                    plan_details = "\n".join([
                        f"  Step {i+1}: {item['agent'].name} ({item['description']})"
                        for i, item in enumerate(execution_plan)
                    ])
                    if ws_server:
                        ws_server.broadcast_agent_log(
                            agent_id=orchestration_agent.id,
                            agent_name=orchestration_agent.name,
                            log_type='decision',
                            message=f"📋 실행 계획 수립 완료 ({len(execution_plan)}개 Agent)",
                            details=f"실행 순서:\n{plan_details}",
                            task_id=task_id
                        )
                    print(f"[Server] Execution plan: {len(execution_plan)} agents")
                else:
                    if ws_server:
                        ws_server.broadcast_agent_log(
                            agent_id=orchestration_agent.id,
                            agent_name=orchestration_agent.name,
                            log_type='info',
                            message="일반 질문으로 판단",
                            details="Specialist Agent 없이 Answer Agent가 직접 답변합니다.",
                            task_id=task_id
                        )
                
                # =====================================================
                # STEP 3: 순차 실행 (Step-by-Step)
                # =====================================================
                agent_results = []
                
                for step_num, plan_item in enumerate(execution_plan, 1):
                    specialist = plan_item['agent']
                    task_desc = plan_item['description']
                    
                    # Agent 작업 시작 로그
                    if ws_server:
                        ws_server.broadcast_agent_log(
                            agent_id=specialist.id,
                            agent_name=specialist.name,
                            log_type='info',
                            message=f"🔧 작업 시작: {task_desc}",
                            details=f"Step {step_num}/{len(execution_plan)}",
                            task_id=task_id
                        )
                    
                    # 🆕 실제 LLM 호출로 Agent 작업 수행
                    prev_results_text = ""
                    if agent_results:
                        prev_results_text = "\n\n이전 작업 결과:\n" + "\n".join([
                            f"- {r['agent']}: {r['result']}" for r in agent_results
                        ])
                    
                    agent_messages = [
                        {
                            "role": "system",
                            "content": f"당신은 '{specialist.name}'입니다. {specialist.description if hasattr(specialist, 'description') else ''}\n주어진 작업을 수행하고 결과를 간결하게 요약해주세요."
                        },
                        {
                            "role": "user",
                            "content": f"""다음 작업을 수행해주세요:

**사용자 요청**: {user_message}
**담당 작업**: {task_desc}
{prev_results_text}

작업을 수행하고 결과를 간결하게 응답해주세요."""
                        }
                    ]
                    
                    llm_result = await call_llm(agent_messages, max_tokens=500)
                    
                    # 디버그: LLM 결과 로깅
                    print(f"[Server] LLM result for {specialist.name}: {llm_result[:100] if llm_result else 'None'}...")
                    
                    # 결과 저장 - LLM 결과가 있으면 사용, 없으면 기본 메시지
                    if llm_result and 'error' not in llm_result.lower():
                        result_text = llm_result
                    else:
                        result_text = f"{task_desc} 작업이 수행되었습니다."
                        print(f"[Server] Using fallback result for {specialist.name} due to LLM error or empty result")
                    
                    result = {
                        'agent': specialist.name,
                        'task': task_desc,
                        'result': result_text
                    }
                    
                    agent_results.append(result)
                    
                    # Agent 작업 완료 로그
                    if ws_server:
                        result_preview = result['result'][:80] + "..." if len(result['result']) > 80 else result['result']
                        ws_server.broadcast_agent_log(
                            agent_id=specialist.id,
                            agent_name=specialist.name,
                            log_type='info',
                            message=f"✅ 작업 완료",
                            details=result_preview,
                            task_id=task_id
                        )
                    
                    print(f"[Server] Step {step_num} completed: {specialist.name} - {result['result'][:50]}...")
                
                # =====================================================
                # STEP 4: Answer Agent - 최종 종합 답변
                # =====================================================
                if ws_server:
                    ws_server.broadcast_agent_log(
                        agent_id="answer-agent-system",
                        agent_name="Answer Agent",
                        log_type='info',
                        message="📝 최종 답변 생성 중...",
                        details=f"종합할 결과: {len(agent_results)}개",
                        task_id=task_id
                    )
                
                # LLM으로 최종 답변 생성
                results_text = ""
                if agent_results:
                    for i, res in enumerate(agent_results, 1):
                        results_text += f"Step {i}. {res['agent']}: {res['result']}\n"
                
                llm_final_messages = [
                    {
                        "role": "system",
                        "content": "당신은 친절한 AI 어시스턴트입니다. 작업 결과를 사용자에게 알기 쉽게 요약해서 전달해주세요. 이모지를 적절히 사용하고, 마크다운 형식으로 응답하세요."
                    },
                    {
                        "role": "user",
                        "content": f"""다음 사용자 요청과 처리 결과를 바탕으로 친절한 응답을 작성해주세요:

**사용자 요청**: {user_message}

**처리 결과**:
{results_text if results_text else "처리된 결과가 없습니다."}

사용자에게 유용하고 친절한 응답을 작성해주세요."""
                    }
                ]
                
                final_answer = await call_llm(llm_final_messages, max_tokens=1000)
                
                if not final_answer or ("LLM" in final_answer and "오류" in final_answer):
                    # LLM 호출 실패 시 기본 메시지
                    if agent_results:
                        final_answer = f"'{user_message}'에 대한 처리가 완료되었습니다. 추가로 도움이 필요하시면 말씀해주세요."
                    else:
                        final_answer = "메시지를 확인했습니다. 어떻게 도와드릴까요?"
                
                # 마지막 실행된 Agent 또는 Orchestration Agent 이름으로 응답
                display_agent = execution_plan[-1]['agent'] if execution_plan else orchestration_agent
                
                # Answer Agent 응답 브로드캐스트
                if ws_server:
                    ws_server.broadcast_task_interaction(
                        task_id=task_id,
                        role='agent',
                        message=final_answer,
                        agent_id=display_agent.id,
                        agent_name=display_agent.name
                    )
                    print(f"[Server] Final response broadcasted for task {task_id}")
                    
                    # 답변 완료 로그
                    ws_server.broadcast_agent_log(
                        agent_id="answer-agent-system",
                        agent_name="Answer Agent",
                        log_type='info',
                        message="✅ 답변 완료",
                        details="사용자에게 최종 답변을 전달했습니다.",
                        task_id=task_id
                    )
                    
                    # Orchestration 완료 로그
                    agent_names = " → ".join([item['agent'].name for item in execution_plan]) if execution_plan else "Direct"
                    ws_server.broadcast_agent_log(
                        agent_id=orchestration_agent.id,
                        agent_name=orchestration_agent.name,
                        log_type='info',
                        message=f"🎉 Task 완료",
                        details=f"실행 흐름: Orchestration → {agent_names} → Answer Agent",
                        task_id=task_id
                    )
                
            except Exception as e:
                print(f"[Server] ERROR processing task_interaction: {e}")
                import traceback
                traceback.print_exc()
                
                # 에러 메시지 브로드캐스트
                if ws_server:
                    ws_server.broadcast_task_interaction(
                        task_id=task_id,
                        role='system',
                        message=f"메시지 처리 중 오류가 발생했습니다: {str(e)}",
                        agent_id=None,
                        agent_name="System"
                    )
        
        elif message.type == WebSocketMessageType.UPDATE_LLM_CONFIG:
            # 🆕 프론트엔드 LLM 설정 동기화
            payload = message.payload
            provider = payload.get('provider')
            model = payload.get('model')
            api_key = payload.get('apiKey')
            base_url = payload.get('baseUrl')
            temperature = payload.get('temperature')
            max_tokens = payload.get('maxTokens')
            
            print(f"[Server] Received LLM config update: provider={provider}, model={model}, baseUrl={base_url}")
            
            # LLMClient 설정 업데이트
            from agents.orchestration import LLMClient
            llm_client = LLMClient()
            updated = llm_client.update_config(
                provider=provider,
                model=model,
                api_key=api_key,
                base_url=base_url,
                temperature=temperature,
                max_tokens=max_tokens
            )
            
            if updated and ws_server:
                ws_server.broadcast_notification(
                    f"LLM 설정이 업데이트되었습니다: {model}",
                    "success"
                )
        
        elif message.type == WebSocketMessageType.CHAT_MESSAGE:
            # 🆕 LLM Chat: Orchestration → Specialist (optional) → Answer Agent
            payload = message.payload
            user_message = payload.get('message')
            
            print(f"[Server] Processing chat_message: {user_message[:50]}...")
            
            # Orchestration Agent 찾기
            orchestration_agent = None
            all_agents = agent_registry.get_all_agents()
            
            for agent in all_agents:
                agent_name_lower = agent.name.lower()
                agent_type_lower = agent.type.lower() if hasattr(agent, 'type') else ''
                state = agent.get_state()
                
                if ('orchestration' in agent_name_lower or 
                    'orchestration' in agent_type_lower or
                    (hasattr(state, 'description') and state.description and 'orchestration' in state.description.lower())):
                    orchestration_agent = agent
                    break
            
            if not orchestration_agent and len(all_agents) > 0:
                orchestration_agent = all_agents[0]
            
            if not orchestration_agent:
                print(f"[Server] ERROR: No agents available for chat")
                if ws_server:
                    ws_server.broadcast_chat_message(
                        role='assistant',
                        content='사용 가능한 Agent가 없습니다. 먼저 Agent를 생성해주세요.',
                        agent_id=None,
                        agent_name="System"
                    )
                return
            
            print(f"[Server] Using Orchestration Agent for LLM chat: {orchestration_agent.name}")
            
            # Orchestration Agent가 메시지 처리 - 프론트엔드에서 LLM 호출
            try:
                # Agent 정보를 프론트엔드로 전달
                available_agents = []
                for ag in all_agents:
                    if ag.id == orchestration_agent.id:
                        continue
                    agent_state = ag.get_state() if hasattr(ag, 'get_state') else None
                    available_agents.append({
                        'id': ag.id,
                        'name': ag.name,
                        'type': agent_state.type if agent_state else 'unknown',
                        'description': agent_state.description if agent_state and hasattr(agent_state, 'description') else ag.name
                    })
                
                # 프론트엔드에 LLM 호출 요청
                if ws_server:
                    ws_server.broadcast_message({
                        'type': 'request_llm_response',
                        'payload': {
                            'user_message': user_message,
                            'available_agents': available_agents,
                            'context': 'chat'
                        }
                    })
                    print(f"[Server] Sent LLM request to frontend for chat")
                    
            except Exception as e:
                print(f"[Server] ERROR processing chat_message: {e}")
                import traceback
                traceback.print_exc()
                
                if ws_server:
                    ws_server.broadcast_chat_message(
                        role='assistant',
                        content=f"메시지 처리 중 오류가 발생했습니다: {str(e)}",
                        agent_id=None,
                        agent_name="System"
                    )

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

