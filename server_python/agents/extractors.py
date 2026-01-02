#!/usr/bin/env python3
"""
Extractors - Fact/Decision 추출기

사용자 입력에서 정보를 추출하여 ConversationStateV3를 업데이트합니다.

핵심 원칙:
- FactExtractor: 객관적 사실 정보 추출 (location, datetime, party_size 등)
- DecisionExtractor: 의사결정 정보 추출 (proceed, selection 등)
- 의미 해석은 TaskSchema에서 담당
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Callable, List, Awaitable
import re

from .conversation_state import ConversationStateV3


# Type alias for LLM call function
LLMCallFunc = Callable[[List[Dict[str, str]], int, bool], Awaitable[str]]


# =============================================================================
# BaseExtractor - 추상 베이스 클래스
# =============================================================================

class BaseExtractor(ABC):
    """추출기 베이스 클래스"""

    @abstractmethod
    async def extract(
        self,
        user_input: str,
        state: ConversationStateV3,
        call_llm_func: Optional[LLMCallFunc] = None
    ) -> Dict[str, Any]:
        """
        사용자 입력에서 정보 추출

        Args:
            user_input: 사용자 입력 텍스트
            state: 현재 ConversationStateV3
            call_llm_func: LLM 호출 함수 (선택)

        Returns:
            추출된 정보 딕셔너리
        """
        pass


# =============================================================================
# FactExtractor - 사실 정보 추출기
# =============================================================================

class FactExtractor(BaseExtractor):
    """
    사실 정보 추출기

    객관적 정보를 추출합니다:
    - location, datetime, party_size
    - name, phone, email
    - budget, preferences

    의사결정(proceed, yes, approve)은 추출하지 않습니다.
    """

    # 패턴 기반 추출 규칙
    PATTERNS = {
        "location": [
            r"(?:위치|장소|지역|어디)(?:는|:)?\s*(.+?)(?:[,\n]|$)",
            r"^(.+?)(?:에서|근처|쪽)",
            r"(을지로|강남|홍대|신촌|이태원|종로|마포|여의도|판교|분당)",
        ],
        "datetime": [
            r"(?:시간|언제|몇시)(?:는|:)?\s*(.+?)(?:[,\n]|$)",
            r"(\d{1,2}:\d{2})",
            r"(오전|오후)\s*(\d{1,2})시(?:\s*(\d{1,2})분)?",
            r"(\d{1,2})시(?:\s*(\d{1,2})분)?",
            r"(오늘|내일|모레|이번\s*주|다음\s*주)",
            r"(\d{1,2})월\s*(\d{1,2})일",
        ],
        "party_size": [
            r"(?:인원|명수|몇명)(?:은|는|:)?\s*(\d+)",
            r"(\d+)\s*명",
            r"(\d+)\s*분",
        ],
        "name": [
            r"(?:이름|성함|예약자)(?:은|는|:)?\s*(.+?)(?:[,\n]|$)",
        ],
        "phone": [
            r"(?:전화|연락처|번호)(?:는|:)?\s*(.+?)(?:[,\n]|$)",
            r"(\d{2,3}[-.\s]?\d{3,4}[-.\s]?\d{4})",
        ],
        "budget": [
            r"(?:예산|가격|비용)(?:은|는|:)?\s*(.+?)(?:[,\n]|$)",
            r"(\d+)\s*(?:원|만원)",
            r"(저렴|보통|비싼|고급)",
        ],
        "food_preference": [
            r"(?:음식|메뉴|종류)(?:는|:)?\s*(.+?)(?:[,\n]|$)",
            r"(한식|중식|일식|양식|분식|중국집|이탈리안|멕시칸)",
        ],
    }

    async def extract(
        self,
        user_input: str,
        state: ConversationStateV3,
        call_llm_func: Optional[LLMCallFunc] = None
    ) -> Dict[str, Any]:
        """사용자 입력에서 사실 정보 추출"""

        if call_llm_func:
            try:
                return await self._extract_with_llm(user_input, state, call_llm_func)
            except Exception as e:
                print(f"[FactExtractor] LLM extraction failed: {e}, falling back to pattern")

        return self._extract_with_patterns(user_input, state)

    async def _extract_with_llm(
        self,
        user_input: str,
        state: ConversationStateV3,
        call_llm_func: LLMCallFunc
    ) -> Dict[str, Any]:
        """LLM 기반 추출"""
        import json

        prompt = f"""다음 사용자 입력에서 객관적 사실 정보만 추출하세요.

