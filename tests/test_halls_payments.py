from decimal import Decimal

import pytest
from sqlalchemy.exc import DBAPIError

from libs import db
from libs.errors import DomainError
from services.halls import service as halls
from tests.factories import act, read
from tests.halls_factories import (
    ACCOUNTANT,
    MANAGER,
    PANORAMA_HALL,
    booking,
    email_types,
    emails,
    invoice,
    invoices,
    new_booking,
    pay,
    seed_halls,
    status,
)


@pytest.fixture(autouse=True)
async def halls_data(world: None) -> None:
    await seed_halls()


async def test_half_payment_makes_booking_prepaid() -> None:
    b = await new_booking()
    await pay(b.id, Decimal(4000), ref="bank-1")
    assert await status(b.id) == "draft"

    await pay(b.id, Decimal(6000), ref="bank-2")
    assert await status(b.id) == "prepaid"
    inv = await invoice(b.id)
    assert inv.status == "open"
    assert not await read(halls.is_fully_paid, inv)
    assert await email_types(b.id) == ["invoice", "prepaid"]


async def test_full_payment_confirms_booking_in_one_step() -> None:
    b = await new_booking(kind="corporate", guests=60)
    await pay(b.id)

    confirmed = await booking(b.id)
    assert confirmed.status == "confirmed"
    assert confirmed.confirmed_at is not None
    inv = await invoice(b.id)
    assert inv.status == "paid"
    assert await read(halls.is_fully_paid, inv)
    sent = await emails(b.id)
    assert [e.type for e in sent] == ["invoice", "confirmed"]
    assert sent[-1].body.startswith("V11 corporate confirmed: Белый зал 22.03.2026")


async def test_payment_over_rest_rejected() -> None:
    b = await new_booking()
    await pay(b.id, Decimal(15000))
    with pytest.raises(DomainError, match=r"больше остатка по счёту \(5000"):
        await pay(b.id, Decimal(6000))


async def test_duplicate_bank_reference_rejected() -> None:
    b = await new_booking()
    await pay(b.id, Decimal(1000), ref="bank-7")
    with pytest.raises(DomainError, match="уже учтён"):
        await pay(b.id, Decimal(1000), ref="bank-7")


async def test_payment_to_void_invoice_rejected_in_service_and_db() -> None:
    b = await new_booking()
    await act(halls.change_venue, b.id, MANAGER[11], PANORAMA_HALL)
    old, _ = await invoices(b.id)
    with pytest.raises(DomainError, match="счёт закрыт"):
        await act(halls.record_payment, old.id, Decimal(100), ACCOUNTANT)
    with pytest.raises(DBAPIError, match="платёж не принимается"):
        async with db.engine().begin() as conn:
            await conn.exec_driver_sql(
                "INSERT INTO halls.hall_payments (invoice_id, amount, recorded_by, paid_at) "
                f"VALUES ({old.id}, 100, {ACCOUNTANT}, now())"
            )
