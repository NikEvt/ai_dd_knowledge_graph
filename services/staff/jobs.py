from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from libs import events
from services.staff.models import Clearance, Shift


async def expire_clearances(session: AsyncSession, now: datetime) -> list[int]:
    clearances = (
        await session.scalars(
            select(Clearance).where(Clearance.status == "active", Clearance.expires_at <= now)
        )
    ).all()
    for clearance in clearances:
        clearance.status = "expired"
        events.publish(
            session,
            "staff.clearance_expired",
            {"clearance_id": clearance.id, "employee_id": clearance.employee_id, "kind": clearance.kind},
        )
    return [c.id for c in clearances]


async def close_finished_shifts(session: AsyncSession, now: datetime) -> list[int]:
    shifts = (
        await session.scalars(select(Shift).where(Shift.status == "planned", Shift.ends_at <= now))
    ).all()
    for shift in shifts:
        shift.status = "done"
    return [s.id for s in shifts]
