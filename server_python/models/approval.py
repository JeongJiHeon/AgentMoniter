from enum import Enum
from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import UUID, uuid4
from pydantic import BaseModel, Field
from .ticket import TicketOption


class ApprovalRequestType(str, Enum):
    PROCEED = "proceed"
    SELECT_OPTION = "select_option"
    PRIORITIZE = "prioritize"
    PROVIDE_INPUT = "provide_input"
    CONFIRM_ACTION = "confirm_action"
    REVIEW_RESULT = "review_result"


class ApprovalStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class InputType(str, Enum):
    TEXT = "text"
    NUMBER = "number"
    DATE = "date"
    SELECT = "select"
    MULTISELECT = "multiselect"


class RequiredInput(BaseModel):
    key: str
    label: str
    type: InputType
    required: bool = True
    options: Optional[List[str]] = None


class ApprovalResponse(BaseModel):
    decision: Optional[str] = None  # 'approve', 'reject', 'select', 'input'
    selectedOptionId: Optional[str] = None
    inputValues: Optional[Dict[str, Any]] = None
    comment: Optional[str] = None
    respondedAt: Optional[datetime] = None


class ApprovalRequest(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    ticketId: str
    agentId: str
    
    # 요청 정보
    type: ApprovalRequestType
    message: str
    context: Optional[str] = None
    
    # 선택지
    options: Optional[List[TicketOption]] = None
    
    # 필요한 입력
    requiredInputs: Optional[List[RequiredInput]] = None
    
    # 상태
    status: ApprovalStatus = ApprovalStatus.PENDING
    
    # 응답
    response: Optional[ApprovalResponse] = None
    
    # 만료 설정
    expiresAt: Optional[datetime] = None
    
    # 우선순위
    priority: int = 0
    
    # 타임스탬프
    createdAt: datetime = Field(default_factory=datetime.now)
    updatedAt: datetime = Field(default_factory=datetime.now)


class ApprovalResponseInput(BaseModel):
    requestId: str
    decision: str  # 'approve', 'reject', 'select', 'input'
    selectedOptionId: Optional[str] = None
    inputValues: Optional[Dict[str, Any]] = None
    comment: Optional[str] = None


class CreateApprovalRequestInput(BaseModel):
    ticketId: str
    agentId: str
    type: ApprovalRequestType
    message: str
    context: Optional[str] = None
    options: Optional[List[TicketOption]] = None
    requiredInputs: Optional[List[RequiredInput]] = None
    expiresAt: Optional[datetime] = None
    priority: int = 0

