"""Открытые лекции на площадках: объявление, регистрация слушателей, лист ожидания."""

from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from libs import clock, events
from libs.errors import AccessDenied, DomainError, NotFound
from services.lectures import settings
from services.lectures.models import Lecture, Notification, Registration, VenueCapacityLimit, WaitlistEntry

# Причины отмены, после которых место на том же мероприятии снова свободно.
SEAT_RELEASING_REASONS = ("listener", "organizer")


async def _lecture(session: AsyncSession, event_id: int, *, lock: bool = False) -> Lecture:
    stmt = select(Lecture).where(Lecture.id == event_id)
    if lock:
        stmt = stmt.with_for_update()
    lecture = await session.scalar(stmt)
    if lecture is None:
        raise NotFound(f"мероприятие {event_id}")
    return lecture


async def _own_lecture(session: AsyncSession, event_id: int, organizer_id: int) -> Lecture:
    lecture = await _lecture(session, event_id, lock=True)
    if lecture.organizer_id != organizer_id:
        raise AccessDenied("мероприятием управляет только его организатор")
    if lecture.status != "scheduled":
        raise DomainError("мероприятие уже отменено или прошло")
    return lecture


async def _venue_limit(session: AsyncSession, venue_id: int) -> int:
    limit = await session.get(VenueCapacityLimit, venue_id)
    if limit is None:
        raise DomainError("для площадки не задан лимит мест")
    return limit.max_capacity


async def confirmed_count(session: AsyncSession, event_id: int) -> int:
    return await session.scalar(
        select(func.count()).where(Registration.event_id == event_id, Registration.status == "confirmed")
    )


def _registration_open(lecture: Lecture, now: datetime) -> bool:
    return lecture.status == "scheduled" and lecture.starts_at - now > settings.REGISTRATION_CLOSES_BEFORE


async def notify(
    session: AsyncSession, *, listener_id: int, event_id: int, kind: str, body: str, dedup_key: str
) -> None:
    """Ставит уведомление слушателю; повторная доставка события не создаёт дубль."""
    await session.execute(
        insert(Notification)
        .values(
            listener_id=listener_id,
            event_id=event_id,
            kind=kind,
            body=body,
            dedup_key=dedup_key,
            created_at=clock.now(),
        )
        .on_conflict_do_nothing(index_elements=["dedup_key"])
    )


# --- площадки ---


async def set_venue_capacity_limit(session: AsyncSession, venue_id: int, max_capacity: int) -> None:
    if max_capacity <= 0:
        raise DomainError("лимит мест площадки должен быть положительным")
    events.publish(
        session, "lectures.venue_limit_changed", {"venue_id": venue_id, "max_capacity": max_capacity}
    )


async def apply_venue_limit(session: AsyncSession, venue_id: int, max_capacity: int) -> list[int]:
    """Обновляет реплику лимита и подтягивает к нему места будущих мероприятий.

    Меняются только мероприятия, где число мест совпадало со старым лимитом и не задавалось
    организатором вручную. Возвращает id изменённых мероприятий.
    """
    now = clock.now()
    replica = await session.get(VenueCapacityLimit, venue_id, with_for_update=True)
    if replica is None:
        session.add(VenueCapacityLimit(venue_id=venue_id, max_capacity=max_capacity, updated_at=now))
        return []
    old = replica.max_capacity
    if old == max_capacity:
        return []
    replica.max_capacity = max_capacity
    replica.updated_at = now
    await session.flush()

    lectures = (
        await session.scalars(
            select(Lecture)
            .where(
                Lecture.venue_id == venue_id,
                Lecture.status == "scheduled",
                Lecture.starts_at > now,
                Lecture.capacity == old,
                Lecture.capacity_manual.is_(False),
            )
            .with_for_update()
        )
    ).all()
    for lecture in lectures:
        lecture.capacity = max_capacity
        lecture.updated_at = now
        if max_capacity > old:
            events.publish(session, "lectures.capacity_increased", {"event_id": lecture.id})
    await session.flush()
    return [lecture.id for lecture in lectures]


# --- мероприятия ---


