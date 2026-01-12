"""
Task repository for database operations.
"""

import uuid
from typing import Optional, List
from datetime import datetime

from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from .base import BaseRepository
from ..models import TaskModel


class TaskRepository(BaseRepository[TaskModel]):
    """Repository for Task operations."""

    def __init__(self, session: AsyncSession):
        super().__init__(session, TaskModel)

    async def get_with_filters(
        self,
        status: Optional[str] = None,
        priority: Optional[str] = None,
        source: Optional[str] = None,
        assigned_agent_id: Optional[uuid.UUID] = None,
        search: Optional[str] = None,
        tags: Optional[List[str]] = None,
        limit: int = 50,
        offset: int = 0,
        order_by: str = "created_at",
        descending: bool = True,
    ) -> List[TaskModel]:
        """Get tasks with multiple filters."""
        query = select(TaskModel)

        # Apply filters
        if status:
            query = query.where(TaskModel.status == status)
        if priority:
            query = query.where(TaskModel.priority == priority)
        if source:
            query = query.where(TaskModel.source == source)
        if assigned_agent_id:
            query = query.where(TaskModel.assigned_agent_id == assigned_agent_id)
        if search:
            search_pattern = f"%{search}%"
            query = query.where(
                or_(
                    TaskModel.title.ilike(search_pattern),
                    TaskModel.description.ilike(search_pattern),
                )
            )
        if tags:
            # Match any of the provided tags
            query = query.where(TaskModel.tags.overlap(tags))

        # Apply ordering
        if hasattr(TaskModel, order_by):
            order_column = getattr(TaskModel, order_by)
            query = query.order_by(
                order_column.desc() if descending else order_column.asc()
            )

        query = query.limit(limit).offset(offset)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_by_status(self, status: str) -> List[TaskModel]:
        """Get all tasks with a specific status."""
        result = await self.session.execute(
            select(TaskModel)
            .where(TaskModel.status == status)
            .order_by(TaskModel.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_pending_tasks(self) -> List[TaskModel]:
        """Get all pending tasks."""
        return await self.get_by_status("pending")

    async def get_in_progress_tasks(self) -> List[TaskModel]:
        """Get all in-progress tasks."""
        return await self.get_by_status("in_progress")

    async def get_unassigned_tasks(self) -> List[TaskModel]:
        """Get tasks without an assigned agent."""
        result = await self.session.execute(
            select(TaskModel)
            .where(TaskModel.assigned_agent_id.is_(None))
            .where(TaskModel.status.notin_(["completed", "cancelled", "failed"]))
            .order_by(TaskModel.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_tasks_by_agent(self, agent_id: uuid.UUID) -> List[TaskModel]:
        """Get all tasks assigned to a specific agent."""
        result = await self.session.execute(
            select(TaskModel)
            .where(TaskModel.assigned_agent_id == agent_id)
            .order_by(TaskModel.created_at.desc())
        )
        return list(result.scalars().all())

    async def assign_agent(
        self,
        task_id: uuid.UUID,
        agent_id: uuid.UUID,
    ) -> Optional[TaskModel]:
        """Assign an agent to a task."""
        return await self.update(
            task_id,
            assigned_agent_id=agent_id,
            status="in_progress",
        )

    async def complete_task(self, task_id: uuid.UUID) -> Optional[TaskModel]:
        """Mark a task as completed."""
        return await self.update(
            task_id,
            status="completed",
            completed_at=datetime.utcnow(),
        )

    async def cancel_task(self, task_id: uuid.UUID) -> Optional[TaskModel]:
        """Cancel a task."""
        return await self.update(task_id, status="cancelled")

    async def fail_task(self, task_id: uuid.UUID) -> Optional[TaskModel]:
        """Mark a task as failed."""
        return await self.update(task_id, status="failed")

    async def count_by_status(self) -> dict:
        """Get task counts grouped by status."""
        from sqlalchemy import func

        result = await self.session.execute(
            select(TaskModel.status, func.count(TaskModel.id))
            .group_by(TaskModel.status)
        )
        return dict(result.all())

    async def delete_completed_tasks(self) -> int:
        """Delete all completed tasks."""
        from sqlalchemy import delete

        result = await self.session.execute(
            delete(TaskModel).where(TaskModel.status == "completed")
        )
        await self.session.flush()
        return result.rowcount
