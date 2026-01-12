"""
Exceptions - 커스텀 예외 클래스

프로젝트 전체에서 사용하는 표준화된 예외 클래스입니다.
"""

from typing import Optional, Dict, Any


class AgentMonitorError(Exception):
    """Agent Monitor 기본 에러 클래스"""

    def __init__(
        self,
        message: str,
        code: str = "UNKNOWN_ERROR",
        details: Optional[Dict[str, Any]] = None
    ):
        """
        Args:
            message: 에러 메시지
            code: 에러 코드
            details: 추가 상세 정보
        """
        super().__init__(message)
        self.message = message
        self.code = code
        self.details = details or {}

    def to_dict(self) -> dict:
        """에러를 딕셔너리로 변환"""
        return {
            "code": self.code,
            "message": self.message,
            "details": self.details
        }


class AgentNotFoundError(AgentMonitorError):
    """Agent를 찾을 수 없을 때 발생"""

    def __init__(self, agent_id: str):
        super().__init__(
            message=f"Agent '{agent_id}' not found",
            code="AGENT_NOT_FOUND",
            details={"agent_id": agent_id}
        )


class AgentInitializationError(AgentMonitorError):
    """Agent 초기화 실패 시 발생"""

    def __init__(self, agent_id: str, reason: str):
        super().__init__(
            message=f"Failed to initialize agent '{agent_id}': {reason}",
            code="AGENT_INITIALIZATION_FAILED",
            details={"agent_id": agent_id, "reason": reason}
        )


class WorkflowError(AgentMonitorError):
    """워크플로우 관련 에러"""

    def __init__(self, message: str, workflow_id: Optional[str] = None):
        super().__init__(
            message=message,
            code="WORKFLOW_ERROR",
            details={"workflow_id": workflow_id} if workflow_id else {}
        )


class LLMError(AgentMonitorError):
    """LLM 호출 관련 에러"""

    def __init__(
        self,
        message: str,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        status_code: Optional[int] = None
    ):
        super().__init__(
            message=message,
            code="LLM_ERROR",
            details={
                "provider": provider,
                "model": model,
                "status_code": status_code
            }
        )


class ValidationError(AgentMonitorError):
    """입력 검증 실패 시 발생"""

    def __init__(self, message: str, field: Optional[str] = None):
        super().__init__(
            message=message,
            code="VALIDATION_ERROR",
            details={"field": field} if field else {}
        )


class WebSocketError(AgentMonitorError):
    """WebSocket 관련 에러"""

    def __init__(self, message: str, client_id: Optional[str] = None):
        super().__init__(
            message=message,
            code="WEBSOCKET_ERROR",
            details={"client_id": client_id} if client_id else {}
        )


class MCPServiceError(AgentMonitorError):
    """MCP 서비스 관련 에러"""

    def __init__(
        self,
        message: str,
        service_type: Optional[str] = None,
        action: Optional[str] = None
    ):
        super().__init__(
            message=message,
            code="MCP_SERVICE_ERROR",
            details={
                "service_type": service_type,
                "action": action
            }
        )
