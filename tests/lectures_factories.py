"""Площадки, мероприятия и слушатели для тестов сервиса лекций."""

from datetime import timedelta

from sqlalchemy import select

from libs import db
from services.lectures import service as lectures
from services.lectures.models import Lecture, Notification, Registration, WaitlistEntry
from tests.factories import T0, act, read

HALL, ROOM, LOFT = 1, 2, 3
LIMITS = {HALL: 5, ROOM: 3, LOFT: 10}

ORGANIZER, ORGANIZER_2 = 701, 702
LISTENERS = tuple(range(1001, 1021))
ANNA, BORIS, VERA, GLEB, DINA, EGOR = LISTENERS[:6]

EVENING = T0 + timedelta(days=3, hours=9)


async def venues(limits: dict[int, int] | None = None) -> None:
    for venue_id, cap in (limits or LIMITS).items():
        await set_limit(venue_id, cap)


async def set_limit(venue_id: int, max_capacity: int) -> None:
    await act(lectures.set_venue_capacity_limit, venue_id, max_capacity)


async def new_event(
    *,
    venue: int = HALL,
    starts_at=EVENING,
    capacity: int | None = None,
    organizer: int = ORGANIZER,
    title: str = "Книжная культура Серебряного века",
) -> int:
    lecture = await act(
        lectures.create_event,
        organizer_id=organizer,
        title=title,
        venue_id=venue,
        starts_at=starts_at,
        capacity=capacity,
    )
    return lecture.id


async def register(event_id: int, listener: int) -> int:
    return (await act(lectures.register, event_id, listener)).id


async def fill(event_id: int, listeners: tuple[int, ...]) -> list[int]:
    return [await register(event_id, listener) for listener in listeners]


async def wait(event_id: int, listener: int) -> int:
    return (await act(lectures.join_waitlist, event_id, listener)).id


async def lecture(event_id: int) -> Lecture:
    async with db.sessionmaker()() as s:
        return await s.get(Lecture, event_id)


async def registration(registration_id: int) -> Registration:
    async with db.sessionmaker()() as s:
        return await s.get(Registration, registration_id)


async def waitlist_entry(entry_id: int) -> WaitlistEntry:
    async with db.sessionmaker()() as s:
        return await s.get(WaitlistEntry, entry_id)


async def attendees(event_id: int) -> list[int]:
    async with db.sessionmaker()() as s:
        rows = await s.scalars(
            select(Registration.listener_id)
            .where(Registration.event_id == event_id, Registration.status == "confirmed")
            .order_by(Registration.id)
        )
        return list(rows.all())


async def notices(listener: int) -> list[Notification]:
    return await read(lectures.notifications, listener)


async def kinds(listener: int) -> list[str]:
    return [n.kind for n in await notices(listener)]
