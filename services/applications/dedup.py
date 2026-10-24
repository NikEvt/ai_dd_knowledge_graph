"""У клиента по одной сфере остаётся одна заявка — та, что первой дошла до записи."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from libs import clock, events
from libs.bpm import engine as bpm
from services.applications.models import Application

OPEN_STAGES = (
    "draft",
    "on_review",
    "needs_rework",
    "awaiting_invoice",
    "awaiting_payment",
    "awaiting_issue",
    "archived",
)


def _same_track(a: Application, b: Application) -> bool:
    return (a.kind == "social") == (b.kind == "social")


async def close_duplicates(session: AsyncSession, winner: Application) -> list[int]:
    others = (
        await session.scalars(
            select(Application).where(
                Application.client_id == winner.client_id,
                Application.sphere_id == winner.sphere_id,
                Application.id != winner.id,
                Application.stage.in_(OPEN_STAGES),
            )
        )
    ).all()
    closed: list[int] = []
    for other in others:
        if not _same_track(winner, other):
            continue
        await bpm.transition(session, other, "closed_duplicate", actor="system")
        attempt = other.attempts[-1]
        if attempt.ended_at is None:
            attempt.ended_at = clock.now()
            attempt.outcome = "duplicate"
        events.publish(
            session,
            "application.closed_duplicate",
            {"application_id": other.id, "winner_id": winner.id},
        )
        closed.append(other.id)
    return closed
