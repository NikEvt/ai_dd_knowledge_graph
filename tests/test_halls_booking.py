from datetime import timedelta
from decimal import Decimal

import pytest
from sqlalchemy.exc import DBAPIError

from libs import db
from libs.errors import AccessDenied, DomainError
from services.halls import service as halls
from tests.factories import T0, act, read
from tests.halls_factories import (
    CENTER,
    CHAMBER_HALL,
    EVENT_END,
    EVENT_START,
    LOFT,
    LOFT_HALL,
    MANAGER,
    PANORAMA_HALL,
    RIVER,
    WHITE_HALL,
    booking,
    email_types,
    history,
    invoice,
    invoices,
    new_booking,
    pay,
    prepay,
    seed_halls,
    status,
)


@pytest.fixture(autouse=True)
async def halls_data(world: None) -> None:
    await seed_halls()


async def test_booking_starts_as_draft_with_invoice() -> None:
    b = await new_booking()
    assert b.status == "draft"
    assert b.venue_id == CENTER
    inv = await invoice(b.id)
    # 4 часа по 5000
    assert inv.amount == Decimal("20000.00")
    assert inv.status == "open"
    assert await email_types(b.id) == ["invoice"]


async def test_partial_hours_are_billed_by_minutes() -> None:
    b = await new_booking(ends_at=EVENT_START + timedelta(hours=2, minutes=30))
    assert (await invoice(b.id)).amount == Decimal("12500.00")


async def test_manager_of_other_venue_cannot_book() -> None:
    with pytest.raises(AccessDenied, match="не закреплён"):
        await new_booking(manager=MANAGER[RIVER])


async def test_guests_over_capacity_rejected() -> None:
    with pytest.raises(DomainError, match="не больше 20 гостей"):
        await new_booking(hall=CHAMBER_HALL, guests=25)


@pytest.mark.parametrize(
    ("starts_at", "hours", "message"),
    [
        (T0 + timedelta(days=1), 4, "не позднее чем за 2"),
        (T0 + timedelta(days=400), 4, "далёкая дата"),
        (EVENT_START, 1, "минимальная аренда"),
        (EVENT_START, 14, "максимальная аренда"),
    ],
)
async def test_booking_period_rules(starts_at, hours: int, message: str) -> None:
    with pytest.raises(DomainError, match=message):
        await new_booking(starts_at=starts_at, ends_at=starts_at + timedelta(hours=hours))


async def test_overlapping_booking_rejected_with_cleanup_gap() -> None:
    await new_booking()
    with pytest.raises(DomainError, match="занят"):
        # Начало через 30 минут после окончания — не успеют убрать зал.
        await new_booking(client="client:boris", starts_at=EVENT_END + timedelta(minutes=30))
    later = await new_booking(client="client:boris", starts_at=EVENT_END + timedelta(hours=1))
    assert later.status == "draft"


async def test_cancelled_booking_frees_hall() -> None:
    first = await new_booking()
    await act(halls.cancel_booking, first.id, MANAGER[CENTER])
    second = await new_booking(client="client:boris")
    assert second.starts_at == first.starts_at


async def test_change_venue_moves_booking_and_reissues_invoice() -> None:
    b = await new_booking()
    await act(halls.change_venue, b.id, MANAGER[CENTER], PANORAMA_HALL)

    moved = await booking(b.id)
    assert (moved.venue_id, moved.hall_id) == (RIVER, PANORAMA_HALL)
    old, new = await invoices(b.id)
    assert old.status == "void"
    assert new.status == "open"
    assert new.amount == Decimal("24000.00")
    assert await email_types(b.id) == ["invoice", "invoice"]


async def test_change_venue_keeps_prepayment() -> None:
    b = await new_booking(guests=35)
    await prepay(b.id)
    assert await status(b.id) == "prepaid"

    # Новый зал дешевле: внесённые 10000 покрывают уже больше половины.
    await act(halls.change_venue, b.id, MANAGER[CENTER], LOFT_HALL)
    inv = await invoice(b.id)
    assert inv.amount == Decimal("12000.00")
    assert await read(halls.paid_total, inv.id) == Decimal("10000.00")
    assert await status(b.id) == "prepaid"


async def test_change_venue_to_pricier_hall_can_drop_prepaid() -> None:
    b = await new_booking(hall=LOFT_HALL, guests=35)
    await prepay(b.id)
    assert await status(b.id) == "prepaid"
    # 6000 из нового счёта на 24000 — меньше половины.
    await act(halls.change_venue, b.id, MANAGER[LOFT], PANORAMA_HALL)
    assert await status(b.id) == "draft"


async def test_change_venue_within_same_venue_rejected() -> None:
    b = await new_booking()
    with pytest.raises(DomainError, match="той же площадке"):
        await act(halls.change_venue, b.id, MANAGER[CENTER], CHAMBER_HALL)


async def test_change_venue_requires_manager_of_current_venue() -> None:
    b = await new_booking()
    with pytest.raises(AccessDenied):
        await act(halls.change_venue, b.id, MANAGER[RIVER], PANORAMA_HALL)


async def test_change_venue_after_confirmation_forbidden() -> None:
    b = await new_booking()
    await pay(b.id)
    assert await status(b.id) == "confirmed"
    with pytest.raises(DomainError, match="до подтверждения"):
        await act(halls.change_venue, b.id, MANAGER[CENTER], PANORAMA_HALL)


async def test_venue_lock_trigger_protects_confirmed_booking() -> None:
    b = await new_booking()
    await pay(b.id)
    with pytest.raises(DBAPIError, match="площадку сменить нельзя"):
        async with db.engine().begin() as conn:
            await conn.exec_driver_sql(
                f"UPDATE halls.hall_bookings SET venue_id = {RIVER}, hall_id = {PANORAMA_HALL} "
                f"WHERE id = {b.id}"
            )
    assert (await booking(b.id)).venue_id == CENTER


async def test_status_history_written_by_trigger() -> None:
    b = await new_booking()
    await prepay(b.id)
    await pay(b.id, Decimal(10000))
    assert await history(b.id) == [(None, "draft"), ("draft", "prepaid"), ("prepaid", "confirmed")]


async def test_deactivate_hall_with_upcoming_bookings_rejected() -> None:
    await new_booking()
    with pytest.raises(DomainError, match="предстоящие брони"):
        await act(halls.deactivate_hall, WHITE_HALL, MANAGER[CENTER])
    hall = await act(halls.deactivate_hall, CHAMBER_HALL, MANAGER[CENTER])
    assert hall.active is False
    with pytest.raises(DomainError, match="не сдаётся"):
        await new_booking(hall=CHAMBER_HALL, guests=10)
