from datetime import timedelta
from decimal import Decimal

import pytest

from libs.errors import DomainError
from services.halls import jobs
from services.halls import service as halls
from tests.factories import T0, act, travel
from tests.halls_factories import (
    CENTER,
    EVENT_END,
    LOFT,
    LOFT_HALL,
    MANAGER,
    booking,
    emails,
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


async def test_cancel_sends_letter_from_event_group_template() -> None:
    wedding = await new_booking()
    conference = await new_booking(
        client="client:acme", kind="conference", starts_at=EVENT_END + timedelta(days=1)
    )
    for b in (wedding, conference):
        await act(halls.cancel_booking, b.id, MANAGER[CENTER])

    assert (await emails(wedding.id))[-1].body.startswith("V11 private cancel:")
    assert (await emails(conference.id))[-1].body.startswith("V11 corporate cancel:")
    cancelled = await booking(wedding.id)
    assert cancelled.status == "cancelled"
    assert cancelled.cancel_reason == "client_request"
    (inv,) = await invoices(wedding.id)
    assert inv.status == "void"


async def test_venue_without_templates_records_unsent_letter() -> None:
    b = await new_booking(hall=LOFT_HALL, guests=30)
    await act(halls.cancel_booking, b.id, MANAGER[LOFT])
    letter = (await emails(b.id))[-1]
    assert (letter.type, letter.status, letter.template_id) == ("cancel", "no_template", None)


async def test_cancelled_and_held_bookings_cannot_be_cancelled_or_paid() -> None:
    b = await new_booking()
    await pay(b.id, Decimal(1000))
    await act(halls.cancel_booking, b.id, MANAGER[CENTER])
    with pytest.raises(DomainError, match="уже отменена"):
        await act(halls.cancel_booking, b.id, MANAGER[CENTER])

    paid = await new_booking(client="client:boris")
    await pay(paid.id)
    travel(EVENT_END + timedelta(hours=1))
    await act(jobs.close_past_events, now=EVENT_END + timedelta(hours=1))
    assert await status(paid.id) == "held"
    with pytest.raises(DomainError, match="уже прошло"):
        await act(halls.cancel_booking, paid.id, MANAGER[CENTER])


async def test_unpaid_booking_cancelled_after_thirty_days() -> None:
    unpaid = await new_booking(starts_at=T0 + timedelta(days=60))
    partly = await new_booking(client="client:boris", starts_at=T0 + timedelta(days=61))
    prepaid = await new_booking(client="client:vera", starts_at=T0 + timedelta(days=62))
    await pay(partly.id, Decimal(1000))
    await prepay(prepaid.id)

    assert await act(jobs.cancel_unpaid, now=T0 + timedelta(days=29, hours=23)) == []
    cancelled = await act(jobs.cancel_unpaid, now=T0 + timedelta(days=30))

    assert cancelled == [unpaid.id, partly.id]
    assert await status(prepaid.id) == "prepaid"
    for b in (unpaid, partly):
        assert (await booking(b.id)).cancel_reason == "unpaid"
        assert (await emails(b.id))[-1].type == "cancel"
        assert (await invoices(b.id))[-1].status == "void"
    assert (await invoice(prepaid.id)).status == "open"


async def test_close_past_events_skips_unconfirmed() -> None:
    confirmed = await new_booking()
    draft = await new_booking(client="client:boris", starts_at=EVENT_END + timedelta(hours=2))
    await pay(confirmed.id)

    held = await act(jobs.close_past_events, now=EVENT_END + timedelta(days=1))
    assert held == [confirmed.id]
    assert await status(draft.id) == "draft"
