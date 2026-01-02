# Context/Message Separation 구현 완료 ✅

## 문제

**Q&A Agent가 Context를 Message에 나열하여 부자연스러운 대화**

```
❌ Before:
Q&A Agent: "을지로, 2명, 12시 30분으로 확인했습니다. 어떤 메뉴로 할까요?"

문제점:
1. "을지로, 2명, 12시 30분" → Context 나열 (정보 덤핑)
2. "확인했습니다" → 시스템 상태 설명
3. 질문이 아닌 확인 문구가 먼저 나옴
4. 사람처럼 대화하지 않음
```

**원인**:
- Q&A Agent 프롬프트가 Context 참고와 Message 생성을 명확히 구분하지 않음
- "확정된 정보를 확인하고..." 같은 지시가 Context 나열을 유도
- LLM이 "친절하게" 정보를 요약하려는 경향

---

## 해결 방법

**핵심 원칙: Context is for knowing, Message is for talking**

```
Context (내부 상태):
- 확정된 정보: location="을지로", party_size=2, datetime="12시 30분"
- Worker 결과: 추천 메뉴 3가지
- 슬롯 상태: required_slots 채워짐

Message (사용자와의 대화):
- "어떤 메뉴로 할까요?" ✅
- "시간은 언제가 좋을까요?" ✅
```

**규칙**:
1. **Context는 참고만** → Message에 나열/요약 금지
2. **지금 필요한 질문 1개만** → 확인 문구 없이
3. **ASK/CONFIRM 패턴만** → INFORM 패턴 제거

---

## 구현 사항

### 1. Q&A Agent System Prompt 수정

**파일**: `server_python/agents/dynamic_orchestration.py` (Lines 985-1016)

**Before** (문제):
```python
system_content = """당신은 대화 시스템의 "Q&A Agent"입니다.

**핵심 역할**:
1. 사용자에게 질문하고 정보를 수집합니다
2. 확정된 정보를 자연스럽게 확인합니다
3. Worker Agent 결과를 전달합니다

// 문제: "확정된 정보 확인" → Context 나열 유도
```

**After** (해결):
```python
system_content = """당신은 대화 시스템의 "Q&A Agent"입니다.

**🔴 Context / Message 분리 원칙** (반드시 지켜야 할 것):

1. **Context is for knowing, Message is for talking**
   - 확정된 정보, Worker 결과, 내부 상태는 Context입니다
   - 당신은 Context를 참고만 하고, **절대 나열하거나 요약하지 마세요**

2. **지금 필요한 질문 1개만 생성**
   - "을지로, 2명으로 확인했습니다..." ❌ (Context 나열)
   - "시간은 언제가 좋을까요?" ✅ (질문만)

**나쁜 예시** (절대 이렇게 하지 마세요):
❌ "을지로, 2명, 12시 30분으로 확인했습니다" (Context 나열)
❌ "필요한 정보를 모두 확인했습니다" (종료 문구)
❌ "돈카츠로 진행하겠습니다" (상태 설명)

**좋은 예시**:
✅ "시간은 언제가 좋을까요?" (질문만)
✅ "어떤 메뉴로 할까요?" (질문만)
✅ "이대로 진행할까요?" (확인 질문만)

**패턴**:
- ASK: "~은 언제가 좋을까요?"
- CONFIRM: "이대로 진행할까요?"
- ❌ INFORM: "~로 확인했습니다" (금지!)
"""
```

**핵심 변경**:
- ✅ Context/Message 분리 원칙 명시
- ✅ 나쁜 예시/좋은 예시 추가
- ✅ INFORM 패턴 명시적 금지
- ✅ "절대 나열하거나 요약하지 마세요" 강조

---

### 2. Q&A Agent User Prompt 수정

**파일**: `server_python/agents/dynamic_orchestration.py` (Lines 1018-1051)

**Before** (문제):
```python
user_prompt = f"""
**확정된 정보**:
{workflow.conversation_state.get_confirmed_info_text()}

**당신의 임무**:
확정된 정보를 확인하고 다음 질문을 생성하세요.

// 문제: "확인하고" → Context 나열 유도
```

**After** (해결):
```python
user_prompt = f"""
**🔒 Context** (for reference only - DO NOT list or summarize in your message):

확정된 정보 (절대 다시 묻지 말 것):
{workflow.conversation_state.get_confirmed_info_text()}

대기 중인 정보:
{workflow.conversation_state.get_pending_info_text()}

이전 Worker 결과:
{prev_worker_result_summary}

**💬 Your Task**:
위 Context를 참고하여, 사용자에게 **지금 필요한 질문 1개만** 생성하세요.

중요:
1. Context를 나열하거나 요약하지 마세요
2. "확인했습니다", "진행합니다" 같은 상태 설명 금지
3. 질문만 하세요 (ASK / CONFIRM 패턴)

예시:
❌ "을지로, 2명으로 확인했습니다. 시간은?"
✅ "시간은 언제가 좋을까요?"
"""
```

