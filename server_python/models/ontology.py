from enum import Enum
from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import UUID, uuid4
from pydantic import BaseModel, Field


class PreferenceCategory(str, Enum):
    DECISION_STYLE = "decision_style"
    COMMUNICATION = "communication"
    PRIORITY_RULE = "priority_rule"
    TIME_PREFERENCE = "time_preference"
    RISK_TOLERANCE = "risk_tolerance"


class TabooType(str, Enum):
    ACTION = "action"
    TIMING = "timing"
    TARGET = "target"
    CONTENT = "content"
    METHOD = "method"


class TabooSeverity(str, Enum):
    WARNING = "warning"
    BLOCK = "block"
    CRITICAL = "critical"


class ApprovalConditionType(str, Enum):
    ALWAYS = "always"
    THRESHOLD = "threshold"
    CATEGORY = "category"
    AGENT_TYPE = "agent_type"
    TIME_BASED = "time_based"
    CUSTOM = "custom"


class ApprovalType(str, Enum):
    EXPLICIT = "explicit"
    IMPLICIT_TIMEOUT = "implicit_timeout"
    NOTIFY_ONLY = "notify_only"


class Priority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class ThinkingPreference(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    category: PreferenceCategory
    name: str
    description: str
    value: Any
    weight: float = Field(default=1.0, ge=0.0, le=1.0)


class Taboo(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    type: TabooType
    description: str
    condition: Optional[str] = None
    severity: TabooSeverity = TabooSeverity.BLOCK
    exceptions: List[str] = Field(default_factory=list)


class FailurePattern(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    name: str
    description: str
    triggers: List[str] = Field(default_factory=list)
    symptoms: List[str] = Field(default_factory=list)
    preventiveMeasures: List[str] = Field(default_factory=list)
    isActive: bool = True


class ApprovalCondition(BaseModel):
    type: ApprovalConditionType
    value: Any


class ApprovalRule(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    name: str
    description: str
    condition: ApprovalCondition
    approvalType: ApprovalType = ApprovalType.EXPLICIT
    timeoutMinutes: Optional[int] = None
    priority: int = 0


class TaskTemplate(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    name: str
    description: str
    triggerKeywords: List[str] = Field(default_factory=list)
    defaultPriority: Priority = Priority.MEDIUM
    requiredFields: List[str] = Field(default_factory=list)
    defaultConstraints: List[str] = Field(default_factory=list)
    suggestedAgentType: Optional[str] = None


class GlobalConstraint(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    description: str
    isActive: bool = True


class UserOntology(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    userId: str
    version: int = 1
    
    preferences: List[ThinkingPreference] = Field(default_factory=list)
    taboos: List[Taboo] = Field(default_factory=list)
    failurePatterns: List[FailurePattern] = Field(default_factory=list)
    approvalRules: List[ApprovalRule] = Field(default_factory=list)
    taskTemplates: List[TaskTemplate] = Field(default_factory=list)
    globalConstraints: List[GlobalConstraint] = Field(default_factory=list)
    
    createdAt: datetime = Field(default_factory=datetime.now)
    updatedAt: datetime = Field(default_factory=datetime.now)


class OntologyContext(BaseModel):
    activePreferences: List[ThinkingPreference] = Field(default_factory=list)
    activeTaboos: List[Taboo] = Field(default_factory=list)
    activeApprovalRules: List[ApprovalRule] = Field(default_factory=list)
    matchedFailurePatterns: List[FailurePattern] = Field(default_factory=list)
    appliedConstraints: List[str] = Field(default_factory=list)

