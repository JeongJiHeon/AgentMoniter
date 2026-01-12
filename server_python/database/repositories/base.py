"""
Base repository class with common CRUD operations.
"""

import uuid
from typing import TypeVar, Generic, Optional, List, Type, Any
from datetime import datetime

from sqlalchemy import select, update, delete, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import DeclarativeBase

from ..models import Base

ModelType = TypeVar("ModelType", bound=Base)


class BaseRepository(Generic[ModelType]):
    """Base repository with common CRUD operations."""

    def __init__(self, session: AsyncSession, model: Type[ModelType]):
        self.session = session
        self.model = model

    async def create(self, **kwargs: Any) -> ModelType:
        """Create a new record."""
        instance = self.model(**kwargs)
        self.session.add(instance)
        await self.session.flush()
        await self.session.refresh(instance)
        return instance

    async def get_by_id(self, id: uuid.UUID) -> Optional[ModelType]:
        """Get a record by ID."""
        result = await self.session.execute(
            select(self.model).where(self.model.id == id)
        )
        return result.scalar_one_or_none()

    async def get_all(
        self,
        limit: int = 100,
        offset: int = 0,
        order_by: Optional[str] = None,
        descending: bool = True,
    ) -> List[ModelType]:
        """Get all records with pagination."""
        query = select(self.model)

        # Apply ordering
        if order_by and hasattr(self.model, order_by):
            order_column = getattr(self.model, order_by)
            query = query.order_by(
                order_column.desc() if descending else order_column.asc()
            )
        elif hasattr(self.model, "created_at"):
            query = query.order_by(
                self.model.created_at.desc() if descending else self.model.created_at.asc()
            )

        query = query.limit(limit).offset(offset)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def update(self, id: uuid.UUID, **kwargs: Any) -> Optional[ModelType]:
        """Update a record by ID."""
        # Remove None values if not explicitly updating to None
        updates = {k: v for k, v in kwargs.items() if v is not None or k in kwargs}

        if hasattr(self.model, "updated_at"):
            updates["updated_at"] = datetime.utcnow()

        await self.session.execute(
            update(self.model)
            .where(self.model.id == id)
            .values(**updates)
        )
        await self.session.flush()
        return await self.get_by_id(id)

    async def delete(self, id: uuid.UUID) -> bool:
        """Delete a record by ID."""
        result = await self.session.execute(
            delete(self.model).where(self.model.id == id)
        )
        await self.session.flush()
        return result.rowcount > 0

    async def count(self) -> int:
        """Count all records."""
        result = await self.session.execute(
            select(func.count()).select_from(self.model)
        )
        return result.scalar() or 0

    async def exists(self, id: uuid.UUID) -> bool:
        """Check if a record exists."""
        result = await self.session.execute(
            select(func.count())
            .select_from(self.model)
            .where(self.model.id == id)
        )
        return (result.scalar() or 0) > 0
