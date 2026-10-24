"""Расписание площадок, запись на визит, выдача и возврат книг."""

import secrets
from datetime import datetime, timedelta

from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from libs import clock, events, settings
from libs.errors import AccessDenied, DomainError, NotFound
from services.applications import public as applications
from services.scheduling.models import Booking, BookingLink, Hold, Loan, Slot, VenueLimit

CLIENT_SIDE = ("client", "representative")


async def _require_site_checker(session: AsyncSession, venue_id: int, site_checker_id: int) -> None:
    venue = await applications.get_venue(session, venue_id)
    if venue.site_checker_id != site_checker_id:
        raise AccessDenied("проверяющий оператор работает только со своей площадкой")


async def create_slot(
    session: AsyncSession,
    *,
    site_checker_id: int,
    venue_id: int,
    sphere_id: int,
    starts_at: datetime,
    capacity: int | None = None,
) -> Slot:
    await _require_site_checker(session, venue_id, site_checker_id)
    if starts_at <= clock.now():
        raise DomainError("нельзя создать окно на прошедшее время")
    if capacity is None:
        limit = await session.get(VenueLimit, venue_id)
        if limit is None:
            raise DomainError("для площадки не задан максимум мест")
        capacity = limit.max_capacity
    slot = Slot(venue_id=venue_id, sphere_id=sphere_id, starts_at=starts_at, capacity=capacity)
    session.add(slot)
    await session.flush()
    return slot


async def _active_bookings(session: AsyncSession, slot_id: int) -> int:
    return await session.scalar(
        select(func.count()).where(Booking.slot_id == slot_id, Booking.status == "active")
    )


async def reduce_capacity(session: AsyncSession, slot_id: int, site_checker_id: int, capacity: int) -> Slot:
    slot = await session.get(Slot, slot_id)
    if slot is None:
        raise NotFound(f"окно {slot_id}")
    await _require_site_checker(session, slot.venue_id, site_checker_id)
    if capacity >= slot.capacity:
        raise DomainError("проверяющий оператор может только уменьшить число мест")
    if capacity < await _active_bookings(session, slot_id):
        raise DomainError("в окне уже записано больше клиентов")
    slot.capacity = capacity
    await session.flush()
    return slot


async def remove_slot(session: AsyncSession, slot_id: int, site_checker_id: int) -> None:
    slot = await session.get(Slot, slot_id)
    if slot is None:
        raise NotFound(f"окно {slot_id}")
    await _require_site_checker(session, slot.venue_id, site_checker_id)
    bookings = (
        await session.scalars(select(Booking).where(Booking.slot_id == slot_id, Booking.status == "active"))
    ).all()
    for b in bookings:
        await _cancel(session, b, slot, reason="slot_removed")
    slot.removed = True


async def issue_link(session: AsyncSession, application_id: int, purpose: str) -> BookingLink:
    await session.execute(
        update(BookingLink).where(BookingLink.application_id == application_id).values(active=False)
    )
    link = BookingLink(application_id=application_id, token=secrets.token_urlsafe(16), purpose=purpose)
    session.add(link)
    await session.flush()
    return link


async def active_link(session: AsyncSession, application_id: int) -> BookingLink | None:
    return await session.scalar(
        select(BookingLink).where(BookingLink.application_id == application_id, BookingLink.active.is_(True))
    )


async def _link_by_token(session: AsyncSession, token: str) -> BookingLink:
    link = await session.scalar(select(BookingLink).where(BookingLink.token == token))
    if link is None or not link.active:
        raise DomainError("ссылка на запись не действует")
    return link


async def free_slots(session: AsyncSession, token: str) -> list[Slot]:
    link = await _link_by_token(session, token)
    brief = await applications.get_brief(session, link.application_id)
    taken = (
        select(Booking.slot_id, func.count().label("n"))
        .where(Booking.status == "active")
        .group_by(Booking.slot_id)
        .subquery()
    )
    rows = await session.scalars(
        select(Slot)
        .outerjoin(taken, taken.c.slot_id == Slot.id)
        .where(
            Slot.venue_id == brief.venue_id,
            Slot.sphere_id == brief.sphere_id,
            Slot.removed.is_(False),
            Slot.starts_at > clock.now(),
            func.coalesce(taken.c.n, 0) < Slot.capacity,
        )
        .order_by(Slot.starts_at)
    )
    return list(rows.all())


async def book(session: AsyncSession, *, token: str, slot_id: int, booked_by: str) -> Booking:
    link = await _link_by_token(session, token)
    brief = await applications.get_brief(session, link.application_id)
    slot = await session.get(Slot, slot_id)
    if slot is None or slot.removed:
        raise NotFound(f"окно {slot_id}")
    if slot.venue_id != brief.venue_id or slot.sphere_id != brief.sphere_id:
        raise DomainError("окно не на площадке или не в сфере заявки")
    if slot.starts_at <= clock.now():
        raise DomainError("нельзя записаться на прошедшее время")
    if await _active_bookings(session, slot_id) >= slot.capacity:
        raise DomainError("в окне нет свободных мест")

    booking = Booking(
        application_id=brief.id,
        slot_id=slot_id,
        purpose=link.purpose,
        status="active",
        booked_by=booked_by,
        created_at=clock.now(),
    )
    session.add(booking)
    if link.purpose == "issue":
        for book_id in brief.book_ids:
            await session.merge(Hold(application_id=brief.id, book_id=book_id))
    await session.flush()
    events.publish(
        session,
        "booking.created",
        {
            "application_id": brief.id,
            "booking_id": booking.id,
            "venue_id": slot.venue_id,
            "starts_at": slot.starts_at.isoformat(),
            "purpose": link.purpose,
        },
    )
    return booking


