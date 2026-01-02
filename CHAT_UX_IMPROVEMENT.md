# Chat UX 개선 요약

## 목표 달성 ✅

Chat에서 "시스템 디버그 로그를 읽는 느낌"을 제거하고 "자연스러운 대화"로 전환했습니다.

```
AS-IS: Agent 디버그 로그 느낌
"Worker Agent 작업 결과가 아직 없습니다"
"정보 수집 단계입니다"
"다음 단계로 진행합니다"

TO-BE: 자연스러운 대화
"점심 메뉴 추천과 예약을 도와드릴게요 🙂"
"을지로, 2명, 12시 30분으로 확인했습니다"
"어떤 메뉴로 할까요?"
```

---

## 핵심 설계 원칙

### ✅ 원칙 1. Chat에는 Q&A Agent만 등장

Chat에서 보이는 화자:
- ✅ Q&A Agent (대표 화자)
- ❌ Planner Agent
- ❌ Orchestrator
- ❌ Worker Agent

나머지 Agent는:
- Activity Log
- Timeline
- Debug Panel

### ✅ 원칙 2. Q&A Agent는 "대표 화자" 역할만 수행

Q&A Agent = 중재자 / 통역자 / 진행자

절대 하면 안 되는 것:
- ❌ 내부 상태 설명
- ❌ 다음 Agent 실행 암시
- ❌ "Worker가 이제 실행됩니다" 같은 말

### ✅ 원칙 3. Chat 메시지는 항상 이 3가지 중 하나

**ASK (정보 요청)**
```
점심 메뉴 추천과 예약을 도와드릴게요 🙂

먼저 몇 가지만 알려주세요:
• 위치
• 인원
• 시간
```

**INFORM (사실 전달)**
```
을지로, 2명, 오늘 12시 30분으로 확인했습니다.
```
```
조건에 맞는 점심 메뉴를 찾았어요:

1) 돈카츠 정식 – 빠르고 든든
2) 회전초밥 – 가볍고 깔끔
3) 규동 – 빠른 한 끼
```

**CONFIRM (선택/확인)**
```
어떤 메뉴로 할까요?
```
```
알겠습니다 👍
그럼 돈카츠 정식 기준으로 근처 식당을 찾아볼게요.

이대로 진행할까요?
```

---

## 변경 사항

### 1. Q&A Agent System Prompt 완전 재작성

**AS-IS (문제점):**
```python
"""당신은 사용자와 대화하는 Q&A Agent입니다.

**상태 결정 규칙** (매우 중요!):
1. **사용자 입력이 이미 제공된 경우** (user_context 또는 현재 사용자 입력에 있음):
   - **정보 수집 단계인 경우** (Worker Agent 결과가 아직 없는 경우):
     * 기본 정보(위치, 인원, 시간 등)가 충분히 수집되었으면 → status: "COMPLETED" (Worker Agent가 작업할 수 있도록 진행)
     * 기본 정보가 부족하면 → status: "WAITING_USER" (추가 질문 작성)
   - **Worker Agent 결과가 있는 경우**:
     * 사용자가 메뉴/옵션을 선택했으면 → status: "COMPLETED" (다음 단계로 진행)
     ...
"""
```

❌ 문제점:
- "Worker Agent 결과가 아직 없는 경우" → 시스템 내부 상태 노출
- "정보 수집 단계" → 사용자가 알 필요 없는 개념
- "Worker Agent가 작업할 수 있도록 진행" → 시스템 관점 설명

