#!/usr/bin/env python3
"""
Dynamic Orchestration Engine

사용자 요청에 따라 동적으로 워크플로우를 생성하고 실행합니다.

플로우 예시:
"점심메뉴 추천해주고 근처 식당을 예약해줘"

Orchestration → 점심 메뉴 Agent (작업만 수행, 사용자에게 표시 안 됨)
→ Orchestration → Q&A Agent (메뉴 선택 질문, 사용자에게 표시)
→ Orchestration → 장소 예약 Agent (작업만 수행, 사용자에게 표시 안 됨)
→ Orchestration → Q&A Agent (예약 확인 질문, 사용자에게 표시)
→ Orchestration → Q&A Agent (최종 응답, 사용자에게 표시)
"""

import asyncio
import json
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from uuid import uuid4

from .orchestration import call_llm, LLMClient
from .agent_result import (
    AgentResult,
    AgentLifecycleStatus,
    waiting_user,
    completed,
    failed,
    running
)
from .planner_agent import planner_agent, PlannerContext, PlannerResult
from .conversation_state import ConversationStateV3
from .task_schema import (
    TaskSchema,
    TaskSchemaRegistry,
    NextAction,
    NextActionType,
    create_initial_state_v3
)
from .extractors import extract_and_update_state
from .task_state import (
    TaskStateManager,
    TaskStatus,
    AgentExecutionStatus,
    task_state_manager
)

# MCP Agents (Background Workers)
from .notion_mcp_agent import NotionMCPAgent, notion_mcp_agent
from .slack_mcp_agent import SlackMCPAgent, slack_mcp_agent


# =============================================================================
# Enums & Types
# =============================================================================

class AgentRole(str, Enum):
    """Agent 역할"""
    ORCHESTRATOR = "orchestrator"      # 워크플로우 조율
    WORKER = "worker"                  # 작업 실행 (사용자와 직접 소통하지 않음)
    Q_AND_A = "q_and_a"                # 사용자와 소통하는 Q&A Agent (질문/답변 통합)


class WorkflowPhase(str, Enum):
    """워크플로우 단계"""
    ANALYZING = "analyzing"            # 요청 분석 중
    EXECUTING = "executing"            # Agent 실행 중
    WAITING_USER = "waiting_user"      # 사용자 입력 대기
    COMPLETING = "completing"          # 완료 처리 중
    FINALIZING = "finalizing"          # 최종 정리 중 (Orchestrator Final Narration)
    COMPLETED = "completed"            # 완료
    FAILED = "failed"                  # 실패


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class AgentStep:
    """단일 Agent 실행 단계"""
    id: str
    agent_id: str
    agent_name: str
    agent_role: AgentRole
    description: str
    order: int
    status: str = "pending"  # pending, running, waiting_user, completed, failed
    result: Optional[str] = None
    data: Optional[Dict[str, Any]] = None
    user_input: Optional[str] = None
    user_prompt: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


@dataclass
class DynamicWorkflow:
    """동적 워크플로우 상태"""
    task_id: str
    original_request: str
    phase: WorkflowPhase = WorkflowPhase.ANALYZING
    steps: List[AgentStep] = field(default_factory=list)
    current_step_index: int = 0
    context: Dict[str, Any] = field(default_factory=dict)  # Agent 간 공유 데이터
    # Schema 기반 상태 관리
    conversation_state: Optional[ConversationStateV3] = None  # 도메인 중립적 상태
    task_schema: Optional[TaskSchema] = None  # 업무별 로직 정의
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    
    def add_step(self, step: AgentStep) -> None:
        """스텝 추가"""
        self.steps.append(step)
        self.updated_at = datetime.now()
    
    def get_current_step(self) -> Optional[AgentStep]:
        """현재 스텝 반환"""
        if 0 <= self.current_step_index < len(self.steps):
            return self.steps[self.current_step_index]
        return None
    
    def advance(self) -> bool:
        """다음 스텝으로 진행"""
        if self.current_step_index < len(self.steps) - 1:
            self.current_step_index += 1
            self.updated_at = datetime.now()
            return True
        return False
    
    def get_completed_results(self) -> List[Dict[str, Any]]:
        """완료된 스텝 결과들"""
        return [
            {
                "agent_name": s.agent_name,
                "agent_role": s.agent_role,
                "description": s.description,
                "result": s.result,
                "data": s.data,
                "user_input": s.user_input
            }
            for s in self.steps
            if s.status == "completed"
        ]


# =============================================================================
# Dynamic Orchestration Engine
# =============================================================================

