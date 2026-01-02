#!/usr/bin/env python3
"""
Planner Agent - First-class Agent for Task Planning

사용자 요청을 분석하여 실행 전략을 수립하는 정식 Agent입니다.
Orchestration 라이프사이클에 참여하며 Re-planning을 지원합니다.
"""

import json
import re
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime

from .orchestration import call_llm
from .agent_result import AgentResult, AgentLifecycleStatus


# =============================================================================
# Planner Types
# =============================================================================

@dataclass
class PlannerContext:
    """Planner Agent 실행 컨텍스트"""
    task_id: str
    user_request: str
    available_agents: List[Dict[str, Any]]
    previous_plan: Optional[List[Dict[str, Any]]] = None
    execution_results: Optional[List[AgentResult]] = None
    reason: str = "initial"  # initial | replan | recovery

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict for logging"""
        return {
            "task_id": self.task_id,
            "user_request": self.user_request[:100] + "..." if len(self.user_request) > 100 else self.user_request,
            "available_agents_count": len(self.available_agents),
            "has_previous_plan": self.previous_plan is not None,
            "has_execution_results": self.execution_results is not None,
            "reason": self.reason
        }


@dataclass
class PlannerResult:
    """Planner Agent 실행 결과"""
    success: bool
    analysis: str
    steps: List[Dict[str, Any]]
    replan_required: bool = False
    replan_reason: Optional[str] = None
    confidence: float = 1.0  # 0.0 ~ 1.0, 계획의 확신도
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict for logging"""
        return {
            "success": self.success,
            "analysis": self.analysis[:200] + "..." if len(self.analysis) > 200 else self.analysis,
            "steps_count": len(self.steps),
            "replan_required": self.replan_required,
            "replan_reason": self.replan_reason,
            "confidence": self.confidence
        }


# =============================================================================
# Planner Agent
# =============================================================================

