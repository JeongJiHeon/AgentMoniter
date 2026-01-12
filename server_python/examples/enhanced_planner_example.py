#!/usr/bin/env python3
"""
Enhanced Planner Agent 사용 예시

이 파일은 Enhanced Planner Agent의 다양한 기능을 데모합니다.
"""

import asyncio
import json
from typing import Dict, List, Any

# Mock LLM function (실제로는 Claude API 사용)
async def mock_llm_call(messages: List[Dict[str, str]], **kwargs) -> str:
    """Mock LLM call for demonstration"""
    print(f"[MockLLM] Called with {len(messages)} messages")

    # 간단한 응답 생성
    last_message = messages[-1]["content"] if messages else ""

    if "분석" in last_message or "analysis" in last_message.lower():
        return """단계별 분석:
1. 사용자는 프로젝트 구조 파악을 원함
2. 파일 시스템 탐색 필요
3. 결과를 정리하여 보고"""

    elif "JSON" in last_message or "json" in last_message:
        return json.dumps({
            "analysis": "태스크를 3단계로 분해했습니다",
            "steps": [
                {
                    "agent_id": "general-agent",
                    "agent_name": "General Agent",
                    "role": "worker",
                    "description": "프로젝트 디렉토리 스캔"
                },
                {
                    "agent_id": "general-agent",
                    "agent_name": "General Agent",
                    "role": "worker",
                    "description": "파일 구조 분석"
                },
                {
                    "agent_id": "qa-agent-system",
                    "agent_name": "Q&A Agent",
                    "role": "q_and_a",
                    "description": "결과 사용자에게 전달"
                }
            ]
        })

    else:
        return "처리 완료"


async def example_1_basic_planning():
    """예시 1: 기본 Planning"""
    print("\n" + "="*60)
    print("예시 1: 기본 Enhanced Planning")
    print("="*60 + "\n")

    # Mock LLM function 패치
    import sys
    sys.path.insert(0, '/Users/1113804/Desktop/Code/24.AgentMoniter/agent-monitor_v2/server_python')

    from agents import enhanced_planner_agent, EnhancedPlannerContext

    # Mock LLM 함수 주입
    from models import orchestration
    original_call_llm = orchestration.call_llm
    orchestration.call_llm = mock_llm_call

    try:
        context = EnhancedPlannerContext(
            task_id="demo-1",
            user_request="프로젝트의 Python 파일들을 찾아서 구조를 분석해줘",
            available_agents=[
                {"id": "general-agent", "name": "General Agent", "type": "custom"}
            ],
            use_task_decomposition=False,  # 간단한 planning만
            use_reasoning=True,
            enable_critique=False,  # 빠른 데모를 위해 비활성화
        )

        result = await enhanced_planner_agent.run(context)

        print(f"✓ Planning 성공: {result.success}")
        print(f"✓ 분석: {result.analysis[:200]}...")
        print(f"✓ 단계 수: {len(result.steps)}")
        print(f"✓ 확신도: {result.confidence:.2%}")

        for i, step in enumerate(result.steps):
            print(f"  {i+1}. {step.get('agent_name', 'Unknown')}: {step.get('description', '')}")

    finally:
        # Restore
        orchestration.call_llm = original_call_llm


async def example_2_tool_system():
    """예시 2: Tool System 사용"""
    print("\n" + "="*60)
    print("예시 2: Tool System")
    print("="*60 + "\n")

    from tools import get_tool_registry, ToolExecutor
    from tools.builtin import register_all_builtin_tools

    # Tool registry 초기화
    registry = get_tool_registry()
    registry.clear()  # 기존 도구 제거
    register_all_builtin_tools(registry)

    print(f"✓ 등록된 도구 수: {len(registry.get_names())}")
    print(f"✓ 도구 목록:")

    for tool_name in registry.get_names()[:10]:
        tool = registry.get(tool_name)
        if tool:
            print(f"  - {tool.name}: {tool.description[:60]}...")

    # Tool executor
    executor = ToolExecutor(registry)

    # Think tool 사용
    print(f"\n✓ Think Tool 실행:")
    result = await executor.execute(
        "think",
        {"thought": "프로젝트 구조 분석 전략을 수립합니다"}
    )

    if result.success:
        print(f"  - 성공: {result.output}")
    else:
        print(f"  - 실패: {result.error}")

    # Stats
    stats = executor.get_stats()
    print(f"\n✓ Executor 통계:")
    print(f"  - 총 실행: {stats['total_executions']}")
    print(f"  - 성공률: {stats['success_rate']}%")


