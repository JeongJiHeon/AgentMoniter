"""
Audit log repository for tracking changes.
"""

import uuid
from typing import Optional, List, Any
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .base import BaseRepository
from ..models import AuditLogModel


class AuditRepository(BaseRepository[AuditLogModel]):
    """Repository for Audit Log operations."""

    def __init__(self, session: AsyncSession):
        super().__init__(session, AuditLogModel)

    async def log_action(
        self,
        entity_type: str,
        entity_id: uuid.UUID,
        action: str,
        old_value: Optional[dict] = None,
        new_value: Optional[dict] = None,
        performed_by: Optional[str] = None,
    ) -> AuditLogModel:
        """Log an action on an entity."""
        return await self.create(
            entity_type=entity_type,
            entity_id=entity_id,
            action=action,
            old_value=old_value,
            new_value=new_value,
            performed_by=performed_by,
        )

    async def get_by_entity(
        self,
        entity_type: str,
        entity_id: uuid.UUID,
        limit: int = 50,
    ) -> List[AuditLogModel]:
        """Get audit logs for a specific entity."""
        result = await self.session.execute(
            select(AuditLogModel)
            .where(AuditLogModel.entity_type == entity_type)
            .where(AuditLogModel.entity_id == entity_id)
            .order_by(AuditLogModel.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_by_entity_type(
        self,
        entity_type: str,
        limit: int = 100,
        offset: int = 0,
    ) -> List[AuditLogModel]:
        """Get audit logs for a specific entity type."""
        result = await self.session.execute(
            select(AuditLogModel)
            .where(AuditLogModel.entity_type == entity_type)
            .order_by(AuditLogModel.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())

    async def get_by_action(
        self,
        action: str,
        limit: int = 100,
    ) -> List[AuditLogModel]:
        """Get audit logs for a specific action."""
        result = await self.session.execute(
            select(AuditLogModel)
            .where(AuditLogModel.action == action)
            .order_by(AuditLogModel.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_recent(
        self,
        limit: int = 50,
        since: Optional[datetime] = None,
    ) -> List[AuditLogModel]:
        """Get recent audit logs."""
        query = select(AuditLogModel)
        if since:
            query = query.where(AuditLogModel.created_at >= since)
        query = query.order_by(AuditLogModel.created_at.desc()).limit(limit)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def log_task_created(
        self,
        task_id: uuid.UUID,
        task_data: dict,
        performed_by: Optional[str] = None,
    ) -> AuditLogModel:
        """Log task creation."""
        return await self.log_action(
            entity_type="task",
            entity_id=task_id,
            action="created",
            new_value=task_data,
            performed_by=performed_by,
        )

    async def log_task_updated(
        self,
        task_id: uuid.UUID,
        old_data: dict,
        new_data: dict,
        performed_by: Optional[str] = None,
    ) -> AuditLogModel:
        """Log task update."""
        return await self.log_action(
            entity_type="task",
            entity_id=task_id,
            action="updated",
            old_value=old_data,
            new_value=new_data,
            performed_by=performed_by,
        )

    async def log_task_deleted(
        self,
        task_id: uuid.UUID,
        task_data: dict,
        performed_by: Optional[str] = None,
    ) -> AuditLogModel:
        """Log task deletion."""
        return await self.log_action(
            entity_type="task",
            entity_id=task_id,
            action="deleted",
            old_value=task_data,
            performed_by=performed_by,
        )

    async def log_agent_status_change(
        self,
        agent_id: uuid.UUID,
        old_status: str,
        new_status: str,
        performed_by: Optional[str] = None,
    ) -> AuditLogModel:
        """Log agent status change."""
        return await self.log_action(
            entity_type="agent",
            entity_id=agent_id,
            action="status_changed",
            old_value={"status": old_status},
            new_value={"status": new_status},
            performed_by=performed_by,
        )
