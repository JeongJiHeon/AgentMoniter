#!/usr/bin/env python3
"""
Enhanced Planner Agent - Claude Code-like Agent Architecture

기존 Planner Agent에 다음 시스템들을 통합:
- Tool System: Tool Registry, Tool Executor
- Agentic Loop: ReAct pattern
- Task Decomposition: Task Graph, DAG
- Context Management: Token limits, Summarization
- Memory System: Short-term/Long-term memory
- Reasoning: Chain-of-Thought, Self-Critique
- Sub-agents: Hierarchical agent system
"""

import json
import re
import asyncio
from typing import Dict, List, Optional, Any, Callable, Awaitable
from dataclasses import dataclass, field
from datetime import datetime

from models.orchestration import call_llm
from .agent_result import AgentResult, AgentLifecycleStatus

# New system imports
from tools import get_tool_registry, ToolExecutor
from tools.builtin import register_all_builtin_tools
from agentic import ReActLoop, ReasoningEngine, SelfCritique, ReasoningStrategy
from task_graph import TaskDecomposer, TaskGraph, GraphExecutor, DecompositionStrategy
from context import ContextManager, MessageRole, MemorySystem, MemoryType
from subagents import SubagentManager, SubagentSpec


# =============================================================================
# Enhanced Planner Types
# =============================================================================

@dataclass
class EnhancedPlannerContext:
    """Enhanced Planner Agent 실행 컨텍스트"""
    task_id: str
    user_request: str
    available_agents: List[Dict[str, Any]]
    previous_plan: Optional[List[Dict[str, Any]]] = None
    execution_results: Optional[List[AgentResult]] = None
    reason: str = "initial"  # initial | replan | recovery
    use_task_decomposition: bool = True
    use_react_loop: bool = False  # ReAct은 선택적 사용
    use_reasoning: bool = True
    enable_critique: bool = True
    context: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict for logging"""
        return {
            "task_id": self.task_id,
            "user_request": self.user_request[:100] + "..." if len(self.user_request) > 100 else self.user_request,
            "available_agents_count": len(self.available_agents),
            "has_previous_plan": self.previous_plan is not None,
            "has_execution_results": self.execution_results is not None,
            "reason": self.reason,
            "use_task_decomposition": self.use_task_decomposition,
            "use_react_loop": self.use_react_loop,
            "use_reasoning": self.use_reasoning,
        }


@dataclass
class EnhancedPlannerResult:
    """Enhanced Planner Agent 실행 결과"""
    success: bool
    analysis: str
    steps: List[Dict[str, Any]]
    replan_required: bool = False
    replan_reason: Optional[str] = None
    confidence: float = 1.0
    task_graph: Optional[TaskGraph] = None
    reasoning_chain: Optional[List[str]] = None
    critique_result: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict for logging"""
        result = {
            "success": self.success,
            "analysis": self.analysis[:200] + "..." if len(self.analysis) > 200 else self.analysis,
            "steps_count": len(self.steps),
            "replan_required": self.replan_required,
            "replan_reason": self.replan_reason,
            "confidence": self.confidence,
            "has_task_graph": self.task_graph is not None,
            "has_reasoning_chain": self.reasoning_chain is not None,
            "has_critique": self.critique_result is not None,
        }
        if self.metadata:
            result["metadata"] = self.metadata
        return result


# =============================================================================
# Enhanced Planner Agent
# =============================================================================