async def example_3_memory_system():
    """예시 3: Memory System"""
    print("\n" + "="*60)
    print("예시 3: Memory System")
    print("="*60 + "\n")

    from context import MemorySystem, MemoryType

    memory = MemorySystem()

    # 메모리 추가
    print("✓ 메모리 추가:")
    memory.add_memory(
        MemoryType.FACT,
        "사용자는 Python 프로젝트 분석을 요청함",
        importance=0.8,
        tags={"user_request", "python"}
    )

    memory.add_memory(
        MemoryType.PATTERN,
        "파일 검색 시 glob 도구가 효율적임",
        importance=0.9,
        tags={"tool_usage", "pattern"}
    )

    memory.add_memory(
        MemoryType.PREFERENCE,
        "사용자는 상세한 분석을 선호함",
        importance=0.7,
        tags={"user_preference"}
    )

    stats = memory.get_stats()
    print(f"  - Short-term: {stats['short_term_count']}")
    print(f"  - Long-term: {stats['long_term_count']}")

    # 메모리 회상
    print(f"\n✓ 관련 메모리 회상 (tag: python):")
    relevant = memory.recall(
        tags={"python"},
        limit=5
    )

    for mem in relevant:
        print(f"  - [{mem.type.value}] {mem.content}")
        print(f"    Importance: {mem.importance}, Accessed: {mem.access_count} times")


async def example_4_context_manager():
    """예시 4: Context Manager"""
    print("\n" + "="*60)
    print("예시 4: Context Manager")
    print("="*60 + "\n")

    from context import ContextManager, MessageRole

    context_mgr = ContextManager(max_tokens=10000)

    # 메시지 추가
    print("✓ 대화 추가:")
    context_mgr.add_message(
        MessageRole.USER,
        "프로젝트 구조를 설명해줘"
    )

    context_mgr.add_message(
        MessageRole.ASSISTANT,
        "프로젝트는 다음과 같이 구성되어 있습니다..."
    )

    context_mgr.add_message(
        MessageRole.USER,
        "좀 더 자세히 설명해줄 수 있어?"
    )

    # 통계
    stats = context_mgr.get_stats()
    print(f"  - 총 메시지: {stats['total_messages']}")
    print(f"  - 총 토큰: {stats['total_tokens']}")
    print(f"  - 사용률: {stats['usage_percent']}%")
    print(f"  - Role 분포: {stats['role_distribution']}")

    # 컨텍스트 윈도우
    window = context_mgr.get_context_window()
    print(f"\n✓ Context Window:")
    print(f"  - 메시지 수: {len(window.messages)}")
    print(f"  - 토큰: {window.total_tokens}/{window.max_tokens}")


