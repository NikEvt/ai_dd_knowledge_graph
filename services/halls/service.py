"""Залы площадок, бронирование под мероприятия, счета и оплата аренды."""

from datetime import datetime, timedelta
from decimal import Decimal
from string import Template as Text
from typing import Any

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from libs import clock, events
from libs.errors import AccessDenied, DomainError, NotFound
from services.halls import settings
from services.halls.models import (
    Hall,
    HallBooking,
    HallEmail,
    HallInvoice,
    HallManager,
    HallPayment,
    HallTemplate,
)

CENT = Decimal("0.01")


async def _require_manager(session: AsyncSession, venue_id: int, manager_id: int) -> None:
    if await session.get(HallManager, (venue_id, manager_id)) is None:
        raise AccessDenied("менеджер не закреплён за площадкой")


async def _hall(session: AsyncSession, hall_id: int) -> Hall:
    hall = await session.get(Hall, hall_id)
    if hall is None:
        raise NotFound(f"зал {hall_id}")
    return hall


async def get_booking(session: AsyncSession, booking_id: int) -> HallBooking:
    booking = await session.get(HallBooking, booking_id)
    if booking is None:
        raise NotFound(f"бронь {booking_id}")
    return booking


# --- Залы ---


async def create_hall(
    session: AsyncSession,
    *,
    manager_id: int,
    venue_id: int,
    name: str,
    capacity: int,
    hourly_rate: Decimal,
) -> Hall:
    await _require_manager(session, venue_id, manager_id)
    name = name.strip()
    if not name:
        raise DomainError("у зала должно быть название")
    taken = await session.scalar(select(Hall.id).where(Hall.venue_id == venue_id, Hall.name == name))
    if taken is not None:
        raise DomainError(f"на площадке уже есть зал «{name}»")
    hall = Hall(venue_id=venue_id, name=name, capacity=capacity, hourly_rate=hourly_rate)
    session.add(hall)
    await session.flush()
    return hall


async def deactivate_hall(session: AsyncSession, hall_id: int, manager_id: int) -> Hall:
    hall = await _hall(session, hall_id)
    await _require_manager(session, hall.venue_id, manager_id)
    upcoming = await session.scalar(
        select(func.count()).where(
            HallBooking.hall_id == hall_id,
            HallBooking.status.in_(settings.ACTIVE_STATUSES),
            HallBooking.ends_at > clock.now(),
        )
    )
    if upcoming:
        raise DomainError("в зале есть предстоящие брони — сначала перенесите или отмените их")
    hall.active = False
    return hall


async def venue_halls(session: AsyncSession, venue_id: int) -> list[Hall]:
    rows = await session.scalars(
        select(Hall).where(Hall.venue_id == venue_id, Hall.active.is_(True)).order_by(Hall.name)
    )
    return list(rows.all())


# --- Бронирование ---


def _check_period(starts_at: datetime, ends_at: datetime) -> None:
    now = clock.now()
    if starts_at - now < timedelta(days=settings.MIN_LEAD_DAYS):
        raise DomainError(f"зал бронируется не позднее чем за {settings.MIN_LEAD_DAYS} дн. до мероприятия")
    if starts_at - now > timedelta(days=settings.BOOKING_HORIZON_DAYS):
        raise DomainError("слишком далёкая дата мероприятия")
    duration = ends_at - starts_at
    if duration < timedelta(hours=settings.MIN_DURATION_HOURS):
        raise DomainError(f"минимальная аренда — {settings.MIN_DURATION_HOURS} ч")
    if duration > timedelta(hours=settings.MAX_DURATION_HOURS):
        raise DomainError(f"максимальная аренда — {settings.MAX_DURATION_HOURS} ч")


