from enum import Enum
from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import UUID, uuid4
from pydantic import BaseModel, Field


class TicketStatus(str, Enum):
    DRAFT = "draft"
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    REJECTED = "rejected"
    BLOCKED = "blocked"


class Priority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class TicketOption(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    label: str
    description: str
    isRecommended: bool = False
    metadata: Optional[Dict[str, Any]] = None


class TicketSourceType(str, Enum):
    EMAIL = "email"
    DOCUMENT = "document"
    CHAT = "chat"
    CALENDAR = "calendar"
    MANUAL = "manual"
    SYSTEM = "system"


class TicketSource(BaseModel):
    type: TicketSourceType
    reference: Optional[str] = None


class Ticket(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    agentId: str
    
    # 작업 정의 (5W1H 기반)
    purpose: str  # Why - 왜 이 작업이 필요한가
    content: str  # What - 무엇을 할 것인가
    context: Optional[str] = None  # Where/When - 맥락 정보
    
    # 사용자 결정 요청
    decisionRequired: Optional[str] = None
    options: List[TicketOption] = Field(default_factory=list)
    selectedOptionId: Optional[str] = None
    
    # 실행 계획
    executionPlan: str
    estimatedImpact: Optional[str] = None
    
    # 메타데이터
    status: TicketStatus = TicketStatus.DRAFT
    priority: Priority = Priority.MEDIUM
    
    # 연관 정보
    parentTicketId: Optional[str] = None
    childTicketIds: List[str] = Field(default_factory=list)
    relatedTicketIds: List[str] = Field(default_factory=list)
    
    # 추적 정보
    source: Optional[TicketSource] = None
    
    # 제약조건 (온톨로지에서 적용된)
    appliedConstraints: List[str] = Field(default_factory=list)
    
    # 타임스탬프
    createdAt: datetime = Field(default_factory=datetime.now)
    updatedAt: datetime = Field(default_factory=datetime.now)
    approvedAt: Optional[datetime] = None
    completedAt: Optional[datetime] = None


class CreateTicketInput(BaseModel):
    agentId: str
    purpose: str
    content: str
    context: Optional[str] = None
    decisionRequired: Optional[str] = None
    options: Optional[List[TicketOption]] = None
    executionPlan: str
    estimatedImpact: Optional[str] = None
    priority: Priority = Priority.MEDIUM
    parentTicketId: Optional[str] = None
    childTicketIds: Optional[List[str]] = None
    relatedTicketIds: Optional[List[str]] = None
    source: Optional[TicketSource] = None
    appliedConstraints: Optional[List[str]] = None

