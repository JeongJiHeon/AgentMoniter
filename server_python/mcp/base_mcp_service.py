from abc import ABC, abstractmethod
from typing import Dict, Set, Optional
from datetime import datetime
from .types import (
    IMCPService,
    MCPServiceType,
    MCPServiceConfig,
    MCPOperationRequest,
    MCPOperationResult,
    MCPValidationResult,
    MCPEventType,
    MCPEvent,
    MCPEventHandler,
    MCPOperationType,
)


class BaseMCPService(IMCPService, ABC):
    """
    MCP 서비스 기본 추상 클래스
    
    핵심 원칙:
    1. 읽기 작업은 자유롭게 수행
    2. 쓰기 작업은 초안 생성까지만, 최종 저장은 승인 후
    3. 전송 작업(메일 발송, 공유 등)은 반드시 승인 필요
    """
    
    # 승인 필요 여부 판단 기준
    APPROVAL_REQUIRED_OPERATIONS = [
        MCPOperationType.SEND,
        MCPOperationType.PUBLISH,
        MCPOperationType.SHARE,
        MCPOperationType.DELETE,
    ]
    
    APPROVAL_OPTIONAL_OPERATIONS = [
        MCPOperationType.CREATE,
        MCPOperationType.UPDATE,
    ]
    
    NO_APPROVAL_OPERATIONS = [
        MCPOperationType.READ,
        MCPOperationType.SEARCH,
        MCPOperationType.LIST,
    ]
    
    def __init__(self, config: MCPServiceConfig):
        self._type = config.type
        self._name = config.name
        self.config = config
        self._connected = False
        self.event_handlers: Dict[str, Set[MCPEventHandler]] = {}
    
    @property
    def type(self) -> MCPServiceType:
        return self._type
    
    @property
    def name(self) -> str:
        return self._name
    
    def is_connected(self) -> bool:
        return self._connected
    
    async def connect(self) -> None:
        if self._connected:
            return
        
        await self._do_connect()
        self._connected = True
        self._emit(MCPEvent(
            type=MCPEventType.SERVICE_CONNECTED,
            service=self._type,
            timestamp=datetime.now(),
            payload={"name": self._name}
        ))
    
    async def disconnect(self) -> None:
        if not self._connected:
            return
        
        await self._do_disconnect()
        self._connected = False
        self._emit(MCPEvent(
            type=MCPEventType.SERVICE_DISCONNECTED,
            service=self._type,
            timestamp=datetime.now(),
            payload={"name": self._name}
        ))
    
    async def execute(self, request: MCPOperationRequest) -> MCPOperationResult:
        if not self._connected:
            return MCPOperationResult(
                success=False,
                error="Service not connected"
            )
        
        # 승인 확인
        if request.requiresApproval and request.status.value != "approved":
            return MCPOperationResult(
                success=False,
                error="Operation requires approval"
            )
        
        self._emit(MCPEvent(
            type=MCPEventType.OPERATION_STARTED,
            service=self._type,
            timestamp=datetime.now(),
            payload={"operation": request.operation, "target": request.target.model_dump()},
            operation_id=request.id
        ))
        
        try:
            result = await self._do_execute(request)
            
            self._emit(MCPEvent(
                type=MCPEventType.OPERATION_COMPLETED if result.success else MCPEventType.OPERATION_FAILED,
                service=self._type,
                timestamp=datetime.now(),
                payload=result.model_dump(),
                operation_id=request.id
            ))
            
            return result
        except Exception as error:
            error_result = MCPOperationResult(
                success=False,
                error=str(error)
            )
            
            self._emit(MCPEvent(
                type=MCPEventType.OPERATION_FAILED,
                service=self._type,
                timestamp=datetime.now(),
                payload=error_result.model_dump(),
                operation_id=request.id
            ))
            
            return error_result
    
    async def validate(self, request: MCPOperationRequest) -> MCPValidationResult:
        errors = []
        warnings = []
        
        # 기본 검증
        if not request.target or not request.target.type:
            errors.append("Target type is required")
        
        # 승인 필요 여부 판단
        requires_approval = self._determine_approval_requirement(request)
        approval_reason = None
        
        if requires_approval:
            approval_reason = self._get_approval_reason(request)
        
        # 서비스별 추가 검증
        service_validation = await self._do_validate(request)
        errors.extend(service_validation.get("errors", []))
        warnings.extend(service_validation.get("warnings", []))
        
        return MCPValidationResult(
            isValid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            requiresApproval=requires_approval,
            approvalReason=approval_reason
        )
    
    async def rollback(self, operation_id: str) -> bool:
        """롤백 (기본 구현: 롤백 불가)"""
        print(f"[{self._name}] Rollback not supported for operation: {operation_id}")
        return False
    
    def on(self, event_type: str, handler: MCPEventHandler) -> None:
        """이벤트 핸들러 등록"""
        if event_type not in self.event_handlers:
            self.event_handlers[event_type] = set()
        self.event_handlers[event_type].add(handler)
    
    def off(self, event_type: str, handler: MCPEventHandler) -> None:
        """이벤트 핸들러 해제"""
        if event_type in self.event_handlers:
            self.event_handlers[event_type].discard(handler)
    
    def _emit(self, event: MCPEvent) -> None:
        """이벤트 발생"""
        handlers = self.event_handlers.get(event.type, set())
        for handler in handlers:
            try:
                handler(event)
            except Exception as error:
                print(f"[{self._name}] Event handler error: {error}")
    
    def _determine_approval_requirement(self, request: MCPOperationRequest) -> bool:
        """승인 필요 여부 판단"""
        # 필수 승인 작업
        if request.operation in self.APPROVAL_REQUIRED_OPERATIONS:
            return True
        
        # 승인 불필요 작업
        if request.operation in self.NO_APPROVAL_OPERATIONS:
            return False
        
        # 선택적 승인 작업 - 서비스별 정책 적용
        return self._should_require_approval(request)
    
    def _get_approval_reason(self, request: MCPOperationRequest) -> str:
        """승인 사유"""
        reasons = {
            MCPOperationType.SEND: "외부로 메시지/이메일을 발송하려고 합니다",
            MCPOperationType.PUBLISH: "콘텐츠를 공개하려고 합니다",
            MCPOperationType.SHARE: "다른 사용자와 공유하려고 합니다",
            MCPOperationType.DELETE: "데이터를 삭제하려고 합니다",
            MCPOperationType.CREATE: "새 콘텐츠를 생성하려고 합니다",
            MCPOperationType.UPDATE: "기존 콘텐츠를 수정하려고 합니다",
        }
        
        return reasons.get(request.operation, "작업을 수행하려고 합니다")
    
    # === Abstract 메서드 (하위 클래스에서 구현) ===
    
    @abstractmethod
    async def _do_connect(self) -> None:
        pass
    
    @abstractmethod
    async def _do_disconnect(self) -> None:
        pass
    
    @abstractmethod
    async def _do_execute(self, request: MCPOperationRequest) -> MCPOperationResult:
        pass
    
    @abstractmethod
    async def _do_validate(self, request: MCPOperationRequest) -> Dict[str, list]:
        """서비스별 검증 로직"""
        pass
    
    def _should_require_approval(self, request: MCPOperationRequest) -> bool:
        """서비스별 승인 필요 여부 추가 판단 (기본값: create/update는 승인 필요)"""
        return True

