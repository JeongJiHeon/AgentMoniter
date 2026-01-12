# Enhanced Planner Agent 사용 가이드

## 개요

Enhanced Planner Agent는 Claude Code와 유사한 고급 에이전트 아키텍처를 제공합니다.

### 주요 기능

1. **Tool System** - 동적 도구 발견 및 실행
2. **ReAct Loop** - Think → Plan → Act → Observe → Reflect
3. **Task Decomposition** - DAG 기반 복잡한 태스크 분해
4. **Context Management** - 토큰 제한 관리 및 자동 요약
5. **Memory System** - Short-term/Long-term 메모리
6. **Reasoning** - Chain-of-Thought, Self-Critique
7. **Sub-agents** - 계층적 에이전트 시스템
8. **MCP Discovery** - MCP 서버 통합

## 설치

```bash
cd server_python
pip install -r requirements.txt
```

## 기본 사용법

### 1. Enhanced Planner Agent 사용

```python
from agents import enhanced_planner_agent, EnhancedPlannerContext

# Context 생성
context = EnhancedPlannerContext(
    task_id="task-123",
    user_request="프로젝트의 모든 Python 파일을 찾아서 import 구조를 분석해줘",
    available_agents=[
        {"id": "general-agent", "name": "General Agent", "type": "custom"}
    ],
    use_task_decomposition=True,  # 복잡한 태스크 분해 사용
    use_reasoning=True,            # Chain-of-Thought 추론 사용
    enable_critique=True,          # Self-Critique 활성화
)

# 실행
result = await enhanced_planner_agent.run(context)

# 결과 확인
if result.success:
    print(f"분석: {result.analysis}")
    print(f"단계 수: {len(result.steps)}")
    print(f"확신도: {result.confidence}")

    for i, step in enumerate(result.steps):
        print(f"{i+1}. {step['agent_name']}: {step['description']}")
```

### 2. Tool System 직접 사용

```python
from tools import get_tool_registry, ToolExecutor
from tools.builtin import register_all_builtin_tools

# Registry 초기화
registry = get_tool_registry()
register_all_builtin_tools(registry)

# Executor 생성
executor = ToolExecutor(registry)

# Tool 실행
result = await executor.execute(
    "read_file",
    {"file_path": "/path/to/file.py"}
)

if result.success:
    print(result.output)
```

### 3. Task Decomposition 사용

```python
from task_graph import TaskDecomposer, GraphExecutor

async def my_llm_function(prompt, history=None):
    # LLM 호출 구현
    return await call_llm([{"role": "user", "content": prompt}])

# Decomposer 생성
decomposer = TaskDecomposer(
    llm_generate=my_llm_function,
    max_subtasks=10
)

# 태스크 분해
decomposition = await decomposer.decompose(
    task="웹 스크래퍼 구축",
    context={"language": "Python"}
)

print(f"분해된 subtask 수: {len(decomposition.subtasks)}")

# Task Graph 생성
graph = decomposer.create_task_graph(decomposition)

# 그래프 실행
async def execute_task(task_node):
    # 각 태스크 실행 로직
    print(f"Executing: {task_node.name}")
    from tools.tool_schemas import ToolResult
    return ToolResult.success_result(f"Completed {task_node.name}")

executor = GraphExecutor(graph, execute_task)
result = await executor.execute_all()

print(f"실행 완료: {result['completed']}/{result['total_tasks']}")
```

### 4. Memory System 사용

```python
from context import MemorySystem, MemoryType

# Memory 초기화
memory = MemorySystem()

# 메모리 추가
memory.add_memory(
    MemoryType.FACT,
    "사용자는 다크 모드를 선호함",
    importance=0.8,
    tags={"user_preference", "ui"}
)

memory.add_memory(
    MemoryType.PATTERN,
    "복잡한 태스크는 Task Decomposition을 사용하면 성공률이 높음",
    importance=0.9,
    tags={"planning", "strategy"}
)

# 메모리 회상
relevant_memories = memory.recall(
    tags={"user_preference"},
    min_importance=0.5,
    limit=5
)

for mem in relevant_memories:
    print(f"- {mem.content} (importance: {mem.importance})")

# 메모리 consolidation
await memory.consolidate()
```

### 5. Context Manager 사용

```python
from context import ContextManager, MessageRole

# Context Manager 초기화
context_mgr = ContextManager(
    max_tokens=100000,
    summarize_func=my_summarize_function
)

# 메시지 추가
context_mgr.add_message(
    MessageRole.USER,
    "프로젝트 구조를 설명해줘"
)

context_mgr.add_message(
    MessageRole.ASSISTANT,
    "프로젝트는 다음과 같이 구성되어 있습니다..."
)

# 컨텍스트 윈도우 가져오기
window = context_mgr.get_context_window()
print(f"토큰 사용: {window.total_tokens}/{window.max_tokens}")

# LLM용 메시지 형식
messages = context_mgr.get_messages_for_llm()

# 자동 요약 (threshold 도달 시)
await context_mgr.maybe_summarize()
```

### 6. Sub-agent Manager 사용

```python
from subagents import SubagentManager, SubagentSpec

async def execute_agent(spec):
    # Sub-agent 실행 로직
    print(f"Executing sub-agent: {spec.name}")
    from subagents import SubagentResult
    return SubagentResult(
        success=True,
        output=f"Completed {spec.task}",
        iterations=1
    )

# Manager 생성
manager = SubagentManager(
    execute_agent=execute_agent,
    max_depth=3,
    max_concurrent=5
)

# Sub-agent 생성 및 실행
spec = SubagentSpec(
    name="FileSearcher",
    role="파일 검색 전문가",
    task="모든 Python 파일 찾기",
    capabilities=["file_search", "glob"]
)

result = await manager.spawn_and_wait(spec)
print(result.output)

# 여러 sub-agent 병렬 실행
results = await manager.spawn_parallel([spec1, spec2, spec3])
```

