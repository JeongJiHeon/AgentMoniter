#!/usr/bin/env python3
"""
Workflow Manager - 워크플로우 생명주기 관리

워크플로우 생성, 조회, 업데이트, 삭제를 담당합니다.
Thread-safe한 동시성 제어를 제공합니다.
"""

import asyncio
from typing import Dict, Optional, Any
from datetime import datetime

from .types import DynamicWorkflow, WorkflowPhase


class WorkflowManager:
    """
    워크플로우 상태 관리자 - 동시성 안전

    책임:
    - 워크플로우 CRUD
    - Lock 관리
    - 상태 조회
    """

    def __init__(self):
        self._workflows: Dict[str, DynamicWorkflow] = {}
        self._locks: Dict[str, asyncio.Lock] = {}
        self._global_lock = asyncio.Lock()

    async def get_lock(self, task_id: str) -> asyncio.Lock:
        """task_id별 Lock 획득"""
        async with self._global_lock:
            if task_id not in self._locks:
                self._locks[task_id] = asyncio.Lock()
            return self._locks[task_id]

    async def create_workflow(
        self,
        task_id: str,
        original_request: str,
        conversation_state: Any = None,
        task_schema: Any = None,
        context: Dict[str, Any] = None
    ) -> DynamicWorkflow:
        """새 워크플로우 생성"""
        lock = await self.get_lock(task_id)
        async with lock:
            workflow = DynamicWorkflow(
                task_id=task_id,
                original_request=original_request,
                conversation_state=conversation_state,
                task_schema=task_schema,
                context=context or {}
            )
            self._workflows[task_id] = workflow
            return workflow

    def get_workflow(self, task_id: str) -> Optional[DynamicWorkflow]:
        """워크플로우 조회 (동기)"""
        return self._workflows.get(task_id)

    async def get_workflow_async(self, task_id: str) -> Optional[DynamicWorkflow]:
        """워크플로우 조회 (비동기, Lock 포함)"""
        lock = await self.get_lock(task_id)
        async with lock:
            return self._workflows.get(task_id)

    def has_pending_workflow(self, task_id: str) -> bool:
        """대기 중인 워크플로우가 있는지 확인"""
        workflow = self._workflows.get(task_id)
        return workflow is not None and workflow.phase == WorkflowPhase.WAITING_USER

    async def update_phase(
        self,
        task_id: str,
        phase: WorkflowPhase
    ) -> Optional[DynamicWorkflow]:
        """워크플로우 단계 업데이트"""
        lock = await self.get_lock(task_id)
        async with lock:
            workflow = self._workflows.get(task_id)
            if workflow:
                workflow.phase = phase
                workflow.updated_at = datetime.now()
            return workflow

    async def update_context(
        self,
        task_id: str,
        key: str,
        value: Any
    ) -> Optional[DynamicWorkflow]:
        """워크플로우 컨텍스트 업데이트"""
        lock = await self.get_lock(task_id)
        async with lock:
            workflow = self._workflows.get(task_id)
            if workflow:
                workflow.context[key] = value
                workflow.updated_at = datetime.now()
            return workflow

    def remove_workflow(self, task_id: str) -> Optional[DynamicWorkflow]:
        """워크플로우 제거"""
        workflow = self._workflows.pop(task_id, None)
        self._locks.pop(task_id, None)
        return workflow

    def get_all_workflows(self) -> Dict[str, DynamicWorkflow]:
        """모든 워크플로우 조회"""
        return dict(self._workflows)

    def get_workflows_by_phase(self, phase: WorkflowPhase) -> Dict[str, DynamicWorkflow]:
        """특정 단계의 워크플로우들 조회"""
        return {
            task_id: wf
            for task_id, wf in self._workflows.items()
            if wf.phase == phase
        }

    def cleanup_completed(self, older_than_hours: int = 24) -> int:
        """완료된 오래된 워크플로우 정리"""
        cutoff = datetime.now()
        removed = 0

        for task_id in list(self._workflows.keys()):
            workflow = self._workflows[task_id]
            if workflow.phase in [WorkflowPhase.COMPLETED, WorkflowPhase.FAILED]:
                age_hours = (cutoff - workflow.updated_at).total_seconds() / 3600
                if age_hours > older_than_hours:
                    del self._workflows[task_id]
                    self._locks.pop(task_id, None)
                    removed += 1

        return removed

    def get_summary(self) -> Dict[str, Any]:
        """워크플로우 상태 요약"""
        summary = {
            "total": len(self._workflows),
            "by_phase": {}
        }

        for phase in WorkflowPhase:
            count = sum(
                1 for wf in self._workflows.values()
                if wf.phase == phase
            )
            if count > 0:
                summary["by_phase"][phase.value] = count

        return summary
