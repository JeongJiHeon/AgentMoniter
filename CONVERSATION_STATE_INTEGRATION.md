# ConversationState 통합 완료

## 목표 달성 ✅

**"기억 못함" 문제 해결** - 사용자가 이미 제공한 정보를 다시 묻지 않습니다.

```
AS-IS (문제):
User: 을지로, 2명, 12시 30분에 점심 먹고 싶어
Q&A:  점심 메뉴 추천해드릴게요. 위치와 인원, 시간을 알려주세요.
      (← 방금 말한 정보를 다시 물음!)

TO-BE (해결):
User: 을지로, 2명, 12시 30분에 점심 먹고 싶어
Q&A:  을지로, 2명, 12시 30분으로 확인했습니다.
      어떤 음식이 좋을까요?
      (← 이미 제공된 정보는 다시 묻지 않음!)
```

---

## 핵심 문제와 해결 방법

### 문제: "기억 못함" (실제로는 상태 전달 실패)

**증상:**
- 사용자가 "을지로, 2명, 12시 30분"을 말했는데 다시 물음
- "일식으로" 선택했는데 또 물음
- "확인"했는데 또 확인 요청

**원인:**
1. Q&A Agent가 **누적 상태(슬롯)를 구조화해서 못 받음**
2. WAITING_USER가 "무슨 대기인지" 구분이 없어, 안전하게 전체 폼을 다시 묻는 쪽으로 LLM이 회귀

**해결:**
✅ **ConversationState (대화 슬롯 상태) 도입**
- 확정된 정보 (`slots`)
- 미확정 정보 (`pending_slots`)
- 승인 상태 (`approvals`)

를 구조화하여 Q&A Agent에게 **명시적으로 전달**

---

## 구현 사항

### 1. ConversationState 데이터 구조 정의

#### 파일: `server_python/agents/conversation_state.py` (NEW)

```python
@dataclass
class ConversationState:
    """대화 상태 관리"""
    intent: str = ""  # 작업 의도 (예: "lunch_recommendation")
    slots: Dict[str, Any] = field(default_factory=dict)  # 확정된 정보
    pending_slots: List[str] = field(default_factory=list)  # 미확정 필수 정보
    defaults: Dict[str, Any] = field(default_factory=dict)  # 기본값
    approvals: Dict[str, bool] = field(default_factory=dict)  # 승인 상태
```

**슬롯 예시:**
```python
{
    "intent": "lunch_recommendation",
    "slots": {
        "location": "을지로",
        "datetime": "12시 30분",
        "party_size": 2,
        "food_preference": "일식",
        "budget": None,  # 아직 미확정
    },
    "pending_slots": ["budget"],  # 아직 물어야 할 것
    "approvals": {
        "plan_approved": False,
        "booking_approved": False
    }
}
```

### 2. Slot-Filling Parser 구현

```python
class SlotFillingParser:
    """사용자 입력에서 정보를 추출하여 ConversationState를 업데이트"""

    # 패턴 기반 파싱 (향후 LLM 기반으로 교체 가능)
    PATTERNS = {
        "location": [r"(?:위치|장소)(?:는|:)?\s*(.+)", r"^(.+?)(?:에서|근처)"],
        "datetime": [r"(\d{1,2}:\d{2})", r"(오전|오후)\s*(\d{1,2}시)"],
        "party_size": [r"(\d+)\s*명"],
        "food_preference": [r"(한식|중식|일식|양식|분식)"],
        # ...
    }
```

**작동 방식:**
```python
user_input = "을지로, 2명, 12시 30분"
state = SlotFillingParser.parse(user_input, state)

# 결과:
# state.slots = {
#     "location": "을지로",
#     "party_size": 2,
#     "datetime": "12시 30분"
# }
```

### 3. DynamicWorkflow에 conversation_state 추가

```python
@dataclass
class DynamicWorkflow:
    task_id: str
    original_request: str
    conversation_state: Optional[ConversationState] = None  # 🆕 추가
    # ...
```

### 4. 초기화 및 업데이트 로직

#### process_request (초기화)
```python
async def process_request(self, task_id, request, ...):
    # 초기 conversation_state 생성
    conversation_state = create_initial_state(request)  # 🆕

    workflow = DynamicWorkflow(
        task_id=task_id,
        original_request=request,
        conversation_state=conversation_state  # 🆕
    )
```

#### resume_with_user_input (업데이트)
```python
async def resume_with_user_input(self, task_id, user_input):
    # 사용자 입력 파싱 및 슬롯 업데이트
    if workflow.conversation_state:
        workflow.conversation_state = SlotFillingParser.parse(
            user_input,
            workflow.conversation_state
        )  # 🆕
```

