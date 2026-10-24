from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from libs import events
from libs.events import subscribe
from services.lectures import service
from services.lectures.models import Lecture


def _when(lecture: Lecture) -> str:
    return lecture.starts_at.strftime("%d.%m.%Y %H:%M")


@subscribe("lectures.venue_limit_changed")
async def on_venue_limit_changed(session: AsyncSession, payload: dict[str, Any]) -> None:
    await service.apply_venue_limit(session, payload["venue_id"], payload["max_capacity"])


@subscribe("lectures.capacity_increased")
async def on_capacity_increased(session: AsyncSession, payload: dict[str, Any]) -> None:
    await service.fill_from_waitlist(session, payload["event_id"])


@subscribe("lectures.registration_created")
async def on_registration_created(session: AsyncSession, payload: dict[str, Any]) -> None:
    lecture = await session.get(Lecture, payload["event_id"])
    await service.notify(
        session,
        listener_id=payload["listener_id"],
        event_id=lecture.id,
        kind="registered",
        body=f"Вы зарегистрированы на «{lecture.title}», {_when(lecture)}",
        dedup_key=f"registered:{payload['registration_id']}",
    )


@subscribe("lectures.registration_cancelled")
async def on_registration_cancelled(session: AsyncSession, payload: dict[str, Any]) -> None:
    lecture = await session.get(Lecture, payload["event_id"])
    reason = payload["reason"]
    if reason == "venue_changed":
        kind, body = "event_moved", f"«{lecture.title}» перенесено на другую площадку, регистрация отменена"
    elif reason == "event_cancelled":
        kind, body = "event_cancelled", f"«{lecture.title}» отменено"
    else:
        kind, body = "registration_cancelled", f"Регистрация на «{lecture.title}» отменена"
    await service.notify(
        session,
        listener_id=payload["listener_id"],
        event_id=lecture.id,
        kind=kind,
        body=body,
        dedup_key=f"cancelled:{payload['registration_id']}",
    )
    # Место освобождается только на том же мероприятии и той же площадке.
    if (
        reason in service.SEAT_RELEASING_REASONS
        and lecture.status == "scheduled"
        and lecture.venue_id == payload["venue_id"]
    ):
        events.publish(session, "lectures.seat_released", {"event_id": lecture.id})


@subscribe("lectures.seat_released")
async def on_seat_released(session: AsyncSession, payload: dict[str, Any]) -> None:
    await service.fill_from_waitlist(session, payload["event_id"])


@subscribe("lectures.waitlist_promoted")
async def on_waitlist_promoted(session: AsyncSession, payload: dict[str, Any]) -> None:
    lecture = await session.get(Lecture, payload["event_id"])
    await service.notify(
        session,
        listener_id=payload["listener_id"],
        event_id=lecture.id,
        kind="waitlist_promoted",
        body=f"Освободилось место: вы зарегистрированы на «{lecture.title}», {_when(lecture)}",
        dedup_key=f"promoted:{payload['registration_id']}",
    )


async def _notify_waitlisted(session: AsyncSession, payload: dict[str, Any], kind: str, body: str) -> None:
    for listener_id in payload["waitlisted"]:
        await service.notify(
            session,
            listener_id=listener_id,
            event_id=payload["event_id"],
            kind=kind,
            body=body,
            dedup_key=f"{kind}:waitlist:{payload['event_id']}:{listener_id}",
        )


@subscribe("lectures.event_moved")
async def on_event_moved(session: AsyncSession, payload: dict[str, Any]) -> None:
    lecture = await session.get(Lecture, payload["event_id"])
    await _notify_waitlisted(
        session,
        payload,
        "event_moved",
        f"«{lecture.title}» перенесено на другую площадку, лист ожидания закрыт",
    )


@subscribe("lectures.event_cancelled")
async def on_event_cancelled(session: AsyncSession, payload: dict[str, Any]) -> None:
    lecture = await session.get(Lecture, payload["event_id"])
    await _notify_waitlisted(session, payload, "event_cancelled", f"«{lecture.title}» отменено")


@subscribe("lectures.waitlist_expired")
async def on_waitlist_expired(session: AsyncSession, payload: dict[str, Any]) -> None:
    lecture = await session.get(Lecture, payload["event_id"])
    await service.notify(
        session,
        listener_id=payload["listener_id"],
        event_id=lecture.id,
        kind="waitlist_expired",
        body=f"Место на «{lecture.title}» так и не освободилось",
        dedup_key=f"expired:{payload['waitlist_id']}",
    )