**핵심 변경**:
- ✅ "🔒 Context (for reference only)" 레이블링
- ✅ "DO NOT list or summarize" 명시
- ✅ Task를 "질문 1개만 생성"으로 변경
- ✅ 나쁜 예시/좋은 예시 직접 제공

---

## 작동 흐름

### Scenario: 점심 메뉴 추천 및 예약 (Context/Message 분리)

**1단계: 필수 정보 수집**
```
Context:
- slots: {}
- required_slots: ["location", "party_size", "datetime"]

Q&A Agent:
→ Message: "어디에서 식사하실 건가요?" ✅
→ 📌 Context 나열 없음
```

**2단계: 사용자 응답**
```
User: "을지로에 2명, 내일 오후 12시 30분"

Context Update:
- slots: {location: "을지로", party_size: 2, datetime: "내일 12시 30분"}
- required_slots_filled: True

Q&A Agent (Gate):
→ COMPLETED (Chat 출력 없음)
```

**3단계: Worker Agent - 메뉴 추천**
```
Worker: "한식 돈카츠, 일식 초밥, 우동/라멘 추천"

Context:
- worker_result: 추천 메뉴 3가지
```

**4단계: 메뉴 선택 질문**
```
Context:
- 확정된 정보: location="을지로", party_size=2, datetime="12시 30분"
- Worker 결과: 추천 메뉴 3가지

Q&A Agent User Prompt:
🔒 Context (DO NOT list):
- 확정: 을지로, 2명, 12시 30분
- Worker: 한식 돈카츠, 일식 초밥, 우동/라멘

Your Task: 질문 1개만 생성

Q&A Agent LLM 응답:
✅ Before: "을지로, 2명, 12시 30분으로 확인했습니다. 추천 메뉴는 한식 돈카츠, 일식 초밥, 우동/라멘입니다. 어떤 메뉴로 할까요?"
✅ After: "어떤 메뉴로 할까요?"

→ Message: "어떤 메뉴로 할까요?" ✅
→ 📌 Context 나열 없음!
```

**5단계: 사용자 응답**
```
User: "돈카츠"

Context Update:
- slots: {menu: "돈카츠"}

Q&A Agent:
→ COMPLETED (Chat 출력 없음)
```

**6단계: Worker Agent - 식당 검색**
```
Worker: "을지로 근처 돈카츠 식당 3곳 검색"

Context:
- worker_result: 식당 후보 3곳
```

**7단계: 식당 선택 질문**
```
Context:
- 확정: 을지로, 2명, 12시 30분, 돈카츠
- Worker: 식당 후보 3곳

Q&A Agent:
✅ Before: "돈카츠로 진행하겠습니다. 을지로 근처 식당을 찾았습니다: 식당 A, B, C. 어떤 식당으로 할까요?"
✅ After: "어떤 식당으로 할까요?"

→ Message: "어떤 식당으로 할까요?" ✅
→ 📌 Context 나열 없음!
```

**8단계: Orchestrator Final Narration**
```
Context:
- 확정: 을지로, 2명, 12시 30분, 돈카츠, 식당 A
- Worker: 예약 완료

Orchestrator (Final Narrator):
→ Message: "내일 12시 30분, 을지로 식당 A에 2명 예약 완료했어요. 맛있게 드세요!" ✅
→ 📌 Context를 자연스럽게 정리 (Orchestrator만 허용)
```

---

## Before vs After 비교

### Before (Context 나열)

```
대화 흐름:
User: "을지로에 2명, 내일 오후 12시반"
Q&A: ❌ "을지로, 2명, 내일 12시 30분으로 확인했습니다"
      → Context 나열

Worker: [메뉴 추천]
Q&A: ❌ "을지로, 2명, 12시 30분으로 확인했습니다. 추천 메뉴는 한식 돈카츠, 일식 초밥, 우동/라멘입니다. 어떤 메뉴로 할까요?"
      → Context 나열 + Worker 결과 나열

User: "돈카츠"
Q&A: ❌ "돈카츠로 진행하겠습니다"
      → 상태 설명

문제점:
1. Q&A Agent가 매번 정보를 반복
2. 사용자가 이미 알고 있는 정보를 계속 들음
3. 부자연스러운 대화
4. Chat이 정보 덤핑장처럼 느껴짐
```

### After (Context/Message 분리)

```
대화 흐름:
User: "을지로에 2명, 내일 오후 12시반"
Q&A: [COMPLETED - 출력 없음]
      → Context에만 저장

Worker: [메뉴 추천]
Q&A: ✅ "어떤 메뉴로 할까요?"
      → 질문만

User: "돈카츠"
Q&A: [COMPLETED - 출력 없음]
      → Context에만 저장

Worker: [식당 검색]
Q&A: ✅ "어떤 식당으로 할까요?"
      → 질문만

User: "1번"
Q&A: [COMPLETED - 출력 없음]

Orchestrator: ✅ "내일 12시 30분, 을지로 식당 A에 2명 예약 완료했어요!"
              → 자연스러운 정리 (Orchestrator만)

장점:
1. Q&A Agent는 질문만 함
2. 사용자는 필요한 정보만 받음
3. 자연스러운 대화
4. Chat이 실제 대화처럼 느껴짐
5. Orchestrator가 마지막에 정리
```

