from typing import Optional, List, Callable, Dict, Any
from datetime import datetime
from models.agent import ThinkingMode


class StateTransition:
    def __init__(
        self,
        from_state: ThinkingMode,
        to_state: ThinkingMode,
        event: str,
        guard: Optional[Callable[[], bool]] = None,
        action: Optional[Callable[[], Any]] = None
    ):
        self.from_state = from_state
        self.to_state = to_state
        self.event = event
        self.guard = guard
        self.action = action


class StateMachineConfig:
    def __init__(
        self,
        initial_state: ThinkingMode = ThinkingMode.IDLE,
        transitions: Optional[List[StateTransition]] = None,
        on_state_change: Optional[Callable[[ThinkingMode, ThinkingMode, str], None]] = None
    ):
        self.initial_state = initial_state
        self.transitions = transitions or []
        self.on_state_change = on_state_change


class ThinkingModeStateMachine:
    """
    Agent 사고 모드 상태 머신
    
    상태 흐름:
    idle -> exploring -> structuring -> validating -> summarizing -> idle
    
    각 상태에서 가능한 전환:
    - idle: 새 작업 시작 시 exploring으로
    - exploring: 정보 수집 완료 시 structuring으로
    - structuring: 작업 분해 완료 시 validating으로
    - validating: 검증 완료 시 summarizing으로, 실패 시 exploring으로
    - summarizing: 완료 시 idle로
    
    모든 상태에서 가능:
    - pause: 현재 상태 유지하며 일시정지
    - reset: idle로 초기화
    - error: 에러 처리 후 idle로
    """
    
    DEFAULT_TRANSITIONS = [
        # idle에서 시작
        StateTransition(ThinkingMode.IDLE, ThinkingMode.EXPLORING, "START_TASK"),
        
        # exploring (탐색)
        StateTransition(ThinkingMode.EXPLORING, ThinkingMode.STRUCTURING, "INFO_COLLECTED"),
        StateTransition(ThinkingMode.EXPLORING, ThinkingMode.IDLE, "NO_ACTION_NEEDED"),
        
        # structuring (구조화)
        StateTransition(ThinkingMode.STRUCTURING, ThinkingMode.VALIDATING, "STRUCTURE_COMPLETE"),
        StateTransition(ThinkingMode.STRUCTURING, ThinkingMode.EXPLORING, "NEED_MORE_INFO"),
        
        # validating (검증)
        StateTransition(ThinkingMode.VALIDATING, ThinkingMode.SUMMARIZING, "VALIDATION_PASSED"),
        StateTransition(ThinkingMode.VALIDATING, ThinkingMode.EXPLORING, "VALIDATION_FAILED"),
        StateTransition(ThinkingMode.VALIDATING, ThinkingMode.STRUCTURING, "RESTRUCTURE_NEEDED"),
        
        # summarizing (요약)
        StateTransition(ThinkingMode.SUMMARIZING, ThinkingMode.IDLE, "TASK_COMPLETE"),
        StateTransition(ThinkingMode.SUMMARIZING, ThinkingMode.VALIDATING, "REVIEW_NEEDED"),
        
        # 공통 전환 (모든 상태에서 가능)
        StateTransition(ThinkingMode.EXPLORING, ThinkingMode.IDLE, "RESET"),
        StateTransition(ThinkingMode.STRUCTURING, ThinkingMode.IDLE, "RESET"),
        StateTransition(ThinkingMode.VALIDATING, ThinkingMode.IDLE, "RESET"),
        StateTransition(ThinkingMode.SUMMARIZING, ThinkingMode.IDLE, "RESET"),
    ]
    
    def __init__(self, config: Optional[StateMachineConfig] = None):
        if config is None:
            config = StateMachineConfig()
        
        self.config = config
        self.current_state = config.initial_state
        self.history: List[Dict[str, Any]] = []
        self.is_paused = False
    
    def get_state(self) -> ThinkingMode:
        """현재 상태 조회"""
        return self.current_state
    
    def get_is_paused(self) -> bool:
        """일시정지 상태 확인"""
        return self.is_paused
    
    async def transition(self, event: str) -> bool:
        """이벤트 발생으로 상태 전환 시도"""
        if self.is_paused and event not in ["RESUME", "RESET"]:
            print(f"[StateMachine] Paused, ignoring event: {event}")
            return False
        
        valid_transition = None
        for t in self.config.transitions:
            if t.from_state == self.current_state and t.event == event:
                valid_transition = t
                break
        
        if not valid_transition:
            print(f"[StateMachine] No valid transition for event '{event}' from state '{self.current_state}'")
            return False
        
        # Guard 조건 확인
        if valid_transition.guard and not valid_transition.guard():
            print(f"[StateMachine] Guard condition failed for transition: {self.current_state} -> {valid_transition.to_state}")
            return False
        
        previous_state = self.current_state
        self.current_state = valid_transition.to_state
        
        # 히스토리 기록
        self.history.append({
            "from": previous_state,
            "to": self.current_state,
            "event": event,
            "timestamp": datetime.now()
        })
        
        # 액션 실행
        if valid_transition.action:
            if callable(valid_transition.action):
                result = valid_transition.action()
                if hasattr(result, '__await__'):
                    await result
        
        # 상태 변경 콜백
        if self.config.on_state_change:
            self.config.on_state_change(previous_state, self.current_state, event)
        
        print(f"[StateMachine] Transition: {previous_state} -> {self.current_state} (event: {event})")
        return True
    
    def pause(self) -> None:
        """일시정지"""
        self.is_paused = True
        print(f"[StateMachine] Paused at state: {self.current_state}")
    
    def resume(self) -> None:
        """재개"""
        self.is_paused = False
        print(f"[StateMachine] Resumed at state: {self.current_state}")
    
    def reset(self) -> None:
        """초기화"""
        self.current_state = self.config.initial_state
        self.is_paused = False
        print(f"[StateMachine] Reset to initial state: {self.current_state}")
    
    def get_available_events(self) -> List[str]:
        """현재 상태에서 가능한 이벤트 목록"""
        return [
            t.event for t in self.config.transitions
            if t.from_state == self.current_state
        ]
    
    def can_transition(self, event: str) -> bool:
        """특정 이벤트가 현재 상태에서 가능한지 확인"""
        return any(
            t.from_state == self.current_state and t.event == event
            for t in self.config.transitions
        )
    
    def get_history(self) -> List[Dict[str, Any]]:
        """상태 전환 히스토리 조회"""
        return self.history.copy()
    
    @staticmethod
    def get_state_description(state: ThinkingMode) -> str:
        """상태별 설명"""
        descriptions = {
            ThinkingMode.IDLE: "대기 중 - 새로운 작업을 기다리는 상태",
            ThinkingMode.EXPLORING: "탐색 중 - 정보를 수집하고 분석하는 상태",
            ThinkingMode.STRUCTURING: "구조화 중 - 작업을 티켓으로 분해하는 상태",
            ThinkingMode.VALIDATING: "검증 중 - 생성된 티켓을 검토하는 상태",
            ThinkingMode.SUMMARIZING: "요약 중 - 결과를 정리하는 상태",
        }
        return descriptions.get(state, "알 수 없는 상태")

