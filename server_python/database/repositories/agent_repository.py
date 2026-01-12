"""
Agent repository for database operations.
"""

import uuid
from typing import Optional, List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .base import BaseRepository
from ..models import AgentModel


class AgentRepository(BaseRepository[AgentModel]):
    """Repository for Agent operations."""

    def __init__(self, session: AsyncSession):
        super().__init__(session, AgentModel)

    async def get_by_type(self, agent_type: str) -> List[AgentModel]:
        """Get all agents of a specific type."""
        result = await self.session.execute(
            select(AgentModel)
            .where(AgentModel.type == agent_type)
            .order_by(AgentModel.name)
        )
        return list(result.scalars().all())

    async def get_by_name(self, name: str) -> Optional[AgentModel]:
        """Get an agent by name."""
        result = await self.session.execute(
            select(AgentModel).where(AgentModel.name == name)
        )
        return result.scalar_one_or_none()

    async def get_active_agents(self) -> List[AgentModel]:
        """Get all active agents."""
        result = await self.session.execute(
            select(AgentModel)
            .where(AgentModel.status.in_(["running", "registered", "waiting"]))
            .order_by(AgentModel.name)
        )
        return list(result.scalars().all())

    async def get_custom_agents(self) -> List[AgentModel]:
        """Get all custom agents."""
        result = await self.session.execute(
            select(AgentModel)
            .where(AgentModel.is_custom == True)
            .order_by(AgentModel.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_system_agents(self) -> List[AgentModel]:
        """Get all system (non-custom) agents."""
        result = await self.session.execute(
            select(AgentModel)
            .where(AgentModel.is_custom == False)
            .order_by(AgentModel.name)
        )
        return list(result.scalars().all())

    async def update_status(
        self,
        agent_id: uuid.UUID,
        status: str,
        thinking_mode: Optional[str] = None,
    ) -> Optional[AgentModel]:
        """Update agent status and thinking mode."""
        updates = {"status": status}
        if thinking_mode:
            updates["thinking_mode"] = thinking_mode
        return await self.update(agent_id, **updates)

    async def get_or_create(
        self,
        agent_id: uuid.UUID,
        name: str,
        agent_type: str,
        **kwargs
    ) -> AgentModel:
        """Get an existing agent or create a new one."""
        existing = await self.get_by_id(agent_id)
        if existing:
            return existing

        return await self.create(
            id=agent_id,
            name=name,
            type=agent_type,
            **kwargs
        )