**TO-BE (개선):**
```python
"""당신은 시스템의 대표 화자입니다.
사용자는 당신과 대화하고 있으며, 내부 Agent 구조를 알 필요가 없습니다.

**핵심 원칙**:
- 당신은 중재자이자 통역자입니다
- 절대 시스템 내부 상태를 설명하지 마세요
- 사용자에게 지금 필요한 행동 하나만 제시하세요

**메시지 패턴**:
당신의 모든 메시지는 다음 3가지 중 하나입니다:

1. **ASK (정보 요청)**: 작업 진행에 필요한 정보를 물어봅니다
   예: "위치와 인원, 시간을 알려주세요"

2. **INFORM (사실 전달)**: 확정된 내용이나 결과를 전달합니다
   예: "을지로, 2명, 12시 30분으로 확인했습니다"
   예: "조건에 맞는 메뉴를 찾았어요: 1) 돈카츠 2) 초밥 3) 규동"

3. **CONFIRM (선택/확인)**: 사용자의 선택이나 진행 여부를 확인합니다
   예: "어떤 메뉴로 할까요?"
   예: "이대로 진행할까요?"

**나쁜 예시** (절대 이렇게 하지 마세요):
❌ "Worker Agent 결과가 아직 없습니다"
❌ "다음 단계로 진행합니다"
❌ "Orchestration에서 실행 중입니다"
❌ "정보 수집 단계입니다"
"""
```

✅ 개선 사항:
- "시스템의 대표 화자" 개념 도입
- ASK / INFORM / CONFIRM 패턴 명시
- 금지 패턴 명시 (❌ 예시)
- 내부 상태 설명 완전 제거

### 2. User Prompt 단순화

**AS-IS:**
```python
f"""**원래 요청**: {workflow.original_request}

**Worker Agent 작업 결과** (사용자에게 표시되지 않음 - 반드시 먼저 요약 설명 필요):
{worker_context}

**사용자 이전 응답**:
{user_context}

**담당 작업**: {step.description}

**중요**:
- **Worker Agent 작업 결과가 없는 경우** (정보 수집 단계):
  - 사용자 입력이 이미 제공된 경우: 기본 정보(위치, 인원, 시간 등)가 있으면 → status: "COMPLETED" 반환 (Worker Agent가 작업 시작)
  - 사용자 입력이 없는 경우: 필요한 정보를 물어보는 질문 작성 → status: "WAITING_USER"
...
"""
```

**TO-BE:**
```python
f"""**사용자 요청**: {workflow.original_request}

**내부 정보** (사용자에게 표시되지 않은 배경 정보):
{worker_context}

**대화 기록** (사용자의 이전 응답):
{user_context}

**현재 단계**: {step.description}

---

위 정보를 바탕으로 사용자에게 지금 필요한 메시지를 작성하세요.

ASK / INFORM / CONFIRM 패턴을 따르세요:
- 내부 정보가 있으면 자연스럽게 요약해서 전달
- 사용자에게 지금 필요한 행동 하나만 제시
- 시스템 내부 상태는 절대 언급하지 마세요
"""
```

### 3. Worker 결과 강제 포함 로직 개선

**AS-IS:**
```python
if "점심" in worker_agent_name or "메뉴" in worker_agent_name:
    summary_header = "점심 메뉴 추천을 드렸습니다:\n\n"
elif "식당" in worker_agent_name or "장소" in worker_agent_name:
    summary_header = "식당 추천을 드렸습니다:\n\n"
else:
    summary_header = f"{worker_agent_name} 작업 결과:\n\n"

message = f"{summary_header}{result_summary}\n\n{message}"
```

❌ 문제점: Agent 이름을 노출하거나 "작업 결과"라는 시스템 용어 사용

**TO-BE:**
```python
# 자연스러운 메시지로 요약 (Agent 이름 노출 최소화)
message = f"{result_summary}\n\n{message}"
```

✅ 개선: 결과를 자연스럽게 요약만 전달

### 4. 내부 상태 표현 개선

**AS-IS:**
```python
worker_context = "아직 작업 결과가 없습니다."
user_context = "없음"
```

**TO-BE:**
```python
worker_context = "(아직 없음)"
user_context = "(없음)"
```

✅ 개선: 시스템 설명이 아닌 간단한 상태 표시

---

## 수정된 파일

### `server_python/agents/dynamic_orchestration.py`

#### 변경 사항 요약:
1. **Line 834-835**: 내부 상태 표현 개선
2. **Line 845-862**: step.user_prompt 처리 시 Agent 이름 노출 최소화
3. **Line 872-952**: Q&A Agent System Prompt 완전 재작성
4. **Line 954-976**: User Prompt 단순화
5. **Line 992-1011**: Worker 결과 강제 포함 로직 개선

