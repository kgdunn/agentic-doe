"""Drop tool_usage (the hosted MCP endpoint's CPU budget)

Revision ID: 0013
Revises: 0012
Create Date: 2026-08-07

``tool_usage`` existed to enforce a per-identity daily CPU quota on the hosted
``/mcp`` REST shim. That endpoint is removed in the same change, so the table
has nothing left to account for.

**Contract-destructive**, like 0012: dropping a table is not blue-green safe,
because the old colour still has a mapped ORM class pointing at it. Ship it in
the same stop-the-world window as 0012.

The table was created in 0001 rather than by a later expand, so the downgrade
recreates it exactly as 0001 did, indexes and unique constraint included.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0013"
down_revision: str | None = "0012"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_index("ix_tool_usage_day", table_name="tool_usage")
    op.drop_index("ix_tool_usage_user_id", table_name="tool_usage")
    op.drop_table("tool_usage")


def downgrade() -> None:
    # ``user_id`` is deliberately NOT a foreign key: the synthetic
    # SERVICE_USER_ID (the shared X-API-Key identity) wrote here too.
    op.create_table(
        "tool_usage",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            primary_key=True,
        ),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("day", sa.Date(), nullable=False),
        sa.Column("cpu_seconds_used", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("call_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("user_id", "day", name="uq_tool_usage_user_day"),
    )
    op.create_index("ix_tool_usage_user_id", "tool_usage", ["user_id"])
    op.create_index("ix_tool_usage_day", "tool_usage", ["day"])
