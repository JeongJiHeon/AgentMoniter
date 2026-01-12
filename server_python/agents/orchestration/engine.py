#!/usr/bin/env python3
"""
Orchestration Engine - 리팩토링된 메인 엔진

기존 DynamicOrchestrationEngine을 모듈화하여 재구성한 버전입니다.
"""

import asyncio
from datetime import datetime
from typing import Dict, List, Optional, Any
from uuid import uuid4

from .types import (
    AgentStep, AgentRole, DynamicWorkflow, WorkflowPhase, SYSTEM_AGENTS
)
from .workflow_manager_v2 import WorkflowManager
from .agent_executor import AgentExecutor
from .qa_handler import QAHandler
from .final_narrator import FinalNarrator
from .logger import OrchestrationLogger, LogLevel, orchestration_logger
from .circuit_breaker import CircuitBreaker, circuit_breaker, CircuitOpenError
from .repository import WorkflowRepository, InMemoryRepository

from ..agent_result import (
    AgentResult, AgentLifecycleStatus, completed, failed
)
from ..task_schema import TaskSchemaRegistry, NextActionType, create_initial_state_v3
from ..extractors import extract_and_update_state
from ..task_state import task_state_manager, TaskStatus, AgentExecutionStatus
from ..prompts.prompt_manager import PromptManager
from ..metrics.collector import metrics_collector

# 순환 참조 방지: planner_agent, call_llm은 메서드 내에서 지연 import


