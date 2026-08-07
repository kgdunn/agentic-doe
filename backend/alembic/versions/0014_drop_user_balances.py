"""Drop user_balances (the prepaid balance ledger)

Revision ID: 0014
Revises: 0013
Create Date: 2026-08-07

Removes the prepaid dollar + token balance ledger created in 0007. Per-user
cost metering was built before there were users to meter, and the balance was
never charged against: nothing decremented it, only the admin top-up endpoint
credited it.

Note what is deliberately **kept**: the per-message cost columns on
``messages`` (``input_cost_usd``, ``output_cost_usd``, ``markup_rate``,
``markup_cost_usd`` and the rate snapshots) and the ``pricing`` service that
fills them. Those are telemetry, not billing. They cost nothing to carry and
they answer "what is the agent actually spending per turn", which is a
question worth being able to answer whether or not anyone is billed for it.

**Contract-destructive**: dropping a table is not blue-green safe, because the
old colour still has a mapped ORM class pointing at it and ``/auth/me`` still
selects from it. Ship it in the same stop-the-world window as 0012 and 0013.

The downgrade recreates the table exactly as 0007 did, but not the balances.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0014"
down_revision: str | None = "0013"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_table("user_balances")


def downgrade() -> None:
    # Mirrors the table as 0007 created it, column for column.
    op.create_table(
        "user_balances",
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "balance_usd",
            sa.Numeric(12, 4),
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "balance_tokens",
            sa.BigInteger(),
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