async def create_event(
    session: AsyncSession,
    *,
    organizer_id: int,
    title: str,
    venue_id: int,
    starts_at: datetime,
    capacity: int | None = None,
) -> Lecture:
    now = clock.now()
    if starts_at - now < settings.MIN_LEAD_TIME:
        raise DomainError("мероприятие нужно объявить хотя бы за сутки до начала")
    if not title.strip():
        raise DomainError("укажите тему мероприятия")
    limit = await _venue_limit(session, venue_id)
    if capacity is None:
        capacity = limit
    busy = await session.scalar(
        select(Lecture.id).where(
            Lecture.venue_id == venue_id, Lecture.starts_at == starts_at, Lecture.status == "scheduled"
        )
    )
    if busy is not None:
        raise DomainError("площадка в это время уже занята другим мероприятием")
    lecture = Lecture(
        title=title.strip(),
        venue_id=venue_id,
        organizer_id=organizer_id,
        starts_at=starts_at,
        capacity=capacity,
        capacity_manual=capacity < limit,
        created_at=now,
        updated_at=now,
    )
    session.add(lecture)
    await session.flush()
    return lecture


async def change_capacity(session: AsyncSession, event_id: int, organizer_id: int, capacity: int) -> Lecture:
    lecture = await _own_lecture(session, event_id, organizer_id)
    if capacity < await confirmed_count(session, event_id):
        raise DomainError("на мероприятие уже зарегистрировано больше слушателей")
    limit = await _venue_limit(session, lecture.venue_id)
    increased = capacity > lecture.capacity
    lecture.capacity = capacity
    lecture.capacity_manual = capacity < limit
    lecture.updated_at = clock.now()
    await session.flush()
    if increased:
        events.publish(session, "lectures.capacity_increased", {"event_id": lecture.id})
    return lecture


async def _drop_audience(session: AsyncSession, lecture: Lecture, reason: str) -> list[int]:
    """Отменяет все регистрации и закрывает лист ожидания; возвращает слушателей из листа."""
    now = clock.now()
    registrations = (
        await session.scalars(
            select(Registration)
            .where(Registration.event_id == lecture.id, Registration.status == "confirmed")
            .order_by(Registration.id)
        )
    ).all()
    for r in registrations:
        _cancel(session, r, lecture, reason, now)
    waiting = await _waiting(session, lecture.id)
    for entry in waiting:
        entry.status = "cancelled"
        entry.closed_at = now
    return [entry.listener_id for entry in waiting]


async def move_event(
    session: AsyncSession, event_id: int, organizer_id: int, *, venue_id: int, capacity: int | None = None
) -> Lecture:
    """Перенос на другую площадку: прежние регистрации и лист ожидания аннулируются."""
    lecture = await _own_lecture(session, event_id, organizer_id)
    if venue_id == lecture.venue_id:
        raise DomainError("мероприятие уже проходит на этой площадке")
    limit = await _venue_limit(session, venue_id)
    busy = await session.scalar(
        select(Lecture.id).where(
            Lecture.venue_id == venue_id,
            Lecture.starts_at == lecture.starts_at,
            Lecture.status == "scheduled",
        )
    )
    if busy is not None:
        raise DomainError("новая площадка в это время уже занята другим мероприятием")

    old_venue_id = lecture.venue_id
    waitlisted = await _drop_audience(session, lecture, "venue_changed")
    lecture.venue_id = venue_id
    lecture.capacity = limit if capacity is None else capacity
    lecture.capacity_manual = lecture.capacity < limit
    lecture.updated_at = clock.now()
    await session.flush()
    events.publish(
        session,
        "lectures.event_moved",
        {
            "event_id": lecture.id,
            "old_venue_id": old_venue_id,
            "venue_id": venue_id,
            "waitlisted": waitlisted,
        },
    )
    return lecture


async def cancel_event(session: AsyncSession, event_id: int, organizer_id: int) -> Lecture:
    lecture = await _own_lecture(session, event_id, organizer_id)
    waitlisted = await _drop_audience(session, lecture, "event_cancelled")
    lecture.status = "cancelled"
    lecture.updated_at = clock.now()
    events.publish(session, "lectures.event_cancelled", {"event_id": lecture.id, "waitlisted": waitlisted})
    return lecture