사용자 입력: "{user_input}"

현재 확정된 정보:
{state.get_facts_text()}

추출 대상 (사실 정보만):
- location: 위치/지역 (예: 을지로, 강남역)
- datetime: 날짜/시간 (예: 오늘 12시 30분)
- party_size: 인원수 (예: 2명, 4명) - 숫자만 추출
- name: 이름/성함
- phone: 전화번호
- budget: 예산 (예: 2만원, 보통)
- food_preference: 음식 선호 (예: 한식, 일식, 중식, 양식)

중요:
1. 사실 정보만 추출 (의사결정/승인 표현 제외)
2. 입력에 명확히 나타난 정보만 추출
3. 없는 정보는 null
4. party_size는 숫자만 (예: "2명" → 2)
5. **기존 값과 다른 새 값이 나타나면 덮어쓰기** (예: 현재 일식인데 "중식"이 나타나면 food_preference: "중식")
6. "중식은 뭐가 있을까", "일식 말고 한식으로" 같은 표현에서 새로운 food_preference 추출

JSON 형식으로 응답:
{{
  "location": "값 또는 null",
  "datetime": "값 또는 null",
  "party_size": 숫자 또는 null,
  "name": "값 또는 null",
  "phone": "값 또는 null",
  "budget": "값 또는 null",
  "food_preference": "값 또는 null"
}}"""

        response = await call_llm_func(
            [
                {"role": "system", "content": "당신은 정보 추출 전문가입니다. JSON만 응답하세요."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=500,
            json_mode=True
        )

        extracted = json.loads(response)
        print(f"[FactExtractor] LLM extracted: {extracted}")

        # null 값 필터링
        return {k: v for k, v in extracted.items() if v is not None and v != "null"}

    def _extract_with_patterns(
        self,
        user_input: str,
        state: ConversationStateV3
    ) -> Dict[str, Any]:
        """패턴 기반 추출 (폴백)"""
        extracted = {}
        input_clean = user_input.strip()

        for slot_name, patterns in self.PATTERNS.items():
            # 새로운 값이 명시적으로 나타나면 기존 값도 덮어씀
            for pattern in patterns:
                match = re.search(pattern, input_clean, re.IGNORECASE)
                if match:
                    value = match.group(1).strip() if match.lastindex else match.group(0).strip()
                    if value:
                        # party_size는 숫자로 변환
                        if slot_name == "party_size":
                            try:
                                value = int(re.search(r'\d+', value).group())
                            except:
                                pass
                        extracted[slot_name] = value
                        break

        print(f"[FactExtractor] Pattern extracted: {extracted}")
        return extracted


# =============================================================================
# DecisionExtractor - 의사결정 추출기
# =============================================================================

class DecisionExtractor(BaseExtractor):
    """
    의사결정 추출기

    사용자의 의사 표현을 추출합니다:
    - proceed: 진행 여부 (true/false)
    - selection: 선택 항목
    - approval: 승인 여부
    - change_preference: 선호 변경 요청

    사실 정보(location, datetime 등)는 추출하지 않습니다.
    """

    # 긍정 키워드
    POSITIVE_KEYWORDS = [
        "네", "예", "응", "좋아", "그래", "진행", "확인", "오케이",
        "ok", "yes", "sure", "ㅇㅇ", "ㅇ", "굿", "좋습니다",
        "해줘", "해주세요", "부탁", "그렇게"
    ]

    # 부정 키워드
    NEGATIVE_KEYWORDS = [
        "아니", "아뇨", "싫어", "취소", "안해", "됐어", "그만",
        "no", "cancel", "ㄴㄴ", "ㄴ"
    ]

    # 방향 전환 키워드 (다른 옵션 요청)
    CHANGE_REQUEST_KEYWORDS = [
        "다른", "다시", "다르게", "바꿔", "변경", "말고",
        "뭐가 있", "뭐 있", "뭐있", "어떤 게 있",
        "추천해", "보여줘", "알려줘"
    ]

    # 음식 카테고리 키워드 (방향 전환 감지용)
    FOOD_CATEGORIES = [
        "한식", "중식", "일식", "양식", "분식", "이탈리안", "멕시칸",
        "중국", "일본", "한국", "베트남", "태국", "인도"
    ]

    # 선택 패턴
    SELECTION_PATTERNS = [
        r"(\d+)번",
        r"(\d+)\.",
        r"(\d+)째",
        r"첫\s*번째|1번째",
        r"두\s*번째|2번째",
        r"세\s*번째|3번째",
    ]

    async def extract(
        self,
        user_input: str,
        state: ConversationStateV3,
        call_llm_func: Optional[LLMCallFunc] = None
    ) -> Dict[str, Any]:
        """사용자 입력에서 의사결정 추출"""

        decisions = {}
        input_lower = user_input.lower().strip()

        # 1. 선택 패턴 감지
        selection = self._extract_selection(user_input)
        if selection is not None:
            decisions["selection"] = selection
            decisions["selection_index"] = selection

        # 2. 방향 전환 요청 감지 (예: "중식은 뭐가 있을까", "다른 거 추천해줘")
        change_request = self._detect_change_request(user_input, state)
        if change_request:
            decisions["change_preference"] = change_request
            print(f"[DecisionExtractor] Change request detected: {change_request}")
            # 방향 전환 시 proceed=False로 설정 (기존 흐름 중단)
            decisions["proceed"] = False

        # 3. 긍정/부정 감지 (방향 전환이 없는 경우에만)
        if "change_preference" not in decisions:
            if any(kw in input_lower for kw in self.POSITIVE_KEYWORDS):
                decisions["proceed"] = True
            elif any(kw in input_lower for kw in self.NEGATIVE_KEYWORDS):
                decisions["proceed"] = False

        # 4. LLM을 사용한 복잡한 의사결정 분석 (선택사항)
        if call_llm_func and not decisions:
            try:
                llm_decisions = await self._extract_with_llm(user_input, state, call_llm_func)
                decisions.update(llm_decisions)
            except Exception as e:
                print(f"[DecisionExtractor] LLM extraction failed: {e}")

        print(f"[DecisionExtractor] Extracted decisions: {decisions}")
        return decisions

    def _detect_change_request(self, user_input: str, state: ConversationStateV3) -> Optional[str]:
        """
        방향 전환 요청 감지

        예:
        - "중식은 뭐가 있을까" → change_preference: "food_preference:중식"
        - "다른 메뉴 추천해줘" → change_preference: "new_options"
        """
        input_lower = user_input.lower().strip()

        # 패턴 1: "X은/는 뭐가 있을까" (새로운 카테고리 탐색 요청)
        for category in self.FOOD_CATEGORIES:
            if category in input_lower:
                # 방향 전환 키워드와 함께 사용되었는지 확인
                if any(kw in input_lower for kw in self.CHANGE_REQUEST_KEYWORDS):
                    return f"food_preference:{category}"
                # 기존 food_preference와 다른 카테고리가 언급되면 방향 전환
                current_pref = state.get_fact("food_preference")
                if current_pref and category != current_pref:
                    return f"food_preference:{category}"

        # 패턴 2: "다른 거", "다시", "바꿔줘" 등 일반적인 방향 전환
        change_keywords_in_input = [kw for kw in self.CHANGE_REQUEST_KEYWORDS if kw in input_lower]
        if change_keywords_in_input:
            # "다른", "다시" 등이 포함된 경우
            if any(kw in input_lower for kw in ["다른", "다시", "다르게", "바꿔", "변경"]):
                return "new_options"

        return None

    def _extract_selection(self, user_input: str) -> Optional[int]:
        """선택 번호 추출"""
        # 숫자 패턴
        for pattern in self.SELECTION_PATTERNS:
            match = re.search(pattern, user_input, re.IGNORECASE)
            if match:
                try:
                    if match.lastindex:
                        return int(match.group(1))
                except:
                    pass

        # "첫번째", "두번째" 등
        ordinal_map = {"첫": 1, "두": 2, "세": 3, "네": 4, "다섯": 5}
        for word, num in ordinal_map.items():
            if f"{word}번째" in user_input or f"{word} 번째" in user_input:
                return num

        return None

    async def _extract_with_llm(
        self,
        user_input: str,
        state: ConversationStateV3,
        call_llm_func: LLMCallFunc
    ) -> Dict[str, Any]:
        """LLM 기반 의사결정 분석"""
        import json

        prompt = f"""다음 사용자 입력에서 의사결정/의도를 분석하세요.