## 기존 Planner Agent와 비교

### 기존 Planner Agent
```python
from agents import planner_agent, PlannerContext

context = PlannerContext(
    task_id="task-123",
    user_request="태스크 설명",
    available_agents=[...]
)

result = await planner_agent.run(context)
```

### Enhanced Planner Agent
```python
from agents import enhanced_planner_agent, EnhancedPlannerContext

context = EnhancedPlannerContext(
    task_id="task-123",
    user_request="태스크 설명",
    available_agents=[...],
    # 추가 기능
    use_task_decomposition=True,
    use_reasoning=True,
    enable_critique=True
)

result = await enhanced_planner_agent.run(context)

# 추가 정보
print(result.task_graph)      # Task Graph (if decomposed)
print(result.reasoning_chain)  # Chain-of-Thought steps
print(result.critique_result)  # Self-critique feedback
```

## 통합 예시

```python
from agents import enhanced_planner_agent, EnhancedPlannerContext

async def plan_and_execute(user_request: str):
    """Enhanced Planner를 사용한 전체 워크플로우"""

    # 1. Planning
    context = EnhancedPlannerContext(
        task_id="auto-gen-id",
        user_request=user_request,
        available_agents=[
            {"id": "general-agent", "name": "General Agent", "type": "custom"}
        ],
        use_task_decomposition=True,
        use_reasoning=True,
        enable_critique=True
    )

    plan_result = await enhanced_planner_agent.run(context)

    if not plan_result.success:
        print("Planning failed")
        return

    print(f"✓ Planning complete: {len(plan_result.steps)} steps")
    print(f"✓ Confidence: {plan_result.confidence:.2%}")

    # 2. Task Graph 실행 (if available)
    if plan_result.task_graph:
        async def execute_node(node):
            print(f"Executing: {node.name}")
            # 실제 실행 로직
            from tools.tool_schemas import ToolResult
            return ToolResult.success_result(f"Done: {node.name}")

        from task_graph import GraphExecutor
        executor = GraphExecutor(
            plan_result.task_graph,
            execute_node
        )

        exec_result = await executor.execute_all()
        print(f"✓ Execution: {exec_result['completed']}/{exec_result['total_tasks']}")

    # 3. 통계 확인
    stats = enhanced_planner_agent.get_stats()
    print(f"\nStats:")
    print(f"- Tools available: {stats['tools']['total_tools']}")
    print(f"- Context tokens: {stats['context']['total_tokens']}")
    print(f"- Memories: {stats['memory']['total_memories']}")

# 사용
await plan_and_execute("프로젝트의 모든 TODO 코멘트를 찾아서 정리해줘")
```

## 고급 기능

### ReAct Loop 사용

```python
from agentic import ReActLoop
from tools import ToolExecutor, get_tool_registry

async def llm_generate(prompt, history, tools):
    # LLM 호출 구현
    pass

# ReAct Loop 생성
loop = ReActLoop(
    llm_generate=llm_generate,
    tool_executor=ToolExecutor(get_tool_registry()),
    max_iterations=15
)

# 실행
result = await loop.run(
    task="프로젝트에서 보안 취약점 찾기",
    context={"project_path": "/path/to/project"}
)

print(f"Steps taken: {result['total_steps']}")
print(f"Final answer: {result['final_answer']}")
```

### Self-Critique로 품질 개선

```python
from agentic import SelfCritique

critique = SelfCritique(
    llm_generate=my_llm_function,
    quality_threshold=7.0
)

# 코드 critique
result = await critique.critique_code(
    code=my_code,
    language="python",
    context="API endpoint implementation"
)

print(f"Quality: {result.overall_quality}/10")
print(f"Issues: {len(result.issues)}")
for issue in result.issues:
    print(f"- [{issue.severity.value}] {issue.description}")

print(f"Suggestions:")
for suggestion in result.suggestions_for_improvement:
    print(f"- {suggestion}")
```

## 설정 커스터마이징

```python
from agents import EnhancedPlannerAgent

# 커스텀 설정으로 생성
custom_planner = EnhancedPlannerAgent(
    max_context_tokens=200000,  # 더 큰 컨텍스트
    enable_tools=True,
    enable_memory=True,
    enable_subagents=True
)

# 사용
result = await custom_planner.run(context)
```

## 문제 해결

### Tool 실행 오류

```python
# Tool Registry 확인
registry = get_tool_registry()
print(f"Available tools: {registry.get_names()}")

# Tool 정보 확인
info = registry.get_tool_info()
print(info)
```

### 메모리 부족

```python
# Context 압축
context_mgr.compress_context(target_tokens=50000)

# 메모리 정리
memory.prune_old_memories()
```

### 디버깅

```python
# 통계 확인
stats = enhanced_planner_agent.get_stats()
print(json.dumps(stats, indent=2))

# 히스토리 export
history = context_mgr.export_history()
with open("context_history.json", "w") as f:
    json.dump(history, f, indent=2)
```

## 다음 단계

1. **LLM 통합**: 실제 Claude API 연결
2. **MCP Protocol**: MCP SDK 통합
3. **Orchestration**: 기존 orchestration과 통합
4. **UI 연동**: 프론트엔드와 WebSocket 연결
5. **Testing**: 단위 테스트 및 통합 테스트

## 참고

- 모든 새로운 시스템은 `server_python/` 하위에 있습니다:
  - `tools/` - Tool System
  - `agentic/` - ReAct, Reasoning, Critique
  - `task_graph/` - Task Decomposition
  - `context/` - Context & Memory
  - `subagents/` - Sub-agents & MCP
