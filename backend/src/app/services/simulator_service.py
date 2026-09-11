"""Service layer for fake-data simulator persistence + reveal policy.

The agent loop in :mod:`app.services.agent_service` uses this module to:

1. Preload existing simulators for a conversation at the start of a turn,
   so their hidden ``private_state`` can be injected into
   ``simulate_process`` / ``reveal_simulator`` tool calls without
   another DB round-trip mid-loop.
2. Persist any simulators created during the turn at its end.
3. Bump the per-simulator ``reveal_request_count`` to enforce the
   double-confirmation policy across turns (first ask  →  wait for user,
   second ask  →  reveal).

All functions are async and accept an ``AsyncSession``; the caller owns
the transaction boundary.
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.simulator import Simulator


async def list_simulators_for_conversation(
    db: AsyncSession,
    conversation_id: uuid.UUID,
) -> list[Simulator]:
    """Return all simulator rows attached to a conversation (chronological)."""
    result = await db.execute(
        select(Simulator).where(Simulator.conversation_id == conversation_id).order_by(Simulator.created_at.asc()),
    )
    return list(result.scalars().all())


async def get_simulator_by_sim_id(
    db: AsyncSession,
    sim_id: str,
    user_id: uuid.UUID,
) -> Simulator | None:
    """Return the simulator row for *sim_id*, enforcing ownership.

    Ownership is enforced *after* the fetch: the row is loaded by
    ``sim_id`` and only then checked against ``user_id``. A caller
    with a valid ``sim_id`` but the wrong ``user_id`` therefore
    triggers a real database read that returns nothing (``None``),
    not a permission error at query time.
    """
    result = await db.execute(
        select(Simulator).where(Simulator.sim_id == sim_id),
    )
    sim = result.scalar_one_or_none()
    if sim is None or sim.user_id != user_id:
        return None
    return sim


async def create_simulator_record(
    db: AsyncSession,
    *,
    sim_id: str,
    public_summary: dict[str, Any],
    private_state: dict[str, Any],
    user_id: uuid.UUID,
    conversation_id: uuid.UUID | None = None,
) -> Simulator:
    """Insert a new simulator row from a ``create_simulator`` tool output."""
    sim = Simulator(
        sim_id=sim_id,
        user_id=user_id,
        conversation_id=conversation_id,
        public_summary=public_summary,
        private_state=private_state,
        reveal_request_count=0,
    )
    db.add(sim)
    await db.flush()
    return sim


async def set_reveal_request_count(
    db: AsyncSession,
    sim_id: str,
    user_id: uuid.UUID,
    count: int,
) -> Simulator | None:
    """Overwrite the reveal-attempt counter for a simulator.

    Called at the end of a turn with the counter that the in-loop agent
    state tracked across tool calls.
    """
    sim = await get_simulator_by_sim_id(db, sim_id, user_id)
    if sim is None:
        return None
    sim.reveal_request_count = count
    await db.flush()
    return sim