class OrchestrationEngineV2:
    """
    리팩토링된 오케스트레이션 엔진

    모듈화된 컴포넌트들을 조합하여 워크플로우를 관리합니다.

    Components:
    - WorkflowManager: 워크플로우 생명주기 관리
    - AgentExecutor: Worker Agent 실행
    - QAHandler: Q&A Agent 처리
    - FinalNarrator: 최종 응답 생성
    - CircuitBreaker: 에러 복구
    - Logger: 구조화된 로깅
    - Repository: 상태 영속성 (선택적)
    """

    def __init__(
        self,
        repository: Optional[WorkflowRepository] = None,
        enable_metrics: bool = True,
        enable_circuit_breaker: bool = True
    ):
        """
        Args:
            repository: 워크플로우 저장소 (None이면 메모리 사용)
            enable_metrics: 메트릭 수집 활성화
            enable_circuit_breaker: Circuit Breaker 활성화
        """
        # Core Components
        self._workflow_manager = WorkflowManager()
        self._prompt_manager = PromptManager()
        self._agent_executor = AgentExecutor()
        self._qa_handler = QAHandler(self._prompt_manager)
        self._final_narrator = FinalNarrator(self._prompt_manager)
        self._logger = orchestration_logger
        self._repository = repository or InMemoryRepository()

        # Optional Components
        self._circuit_breaker = circuit_breaker if enable_circuit_breaker else None
        self._enable_metrics = enable_metrics

        # WebSocket & TaskStateManager
        self.ws_server: Any = None
        self.task_state_manager = task_state_manager

        # MCP Agents
        self._mcp_agents: Dict[str, Any] = {}

        # Register system agents
        self._register_system_agents()

    def _register_system_agents(self) -> None:
        """시스템 Agent 등록"""
        for agent_key, agent_info in SYSTEM_AGENTS.items():
            self.task_state_manager.register_agent(
                agent_id=agent_info["id"],
                agent_name=agent_info["name"]
            )

    # =========================================================================
    # Configuration
    # =========================================================================

    def set_ws_server(self, ws_server: Any) -> None:
        """WebSocket 서버 설정"""
        self.ws_server = ws_server
        self._setup_event_handlers()
        self._logger.set_ws_callback(self._broadcast_log)

    def _setup_event_handlers(self) -> None:
        """이벤트 핸들러 설정"""
        def on_task_status_change(event: Dict[str, Any]) -> None:
            if self.ws_server:
                self.ws_server.broadcast_task_status_change(event)
                summary = self.task_state_manager.get_task_summary()
                self.ws_server.broadcast_task_summary(summary)

        def on_agent_status_change(agent_status: Dict[str, Any]) -> None:
            if self.ws_server:
                self.ws_server.broadcast_agent_status_change(agent_status)
                summary = self.task_state_manager.get_agent_summary()
                self.ws_server.broadcast_agent_summary(summary)

        self.task_state_manager.set_status_change_handler(on_task_status_change)
        self.task_state_manager.set_agent_change_handler(on_agent_status_change)

    def _broadcast_log(
        self,
        agent_id: str,
        agent_name: str,
        log_type: str,
        message: str,
        details: str = "",
        task_id: str = None
    ) -> None:
        """로그 브로드캐스트"""
        if self.ws_server:
            self.ws_server.broadcast_agent_log(
                agent_id=agent_id,
                agent_name=agent_name,
                log_type=log_type,
                message=message,
                details=details,
                task_id=task_id
            )

    def register_mcp_agent(self, agent_type: str, agent_instance: Any) -> None:
        """MCP Agent 등록"""
        self._mcp_agents[agent_type] = agent_instance
        self._agent_executor.register_mcp_agent(agent_type, agent_instance)

    # =========================================================================
    # Main Entry Points
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

        Args:
            task_id: Task ID
            request: 사용자 요청
            available_agents: 사용 가능한 Agent 목록
            slack_channel: Slack 채널 (선택)
            slack_ts: Slack 타임스탬프 (선택)

        Returns:
            응답 메시지 또는 None (사용자 입력 대기)
        """
        start_time = datetime.now()

        # Schema 기반 상태 초기화
        conversation_state = create_initial_state_v3(request)
        task_schema = TaskSchemaRegistry.infer_from_request(request)

        # 워크플로우 생성
        workflow = await self._workflow_manager.create_workflow(
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

        # TaskStateManager 시작
        self.task_state_manager.start_execution(task_id=task_id, total_steps=0)

        self._logger.info(
            "orchestrator-system", "Orchestration Agent",
            f"🎯 새로운 요청 수신: {request[:50]}...",
            task_id=task_id
        )

        # 요청 분석 및 계획 수립
        plan_result = await self._analyze_and_plan(workflow, available_agents)

        if not plan_result:
            self._logger.error(
                "orchestrator-system", "Orchestration Agent",
                "❌ 요청 분석 실패",
                task_id=task_id
            )
            return "요청을 분석할 수 없습니다. 다시 시도해주세요."

        # 워크플로우 실행
        result = await self._execute_workflow(task_id)

        # 메트릭 기록
        if self._enable_metrics:
            total_time = (datetime.now() - start_time).total_seconds() * 1000
            metrics_collector.record_workflow_completion(
                task_id=task_id,
                total_time_ms=total_time,
                steps_count=len(workflow.steps),
                success=result is not None
            )

        return result

    async def resume_with_user_input(
        self,
        task_id: str,
        user_input: str
    ) -> Optional[str]:
        """
        사용자 입력으로 워크플로우 재개

        Args:
            task_id: Task ID
            user_input: 사용자 입력

        Returns:
            응답 메시지 또는 None
        """
        workflow = self._workflow_manager.get_workflow(task_id)
        if not workflow:
            return "워크플로우를 찾을 수 없습니다."

        current_step = workflow.get_current_step()
        if not current_step:
            return "현재 진행 중인 단계가 없습니다."

        # 사용자 응답 표시
        if self.ws_server:
            self.ws_server.broadcast_task_interaction(
                task_id=task_id,
                role='user',
                message=user_input,
                agent_id=None,
                agent_name=None
            )

        # 사용자 입력 저장
        current_step.user_input = user_input

        # Schema 기반 상태 업데이트
        if workflow.conversation_state:
            # 지연 import로 순환 참조 방지
            from models.orchestration import call_llm
            workflow.conversation_state = await extract_and_update_state(
                user_input,
                workflow.conversation_state,
                call_llm_func=call_llm
            )

        workflow.phase = WorkflowPhase.EXECUTING

        # TaskStateManager 업데이트
        self.task_state_manager.update_execution(
            task_id=task_id,
            status=TaskStatus.RUNNING
        )

        # Agent 실행
        result = await self._execute_agent_step(task_id, current_step, user_input)

        return await self._handle_agent_result(task_id, current_step, result)

    # =========================================================================
    # Planning
    # =========================================================================

    async def _analyze_and_plan(
        self,
        workflow: DynamicWorkflow,
        available_agents: List[Dict[str, Any]],
        reason: str = "initial"
    ) -> Optional[List[Dict[str, Any]]]:
        """요청 분석 및 계획 수립"""
        # 지연 import로 순환 참조 방지
        from ..planner_agent import planner_agent, PlannerContext

        workflow.phase = WorkflowPhase.ANALYZING

        self._logger.info(
            "planner-agent", "Planner Agent",
            f"🎯 Planning 시작 - Reason: {reason}",
            task_id=workflow.task_id
        )

        # PlannerAgent 호출
        planner_context = PlannerContext(
            task_id=workflow.task_id,
            user_request=workflow.original_request,
            available_agents=available_agents,
            reason=reason
        )

        planner_result = await planner_agent.run(planner_context)

        if not planner_result.success:
            return None

        steps = planner_result.steps

        self._logger.decision(
            "planner-agent", "Planner Agent",
            f"📋 실행 계획 수립: {len(steps)}개 단계",
            task_id=workflow.task_id,
            details=planner_result.analysis
        )

        # 스텝 생성
        for i, step_data in enumerate(steps):
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

        # TaskStateManager 업데이트
        execution = self.task_state_manager.get_execution(workflow.task_id)
        if execution:
            execution.total_steps = len(steps)

        return steps

    # =========================================================================
    # Workflow Execution
    # =========================================================================

    async def _execute_workflow(self, task_id: str) -> Optional[str]:
        """워크플로우 실행"""
        workflow = self._workflow_manager.get_workflow(task_id)
        if not workflow:
            return None

        workflow.phase = WorkflowPhase.EXECUTING

        while True:
            current_step = workflow.get_current_step()
            if not current_step:
                return await self._generate_final_answer(task_id)

            if current_step.status == "completed":
                if not workflow.advance():
                    return await self._generate_final_answer(task_id)
                continue

            # 스텝 실행
            current_step.status = "running"
            current_step.started_at = datetime.now()

            self._update_agent_running_state(task_id, current_step)

            self._logger.info(
                current_step.agent_id, current_step.agent_name,
                f"🔧 작업 시작: {current_step.description}",
                task_id=task_id,
                details=f"Step {current_step.order}/{len(workflow.steps)}"
            )

            # Agent 실행
            result = await self._execute_agent_step(task_id, current_step)

            # 결과 처리
            response = await self._handle_agent_result(task_id, current_step, result)
            if response is not None or workflow.phase == WorkflowPhase.WAITING_USER:
                return response

    async def _execute_agent_step(
        self,
        task_id: str,
        step: AgentStep,
        user_input: Optional[str] = None
    ) -> AgentResult:
        """Agent 스텝 실행"""
        workflow = self._workflow_manager.get_workflow(task_id)
        if not workflow:
            return failed("워크플로우를 찾을 수 없습니다.")

        start_time = datetime.now()

        # Circuit Breaker를 통한 실행
        if self._circuit_breaker:
            try:
                if step.agent_role == AgentRole.Q_AND_A:
                    result = await self._circuit_breaker.call(
                        step.agent_id,
                        self._qa_handler.handle,
                        workflow, step, user_input
                    )
                else:
                    result = await self._circuit_breaker.call(
                        step.agent_id,
                        self._agent_executor.execute,
                        workflow, step, user_input
                    )
            except CircuitOpenError:
                result = failed(f"Agent {step.agent_name}이 일시적으로 사용 불가합니다.")
        else:
            if step.agent_role == AgentRole.Q_AND_A:
                result = await self._qa_handler.handle(workflow, step, user_input)
            else:
                result = await self._agent_executor.execute(workflow, step, user_input)

        # 메트릭 기록
        if self._enable_metrics:
            execution_time = (datetime.now() - start_time).total_seconds() * 1000
            metrics_collector.record_agent_execution(
                agent_id=step.agent_id,
                agent_name=step.agent_name,
                execution_time_ms=execution_time,
                success=result.status == AgentLifecycleStatus.COMPLETED,
                task_id=task_id
            )

        return result

    async def _handle_agent_result(
        self,
        task_id: str,
        step: AgentStep,
        result: AgentResult
    ) -> Optional[str]:
        """Agent 결과 처리"""
        workflow = self._workflow_manager.get_workflow(task_id)
        if not workflow:
            return None

        if result.status == AgentLifecycleStatus.WAITING_USER:
            return self._handle_waiting_user(task_id, workflow, step, result)

        elif result.status == AgentLifecycleStatus.COMPLETED:
            return await self._handle_completed(task_id, workflow, step, result)

        elif result.status == AgentLifecycleStatus.FAILED:
            return await self._handle_failed(task_id, workflow, step, result)

        elif result.status == AgentLifecycleStatus.RUNNING:
            step.status = "running"
            return None

        else:
            return self._handle_unknown_status(task_id, workflow, step, result)

    def _handle_waiting_user(
        self,
        task_id: str,
        workflow: DynamicWorkflow,
        step: AgentStep,
        result: AgentResult
    ) -> None:
        """WAITING_USER 상태 처리"""
        step.status = "waiting_user"
        workflow.phase = WorkflowPhase.WAITING_USER

        self.task_state_manager.set_waiting_user(task_id)
        self.task_state_manager.update_agent_status(
            agent_id=step.agent_id,
            status=AgentExecutionStatus.WAITING,
            current_step="사용자 입력 대기 중"
        )

        if self.ws_server and result.message:
            self.ws_server.broadcast_task_interaction(
                task_id=task_id,
                role='agent',
                message=result.message,
                agent_id=step.agent_id,
                agent_name=step.agent_name
            )

        self._logger.info(
            step.agent_id, step.agent_name,
            "❓ 사용자 입력 대기",
            task_id=task_id,
            details=result.message[:200] if result.message else ""
        )

        return None

    async def _handle_completed(
        self,
        task_id: str,
        workflow: DynamicWorkflow,
        step: AgentStep,
        result: AgentResult
    ) -> Optional[str]:
        """COMPLETED 상태 처리"""
        step.status = "completed"
        step.result = (
            result.final_data.get("output", result.message)
            if result.final_data else result.message
        )
        step.completed_at = datetime.now()

        # TaskStateManager 업데이트
        execution = self.task_state_manager.get_execution(task_id)
        if execution:
            self.task_state_manager.update_execution(
                task_id=task_id,
                completed_steps=execution.completed_steps + 1,
                status=TaskStatus.RUNNING
            )
        self.task_state_manager.set_agent_idle(step.agent_id)

        # Context에 결과 저장
        if result.final_data:
            workflow.context[f"step_{step.order}_result"] = result.final_data
        else:
            workflow.context[f"step_{step.order}_result"] = result.message

        self._logger.info(
            step.agent_id, step.agent_name,
            "✅ 작업 완료",
            task_id=task_id,
            details=result.message[:100] if result.message else ""
        )

        # Q&A Agent 응답 표시 (Gate 종료 제외)
        if step.agent_role == AgentRole.Q_AND_A:
            is_gate = (
                result.final_data and
                result.final_data.get("reason") in ["required_slots_filled", "schema_complete", "needs_worker_execution"]
            )
            if not is_gate and self.ws_server and result.message:
                self.ws_server.broadcast_task_interaction(
                    task_id=task_id,
                    role='agent',
                    message=result.message,
                    agent_id=step.agent_id,
                    agent_name=step.agent_name
                )

        # 다음 단계로 진행
        if not workflow.advance():
            return await self._generate_final_answer(task_id)

        return await self._execute_workflow(task_id)

    async def _handle_failed(
        self,
        task_id: str,
        workflow: DynamicWorkflow,
        step: AgentStep,
        result: AgentResult
    ) -> str:
        """FAILED 상태 처리"""
        step.status = "failed"

        self.task_state_manager.set_agent_idle(step.agent_id)

        error_message = (
            result.message or
            (result.error.get("message", "작업 처리 중 오류가 발생했습니다.")
             if result.error else "작업 처리 중 오류가 발생했습니다.")
        )

        self._logger.error(
            step.agent_id, step.agent_name,
            f"❌ 작업 실패: {error_message}",
            task_id=task_id
        )

        # 재계획 시도
        replan_success = await self._attempt_replan(task_id, f"agent_failure: {step.agent_name}")

        if replan_success:
            return await self._execute_workflow(task_id)
        else:
            workflow.phase = WorkflowPhase.FAILED
            self.task_state_manager.complete_execution(task_id, success=False)
            return error_message

    def _handle_unknown_status(
        self,
        task_id: str,
        workflow: DynamicWorkflow,
        step: AgentStep,
        result: AgentResult
    ) -> str:
        """알 수 없는 상태 처리"""
        step.status = "failed"
        workflow.phase = WorkflowPhase.FAILED

        self.task_state_manager.set_agent_idle(step.agent_id)
        self.task_state_manager.complete_execution(task_id, success=False)

        self._logger.error(
            step.agent_id, step.agent_name,
            f"❌ 알 수 없는 Agent 상태: {result.status}",
            task_id=task_id
        )

        return "알 수 없는 오류가 발생했습니다."

    # =========================================================================
    # Re-planning
    # =========================================================================

    async def _attempt_replan(self, task_id: str, reason: str) -> bool:
        """재계획 시도"""
        # 지연 import로 순환 참조 방지
        from ..planner_agent import planner_agent, PlannerContext

        workflow = self._workflow_manager.get_workflow(task_id)
        if not workflow:
            return False

        self._logger.warning(
            "planner-agent", "Planner Agent",
            f"⚠️ 재계획 시도: {reason}",
            task_id=task_id
        )

        # 기존 계획 수집
        previous_plan = [
            {
                "agent_id": step.agent_id,
                "agent_name": step.agent_name,
                "description": step.description,
                "status": step.status
            }
            for step in workflow.steps
        ]

        # PlannerAgent 재호출
        planner_context = PlannerContext(
            task_id=task_id,
            user_request=workflow.original_request,
            available_agents=workflow.context.get("available_agents", []),
            previous_plan=previous_plan,
            reason=f"replan: {reason}"
        )

        planner_result = await planner_agent.run(planner_context)

        if not planner_result.success:
            self._logger.error(
                "planner-agent", "Planner Agent",
                "❌ 재계획 실패",
                task_id=task_id
            )
            return False

        # 워크플로우 리셋
        workflow.steps.clear()
        workflow.current_step_index = 0

        # 새 스텝 생성
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

        self._logger.decision(
            "planner-agent", "Planner Agent",
            f"🔄 재계획 완료: {len(workflow.steps)}개 단계",
            task_id=task_id
        )

        return True

    # =========================================================================
    # Final Response
    # =========================================================================

    async def _generate_final_answer(self, task_id: str) -> str:
        """최종 응답 생성"""
        workflow = self._workflow_manager.get_workflow(task_id)
        if not workflow:
            return "워크플로우를 찾을 수 없습니다."

        workflow.phase = WorkflowPhase.FINALIZING

        self._logger.info(
            "orchestrator-system", "Orchestration Agent",
            "🎯 최종 정리 중 (Final Narration)",
            task_id=task_id
        )

        # Final Narrator를 통한 응답 생성
        final_response = await self._final_narrator.generate(workflow)

        workflow.phase = WorkflowPhase.COMPLETED
        self.task_state_manager.complete_execution(task_id, success=True)

        # WebSocket 전송
        if self.ws_server:
            self.ws_server.broadcast_task_interaction(
                task_id=task_id,
                role='agent',
                message=final_response,
                agent_id="orchestrator-final",
                agent_name="Assistant"
            )

        self._logger.info(
            "orchestrator-system", "Orchestration Agent",
            "✅ Final Narration 완료",
            task_id=task_id
        )

        return final_response

    # =========================================================================
    # Utility Methods
    # =========================================================================

    def _update_agent_running_state(
        self,
        task_id: str,
        step: AgentStep
    ) -> None:
        """Agent 실행 상태 업데이트"""
        execution = self.task_state_manager.get_execution(task_id)
        if execution:
            self.task_state_manager.set_agent_running(
                agent_id=step.agent_id,
                agent_name=step.agent_name,
                task_id=task_id,
                execution_id=execution.execution_id,
                step_description=step.description
            )
            self.task_state_manager.update_execution(
                task_id=task_id,
                active_agent_id=step.agent_id,
                active_agent_name=step.agent_name,
                current_step=step.description
            )

    def has_pending_workflow(self, task_id: str) -> bool:
        """대기 중인 워크플로우 확인"""
        return self._workflow_manager.has_pending_workflow(task_id)

    def get_workflow(self, task_id: str) -> Optional[DynamicWorkflow]:
        """워크플로우 조회"""
        return self._workflow_manager.get_workflow(task_id)

    def remove_workflow(self, task_id: str) -> None:
        """워크플로우 제거"""
        self._workflow_manager.remove_workflow(task_id)

    def get_metrics_summary(self) -> Dict[str, Any]:
        """메트릭 요약 조회"""
        if self._enable_metrics:
            return metrics_collector.get_summary()
        return {}

    def get_circuit_breaker_summary(self) -> Dict[str, Any]:
        """Circuit Breaker 상태 조회"""
        if self._circuit_breaker:
            return self._circuit_breaker.get_summary()
        return {}


# 전역 인스턴스 (하위 호환성)
orchestration_engine_v2 = OrchestrationEngineV2()