async def _check_hall_free(
    session: AsyncSession,
    hall: Hall,
    starts_at: datetime,
    ends_at: datetime,
    exclude_id: int | None = None,
) -> None:
    gap = timedelta(minutes=settings.CLEANUP_MINUTES)
    query = select(HallBooking.id).where(
        HallBooking.hall_id == hall.id,
        HallBooking.status.in_(settings.ACTIVE_STATUSES),
        HallBooking.starts_at < ends_at + gap,
        HallBooking.ends_at + gap > starts_at,
    )
    if exclude_id is not None:
        query = query.where(HallBooking.id != exclude_id)
    if await session.scalar(query.limit(1)) is not None:
        raise DomainError(f"зал «{hall.name}» занят в это время")


def _check_fits(hall: Hall, guests: int) -> None:
    if not hall.active:
        raise DomainError(f"зал «{hall.name}» не сдаётся")
    if guests > hall.capacity:
        raise DomainError(f"зал «{hall.name}» вмещает не больше {hall.capacity} гостей")


def rent_amount(hall: Hall, starts_at: datetime, ends_at: datetime) -> Decimal:
    minutes = Decimal(int((ends_at - starts_at).total_seconds() // 60))
    return (hall.hourly_rate * minutes / 60).quantize(CENT)


async def create_booking(
    session: AsyncSession,
    *,
    manager_id: int,
    hall_id: int,
    client_ref: str,
    event_kind: str,
    guests: int,
    starts_at: datetime,
    ends_at: datetime,
) -> HallBooking:
    hall = await _hall(session, hall_id)
    await _require_manager(session, hall.venue_id, manager_id)
    if event_kind not in settings.EVENT_KINDS:
        raise DomainError(f"неизвестный вид мероприятия: {event_kind}")
    if guests <= 0:
        raise DomainError("число гостей должно быть положительным")
    _check_fits(hall, guests)
    _check_period(starts_at, ends_at)
    await _check_hall_free(session, hall, starts_at, ends_at)

    booking = HallBooking(
        hall_id=hall.id,
        venue_id=hall.venue_id,
        client_ref=client_ref,
        event_kind=event_kind,
        guests=guests,
        starts_at=starts_at,
        ends_at=ends_at,
        status="draft",
        created_by=manager_id,
        created_at=clock.now(),
    )
    session.add(booking)
    await session.flush()
    events.publish(
        session,
        "halls.booking_created",
        {
            "booking_id": booking.id,
            "hall_id": hall.id,
            "venue_id": hall.venue_id,
            "starts_at": starts_at.isoformat(),
        },
    )
    await issue_invoice(session, booking, hall)
    return booking


async def change_venue(
    session: AsyncSession, booking_id: int, manager_id: int, new_hall_id: int
) -> HallBooking:
    """Перенос брони в зал другой площадки. Счёт перевыставляется по ставке нового зала."""
    booking = await get_booking(session, booking_id)
    await _require_manager(session, booking.venue_id, manager_id)
    if booking.status not in ("draft", "prepaid"):
        raise DomainError("площадку можно сменить только до подтверждения брони")
    hall = await _hall(session, new_hall_id)
    if hall.venue_id == booking.venue_id:
        raise DomainError("зал находится на той же площадке")
    _check_fits(hall, booking.guests)
    await _check_hall_free(session, hall, booking.starts_at, booking.ends_at, exclude_id=booking.id)

    old_venue_id = booking.venue_id
    booking.hall_id = hall.id
    booking.venue_id = hall.venue_id
    await session.flush()
    events.publish(
        session,
        "halls.venue_changed",
        {"booking_id": booking.id, "old_venue_id": old_venue_id, "venue_id": hall.venue_id},
    )
    return booking


async def _cancel(session: AsyncSession, booking: HallBooking, *, reason: str, at: datetime) -> None:
    booking.status = "cancelled"
    booking.cancelled_at = at
    booking.cancel_reason = reason
    events.publish(
        session,
        "halls.booking_cancelled",
        {
            "booking_id": booking.id,
            "venue_id": booking.venue_id,
            "starts_at": booking.starts_at.isoformat(),
            "reason": reason,
        },
    )


async def cancel_booking(
    session: AsyncSession, booking_id: int, manager_id: int, reason: str = "client_request"
) -> HallBooking:
    booking = await get_booking(session, booking_id)
    await _require_manager(session, booking.venue_id, manager_id)
    if booking.status == "cancelled":
        raise DomainError("бронь уже отменена")
    if booking.status == "held":
        raise DomainError("мероприятие уже прошло")
    await _cancel(session, booking, reason=reason, at=clock.now())
    return booking


async def cancel_unpaid(session: AsyncSession, booking: HallBooking, now: datetime) -> None:
    await _cancel(session, booking, reason="unpaid", at=now)


async def mark_held(session: AsyncSession, booking: HallBooking) -> None:
    booking.status = "held"
    events.publish(
        session,
        "halls.booking_held",
        {"booking_id": booking.id, "venue_id": booking.venue_id, "hall_id": booking.hall_id},
    )


# --- Счета и оплата ---


async def active_invoice(session: AsyncSession, booking_id: int) -> HallInvoice | None:
    return await session.scalar(
        select(HallInvoice).where(HallInvoice.booking_id == booking_id, HallInvoice.status != "void")
    )


async def paid_total(session: AsyncSession, invoice_id: int) -> Decimal:
    total = await session.scalar(
        select(func.coalesce(func.sum(HallPayment.amount), 0)).where(HallPayment.invoice_id == invoice_id)
    )
    return Decimal(total)


async def is_fully_paid(session: AsyncSession, invoice: HallInvoice) -> bool:
    return await paid_total(session, invoice.id) >= invoice.amount


async def issue_invoice(session: AsyncSession, booking: HallBooking, hall: Hall) -> HallInvoice:
    invoice = HallInvoice(
        booking_id=booking.id,
        amount=rent_amount(hall, booking.starts_at, booking.ends_at),
        status="open",
        issued_at=clock.now(),
    )
    session.add(invoice)
    await session.flush()
    events.publish(
        session,
        "halls.invoice_issued",
        {"booking_id": booking.id, "invoice_id": invoice.id, "amount": str(invoice.amount)},
    )
    return invoice


async def reissue_invoice(session: AsyncSession, booking_id: int) -> HallInvoice | None:
    """Аннулирует действующий счёт брони и выставляет новый; принятые платежи переходят в новый счёт."""
    booking = await get_booking(session, booking_id)
    if booking.status not in ("draft", "prepaid"):
        return None
    old = await active_invoice(session, booking.id)
    if old is not None:
        old.status = "void"
        old.closed_at = clock.now()
        await session.flush()
    invoice = await issue_invoice(session, booking, await _hall(session, booking.hall_id))
    if old is not None:
        await session.execute(
            update(HallPayment).where(HallPayment.invoice_id == old.id).values(invoice_id=invoice.id)
        )
        if await is_fully_paid(session, invoice):
            invoice.status = "paid"
            invoice.closed_at = clock.now()
        events.publish(
            session, "halls.payment_received", {"booking_id": booking.id, "invoice_id": invoice.id}
        )
    return invoice


async def void_invoice(session: AsyncSession, booking_id: int) -> None:
    invoice = await active_invoice(session, booking_id)
    if invoice is not None and invoice.status == "open":
        invoice.status = "void"
        invoice.closed_at = clock.now()


async def record_payment(
    session: AsyncSession,
    invoice_id: int,
    amount: Decimal,
    recorded_by: int,
    external_ref: str | None = None,
) -> HallPayment:
    invoice = await session.get(HallInvoice, invoice_id)
    if invoice is None:
        raise NotFound(f"счёт {invoice_id}")
    if invoice.status != "open":
        raise DomainError("счёт закрыт, платёж принять нельзя")
    booking = await get_booking(session, invoice.booking_id)
    if booking.status == "cancelled":
        raise DomainError("бронь отменена, платёж принять нельзя")
    if amount <= 0:
        raise DomainError("сумма платежа должна быть положительной")
    if external_ref is not None:
        dup = await session.scalar(select(HallPayment.id).where(HallPayment.external_ref == external_ref))
        if dup is not None:
            raise DomainError(f"платёж {external_ref} уже учтён")
    rest = invoice.amount - await paid_total(session, invoice.id)
    if amount > rest:
        raise DomainError(f"сумма больше остатка по счёту ({rest})")

    payment = HallPayment(
        invoice_id=invoice.id,
        amount=amount,
        external_ref=external_ref,
        recorded_by=recorded_by,
        paid_at=clock.now(),
    )
    session.add(payment)
    await session.flush()
    if await is_fully_paid(session, invoice):
        invoice.status = "paid"
        invoice.closed_at = clock.now()
    events.publish(
        session,
        "halls.payment_received",
        {"booking_id": booking.id, "invoice_id": invoice.id, "amount": str(amount)},
    )
    return payment


async def apply_payments(session: AsyncSession, booking_id: int) -> HallBooking:
    """Пересчитывает статус брони по оплате действующего счёта."""
    booking = await get_booking(session, booking_id)
    if booking.status not in ("draft", "prepaid"):
        return booking
    invoice = await active_invoice(session, booking.id)
    if invoice is None:
        return booking
    paid = await paid_total(session, invoice.id)
    payload = {"booking_id": booking.id, "venue_id": booking.venue_id, "invoice_id": invoice.id}
    if await is_fully_paid(session, invoice):
        booking.status = "confirmed"
        booking.confirmed_at = clock.now()
        events.publish(session, "halls.booking_confirmed", payload)
    elif paid >= invoice.amount * settings.PREPAY_SHARE:
        if booking.status == "draft":
            booking.status = "prepaid"
            events.publish(session, "halls.booking_prepaid", payload | {"paid": str(paid)})
    elif booking.status == "prepaid":
        # После перевыставления счёта внесённого может не хватать на предоплату.
        booking.status = "draft"
    return booking


# --- Письма клиенту ---


async def set_template(
    session: AsyncSession, *, manager_id: int, venue_id: int, kind_group: str, type_: str, body: str
) -> HallTemplate:
    await _require_manager(session, venue_id, manager_id)
    if kind_group not in set(settings.TEMPLATE_GROUP.values()):
        raise DomainError(f"неизвестная группа шаблонов: {kind_group}")
    tpl = await session.scalar(
        select(HallTemplate).where(
            HallTemplate.venue_id == venue_id,
            HallTemplate.kind_group == kind_group,
            HallTemplate.type == type_,
        )
    )
    if tpl is None:
        tpl = HallTemplate(venue_id=venue_id, kind_group=kind_group, type=type_, body=body)
        session.add(tpl)
    else:
        tpl.body = body
    await session.flush()
    return tpl


async def find_template(
    session: AsyncSession, venue_id: int, event_kind: str, type_: str
) -> HallTemplate | None:
    return await session.scalar(
        select(HallTemplate).where(
            HallTemplate.venue_id == venue_id,
            HallTemplate.kind_group == settings.TEMPLATE_GROUP[event_kind],
            HallTemplate.type == type_,
        )
    )


async def send_email(
    session: AsyncSession, booking_id: int, type_: str, extra: dict[str, Any] | None = None
) -> HallEmail:
    booking = await get_booking(session, booking_id)
    hall = await _hall(session, booking.hall_id)
    tpl = await find_template(session, booking.venue_id, booking.event_kind, type_)
    context = {
        "hall": hall.name,
        "starts_at": booking.starts_at.strftime("%d.%m.%Y %H:%M"),
        "guests": booking.guests,
        **(extra or {}),
    }
    email = HallEmail(
        booking_id=booking.id,
        client_ref=booking.client_ref,
        type=type_,
        template_id=tpl.id if tpl else None,
        body=Text(tpl.body).safe_substitute(context) if tpl else "",
        status="sent" if tpl else "no_template",
        created_at=clock.now(),
    )
    session.add(email)
    await session.flush()
    return email
