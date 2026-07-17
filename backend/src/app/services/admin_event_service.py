"""Service helpers for the ``admin_events`` operational log.

Four thin helpers the rest of the app (and the backup/restore shell
scripts, via the ``admin-event`` CLI subcommand) call into:

- ``start_event`` — insert an ``in_progress`` row, return its id.
- ``finish_event`` — close that row out as ``success`` or ``failed``,
  merge extra keys into the JSONB payload, and fill in
  ``completed_at`` / ``duration_ms``.
- ``log_snapshot`` — insert a single-row ``info`` event (user counts,
  token usage, etc.).
- ``list_events`` — paginated event list for the admin dashboard,
  filterable by ``event_type`` / ``status``.

Timestamps are Python-side UTC so ``duration_ms`` can be computed
without a round-trip refresh.
"""

from __future__ import annotations

import datetime as dt
import uuid
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.admin_event import AdminEvent

_TERMINAL_STATUSES: frozenset[str] = frozenset({"success", "failed"})


async def start_event(
    db: AsyncSession,
    *,
    event_type: str,
    source: str,
    actor: str | None = None,
    message: str | None = None,
    payload: dict[str, Any] | None = None,
) -> uuid.UUID:
    """Insert an ``in_progress`` row and return its id."""
    event = AdminEvent(
        event_type=event_type,
        status="in_progress",
        source=source,
        actor=actor,
        message=message,
        payload=payload or {},
        started_at=dt.datetime.now(dt.UTC),
    )
    db.add(event)
    await db.flush()
    return event.id


async def finish_event(
    db: AsyncSession,
    event_id: uuid.UUID,
    *,
    status: str,
    message: str | None = None,
    error_message: str | None = None,
    payload_merge: dict[str, Any] | None = None,
) -> None:
    """Close out an ``in_progress`` row.

    ``status`` must be ``"success"`` or ``"failed"``. ``payload_merge``
    is shallow-merged into the existing payload so callers can add
    extra keys (size_bytes, sha256, s3_key, …) without overwriting the
    keys set by ``start_event``.
    """
    if status not in _TERMINAL_STATUSES:
        raise ValueError(f"finish_event status must be one of {sorted(_TERMINAL_STATUSES)}, got {status!r}")

    event = await db.get(AdminEvent, event_id)
    if event is None:
        raise ValueError(f"admin_events id {event_id} not found")

    now = dt.datetime.now(dt.UTC)
    event.status = status
    if message is not None:
        event.message = message
    if error_message is not None:
        event.error_message = error_message
    if payload_merge:
        event.payload = {**(event.payload or {}), **payload_merge}
    event.completed_at = now
    if event.started_at is not None:
        started = event.started_at
        if started.tzinfo is None:
            started = started.replace(tzinfo=dt.UTC)
        event.duration_ms = int((now - started).total_seconds() * 1000)
    await db.flush()


async def list_events(
    db: AsyncSession,
    *,
    page: int = 1,
    page_size: int = 50,
    event_type: str | None = None,
    status: str | None = None,
) -> tuple[list[AdminEvent], int]:
    """Paginated event list for the admin dashboard.

    Filters are ANDed. Ordering is ``created_at DESC`` so the freshest
    rows land on page 1 (hits ``ix_admin_events_created_at`` and its
    per-event-type / per-status composite friends from migration 0002).
    """
    query = select(AdminEvent)
    count_query = select(func.count()).select_from(AdminEvent)

    conditions: list[Any] = []
    if event_type:
        conditions.append(AdminEvent.event_type == event_type)
    if status:
        conditions.append(AdminEvent.status == status)

    if conditions:
        query = query.where(*conditions)
        count_query = count_query.where(*conditions)

    query = query.order_by(AdminEvent.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    events = list(result.scalars().all())

    total = (await db.execute(count_query)).scalar_one()
    return events, total


async def log_snapshot(
    db: AsyncSession,
    *,
    event_type: str,
    source: str,
    payload: dict[str, Any],
    message: str | None = None,
) -> uuid.UUID:
    """Insert a single-row ``info`` event for periodic snapshots."""
    event = AdminEvent(
        event_type=event_type,
        status="info",
        source=source,
        payload=payload,
        message=message,
    )
    db.add(event)
    await db.flush()
    return event.id
