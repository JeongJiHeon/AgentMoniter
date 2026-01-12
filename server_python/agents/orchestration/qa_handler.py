#!/usr/bin/env python3
"""
Q&A Handler - Q&A Agent 전용 핸들러

사용자와의 대화를 담당하는 Q&A Agent 로직을 처리합니다.
"""

import json
import re
from typing import Optional, Dict, Any, List

from .types import AgentStep, AgentRole, DynamicWorkflow
from ..agent_result import (
    AgentResult,
    AgentLifecycleStatus,
    waiting_user,
    completed,
    failed,
)
from ..task_schema import NextActionType
from ..prompts.prompt_manager import PromptManager

# 순환 참조 방지: call_llm은 메서드 내에서 지연 import


class QAHandler:
    """
    Q&A Agent 핸들러

    책임:
    - 사용자와의 대화 관리
    - Schema 기반 완료 체크
    - 질문/응답 생성
    """

    def __init__(self, prompt_manager: Optional[PromptManager] = None):
        """
        Args:
            prompt_manager: 프롬프트 템플릿 관리자
        """
        self._prompt_manager = prompt_manager or PromptManager()

    async def handle(
        self,
        workflow: DynamicWorkflow,
        step: AgentStep,
        user_input: Optional[str] = None
    ) -> AgentResult:
        """
        Q&A Agent 스텝 처리

        Args:
            workflow: 현재 워크플로우
            step: Q&A 스텝
            user_input: 사용자 입력

        Returns:
            AgentResult
        """
        # Worker 결과 수집
        worker_context = self._collect_worker_context(workflow)
        user_context = self._collect_user_context(workflow, user_input)

        try:
            # step.user_prompt가 있고 사용자 입력이 없으면 초기 질문 반환
            if step.user_prompt and not user_input:
                return self._create_initial_question(step, worker_context)

            # Schema 기반 완료 체크
            if user_input and workflow.task_schema and workflow.conversation_state:
                schema_result = self._check_schema_completion(workflow)
                if schema_result:
                    return schema_result

            # LLM을 통한 대화 생성
            return await self._generate_response(
                workflow, step, worker_context, user_context
            )

        except Exception as e:
            print(f"[QAHandler] Error: {e}")
            import traceback
            traceback.print_exc()
            return failed(f"Q&A Agent 실행 중 오류 발생: {str(e)}")

    def _collect_worker_context(self, workflow: DynamicWorkflow) -> str:
        """Worker Agent 결과 수집"""
        worker_results = workflow.get_completed_results()

        worker_context_parts = []
        for r in worker_results:
            if r.get('result') and r.get('agent_role') != AgentRole.Q_AND_A:
                worker_context_parts.append(
                    f"[{r['agent_name']} 작업 결과]\n{r['result']}"
                )

        return "\n\n---\n\n".join(worker_context_parts) if worker_context_parts else "(아직 없음)"

    def _collect_user_context(
        self,
        workflow: DynamicWorkflow,
        user_input: Optional[str]
    ) -> str:
        """사용자 응답 컨텍스트 수집"""
        worker_results = workflow.get_completed_results()

        user_responses = []
        for r in worker_results:
            if r.get('user_input'):
                user_responses.append(f"[사용자 응답]\n{r['user_input']}")

        user_context = "\n\n---\n\n".join(user_responses) if user_responses else "(없음)"

        if user_input:
            user_context += f"\n\n---\n\n[현재 사용자 입력]\n{user_input}"

        return user_context

    def _create_initial_question(
        self,
        step: AgentStep,
        worker_context: str
    ) -> AgentResult:
        """초기 질문 생성"""
        message = step.user_prompt

        # Worker 결과가 있으면 자연스럽게 추가
        if worker_context.strip() != "(아직 없음)":
            # 최신 Worker 결과를 포함
            message = f"{worker_context}\n\n{message}"

        return waiting_user(
            message=message,
            partial_data={
                "agent_name": step.agent_name,
                "step_description": step.description
            }
        )

    def _check_schema_completion(
        self,
        workflow: DynamicWorkflow
    ) -> Optional[AgentResult]:
        """Schema 기반 완료 체크"""
        next_action = workflow.task_schema.get_next_action(
            workflow.conversation_state
        )

        if next_action.action_type == NextActionType.COMPLETE:
            return completed(
                final_data={
                    "conversation_state": workflow.conversation_state.to_dict(),
                    "reason": "schema_complete",
                },
                message=""
            )

        if next_action.action_type == NextActionType.EXECUTE:
            workflow.conversation_state.set_flag("needs_worker_execution", True)
            if next_action.worker_id:
                workflow.context["next_worker_id"] = next_action.worker_id

            return completed(
                final_data={
                    "conversation_state": workflow.conversation_state.to_dict(),
                    "reason": "needs_worker_execution",
                    "worker_id": next_action.worker_id,
                },
                message=""
            )

        return None

    async def _generate_response(
        self,
        workflow: DynamicWorkflow,
        step: AgentStep,
        worker_context: str,
        user_context: str
    ) -> AgentResult:
        """LLM을 통한 응답 생성"""
        # 지연 import로 순환 참조 방지
        from models.orchestration import call_llm

        # 프롬프트 로드
        system_prompt = self._prompt_manager.get_qa_system_prompt()

        # 확정된 정보 텍스트
        facts_text = "(없음)"
        missing_facts = "(없음)"
        decisions_text = "(없음)"

        if workflow.conversation_state:
            facts_text = workflow.conversation_state.get_facts_text()
            decisions_text = workflow.conversation_state.get_decisions_text()

        if workflow.task_schema and workflow.conversation_state:
            missing = workflow.task_schema.get_missing_facts(workflow.conversation_state)
            missing_facts = ', '.join(missing) if missing else '(없음)'

        user_prompt = f"""**사용자 요청**: {workflow.original_request}

**현재 단계**: {step.description}

---

**🔒 Context** (for reference only - DO NOT list or summarize in your message):

확정된 정보 (절대 다시 묻지 말 것):
{facts_text}

미확정 정보 (필요한 facts):
{missing_facts}

의사결정 상태:
{decisions_text}

Worker 결과:
{worker_context}

대화 기록:
{user_context}

---

**💬 Your Task**:
위 Context를 참고하여, 사용자에게 **지금 필요한 질문 1개만** 생성하세요.

JSON 형식으로 응답하세요."""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]

        response = await call_llm(messages, max_tokens=4000, json_mode=True)

        return self._parse_llm_response(response, step)

    def _parse_llm_response(
        self,
        response: str,
        step: AgentStep
    ) -> AgentResult:
        """LLM 응답 파싱"""
        try:
            # JSON 코드 블록 추출
            json_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', response)
            if json_match:
                response = json_match.group(1).strip()

            result_data = json.loads(response)
            status_str = result_data.get("status", "COMPLETED").upper()
            message = result_data.get("message", "작업이 완료되었습니다.")

            if status_str == "WAITING_USER":
                return waiting_user(
                    message=message,
                    partial_data={
                        "agent_name": step.agent_name,
                        "step_description": step.description
                    }
                )
            else:
                return completed(
                    final_data={
                        "message": message,
                        "agent_name": step.agent_name
                    },
                    message=message
                )

        except (json.JSONDecodeError, KeyError) as e:
            print(f"[QAHandler] JSON parse error: {e}")
            # 파싱 실패 시 기본값
            return waiting_user(
                message=response if response else "질문이 있습니다.",
                partial_data={"agent_name": step.agent_name}
            )
