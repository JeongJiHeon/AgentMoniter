#!/usr/bin/env python3
"""
Orchestration Types - 공통 타입 및 Enum 정의

모든 Orchestration 관련 모듈에서 사용하는 공통 타입을 정의합니다.
"""

from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Any, TYPE_CHECKING

if TYPE_CHECKING:
    from ..conversation_state import ConversationStateV3
    from ..task_schema import TaskSchema


# =============================================================================
# Enums
# =============================================================================

class AgentRole(str, Enum):
    """Agent 역할"""
    ORCHESTRATOR = "orchestrator"      # 워크플로우 조율
    WORKER = "worker"                  # 작업 실행 (사용자와 직접 소통하지 않음)
    Q_AND_A = "q_and_a"                # 사용자와 소통하는 Q&A Agent


class WorkflowPhase(str, Enum):
    """워크플로우 단계"""
    ANALYZING = "analyzing"            # 요청 분석 중
    EXECUTING = "executing"            # Agent 실행 중
    WAITING_USER = "waiting_user"      # 사용자 입력 대기
    COMPLETING = "completing"          # 완료 처리 중
    FINALIZING = "finalizing"          # 최종 정리 중
    COMPLETED = "completed"            # 완료
    FAILED = "failed"                  # 실패


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class AgentStep:
    """단일 Agent 실행 단계"""
    id: str
    agent_id: str
    agent_name: str
    agent_role: AgentRole
    description: str
    order: int
    status: str = "pending"  # pending, running, waiting_user, completed, failed
    result: Optional[str] = None
    data: Optional[Dict[str, Any]] = None
    user_input: Optional[str] = None
    user_prompt: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환"""
        return {
            "id": self.id,
            "agent_id": self.agent_id,
            "agent_name": self.agent_name,
            "agent_role": self.agent_role.value,
            "description": self.description,
            "order": self.order,
            "status": self.status,
            "result": self.result,
            "data": self.data,
            "user_input": self.user_input,
            "user_prompt": self.user_prompt,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }


@dataclass
class DynamicWorkflow:
    """동적 워크플로우 상태"""
    task_id: str
    original_request: str
    phase: WorkflowPhase = WorkflowPhase.ANALYZING
    steps: List[AgentStep] = field(default_factory=list)
    current_step_index: int = 0
    context: Dict[str, Any] = field(default_factory=dict)
    conversation_state: Optional['ConversationStateV3'] = None
    task_schema: Optional['TaskSchema'] = None
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    def add_step(self, step: AgentStep) -> None:
        """스텝 추가"""
        self.steps.append(step)
        self.updated_at = datetime.now()

    def get_current_step(self) -> Optional[AgentStep]:
        """현재 스텝 반환"""
        if 0 <= self.current_step_index < len(self.steps):
            return self.steps[self.current_step_index]
        return None

    def advance(self) -> bool:
        """다음 스텝으로 진행"""
        if self.current_step_index < len(self.steps) - 1:
            self.current_step_index += 1
            self.updated_at = datetime.now()
            return True
        return False

    def get_completed_results(self) -> List[Dict[str, Any]]:
        """완료된 스텝 결과들"""
        return [
            {
                "agent_name": s.agent_name,
                "agent_role": s.agent_role,
                "description": s.description,
                "result": s.result,
                "data": s.data,
                "user_input": s.user_input
            }
            for s in self.steps
            if s.status == "completed"
        ]

    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리로 변환 (직렬화용)"""
        return {
            "task_id": self.task_id,
            "original_request": self.original_request,
            "phase": self.phase.value,
            "steps": [s.to_dict() for s in self.steps],
            "current_step_index": self.current_step_index,
            "context": self.context,
            "conversation_state": self.conversation_state.to_dict() if self.conversation_state else None,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


# =============================================================================
# System Agent Definitions
# =============================================================================

SYSTEM_AGENTS = {
    "orchestrator": {
        "id": "orchestrator-system",
        "name": "Orchestration Agent",
        "role": AgentRole.ORCHESTRATOR
    },
    "planner": {
        "id": "planner-agent",
        "name": "Planner Agent",
        "role": AgentRole.ORCHESTRATOR
    },
    "q_and_a": {
        "id": "qa-agent-system",
        "name": "Q&A Agent",
        "role": AgentRole.Q_AND_A
    },
    "notion-mcp": {
        "id": "notion-mcp-agent",
        "name": "Notion MCP Agent",
        "role": AgentRole.WORKER
    },
    "slack-mcp": {
        "id": "slack-mcp-agent",
        "name": "Slack MCP Agent",
        "role": AgentRole.WORKER
    }
}