class PlannerAgent:
    """
    Planner Agent - Task 분석 및 실행 전략 수립

    핵심 책임:
    1. 사용자 요청 분석
    2. 실행 단계 계획 수립
    3. Agent 선택 및 순서 결정
    4. Re-planning 조건 판단

    중요 규칙 (기존 _analyze_and_plan 유지):
    1. Worker Agent는 사용자와 직접 소통하지 않음
    2. 사용자 소통은 Q&A Agent만 담당
    3. 마지막 단계는 Q&A Agent가 최종 응답 정리
    """

    def __init__(self):
        self.agent_id = "planner-agent"
        self.name = "Planner Agent"
        self.description = "Task 분석 및 실행 전략 수립"
        self.system_prompt = self._build_system_prompt()

    def _build_system_prompt(self) -> str:
        """시스템 프롬프트 생성"""
        return """당신은 멀티-에이전트 시스템의 Planner Agent입니다.
사용자 요청을 분석하여 어떤 Agent들이 어떤 순서로 작업해야 하는지 계획을 세워주세요.

중요 규칙:
1. Worker Agent들은 사용자와 직접 소통하지 않습니다. 작업만 수행합니다.
2. 사용자와 소통이 필요할 때는 Q&A Agent를 사용하세요.
3. 예: "메뉴 추천" 후 → Q&A Agent가 "어떤 메뉴로 할까요?" 질문
4. 예: "예약 진행" 후 → Q&A Agent가 "이대로 예약할까요?" 확인
5. 모든 작업 완료 후 마지막에 Q&A Agent가 최종 응답을 정리합니다
6. 각 step에 success criteria를 암묵적으로 고려하세요
7. 실패 가능성이 높은 단계에는 재계획 여지를 남기세요"""

    async def run(self, context: PlannerContext) -> PlannerResult:
        """
        Planner Agent 실행

        기존 _analyze_and_plan() 로직을 그대로 사용하되,
        Agent로서 실행됩니다.
        """
        print(f"[PlannerAgent] Starting planning - reason: {context.reason}")
        print(f"[PlannerAgent] Context: {context.to_dict()}")

        # Agent가 없으면 기본 Agent 추가
        available_agents = context.available_agents
        if not available_agents:
            available_agents = [
                {"id": "general-agent", "name": "General Agent", "type": "custom"},
            ]

        agent_descriptions = "\n".join([
            f"- {a['name']} (ID: {a['id']}): {a.get('type', 'custom')}"
            for a in available_agents
        ])

        # Re-planning 컨텍스트 추가
        replan_context = ""
        if context.reason != "initial":
            replan_context = f"\n\n**재계획 사유**: {context.reason}"
            if context.previous_plan:
                replan_context += f"\n\n**이전 계획** ({len(context.previous_plan)}개 단계):"
                for i, step in enumerate(context.previous_plan):
                    replan_context += f"\n{i+1}. {step.get('agent_name', 'Unknown')}: {step.get('description', '')}"

            if context.execution_results:
                replan_context += f"\n\n**실행 결과**:"
                for i, result in enumerate(context.execution_results):
                    status = result.status if hasattr(result, 'status') else 'unknown'
                    message = result.message if hasattr(result, 'message') else ''
                    replan_context += f"\n{i+1}. Status: {status}, Message: {message[:100] if message else 'None'}"

        messages = [
            {
                "role": "system",
                "content": self.system_prompt
            },
            {
                "role": "user",
                "content": f"""사용자 요청: {context.user_request}

사용 가능한 Agent 목록:
{agent_descriptions}
{replan_context}

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

        print(f"[PlannerAgent] Calling LLM for planning...")
        response = await call_llm(messages, max_tokens=8000, json_mode=True)
        print(f"[PlannerAgent] LLM Response: {response[:500] if response else 'EMPTY'}...")

        try:
            plan = json.loads(response)
            steps = plan.get("steps", [])
            analysis = plan.get("analysis", "")
            print(f"[PlannerAgent] Parsed {len(steps)} steps from plan")

            # 성공적인 계획 수립
            return PlannerResult(
                success=True,
                analysis=analysis,
                steps=steps,
                confidence=1.0,
                metadata={
                    "agent_id": self.agent_id,
                    "agent_name": self.name,
                    "planning_reason": context.reason,
                    "timestamp": datetime.now().isoformat()
                }
            )

        except json.JSONDecodeError as e:
            print(f"[PlannerAgent] JSON parse error: {e}")
            print(f"[PlannerAgent] Failed to parse plan: {response[:500] if response else 'EMPTY'}")

            # JSON 코드 블록에서 추출 시도
            try:
                json_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', response)
                if json_match:
                    json_text = json_match.group(1).strip()
                    plan = json.loads(json_text)
                    steps = plan.get("steps", [])
                    analysis = plan.get("analysis", "")
                    print(f"[PlannerAgent] Extracted {len(steps)} steps from code block")

                    return PlannerResult(
                        success=True,
                        analysis=analysis,
                        steps=steps,
                        confidence=0.8,  # 코드 블록 추출이므로 약간 낮은 신뢰도
                        metadata={
                            "agent_id": self.agent_id,
                            "agent_name": self.name,
                            "planning_reason": context.reason,
                            "extraction_method": "code_block",
                            "timestamp": datetime.now().isoformat()
                        }
                    )
            except Exception as e2:
                print(f"[PlannerAgent] Code block extraction also failed: {e2}")

            # 완전 실패
            return PlannerResult(
                success=False,
                analysis="",
                steps=[],
                confidence=0.0,
                metadata={
                    "agent_id": self.agent_id,
                    "agent_name": self.name,
                    "error": str(e),
                    "timestamp": datetime.now().isoformat()
                }
            )

    async def evaluate_execution(
        self,
        plan: List[Dict[str, Any]],
        results: List[AgentResult]
    ) -> Dict[str, Any]:
        """
        실행 결과 평가 및 재계획 필요성 판단

        Returns:
            {
                "replan_required": bool,
                "reason": str,
                "confidence": float
            }
        """
        print(f"[PlannerAgent] Evaluating execution - {len(results)} results")

        # 1. 실패한 단계가 있는지 확인
        failed_results = [r for r in results if r.status == AgentLifecycleStatus.FAILED]
        if failed_results:
            return {
                "replan_required": True,
                "reason": f"agent_failure: {len(failed_results)} step(s) failed",
                "confidence": 0.0
            }

        # 2. 낮은 신뢰도 확인 (partial_data에 confidence가 있는 경우)
        low_confidence_results = []
        for r in results:
            if r.partial_data and isinstance(r.partial_data, dict):
                confidence = r.partial_data.get("confidence", 1.0)
                if confidence < 0.6:
                    low_confidence_results.append(r)

        if low_confidence_results:
            avg_confidence = sum(
                r.partial_data.get("confidence", 1.0)
                for r in low_confidence_results
            ) / len(low_confidence_results)

            return {
                "replan_required": True,
                "reason": f"low_confidence: {len(low_confidence_results)} step(s) with confidence < 0.6",
                "confidence": avg_confidence
            }

        # 3. 모두 정상
        return {
            "replan_required": False,
            "reason": "execution_successful",
            "confidence": 1.0
        }


# =============================================================================
# Global Instance
# =============================================================================

planner_agent = PlannerAgent()
