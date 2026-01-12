"""
SQLAlchemy ORM models for Agent Monitor.
"""

import uuid
from datetime import datetime
from typing import Optional, List

from sqlalchemy import (
    String,
    Text,
    Boolean,
    Integer,
    DateTime,
    ForeignKey,
    JSON,
    ARRAY,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    mapped_column,
    relationship,
)


class Base(DeclarativeBase):
    """Base class for all ORM models."""
    pass


class TaskModel(Base):
    """Task ORM model."""
    __tablename__ = "tasks"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="pending")
    priority: Mapped[str] = mapped_column(String(50), nullable=False, default="medium")
    source: Mapped[str] = mapped_column(String(50), nullable=False, default="manual")
    source_reference: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    assigned_agent_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("agents.id", ondelete="SET NULL"),
        nullable=True
    )
    auto_assign: Mapped[bool] = mapped_column(Boolean, default=False)
    due_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    tags: Mapped[List[str]] = mapped_column(ARRAY(String), default=list)
    metadata_json: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    graph_data: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )

    # Relationships
    assigned_agent: Mapped[Optional["AgentModel"]] = relationship(
        "AgentModel",
        back_populates="assigned_tasks"
    )
    audit_logs: Mapped[List["AuditLogModel"]] = relationship(
        "AuditLogModel",
        back_populates="task",
        foreign_keys="AuditLogModel.entity_id",
        primaryjoin="and_(TaskModel.id==AuditLogModel.entity_id, AuditLogModel.entity_type=='task')"
    )

    def __repr__(self) -> str:
        return f"<Task(id={self.id}, title='{self.title}', status='{self.status}')>"


class AgentModel(Base):
    """Agent ORM model."""
    __tablename__ = "agents"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    type: Mapped[str] = mapped_column(String(50), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="idle")
    thinking_mode: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    is_custom: Mapped[bool] = mapped_column(Boolean, default=False)
    system_prompt: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    constraints: Mapped[Optional[List[str]]] = mapped_column(ARRAY(String), default=list)
    allowed_mcps: Mapped[Optional[List[str]]] = mapped_column(ARRAY(String), default=list)
    config: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )

    # Relationships
    assigned_tasks: Mapped[List["TaskModel"]] = relationship(
        "TaskModel",
        back_populates="assigned_agent"
    )
    tickets: Mapped[List["TicketModel"]] = relationship(
        "TicketModel",
        back_populates="agent"
    )
    approvals: Mapped[List["ApprovalModel"]] = relationship(
        "ApprovalModel",
        back_populates="agent"
    )

    def __repr__(self) -> str:
        return f"<Agent(id={self.id}, name='{self.name}', type='{self.type}')>"


class TicketModel(Base):
    """Ticket ORM model."""
    __tablename__ = "tickets"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    agent_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("agents.id", ondelete="SET NULL"),
        nullable=True
    )
    purpose: Mapped[str] = mapped_column(Text, nullable=False)
    content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="pending")
    priority: Mapped[int] = mapped_column(Integer, default=0)
    options: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False
    )

    # Relationships
    agent: Mapped[Optional["AgentModel"]] = relationship(
        "AgentModel",
        back_populates="tickets"
    )
    approval: Mapped[Optional["ApprovalModel"]] = relationship(
        "ApprovalModel",
        back_populates="ticket",
        uselist=False
    )

    def __repr__(self) -> str:
        return f"<Ticket(id={self.id}, purpose='{self.purpose[:50]}...', status='{self.status}')>"


class ApprovalModel(Base):
    """Approval request ORM model."""
    __tablename__ = "approvals"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    ticket_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tickets.id", ondelete="CASCADE"),
        nullable=True
    )
    agent_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("agents.id", ondelete="SET NULL"),
        nullable=True
    )
    type: Mapped[str] = mapped_column(String(50), nullable=False)
    message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="pending")
    options: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    response: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False
    )
    responded_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )

    # Relationships
    ticket: Mapped[Optional["TicketModel"]] = relationship(
        "TicketModel",
        back_populates="approval"
    )
    agent: Mapped[Optional["AgentModel"]] = relationship(
        "AgentModel",
        back_populates="approvals"
    )

    def __repr__(self) -> str:
        return f"<Approval(id={self.id}, type='{self.type}', status='{self.status}')>"


class AuditLogModel(Base):
    """Audit log ORM model for tracking changes."""
    __tablename__ = "audit_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False)
    entity_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    action: Mapped[str] = mapped_column(String(50), nullable=False)
    old_value: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    new_value: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    performed_by: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False
    )

    # Optional relationships for convenience
    task: Mapped[Optional["TaskModel"]] = relationship(
        "TaskModel",
        back_populates="audit_logs",
        foreign_keys=[entity_id],
        primaryjoin="and_(AuditLogModel.entity_id==TaskModel.id, AuditLogModel.entity_type=='task')",
        viewonly=True
    )

    def __repr__(self) -> str:
        return f"<AuditLog(id={self.id}, entity_type='{self.entity_type}', action='{self.action}')>"
