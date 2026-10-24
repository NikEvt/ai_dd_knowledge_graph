from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from libs import events
from services.lectures import service, settings
from services.lectures.models import Lecture, Registration, WaitlistEntry


async def close_waitlists(session: AsyncSession, now: datetime) -> list[int]:
    """Когда регистрация закрылась, ждать места больше бессмысленно: лист ожидания истекает."""
    entries = (
        await session.scalars(
            select(WaitlistEntry)
            .join(Lecture, Lecture.id == WaitlistEntry.event_id)
            .where(
                WaitlistEntry.status == "waiting",
                Lecture.starts_at <= now + settings.REGISTRATION_CLOSES_BEFORE,
            )
            .order_by(WaitlistEntry.id)
            .with_for_update(of=WaitlistEntry, skip_locked=True)
        )
    ).all()
    for entry in entries:
        entry.status = "expired"
        entry.closed_at = now
        events.publish(
            session,
            "lectures.waitlist_expired",
            {"waitlist_id": entry.id, "event_id": entry.event_id, "listener_id": entry.listener_id},
        )
    return [entry.id for entry in entries]


async def send_reminders(session: AsyncSession, now: datetime) -> int:
    rows = (
        await session.execute(
            select(Registration, Lecture)
            .join(Lecture, Lecture.id == Registration.event_id)
            .where(
                Registration.status == "confirmed",
                Lecture.status == "scheduled",
                Lecture.starts_at > now,
                Lecture.starts_at <= now + settings.REMINDER_AHEAD,
            )
            .order_by(Registration.id)
        )
    ).all()
    for registration, lecture in rows:
        await service.notify(
            session,
            listener_id=registration.listener_id,
            event_id=lecture.id,
            kind="reminder",
            body=f"Напоминаем: «{lecture.title}» начнётся {lecture.starts_at:%d.%m.%Y в %H:%M}",
            dedup_key=f"reminder:{registration.id}",
        )
    return len(rows)


async def finish_past_events(session: AsyncSession, now: datetime) -> list[int]:
    lectures = (
        await session.scalars(
            select(Lecture).where(
                Lecture.status == "scheduled", Lecture.starts_at <= now - settings.FINISH_AFTER
            )
        )
    ).all()
    for lecture in lectures:
        lecture.status = "finished"
        lecture.updated_at = now
    return [lecture.id for lecture in lectures]