class EnhancedPlannerAgent:
    """
    Enhanced Planner Agent - Claude Code-like Architecture

    핵심 기능:
    1. Task Decomposition: 복잡한 태스크를 DAG로 분해
    2. ReAct Loop: Think → Plan → Act → Observe → Reflect
    3. Tool System: 동적 도구 발견 및 실행
    4. Context Management: 컨텍스트 관리 및 요약
    5. Memory System: Short-term/Long-term 메모리
    6. Reasoning: Chain-of-Thought, Self-Critique
    7. Sub-agents: 계층적 에이전트 시스템
    """

    def __init__(
        self,
        max_context_tokens: int = 100000,
        enable_tools: bool = True,
        enable_memory: bool = True,
        enable_subagents: bool = True,
    ):
        self.agent_id = "enhanced-planner-agent"
        self.name = "Enhanced Planner Agent"
        self.description = "Claude Code-like task planning with advanced capabilities"

        # Tool System
        self.enable_tools = enable_tools
        if enable_tools:
            self.tool_registry = get_tool_registry()
            register_all_builtin_tools(self.tool_registry)
            self.tool_executor = ToolExecutor(self.tool_registry)
            print(f"[EnhancedPlanner] Registered {len(self.tool_registry.get_names())} tools")

        # Context Management
        self.context_manager = ContextManager(
            max_tokens=max_context_tokens,
            summarize_func=self._summarize_context,
        )

        # Memory System
        self.enable_memory = enable_memory
        if enable_memory:
            self.memory = MemorySystem(
                max_short_term=100,
                max_long_term=1000,
            )

        # Reasoning & Critique
        self.reasoning_engine = ReasoningEngine(
            llm_generate=self._llm_generate,
            strategy=ReasoningStrategy.CHAIN_OF_THOUGHT,
        )
        self.critique_system = SelfCritique(
            llm_generate=self._llm_generate,
            quality_threshold=7.0,
        )

        # Task Decomposition
        self.task_decomposer = TaskDecomposer(
            llm_generate=self._llm_generate,
            max_depth=3,
            max_subtasks=10,
        )

        # Sub-agent Manager
        self.enable_subagents = enable_subagents
        if enable_subagents:
            self.subagent_manager = SubagentManager(
                execute_agent=self._execute_subagent,
                max_depth=3,
                max_concurrent=5,
            )

        self.system_prompt = self._build_system_prompt()

    def _build_system_prompt(self) -> str:
        """시스템 프롬프트 생성"""
        return """당신은 고급 멀티-에이전트 시스템의 Enhanced Planner Agent입니다.

핵심 역할:
1. 사용자 요청을 분석하고 실행 전략을 수립합니다
2. 복잡한 태스크를 subtask로 분해합니다
3. 적절한 Agent와 Tool을 선택합니다
4. 실행 순서와 의존성을 관리합니다

중요 규칙:
1. Worker Agent들은 사용자와 직접 소통하지 않습니다
2. 사용자 소통은 Q&A Agent만 담당합니다
3. 각 단계에 명확한 성공 기준을 설정합니다
4. 실패 가능성을 고려하여 재계획 여지를 남깁니다
5. 도구를 적극 활용하여 효율성을 높입니다

가용 능력:
- Task Decomposition: 복잡한 태스크 분해
- Tool Execution: 파일 조작, 검색, Bash 등
- Chain-of-Thought: 단계별 추론
- Self-Critique: 계획 품질 평가"""

    async def run(self, context: EnhancedPlannerContext) -> EnhancedPlannerResult:
        """
        Enhanced Planner Agent 실행

        Args:
            context: 실행 컨텍스트

        Returns:
            EnhancedPlannerResult
        """
        print(f"[EnhancedPlanner] Starting enhanced planning")
        print(f"[EnhancedPlanner] Context: {context.to_dict()}")

        # Add to context manager
        self.context_manager.add_message(
            MessageRole.USER,
            f"Task: {context.user_request}",
            metadata={"task_id": context.task_id}
        )

        # Add to memory
        if self.enable_memory:
            self.memory.add_memory(
                MemoryType.EXPERIENCE,
                f"Planning task: {context.user_request}",
                importance=0.8,
                tags={"planning", "task", context.task_id},
            )

        try:
            # Phase 1: Task Analysis with Reasoning
            if context.use_reasoning:
                analysis_result = await self._analyze_with_reasoning(context)
            else:
                analysis_result = await self._analyze_basic(context)

            # Phase 2: Task Decomposition (if enabled)
            if context.use_task_decomposition and self._is_complex_task(context.user_request):
                decomposition = await self._decompose_task(context, analysis_result)
                steps = self._convert_decomposition_to_steps(decomposition, context.available_agents)
                task_graph = self.task_decomposer.create_task_graph(decomposition)
            else:
                # Simple planning
                steps = await self._plan_simple(context, analysis_result)
                task_graph = None

            # Phase 3: Self-Critique (if enabled)
            critique_result = None
            if context.enable_critique:
                critique_result = await self._critique_plan(context, steps)

                # Revise if quality is low
                if critique_result.should_revise and critique_result.overall_quality < 7.0:
                    print(f"[EnhancedPlanner] Plan quality low ({critique_result.overall_quality:.1f}), revising...")
                    steps = await self._revise_plan(context, steps, critique_result)
                    # Re-critique
                    critique_result = await self._critique_plan(context, steps)

            # Calculate confidence
            confidence = self._calculate_confidence(
                analysis_result,
                critique_result,
                len(steps)
            )

            # Build result
            result = EnhancedPlannerResult(
                success=True,
                analysis=analysis_result.get("analysis", ""),
                steps=steps,
                confidence=confidence,
                task_graph=task_graph,
                reasoning_chain=analysis_result.get("reasoning_chain"),
                critique_result=critique_result.to_dict() if critique_result else None,
                metadata={
                    "agent_id": self.agent_id,
                    "agent_name": self.name,
                    "planning_reason": context.reason,
                    "timestamp": datetime.now().isoformat(),
                    "tools_available": len(self.tool_registry.get_names()) if self.enable_tools else 0,
                }
            )

            # Add to memory
            if self.enable_memory:
                self.memory.add_memory(
                    MemoryType.PATTERN,
                    f"Successfully planned {len(steps)} steps for: {context.user_request[:100]}",
                    importance=0.7,
                    confidence=confidence,
                    tags={"planning_success", context.task_id},
                )

            print(f"[EnhancedPlanner] Planning complete: {len(steps)} steps, confidence={confidence:.2f}")
            return result

        except Exception as e:
            print(f"[EnhancedPlanner] Planning failed: {e}")
            import traceback
            traceback.print_exc()

            # Add failure to memory
            if self.enable_memory:
                self.memory.add_memory(
                    MemoryType.EXPERIENCE,
                    f"Planning failed for: {context.user_request[:100]} - {str(e)}",
                    importance=0.6,
                    tags={"planning_failure", context.task_id},
                )

            return EnhancedPlannerResult(
                success=False,
                analysis="",
                steps=[],
                confidence=0.0,
                metadata={
                    "error": str(e),
                    "agent_id": self.agent_id,
                    "timestamp": datetime.now().isoformat(),
                }
            )

    async def _analyze_with_reasoning(
        self,
        context: EnhancedPlannerContext
    ) -> Dict[str, Any]:
        """Chain-of-Thought를 사용한 태스크 분석"""
        print("[EnhancedPlanner] Analyzing with Chain-of-Thought reasoning...")

        # Recall relevant memories
        relevant_memories = []
        if self.enable_memory:
            relevant_memories = self.memory.recall(
                tags={"planning", "pattern"},
                limit=5,
            )

        # Build reasoning prompt
        memory_context = ""
        if relevant_memories:
            memory_context = "\n\n관련 경험:\n" + "\n".join([
                f"- {m.content}" for m in relevant_memories
            ])

        problem = f"""사용자 요청을 분석해주세요:

요청: {context.user_request}

사용 가능한 Agent 수: {len(context.available_agents)}
사용 가능한 Tool 수: {len(self.tool_registry.get_names()) if self.enable_tools else 0}
{memory_context}

분석 항목:
1. 요청의 핵심 목표는 무엇인가?
2. 필요한 정보나 리소스는?
3. 예상되는 어려움은?
4. 어떤 접근 방식이 최적인가?
5. 성공 기준은?"""

        reasoning_result = await self.reasoning_engine.reason(
            problem=problem,
            context=context.context,
        )

        return {
            "analysis": reasoning_result.get("reasoning_chain", ""),
            "reasoning_chain": reasoning_result.get("steps", []),
            "strategy": reasoning_result.get("strategy", "chain_of_thought"),
        }

    async def _analyze_basic(
        self,
        context: EnhancedPlannerContext
    ) -> Dict[str, Any]:
        """기본 LLM 분석"""
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": f"사용자 요청을 분석해주세요: {context.user_request}"}
        ]

        response = await call_llm(messages, max_tokens=2000)

        return {
            "analysis": response,
            "reasoning_chain": None,
            "strategy": "basic",
        }

    def _is_complex_task(self, request: str) -> bool:
        """태스크가 복잡한지 판단"""
        # 간단한 휴리스틱: 길이, 키워드 등
        complexity_indicators = [
            len(request) > 200,
            "여러" in request or "multiple" in request.lower(),
            "복잡" in request or "complex" in request.lower(),
            "단계" in request or "step" in request.lower(),
            request.count("그리고") > 2 or request.count("and") > 2,
        ]

        return sum(complexity_indicators) >= 2

    async def _decompose_task(
        self,
        context: EnhancedPlannerContext,
        analysis_result: Dict[str, Any]
    ) -> Any:
        """태스크를 subtask로 분해"""
        print("[EnhancedPlanner] Decomposing complex task...")

        decomposition = await self.task_decomposer.decompose(
            task=context.user_request,
            context={
                "analysis": analysis_result.get("analysis", ""),
                "available_agents": context.available_agents,
                "available_tools": self.tool_registry.get_names() if self.enable_tools else [],
            },
            strategy=DecompositionStrategy.AUTO,
        )

        print(f"[EnhancedPlanner] Decomposed into {len(decomposition.subtasks)} subtasks")
        return decomposition

    def _convert_decomposition_to_steps(
        self,
        decomposition: Any,
        available_agents: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Decomposition을 실행 단계로 변환"""
        steps = []

        # Agent ID 매핑 (간단한 매칭)
        agent_map = {agent["name"].lower(): agent for agent in available_agents}

        for i, subtask in enumerate(decomposition.subtasks):
            # Find matching agent
            agent_id = "general-agent"
            agent_name = "General Agent"

            for key in agent_map:
                if key in subtask.name.lower() or key in subtask.description.lower():
                    agent_id = agent_map[key]["id"]
                    agent_name = agent_map[key]["name"]
                    break

            step = {
                "agent_id": agent_id,
                "agent_name": agent_name,
                "role": "worker",
                "description": subtask.description,
                "dependencies": subtask.dependencies,
                "complexity": subtask.estimated_complexity,
                "task_type": subtask.task_type,
            }
            steps.append(step)

        # Add final Q&A step
        steps.append({
            "agent_id": "qa-agent-system",
            "agent_name": "Q&A Agent",
            "role": "q_and_a",
            "description": "최종 결과를 사용자에게 전달",
        })

        return steps

    async def _plan_simple(
        self,
        context: EnhancedPlannerContext,
        analysis_result: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """간단한 플래닝 (기존 방식)"""
        print("[EnhancedPlanner] Using simple planning...")

        agent_descriptions = "\n".join([
            f"- {a['name']} (ID: {a['id']}): {a.get('type', 'custom')}"
            for a in context.available_agents
        ])

        messages = [
            {"role": "system", "content": self.system_prompt},
            {
                "role": "user",
                "content": f"""사용자 요청: {context.user_request}

분석 결과: {analysis_result.get('analysis', '')[:500]}

사용 가능한 Agent:
{agent_descriptions}

JSON 형식으로 실행 계획을 작성해주세요:
```json
{{
  "steps": [
    {{
      "agent_id": "agent-id",
      "agent_name": "Agent 이름",
      "role": "worker",
      "description": "수행할 작업"
    }}
  ]
}}
```"""
            }
        ]

        response = await call_llm(messages, max_tokens=4000, json_mode=True)

        try:
            plan = json.loads(response)
            return plan.get("steps", [])
        except:
            # JSON 추출 시도
            json_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', response)
            if json_match:
                plan = json.loads(json_match.group(1))
                return plan.get("steps", [])

            return []

    async def _critique_plan(
        self,
        context: EnhancedPlannerContext,
        steps: List[Dict[str, Any]]
    ) -> Any:
        """계획 품질 평가"""
        print("[EnhancedPlanner] Critiquing plan...")

        plan_description = "\n".join([
            f"{i+1}. {step.get('agent_name', 'Unknown')}: {step.get('description', '')}"
            for i, step in enumerate(steps)
        ])

        critique_result = await self.critique_system.critique_result(
            task=context.user_request,
            result=plan_description,
            context={"step_count": len(steps)},
        )

        print(f"[EnhancedPlanner] Critique quality: {critique_result.overall_quality:.1f}/10")
        return critique_result

    async def _revise_plan(
        self,
        context: EnhancedPlannerContext,
        steps: List[Dict[str, Any]],
        critique_result: Any
    ) -> List[Dict[str, Any]]:
        """피드백을 반영하여 계획 수정"""
        print("[EnhancedPlanner] Revising plan based on critique...")

        suggestions = "\n".join(critique_result.suggestions_for_improvement)
        issues = "\n".join([
            f"- {issue.description}" for issue in critique_result.issues
        ])

        messages = [
            {"role": "system", "content": self.system_prompt},
            {
                "role": "user",
                "content": f"""다음 계획을 개선해주세요:

원래 요청: {context.user_request}

현재 계획:
{json.dumps(steps, indent=2, ensure_ascii=False)}

발견된 문제:
{issues}

개선 제안:
{suggestions}

개선된 계획을 JSON 형식으로 작성해주세요."""
            }
        ]

        response = await call_llm(messages, max_tokens=4000, json_mode=True)

        try:
            revised = json.loads(response)
            return revised.get("steps", steps)  # 파싱 실패시 원본 반환
        except:
            return steps

    def _calculate_confidence(
        self,
        analysis_result: Dict[str, Any],
        critique_result: Any,
        step_count: int
    ) -> float:
        """계획의 확신도 계산"""
        confidence = 1.0

        # Critique 결과 반영
        if critique_result:
            critique_confidence = critique_result.overall_quality / 10
            confidence *= critique_confidence

        # 복잡도 반영 (너무 많은 단계는 불확실성 증가)
        if step_count > 10:
            complexity_penalty = max(0.7, 1.0 - (step_count - 10) * 0.03)
            confidence *= complexity_penalty

        # Reasoning 전략 반영
        strategy = analysis_result.get("strategy", "basic")
        if strategy == "tree_of_thoughts":
            confidence *= 1.1  # ToT는 더 신뢰
        elif strategy == "basic":
            confidence *= 0.9  # Basic은 덜 신뢰

        return min(1.0, max(0.0, confidence))

    async def _llm_generate(self, prompt: str, history: Optional[List[Dict]] = None) -> str:
        """LLM 생성 함수 (Reasoning, Critique용)"""
        messages = []
        if history:
            messages.extend(history)
        messages.append({"role": "user", "content": prompt})

        return await call_llm(messages, max_tokens=4000)

    async def _summarize_context(self, messages: List[Any]) -> str:
        """컨텍스트 요약 함수"""
        content = "\n\n".join([
            f"{msg.role.value}: {msg.content[:200]}..."
            for msg in messages
        ])

        summary_prompt = f"""다음 대화 내용을 간결하게 요약해주세요:

{content}

핵심 내용만 3-5문장으로 요약:"""

        return await self._llm_generate(summary_prompt)

    async def _execute_subagent(self, spec: SubagentSpec) -> Any:
        """Sub-agent 실행 함수"""
        # Placeholder - 실제로는 적절한 agent를 실행
        print(f"[EnhancedPlanner] Executing sub-agent: {spec.name}")

        # 간단한 구현 예시
        from subagents import SubagentResult

        return SubagentResult(
            success=True,
            output=f"Sub-agent {spec.name} completed task: {spec.task}",
            iterations=1,
        )

    def get_stats(self) -> Dict[str, Any]:
        """통계 정보"""
        stats = {
            "agent_id": self.agent_id,
            "agent_name": self.name,
        }

        if self.enable_tools:
            stats["tools"] = self.tool_registry.get_tool_info()

        stats["context"] = self.context_manager.get_stats()

        if self.enable_memory:
            stats["memory"] = self.memory.get_stats()

        if self.enable_subagents:
            stats["subagents"] = self.subagent_manager.get_stats()

        return stats


# =============================================================================
# Global Instance
# =============================================================================

enhanced_planner_agent = EnhancedPlannerAgent(
    max_context_tokens=100000,
    enable_tools=True,
    enable_memory=True,
    enable_subagents=True,
)
