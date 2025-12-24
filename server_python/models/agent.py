from enum import Enum
from datetime import datetime
from typing import Optional, List
from uuid import UUID, uuid4
from pydantic import BaseModel, Field


class ThinkingMode(str, Enum):
    IDLE = "idle"
    EXPLORING = "exploring"
    STRUCTURING = "structuring"
    VALIDATING = "validating"
    SUMMARIZING = "summarizing"


class AgentType(str, Enum):
    DOCUMENT_PROCESSOR = "document-processor"
    EMAIL_HANDLER = "email-handler"
    RESEARCH_ASSISTANT = "research-assistant"
    SCHEDULE_MANAGER = "schedule-manager"
    TASK_COORDINATOR = "task-coordinator"
    CUSTOM = "custom"


class AgentStatus(str, Enum):
    ACTIVE = "active"
    IDLE = "idle"
    PAUSED = "paused"
    ERROR = "error"
    DISABLED = "disabled"


class ConstraintType(str, Enum):
    ACTION_FORBIDDEN = "action_forbidden"
    APPROVAL_REQUIRED = "approval_required"
    NOTIFY_REQUIRED = "notify_required"
    LIMIT_SCOPE = "limit_scope"
    TIME_RESTRICTION = "time_restriction"


class ConstraintSource(str, Enum):
    ONTOLOGY = "ontology"
    USER = "user"
    SYSTEM = "system"


class AgentConstraint(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    type: ConstraintType
    description: str
    condition: Optional[str] = None
    isActive: bool = True
    source: ConstraintSource = ConstraintSource.SYSTEM


class AgentPermissions(BaseModel):
    canCreateTickets: bool = True
    canExecuteApproved: bool = True
    canAccessMcp: List[str] = Field(default_factory=list)


class AgentStats(BaseModel):
    ticketsCreated: int = 0
    ticketsCompleted: int = 0
    ticketsRejected: int = 0
    averageApprovalTime: Optional[float] = None  # ms


class Agent(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    name: str
    type: AgentType
    description: Optional[str] = None
    
    # 상태 정보
    status: AgentStatus = AgentStatus.IDLE
    thinkingMode: ThinkingMode = ThinkingMode.IDLE
    
    # 현재 작업
    currentTaskId: Optional[str] = None
    currentTaskDescription: Optional[str] = None
    
    # 제약조건
    constraints: List[AgentConstraint] = Field(default_factory=list)
    
    # 권한
    permissions: AgentPermissions = Field(default_factory=AgentPermissions)
    
    # 통계
    stats: AgentStats = Field(default_factory=AgentStats)
    
    # 메타데이터
    lastActivity: datetime = Field(default_factory=datetime.now)
    createdAt: datetime = Field(default_factory=datetime.now)
    updatedAt: datetime = Field(default_factory=datetime.now)


class RegisterAgentInput(BaseModel):
    name: str
    type: AgentType
    description: Optional[str] = None
    constraints: Optional[List[dict]] = None
    permissions: Optional[dict] = None


class AgentStateUpdate(BaseModel):
    agentId: str
    status: Optional[AgentStatus] = None
    thinkingMode: Optional[ThinkingMode] = None
    currentTaskId: Optional[str] = None
    currentTaskDescription: Optional[str] = None

