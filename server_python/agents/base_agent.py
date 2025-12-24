from abc import ABC, abstractmethod
from datetime import datetime
from typing import Optional, Dict, Any, Set
from uuid import uuid4
from models.agent import Agent, AgentStateUpdate, ThinkingMode, AgentStatus, AgentConstraint, ConstraintSource
from models.approval import ApprovalRequest
from .types import (
    IAgent,
    AgentConfig,
    AgentEvent,
    AgentEventType,
    AgentEventHandler,
    AgentExecutionContext,
    AgentInput,
    AgentOutput,
)
from .thinking_mode_state_machine import ThinkingModeStateMachine, StateMachineConfig


class BaseAgent(IAgent, ABC):
    """
    기본 Agent 추상 클래스
    
    모든 Worker Agent는 이 클래스를 상속하여 구현합니다.
    핵심 원칙:
    1. 임의로 결정하지 않고 사용자에게 승인 요청
    2. 온톨로지 규칙 준수
    3. 투명한 상태 공개
    """
    
    def __init__(self, config: AgentConfig):
        self._id = str(uuid4())
        self._name = config.name
        self._type = config.type
        
        now = datetime.now()
        
        # 초기 상태 설정
        from models.agent import AgentType, AgentPermissions, AgentStats
        
        # AgentType 변환
        agent_type = AgentType.CUSTOM
        try:
            # type 문자열을 AgentType enum으로 변환 시도
            type_upper = config.type.upper().replace("-", "_")
            if hasattr(AgentType, type_upper):
                agent_type = getattr(AgentType, type_upper)
        except Exception:
            pass
        
        self._state = Agent(
            id=self._id,
            name=config.name,
            type=agent_type,
            description=config.description,
            status=AgentStatus.IDLE,
            thinkingMode=ThinkingMode.IDLE,
            constraints=self._build_constraints(config.constraints or []),
            permissions=self._build_permissions(config.permissions or {}),
            stats=AgentStats(),
            lastActivity=now,
            createdAt=now,
            updatedAt=now,
        )
        
        # 상태 머신 초기화
        self.state_machine = ThinkingModeStateMachine(
            StateMachineConfig(
                initial_state=ThinkingMode.IDLE,
                transitions=ThinkingModeStateMachine.DEFAULT_TRANSITIONS,
                on_state_change=self._on_thinking_mode_change
            )
        )
        
        self.context: Optional[AgentExecutionContext] = None
        self.event_handlers: Dict[str, Set[AgentEventHandler]] = {}
    
    @property
    def id(self) -> str:
        return self._id
    
    @property
    def name(self) -> str:
        return self._name
    
    @property
    def type(self) -> str:
        return self._type
    
    def get_state(self) -> Agent:
        """상태 조회"""
        return self._state.model_copy(deep=True)
    
    def get_thinking_mode(self) -> ThinkingMode:
        """사고 모드 조회"""
        return self.state_machine.get_state()
    
    def is_active(self) -> bool:
        """활성 상태 확인"""
        return self._state.status == AgentStatus.ACTIVE
    
    async def initialize(self, context: AgentExecutionContext) -> None:
        """초기화"""
        self.context = context
        self.log("info", "Agent initialized with context")
        await self.on_initialize(context)
    
    async def start(self) -> None:
        """시작"""
        self._state.status = AgentStatus.ACTIVE
        self._state.lastActivity = datetime.now()
        self.log("info", "Agent started")
        await self.on_start()
        self._emit_state_change()
    
    async def pause(self) -> None:
        """일시정지"""
        self._state.status = AgentStatus.PAUSED
        self.state_machine.pause()
        self.log("info", "Agent paused")
        await self.on_pause()
        self._emit_state_change()
    
    async def resume(self) -> None:
        """재개"""
        self._state.status = AgentStatus.ACTIVE
        self.state_machine.resume()
        self.log("info", "Agent resumed")
        await self.on_resume()
        self._emit_state_change()
    
    async def stop(self) -> None:
        """중지"""
        self._state.status = AgentStatus.IDLE
        self.state_machine.reset()
        self._state.currentTaskId = None
        self._state.currentTaskDescription = None
        self.log("info", "Agent stopped")
        await self.on_stop()
        self._emit_state_change()
    
    async def process(self, input: AgentInput) -> AgentOutput:
        """작업 처리"""
        self._state.status = AgentStatus.ACTIVE
        self._state.lastActivity = datetime.now()
        
        try:
            # 1. 탐색 단계
            await self.state_machine.transition("START_TASK")
            exploration_result = await self.explore(input)
            
            if not exploration_result.get("should_proceed", False):
                await self.state_machine.transition("NO_ACTION_NEEDED")
                return self._create_empty_output()
            
            # 2. 구조화 단계
            await self.state_machine.transition("INFO_COLLECTED")
            structured_result = await self.structure(exploration_result.get("data"))
            
            # 3. 검증 단계
            await self.state_machine.transition("STRUCTURE_COMPLETE")
            validation_result = await self.validate(structured_result)
            
            if not validation_result.get("is_valid", False):
                await self.state_machine.transition("VALIDATION_FAILED")
                return self._create_empty_output()
            
            # 4. 요약 단계
            await self.state_machine.transition("VALIDATION_PASSED")
            output = await self.summarize(validation_result.get("data"))
            
            # 5. 완료
            await self.state_machine.transition("TASK_COMPLETE")
            
            # 통계 업데이트
            self._state.stats.ticketsCreated += len(output.tickets)
            
            return output
        except Exception as error:
            self.log("error", f"Processing error: {error}")
            self.state_machine.reset()
            raise
    
    async def on_approval_received(self, approval: ApprovalRequest) -> None:
        """승인 처리"""
        self.log("info", f"Approval received: {approval.id} - {approval.status}")
        
        if approval.status.value == "approved":
            self._state.stats.ticketsCompleted += 1
            await self.on_approved(approval)
        elif approval.status.value == "rejected":
            self._state.stats.ticketsRejected += 1
            await self.on_rejected(approval)
        
        self._emit_state_change()
    
    async def update_state(self, update: AgentStateUpdate) -> None:
        """상태 업데이트"""
        if update.status:
            self._state.status = update.status
        if update.thinkingMode:
            self._state.thinkingMode = update.thinkingMode
        if update.currentTaskId is not None:
            self._state.currentTaskId = update.currentTaskId
        if update.currentTaskDescription is not None:
            self._state.currentTaskDescription = update.currentTaskDescription
        
        self._state.updatedAt = datetime.now()
        self._state.lastActivity = datetime.now()
        self._emit_state_change()
    
    def on(self, event_type: str, handler: AgentEventHandler) -> None:
        """이벤트 핸들러 등록"""
        if event_type not in self.event_handlers:
            self.event_handlers[event_type] = set()
        self.event_handlers[event_type].add(handler)
    
    def off(self, event_type: str, handler: AgentEventHandler) -> None:
        """이벤트 핸들러 해제"""
        if event_type in self.event_handlers:
            self.event_handlers[event_type].discard(handler)
    
    def emit(self, event: AgentEvent) -> None:
        """이벤트 발생"""
        handlers = self.event_handlers.get(event.type, set())
        for handler in handlers:
            try:
                handler(event)
            except Exception as error:
                print(f"Event handler error: {error}")
    
    # === Protected 메서드 (하위 클래스에서 구현) ===
    
    @abstractmethod
    async def explore(self, input: AgentInput) -> Dict[str, Any]:
        """탐색 단계 - 입력 분석 및 정보 수집"""
        pass
    
    @abstractmethod
    async def structure(self, data: Any) -> Any:
        """구조화 단계 - 작업 분해 및 티켓 생성"""
        pass
    
    @abstractmethod
    async def validate(self, data: Any) -> Dict[str, Any]:
        """검증 단계 - 생성된 구조 검증"""
        pass
    
    @abstractmethod
    async def summarize(self, data: Any) -> AgentOutput:
        """요약 단계 - 최종 출력 생성"""
        pass
    
    # === 라이프사이클 훅 (선택적 오버라이드) ===
    
    async def on_initialize(self, context: AgentExecutionContext) -> None:
        """초기화 훅"""
        pass
    
    async def on_start(self) -> None:
        """시작 훅"""
        pass
    
    async def on_pause(self) -> None:
        """일시정지 훅"""
        pass
    
    async def on_resume(self) -> None:
        """재개 훅"""
        pass
    
    async def on_stop(self) -> None:
        """중지 훅"""
        pass
    
    async def on_approved(self, approval: ApprovalRequest) -> None:
        """승인 훅"""
        pass
    
    async def on_rejected(self, approval: ApprovalRequest) -> None:
        """거부 훅"""
        pass
    
    # === Private 헬퍼 ===
    
    def _build_constraints(self, constraints: list) -> list:
        """제약조건 빌드"""
        result = []
        for c in constraints:
            # 문자열인 경우 딕셔너리로 변환
            if isinstance(c, str):
                c = {
                    "type": "action_forbidden",
                    "description": c
                }
            # 딕셔너리인 경우 그대로 사용
            elif not isinstance(c, dict):
                # 다른 타입은 건너뛰기
                continue
            
            constraint_type = c.get("type", "action_forbidden")
            result.append(AgentConstraint(
                id=str(uuid4()),
                type=constraint_type,
                description=c.get("description", ""),
                condition=c.get("condition"),
                isActive=True,
                source=ConstraintSource.SYSTEM
            ))
        return result
    
    def _build_permissions(self, permissions: dict) -> Any:
        """권한 빌드"""
        from models.agent import AgentPermissions
        return AgentPermissions(
            canCreateTickets=permissions.get("canCreateTickets", True),
            canExecuteApproved=permissions.get("canExecuteApproved", True),
            canAccessMcp=permissions.get("canAccessMcp", [])
        )
    
    def _on_thinking_mode_change(self, from_state: ThinkingMode, to_state: ThinkingMode, event: str) -> None:
        """사고 모드 변경 핸들러"""
        self._state.thinkingMode = to_state
        self._state.updatedAt = datetime.now()
        
        self.emit(AgentEvent(
            type=AgentEventType.STATE_CHANGED,
            agent_id=self._id,
            timestamp=datetime.now(),
            payload={"from": from_state, "to": to_state, "event": event}
        ))
    
    def _emit_state_change(self) -> None:
        """상태 변경 이벤트 발생"""
        self.emit(AgentEvent(
            type=AgentEventType.STATE_CHANGED,
            agent_id=self._id,
            timestamp=datetime.now(),
            payload=self.get_state()
        ))
    
    def log(self, level: str, message: str) -> None:
        """로깅"""
        self.emit(AgentEvent(
            type=AgentEventType.LOG,
            agent_id=self._id,
            timestamp=datetime.now(),
            payload={"level": level, "message": message}
        ))
    
    def _create_empty_output(self) -> AgentOutput:
        """빈 출력 생성"""
        return AgentOutput(
            tickets=[],
            approval_requests=[],
            logs=[]
        )

