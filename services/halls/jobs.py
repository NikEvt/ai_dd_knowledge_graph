from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from services.halls import service, settings
from services.halls.models import HallBooking


async def cancel_unpaid(session: AsyncSession, now: datetime) -> list[int]:
    """Отменяет брони, по которым так и не внесли предоплату."""
    bookings = (
        await session.scalars(
            select(HallBooking)
            .where(
                HallBooking.status == "draft",
                HallBooking.created_at <= now - timedelta(days=settings.UNPAID_CANCEL_DAYS),
            )
            .order_by(HallBooking.id)
            .with_for_update(skip_locked=True)
        )
    ).all()
    for booking in bookings:
        await service.cancel_unpaid(session, booking, now)
    return [b.id for b in bookings]


async def close_past_events(session: AsyncSession, now: datetime) -> list[int]:
    """Подтверждённые брони, чьё мероприятие закончилось, переводятся в «проведено»."""
    bookings = (
        await session.scalars(
            select(HallBooking)
            .where(HallBooking.status == "confirmed", HallBooking.ends_at <= now)
            .order_by(HallBooking.id)
        )
    ).all()
    for booking in bookings:
        await service.mark_held(session, booking)
    return [b.id for b in bookings]