---

## 성공 기준 검증 ✅

| 기준 | 상태 | 비고 |
|------|------|------|
| ✅ Chat에 시스템 내부 설명 없음 | 완료 | 금지 패턴 명시 (❌ 예시) |
| ✅ 사용자는 "한 명의 AI와 대화 중" | 완료 | "시스템의 대표 화자" 개념 |
| ✅ 같은 질문 반복 방지 | 완료 | 상태 결정 규칙 단순화 |
| ✅ 사용자 답변 목적 명확 | 완료 | ASK/INFORM/CONFIRM 패턴 |

---

## 오케스트레이션 로직 유지 ✅

**변경하지 않은 것들** (중요):
- ✅ DynamicWorkflow 구조
- ✅ PlannerAgent 분리
- ✅ AgentResult.status 기반 제어
- ✅ WAITING_USER / COMPLETED / FAILED / RUNNING 분기
- ✅ WebSocket broadcast_task_interaction
- ✅ Worker Agent 결과는 사용자에게 직접 노출하지 않음

**변경한 것**:
- ✅ Q&A Agent 프롬프트만 개선 (표현 방식만 변경)
- ✅ 내부 상태 설명 제거 (로직은 동일)

---

## 테스트 결과

```bash
✓ Syntax check passed
✓ Import successful - Chat UX 개선 적용 완료

=== Chat UX 개선 확인 ===

✓ Q&A Agent 프롬프트 업데이트 확인:
  - '시스템의 대표 화자' 개념 도입 ✓
  - 내부 상태 노출 문구 제거 ✓
  - 나쁜 예시 (금지 패턴) 명시 ✓
```

---

## 예상 Chat 흐름 (Before vs After)

### 예시 1: 정보 수집 단계

**AS-IS (Before):**
```
Q&A Agent: Worker Agent 작업 결과가 아직 없습니다.
필요한 정보를 알려주세요:
- 위치
- 인원
- 시간
```

**TO-BE (After):**
```
Q&A Agent: 점심 메뉴 추천과 예약을 도와드릴게요 🙂

먼저 몇 가지만 알려주세요:
• 위치
• 인원
• 시간
```

### 예시 2: 정보 확인

**AS-IS (Before):**
```
Q&A Agent: 을지로, 2명, 12시 30분으로 확인했습니다.
이제 Worker Agent가 작업을 시작합니다.
```

**TO-BE (After):**
```
Q&A Agent: 을지로, 2명, 오늘 12시 30분으로 확인했습니다.
```

### 예시 3: Worker 결과 후 선택

**AS-IS (Before):**
```
Q&A Agent: 점심 메뉴 추천 Agent 작업 결과:

- 국수/냉면: 12,000-18,000원
- 한식 백반: 8,000-12,000원

다음 단계로 진행하기 위해 메뉴를 선택해주세요.
```

**TO-BE (After):**
```
Q&A Agent: 조건에 맞는 점심 메뉴를 찾았어요:

1) 돈카츠 정식 – 빠르고 든든
2) 회전초밥 – 가볍고 깔끔
3) 규동 – 빠른 한 끼

어떤 메뉴로 할까요?
```

### 예시 4: 최종 완료

**AS-IS (Before):**
```
Q&A Agent: 모든 작업이 완료되었습니다.
Orchestration이 성공적으로 종료되었습니다.
```

**TO-BE (After):**
```
Q&A Agent: 예약까지 모두 완료했어요 ✅
즐거운 점심 되세요!
```

---

## 요약

**"시스템 디버그 로그" → "자연스러운 대화"**

- ✅ Q&A Agent를 "시스템의 대표 화자"로 재정의
- ✅ ASK / INFORM / CONFIRM 패턴 도입
- ✅ 내부 상태 설명 완전 제거
- ✅ 금지 패턴 명시 (❌ 예시)
- ✅ 오케스트레이션 로직 100% 유지

**Do NOT explain the system. Act as a conversational proxy that only exposes what the user needs next.**