사용자 입력: "{user_input}"

분석 대상:
- proceed: 진행 의사 (true/false/null)
- selection: 선택한 항목 (문자열 또는 null)
- rejection_reason: 거부 이유 (문자열 또는 null)

중요:
1. 사실 정보(위치, 시간 등)는 분석하지 마세요
2. 오직 의사결정/선택/확인만 분석
3. 불확실하면 null

JSON 형식으로 응답:
{{
  "proceed": true/false/null,
  "selection": "값 또는 null",
  "rejection_reason": "값 또는 null"
}}"""

        response = await call_llm_func(
            [
                {"role": "system", "content": "의사결정 분석 전문가입니다. JSON만 응답하세요."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=300,
            json_mode=True
        )

        extracted = json.loads(response)
        return {k: v for k, v in extracted.items() if v is not None and v != "null"}


# =============================================================================
# CombinedExtractor - 통합 추출기
# =============================================================================

class CombinedExtractor:
    """
    Fact + Decision 통합 추출기

    ConversationStateV3를 직접 업데이트합니다.
    """

    def __init__(self):
        self.fact_extractor = FactExtractor()
        self.decision_extractor = DecisionExtractor()

    async def extract_and_update(
        self,
        user_input: str,
        state: ConversationStateV3,
        call_llm_func: Optional[LLMCallFunc] = None
    ) -> ConversationStateV3:
        """
        사용자 입력에서 정보 추출 및 상태 업데이트

        Args:
            user_input: 사용자 입력
            state: 업데이트할 ConversationStateV3
            call_llm_func: LLM 호출 함수

        Returns:
            업데이트된 ConversationStateV3
        """
        # Fact 추출
        facts = await self.fact_extractor.extract(user_input, state, call_llm_func)
        for key, value in facts.items():
            state.set_fact(key, value)

        # Decision 추출
        decisions = await self.decision_extractor.extract(user_input, state, call_llm_func)
        for key, value in decisions.items():
            state.set_decision(key, value)

        print(f"[CombinedExtractor] State updated - facts: {state.facts}, decisions: {state.decisions}")
        return state

    async def extract_facts_only(
        self,
        user_input: str,
        state: ConversationStateV3,
        call_llm_func: Optional[LLMCallFunc] = None
    ) -> Dict[str, Any]:
        """Fact만 추출 (상태 업데이트 없음)"""
        return await self.fact_extractor.extract(user_input, state, call_llm_func)

    async def extract_decisions_only(
        self,
        user_input: str,
        state: ConversationStateV3,
        call_llm_func: Optional[LLMCallFunc] = None
    ) -> Dict[str, Any]:
        """Decision만 추출 (상태 업데이트 없음)"""
        return await self.decision_extractor.extract(user_input, state, call_llm_func)


# =============================================================================
# 싱글톤 인스턴스
# =============================================================================

# 전역 인스턴스
combined_extractor = CombinedExtractor()
fact_extractor = FactExtractor()
decision_extractor = DecisionExtractor()


# =============================================================================
# 편의 함수
# =============================================================================

async def extract_and_update_state(
    user_input: str,
    state: ConversationStateV3,
    call_llm_func: Optional[LLMCallFunc] = None
) -> ConversationStateV3:
    """
    사용자 입력에서 정보를 추출하고 상태를 업데이트하는 편의 함수

    Args:
        user_input: 사용자 입력
        state: ConversationStateV3
        call_llm_func: LLM 호출 함수

    Returns:
        업데이트된 ConversationStateV3
    """
    return await combined_extractor.extract_and_update(user_input, state, call_llm_func)
