"""Admin user-management schemas."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from ipaddress import IPv4Address, IPv6Address

from pydantic import BaseModel, Field, field_validator

from app.schemas.signup import RoleSummary


class AdminUserDetail(BaseModel):
    id: uuid.UUID
    email: str
    display_name: str | None
    is_admin: bool
    is_active: bool
    role: RoleSummary | None = None
    created_at: datetime

    # Sign-in activity + geo (populated once the user has logged in since
    # the activity-tracking rollout; NULL for accounts that never have).
    last_login_at: datetime | None = None
    last_login_ip: str | None = None
    country: str | None = None
    timezone: str | None = None

    # Lifetime LLM spend + usage (zero when the user has no conversations).
    total_cost_usd: Decimal = Decimal("0")
    total_markup_cost_usd: Decimal = Decimal("0")
    total_tokens: int = 0
    conversation_count: int = 0
    last_conversation_at: datetime | None = None

    feedback_count: int = 0
    open_experiments: int = 0
    avg_runs_per_experiment: float | None = None

    # Lifecycle signal from the signup flow ("pending" / "approved" /
    # "registered" / "rejected"). None when no signup request exists.
    signup_status: str | None = None
    disclaimers_accepted: bool | None = None

    model_config = {"from_attributes": True}

    @field_validator("last_login_ip", mode="before")
    @classmethod
    def _ip_to_str(cls, v: object) -> object:
        # Postgres `INET` columns deserialise as ipaddress.IPv4Address /
        # IPv6Address; normalise to canonical text so the field stays a JSON
        # string. SQLite tests already see plain strings, so this is a no-op
        # there.
        if isinstance(v, (IPv4Address, IPv6Address)):
            return str(v)
        return v


class AdminUserListResponse(BaseModel):
    users: list[AdminUserDetail]
    total: int
    page: int
    page_size: int


class AdminUserUpdateRequest(BaseModel):
    """Partial update for a user. Null means 'leave unchanged'."""

    is_admin: bool | None = None
    is_active: bool | None = None
    role_id: uuid.UUID | None = None
    clear_role: bool = False
    display_name: str | None = Field(None, max_length=100)


class AdminUserResetPasswordResponse(BaseModel):
    """Returned to admins after issuing a reset link for a user.

    ``url`` is included so an admin can copy-paste the link out-of-band
    (e.g. when SMTP is intentionally unconfigured in development).
    """

    message: str
    url: str
