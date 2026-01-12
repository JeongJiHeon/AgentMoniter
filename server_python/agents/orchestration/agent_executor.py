#!/usr/bin/env python3
"""
Agent Executor - Agent 실행 로직

Worker Agent와 MCP Agent 실행을 담당합니다.
Q&A Agent는 별도의 QAHandler에서 처리합니다.
"""

from typing import Dict, List, Optional, Any, TYPE_CHECKING

from .types import AgentStep, AgentRole, DynamicWorkflow
from ..agent_result import (
    AgentResult,
    completed,
    failed,
)

# 순환 참조 방지를 위한 지연 import
if TYPE_CHECKING:
    pass  # 타입 힌트만 필요한 경우 여기에 추가


class AgentExecutor:
    """
    Agent 실행기

    책임:
    - Worker Agent 실행 (LLM 기반)
    - MCP Agent 실행 (Notion, Slack 등)
    - 실행 결과 반환
    """

    def __init__(self, mcp_agents: Dict[str, Any] = None):
        """
        Args:
            mcp_agents: MCP Agent 인스턴스 딕셔너리 (예: {"notion-mcp": notion_agent})
        """
        self._mcp_agents = mcp_agents or {}

    def register_mcp_agent(self, agent_type: str, agent_instance: Any) -> None:
        """MCP Agent 등록"""
        self._mcp_agents[agent_type] = agent_instance

    def get_mcp_agent(self, agent_type: str) -> Optional[Any]:
        """MCP Agent 조회"""
        return self._mcp_agents.get(agent_type)

    def get_available_mcp_agents(self) -> List[str]:
        """사용 가능한 MCP Agent 타입 목록"""
        return list(self._mcp_agents.keys())

    async def execute(
        self,
        workflow: DynamicWorkflow,
        step: AgentStep,
        user_input: Optional[str] = None
    ) -> AgentResult:
        """
        Agent 실행 (Worker/MCP)

        Args:
            workflow: 현재 워크플로우
            step: 실행할 스텝
            user_input: 사용자 입력 (있는 경우)

        Returns:
            AgentResult
        """
        # MCP Agent 체크
        agent_type = self._detect_mcp_agent_type(step)

        if agent_type and agent_type in self._mcp_agents:
            return await self._execute_mcp_agent(
                workflow, step, agent_type, user_input
            )

        # 일반 Worker Agent (LLM 기반)
        return await self._execute_llm_agent(workflow, step, user_input)

    def _detect_mcp_agent_type(self, step: AgentStep) -> Optional[str]:
        """스텝에서 MCP Agent 타입 감지"""
        for mcp_type in self._mcp_agents.keys():
            if mcp_type in step.agent_id or mcp_type in step.agent_name.lower():
                return mcp_type
        return None

    async def _execute_mcp_agent(
        self,
        workflow: DynamicWorkflow,
        step: AgentStep,
        agent_type: str,
        user_input: Optional[str] = None
    ) -> AgentResult:
        """MCP Agent 실행"""
        mcp_agent = self._mcp_agents[agent_type]

        # Context 구성
        context = {
            "task_id": workflow.task_id,
            "original_request": workflow.original_request,
            "user_input": user_input,
            "previous_results": workflow.get_completed_results(),
        }

        # ConversationState에서 Facts/Decisions 추가
        if workflow.conversation_state:
            context["facts"] = workflow.conversation_state.facts
            context["decisions"] = workflow.conversation_state.decisions

        try:
            result = await mcp_agent.execute_task(step.description, context)
            return result
        except Exception as e:
            return failed(f"MCP Agent 실행 실패: {str(e)}")

    async def _execute_llm_agent(
        self,
        workflow: DynamicWorkflow,
        step: AgentStep,
        user_input: Optional[str] = None
    ) -> AgentResult:
        """LLM 기반 Worker Agent 실행"""
        # 지연 import로 순환 참조 방지
        from models.orchestration import call_llm

        # 이전 결과들을 컨텍스트로 포함
        prev_results = workflow.get_completed_results()
        prev_text = self._build_previous_results_text(prev_results)

        # 현재 사용자 입력 포함
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

    def _build_previous_results_text(
        self,
        prev_results: List[Dict[str, Any]]
    ) -> str:
        """이전 결과 텍스트 생성"""
        if not prev_results:
            return ""

        text = "\n\n**이전 작업 결과:**\n" + "\n".join([
            f"- {r['agent_name']}: {r['result']}"
            for r in prev_results
            if r['result']
        ])

        # 사용자 입력도 포함
        user_inputs = [r for r in prev_results if r.get('user_input')]
        if user_inputs:
            text += "\n\n**사용자 선택:**\n" + "\n".join([
                f"- {r['user_input']}" for r in user_inputs
            ])

        return text
