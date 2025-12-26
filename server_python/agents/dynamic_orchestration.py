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
        
        # 시스템 Agent 정의
        self.system_agents = {
            "orchestrator": {
                "id": "orchestrator-system",
                "name": "Orchestration Agent",
                "role": AgentRole.ORCHESTRATOR
            },
            "q_and_a": {
                "id": "qa-agent-system", 
                "name": "Q&A Agent",
                "role": AgentRole.Q_AND_A
            }
        }
    
    def set_ws_server(self, ws_server: Any) -> None:
        """WebSocket 서버 설정"""
        self.ws_server = ws_server
    
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
            # 워크플로우 생성
            workflow = DynamicWorkflow(
                task_id=task_id,
                original_request=request,
                context={
                    "available_agents": available_agents,
                    "slack_channel": slack_channel,
                    "slack_ts": slack_ts
                }
            )
            self._workflows[task_id] = workflow
        
        self._log("orchestrator-system", "Orchestration Agent", "info",
                  f"🎯 새로운 요청 수신: {request[:50]}...", task_id=task_id)
        
        # 1. 요청 분석 및 초기 Plan 생성
        initial_plan = await self._analyze_and_plan(workflow, available_agents)
        
        if not initial_plan:
            self._log("orchestrator-system", "Orchestration Agent", "error",
                      "❌ 요청 분석 실패", task_id=task_id)
            return "요청을 분석할 수 없습니다. 다시 시도해주세요."
        
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
        
        self._log(current_step.agent_id, current_step.agent_name, "info",
                  f"📥 사용자 응답 수신: {user_input[:50]}...", task_id=task_id)
        
        workflow.phase = WorkflowPhase.EXECUTING
        
        # Agent 실행 (user_input 제공)
        result = await self._execute_agent_step(task_id, current_step, user_input=user_input)
        
        # AgentResult.status로만 분기
        if result.status == AgentLifecycleStatus.WAITING_USER:
            # Agent가 또 다른 질문 요청 (multi-turn 대화)
            current_step.status = "waiting_user"
            workflow.phase = WorkflowPhase.WAITING_USER
            
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
            
            # 결과를 context에 저장
            if result.final_data:
                workflow.context[f"step_{current_step.order}_result"] = result.final_data
            else:
                workflow.context[f"step_{current_step.order}_result"] = result.message
            
            self._log(current_step.agent_id, current_step.agent_name, "info",
                      f"✅ 작업 완료",
                      details=(result.message[:100] + "..." if result.message and len(result.message) > 100 else result.message) if result.message else "",
                      task_id=task_id)
            
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
        available_agents: List[Dict[str, Any]]
    ) -> Optional[List[Dict[str, Any]]]:
        """
        요청 분석 및 초기 Plan 생성
        """
        workflow.phase = WorkflowPhase.ANALYZING
        
        # Agent가 없으면 기본 Agent 추가
        if not available_agents:
            available_agents = [
                {"id": "general-agent", "name": "General Agent", "type": "custom"},
            ]
        
        agent_descriptions = "\n".join([
            f"- {a['name']} (ID: {a['id']}): {a.get('type', 'custom')}"
            for a in available_agents
        ])
        
        messages = [
            {
                "role": "system",
                "content": """당신은 멀티-에이전트 시스템의 Orchestration Agent입니다.
사용자 요청을 분석하여 어떤 Agent들이 어떤 순서로 작업해야 하는지 계획을 세워주세요.

중요 규칙:
1. Worker Agent들은 사용자와 직접 소통하지 않습니다. 작업만 수행합니다.
2. 사용자와 소통이 필요할 때는 Q&A Agent를 사용하세요.
3. 예: "메뉴 추천" 후 → Q&A Agent가 "어떤 메뉴로 할까요?" 질문
4. 예: "예약 진행" 후 → Q&A Agent가 "이대로 예약할까요?" 확인
5. 모든 작업 완료 후 마지막에 Q&A Agent가 최종 응답을 정리합니다"""
            },
            {
                "role": "user",
                "content": f"""사용자 요청: {workflow.original_request}

사용 가능한 Agent 목록:
{agent_descriptions}

다음 JSON 형식으로 실행 계획을 작성해주세요:
```json
{{
  "analysis": "요청 분석 내용",
  "steps": [
    {{
      "agent_id": "agent-id",
      "agent_name": "Agent 이름",
      "role": "worker",
      "description": "이 Agent가 수행할 작업",
      "needs_user_confirmation": false
    }},
    {{
      "agent_id": "qa-agent-system",
      "agent_name": "Q&A Agent",
      "role": "q_and_a",
      "description": "사용자에게 질문 또는 최종 응답 생성",
      "user_prompt": "질문이 필요한 경우에만 작성 (선택사항)"
    }}
  ]
}}
```"""
            }
        ]
        
        print(f"[DynamicOrchestration] Calling LLM for planning...")
        response = await call_llm(messages, max_tokens=8000, json_mode=True)
        print(f"[DynamicOrchestration] LLM Response: {response[:500] if response else 'EMPTY'}...")
        
        try:
            plan = json.loads(response)
            steps = plan.get("steps", [])
            print(f"[DynamicOrchestration] Parsed {len(steps)} steps from plan")
            
            self._log("orchestrator-system", "Orchestration Agent", "decision",
                      f"📋 실행 계획 수립: {len(steps)}개 단계",
                      details=plan.get("analysis", ""),
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
            
            return steps
            
        except json.JSONDecodeError as e:
            print(f"[DynamicOrchestration] JSON parse error: {e}")
            print(f"[DynamicOrchestration] Failed to parse plan: {response[:500] if response else 'EMPTY'}")
            
            # JSON 코드 블록에서 추출 시도
            try:
                import re
                json_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', response)
                if json_match:
                    json_text = json_match.group(1).strip()
                    plan = json.loads(json_text)
                    steps = plan.get("steps", [])
                    print(f"[DynamicOrchestration] Extracted {len(steps)} steps from code block")
                    
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
                    
                    return steps
            except Exception as e2:
                print(f"[DynamicOrchestration] Code block extraction also failed: {e2}")
            
            return None
    
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
                    # Q&A Agent의 최종 응답은 사용자에게 표시
                    if self.ws_server and result.message:
                        self.ws_server.broadcast_task_interaction(
                            task_id=task_id,
                            role='agent',
                            message=result.message,
                            agent_id=current_step.agent_id,
                            agent_name=current_step.agent_name
                        )
                
                # Orchestration이 다음 단계 결정
                return await self._orchestrate_next(task_id)
            
            elif result.status == AgentLifecycleStatus.FAILED:
                # Agent가 실패 선언
                current_step.status = "failed"
                workflow.phase = WorkflowPhase.FAILED
                
                error_message = result.message or result.error.get("message", "작업 처리 중 오류가 발생했습니다.") if result.error else "작업 처리 중 오류가 발생했습니다."
                
                self._log(current_step.agent_id, current_step.agent_name, "error",
                          f"❌ 작업 실패: {error_message}",
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
        """
        workflow = self._workflows.get(task_id)
        if not workflow:
            return failed("워크플로우를 찾을 수 없습니다.")
        
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
        - LLM이 전체 context를 보고 WAITING_USER 또는 COMPLETED 상태 결정
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
        
        worker_context = "\n\n---\n\n".join(worker_context_parts) if worker_context_parts else "아직 작업 결과가 없습니다."
        user_context = "\n\n---\n\n".join(user_responses) if user_responses else "없음"
        
        # 현재 사용자 입력도 포함 (resume_with_user_input에서 전달된 경우)
        if user_input:
            user_context += f"\n\n---\n\n[현재 사용자 입력]\n{user_input}"
        
        # LLM이 전체 context를 보고 질문이 필요한지 최종 응답인지 결정
        # description 기반 판단 제거 - LLM이 상황을 판단
        try:
            # step.user_prompt가 있고 사용자 입력이 없으면 초기 질문 반환
            if step.user_prompt and not user_input:
                message = step.user_prompt
                # Worker Agent 결과 요약 추가
                if worker_results_data and worker_context.strip() != "아직 작업 결과가 없습니다.":
                    latest_worker_result = worker_results_data[-1]
                    worker_result_text = latest_worker_result['result']
                    worker_agent_name = latest_worker_result['agent_name']
                    
                    result_summary = worker_result_text[:500]
                    if len(worker_result_text) > 500:
                        result_summary += "..."
                    
                    if "점심" in worker_agent_name or "메뉴" in worker_agent_name:
                        summary_header = "점심 메뉴 추천을 드렸습니다:\n\n"
                    elif "식당" in worker_agent_name or "장소" in worker_agent_name:
                        summary_header = "식당 추천을 드렸습니다:\n\n"
                    else:
                        summary_header = f"{worker_agent_name} 작업 결과:\n\n"
                    
                    message = f"{summary_header}{result_summary}\n\n{message}"
                
                return waiting_user(
                    message=message,
                    partial_data={"agent_name": step.agent_name, "step_description": step.description}
                )
            
            # 사용자 입력이 있거나 step.user_prompt가 없으면 LLM이 상황을 판단하여 상태 결정
            messages = [
                {
                    "role": "system",
                    "content": """당신은 사용자와 대화하는 Q&A Agent입니다.

**상태 결정 규칙** (매우 중요!):
1. **사용자 입력이 이미 제공된 경우** (user_context 또는 현재 사용자 입력에 있음):
   - **정보 수집 단계인 경우** (Worker Agent 결과가 아직 없는 경우):
     * 기본 정보(위치, 인원, 시간 등)가 충분히 수집되었으면 → status: "COMPLETED" (Worker Agent가 작업할 수 있도록 진행)
     * 기본 정보가 부족하면 → status: "WAITING_USER" (추가 질문 작성)
   - **Worker Agent 결과가 있는 경우**:
     * 사용자가 선택/확인을 완료했으면 → status: "COMPLETED" (다음 단계로 진행)
     * 추가 확인이 필요하면 → status: "WAITING_USER" (확인 질문 작성)
   - **절대로 같은 질문을 반복하지 마세요!**
   
2. **사용자 입력이 없는 경우**:
   - 필요한 정보를 물어보는 질문 작성 → status: "WAITING_USER"

**중요**: 정보 수집 단계에서 사용자로부터 기본 정보(위치, 인원, 시간, 선호도 등)를 받았으면, 완벽하지 않더라도 Worker Agent가 작업을 시작할 수 있도록 status: "COMPLETED"를 반환하세요.

**메시지 작성 규칙**:
1. 아래 'Worker Agent 작업 결과'는 사용자에게 **표시되지 않은 내부 정보**입니다
2. **반드시 먼저 Worker Agent의 작업 결과를 요약해서 사용자에게 설명**해야 합니다
3. 설명 없이 질문만 하면 안 됩니다
4. 사용자가 이미 답변한 내용을 고려하여 응답하세요

다음 JSON 형식으로 응답하세요:
```json
{
  "status": "WAITING_USER" 또는 "COMPLETED",
  "message": "사용자에게 보여줄 메시지 (Worker Agent 결과 요약 포함 필수)"
}
```

예시 (질문 필요 - 사용자 입력 없음):
{
  "status": "WAITING_USER",
  "message": "점심 메뉴 추천과 근처 식당 예약을 도와드릴게요. 아래 정보를 알려주세요:\n- 위치\n- 인원\n- 시간"
}

예시 (정보 수집 완료 - COMPLETED 반환):
{
  "status": "COMPLETED",
  "message": "을지로, 인원 2명, 점심 시간으로 확인했습니다. 메뉴를 추천해드리겠습니다."
}

예시 (Worker Agent 결과 후 - 사용자 선택 확인):
{
  "status": "WAITING_USER",
  "message": "점심 메뉴를 추천해드렸어요:\n\n- 국수/냉면: 시원하고 담백하게 빠르게 먹기 좋음 (12,000-18,000원)\n- 한식 백반/국밥: 든든하고 가성비 좋음 (8,000-12,000원)\n\n위 메뉴 중 어떤 걸로 하실까요?"
}
"""
                },
                {
                    "role": "user",
                    "content": f"""**원래 요청**: {workflow.original_request}

**Worker Agent 작업 결과** (사용자에게 표시되지 않음 - 반드시 먼저 요약 설명 필요):
{worker_context}

**사용자 이전 응답**:
{user_context}

**담당 작업**: {step.description}

**중요**: 
- **Worker Agent 작업 결과가 없는 경우** (정보 수집 단계):
  - 사용자 입력이 이미 제공된 경우: 기본 정보(위치, 인원, 시간 등)가 있으면 → status: "COMPLETED" 반환 (Worker Agent가 작업 시작)
  - 사용자 입력이 없는 경우: 필요한 정보를 물어보는 질문 작성 → status: "WAITING_USER"
- **Worker Agent 작업 결과가 있는 경우**:
  - 사용자 입력이 이미 제공된 경우: 선택/확인 완료했으면 → status: "COMPLETED", 추가 확인 필요하면 → status: "WAITING_USER"
  - 사용자 입력이 없는 경우: Worker Agent 결과를 요약하고 질문 작성 → status: "WAITING_USER"

위 정보를 바탕으로:
1. 사용자 입력이 더 필요한지, 아니면 최종 응답만 하면 되는지 판단
2. Worker Agent 작업 결과를 **반드시 먼저 요약해서 사용자에게 설명** (절대 생략 불가!)
3. 그 다음 질문 또는 최종 응답 작성

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
                
                # Worker Agent 결과가 있는데 응답에 포함되지 않았으면 강제로 포함
                if worker_results_data and worker_context.strip() != "아직 작업 결과가 없습니다.":
                    latest_worker_result = worker_results_data[-1]
                    worker_result_text = latest_worker_result['result']
                    worker_agent_name = latest_worker_result['agent_name']
                    
                    result_preview = worker_result_text[:150].replace('\n', ' ')
                    has_result_in_response = result_preview in message or any(
                        keyword in message 
                        for keyword in result_preview.split()[:5]
                    )
                    
                    if not has_result_in_response:
                        result_summary = worker_result_text[:500]
                        if len(worker_result_text) > 500:
                            result_summary += "..."
                        
                        if "점심" in worker_agent_name or "메뉴" in worker_agent_name:
                            summary_header = "점심 메뉴 추천을 드렸습니다:\n\n"
                        elif "식당" in worker_agent_name or "장소" in worker_agent_name:
                            summary_header = "식당 추천을 드렸습니다:\n\n"
                        else:
                            summary_header = f"{worker_agent_name} 작업 결과:\n\n"
                        
                        message = f"{summary_header}{result_summary}\n\n{message}"
                        print(f"[DynamicOrchestration] Worker Agent 결과를 응답에 강제 포함: {worker_agent_name}")
                
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
        모든 스텝 완료 후 최종 응답 생성
        """
        workflow = self._workflows.get(task_id)
        if not workflow:
            return None
        
        workflow.phase = WorkflowPhase.COMPLETED
        
        # 모든 결과 수집
        all_results = workflow.get_completed_results()
        
        # 최종 응답 생성
        if all_results:
            summary = "\n\n".join([
                f"**{r['agent_name']}**: {r['result']}"
                for r in all_results
                if r.get('result')
            ])
            final_message = f"✅ 모든 작업이 완료되었습니다.\n\n{summary}"
        else:
            final_message = "✅ 작업이 완료되었습니다."
        
        # WebSocket으로 최종 응답 전송
        if self.ws_server:
            self.ws_server.broadcast_task_interaction(
                task_id=task_id,
                role='agent',
                message=final_message,
                agent_id="orchestrator-system",
                agent_name="Orchestration Agent"
            )
        
        self._log("orchestrator-system", "Orchestration Agent", "info",
                  "🎉 워크플로우 완료",
                  task_id=task_id)
        
        return final_message
    
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