async def book_by_operator(
    session: AsyncSession, application_id: int, slot_id: int, operator_id: int
) -> Booking:
    brief = await applications.get_brief(session, application_id)
    if brief.operator_id != operator_id:
        raise AccessDenied("заявка закреплена за другим оператором")
    link = await active_link(session, application_id)
    if link is None:
        raise DomainError("по заявке нет действующей ссылки на запись")
    return await book(session, token=link.token, slot_id=slot_id, booked_by="operator")


async def _cancel(session: AsyncSession, booking: Booking, slot: Slot, reason: str) -> None:
    booking.status = "no_show" if reason == "no_show" else "cancelled"
    events.publish(
        session,
        "booking.cancelled",
        {
            "application_id": booking.application_id,
            "booking_id": booking.id,
            "venue_id": slot.venue_id,
            "starts_at": slot.starts_at.isoformat(),
            "reason": reason,
        },
    )


async def cancel_booking(session: AsyncSession, booking_id: int, *, by: str) -> Booking:
    booking = await session.get(Booking, booking_id)
    if booking is None or booking.status != "active":
        raise DomainError("запись не действует")
    slot = await session.get(Slot, booking.slot_id)
    if by in CLIENT_SIDE and slot.starts_at - clock.now() < timedelta(
        days=settings.CLIENT_RESCHEDULE_MIN_DAYS
    ):
        raise DomainError("менее чем за два дня перенести или отменить визит может только оператор")
    await _cancel(session, booking, slot, reason="cancelled")
    return booking


async def reschedule(session: AsyncSession, booking_id: int, new_slot_id: int, *, by: str) -> Booking:
    booking = await cancel_booking(session, booking_id, by=by)
    await session.flush()
    link = await active_link(session, booking.application_id)
    return await book(session, token=link.token, slot_id=new_slot_id, booked_by=by)


async def mark_no_show(session: AsyncSession, booking_id: int, site_checker_id: int) -> Booking:
    booking = await session.get(Booking, booking_id)
    if booking is None or booking.status != "active":
        raise DomainError("запись не действует")
    slot = await session.get(Slot, booking.slot_id)
    await _require_site_checker(session, slot.venue_id, site_checker_id)
    await _cancel(session, booking, slot, reason="no_show")
    return booking


async def issue_books(session: AsyncSession, booking_id: int, site_checker_id: int) -> list[Loan]:
    booking = await session.get(Booking, booking_id)
    if booking is None or booking.status != "active" or booking.purpose != "issue":
        raise DomainError("нет действующей записи за книгами")
    slot = await session.get(Slot, booking.slot_id)
    brief = await applications.get_brief(session, booking.application_id)
    if brief.site_checker_id != site_checker_id:
        raise AccessDenied("книги выдаёт проверяющий оператор площадки заявки")
    if brief.stage != "awaiting_issue":
        raise DomainError("выдача возможна только на этапе «Ожидает выдачи»")
    now = clock.now()
    if slot.starts_at.date() != now.date():
        raise DomainError("выдача только в выбранную дату")

    loans = [
        Loan(
            application_id=brief.id,
            book_id=book_id,
            issued_at=now,
            due_at=now + timedelta(days=settings.LOAN_PERIOD_DAYS),
            status="out",
        )
        for book_id in brief.book_ids
    ]
    session.add_all(loans)
    booking.status = "done"
    await session.execute(delete(Hold).where(Hold.application_id == brief.id))
    await issue_link(session, brief.id, "return")
    events.publish(session, "books.issued", {"application_id": brief.id})
    return loans


async def _loan_for_checker(session: AsyncSession, loan_id: int, site_checker_id: int) -> Loan:
    loan = await session.get(Loan, loan_id)
    if loan is None:
        raise NotFound(f"выдача {loan_id}")
    brief = await applications.get_brief(session, loan.application_id)
    if brief.site_checker_id != site_checker_id:
        raise AccessDenied("книги принимает проверяющий оператор площадки заявки")
    if loan.status != "out":
        raise DomainError("книга уже возвращена или списана")
    return loan


async def return_book(
    session: AsyncSession, loan_id: int, site_checker_id: int, *, damaged: bool = False
) -> Loan:
    loan = await _loan_for_checker(session, loan_id, site_checker_id)
    loan.status = "returned"
    loan.returned_at = clock.now()
    loan.damaged = damaged
    if damaged:
        events.publish(session, "loan.damaged", {"application_id": loan.application_id, "loan_id": loan.id})
    return loan


async def mark_lost(session: AsyncSession, loan_id: int, site_checker_id: int) -> Loan:
    loan = await _loan_for_checker(session, loan_id, site_checker_id)
    loan.status = "lost"
    events.publish(session, "loan.lost", {"application_id": loan.application_id, "loan_id": loan.id})
    return loan


async def reset_bookings(session: AsyncSession, application_id: int, *, reason: str) -> None:
    """Отменяет действующие записи, освобождает книги и гасит ссылку на запись."""
    bookings = (
        await session.scalars(
            select(Booking).where(Booking.application_id == application_id, Booking.status == "active")
        )
    ).all()
    for b in bookings:
        slot = await session.get(Slot, b.slot_id)
        await _cancel(session, b, slot, reason=reason)
    await session.execute(delete(Hold).where(Hold.application_id == application_id))
    await session.execute(
        update(BookingLink).where(BookingLink.application_id == application_id).values(active=False)
    )
