#!/usr/bin/env python3
"""
ConversationState - 도메인 중립적 대화 상태 컨테이너

이 모듈은 업무 로직을 알지 못합니다.
모든 업무 의미와 종료 조건은 TaskSchema에서 정의됩니다.

핵심 원칙:
- ConversationState는 업무를 모름
- 업무 의미와 흐름은 TaskSchema로 정의
- Fact(사실)와 Decision(의사결정)을 분리
"""

from typing import Dict, Any, List
from dataclasses import dataclass, field


@dataclass
class ConversationStateV3:
    """
    도메인 중립적 대화 상태 컨테이너

    이 클래스는 업무 로직을 알지 못합니다.
    모든 업무 의미와 종료 조건은 TaskSchema에서 정의됩니다.

    Attributes:
        facts: 사용자 입력에서 추출된 사실 정보 (location, datetime 등)
        decisions: 사용자의 의사 표현 (proceed, approve, selection 등)
        flags: 내부 제어용 상태 (locked, execution_ready 등)
        metadata: 태스크 관련 메타데이터 (task_type, timestamps 등)
    """
    facts: Dict[str, Any] = field(default_factory=dict)
    decisions: Dict[str, Any] = field(default_factory=dict)
    flags: Dict[str, bool] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    # =========================================================================
    # Fact 관련 메서드
    # =========================================================================

    def set_fact(self, key: str, value: Any) -> None:
        """사실 정보 설정"""
        self.facts[key] = value

    def get_fact(self, key: str, default: Any = None) -> Any:
        """사실 정보 조회"""
        return self.facts.get(key, default)

    def has_fact(self, key: str) -> bool:
        """사실 정보 존재 여부 확인 (None이 아닌 값이 있는지)"""
        return key in self.facts and self.facts[key] is not None

    def has_all_facts(self, keys: List[str]) -> bool:
        """모든 지정된 사실 정보가 존재하는지 확인"""
        return all(self.has_fact(k) for k in keys)

    def get_missing_facts(self, required: List[str]) -> List[str]:
        """필요한 사실 정보 중 누락된 것들 반환"""
        return [k for k in required if not self.has_fact(k)]

    # =========================================================================
    # Decision 관련 메서드
    # =========================================================================

    def set_decision(self, key: str, value: Any) -> None:
        """의사결정 설정"""
        self.decisions[key] = value

    def get_decision(self, key: str, default: Any = None) -> Any:
        """의사결정 조회"""
        return self.decisions.get(key, default)

    def has_decision(self, key: str) -> bool:
        """의사결정 존재 여부 확인"""
        return key in self.decisions and self.decisions[key] is not None

    def has_all_decisions(self, keys: List[str]) -> bool:
        """모든 지정된 의사결정이 존재하는지 확인"""
        return all(self.has_decision(k) for k in keys)

    def get_missing_decisions(self, required: List[str]) -> List[str]:
        """필요한 의사결정 중 누락된 것들 반환"""
        return [k for k in required if not self.has_decision(k)]

    # =========================================================================
    # Flag 관련 메서드
    # =========================================================================

    def set_flag(self, key: str, value: bool) -> None:
        """제어 플래그 설정"""
        self.flags[key] = value

    def get_flag(self, key: str, default: bool = False) -> bool:
        """제어 플래그 조회"""
        return self.flags.get(key, default)

    def is_flag_set(self, key: str) -> bool:
        """플래그가 True로 설정되어 있는지 확인"""
        return self.flags.get(key, False) is True

    # =========================================================================
    # Metadata 관련 메서드
    # =========================================================================

    def set_metadata(self, key: str, value: Any) -> None:
        """메타데이터 설정"""
        self.metadata[key] = value

    def get_metadata(self, key: str, default: Any = None) -> Any:
        """메타데이터 조회"""
        return self.metadata.get(key, default)

    # =========================================================================
    # 직렬화
    # =========================================================================

    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 직렬화"""
        return {
            "facts": dict(self.facts),
            "decisions": dict(self.decisions),
            "flags": dict(self.flags),
            "metadata": dict(self.metadata)
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ConversationStateV3':
        """딕셔너리에서 역직렬화"""
        return cls(
            facts=data.get("facts", {}),
            decisions=data.get("decisions", {}),
            flags=data.get("flags", {}),
            metadata=data.get("metadata", {})
        )

    # =========================================================================
    # 유틸리티 메서드
    # =========================================================================

    def get_facts_text(self) -> str:
        """확정된 사실 정보 텍스트 생성"""
        if not self.facts:
            return "(없음)"
        lines = [f"- {key}: {value}" for key, value in self.facts.items() if value is not None]
        return "\n".join(lines) if lines else "(없음)"

    def get_decisions_text(self) -> str:
        """의사결정 정보 텍스트 생성"""
        if not self.decisions:
            return "(없음)"
        lines = [f"- {key}: {value}" for key, value in self.decisions.items() if value is not None]
        return "\n".join(lines) if lines else "(없음)"

    def merge(self, other: 'ConversationStateV3') -> 'ConversationStateV3':
        """다른 상태와 병합 (other의 값이 우선)"""
        merged = ConversationStateV3(
            facts={**self.facts, **other.facts},
            decisions={**self.decisions, **other.decisions},
            flags={**self.flags, **other.flags},
            metadata={**self.metadata, **other.metadata}
        )
        return merged

    def clear(self) -> None:
        """모든 상태 초기화"""
        self.facts.clear()
        self.decisions.clear()
        self.flags.clear()
        self.metadata.clear()

    def __repr__(self) -> str:
        return (
            f"ConversationStateV3("
            f"facts={self.facts}, "
            f"decisions={self.decisions}, "
            f"flags={self.flags})"
        )