async def upcoming(session: AsyncSession, venue_id: int | None = None) -> list[tuple[Lecture, int]]:
    """Будущие мероприятия с числом свободных мест."""
    taken = (
        select(Registration.event_id, func.count().label("n"))
        .where(Registration.status == "confirmed")
        .group_by(Registration.event_id)
        .subquery()
    )
    stmt = (
        select(Lecture, Lecture.capacity - func.coalesce(taken.c.n, 0))
        .outerjoin(taken, taken.c.event_id == Lecture.id)
        .where(Lecture.status == "scheduled", Lecture.starts_at > clock.now())
        .order_by(Lecture.starts_at, Lecture.id)
    )
    if venue_id is not None:
        stmt = stmt.where(Lecture.venue_id == venue_id)
    return [(lecture, max(free, 0)) for lecture, free in (await session.execute(stmt)).all()]


# --- регистрации ---


async def _active_registrations(session: AsyncSession, listener_id: int) -> int:
    return await session.scalar(
        select(func.count())
        .select_from(Registration)
        .join(Lecture, Lecture.id == Registration.event_id)
        .where(
            Registration.listener_id == listener_id,
            Registration.status == "confirmed",
            Lecture.status == "scheduled",
            Lecture.starts_at > clock.now(),
        )
    )


async def _registered(session: AsyncSession, event_id: int, listener_id: int) -> Registration | None:
    return await session.scalar(
        select(Registration).where(
            Registration.event_id == event_id,
            Registration.listener_id == listener_id,
            Registration.status == "confirmed",
        )
    )


async def register(session: AsyncSession, event_id: int, listener_id: int) -> Registration:
    lecture = await _lecture(session, event_id, lock=True)
    if not _registration_open(lecture, clock.now()):
        raise DomainError("регистрация на мероприятие закрыта")
    if await _registered(session, event_id, listener_id) is not None:
        raise DomainError("слушатель уже зарегистрирован на это мероприятие")
    if await _active_registrations(session, listener_id) >= settings.MAX_ACTIVE_REGISTRATIONS:
        raise DomainError("у слушателя уже максимальное число регистраций на будущие мероприятия")
    if await confirmed_count(session, event_id) >= lecture.capacity:
        raise DomainError("свободных мест нет, можно встать в лист ожидания")

    registration = Registration(
        event_id=event_id, listener_id=listener_id, status="confirmed", created_at=clock.now()
    )
    session.add(registration)
    entry = await _waiting_entry(session, event_id, listener_id)
    if entry is not None:
        entry.status = "left"
        entry.closed_at = clock.now()
    await session.flush()
    events.publish(
        session,
        "lectures.registration_created",
        {"registration_id": registration.id, "event_id": event_id, "listener_id": listener_id},
    )
    return registration


def _cancel(session: AsyncSession, r: Registration, lecture: Lecture, reason: str, now: datetime) -> None:
    r.status = "cancelled"
    r.cancelled_at = now
    r.cancel_reason = reason
    events.publish(
        session,
        "lectures.registration_cancelled",
        {
            "registration_id": r.id,
            "event_id": lecture.id,
            "venue_id": lecture.venue_id,
            "listener_id": r.listener_id,
            "reason": reason,
        },
    )


async def cancel_registration(session: AsyncSession, registration_id: int, listener_id: int) -> Registration:
    r = await session.get(Registration, registration_id)
    if r is None:
        raise NotFound(f"регистрация {registration_id}")
    if r.listener_id != listener_id:
        raise AccessDenied("отменить регистрацию может только сам слушатель")
    if r.status != "confirmed":
        raise DomainError("регистрация уже отменена")
    lecture = await _lecture(session, r.event_id)
    now = clock.now()
    if lecture.starts_at <= now:
        raise DomainError("мероприятие уже началось")
    _cancel(session, r, lecture, "listener", now)
    return r


async def remove_listener(session: AsyncSession, registration_id: int, organizer_id: int) -> Registration:
    r = await session.get(Registration, registration_id)
    if r is None or r.status != "confirmed":
        raise DomainError("регистрация не действует")
    lecture = await _own_lecture(session, r.event_id, organizer_id)
    _cancel(session, r, lecture, "organizer", clock.now())
    return r


# --- лист ожидания ---


