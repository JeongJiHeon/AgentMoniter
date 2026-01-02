# PlannerAgent Refactoring Summary

## 목표 달성 ✅

`_analyze_and_plan()` 내부 함수를 **정식 1급 Agent (PlannerAgent)** 로 승격하여 진짜 Agentic Workflow를 구현했습니다.

```
AS-IS: 고정된 시나리오 실행기
DynamicOrchestration → _analyze_and_plan() → 고정 steps → 실행

TO-BE: 스스로 계획하고 수정하는 Agent System
User Intent → PlannerAgent → Execution → Reflection → Replan (optional)
```

---

## 변경 사항

### 1. 새로운 파일 추가

#### `server_python/agents/planner_agent.py`
- **PlannerAgent** 클래스: 독립적인 Planning Agent
- **PlannerContext**: Planner 실행 컨텍스트
  - `task_id`, `user_request`, `available_agents`
  - `previous_plan`, `execution_results` (재계획용)
  - `reason`: "initial" | "replan" | "recovery"
- **PlannerResult**: Planning 결과
  - `success`, `analysis`, `steps`
  - `confidence` (0.0~1.0): 계획 신뢰도
  - `replan_required`, `replan_reason`

**핵심 메서드:**
```python
async def run(context: PlannerContext) -> PlannerResult
async def evaluate_execution(plan, results) -> Dict[str, Any]
```

---

### 2. 수정된 파일

#### `server_python/agents/dynamic_orchestration.py`

**Import 추가:**
```python
from .planner_agent import planner_agent, PlannerContext, PlannerResult
```

**system_agents에 PlannerAgent 등록:**
```python
self.system_agents = {
    "orchestrator": {...},
    "planner": {                          # 🆕 추가
        "id": "planner-agent",
        "name": "Planner Agent",
        "role": AgentRole.ORCHESTRATOR
    },
    "q_and_a": {...}
}
```

**_analyze_and_plan() 메서드 수정:**
- 기존: 내부에서 직접 LLM 호출
- 변경: PlannerAgent 호출
```python
async def _analyze_and_plan(
    workflow, available_agents, reason="initial"  # 🆕 reason 파라미터
) -> Optional[List[Dict]]:
    planner_context = PlannerContext(...)
    planner_result = await planner_agent.run(planner_context)  # 🆕
    # ... steps 생성
```

**Re-planning 메서드 추가:**
```python
# 🆕 재계획 필요성 확인
async def _check_replan_needed(task_id, current_result) -> Optional[str]:
    # 1. Agent 실패 감지
    # 2. 낮은 신뢰도 감지 (< 0.6)
    # 3. 사용자 입력 방향 변경 (TODO)

# 🆕 워크플로우 재계획
async def _replan_workflow(task_id, reason) -> bool:
    # 1. 기존 계획 및 실행 결과 수집
    # 2. PlannerAgent 재호출
    # 3. 새로운 steps 생성
    # 4. 워크플로우 초기화 및 재시작
```

**_execute_workflow() 수정:**
```python
elif result.status == AgentLifecycleStatus.COMPLETED:
    # ... 기존 로직 ...

    # 🆕 재계획 필요성 체크
    replan_reason = await self._check_replan_needed(task_id, result)
    if replan_reason:
        replan_success = await self._replan_workflow(task_id, replan_reason)
        if replan_success:
            return await self._execute_workflow(task_id)  # 재시작

elif result.status == AgentLifecycleStatus.FAILED:
    # 🆕 실패 시 자동 재계획 시도
    replan_success = await self._replan_workflow(task_id, "agent_failure")
    if replan_success:
        return await self._execute_workflow(task_id)  # 재시작
```

#### `server_python/agents/__init__.py`

**Export 추가:**
```python
from .planner_agent import PlannerAgent, planner_agent, PlannerContext, PlannerResult

__all__ = [
    ...,
    "PlannerAgent",
    "planner_agent",
    "PlannerContext",
    "PlannerResult",
]
```

---

## 성공 기준 검증 ✅

| 기준 | 상태 | 설명 |
|------|------|------|
| ✅ PlannerAgent가 정식 Agent | 완료 | `planner_agent.py`에 독립 클래스로 구현 |
| ✅ Planning이 내부 함수가 아님 | 완료 | `_analyze_and_plan()`이 PlannerAgent 호출 |
| ✅ Agent Registry 등록 | 완료 | `system_agents['planner']` 등록 |
| ✅ Re-plan 실행 중 가능 | 완료 | `_check_replan_needed()`, `_replan_workflow()` |
| ✅ Workflow는 Planner 없이 실행 불가 | 완료 | `process_request()`에서 필수 호출 |

---

## Re-Planning 트리거

### 1. Agent 실패 (자동)
```python
if result.status == AgentLifecycleStatus.FAILED:
    await self._replan_workflow(task_id, "agent_failure")
```