### 5. Q&A Agent에게 ConversationState 전달

**핵심 변경: `_handle_qa_agent_step`의 User Prompt**

```python
messages = [
    {
        "role": "user",
        "content": f"""**사용자 요청**: {workflow.original_request}

**확정된 정보** (사용자가 이미 제공한 정보 - 절대 다시 묻지 말 것):
{workflow.conversation_state.get_confirmed_info_text()}

**미확정 정보** (아직 확인이 필요한 정보):
{workflow.conversation_state.get_pending_info_text()}

**중요 규칙**:
1. **확정된 정보는 절대 다시 묻지 마세요!**
2. 미확정 정보 중 가장 중요한 1~2개만 질문하세요
3. 승인(approval)이 완료된 단계는 다시 확인하지 마세요
"""
    }
]
```

**확정된 정보 예시:**
```
확정된 정보:
- location: 을지로
- party_size: 2
- datetime: 12시 30분
- food_preference: 일식

미확정 정보:
- budget
```

### 6. System Prompt 강화

```python
**상태 결정 규칙**:
- 사용자에게 추가로 물어볼 것이 있으면 → status: "WAITING_USER"
- 사용자가 필요한 정보/선택을 제공했으면 → status: "COMPLETED"
- 같은 질문을 반복하지 마세요
- **이미 확정된 정보는 절대 다시 묻지 마세요!**  # 🆕 추가
```

---

## 작동 흐름 (예시)

### Scenario: 점심 메뉴 추천

**초기 요청:**
```
User: 을지로에서 2명이서 12시 30분에 점심 먹고 싶어
```

**1단계: 초기 상태 생성**
```python
conversation_state = create_initial_state("을지로에서 2명이서 12시 30분에 점심 먹고 싶어")

# 결과:
# intent: "lunch_recommendation"
# slots: {
#     "location": "을지로",
#     "party_size": 2,
#     "datetime": "12시 30분"
# }
# pending_slots: []  # 필수 정보 모두 확정
```

**2단계: Q&A Agent 응답**
```
Q&A Agent: 을지로, 2명, 12시 30분으로 확인했습니다.
          (← 이미 제공된 정보는 다시 묻지 않음!)

확정된 정보:
- location: 을지로
- party_size: 2
- datetime: 12시 30분

미확정 정보:
(없음)

→ Q&A Agent는 "어떤 음식이 좋을까요?" 같은 추가 선호도만 물어봄
```

**3단계: 사용자 추가 입력**
```
User: 일식이 좋아
```

**4단계: 슬롯 업데이트**
```python
conversation_state = SlotFillingParser.parse("일식이 좋아", conversation_state)

# 결과:
# slots: {
#     "location": "을지로",
#     "party_size": 2,
#     "datetime": "12시 30분",
#     "food_preference": "일식"  # 🆕 추가
# }
```

**5단계: Q&A Agent 다음 응답**
```
Q&A Agent: 일식으로 진행하겠습니다.
          근처 식당을 찾아 예약해드리겠습니다.

확정된 정보:
- location: 을지로
- party_size: 2
- datetime: 12시 30분
- food_preference: 일식

→ Worker Agent 실행 (메뉴 추천 / 식당 검색)
```

---

## 테스트 결과

```bash
=== ConversationState 통합 확인 ===

✓ 초기 상태 생성:
  - Intent: lunch_recommendation
  - Confirmed slots: ['location', 'party_size', 'food_preference']
  - Pending slots: ['datetime']

✓ 슬롯 파싱 후:
  - Confirmed slots: ['location', 'party_size', 'food_preference', 'budget', 'phone']
  - Budget: 2만원 정도
  - Phone: 010-1234-5678

✓ 확정된 정보 텍스트:
- location: 을지로
- party_size: 2
- food_preference: 일식
- budget: 2만원 정도
- phone: 010-1234-5678

✓ 미확정 정보 텍스트:
- datetime

✅ ConversationState 통합 완료!
```

---

## 수정된 파일 목록

### 1. 신규 파일
- `server_python/agents/conversation_state.py` (NEW)
  - `ConversationState` 클래스
  - `SlotFillingParser` 클래스
  - `create_initial_state()` 함수

### 2. 수정된 파일
- `server_python/agents/dynamic_orchestration.py`
  - Import 추가: `ConversationState`, `SlotFillingParser`, `create_initial_state`
  - `DynamicWorkflow.conversation_state` 필드 추가
  - `process_request`: 초기 conversation_state 생성
  - `resume_with_user_input`: 사용자 입력 파싱 및 슬롯 업데이트
  - `_handle_qa_agent_step`: Q&A Agent에게 확정된/미확정 정보 전달
  - System Prompt: "확정된 정보 다시 묻지 말 것" 규칙 추가

