"""SQLAlchemy model for experiment persistence.

An Experiment is created along two paths:

- Auto-created by ``experiment_service._create_experiment_from_design``
  when the agent's ``generate_design`` tool succeeds inside a chat
  turn.
- Persisted directly by the initial-draft path in
  ``api/v1/endpoints/uploads.py`` (``_persist_initial_draft``) when a
  user uploads an existing design spreadsheet.

Either way it stores the full design output (JSONB), factor specs,
and user-entered results so experiments survive browser sessions and
support incremental results entry.
"""

from __future__ import annotations

import uuid

from sqlalchemy import JSON, DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Experiment(Base):
    """A persisted DOE experiment with design matrix and results."""

    __tablename__ = "experiments"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(
        String(255),
        default="Untitled Experiment",
        server_default="Untitled Experiment",
    )
    status: Mapped[str] = mapped_column(
        String(20),
        default="draft",
        server_default="draft",
    )
    design_type: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # Factor specifications, stored as a JSON array of per-factor dicts,
    # e.g. ``[{"name": "temperature", "type": "continuous", "low": 20,
    # "high": 60, "units": "C"}, ...]``. Both write paths
    # (``experiment_service._create_experiment_from_design`` and
    # ``uploads._persist_initial_draft``) assign a Python ``list``
    # here; the ``dict`` annotation predates the shape decision and
    # is a known mismatch, kept as-is to avoid a schema-touching
    # change on a docstring-only pass.
    factors: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # Full generate_design tool output (design_coded, design_actual, run_order, etc.)
    design_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # User-entered results: [{run_index: 0, response_name: value}, ...]
    results_data: Mapped[list | None] = mapped_column(JSON, nullable=True)

    # Output of the most recent evaluate_design call (aliasing, resolution,
    # efficiency, VIF, condition number, prediction-variance map, power).
    evaluation_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # Link to originating conversation (SET NULL on conversation delete)
    conversation_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("conversations.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Timestamps
    created_at: Mapped[str] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    updated_at: Mapped[str] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    # Relationships
    conversation = relationship("Conversation")
