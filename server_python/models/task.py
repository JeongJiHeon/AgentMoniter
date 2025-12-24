from enum import Enum
from datetime import datetime
from typing import Optional, List
from uuid import UUID, uuid4
from pydantic import BaseModel, Field


class TaskStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class TaskPriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class TaskSource(str, Enum):
    MANUAL = "manual"
    SLACK = "slack"
    CONFLUENCE = "confluence"
    EMAIL = "email"
    OTHER = "other"


class Task(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    title: str
    description: str
    status: TaskStatus = TaskStatus.PENDING
    priority: TaskPriority = TaskPriority.MEDIUM
    source: TaskSource = TaskSource.MANUAL
    sourceReference: Optional[str] = None  # 원본 메시지/문서 ID
    assignedAgentId: Optional[str] = None
    autoAssign: Optional[bool] = None  # Task별 자동 할당 여부 (None이면 기본 규칙 적용)
    dueDate: Optional[datetime] = None
    tags: List[str] = Field(default_factory=list)
    createdAt: datetime = Field(default_factory=datetime.now)
    updatedAt: datetime = Field(default_factory=datetime.now)
    completedAt: Optional[datetime] = None


class CreateTaskInput(BaseModel):
    title: str
    description: str
    priority: Optional[TaskPriority] = TaskPriority.MEDIUM
    source: Optional[TaskSource] = TaskSource.MANUAL
    sourceReference: Optional[str] = None
    dueDate: Optional[datetime] = None
    tags: Optional[List[str]] = None
    autoAssign: Optional[bool] = None

