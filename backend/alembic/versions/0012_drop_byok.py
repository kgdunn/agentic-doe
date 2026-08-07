"""Drop the BYOK schema

Revision ID: 0012
Revises: 0011
Create Date: 2026-08-07

Reverses 0011. Removes the BYOK (Bring-Your-Own Anthropic API key) schema:

- ``users``: the six BYOK columns.
- ``sessions``: the two per-session DEK wrap columns.
- ``messages``: ``byok_used``.
- ``byok_credentials_history``: the audit table, dropped outright.

**This migration is contract-destructive.** Per the expand/contract rule in
CLAUDE.md it is NOT safe under a blue-green cutover: the old colour still
selects ``users.byok_token_status`` and ``messages.byok_used``, and every
query it issues against those columns starts failing the moment this runs.
Deploy it as a single stop-the-world migration, with both colours down.

Doing it safely instead would take two deploys: first ship the code that
stops reading these columns, then drop them once no container is left that
remembers they existed. That sequencing was waived deliberately here, since
there are no production rows to protect and the feature never launched.

The downgrade recreates the columns and the table, but **not the data**. Any
enrolled API key ciphertext is gone for good once this runs, which is the
correct outcome: the point of the change is that the platform should not be
holding user API keys at all.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0012"
down_revision: str | None = "0011"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_index("ix_byok_credentials_history_user_id", table_name="byok_credentials_history")
    op.drop_table("byok_credentials_history")

    op.drop_column("messages", "byok_used")

    op.drop_column("sessions", "byok_dek_session_wrapped")
    op.drop_column("sessions", "byok_session_key_encrypted")

    for column in (
        "byok_token_status",
        "byok_token_last_verified_at",
        "byok_kdf_params",
        "byok_kek_salt",
        "byok_dek_wrapped",
        "byok_token_ciphertext",
    ):
        op.drop_column("users", column)


def downgrade() -> None:
    op.add_column("users", sa.Column("byok_token_ciphertext", sa.LargeBinary(), nullable=True))
    op.add_column("users", sa.Column("byok_dek_wrapped", sa.LargeBinary(), nullable=True))
    op.add_column("users", sa.Column("byok_kek_salt", sa.LargeBinary(), nullable=True))
    op.add_column("users", sa.Column("byok_kdf_params", postgresql.JSONB(), nullable=True))
    op.add_column(
        "users",
        sa.Column("byok_token_last_verified_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "users",
        sa.Column(
            "byok_token_status",
            sa.String(length=20),
            nullable=False,
            server_default="absent",
        ),
    )

    op.add_column("sessions", sa.Column("byok_session_key_encrypted", sa.LargeBinary(), nullable=True))
    op.add_column("sessions", sa.Column("byok_dek_session_wrapped", sa.LargeBinary(), nullable=True))

    op.add_column(
        "messages",
        sa.Column("byok_used", sa.Boolean(), nullable=False, server_default="false"),
    )

    # Mirrors the table as 0011 created it, column for column.
    op.create_table(
        "byok_credentials_history",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("action", sa.String(32), nullable=False),
        sa.Column("status_after", sa.String(20), nullable=False),
        sa.Column("last_verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_byok_credentials_history_user_id",
        "byok_credentials_history",
        ["user_id"],
    )