class DynamicOrchestrationEngine:
    """
    동적 오케스트레이션 엔진
    
    각 Agent 실행 후 Orchestration이 다음 단계를 결정합니다.
    """
    
    def __init__(self):
        self._workflows: Dict[str, DynamicWorkflow] = {}
        self._locks: Dict[str, asyncio.Lock] = {}
        self._global_lock = asyncio.Lock()
        self.ws_server: Any = None
        self.task_state_manager = task_state_manager

        # MCP Agent 인스턴스 (백그라운드 Worker)
        self._mcp_agents: Dict[str, Any] = {
            "notion-mcp": notion_mcp_agent,
            "slack-mcp": slack_mcp_agent,
        }

        # 시스템 Agent 정의
        self.system_agents = {
            "orchestrator": {
                "id": "orchestrator-system",
                "name": "Orchestration Agent",
                "role": AgentRole.ORCHESTRATOR
            },
            "planner": {
                "id": "planner-agent",
                "name": "Planner Agent",
                "role": AgentRole.ORCHESTRATOR
            },
            "q_and_a": {
                "id": "qa-agent-system",
                "name": "Q&A Agent",
                "role": AgentRole.Q_AND_A
            },
            # MCP Agents (Background Workers)
            "notion-mcp": {
                "id": "notion-mcp-agent",
                "name": "Notion MCP Agent",
                "role": AgentRole.WORKER
            },
            "slack-mcp": {
                "id": "slack-mcp-agent",
                "name": "Slack MCP Agent",
                "role": AgentRole.WORKER
            }
        }

        # 시스템 Agent 등록
        for agent_key, agent_info in self.system_agents.items():
            self.task_state_manager.register_agent(
                agent_id=agent_info["id"],
                agent_name=agent_info["name"]
            )

    def set_ws_server(self, ws_server: Any) -> None:
        """WebSocket 서버 설정 및 이벤트 핸들러 연결"""
        self.ws_server = ws_server
        self._setup_event_handlers()

    def configure_notion_agent(self, api_key: str) -> bool:
        """
        Notion MCP Agent 설정

        Args:
            api_key: Notion Integration API Key

        Returns:
            설정 성공 여부
        """
        try:
            notion_agent = self._mcp_agents.get("notion-mcp")
            if notion_agent:
                notion_agent.configure(api_key)
                print(f"[DynamicOrchestration] Notion MCP Agent configured")
                return True
            return False
        except Exception as e:
            print(f"[DynamicOrchestration] Failed to configure Notion Agent: {e}")
            return False

    def configure_slack_agent(
        self,
        bot_token: str = None,
        webhook_url: str = None
    ) -> bool:
        """
        Slack MCP Agent 설정

        Args:
            bot_token: Slack Bot OAuth Token
            webhook_url: Slack Webhook URL

        Returns:
            설정 성공 여부
        """
        try:
            slack_agent = self._mcp_agents.get("slack-mcp")
            if slack_agent:
                slack_agent.configure(bot_token, webhook_url)
                print(f"[DynamicOrchestration] Slack MCP Agent configured")
                return True
            return False
        except Exception as e:
            print(f"[DynamicOrchestration] Failed to configure Slack Agent: {e}")
            return False

    def get_mcp_agent(self, agent_type: str) -> Optional[Any]:
        """MCP Agent 인스턴스 조회"""
        return self._mcp_agents.get(agent_type)

    def get_available_mcp_agents(self) -> List[str]:
        """사용 가능한 MCP Agent 타입 목록"""
        return list(self._mcp_agents.keys())

    def _setup_event_handlers(self) -> None:
        """TaskStateManager 이벤트 핸들러 설정"""
        def on_task_status_change(event: Dict[str, Any]) -> None:
            if self.ws_server:
                self.ws_server.broadcast_task_status_change(event)
                # Task 상태 요약도 함께 전송
                summary = self.task_state_manager.get_task_summary()
                self.ws_server.broadcast_task_summary(summary)

        def on_agent_status_change(agent_status: Dict[str, Any]) -> None:
            if self.ws_server:
                self.ws_server.broadcast_agent_status_change(agent_status)
                # Agent 상태 요약도 함께 전송
                summary = self.task_state_manager.get_agent_summary()
                self.ws_server.broadcast_agent_summary(summary)

        self.task_state_manager.set_status_change_handler(on_task_status_change)
        self.task_state_manager.set_agent_change_handler(on_agent_status_change)
    
    def _convert_workflow_to_graph(self, workflow: DynamicWorkflow) -> Dict[str, Any]:
        """
        DynamicWorkflow를 TaskGraph 형식으로 변환
        
        Args:
            workflow: DynamicWorkflow 인스턴스
            
        Returns:
            TaskGraph dict 형식의 데이터
        """
        nodes = {}
        
        # 각 step을 node로 변환
        for step in workflow.steps:
            # 직전 step만 dependency로 설정 (순차 실행)
            dependencies = []
            if step.order > 1:
                # 바로 이전 step만 dependency
                dependencies = [f"step_{step.order - 1}"]
            
            # Status 매핑
            status_map = {
                "pending": "pending",
                "running": "running",
                "waiting_user": "running",  # waiting도 running으로 표시
                "completed": "completed",
                "failed": "failed"
            }
            graph_status = status_map.get(step.status, "pending")
            
            node_id = f"step_{step.order}"
            nodes[node_id] = {
                "id": node_id,
                "name": step.description or f"{step.agent_name} - Step {step.order}",
                "label": step.description or f"{step.agent_name} - Step {step.order}",
                "description": step.description,
                "dependencies": dependencies,
                "status": graph_status,
                "task_type": "agent_step",
                "task_data": {
                    "agent_id": step.agent_id,
                    "agent_name": step.agent_name,
                    "agent_role": step.agent_role.value if hasattr(step.agent_role, 'value') else str(step.agent_role),
                    "order": step.order,
                    "result": step.result,
                },
                "metadata": {
                    "started_at": step.started_at.isoformat() if step.started_at else None,
                    "completed_at": step.completed_at.isoformat() if step.completed_at else None,
                },
                "created_at": workflow.created_at.isoformat(),
            }
        
        graph_data = {
            "name": workflow.original_request[:50] if workflow.original_request else f"Workflow {workflow.task_id}",
            "nodes": nodes,
            "stats": {
                "total_tasks": len(nodes),
                "status_counts": {
                    "pending": sum(1 for n in nodes.values() if n["status"] == "pending"),
                    "running": sum(1 for n in nodes.values() if n["status"] == "running"),
                    "completed": sum(1 for n in nodes.values() if n["status"] == "completed"),
                    "failed": sum(1 for n in nodes.values() if n["status"] == "failed"),
                }
            }
        }
        
        return graph_data
    
    def _update_task_graph(self, task_id: str) -> None:
        """워크플로우를 graph로 변환하여 저장"""
        workflow = self._workflows.get(task_id)
        if not workflow or not self.ws_server:
            return
        
        try:
            graph_data = self._convert_workflow_to_graph(workflow)
            self.ws_server.save_task_graph(task_id, graph_data)
            # 실시간으로 클라이언트에 전송
            self.ws_server.broadcast_task_graph(task_id, graph_data)
        except Exception as e:
            print(f"[DynamicOrchestration] Error updating task graph: {e}")
            import traceback
            traceback.print_exc()
    
    async def _get_lock(self, task_id: str) -> asyncio.Lock:
        """task_id별 Lock 획득"""
        async with self._global_lock:
            if task_id not in self._locks:
                self._locks[task_id] = asyncio.Lock()
            return self._locks[task_id]
    
    # =========================================================================
    # Main Entry Point
    # =========================================================================
    
    async def process_request(
        self,
        task_id: str,
        request: str,
        available_agents: List[Dict[str, Any]],
        slack_channel: Optional[str] = None,
        slack_ts: Optional[str] = None
    ) -> Optional[str]:
        """
        새로운 요청 처리
        
        1. Orchestration이 요청 분석
        2. 초기 Plan 생성
        3. 워크플로우 실행 시작
        """
        lock = await self._get_lock(task_id)
        async with lock:
            # Schema 기반 상태 관리 초기화
            conversation_state = create_initial_state_v3(request)
            task_schema = TaskSchemaRegistry.infer_from_request(request)

            # 워크플로우 생성
            workflow = DynamicWorkflow(
                task_id=task_id,
                original_request=request,
                conversation_state=conversation_state,
                task_schema=task_schema,
                context={
                    "available_agents": available_agents,
                    "slack_channel": slack_channel,
                    "slack_ts": slack_ts
                }
            )
            self._workflows[task_id] = workflow

        # TaskStateManager: Task 실행 시작
        self.task_state_manager.start_execution(task_id=task_id, total_steps=0)

        self._log("orchestrator-system", "Orchestration Agent", "info",
                  f"🎯 새로운 요청 수신: {request[:50]}...", task_id=task_id)
        self._log("orchestrator-system", "Orchestration Agent", "info",
                  f"📋 TaskSchema: {task_schema.task_type}, required_facts={task_schema.required_facts}",
                  task_id=task_id)

        # 1. 요청 분석 및 초기 Plan 생성
        initial_plan = await self._analyze_and_plan(workflow, available_agents)
        
        if not initial_plan:
            self._log("orchestrator-system", "Orchestration Agent", "error",
                      "❌ 요청 분석 실패", task_id=task_id)
            return "요청을 분석할 수 없습니다. 다시 시도해주세요."
        
        # 초기 plan이 생성된 후 graph 업데이트
        self._update_task_graph(task_id)
        
        # 2. 워크플로우 실행
        return await self._execute_workflow(task_id)
    
    async def resume_with_user_input(
        self,
        task_id: str,
        user_input: str
    ) -> Optional[str]:
        """
        사용자 입력으로 워크플로우 재개
        user_input은 진행 트리거일 뿐, 완료 신호가 아님
        AgentResult.status로만 진행 결정
        """
        workflow = self._workflows.get(task_id)
        if not workflow:
            return "워크플로우를 찾을 수 없습니다."
        
        current_step = workflow.get_current_step()
        if not current_step:
            return "현재 진행 중인 단계가 없습니다."
        
        # 사용자 응답을 화면에 표시 (echo back)
        if self.ws_server:
            self.ws_server.broadcast_task_interaction(
                task_id=task_id,
                role='user',
                message=user_input,
                agent_id=None,
                agent_name=None
            )
            print(f"[DynamicOrchestration] 사용자 응답 echo: {user_input[:50]}...")
        
        # 사용자 입력 저장 (Agent 실행 시 context로 전달)
        current_step.user_input = user_input

        # Schema 기반 상태 업데이트 (Fact/Decision 분리 추출)
        if workflow.conversation_state:
            workflow.conversation_state = await extract_and_update_state(
                user_input,
                workflow.conversation_state,
                call_llm_func=call_llm
            )
            self._log(current_step.agent_id, current_step.agent_name, "info",
                      f"📥 사용자 응답 수신: {user_input[:50]}...",
                      details=f"facts: {workflow.conversation_state.facts}, decisions: {workflow.conversation_state.decisions}",
                      task_id=task_id)

        workflow.phase = WorkflowPhase.EXECUTING

        # TaskStateManager: Task 상태를 RUNNING으로, Agent를 RUNNING으로 전환
        self.task_state_manager.update_execution(task_id=task_id, status=TaskStatus.RUNNING)
        execution = self.task_state_manager.get_execution(task_id)
        if execution:
            self.task_state_manager.set_agent_running(
                agent_id=current_step.agent_id,
                agent_name=current_step.agent_name,
                task_id=task_id,
                execution_id=execution.execution_id,
                step_description=current_step.description
            )

        # Agent 실행 (user_input 제공)
        result = await self._execute_agent_step(task_id, current_step, user_input=user_input)

        # AgentResult.status로만 분기
        if result.status == AgentLifecycleStatus.WAITING_USER:
            # Agent가 또 다른 질문 요청 (multi-turn 대화)
            current_step.status = "waiting_user"
            workflow.phase = WorkflowPhase.WAITING_USER

            # TaskStateManager: Task를 WAITING_USER로, Agent를 WAITING으로
            self.task_state_manager.set_waiting_user(task_id)
            self.task_state_manager.update_agent_status(
                agent_id=current_step.agent_id,
                status=AgentExecutionStatus.WAITING,
                current_step="사용자 입력 대기 중"
            )

            # WebSocket으로 질문 전송
            if self.ws_server and result.message:
                self.ws_server.broadcast_task_interaction(
                    task_id=task_id,
                    role='agent',
                    message=result.message,
                    agent_id=current_step.agent_id,
                    agent_name=current_step.agent_name
                )

            self._log(current_step.agent_id, current_step.agent_name, "info",
                      f"❓ 추가 질문: {result.message[:100] if result.message else ''}...",
                      task_id=task_id)

            return None  # advance 금지

        elif result.status == AgentLifecycleStatus.COMPLETED:
            # Agent가 완료 선언
            current_step.status = "completed"
            current_step.result = result.final_data.get("output", result.message) if result.final_data else result.message
            current_step.completed_at = datetime.now()

            # TaskStateManager: completed_steps 증가, Agent를 IDLE로
            execution = self.task_state_manager.get_execution(task_id)
            if execution:
                self.task_state_manager.update_execution(
                    task_id=task_id,
                    completed_steps=execution.completed_steps + 1,
                    status=TaskStatus.RUNNING
                )
            self.task_state_manager.set_agent_idle(current_step.agent_id)

            # 결과를 context에 저장
            if result.final_data:
                workflow.context[f"step_{current_step.order}_result"] = result.final_data
            else:
                workflow.context[f"step_{current_step.order}_result"] = result.message

            self._log(current_step.agent_id, current_step.agent_name, "info",
                      f"✅ 작업 완료",
                      details=(result.message[:100] + "..." if result.message and len(result.message) > 100 else result.message) if result.message else "",
                      task_id=task_id)

            # Task graph 업데이트
            self._update_task_graph(task_id)

            # Q&A Agent의 최종 응답은 사용자에게 표시
            if current_step.agent_role == AgentRole.Q_AND_A and self.ws_server and result.message:
                self.ws_server.broadcast_task_interaction(
                    task_id=task_id,
                    role='agent',
                    message=result.message,
                    agent_id=current_step.agent_id,
                    agent_name=current_step.agent_name
                )

            # 다음 단계로 진행
            return await self._orchestrate_next(task_id)
        
        elif result.status == AgentLifecycleStatus.FAILED:
            # Agent가 실패 선언
            current_step.status = "failed"
            workflow.phase = WorkflowPhase.FAILED

            # TaskStateManager: Agent를 IDLE로, Task를 FAILED로
            self.task_state_manager.set_agent_idle(current_step.agent_id)
            self.task_state_manager.complete_execution(task_id, success=False)

            error_message = result.message or result.error.get("message", "작업 처리 중 오류가 발생했습니다.") if result.error else "작업 처리 중 오류가 발생했습니다."

            self._log(current_step.agent_id, current_step.agent_name, "error",
                      f"❌ 작업 실패: {error_message}",
                      task_id=task_id)

            return error_message

        elif result.status == AgentLifecycleStatus.RUNNING:
            # Agent가 계속 실행 중
            current_step.status = "running"
            return None

        else:
            # 알 수 없는 상태
            current_step.status = "failed"
            workflow.phase = WorkflowPhase.FAILED

            # TaskStateManager: Agent를 IDLE로, Task를 FAILED로
            self.task_state_manager.set_agent_idle(current_step.agent_id)
            self.task_state_manager.complete_execution(task_id, success=False)

            self._log(current_step.agent_id, current_step.agent_name, "error",
                      f"❌ 알 수 없는 Agent 상태: {result.status}",
                      task_id=task_id)
            return "알 수 없는 오류가 발생했습니다."

    # =========================================================================
    # Orchestration Logic
    # =========================================================================
    
    async def _analyze_and_plan(
        self,
        workflow: DynamicWorkflow,
        available_agents: List[Dict[str, Any]],
        reason: str = "initial"
    ) -> Optional[List[Dict[str, Any]]]:
        """
        요청 분석 및 Plan 생성 (PlannerAgent 사용)

        이제 PlannerAgent를 호출하여 계획을 수립합니다.
        """
        workflow.phase = WorkflowPhase.ANALYZING

        self._log("planner-agent", "Planner Agent", "info",
                  f"🎯 Planning 시작 - Reason: {reason}",
                  task_id=workflow.task_id)

        # PlannerAgent 호출
        planner_context = PlannerContext(
            task_id=workflow.task_id,
            user_request=workflow.original_request,
            available_agents=available_agents,
            reason=reason
        )

        planner_result = await planner_agent.run(planner_context)

        if not planner_result.success:
            self._log("planner-agent", "Planner Agent", "error",
                      "❌ Planning 실패",
                      task_id=workflow.task_id)
            return None

        steps = planner_result.steps
        print(f"[DynamicOrchestration] PlannerAgent returned {len(steps)} steps")

        self._log("planner-agent", "Planner Agent", "decision",
                  f"📋 실행 계획 수립: {len(steps)}개 단계 (신뢰도: {planner_result.confidence:.2f})",
                  details=planner_result.analysis,
                  task_id=workflow.task_id)

        # 스텝 생성
        for i, step_data in enumerate(steps):
            # role 매핑 (호환성: question/answer -> q_and_a)
            role_str = step_data.get("role", "worker")
            if role_str in ["question", "answer"]:
                role_str = "q_and_a"

            step = AgentStep(
                id=str(uuid4()),
                agent_id=step_data.get("agent_id", f"agent-{i}"),
                agent_name=step_data.get("agent_name", f"Agent {i+1}"),
                agent_role=AgentRole(role_str),
                description=step_data.get("description", ""),
                order=i + 1,
                user_prompt=step_data.get("user_prompt")
            )
            workflow.add_step(step)

        # 재계획 필요성 저장 (나중에 사용)
        workflow.context["planner_confidence"] = planner_result.confidence
        workflow.context["planner_result"] = planner_result

        # TaskStateManager: total_steps 업데이트
        execution = self.task_state_manager.get_execution(workflow.task_id)
        if execution:
            execution.total_steps = len(steps)

        return steps
    
    async def _check_replan_needed(
        self,
        task_id: str,
        current_result: AgentResult
    ) -> Optional[str]:
        """
        재계획 필요성 확인

        Re-planning 트리거:
        1. Agent 실패
        2. 낮은 신뢰도 (confidence < 0.6)
        3. 사용자 입력 방향 변경 (향후 구현)

        Returns:
            재계획 사유 (재계획 필요 시) 또는 None
        """
        workflow = self._workflows.get(task_id)
        if not workflow:
            return None

        # 1. Agent 실패
        if current_result.status == AgentLifecycleStatus.FAILED:
            return "agent_failure"

        # 2. 낮은 신뢰도
        if current_result.partial_data and isinstance(current_result.partial_data, dict):
            confidence = current_result.partial_data.get("confidence", 1.0)
            if confidence < 0.6:
                return f"low_confidence_{confidence:.2f}"

        # 3. 사용자 입력 방향 변경 (향후 구현)
        # TODO: 사용자 입력이 기존 계획과 상충되는지 확인

        return None

    async def _replan_workflow(
        self,
        task_id: str,
        reason: str
    ) -> bool:
        """
        워크플로우 재계획

        Returns:
            성공 여부
        """
        workflow = self._workflows.get(task_id)
        if not workflow:
            return False

        self._log("planner-agent", "Planner Agent", "warning",
                  f"⚠️ 재계획 트리거 - Reason: {reason}",
                  task_id=task_id)

        # 기존 계획 및 실행 결과 수집
        previous_plan = [
            {
                "agent_id": step.agent_id,
                "agent_name": step.agent_name,
                "description": step.description,
                "status": step.status
            }
            for step in workflow.steps
        ]

        execution_results = []
        for step in workflow.steps:
            if step.status in ["completed", "failed"]:
                # AgentResult 재구성 (저장된 데이터에서)
                result_data = workflow.context.get(f"step_{step.order}_result")
                if result_data:
                    execution_results.append(
                        AgentResult(
                            status=AgentLifecycleStatus.COMPLETED if step.status == "completed" else AgentLifecycleStatus.FAILED,
                            message=step.result if isinstance(step.result, str) else str(step.result),
                            final_data=result_data if isinstance(result_data, dict) else {"output": str(result_data)}
                        )
                    )

        # PlannerAgent 재호출
        planner_context = PlannerContext(
            task_id=task_id,
            user_request=workflow.original_request,
            available_agents=workflow.context.get("available_agents", []),
            previous_plan=previous_plan,
            execution_results=execution_results,
            reason=f"replan: {reason}"
        )

        planner_result = await planner_agent.run(planner_context)

        if not planner_result.success:
            self._log("planner-agent", "Planner Agent", "error",
                      "❌ 재계획 실패",
                      task_id=task_id)
            return False

        # 기존 워크플로우 초기화
        workflow.steps.clear()
        workflow.current_step_index = 0

        # 새로운 스텝 생성
        for i, step_data in enumerate(planner_result.steps):
            role_str = step_data.get("role", "worker")
            if role_str in ["question", "answer"]:
                role_str = "q_and_a"

            step = AgentStep(
                id=str(uuid4()),
                agent_id=step_data.get("agent_id", f"agent-{i}"),
                agent_name=step_data.get("agent_name", f"Agent {i+1}"),
                agent_role=AgentRole(role_str),
                description=step_data.get("description", ""),
                order=i + 1,
                user_prompt=step_data.get("user_prompt")
            )
            workflow.add_step(step)

        self._log("planner-agent", "Planner Agent", "decision",
                  f"🔄 재계획 완료: {len(workflow.steps)}개 단계",
                  details=planner_result.analysis,
                  task_id=task_id)

        return True

    async def _orchestrate_next(self, task_id: str) -> Optional[str]:
        """
        Orchestration이 다음 단계 결정

        현재 결과를 보고 계획대로 진행하거나 수정
        """
        workflow = self._workflows.get(task_id)
        if not workflow:
            return None

        # 다음 스텝으로 진행
        if not workflow.advance():
            # 모든 스텝 완료
            return await self._generate_final_answer(task_id)

        self._log("orchestrator-system", "Orchestration Agent", "info",
                  f"🔄 다음 단계로 진행: Step {workflow.current_step_index + 1}",
                  task_id=task_id)

        return await self._execute_workflow(task_id)
    
    # =========================================================================
    # Workflow Execution
    # =========================================================================
    
    async def _execute_agent_step(
        self,
        task_id: str,
        step: AgentStep,
        user_input: Optional[str] = None
    ) -> AgentResult:
        """
        통일된 Agent 실행 메서드
        Worker/Q&A Agent 구분 없이 동일한 인터페이스로 실행
        """
        if step.agent_role == AgentRole.Q_AND_A:
            return await self._handle_qa_agent_step(task_id, step, user_input)
        else:
            return await self._execute_worker_agent(task_id, step, user_input)
    
    async def _execute_workflow(self, task_id: str) -> Optional[str]:
        """
        워크플로우 실행
        AgentResult.status만 보고 진행 결정 (Orchestrator는 판단하지 않음)
        """
        workflow = self._workflows.get(task_id)
        if not workflow:
            return None
        
        workflow.phase = WorkflowPhase.EXECUTING
        
        while True:
            current_step = workflow.get_current_step()
            if not current_step:
                # 모든 스텝 완료
                return await self._generate_final_answer(task_id)
            
            # 이미 완료된 스텝은 건너뛰기
            if current_step.status == "completed":
                if not workflow.advance():
                    return await self._generate_final_answer(task_id)
                continue
            
            # 스텝 실행
            current_step.status = "running"
            current_step.started_at = datetime.now()
            
            # Task graph 업데이트
            self._update_task_graph(task_id)

            # TaskStateManager: Agent 실행 상태로 설정
            execution = self.task_state_manager.get_execution(task_id)
            if execution:
                self.task_state_manager.set_agent_running(
                    agent_id=current_step.agent_id,
                    agent_name=current_step.agent_name,
                    task_id=task_id,
                    execution_id=execution.execution_id,
                    step_description=current_step.description
                )
                self.task_state_manager.update_execution(
                    task_id=task_id,
                    active_agent_id=current_step.agent_id,
                    active_agent_name=current_step.agent_name,
                    current_step=current_step.description
                )

            self._log(current_step.agent_id, current_step.agent_name, "info",
                      f"🔧 작업 시작: {current_step.description}",
                      details=f"Step {current_step.order}/{len(workflow.steps)}",
                      task_id=task_id)

            # 통일된 Agent 실행 (Worker/Q&A 구분 없음)
            result = await self._execute_agent_step(task_id, current_step)
            
            # AgentResult.status만 보고 진행 결정
            if result.status == AgentLifecycleStatus.WAITING_USER:
                # Agent가 사용자 입력 대기 요청
                current_step.status = "waiting_user"
                current_step.user_input = None  # 아직 입력 없음
                workflow.phase = WorkflowPhase.WAITING_USER

                # TaskStateManager: Task를 WAITING_USER로, Agent를 WAITING으로 설정
                self.task_state_manager.set_waiting_user(task_id)
                self.task_state_manager.update_agent_status(
                    agent_id=current_step.agent_id,
                    status=AgentExecutionStatus.WAITING,
                    current_step="사용자 입력 대기 중"
                )

                # WebSocket으로 메시지 전송 (사용자에게 표시)
                if self.ws_server and result.message:
                    self.ws_server.broadcast_task_interaction(
                        task_id=task_id,
                        role='agent',
                        message=result.message,
                        agent_id=current_step.agent_id,
                        agent_name=current_step.agent_name
                    )

                self._log(current_step.agent_id, current_step.agent_name, "info",
                          f"❓ 사용자 입력 대기",
                          details=result.message[:200] if result.message else "",
                          task_id=task_id)

                return None  # advance 금지
            
            elif result.status == AgentLifecycleStatus.COMPLETED:
                # Agent가 완료 선언
                current_step.status = "completed"
                current_step.result = result.final_data.get("output", result.message) if result.final_data else result.message
                current_step.completed_at = datetime.now()

                # TaskStateManager: completed_steps 증가, Agent를 IDLE로
                execution = self.task_state_manager.get_execution(task_id)
                if execution:
                    self.task_state_manager.update_execution(
                        task_id=task_id,
                        completed_steps=execution.completed_steps + 1,
                        status=TaskStatus.RUNNING
                    )
                self.task_state_manager.set_agent_idle(current_step.agent_id)

                # 결과를 context에 저장
                if result.final_data:
                    workflow.context[f"step_{current_step.order}_result"] = result.final_data
                else:
                    workflow.context[f"step_{current_step.order}_result"] = result.message

                self._log(current_step.agent_id, current_step.agent_name, "info",
                          f"✅ 작업 완료",
                          details=(result.message[:100] + "..." if result.message and len(result.message) > 100 else result.message) if result.message else "",
                          task_id=task_id)

                # Worker Agent 결과는 사용자에게 직접 표시하지 않음
                # Q&A Agent가 context로 사용하여 사용자와 소통함
                if current_step.agent_role != AgentRole.Q_AND_A:
                    print(f"[DynamicOrchestration] Worker Agent 결과 저장 (사용자에게 표시 안 함): {current_step.agent_name}")
                else:
                    # Q&A Agent의 Gate 종료는 Chat에 표시하지 않음
                    is_gate_completion = (
                        result.final_data
                        and result.final_data.get("reason") == "required_slots_filled"
                    )

                    if is_gate_completion:
                        print(f"[DynamicOrchestration] Q&A Agent Gate 종료 (Chat 출력 없음)")
                    elif self.ws_server and result.message:
                        # Q&A Agent의 일반 응답만 사용자에게 표시
                        self.ws_server.broadcast_task_interaction(
                            task_id=task_id,
                            role='agent',
                            message=result.message,
                            agent_id=current_step.agent_id,
                            agent_name=current_step.agent_name
                        )

                # 재계획 필요성 체크 (낮은 신뢰도 등)
                replan_reason = await self._check_replan_needed(task_id, result)
                if replan_reason:
                    self._log("planner-agent", "Planner Agent", "warning",
                              f"⚠️ 재계획 필요 감지: {replan_reason}",
                              task_id=task_id)

                    # 재계획 시도
                    replan_success = await self._replan_workflow(task_id, replan_reason)
                    if replan_success:
                        # 재계획 성공 - 처음부터 다시 실행
                        self._log("planner-agent", "Planner Agent", "info",
                                  "🔄 재계획 성공 - 워크플로우 재시작",
                                  task_id=task_id)
                        return await self._execute_workflow(task_id)
                    else:
                        # 재계획 실패 - 기존 계획대로 진행
                        self._log("planner-agent", "Planner Agent", "warning",
                                  "⚠️ 재계획 실패 - 기존 계획 유지",
                                  task_id=task_id)

                # Orchestration이 다음 단계 결정
                return await self._orchestrate_next(task_id)
            
            elif result.status == AgentLifecycleStatus.FAILED:
                # Agent가 실패 선언
                current_step.status = "failed"

                # TaskStateManager: Agent를 IDLE로
                self.task_state_manager.set_agent_idle(current_step.agent_id)

                error_message = result.message or result.error.get("message", "작업 처리 중 오류가 발생했습니다.") if result.error else "작업 처리 중 오류가 발생했습니다."

                self._log(current_step.agent_id, current_step.agent_name, "error",
                          f"❌ 작업 실패: {error_message}",
                          task_id=task_id)

                # 실패 시 자동 재계획 시도
                replan_reason = f"agent_failure: {current_step.agent_name}"
                self._log("planner-agent", "Planner Agent", "warning",
                          f"⚠️ 실패 감지 - 재계획 시도: {replan_reason}",
                          task_id=task_id)

                replan_success = await self._replan_workflow(task_id, replan_reason)
                if replan_success:
                    # 재계획 성공 - 워크플로우 재시작
                    self._log("planner-agent", "Planner Agent", "info",
                              "🔄 재계획 성공 - 워크플로우 재시작",
                              task_id=task_id)
                    return await self._execute_workflow(task_id)
                else:
                    # 재계획 실패 - 워크플로우 중단
                    workflow.phase = WorkflowPhase.FAILED
                    # TaskStateManager: Task를 FAILED로
                    self.task_state_manager.complete_execution(task_id, success=False)
                    self._log("planner-agent", "Planner Agent", "error",
                              "❌ 재계획 실패 - 워크플로우 중단",
                              task_id=task_id)
                    return error_message

            elif result.status == AgentLifecycleStatus.RUNNING:
                # Agent가 계속 실행 중 (비동기 작업 등)
                current_step.status = "running"
                # 계속 진행 대기
                return None
            
            else:
                # 알 수 없는 상태
                current_step.status = "failed"
                workflow.phase = WorkflowPhase.FAILED
                # TaskStateManager: Task를 FAILED로
                self.task_state_manager.complete_execution(task_id, success=False)
                self._log(current_step.agent_id, current_step.agent_name, "error",
                          f"❌ 알 수 없는 Agent 상태: {result.status}",
                          task_id=task_id)
                return "알 수 없는 오류가 발생했습니다."
    
    async def _execute_worker_agent(
        self,
        task_id: str,
        step: AgentStep,
        user_input: Optional[str] = None
    ) -> AgentResult:
        """
        Worker Agent 실행
        AgentResult를 반환하여 상태를 명시적으로 선언

        MCP Agent인 경우 해당 Agent의 execute_task를 호출합니다.
        """
        workflow = self._workflows.get(task_id)
        if not workflow:
            return failed("워크플로우를 찾을 수 없습니다.")

        # MCP Agent 체크 - agent_id에서 타입 추출
        agent_type = None
        for mcp_type in self._mcp_agents.keys():
            if mcp_type in step.agent_id or mcp_type in step.agent_name.lower():
                agent_type = mcp_type
                break

        # MCP Agent인 경우 해당 Agent의 execute_task 호출
        if agent_type and agent_type in self._mcp_agents:
            mcp_agent = self._mcp_agents[agent_type]

            # Context 구성
            context = {
                "task_id": task_id,
                "original_request": workflow.original_request,
                "user_input": user_input,
                "previous_results": workflow.get_completed_results(),
            }

            # ConversationState에서 Facts/Decisions 추가
            if workflow.conversation_state:
                context["facts"] = workflow.conversation_state.facts
                context["decisions"] = workflow.conversation_state.decisions

            self._log(step.agent_id, step.agent_name, "info",
                      f"🔌 MCP Agent 실행: {agent_type}",
                      task_id=task_id)

            try:
                result = await mcp_agent.execute_task(step.description, context)
                return result
            except Exception as e:
                self._log(step.agent_id, step.agent_name, "error",
                          f"❌ MCP Agent 실행 실패: {str(e)}",
                          task_id=task_id)
                return failed(f"MCP Agent 실행 실패: {str(e)}")

        # 일반 Worker Agent (LLM 기반)
        # 이전 결과들을 컨텍스트로 포함
        prev_results = workflow.get_completed_results()
        prev_text = ""
        if prev_results:
            prev_text = "\n\n**이전 작업 결과:**\n" + "\n".join([
                f"- {r['agent_name']}: {r['result']}"
                for r in prev_results
                if r['result']
            ])

            # 사용자 입력도 포함
            user_inputs = [r for r in prev_results if r.get('user_input')]
            if user_inputs:
                prev_text += "\n\n**사용자 선택:**\n" + "\n".join([
                    f"- {r['user_input']}" for r in user_inputs
                ])

        # 현재 사용자 입력도 포함 (resume_with_user_input에서 전달된 경우)
        if user_input:
            prev_text += f"\n\n**현재 사용자 입력:**\n{user_input}"

        messages = [
            {
                "role": "system",
                "content": f"""당신은 '{step.agent_name}' Agent입니다.
주어진 작업을 수행하고 결과를 반환해주세요.
이전 작업 결과와 사용자 입력을 참고하여 작업을 진행하세요."""
            },
            {
                "role": "user",
                "content": f"""**원래 요청**: {workflow.original_request}

**담당 작업**: {step.description}
{prev_text}

작업을 수행하고 결과를 알려주세요."""
            }
        ]

        try:
            response = await call_llm(messages, max_tokens=8000)
            if response:
                return completed(
                    final_data={"output": response, "agent_name": step.agent_name},
                    message=response
                )
            else:
                return failed("LLM 응답이 비어있습니다.")
        except Exception as e:
            return failed(f"작업 실행 중 오류 발생: {str(e)}")
    
    async def _handle_qa_agent_step(
        self,
        task_id: str,
        step: AgentStep,
        user_input: Optional[str] = None
    ) -> AgentResult:
        """
        Q&A Agent: 사용자와 소통 (질문 또는 답변)
        - 다른 Agent들의 결과를 context로 받아서 사용자와 소통
        - Worker Agent 결과는 사용자에게 직접 표시되지 않음
        - 필수 슬롯이 모두 채워지면 즉시 COMPLETED (Gate 역할)
        """
        workflow = self._workflows.get(task_id)
        if not workflow:
            return failed("워크플로우를 찾을 수 없습니다.")

        # 모든 Worker Agent 결과 수집 (사용자에게 표시되지 않은 내부 context)
        worker_results = workflow.get_completed_results()
        
        # Worker Agent 결과만 필터링 (Q&A Agent 결과 제외)
        worker_context_parts = []
        worker_results_data = []  # Worker Agent 결과 원본 저장
        user_responses = []
        for r in worker_results:
            if r.get('result') and r.get('agent_role') != AgentRole.Q_AND_A:
                # Worker Agent 결과는 사용자에게 표시되지 않았으므로 context로만 사용
                worker_context_parts.append(f"[{r['agent_name']} 작업 결과]\n{r['result']}")
                worker_results_data.append({
                    'agent_name': r['agent_name'],
                    'result': r['result']
                })
            if r.get('user_input'):
                user_responses.append(f"[사용자 응답]\n{r['user_input']}")
        
        worker_context = "\n\n---\n\n".join(worker_context_parts) if worker_context_parts else "(아직 없음)"
        user_context = "\n\n---\n\n".join(user_responses) if user_responses else "(없음)"
        
        # 현재 사용자 입력도 포함 (resume_with_user_input에서 전달된 경우)
        if user_input:
            user_context += f"\n\n---\n\n[현재 사용자 입력]\n{user_input}"
        
        # LLM이 전체 context를 보고 질문이 필요한지 최종 응답인지 결정
        # description 기반 판단 제거 - LLM이 상황을 판단
        try:
            # step.user_prompt가 있고 사용자 입력이 없으면 초기 질문 반환
            if step.user_prompt and not user_input:
                message = step.user_prompt
                # Worker 결과가 있으면 자연스럽게 요약 추가
                if worker_results_data and worker_context.strip() != "(아직 없음)":
                    latest_worker_result = worker_results_data[-1]
                    worker_result_text = latest_worker_result['result']

                    # Worker 결과 전체를 표시 (잘림 없음)
                    # 자연스러운 메시지로 결과 전달 (Agent 이름 노출 최소화)
                    message = f"{worker_result_text}\n\n{message}"

                return waiting_user(
                    message=message,
                    partial_data={"agent_name": step.agent_name, "step_description": step.description}
                )

            # =====================================================================
            # Schema 기반 완료 체크 (Orchestrator가 판단)
            # =====================================================================
            if user_input and workflow.task_schema and workflow.conversation_state:
                # Schema를 통해 다음 액션 결정
                next_action = workflow.task_schema.get_next_action(workflow.conversation_state)

                self._log(step.agent_id, step.agent_name, "info",
                          f"📋 Schema 평가: next_action={next_action.action_type.value}",
                          details=f"facts={workflow.conversation_state.facts}, decisions={workflow.conversation_state.decisions}",
                          task_id=task_id)

                # Schema가 COMPLETE 또는 EXECUTE를 반환하면 Q&A 종료
                if next_action.action_type == NextActionType.COMPLETE:
                    print(f"[DynamicOrchestration] Q&A Agent: Schema COMPLETE → COMPLETED")
                    return completed(
                        final_data={
                            "conversation_state": workflow.conversation_state.to_dict(),
                            "reason": "schema_complete",
                            "agent_name": step.agent_name
                        },
                        message=""  # Chat 출력 없음 - Orchestrator가 최종 정리
                    )

                if next_action.action_type == NextActionType.EXECUTE:
                    print(f"[DynamicOrchestration] Q&A Agent: Schema EXECUTE → COMPLETED (Worker 실행 필요)")
                    # Worker 실행이 필요함을 알림
                    workflow.conversation_state.set_flag("needs_worker_execution", True)
                    if next_action.worker_id:
                        workflow.context["next_worker_id"] = next_action.worker_id
                    return completed(
                        final_data={
                            "conversation_state": workflow.conversation_state.to_dict(),
                            "reason": "needs_worker_execution",
                            "worker_id": next_action.worker_id,
                            "agent_name": step.agent_name
                        },
                        message=""  # Chat 출력 없음
                    )

            # 사용자 입력이 있거나 step.user_prompt가 없으면 LLM이 상황을 판단하여 상태 결정
            messages = [
                {
                    "role": "system",
                    "content": """당신은 시스템의 대표 화자입니다.
사용자는 당신과 대화하고 있으며, 내부 Agent 구조를 알 필요가 없습니다.

**핵심 원칙**:
- 당신은 중재자이자 통역자입니다
- 절대 시스템 내부 상태를 설명하지 마세요
- 사용자에게 지금 필요한 행동 하나만 제시하세요

**메시지 패턴**:
당신의 모든 메시지는 다음 3가지 중 하나입니다:

1. **ASK (정보 요청)**: 작업 진행에 필요한 정보를 물어봅니다
   예: "위치와 인원, 시간을 알려주세요"

2. **INFORM (사실 전달)**: 확정된 내용이나 결과를 전달합니다
   예: "을지로, 2명, 12시 30분으로 확인했습니다"
   예: "조건에 맞는 메뉴를 찾았어요: 1) 돈카츠 2) 초밥 3) 규동"

3. **CONFIRM (선택/확인)**: 사용자의 선택이나 진행 여부를 확인합니다
   예: "어떤 메뉴로 할까요?"
   예: "이대로 진행할까요?"

**상태 결정 규칙**:
- 사용자에게 추가로 물어볼 것이 있으면 → status: "WAITING_USER"
- 사용자가 필요한 정보/선택을 제공했으면 → status: "COMPLETED"
- 같은 질문을 반복하지 마세요
- **이미 확정된 정보는 절대 다시 묻지 마세요!**

**메시지 작성 규칙**:
1. 필요한 경우 지금까지 확정된 내용 1~2줄 요약
2. 지금 사용자에게 필요한 행동 하나
3. 선택지 또는 질문

다음 JSON 형식으로 응답하세요:
```json
{
  "status": "WAITING_USER" 또는 "COMPLETED",
  "message": "사용자에게 보여줄 메시지"
}
```

**좋은 예시**:

정보 수집 (ASK):
{
  "status": "WAITING_USER",
  "message": "점심 메뉴 추천과 예약을 도와드릴게요 🙂\n\n먼저 몇 가지만 알려주세요:\n• 위치\n• 인원\n• 시간"
}

정보 확인 (INFORM):
{
  "status": "COMPLETED",
  "message": "을지로, 2명, 오늘 12시 30분으로 확인했습니다."
}

결과 전달 + 선택 요청 (INFORM + CONFIRM):
{
  "status": "WAITING_USER",
  "message": "조건에 맞는 점심 메뉴를 찾았어요:\n\n1) 돈카츠 정식 – 빠르고 든든\n2) 회전초밥 – 가볍고 깔끔\n3) 규동 – 빠른 한 끼\n\n어떤 메뉴로 할까요?"
}

선택 확인 (CONFIRM):
{
  "status": "COMPLETED",
  "message": "알겠습니다 👍\n그럼 돈카츠 정식 기준으로 근처 식당을 찾아볼게요."
}

**🔴 Context / Message 분리 원칙** (반드시 지켜야 할 것):

1. **Context is for knowing, Message is for talking**
   - 확정된 정보, Worker 결과, 내부 상태는 Context입니다
   - 당신은 Context를 참고만 하고, **절대 나열하거나 요약하지 마세요**

2. **지금 필요한 질문 1개만 생성**
   - "을지로, 2명으로 확인했습니다..." ❌ (Context 나열)
   - "시간은 언제가 좋을까요?" ✅ (질문만)

3. **당신은 대화를 끝내지 않습니다**
   - "모든 정보를 확인했습니다" ❌
   - "예약까지 모두 완료했어요" ❌
   - 최종 요약과 마무리는 Orchestrator의 책임

4. **Worker 결과를 요약하지 마세요**
   - Worker가 준 정보는 Context입니다
   - "조건에 맞는 메뉴를 찾았어요: 1) 돈카츠..." ✅ (자연스러운 전달)
   - "Worker Agent가 3개 메뉴를 추천했습니다..." ❌ (요약)

**나쁜 예시** (절대 이렇게 하지 마세요):
❌ "을지로, 2명, 12시 30분으로 확인했습니다" (Context 나열)
❌ "필요한 정보를 모두 확인했습니다" (종료 문구)
❌ "Worker Agent 결과가 아직 없습니다" (내부 상태)
❌ "정보 수집 단계입니다" (내부 상태)
❌ "다음 단계로 진행합니다" (내부 상태)

**좋은 예시**:
✅ "시간은 언제가 좋을까요?" (질문만)
✅ "어떤 메뉴로 할까요?" (질문만)
✅ "이 중 하나로 예약할까요?" (질문만)
"""
                },
                {
                    "role": "user",
                    "content": f"""**사용자 요청**: {workflow.original_request}

**현재 단계**: {step.description}

---

**🔒 Context** (for reference only - DO NOT list or summarize in your message):

확정된 정보 (절대 다시 묻지 말 것):
{workflow.conversation_state.get_facts_text() if workflow.conversation_state else '(없음)'}

미확정 정보 (필요한 facts):
{', '.join(workflow.task_schema.get_missing_facts(workflow.conversation_state)) if workflow.task_schema and workflow.conversation_state else '(없음)'}

의사결정 상태:
{workflow.conversation_state.get_decisions_text() if workflow.conversation_state else '(없음)'}

Worker 결과:
{worker_context}

대화 기록:
{user_context}

---

**💬 Your Task**:
위 Context를 참고하여, 사용자에게 **지금 필요한 질문 1개만** 생성하세요.

🔴 절대 금지:
1. 확정된 정보 나열 ❌ ("을지로, 2명으로 확인했습니다")
2. Worker 결과 나열 ❌ ("메뉴 옵션은 한식, 일식, 중식입니다")
3. Context 요약 ❌ ("지금까지 수집한 정보는...")
4. 상태 설명 ❌ ("확인했습니다", "진행하겠습니다")

✅ 올바른 예시:
- "예약자 성함을 알려주실 수 있을까요?" (질문만)
- "연락처를 알려주세요" (질문만)
- "이대로 진행할까요?" (확인 질문만)

JSON 형식으로 응답하세요."""
                }
            ]
            
            response = await call_llm(messages, max_tokens=4000, json_mode=True)
            
            # JSON 파싱
            try:
                import re
                json_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', response)
                if json_match:
                    response = json_match.group(1).strip()
                
                result_data = json.loads(response)
                status_str = result_data.get("status", "COMPLETED").upper()
                message = result_data.get("message", "작업이 완료되었습니다.")

                # 🔴 Context/Message 분리 원칙:
                # Worker 결과는 Context이므로 Q&A Agent 메시지에 강제로 붙이지 않습니다.
                # Worker 결과는 이미 Q&A Agent 프롬프트에 제공되었고,
                # LLM이 필요하면 자연스럽게 언급할 것입니다.
                # 강제로 붙이면 정보 덤핑이 발생합니다.

                # 상태에 따라 AgentResult 반환
                if status_str == "WAITING_USER":
                    return waiting_user(
                        message=message,
                        partial_data={"agent_name": step.agent_name, "step_description": step.description}
                    )
                else:  # COMPLETED
                    return completed(
                        final_data={"message": message, "agent_name": step.agent_name},
                        message=message
                    )
                    
            except (json.JSONDecodeError, KeyError) as e:
                print(f"[DynamicOrchestration] JSON parse error in Q&A Agent: {e}")
                print(f"[DynamicOrchestration] Response: {response[:500]}")
                # 파싱 실패 시 기본값: 사용자 입력이 있으면 COMPLETED, 없으면 WAITING_USER
                if user_input:
                    return completed(
                        final_data={"message": response if response else "작업이 완료되었습니다."},
                        message=response if response else "작업이 완료되었습니다."
                    )
                else:
                    return waiting_user(
                        message=response if response else "질문이 있습니다.",
                        partial_data={"agent_name": step.agent_name}
                    )
                    
        except Exception as e:
            print(f"[DynamicOrchestration] Error in Q&A Agent: {e}")
            import traceback
            traceback.print_exc()
            return failed(f"Q&A Agent 실행 중 오류 발생: {str(e)}")
    
    # =========================================================================
    # Utility Methods
    # =========================================================================
    
    async def _generate_final_answer(self, task_id: str) -> Optional[str]:
        """
        모든 스텝 완료 후 Orchestrator Final Narration 생성

        Orchestrator = Final Narrator:
        - Agent 이름 언급 ❌
        - "모든 작업이 완료되었습니다" ❌
        - 사람처럼 정리 + 다음 액션 제시 ✅
        """
        workflow = self._workflows.get(task_id)
        if not workflow:
            return None

        # FINALIZING Phase 진입
        workflow.phase = WorkflowPhase.FINALIZING

        self._log("orchestrator-system", "Orchestration Agent", "info",
                  "🎯 최종 정리 중 (Final Narration)",
                  task_id=task_id)

        # 모든 Worker 결과 수집 (Q&A 제외)
        all_results = workflow.get_completed_results()
        worker_results = [
            r for r in all_results
            if r.get('agent_role') != AgentRole.Q_AND_A and r.get('result')
        ]

        # Worker 결과 텍스트 생성
        worker_context = "\n\n---\n\n".join([
            f"[{r['agent_name']}의 작업 결과]\n{r['result']}"
            for r in worker_results
        ]) if worker_results else "(내부 작업 결과 없음)"

        # ConversationState에서 확정된 정보 수집
        confirmed_info = ""
        if workflow.conversation_state:
            confirmed_info = workflow.conversation_state.get_facts_text()

        # Final Narration LLM 프롬프트
        messages = [
            {
                "role": "system",
                "content": """당신은 Orchestrator입니다.
모든 작업이 완료되었으므로, 이제 사용자에게 최종 정리를 해줄 차례입니다.

**당신의 역할**:
당신은 시스템의 "Final Narrator"입니다.
사용자가 요청한 작업의 결과를 사람처럼 정리하고, 다음 행동을 제시합니다.

**출력 규칙**:
1. Agent 이름을 언급하지 마세요 (❌ "Worker Agent가...", "Q&A Agent가...")
2. 시스템 내부 상태를 설명하지 마세요 (❌ "모든 작업이 완료되었습니다")
3. 확정된 정보를 자연스럽게 요약하세요
4. Worker 결과를 사람이 말하듯 정리하세요
5. 다음 행동 1가지만 제시하세요 (선택지 또는 질문)

**좋은 예시**:
```
정리해볼게요 🙂

오늘 점심은 아래 조건으로 진행하면 좋아요:
- 위치: 을지로
- 인원: 2명
- 메뉴: 돈카츠

이 조건으로 예약 가능한 곳은:
1) 경양카츠 명동점 (13:00 / 13:10 / 13:30)
2) 돈가스클럽 을지로점 (12:30 / 13:00)

이 중 하나로 예약할까요?
아니면 다른 메뉴를 더 볼까요?
```

**나쁜 예시** (절대 이렇게 하지 마세요):
❌ "모든 작업이 완료되었습니다"
❌ "Worker Agent의 결과입니다"
❌ "Q&A Agent가 수집한 정보입니다"
❌ "다음 단계로 진행합니다"

**메시지 작성 방법**:
1. "정리해볼게요" 또는 자연스러운 시작
2. 확정된 정보 요약 (2-3줄)
3. Worker 결과 요약 (사람이 말하듯)
4. 다음 행동 1가지 (질문 또는 선택지)

자연스럽고 친근한 톤으로 작성하세요.
"""
            },
            {
                "role": "user",
                "content": f"""**사용자의 원래 요청**:
{workflow.original_request}

**확정된 정보** (사용자가 제공한 정보):
{confirmed_info if confirmed_info else '(없음)'}

**내부 작업 결과** (사용자에게 직접 표시되지 않은 결과):
{worker_context}

---

위 정보를 바탕으로, 사용자에게 최종 정리와 다음 행동을 제시하는 메시지를 작성하세요.

중요:
- Agent 이름 절대 언급 금지
- "완료되었습니다" 같은 시스템 멘트 금지
- 사람처럼 자연스럽게 정리
- 다음 행동 1가지만 제시
"""
            }
        ]

        try:
            # LLM 호출하여 Final Narration 생성
            final_narration = await call_llm(messages, max_tokens=2000)

            if not final_narration or not final_narration.strip():
                # LLM 실패 시 자연스러운 fallback 메시지 생성
                final_narration = self._generate_fallback_message(
                    workflow, confirmed_info, worker_context
                )

            # COMPLETED Phase로 전환
            workflow.phase = WorkflowPhase.COMPLETED

            # TaskStateManager: Task를 COMPLETED로
            self.task_state_manager.complete_execution(task_id, success=True)

            # WebSocket으로 Final Narration 전송 (Chat에만 표시)
            if self.ws_server:
                self.ws_server.broadcast_task_interaction(
                    task_id=task_id,
                    role='agent',
                    message=final_narration,
                    agent_id="orchestrator-final",
                    agent_name="Assistant"  # 사용자에게는 "Assistant"로 표시
                )

            self._log("orchestrator-system", "Orchestration Agent", "info",
                      "✅ Final Narration 완료",
                      details=final_narration[:100],
                      task_id=task_id)

            return final_narration

        except Exception as e:
            self._log("orchestrator-system", "Orchestration Agent", "error",
                      f"❌ Final Narration 생성 실패: {str(e)}",
                      task_id=task_id)

            # 실패 시 자연스러운 fallback 메시지 생성
            fallback_message = self._generate_fallback_message(
                workflow, confirmed_info, worker_context
            )

            if self.ws_server:
                self.ws_server.broadcast_task_interaction(
                    task_id=task_id,
                    role='agent',
                    message=fallback_message,
                    agent_id="orchestrator-final",
                    agent_name="Assistant"
                )

            workflow.phase = WorkflowPhase.COMPLETED
            return fallback_message
    
    def _generate_fallback_message(
        self,
        workflow: DynamicWorkflow,
        confirmed_info: str,
        worker_context: str
    ) -> str:
        """
        Fallback 응답 생성 (LLM 실패 시)
        대화 맥락을 활용하여 자연스러운 메시지 생성

        Args:
            workflow: 워크플로우
            confirmed_info: 확정된 정보
            worker_context: Worker 작업 결과

        Returns:
            자연스러운 fallback 메시지
        """
        # 확정된 정보가 있으면 활용
        if confirmed_info and confirmed_info.strip() and confirmed_info != "(없음)":
            # 간단히 요약하여 자연스럽게 표현
            info_lines = confirmed_info.split('\n')[:3]  # 최대 3줄만
            info_summary = '\n'.join(info_lines)
            if len(confirmed_info.split('\n')) > 3:
                info_summary += "\n..."
            return f"정리해볼게요 🙂\n\n{info_summary}\n\n다음 단계를 진행할까요?"

        # Worker 결과가 있으면 활용
        if worker_context and worker_context != "(내부 작업 결과 없음)":
            # 결과에서 핵심만 추출 (첫 200자)
            result_preview = worker_context[:200]
            if len(worker_context) > 200:
                result_preview += "..."
            return f"다음과 같이 정리했습니다:\n\n{result_preview}\n\n원하시는 대로 진행할까요?"

        # 아무 정보도 없으면 간단한 확인 메시지
        return "요청하신 내용을 확인했습니다. 추가로 필요한 것이 있으면 알려주세요."
    
    def _log(
        self,
        agent_id: str,
        agent_name: str,
        log_type: str,
        message: str,
        details: str = "",
        task_id: str = None
    ) -> None:
        """Agent Activity 로그"""
        print(f"[{agent_name}] {message}")
        if self.ws_server:
            self.ws_server.broadcast_agent_log(
                agent_id=agent_id,
                agent_name=agent_name,
                log_type=log_type,
                message=message,
                details=details,
                task_id=task_id
            )
    
    def has_pending_workflow(self, task_id: str) -> bool:
        """대기 중인 워크플로우가 있는지 확인"""
        workflow = self._workflows.get(task_id)
        return workflow is not None and workflow.phase == WorkflowPhase.WAITING_USER
    
    def get_workflow(self, task_id: str) -> Optional[DynamicWorkflow]:
        """워크플로우 조회"""
        return self._workflows.get(task_id)
    
    def remove_workflow(self, task_id: str) -> None:
        """워크플로우 제거"""
        if task_id in self._workflows:
            del self._workflows[task_id]
        if task_id in self._locks:
            del self._locks[task_id]


# =============================================================================
# Global Instance
# =============================================================================

dynamic_orchestration = DynamicOrchestrationEngine()