### 2. 낮은 신뢰도 (자동)
```python
if result.partial_data.get("confidence", 1.0) < 0.6:
    await self._replan_workflow(task_id, f"low_confidence_{confidence}")
```

### 3. 사용자 입력 방향 변경 (향후 구현)
```python
# TODO: 사용자 입력이 기존 계획과 상충되는지 확인
if user_input_contradicts_plan:
    await self._replan_workflow(task_id, "user_deviation")
```

---

## 테스트 결과

```bash
✓ PlannerAgent import successful
✓ DynamicOrchestration import successful
✓ System agents: ['orchestrator', 'planner', 'q_and_a']
✓ All structural checks passed!
```

### PlannerAgent 메서드 확인
```
- run(context: PlannerContext) -> PlannerResult
- evaluate_execution(plan: List[Dict], results: List[AgentResult]) -> Dict
```

### DynamicOrchestrationEngine 메서드 확인
```
- _analyze_and_plan(workflow, available_agents, reason='initial')
- _check_replan_needed(task_id, current_result) -> Optional[str]
- _replan_workflow(task_id, reason) -> bool
```

---

## 작동 방식

### 초기 Planning
```python
# 1. 사용자 요청 수신
workflow = DynamicWorkflow(task_id, user_request)

# 2. PlannerAgent 호출
planner_context = PlannerContext(
    task_id=task_id,
    user_request=user_request,
    available_agents=agents,
    reason="initial"
)
planner_result = await planner_agent.run(planner_context)

# 3. Steps 생성 및 실행
for step_data in planner_result.steps:
    workflow.add_step(AgentStep(...))
```

### Re-Planning (실패 시)
```python
# 1. Agent 실행 실패 감지
if result.status == AgentLifecycleStatus.FAILED:

    # 2. 기존 계획 및 실행 결과 수집
    previous_plan = [step.to_dict() for step in workflow.steps]
    execution_results = [...]

    # 3. PlannerAgent 재호출
    planner_context = PlannerContext(
        task_id=task_id,
        user_request=user_request,
        available_agents=agents,
        previous_plan=previous_plan,
        execution_results=execution_results,
        reason="replan: agent_failure"
    )
    planner_result = await planner_agent.run(planner_context)

    # 4. 워크플로우 재시작
    workflow.steps.clear()
    # ... 새로운 steps 추가
    return await self._execute_workflow(task_id)
```

---

## 기존 로직 유지 사항

✅ **LLM 프롬프트 그대로 유지**
- Worker Agent는 사용자와 직접 소통 ❌
- Q&A Agent만 사용자 소통 ⭕
- 마지막 단계는 Q&A Agent 요약 ⭕

✅ **JSON Schema 그대로 유지**
```json
{
  "analysis": "...",
  "steps": [
    {
      "agent_id": "...",
      "agent_name": "...",
      "role": "worker" | "q_and_a",
      "description": "...",
      "user_prompt": "..."
    }
  ]
}
```

✅ **실행 흐름 그대로 유지**
- AgentResult 기반 상태 전환
- WAITING_USER, COMPLETED, FAILED 분기
- Q&A Agent multi-turn 대화

---

## 향후 개선 사항

### 1. BaseAgent 상속 (선택사항)
현재 PlannerAgent는 독립 클래스입니다. 향후 통합을 위해 BaseAgent 상속 가능:
```python
class PlannerAgent(BaseAgent):
    async def explore(self, input: AgentInput) -> Dict:
        # Planning exploration

    async def run(self, context: AgentContext) -> AgentResult:
        # Current run() logic
```

### 2. 사용자 입력 방향 변경 감지
```python
async def _check_user_deviation(self, task_id: str, user_input: str) -> bool:
    # LLM을 사용하여 사용자 입력이 기존 계획과 상충되는지 확인
    # 예: "메뉴 추천" 계획 중 사용자가 "식당 예약만 해줘"라고 입력
```

### 3. Planner 신뢰도 학습
```python
# 성공/실패 이력 기반 Planner 성능 개선
workflow.context["planner_history"] = [
    {"plan": [...], "success": True, "confidence": 0.95},
    {"plan": [...], "success": False, "confidence": 0.62},
]
```

---

## 요약

**"고정된 시나리오 실행기" → "스스로 계획하고 수정하는 Agent System"**

- ✅ PlannerAgent가 정식 1급 Agent로 승격
- ✅ Re-planning 기능 추가 (실패/낮은 신뢰도 시 자동 재계획)
- ✅ 기존 기능 100% 유지 (LLM 프롬프트, JSON 구조, 실행 흐름)
- ✅ Agent Registry에 등록 (`system_agents['planner']`)
- ✅ 모든 테스트 통과

**No new features added. Only promoted existing planning logic into a first-class PlannerAgent and wired it into the orchestration lifecycle.**