async def _waiting(session: AsyncSession, event_id: int, limit: int | None = None) -> list[WaitlistEntry]:
    stmt = (
        select(WaitlistEntry)
        .where(WaitlistEntry.event_id == event_id, WaitlistEntry.status == "waiting")
        .order_by(WaitlistEntry.created_at, WaitlistEntry.id)
        .with_for_update(skip_locked=True)
    )
    if limit is not None:
        stmt = stmt.limit(limit)
    return list((await session.scalars(stmt)).all())


async def _waiting_entry(session: AsyncSession, event_id: int, listener_id: int) -> WaitlistEntry | None:
    return await session.scalar(
        select(WaitlistEntry).where(
            WaitlistEntry.event_id == event_id,
            WaitlistEntry.listener_id == listener_id,
            WaitlistEntry.status == "waiting",
        )
    )


async def join_waitlist(session: AsyncSession, event_id: int, listener_id: int) -> WaitlistEntry:
    lecture = await _lecture(session, event_id, lock=True)
    if not _registration_open(lecture, clock.now()):
        raise DomainError("регистрация на мероприятие закрыта")
    if await _registered(session, event_id, listener_id) is not None:
        raise DomainError("слушатель уже зарегистрирован на это мероприятие")
    if await confirmed_count(session, event_id) < lecture.capacity:
        raise DomainError("на мероприятии есть свободные места, регистрируйтесь напрямую")
    if await _waiting_entry(session, event_id, listener_id) is not None:
        raise DomainError("слушатель уже в листе ожидания")
    queued = await session.scalar(
        select(func.count()).where(WaitlistEntry.event_id == event_id, WaitlistEntry.status == "waiting")
    )
    if queued >= settings.WAITLIST_MAX_SIZE:
        raise DomainError("лист ожидания заполнен")
    entry = WaitlistEntry(event_id=event_id, listener_id=listener_id, created_at=clock.now())
    session.add(entry)
    await session.flush()
    return entry


async def leave_waitlist(session: AsyncSession, entry_id: int, listener_id: int) -> WaitlistEntry:
    entry = await session.get(WaitlistEntry, entry_id)
    if entry is None:
        raise NotFound(f"запись листа ожидания {entry_id}")
    if entry.listener_id != listener_id:
        raise AccessDenied("покинуть лист ожидания может только сам слушатель")
    if entry.status != "waiting":
        raise DomainError("запись в листе ожидания уже закрыта")
    entry.status = "left"
    entry.closed_at = clock.now()
    return entry


async def waitlist_position(session: AsyncSession, entry_id: int) -> int:
    entry = await session.get(WaitlistEntry, entry_id)
    if entry is None or entry.status != "waiting":
        raise NotFound(f"запись листа ожидания {entry_id}")
    ahead = await session.scalar(
        select(func.count()).where(
            WaitlistEntry.event_id == entry.event_id,
            WaitlistEntry.status == "waiting",
            (WaitlistEntry.created_at < entry.created_at)
            | ((WaitlistEntry.created_at == entry.created_at) & (WaitlistEntry.id < entry.id)),
        )
    )
    return ahead + 1


async def fill_from_waitlist(session: AsyncSession, event_id: int) -> list[Registration]:
    """Отдаёт свободные места первым из листа ожидания."""
    lecture = await _lecture(session, event_id, lock=True)
    now = clock.now()
    if not _registration_open(lecture, now):
        return []
    free = lecture.capacity - await confirmed_count(session, event_id)
    if free <= 0:
        return []
    promoted = []
    for entry in await _waiting(session, event_id, limit=free):
        entry.status = "promoted"
        entry.closed_at = now
        registration = Registration(
            event_id=event_id,
            listener_id=entry.listener_id,
            status="confirmed",
            source="waitlist",
            created_at=now,
        )
        session.add(registration)
        await session.flush()
        events.publish(
            session,
            "lectures.waitlist_promoted",
            {
                "registration_id": registration.id,
                "waitlist_id": entry.id,
                "event_id": event_id,
                "listener_id": entry.listener_id,
            },
        )
        promoted.append(registration)
    return promoted


# --- уведомления ---


async def notifications(session: AsyncSession, listener_id: int) -> list[Notification]:
    rows = await session.scalars(
        select(Notification)
        .where(Notification.listener_id == listener_id)
        .order_by(Notification.created_at, Notification.id)
    )
    return list(rows.all())