async def example_5_task_decomposition():
    """예시 5: Task Decomposition"""
    print("\n" + "="*60)
    print("예시 5: Task Decomposition")
    print("="*60 + "\n")

    from task_graph import TaskDecomposer

    # Mock LLM 주입
    decomposer = TaskDecomposer(
        llm_generate=lambda p, h=None: asyncio.create_task(asyncio.sleep(0, result=json.dumps({
            "rationale": "웹 스크래퍼는 3단계로 분해됩니다",
            "subtasks": [
                {
                    "name": "HTML 페칭",
                    "description": "웹 페이지 HTML을 가져옴",
                    "dependencies": [],
                    "estimated_complexity": 3,
                    "task_type": "tool_call"
                },
                {
                    "name": "파싱",
                    "description": "HTML을 파싱하여 데이터 추출",
                    "dependencies": ["HTML 페칭"],
                    "estimated_complexity": 5,
                    "task_type": "generic"
                },
                {
                    "name": "저장",
                    "description": "추출된 데이터를 파일에 저장",
                    "dependencies": ["파싱"],
                    "estimated_complexity": 2,
                    "task_type": "tool_call"
                }
            ]
        }))),
        max_subtasks=10
    )

    print("✓ Task 분해:")
    decomposition = await decomposer.decompose(
        task="간단한 웹 스크래퍼 만들기"
    )

    print(f"  - 원본 태스크: {decomposition.original_task}")
    print(f"  - 전략: {decomposition.strategy.value}")
    print(f"  - Subtasks: {len(decomposition.subtasks)}")
    print(f"  - 예상 단계: {decomposition.estimated_total_steps}")

    for i, subtask in enumerate(decomposition.subtasks):
        deps = f" (depends on: {', '.join(subtask.dependencies)})" if subtask.dependencies else ""
        print(f"  {i+1}. {subtask.name}{deps}")
        print(f"     {subtask.description}")
        print(f"     Complexity: {subtask.estimated_complexity}/10")


async def example_6_complete_workflow():
    """예시 6: 완전한 워크플로우"""
    print("\n" + "="*60)
    print("예시 6: 완전한 Enhanced Planner 워크플로우")
    print("="*60 + "\n")

    import sys
    sys.path.insert(0, '/Users/1113804/Desktop/Code/24.AgentMoniter/agent-monitor_v2/server_python')

    from agents import enhanced_planner_agent, EnhancedPlannerContext

    # Mock LLM 주입
    from models import orchestration
    original_call_llm = orchestration.call_llm
    orchestration.call_llm = mock_llm_call

    try:
        print("✓ Step 1: Planning")
        context = EnhancedPlannerContext(
            task_id="demo-complete",
            user_request="프로젝트의 모든 TODO 코멘트를 찾아서 정리해줘",
            available_agents=[
                {"id": "general-agent", "name": "General Agent", "type": "custom"}
            ],
            use_task_decomposition=False,
            use_reasoning=True,
            enable_critique=False,
        )

        result = await enhanced_planner_agent.run(context)
        print(f"  - 성공: {result.success}")
        print(f"  - 단계: {len(result.steps)}")

        print(f"\n✓ Step 2: 통계 확인")
        stats = enhanced_planner_agent.get_stats()
        print(f"  - Tools: {stats['tools']['total_tools']}")
        print(f"  - Context tokens: {stats['context']['total_tokens']}")
        print(f"  - Memories: {stats['memory']['total_memories']}")

        print(f"\n✓ Step 3: Memory 확인")
        memories = enhanced_planner_agent.memory.recall(
            tags={"planning"},
            limit=3
        )
        print(f"  - Planning 관련 메모리: {len(memories)}")
        for mem in memories:
            print(f"    - {mem.content[:60]}...")

        print(f"\n✓ 완료!")

    finally:
        orchestration.call_llm = original_call_llm


async def main():
    """모든 예시 실행"""
    print("\n" + "="*60)
    print("Enhanced Planner Agent 데모")
    print("="*60)

    examples = [
        ("기본 Planning", example_1_basic_planning),
        ("Tool System", example_2_tool_system),
        ("Memory System", example_3_memory_system),
        ("Context Manager", example_4_context_manager),
        ("Task Decomposition", example_5_task_decomposition),
        ("완전한 워크플로우", example_6_complete_workflow),
    ]

    for i, (name, func) in enumerate(examples, 1):
        try:
            await func()
        except Exception as e:
            print(f"\n❌ 예시 {i} ({name}) 실패: {e}")
            import traceback
            traceback.print_exc()

        # 구분을 위한 대기
        await asyncio.sleep(0.5)

    print("\n" + "="*60)
    print("모든 데모 완료!")
    print("="*60 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
