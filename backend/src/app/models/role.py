"""SQLAlchemy model for user roles / profiles."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Role(Base):
    """A user role / profile (e.g. ``chemical_engineer``).

    ``name`` is a slug (``[a-z0-9_]+``) that is safe to interpolate
    into the LLM system prompt. ``is_builtin`` marks the seven roles
    seeded at migration time so the admin UI can prevent them from
    being deleted.
    """

    __tablename__ = "roles"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )
    name: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_builtin: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )
