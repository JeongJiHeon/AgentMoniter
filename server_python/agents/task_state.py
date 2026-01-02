#!/usr/bin/env python3
"""
Task State Machine - Task/Agent 상태 관리

명시적인 상태 머신을 통해 Task와 Agent의 상태를 관리합니다.

핵심 원칙:
- Task 상태는 명시적인 전이 조건으로만 변경
- Agent 상태는 실시간으로 추적 및 broadcast
- Execution 단위로 로그 관리 (가비지 방지)
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime
from uuid import uuid4


# =============================================================================
# Task 상태 정의
# =============================================================================

class TaskStatus(str, Enum):
    """Task 상태 머신"""
    IDLE = "idle"                      # 초기 상태
    RUNNING = "running"                # 실행 중
    WAITING_USER = "waiting_user"      # 사용자 입력 대기
    COMPLETED = "completed"            # 완료
    FAILED = "failed"                  # 실패


class AgentExecutionStatus(str, Enum):
    """Agent 실행 상태"""
    REGISTERED = "registered"          # 시스템에 등록됨
    IDLE = "idle"                      # 대기 중 (사용 가능)
    RUNNING = "running"                # 현재 작업 수행 중
    WAITING = "waiting"                # 응답 대기 중
    DISABLED = "disabled"              # 비활성화됨


# =============================================================================
# Task Execution Context
# =============================================================================

@dataclass
class TaskExecution:
    """
    Task 실행 단위

    각 Task 실행마다 고유한 execution_id를 부여하여
    로그와 상태를 격리합니다.
    """
    execution_id: str = field(default_factory=lambda: str(uuid4()))
    task_id: str = ""
    status: TaskStatus = TaskStatus.IDLE

    # Agent 추적
    assigned_agents: List[str] = field(default_factory=list)
    active_agent_id: Optional[str] = None
    active_agent_name: Optional[str] = None

    # 진행 상태
    total_steps: int = 0
    completed_steps: int = 0
    current_step_description: str = ""

    # 타임스탬프
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    last_activity: Optional[datetime] = None

    # 로그 (execution 단위)
    logs: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "execution_id": self.execution_id,
            "task_id": self.task_id,
            "status": self.status.value,
            "assigned_agents": self.assigned_agents,
            "active_agent_id": self.active_agent_id,
            "active_agent_name": self.active_agent_name,
            "total_steps": self.total_steps,
            "completed_steps": self.completed_steps,
            "current_step_description": self.current_step_description,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "last_activity": self.last_activity.isoformat() if self.last_activity else None,
        }


# =============================================================================
# Agent Status Tracker
# =============================================================================

@dataclass
class AgentStatus:
    """Agent 상태 추적"""
    agent_id: str
    agent_name: str
    status: AgentExecutionStatus = AgentExecutionStatus.IDLE
    current_task_id: Optional[str] = None
    current_execution_id: Optional[str] = None
    current_step: Optional[str] = None
    last_activity: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "agent_name": self.agent_name,
            "status": self.status.value,
            "current_task_id": self.current_task_id,
            "current_execution_id": self.current_execution_id,
            "current_step": self.current_step,
            "last_activity": self.last_activity.isoformat() if self.last_activity else None,
        }


# =============================================================================
# Task State Manager
# =============================================================================

class TaskStateManager:
    """
    Task 상태 관리자

    - Task 상태 머신 관리
    - 종료 조건 자동 판별
    - Execution 단위 로그 관리
    - Agent 활성 상태 추적
    """

    def __init__(self):
        # Task 실행 컨텍스트
        self._executions: Dict[str, TaskExecution] = {}

        # Agent 상태 추적
        self._agent_statuses: Dict[str, AgentStatus] = {}

        # 이벤트 핸들러
        self._on_status_change: Optional[Callable] = None
        self._on_agent_change: Optional[Callable] = None

    # =========================================================================
    # Event Handlers
    # =========================================================================

    def set_status_change_handler(self, handler: Callable) -> None:
        """Task 상태 변경 핸들러 설정"""
        self._on_status_change = handler

    def set_agent_change_handler(self, handler: Callable) -> None:
        """Agent 상태 변경 핸들러 설정"""
        self._on_agent_change = handler

    # =========================================================================
    # Task Execution Lifecycle
    # =========================================================================

    def start_execution(self, task_id: str, total_steps: int = 0) -> TaskExecution:
        """
        새로운 Task 실행 시작

        Returns:
            새로운 TaskExecution 인스턴스
        """
        execution = TaskExecution(
            task_id=task_id,
            status=TaskStatus.RUNNING,
            total_steps=total_steps,
            started_at=datetime.now(),
            last_activity=datetime.now()
        )
        self._executions[task_id] = execution

        self._emit_status_change(task_id, TaskStatus.IDLE, TaskStatus.RUNNING)
        return execution

    def get_execution(self, task_id: str) -> Optional[TaskExecution]:
        """Task 실행 컨텍스트 조회"""
        return self._executions.get(task_id)

    def update_execution(
        self,
        task_id: str,
        status: Optional[TaskStatus] = None,
        active_agent_id: Optional[str] = None,
        active_agent_name: Optional[str] = None,
        current_step: Optional[str] = None,
        completed_steps: Optional[int] = None
    ) -> Optional[TaskExecution]:
        """Task 실행 상태 업데이트"""
        execution = self._executions.get(task_id)
        if not execution:
            return None

        old_status = execution.status

        if status:
            execution.status = status
        if active_agent_id is not None:
            execution.active_agent_id = active_agent_id
        if active_agent_name is not None:
            execution.active_agent_name = active_agent_name
        if current_step is not None:
            execution.current_step_description = current_step
        if completed_steps is not None:
            execution.completed_steps = completed_steps

        execution.last_activity = datetime.now()

        if status and status != old_status:
            self._emit_status_change(task_id, old_status, status)

        return execution

    def complete_execution(self, task_id: str, success: bool = True) -> Optional[TaskExecution]:
        """
        Task 실행 완료

        Args:
            task_id: Task ID
            success: 성공 여부
        """
        execution = self._executions.get(task_id)
        if not execution:
            return None

        old_status = execution.status
        new_status = TaskStatus.COMPLETED if success else TaskStatus.FAILED

        execution.status = new_status
        execution.completed_at = datetime.now()
        execution.last_activity = datetime.now()
        execution.active_agent_id = None
        execution.active_agent_name = None

        # 해당 Task에 할당된 모든 Agent를 IDLE로 변경
        for agent_id in execution.assigned_agents:
            self.update_agent_status(
                agent_id=agent_id,
                status=AgentExecutionStatus.IDLE,
                current_task_id=None,
                current_step=None
            )

        self._emit_status_change(task_id, old_status, new_status)
        return execution

    def set_waiting_user(self, task_id: str) -> Optional[TaskExecution]:
        """사용자 입력 대기 상태로 전환"""
        return self.update_execution(task_id, status=TaskStatus.WAITING_USER)

    # =========================================================================
    # Agent Status Management
    # =========================================================================

    def register_agent(self, agent_id: str, agent_name: str) -> AgentStatus:
        """Agent 등록"""
        agent_status = AgentStatus(
            agent_id=agent_id,
            agent_name=agent_name,
            status=AgentExecutionStatus.REGISTERED,
            last_activity=datetime.now()
        )
        self._agent_statuses[agent_id] = agent_status
        return agent_status

    def get_agent_status(self, agent_id: str) -> Optional[AgentStatus]:
        """Agent 상태 조회"""
        return self._agent_statuses.get(agent_id)

    def update_agent_status(
        self,
        agent_id: str,
        status: Optional[AgentExecutionStatus] = None,
        current_task_id: Optional[str] = None,
        current_step: Optional[str] = None,
        agent_name: Optional[str] = None
    ) -> Optional[AgentStatus]:
        """Agent 상태 업데이트"""
        agent_status = self._agent_statuses.get(agent_id)

        if not agent_status:
            # 자동 등록
            agent_status = AgentStatus(
                agent_id=agent_id,
                agent_name=agent_name or agent_id
            )
            self._agent_statuses[agent_id] = agent_status

        old_status = agent_status.status

        if status:
            agent_status.status = status
        if current_task_id is not None:
            agent_status.current_task_id = current_task_id
        if current_step is not None:
            agent_status.current_step = current_step
        if agent_name:
            agent_status.agent_name = agent_name

        agent_status.last_activity = datetime.now()

        if status and status != old_status:
            self._emit_agent_change(agent_status)

        return agent_status

    def set_agent_running(
        self,
        agent_id: str,
        agent_name: str,
        task_id: str,
        execution_id: str,
        step_description: str = ""
    ) -> AgentStatus:
        """Agent를 실행 중 상태로 설정"""
        agent_status = self.update_agent_status(
            agent_id=agent_id,
            agent_name=agent_name,
            status=AgentExecutionStatus.RUNNING,
            current_task_id=task_id,
            current_step=step_description
        )
        if agent_status:
            agent_status.current_execution_id = execution_id

        # Task execution에 Agent 추가
        execution = self._executions.get(task_id)
        if execution and agent_id not in execution.assigned_agents:
            execution.assigned_agents.append(agent_id)

        return agent_status

    def set_agent_idle(self, agent_id: str) -> Optional[AgentStatus]:
        """Agent를 대기 상태로 설정"""
        return self.update_agent_status(
            agent_id=agent_id,
            status=AgentExecutionStatus.IDLE,
            current_task_id=None,
            current_step=None
        )

    # =========================================================================
    # Task Completion Conditions
    # =========================================================================

    def check_completion_conditions(self, task_id: str) -> bool:
        """
        Task 종료 조건 확인

        종료 조건:
        1. 모든 assigned agent가 done 상태
        2. 명시적으로 complete_execution() 호출됨
        3. 모든 required steps가 완료됨

        Returns:
            True if task should be marked as completed
        """
        execution = self._executions.get(task_id)
        if not execution:
            return False

        # 이미 완료/실패 상태면 조건 체크 불필요
        if execution.status in [TaskStatus.COMPLETED, TaskStatus.FAILED]:
            return False

        # 조건 1: 모든 steps 완료
        if execution.total_steps > 0 and execution.completed_steps >= execution.total_steps:
            return True

        # 조건 2: 모든 assigned agent가 IDLE 상태 (작업 완료)
        if execution.assigned_agents:
            all_idle = all(
                self._agent_statuses.get(aid, AgentStatus(aid, aid)).status == AgentExecutionStatus.IDLE
                for aid in execution.assigned_agents
            )
            if all_idle and execution.completed_steps > 0:
                return True

        return False

    def auto_complete_if_done(self, task_id: str) -> bool:
        """종료 조건 충족 시 자동 완료 처리"""
        if self.check_completion_conditions(task_id):
            self.complete_execution(task_id, success=True)
            return True
        return False

    # =========================================================================
    # Log Management (Execution-scoped)
    # =========================================================================

    def add_log(
        self,
        task_id: str,
        agent_id: str,
        agent_name: str,
        log_type: str,
        message: str,
        details: str = ""
    ) -> Optional[Dict[str, Any]]:
        """
        Execution 단위 로그 추가

        이전 execution의 로그는 자동으로 분리됩니다.
        """
        execution = self._executions.get(task_id)
        if not execution:
            return None

        log_entry = {
            "id": str(uuid4()),
            "execution_id": execution.execution_id,
            "agent_id": agent_id,
            "agent_name": agent_name,
            "type": log_type,
            "message": message,
            "details": details,
            "timestamp": datetime.now().isoformat()
        }

        execution.logs.append(log_entry)
        return log_entry

    def get_logs(self, task_id: str, execution_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Task 로그 조회

        Args:
            task_id: Task ID
            execution_id: 특정 execution의 로그만 조회 (None이면 현재 execution)
        """
        execution = self._executions.get(task_id)
        if not execution:
            return []

        target_execution_id = execution_id or execution.execution_id
        return [
            log for log in execution.logs
            if log.get("execution_id") == target_execution_id
        ]

    def clear_stale_logs(self, task_id: str) -> int:
        """
        이전 execution의 stale 로그 정리

        Returns:
            삭제된 로그 수
        """
        execution = self._executions.get(task_id)
        if not execution:
            return 0

        current_execution_id = execution.execution_id
        original_count = len(execution.logs)

        execution.logs = [
            log for log in execution.logs
            if log.get("execution_id") == current_execution_id
        ]

        return original_count - len(execution.logs)

    # =========================================================================
    # Status Summary
    # =========================================================================

    def get_task_summary(self) -> Dict[str, Any]:
        """전체 Task 상태 요약"""
        running = []
        waiting = []
        completed = []
        failed = []

        for task_id, execution in self._executions.items():
            task_info = {
                "task_id": task_id,
                "execution_id": execution.execution_id,
                "active_agent": execution.active_agent_name,
                "progress": f"{execution.completed_steps}/{execution.total_steps}"
            }

            if execution.status == TaskStatus.RUNNING:
                running.append(task_info)
            elif execution.status == TaskStatus.WAITING_USER:
                waiting.append(task_info)
            elif execution.status == TaskStatus.COMPLETED:
                completed.append(task_info)
            elif execution.status == TaskStatus.FAILED:
                failed.append(task_info)

        return {
            "running": running,
            "waiting": waiting,
            "completed": completed,
            "failed": failed,
            "counts": {
                "running": len(running),
                "waiting": len(waiting),
                "completed": len(completed),
                "failed": len(failed),
                "total": len(self._executions)
            }
        }

    def get_agent_summary(self) -> Dict[str, Any]:
        """전체 Agent 상태 요약"""
        registered = []
        idle = []
        running = []
        disabled = []

        for agent_id, status in self._agent_statuses.items():
            agent_info = {
                "agent_id": agent_id,
                "agent_name": status.agent_name,
                "current_task": status.current_task_id,
                "current_step": status.current_step
            }

            if status.status == AgentExecutionStatus.REGISTERED:
                registered.append(agent_info)
            elif status.status == AgentExecutionStatus.IDLE:
                idle.append(agent_info)
            elif status.status == AgentExecutionStatus.RUNNING:
                running.append(agent_info)
            elif status.status == AgentExecutionStatus.DISABLED:
                disabled.append(agent_info)

        # 활성 Agent = registered + idle + running
        active_count = len(registered) + len(idle) + len(running)

        return {
            "registered": registered,
            "idle": idle,
            "running": running,
            "disabled": disabled,
            "counts": {
                "active": active_count,
                "running": len(running),
                "idle": len(idle) + len(registered),
                "disabled": len(disabled),
                "total": len(self._agent_statuses)
            }
        }

    def get_current_active_agent(self, task_id: str) -> Optional[Dict[str, Any]]:
        """현재 실행 중인 Agent 정보"""
        execution = self._executions.get(task_id)
        if not execution or not execution.active_agent_id:
            return None

        agent_status = self._agent_statuses.get(execution.active_agent_id)
        if not agent_status:
            return None

        return {
            "agent_id": execution.active_agent_id,
            "agent_name": execution.active_agent_name,
            "status": agent_status.status.value,
            "current_step": execution.current_step_description
        }

    # =========================================================================
    # Cleanup
    # =========================================================================

    def cleanup_completed_tasks(self, older_than_hours: int = 24) -> int:
        """완료된 오래된 Task 정리"""
        cutoff = datetime.now()
        removed = 0

        for task_id in list(self._executions.keys()):
            execution = self._executions[task_id]
            if execution.status in [TaskStatus.COMPLETED, TaskStatus.FAILED]:
                if execution.completed_at:
                    age_hours = (cutoff - execution.completed_at).total_seconds() / 3600
                    if age_hours > older_than_hours:
                        del self._executions[task_id]
                        removed += 1

        return removed

    def reconcile_state(self) -> Dict[str, Any]:
        """
        상태 정합성 검사 및 수정

        Returns:
            수정된 항목 수
        """
        fixes = {
            "zombie_tasks_removed": 0,
            "stale_agents_reset": 0,
            "orphan_logs_removed": 0
        }

        # 1. Zombie task 제거 (RUNNING인데 오래된 경우)
        for task_id, execution in list(self._executions.items()):
            if execution.status == TaskStatus.RUNNING:
                if execution.last_activity:
                    idle_minutes = (datetime.now() - execution.last_activity).total_seconds() / 60
                    if idle_minutes > 30:  # 30분 이상 비활성
                        execution.status = TaskStatus.FAILED
                        fixes["zombie_tasks_removed"] += 1

        # 2. Stale agent 리셋 (RUNNING인데 task가 없는 경우)
        for agent_id, status in self._agent_statuses.items():
            if status.status == AgentExecutionStatus.RUNNING:
                if status.current_task_id:
                    execution = self._executions.get(status.current_task_id)
                    if not execution or execution.status in [TaskStatus.COMPLETED, TaskStatus.FAILED]:
                        status.status = AgentExecutionStatus.IDLE
                        status.current_task_id = None
                        status.current_step = None
                        fixes["stale_agents_reset"] += 1

        return fixes

    # =========================================================================
    # Internal Helpers
    # =========================================================================

    def _emit_status_change(
        self,
        task_id: str,
        old_status: TaskStatus,
        new_status: TaskStatus
    ) -> None:
        """상태 변경 이벤트 발행"""
        if self._on_status_change:
            execution = self._executions.get(task_id)
            self._on_status_change({
                "task_id": task_id,
                "execution_id": execution.execution_id if execution else None,
                "old_status": old_status.value,
                "new_status": new_status.value,
                "timestamp": datetime.now().isoformat()
            })

    def _emit_agent_change(self, agent_status: AgentStatus) -> None:
        """Agent 상태 변경 이벤트 발행"""
        if self._on_agent_change:
            self._on_agent_change(agent_status.to_dict())


# =============================================================================
# Global Instance
# =============================================================================

task_state_manager = TaskStateManager()
