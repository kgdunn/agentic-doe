"""SQLAlchemy model for one-time password setup / reset tokens.

Used for both:

- The first-time admin bootstrap (``purpose="setup"``): a freshly created
  user has an empty ``password_hash`` and receives a setup link that lets
  them pick their initial password.
- Ordinary password reset for existing users (``purpose="reset"``).

A token is single-use. Once ``used_at`` is set, it can no longer be
redeemed.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class SetupToken(Base):
    __tablename__ = "setup_tokens"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
    )
    token: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    purpose: Mapped[str] = mapped_column(String(20))

    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
