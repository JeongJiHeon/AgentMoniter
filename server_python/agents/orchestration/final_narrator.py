#!/usr/bin/env python3
"""
Final Narrator - 최종 응답 생성

모든 워크플로우 완료 후 사용자에게 전달할 최종 응답을 생성합니다.
"""

from typing import Optional, Dict, Any, List

from .types import DynamicWorkflow, AgentRole
from ..prompts.prompt_manager import PromptManager

# 순환 참조 방지: call_llm은 메서드 내에서 지연 import


class FinalNarrator:
    """
    Final Narrator - 최종 응답 생성기

    책임:
    - Worker 결과 수집 및 정리
    - 자연스러운 최종 응답 생성
    - Agent 이름 숨기기 (사용자 친화적)
    """

    def __init__(self, prompt_manager: Optional[PromptManager] = None):
        """
        Args:
            prompt_manager: 프롬프트 템플릿 관리자
        """
        self._prompt_manager = prompt_manager or PromptManager()

    async def generate(self, workflow: DynamicWorkflow) -> str:
        """
        최종 응답 생성

        Args:
            workflow: 완료된 워크플로우

        Returns:
            최종 응답 메시지
        """
        # Worker 결과 수집 (Q&A 제외)
        worker_context = self._collect_worker_results(workflow)

        # 확정된 정보 수집
        confirmed_info = self._collect_confirmed_info(workflow)

        # LLM을 통한 Final Narration 생성
        try:
            return await self._generate_narration(
                workflow, worker_context, confirmed_info
            )
        except Exception as e:
            print(f"[FinalNarrator] Error: {e}")
            # 실패 시 자연스러운 fallback 응답
            return self.generate_fallback(workflow)

    def _collect_worker_results(self, workflow: DynamicWorkflow) -> str:
        """Worker 결과 수집"""
        all_results = workflow.get_completed_results()

        worker_results = [
            r for r in all_results
            if r.get('agent_role') != AgentRole.Q_AND_A and r.get('result')
        ]

        if not worker_results:
            return "(내부 작업 결과 없음)"

        return "\n\n---\n\n".join([
            f"[{r['agent_name']}의 작업 결과]\n{r['result']}"
            for r in worker_results
        ])

    def _collect_confirmed_info(self, workflow: DynamicWorkflow) -> str:
        """확정된 정보 수집"""
        if workflow.conversation_state:
            return workflow.conversation_state.get_facts_text()
        return "(없음)"

    async def _generate_narration(
        self,
        workflow: DynamicWorkflow,
        worker_context: str,
        confirmed_info: str
    ) -> str:
        """LLM을 통한 Final Narration 생성"""
        # 지연 import로 순환 참조 방지
        from models.orchestration import call_llm

        system_prompt = self._prompt_manager.get_final_narration_prompt()

        user_prompt = f"""**사용자의 원래 요청**:
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
- 다음 행동 1가지만 제시"""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]

        response = await call_llm(messages, max_tokens=2000)

        if not response or not response.strip():
            # LLM 응답이 없으면 fallback 사용
            return self.generate_fallback(workflow)

        return response

    def generate_fallback(self, workflow: DynamicWorkflow) -> str:
        """
        Fallback 응답 생성 (LLM 실패 시)
        대화 맥락을 활용하여 자연스러운 메시지 생성

        Args:
            workflow: 워크플로우

        Returns:
            기본 응답 메시지
        """
        confirmed_info = self._collect_confirmed_info(workflow)
        worker_results = self._collect_worker_results(workflow)

        # 확정된 정보가 있으면 활용
        if confirmed_info and confirmed_info != "(없음)":
            # 간단히 요약하여 자연스럽게 표현
            info_lines = confirmed_info.split('\n')[:3]  # 최대 3줄만
            info_summary = '\n'.join(info_lines)
            if len(confirmed_info.split('\n')) > 3:
                info_summary += "\n..."
            return f"정리해볼게요 🙂\n\n{info_summary}\n\n다음 단계를 진행할까요?"

        # Worker 결과가 있으면 활용
        if worker_results and worker_results != "(내부 작업 결과 없음)":
            # 결과에서 핵심만 추출 (첫 200자)
            result_preview = worker_results[:200]
            if len(worker_results) > 200:
                result_preview += "..."
            return f"다음과 같이 정리했습니다:\n\n{result_preview}\n\n원하시는 대로 진행할까요?"

        # 아무 정보도 없으면 간단한 확인 메시지
        return "요청하신 내용을 확인했습니다. 추가로 필요한 것이 있으면 알려주세요."
