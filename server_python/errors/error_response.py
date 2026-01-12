"""
ErrorResponse - 표준 에러 응답 형식

API 및 WebSocket 응답에서 사용하는 표준화된 에러 응답 클래스입니다.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any
from uuid import uuid4


class ErrorType(str, Enum):
    """에러 유형"""
    NETWORK = "network"
    AUTH = "auth"
    VALIDATION = "validation"
    BUSINESS = "business"
    SYSTEM = "system"


class ErrorSeverity(str, Enum):
    """에러 심각도"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class ErrorResponse:
    """표준 에러 응답"""
    error_code: str
    message: str
    error_type: ErrorType = ErrorType.SYSTEM
    severity: ErrorSeverity = ErrorSeverity.ERROR
    details: Optional[Dict[str, Any]] = None
    trace_id: str = field(default_factory=lambda: str(uuid4()))
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict:
        """딕셔너리로 변환"""
        return {
            "success": False,
            "error": {
                "code": self.error_code,
                "type": self.error_type.value,
                "severity": self.severity.value,
                "message": self.message,
                "details": self.details,
                "traceId": self.trace_id,
                "timestamp": self.timestamp.isoformat()
            }
        }

    def to_websocket_message(self) -> dict:
        """WebSocket 메시지 형식으로 변환"""
        return {
            "type": "error",
            "payload": self.to_dict()["error"]
        }

    @classmethod
    def from_exception(cls, exception: Exception, trace_id: Optional[str] = None):
        """예외로부터 ErrorResponse 생성"""
        from .exceptions import AgentMonitorError

        if isinstance(exception, AgentMonitorError):
            return cls(
                error_code=exception.code,
                message=exception.message,
                details=exception.details,
                trace_id=trace_id or str(uuid4())
            )

        # 일반 예외
        return cls(
            error_code="INTERNAL_ERROR",
            message=str(exception),
            error_type=ErrorType.SYSTEM,
            severity=ErrorSeverity.ERROR,
            trace_id=trace_id or str(uuid4())
        )

    @classmethod
    def validation_error(cls, message: str, field: Optional[str] = None):
        """검증 에러 생성"""
        return cls(
            error_code="VALIDATION_ERROR",
            message=message,
            error_type=ErrorType.VALIDATION,
            severity=ErrorSeverity.WARNING,
            details={"field": field} if field else None
        )

    @classmethod
    def not_found(cls, resource: str, resource_id: str):
        """리소스 미발견 에러 생성"""
        return cls(
            error_code=f"{resource.upper()}_NOT_FOUND",
            message=f"{resource} '{resource_id}' not found",
            error_type=ErrorType.BUSINESS,
            severity=ErrorSeverity.WARNING,
            details={"resource": resource, "id": resource_id}
        )

    @classmethod
    def internal_error(cls, message: str = "Internal server error"):
        """내부 서버 에러 생성"""
        return cls(
            error_code="INTERNAL_ERROR",
            message=message,
            error_type=ErrorType.SYSTEM,
            severity=ErrorSeverity.ERROR
        )