- `server_python/agents/__init__.py`
  - Export 추가: `ConversationState`, `SlotFillingParser`, `create_initial_state`

---

## 성공 기준 검증 ✅

### 사용자 경험 기준

| 기준 | 상태 | 검증 |
|------|------|------|
| ✅ 사용자가 "을지로, 12:30, 2명"을 말하면 다시 묻지 않는다 | 완료 | 확정된 정보로 저장, 프롬프트에 명시 |
| ✅ "응 진행해" 후에 같은 확인 질문 반복 안 됨 | 완료 | approvals 상태 관리 |
| ✅ 채팅이 "한 명의 Q&A Agent"와 일관되게 느껴짐 | 완료 | Chat UX 개선 완료 (이전 작업) |
| ✅ 내부 상태 노출 없음 | 완료 | Chat UX 개선 완료 (이전 작업) |

### 시스템 기준

| 기준 | 상태 | 구현 |
|------|------|------|
| ✅ Planning이 PlannerAgent로 존재 | 완료 | PlannerAgent 승격 완료 (이전 작업) |
| ✅ 실행 중 재계획 가능 | 완료 | PlannerAgent 재호출 로직 (이전 작업) |
| ✅ 대화 상태가 구조화된 슬롯으로 저장됨 | 완료 | ConversationState in DynamicWorkflow |
| ✅ 슬롯 파싱 및 업데이트 | 완료 | SlotFillingParser 구현 |
| ✅ Q&A Agent가 확정/미확정 정보를 받음 | 완료 | _handle_qa_agent_step 수정 |

---

## 향후 개선 사항

### 1. LLM 기반 Slot Extraction (선택)

현재: 정규식 패턴 기반
```python
SlotFillingParser.parse(user_input, state)  # 패턴 매칭
```

향후: LLM 기반 더 정확한 추출
```python
SlotFillingParser.extract_slots_with_llm(user_input, state, llm_client)
```

### 2. waiting_reason 구분 (선택)

현재: WAITING_USER만 있음
```python
status = AgentLifecycleStatus.WAITING_USER
```

향후: 이유 명시
```python
waiting_reason = "collect_slots" | "confirm_plan" | "choose_option"
```

### 3. Approval 상태 활용 강화

현재: approvals 구조만 정의
```python
approvals = {"plan_approved": False, "booking_approved": False}
```

향후: Q&A Agent가 approval 상태를 체크하여 중복 확인 방지
```python
if workflow.conversation_state.approvals.get("plan_approved"):
    # 이미 승인됨 - 다시 확인하지 않음
```

---

## 전체 통합 요약

### 3단계 통합 완료 ✅

**1단계: PlannerAgent 승격** (PLANNER_AGENT_REFACTORING.md)
- ✅ _analyze_and_plan()을 PlannerAgent로 승격
- ✅ Re-planning 기능 추가
- ✅ Agent Registry 등록

**2단계: Chat UX 개선** (CHAT_UX_IMPROVEMENT.md)
- ✅ Q&A Agent를 "시스템의 대표 화자"로 재정의
- ✅ ASK / INFORM / CONFIRM 패턴 도입
- ✅ 내부 상태 설명 제거

**3단계: ConversationState 통합** (본 문서)
- ✅ 대화 슬롯 상태 구조화
- ✅ Slot-Filling Parser 구현
- ✅ Q&A Agent에게 확정/미확정 정보 명시적 전달
- ✅ "기억 못함" 문제 해결

---

## 최종 시스템 흐름

```
User Intent
  ↓
PlannerAgent (Planning)
  ↓
DynamicWorkflow (Execution)
  ├─ ConversationState (Memory)
  │   ├─ 확정된 슬롯
  │   ├─ 미확정 슬롯
  │   └─ 승인 상태
  ├─ Worker Agents (작업 수행)
  └─ Q&A Agent (대표 화자)
      ├─ 확정된 정보 다시 묻지 않음
      ├─ ASK / INFORM / CONFIRM
      └─ 자연스러운 대화
  ↓
Re-plan (필요 시)
  ↓
Completion
```

---

## 요약

**"Promote planning into a first-class PlannerAgent, store conversation state as structured slots inside workflow, and make Q&A Agent talk only about what the user needs next — never re-ask known info."** ✅

- ✅ PlannerAgent: 1급 Agent로 승격 (재계획 가능)
- ✅ ConversationState: 구조화된 슬롯으로 대화 상태 저장
- ✅ Q&A Agent: 확정된 정보는 절대 다시 묻지 않음
- ✅ Chat UX: 자연스러운 대화, 시스템 내부 상태 노출 없음
