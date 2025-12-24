from enum import Enum
from typing import Optional, Dict, Any, Callable
from datetime import datetime
from uuid import UUID, uuid4
from pydantic import BaseModel, Field


class MCPServiceType(str, Enum):
    NOTION = "notion"
    CONFLUENCE = "confluence"
    GMAIL = "gmail"
    GOOGLE_DOCS = "google-docs"
    GOOGLE_CALENDAR = "google-calendar"
    SLACK = "slack"
    JIRA = "jira"
    GITHUB = "github"
    CUSTOM = "custom"


class MCPOperationType(str, Enum):
    # 읽기 작업 (승인 불필요)
    READ = "read"
    SEARCH = "search"
    LIST = "list"
    
    # 쓰기 작업 (승인 필요)
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    
    # 전송 작업 (승인 필수)
    SEND = "send"
    PUBLISH = "publish"
    SHARE = "share"


class MCPOperationStatus(str, Enum):
    PENDING = "pending"
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class MCPOperationTarget(BaseModel):
    type: str
    id: Optional[str] = None
    path: Optional[str] = None


class MCPOperationRequest(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    agentId: str
    ticketId: Optional[str] = None
    
    # 서비스 정보
    service: MCPServiceType
    operation: MCPOperationType
    
    # 작업 상세
    target: MCPOperationTarget
    
    # 작업 데이터
    payload: Dict[str, Any] = Field(default_factory=dict)
    
    # 상태
    status: MCPOperationStatus = MCPOperationStatus.PENDING
    
    # 승인 요구 여부
    requiresApproval: bool = False
    approvalRequestId: Optional[str] = None
    
    # 결과
    result: Optional[Dict[str, Any]] = None
    
    # 메타데이터
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    # 타임스탬프
    createdAt: datetime = Field(default_factory=datetime.now)
    updatedAt: datetime = Field(default_factory=datetime.now)


class MCPServiceConfig(BaseModel):
    type: MCPServiceType
    name: str
    enabled: bool = True
    credentials: Optional[Dict[str, str]] = None
    baseUrl: Optional[str] = None
    options: Optional[Dict[str, Any]] = None


class MCPOperationResult(BaseModel):
    success: bool
    data: Optional[Any] = None
    error: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class MCPValidationResult(BaseModel):
    isValid: bool
    errors: list = Field(default_factory=list)
    warnings: list = Field(default_factory=list)
    requiresApproval: bool = False
    approvalReason: Optional[str] = None


class MCPEventType:
    OPERATION_STARTED = "operation_started"
    OPERATION_COMPLETED = "operation_completed"
    OPERATION_FAILED = "operation_failed"
    APPROVAL_REQUIRED = "approval_required"
    SERVICE_CONNECTED = "service_connected"
    SERVICE_DISCONNECTED = "service_disconnected"


class MCPEvent:
    def __init__(
        self,
        type: str,
        service: MCPServiceType,
        timestamp: datetime,
        payload: Any,
        operation_id: Optional[str] = None
    ):
        self.type = type
        self.service = service
        self.operation_id = operation_id
        self.timestamp = timestamp
        self.payload = payload


MCPEventHandler = Callable[[MCPEvent], None]


class IMCPService:
    """MCP 서비스 인터페이스"""
    
    @property
    def type(self) -> MCPServiceType:
        raise NotImplementedError
    
    @property
    def name(self) -> str:
        raise NotImplementedError
    
    def is_connected(self) -> bool:
        raise NotImplementedError
    
    async def connect(self) -> None:
        raise NotImplementedError
    
    async def disconnect(self) -> None:
        raise NotImplementedError
    
    async def execute(self, request: MCPOperationRequest) -> MCPOperationResult:
        raise NotImplementedError
    
    async def validate(self, request: MCPOperationRequest) -> MCPValidationResult:
        raise NotImplementedError
    
    async def rollback(self, operation_id: str) -> bool:
        raise NotImplementedError

