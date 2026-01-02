#!/usr/bin/env python3
"""
TaskSchema - 업무별 로직 정의

ConversationState는 도메인 중립적이며, 모든 업무 의미와 종료 조건은
이 모듈의 TaskSchema에서 정의됩니다.

핵심 원칙:
- ConversationState는 업무를 모름
- TaskSchema가 완료 조건과 다음 액션 정책을 정의
- Q&A Agent는 발화 생성만 담당
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Any, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .conversation_state import ConversationStateV3


# =============================================================================
# NextAction - 다음 액션 타입 정의
# =============================================================================

class NextActionType(str, Enum):
    """시스템이 수행해야 할 다음 액션 타입"""
    ASK = "ASK"           # 사용자에게 정보 요청
    INFORM = "INFORM"     # 사용자에게 결과 전달
    CONFIRM = "CONFIRM"   # 사용자에게 선택/확인 요청
    EXECUTE = "EXECUTE"   # Worker Agent 실행
    COMPLETE = "COMPLETE" # 워크플로우 완료


@dataclass
class NextAction:
    """
    TaskSchema가 반환하는 다음 액션 정보

    Attributes:
        action_type: 액션 유형 (ASK, INFORM, CONFIRM, EXECUTE, COMPLETE)
        target_facts: 수집해야 할 fact 키 목록
        target_decisions: 필요한 decision 키 목록
        message_hint: Q&A Agent가 메시지 생성 시 참고할 힌트
        worker_id: EXECUTE 시 실행할 Worker Agent ID (선택)
    """
    action_type: NextActionType
    target_facts: List[str] = field(default_factory=list)
    target_decisions: List[str] = field(default_factory=list)
    message_hint: Optional[str] = None
    worker_id: Optional[str] = None

    def __repr__(self) -> str:
        return (
            f"NextAction({self.action_type.value}, "
            f"facts={self.target_facts}, "
            f"decisions={self.target_decisions})"
        )


# =============================================================================
# TaskSchema - 추상 베이스 클래스
# =============================================================================

class TaskSchema(ABC):
    """
    업무 스키마 추상 클래스

    모든 업무별 로직은 이 클래스를 상속받아 구현합니다.
    ConversationState의 상태를 평가하고, 다음 액션을 결정합니다.

    주요 책임:
    - 필요한 facts/decisions 정의
    - 완료 조건 평가
    - 다음 액션 결정
    """

    @property
    @abstractmethod
    def task_type(self) -> str:
        """업무 유형 식별자"""
        pass

    @property
    @abstractmethod
    def required_facts(self) -> List[str]:
        """수집해야 할 필수 fact 키 목록"""
        pass

    @property
    @abstractmethod
    def required_decisions(self) -> List[str]:
        """필요한 필수 decision 키 목록"""
        pass

    @property
    def optional_facts(self) -> List[str]:
        """선택적 fact 키 목록 (기본값: 빈 리스트)"""
        return []

    @abstractmethod
    def is_complete(self, state: 'ConversationStateV3') -> bool:
        """
        완료 조건 평가

        Args:
            state: 현재 ConversationStateV3

        Returns:
            완료 가능 여부 (True면 워크플로우 진행 가능)
        """
        pass

    @abstractmethod
    def get_next_action(self, state: 'ConversationStateV3') -> NextAction:
        """
        다음 액션 결정

        Args:
            state: 현재 ConversationStateV3

        Returns:
            수행해야 할 NextAction
        """
        pass

    def get_missing_facts(self, state: 'ConversationStateV3') -> List[str]:
        """누락된 필수 fact 반환"""
        return state.get_missing_facts(self.required_facts)

    def get_missing_decisions(self, state: 'ConversationStateV3') -> List[str]:
        """누락된 필수 decision 반환"""
        return state.get_missing_decisions(self.required_decisions)

    def get_progress_summary(self, state: 'ConversationStateV3') -> Dict[str, Any]:
        """진행 상황 요약 반환"""
        return {
            "task_type": self.task_type,
            "facts_collected": list(state.facts.keys()),
            "facts_missing": self.get_missing_facts(state),
            "decisions_made": list(state.decisions.keys()),
            "decisions_missing": self.get_missing_decisions(state),
            "is_complete": self.is_complete(state)
        }


# =============================================================================
# LunchBookingSchema - 점심 예약 업무 스키마
# =============================================================================

class LunchBookingSchema(TaskSchema):
    """
    점심 메뉴 추천 및 식당 예약 업무 스키마

    Flow:
    1. 기본 정보 수집 (location, datetime, party_size)
    2. 메뉴 추천 Worker 실행
    3. 메뉴 선택 확인
    4. 식당 예약 Worker 실행
    5. 예약 확인
    """

    @property
    def task_type(self) -> str:
        return "lunch_booking"

    @property
    def required_facts(self) -> List[str]:
        return ["location", "datetime", "party_size"]

    @property
    def required_decisions(self) -> List[str]:
        return ["menu_selection", "proceed_booking"]

    @property
    def optional_facts(self) -> List[str]:
        return ["budget", "food_preference"]

    def is_complete(self, state: 'ConversationStateV3') -> bool:
        """
        완료 조건:
        - 모든 필수 fact 수집됨
        - 메뉴 선택 완료
        - 예약 진행 확인됨
        """
        has_all_facts = state.has_all_facts(self.required_facts)
        has_all_decisions = state.has_all_decisions(self.required_decisions)
        return has_all_facts and has_all_decisions

    def get_next_action(self, state: 'ConversationStateV3') -> NextAction:
        """
        상태에 따른 다음 액션 결정

        Phase 순서:
        1. 필수 정보 수집 (ASK)
        2. 메뉴 추천 실행 (EXECUTE)
        3. 메뉴 선택 확인 (CONFIRM)
        4. 예약 진행 확인 (CONFIRM)
        5. 완료 (COMPLETE)

        방향 전환 처리:
        - change_preference decision이 있으면 해당 카테고리로 재추천
        """

        # 방향 전환 요청 확인 (최우선 처리)
        change_request = state.get_decision("change_preference")
        if change_request:
            # 방향 전환 플래그 초기화 (재추천 후 다시 트리거되지 않도록)
            state.set_decision("change_preference", None)

            # food_preference 업데이트 (새로운 카테고리로)
            if change_request.startswith("food_preference:"):
                new_preference = change_request.split(":")[1]
                state.set_fact("food_preference", new_preference)
                print(f"[LunchBookingSchema] Preference changed to: {new_preference}")

            # 메뉴 옵션 플래그 리셋 (재추천 트리거)
            state.set_flag("menu_options_available", False)

            # 메뉴 추천 재실행
            return NextAction(
                action_type=NextActionType.EXECUTE,
                worker_id="menu_recommendation",
                message_hint=f"새로운 선호({state.get_fact('food_preference')})로 메뉴를 다시 추천합니다"
            )

        # Phase 1: 필수 정보 수집
        missing_facts = self.get_missing_facts(state)
        if missing_facts:
            return NextAction(
                action_type=NextActionType.ASK,
                target_facts=missing_facts,
                message_hint=self._get_fact_collection_hint(missing_facts)
            )

        # Phase 2: 메뉴 추천 실행 (Worker 결과 없으면)
        if not state.is_flag_set("menu_options_available"):
            return NextAction(
                action_type=NextActionType.EXECUTE,
                worker_id="menu_recommendation",
                message_hint="메뉴 추천 에이전트를 실행합니다"
            )

        # Phase 3: 메뉴 선택 확인
        if not state.has_decision("menu_selection"):
            return NextAction(
                action_type=NextActionType.CONFIRM,
                target_decisions=["menu_selection"],
                message_hint="추천된 메뉴 중에서 선택을 요청합니다"
            )

        # Phase 4: 예약 진행 확인
        if not state.has_decision("proceed_booking"):
            return NextAction(
                action_type=NextActionType.CONFIRM,
                target_decisions=["proceed_booking"],
                message_hint="선택한 메뉴로 예약을 진행할지 확인합니다"
            )

        # Phase 5: 완료
        return NextAction(action_type=NextActionType.COMPLETE)

    def _get_fact_collection_hint(self, missing: List[str]) -> str:
        """누락된 정보에 대한 힌트 생성"""
        hint_map = {
            "location": "위치/지역",
            "datetime": "날짜와 시간",
            "party_size": "인원수"
        }
        items = [hint_map.get(f, f) for f in missing]
        return f"다음 정보가 필요합니다: {', '.join(items)}"


# =============================================================================
# BookingSchema - 일반 예약 업무 스키마
# =============================================================================

class BookingSchema(TaskSchema):
    """
    일반 예약 업무 스키마

    Flow:
    1. 예약자 정보 수집 (name, phone, datetime)
    2. 예약 확인
    """

    @property
    def task_type(self) -> str:
        return "booking"

    @property
    def required_facts(self) -> List[str]:
        return ["name", "phone", "datetime"]

    @property
    def required_decisions(self) -> List[str]:
        return ["proceed_booking"]

    def is_complete(self, state: 'ConversationStateV3') -> bool:
        has_all_facts = state.has_all_facts(self.required_facts)
        has_all_decisions = state.has_all_decisions(self.required_decisions)
        return has_all_facts and has_all_decisions

    def get_next_action(self, state: 'ConversationStateV3') -> NextAction:
        # Phase 1: 정보 수집
        missing_facts = self.get_missing_facts(state)
        if missing_facts:
            hint_map = {
                "name": "예약자 성함",
                "phone": "연락처",
                "datetime": "예약 일시"
            }
            items = [hint_map.get(f, f) for f in missing_facts]
            return NextAction(
                action_type=NextActionType.ASK,
                target_facts=missing_facts,
                message_hint=f"다음 정보가 필요합니다: {', '.join(items)}"
            )

        # Phase 2: 예약 확인
        if not state.has_decision("proceed_booking"):
            return NextAction(
                action_type=NextActionType.CONFIRM,
                target_decisions=["proceed_booking"],
                message_hint="입력된 정보로 예약을 진행할지 확인합니다"
            )

        return NextAction(action_type=NextActionType.COMPLETE)


# =============================================================================
# GeneralSchema - 일반 대화 스키마 (필수 정보 없음)
# =============================================================================

class GeneralSchema(TaskSchema):
    """
    일반 대화 스키마

    필수 정보 없이 자유로운 대화를 처리합니다.
    """

    @property
    def task_type(self) -> str:
        return "general"

    @property
    def required_facts(self) -> List[str]:
        return []

    @property
    def required_decisions(self) -> List[str]:
        return []

    def is_complete(self, state: 'ConversationStateV3') -> bool:
        # 일반 대화는 항상 완료 가능
        return True

    def get_next_action(self, state: 'ConversationStateV3') -> NextAction:
        return NextAction(action_type=NextActionType.COMPLETE)


# =============================================================================
# TaskSchemaRegistry - 스키마 레지스트리
# =============================================================================

class TaskSchemaRegistry:
    """
    TaskSchema 레지스트리

    모든 등록된 스키마를 관리하고,
    사용자 요청에서 적절한 스키마를 추론합니다.
    """

    _schemas: Dict[str, TaskSchema] = {}
    _initialized: bool = False

    @classmethod
    def _ensure_initialized(cls) -> None:
        """기본 스키마 초기화 보장"""
        if not cls._initialized:
            cls._schemas = {
                "lunch_booking": LunchBookingSchema(),
                "booking": BookingSchema(),
                "general": GeneralSchema()
            }
            cls._initialized = True

    @classmethod
    def register(cls, schema: TaskSchema) -> None:
        """스키마 등록"""
        cls._ensure_initialized()
        cls._schemas[schema.task_type] = schema

    @classmethod
    def get(cls, task_type: str) -> Optional[TaskSchema]:
        """task_type으로 스키마 조회"""
        cls._ensure_initialized()
        return cls._schemas.get(task_type)

    @classmethod
    def get_all(cls) -> Dict[str, TaskSchema]:
        """모든 등록된 스키마 반환"""
        cls._ensure_initialized()
        return dict(cls._schemas)

    @classmethod
    def infer_from_request(cls, user_request: str) -> TaskSchema:
        """
        사용자 요청에서 적절한 스키마 추론

        Args:
            user_request: 사용자 요청 텍스트

        Returns:
            추론된 TaskSchema (기본값: GeneralSchema)
        """
        cls._ensure_initialized()
        request_lower = user_request.lower()

        # 점심/저녁/메뉴/식당 관련 키워드
        if any(kw in request_lower for kw in ["점심", "저녁", "메뉴", "추천", "식당", "맛집"]):
            return cls._schemas["lunch_booking"]

        # 예약 관련 키워드
        if any(kw in request_lower for kw in ["예약", "booking", "reserve"]):
            return cls._schemas["booking"]

        # 기본값: 일반 대화
        return cls._schemas["general"]

    @classmethod
    def infer_task_type(cls, user_request: str) -> str:
        """사용자 요청에서 task_type 추론"""
        schema = cls.infer_from_request(user_request)
        return schema.task_type


# =============================================================================
# 유틸리티 함수
# =============================================================================

def create_initial_state_v3(user_request: str) -> 'ConversationStateV3':
    """
    사용자 요청으로부터 초기 ConversationStateV3 생성

    Args:
        user_request: 사용자 요청 텍스트

    Returns:
        초기화된 ConversationStateV3
    """
    from .conversation_state import ConversationStateV3

    schema = TaskSchemaRegistry.infer_from_request(user_request)

    state = ConversationStateV3()
    state.set_metadata("task_type", schema.task_type)
    state.set_metadata("schema_name", schema.__class__.__name__)

    return state
