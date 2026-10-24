"""Данные и типовые шаги сервиса аренды залов для тестов."""

from datetime import datetime, timedelta
from decimal import Decimal

from sqlalchemy import select

from libs import db
from services.halls import service as halls
from services.halls.models import (
    BookingHistory,
    Hall,
    HallBooking,
    HallEmail,
    HallInvoice,
    HallManager,
    HallTemplate,
)
from tests.factories import T0, act, read

# Площадки — просто номера, ядро про них не знает.
CENTER, RIVER, LOFT = 11, 12, 13
MANAGER = {CENTER: 801, RIVER: 802, LOFT: 803}
ACCOUNTANT = 901

WHITE_HALL, CHAMBER_HALL, PANORAMA_HALL, LOFT_HALL = 1, 2, 3, 4

EVENT_START = T0 + timedelta(days=20, hours=6)  # 22 марта, 15:00 UTC
EVENT_END = EVENT_START + timedelta(hours=4)


async def seed_halls() -> None:
    async with db.sessionmaker().begin() as s:
        s.add_all([HallManager(venue_id=v, manager_id=m) for v, m in MANAGER.items()])
        s.add_all(
            [
                Hall(
                    id=WHITE_HALL, venue_id=CENTER, name="Белый зал", capacity=80, hourly_rate=Decimal(5000)
                ),
                Hall(
                    id=CHAMBER_HALL, venue_id=CENTER, name="Камерный", capacity=20, hourly_rate=Decimal(2000)
                ),
                Hall(
                    id=PANORAMA_HALL, venue_id=RIVER, name="Панорама", capacity=120, hourly_rate=Decimal(6000)
                ),
                Hall(id=LOFT_HALL, venue_id=LOFT, name="Лофт", capacity=40, hourly_rate=Decimal(3000)),
            ]
        )
        for venue_id in (CENTER, RIVER):
            for group in ("corporate", "private"):
                for type_ in ("invoice", "prepaid", "confirmed", "cancel"):
                    s.add(
                        HallTemplate(
                            venue_id=venue_id,
                            kind_group=group,
                            type=type_,
                            body=f"V{venue_id} {group} {type_}: $hall $starts_at",
                        )
                    )
    async with db.engine().begin() as conn:
        await conn.exec_driver_sql("SELECT setval(pg_get_serial_sequence('halls.halls', 'id'), 100)")


async def new_booking(
    *,
    hall: int = WHITE_HALL,
    client: str = "client:anna",
    kind: str = "wedding",
    guests: int = 50,
    starts_at: datetime = EVENT_START,
    ends_at: datetime | None = None,
    manager: int | None = None,
) -> HallBooking:
    hall_obj = await read(lambda s: s.get(Hall, hall))
    return await act(
        halls.create_booking,
        manager_id=manager or MANAGER[hall_obj.venue_id],
        hall_id=hall,
        client_ref=client,
        event_kind=kind,
        guests=guests,
        starts_at=starts_at,
        ends_at=ends_at or starts_at + (EVENT_END - EVENT_START),
    )


async def booking(booking_id: int) -> HallBooking:
    return await read(halls.get_booking, booking_id)


async def status(booking_id: int) -> str:
    return (await booking(booking_id)).status


async def invoice(booking_id: int) -> HallInvoice:
    return await read(halls.active_invoice, booking_id)


async def pay(booking_id: int, amount: Decimal | None = None, ref: str | None = None) -> None:
    inv = await invoice(booking_id)
    await act(halls.record_payment, inv.id, inv.amount if amount is None else amount, ACCOUNTANT, ref)


async def prepay(booking_id: int) -> None:
    inv = await invoice(booking_id)
    await pay(booking_id, inv.amount / 2)


async def emails(booking_id: int) -> list[HallEmail]:
    async def q(s):
        rows = await s.scalars(
            select(HallEmail).where(HallEmail.booking_id == booking_id).order_by(HallEmail.id)
        )
        return list(rows.all())

    return await read(q)


async def email_types(booking_id: int) -> list[str]:
    return [e.type for e in await emails(booking_id)]


async def history(booking_id: int) -> list[tuple[str | None, str]]:
    async def q(s):
        rows = await s.execute(
            select(BookingHistory.old_status, BookingHistory.new_status)
            .where(BookingHistory.booking_id == booking_id)
            .order_by(BookingHistory.id)
        )
        return [tuple(r) for r in rows.all()]

    return await read(q)


async def invoices(booking_id: int) -> list[HallInvoice]:
    async def q(s):
        rows = await s.scalars(
            select(HallInvoice).where(HallInvoice.booking_id == booking_id).order_by(HallInvoice.id)
        )
        return list(rows.all())

    return await read(q)