---

## 수정된 파일

**`server_python/agents/dynamic_orchestration.py`** (1곳 수정)

**Lines 985-1051**: Q&A Agent 프롬프트 수정
- System Prompt: Context/Message 분리 원칙 추가
- User Prompt: Context 섹션 레이블링 + 나열 금지 명시

---

## 성공 기준 검증

### 테스트 시나리오

1. **정보 수집 후 선택 질문**
   ```
   User: "을지로, 2명, 12시 30분"

   예상:
   Q&A: "어떤 메뉴로 할까요?"

   ❌ 실패:
   Q&A: "을지로, 2명, 12시 30분으로 확인했습니다. 어떤 메뉴로 할까요?"
   ```

2. **Worker 결과 후 선택 질문**
   ```
   Worker: [메뉴 추천]

   예상:
   Q&A: "어떤 메뉴로 할까요?"

   ❌ 실패:
   Q&A: "추천 메뉴는 한식 돈카츠, 일식 초밥입니다. 어떤 메뉴로 할까요?"
   ```

3. **사용자 선택 후 확인**
   ```
   User: "돈카츠"

   예상:
   Q&A: [COMPLETED - 출력 없음]

   ❌ 실패:
   Q&A: "돈카츠로 진행하겠습니다"
   ```

4. **최종 정리**
   ```
   예상:
   Orchestrator: "내일 12시 30분, 을지로 식당 A에 2명 예약 완료했어요!"

   ✅ 성공:
   - Orchestrator가 Context를 자연스럽게 정리
   - Q&A Agent는 Context 나열 안 함
   ```

---

## 핵심 원칙

### Context vs Message

```
Context (내부 상태):
- 목적: Agent들이 참고하는 정보
- 저장 위치: ConversationState.slots
- 출력: 사용자에게 보이지 않음
- 예시:
  {
    "location": "을지로",
    "party_size": 2,
    "datetime": "12시 30분",
    "menu": "돈카츠"
  }

Message (사용자 대화):
- 목적: 사용자와 대화
- 출력 위치: Chat Panel
- 원칙: Context 나열 금지
- 예시:
  ✅ "어떤 메뉴로 할까요?"
  ❌ "을지로, 2명으로 확인했습니다"
```

### Agent 역할 분리

```
Q&A Agent:
- Context 참고만 (나열 금지)
- 질문만 생성 (ASK/CONFIRM)
- INFORM 패턴 금지

Worker Agent:
- Context만 업데이트
- 사용자와 대화 안 함

Orchestrator:
- Final Narrator (마지막에만)
- Context를 자연스럽게 정리
- 사용자에게 결과 전달
```

---

## 요약

**"Q&A Agent는 Context를 참고만 하고, Message에는 질문만 출력하라"** ✅

- ✅ **Context/Message 분리**: System Prompt에 원칙 명시
- ✅ **나열 금지**: "DO NOT list or summarize" 명시
- ✅ **질문만 생성**: ASK/CONFIRM 패턴만 허용
- ✅ **INFORM 패턴 금지**: "확인했습니다", "진행합니다" 금지

**결과**:
- Q&A Agent: 질문만 함 → 자연스러운 대화
- Worker Agent: Context만 업데이트 → 사용자에게 안 보임
- Orchestrator: 마지막에 정리 → 자연스러운 마무리
- Chat: 실제 대화처럼 느껴짐 → UX 개선

---

**Context/Message 분리가 완성되었습니다!** 🎉

## 전체 아키텍처 (최종)

```
User Request
    ↓
PlannerAgent (Plan 생성)
    ↓
Orchestrator (Workflow 실행)
    ↓
┌─────────────────────────────────┐
│ Agent Loop                      │
│                                 │
│ Q&A Agent:                      │
│ - Context 참고만                │
│ - 질문만 생성 (ASK/CONFIRM)     │
│ - INFORM 금지                   │
│ - Gate: required_slots 체크     │
│                                 │
│ Worker Agent:                   │
│ - Context만 업데이트            │
│ - 사용자와 대화 안 함           │
│                                 │
│ Context:                        │
│ - ConversationState.slots       │
│ - Worker 결과                   │
│ - 사용자에게 안 보임            │
│                                 │
│ Message:                        │
│ - Chat에 출력                   │
│ - Q&A Agent 질문만              │
│ - Orchestrator 정리만           │
└─────────────────────────────────┘
    ↓
Orchestrator Final Narration
    ↓
User Response
```

**모든 구성 요소가 유기적으로 작동하는 자연스러운 대화 시스템** ✅
